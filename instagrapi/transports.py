"""Optional transports for the requests sessions used by Client."""

import os
import re
from email.message import Message
from io import BytesIO
from types import SimpleNamespace
from urllib.parse import urlsplit

from requests import exceptions
from requests.adapters import HTTPAdapter
from requests.utils import select_proxy
from urllib3._collections import HTTPHeaderDict
from urllib3.response import HTTPResponse


def create_curl_h2_adapter():
    return _CurlH2Adapter()


class _CurlH2Adapter(HTTPAdapter):
    """Buffered private API transport with h2-only ALPN and no request retries.

    Requests owns redirects, cookies and decompression. Curl owns the persistent
    connection pool; browser impersonation and its extra headers are disabled.
    """

    def __init__(self):
        try:
            import curl_cffi
            from curl_cffi import CurlHttpVersion, CurlOpt, ffi
            from curl_cffi import requests as curl_requests
        except ImportError as exc:
            raise RuntimeError(
                "curl private transport requires the optional curl extra: pip install instagrapi[curl]"
            ) from exc

        version = re.search(r"libcurl/(\d+)\.(\d+)\.(\d+)", curl_cffi.__curl_version__)
        if not version or tuple(map(int, version.groups())) < (8, 10, 0):
            raise RuntimeError("curl private transport requires libcurl >= 8.10.0 for h2-only ALPN")

        super().__init__(max_retries=0)
        self._curl_requests = curl_requests
        self._http2 = CurlHttpVersion.V2_0
        self._capath_option = CurlOpt.CAPATH
        self._cainfo_option = CurlOpt.CAINFO
        self._null_pointer = ffi.NULL
        self.client = curl_requests.Session(
            trust_env=False,
            default_headers=False,
            discard_cookies=True,
            http_version=CurlHttpVersion.V2_PRIOR_KNOWLEDGE,
            curl_options={
                CurlOpt.HTTP_CONTENT_DECODING: 0,
                # Requests has already resolved environment proxies/no_proxy.
                CurlOpt.NOPROXY: "",
            },
        )
        # curl_cffi reads CA environment variables even with trust_env=False.
        # Only the outer requests session may resolve that environment policy.
        self.client.verify = True

    def send(self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None):
        if timeout is not None:
            values = timeout if isinstance(timeout, tuple) else (timeout,)
            if (isinstance(timeout, tuple) and len(timeout) != 2) or any(
                not isinstance(value, (int, float)) for value in values
            ):
                raise ValueError("curl timeout must be numeric, a pair of numeric values, or None")
        # curl_cffi treats string verify values as CA files; requests also accepts
        # hashed CA directories. Clear the previous directory on every send.
        self.client.curl_options.pop(self._capath_option, None)
        self.client.curl_options.pop(self._cainfo_option, None)
        if isinstance(verify, str) and os.path.isdir(verify):
            self.client.curl_options[self._capath_option] = verify
            self.client.curl_options[self._cainfo_option] = self._null_pointer
            verify = True
        body = request.body
        if hasattr(body, "read"):
            body = body.read()
        if body is not None and not isinstance(body, (str, bytes, bytearray)):
            body = b"".join(chunk.encode() if isinstance(chunk, str) else chunk for chunk in body)
        if isinstance(body, bytearray):
            body = bytes(body)
        try:
            upstream = self.client.request(
                request.method,
                request.url,
                data=body,
                headers=list(request.headers.items()),
                # An explicit empty proxy prevents libcurl from reading the
                # process environment when requests.Session.trust_env is False.
                proxies={"all": select_proxy(request.url, proxies) or ""},
                timeout=timeout,
                verify=verify,
                cert=cert,
                allow_redirects=False,
                default_headers=False,
                accept_encoding=None,
                discard_cookies=True,
                quote=False,
            )
        except self._curl_requests.exceptions.RequestException as exc:
            # curl_cffi adds subclasses such as CertificateVerifyError and
            # DNSError; preserve their requests-compatible parent category.
            error_class = exceptions.RequestException
            transport_errors = {
                # A partial transfer must not enter private_request's legacy
                # incomplete-read retry and resubmit a credential-bearing POST.
                "IncompleteRead": exceptions.ConnectionError,
                # Curl uses HTTPError for HTTP/2 protocol/stream failures.
                # HTTP status errors are raised later by requests with a Response.
                "HTTPError": exceptions.ConnectionError,
            }
            for parent in type(exc).__mro__:
                candidate = transport_errors.get(parent.__name__, getattr(exceptions, parent.__name__, None))
                if isinstance(candidate, type) and issubclass(candidate, exceptions.RequestException):
                    error_class = candidate
                    break
            raise error_class(f"curl private transport failed ({type(exc).__name__})", request=request) from exc

        if urlsplit(request.url).scheme == "https" and upstream.http_version != self._http2:
            raise exceptions.ConnectionError("curl private transport did not negotiate HTTP/2", request=request)

        pairs = list(upstream.headers.multi_items())
        message = Message()
        for name, value in pairs:
            message[name] = value
        raw = HTTPResponse(
            body=BytesIO(upstream.content),
            headers=HTTPHeaderDict(pairs),
            status=upstream.status_code,
            reason=upstream.reason,
            version=20,
            request_method=request.method,
            preload_content=False,
            decode_content=False,
            original_response=SimpleNamespace(msg=message, close=lambda: None, isclosed=lambda: True),
        )
        return self.build_response(request, raw)

    def close(self):
        self.client.close()
        super().close()
