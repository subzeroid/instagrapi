"""Opt-in private HTTP/2 transport over the pinned tls-client native library.

Requests owns cookies, redirects, headers and proxy selection. The native client
owns connection pooling and response decompression. No retries or fallback.
"""

import base64
import ctypes
import json
import math
import threading
from email.message import Message
from io import BytesIO
from types import SimpleNamespace
from urllib.parse import urlsplit
from uuid import uuid4

from requests import exceptions
from requests.adapters import HTTPAdapter
from requests.utils import select_proxy
from urllib3._collections import HTTPHeaderDict
from urllib3.response import HTTPResponse

from instagrapi.utls_native import load_library

# Accepted in CAA experiments with Android app profile 449.0.0.52.84. This is
# not claimed to be a capture of the official Android client's fingerprint:
# https://github.com/subzeroid/instagrapi/issues/2852#issuecomment-6071774879
_PROFILE = {
    "ja3String": "771,4865,0-43-10-51-13-16-45,29-23,",
    "supportedVersions": ["1.3"],
    "supportedSignatureAlgorithms": ["ECDSAWithP256AndSHA256", "ECDSAWithP384AndSHA384", "PSSWithSHA256"],
    "keyShareCurves": ["X25519"],
    "alpnProtocols": ["h2"],
    "certCompressionAlgos": [],
    "h2Settings": {
        "HEADER_TABLE_SIZE": 65536,
        "ENABLE_PUSH": 0,
        "MAX_CONCURRENT_STREAMS": 1000,
        "INITIAL_WINDOW_SIZE": 6291456,
        "MAX_HEADER_LIST_SIZE": 262144,
    },
    "h2SettingsOrder": [
        "HEADER_TABLE_SIZE",
        "ENABLE_PUSH",
        "MAX_CONCURRENT_STREAMS",
        "INITIAL_WINDOW_SIZE",
        "MAX_HEADER_LIST_SIZE",
    ],
    "pseudoHeaderOrder": [":method", ":authority", ":scheme", ":path"],
    "connectionFlow": 15663105,
}


class _NativeClient:
    def __init__(self, library_path):
        self.library = load_library(library_path)
        self.session_id = str(uuid4())
        self.created = False
        self.closed = False
        self.policy = None
        self.lock = threading.Lock()

    def _call(self, operation, value):
        pointer = getattr(self.library, operation)(json.dumps(value).encode())
        if not pointer:
            raise exceptions.ConnectionError("uTLS native transport returned no response")
        result = None
        try:
            result = json.loads(ctypes.string_at(pointer))
            if not isinstance(result, dict) or not isinstance(result.get("id"), str):
                raise ValueError("invalid response")
            return result
        except (UnicodeDecodeError, ValueError):
            raise exceptions.ConnectionError("uTLS native transport returned malformed JSON") from None
        finally:
            if isinstance(result, dict) and isinstance(result.get("id"), str):
                self.library.freeMemory(result["id"].encode())

    def request(self, value):
        with self.lock:
            if self.closed:
                raise exceptions.ConnectionError("uTLS native session is closed")
            policy = (value["proxyUrl"], value["timeoutMilliseconds"], value["insecureSkipVerify"])
            # The native C API caches client configuration by sessionId. Rebuild
            # before changing TLS, deadline or route; cookies stay in requests.
            if self.policy is not None and self.policy != policy:
                self._close_session()
                self.session_id = str(uuid4())
            self.policy = policy
            result = self._call("request", {**value, "sessionId": self.session_id, "customTlsClient": _PROFILE})
            status = result.get("status")
            if status == 0:
                detail = str(result.get("body", "")).lower()
                # v1.16.0 destroySession panics if client construction failed
                # before creating the cache entry. Request failures have an entry.
                if detail.startswith("failed to do request:"):
                    self.created = True
                error = exceptions.ConnectionError
                if "certificate" in detail or "x509:" in detail or "tls:" in detail:
                    error = exceptions.SSLError
                elif "timeout" in detail or "deadline exceeded" in detail:
                    error = exceptions.Timeout
                raise error("uTLS private transport failed")
            if not isinstance(status, int) or not 100 <= status <= 599:
                raise exceptions.ConnectionError("uTLS native transport returned an invalid HTTP status")
            self.created = True
            if result.get("usedProtocol") != "HTTP/2.0":
                raise exceptions.ConnectionError("uTLS private transport did not negotiate HTTP/2")
            headers, encoded = result.get("headers"), result.get("body")
            if (
                not isinstance(headers, dict)
                or not all(
                    isinstance(name, str) and isinstance(values, list) and all(isinstance(item, str) for item in values)
                    for name, values in headers.items()
                )
                or not isinstance(encoded, str)
                or ";base64," not in encoded
            ):
                raise exceptions.ConnectionError("uTLS native transport returned an invalid HTTP response")
            try:
                body = base64.b64decode(encoded.split(";base64,", 1)[1], validate=True)
            except ValueError:
                raise exceptions.ConnectionError("uTLS native transport returned an invalid response body") from None
            return status, headers, body

    def close(self):
        with self.lock:
            if not self.closed:
                self.closed = True
                self._close_session()

    def _close_session(self):
        if self.created:
            self._call("destroySession", {"sessionId": self.session_id})
            self.created = False


class _UtlsH2Adapter(HTTPAdapter):
    def __init__(self, library_path):
        super().__init__(max_retries=0)
        self.client = _NativeClient(library_path)

    def send(self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None):
        if urlsplit(request.url).scheme != "https":
            raise ValueError("utls private transport supports HTTPS only")
        if verify is not True and verify is not False:
            raise ValueError("utls supports system CA validation; custom CA files and directories are not supported")
        if cert is not None:
            raise ValueError("utls does not support client certificates")
        seconds = 30 if timeout is None else timeout
        if (
            isinstance(seconds, bool)
            or not isinstance(seconds, (int, float))
            or not math.isfinite(seconds)
            or seconds <= 0
        ):
            raise ValueError(
                "utls timeout must be a positive numeric total deadline; connect/read tuples are not supported"
            )
        body = request.body
        if hasattr(body, "read"):
            body = body.read()
        if body is not None and not isinstance(body, (str, bytes, bytearray)):
            body = b"".join(chunk.encode() if isinstance(chunk, str) else chunk for chunk in body)
        binary = isinstance(body, (bytes, bytearray))
        status, headers, content = self.client.request(
            {
                "requestMethod": request.method,
                "requestUrl": request.url,
                "headers": dict(request.headers),
                "headerOrder": [name.lower() for name in request.headers],
                "requestBody": base64.b64encode(body).decode() if binary else body,
                "isByteRequest": binary,
                "isByteResponse": True,
                "withoutCookieJar": True,
                "requestCookies": [],
                "followRedirects": False,
                "forceHttp1": False,
                "disableHttp3": True,
                "withProtocolRacing": False,
                "withRandomTLSExtensionOrder": False,
                "insecureSkipVerify": not verify,
                "timeoutMilliseconds": max(1, math.ceil(seconds * 1000)),
                "proxyUrl": select_proxy(request.url, proxies) or "",
                "withDebug": False,
                "catchPanics": True,
                "transportOptions": {"disableCompression": True},
            }
        )
        # Native BuildResponse decodes bodies. Remove stale encoding/length to
        # avoid a second decode, retaining representation metadata for HEAD/304.
        excluded_headers = (
            set() if request.method == "HEAD" or status == 304 else {"content-encoding", "content-length"}
        )
        pairs = [
            (name, value)
            for name, values in headers.items()
            for value in values
            if name.lower() not in excluded_headers
        ]
        message = Message()
        for name, value in pairs:
            message[name] = value
        raw = HTTPResponse(
            body=BytesIO(content),
            headers=HTTPHeaderDict(pairs),
            status=status,
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


def create_utls_h2_adapter(library_path):
    return _UtlsH2Adapter(library_path)
