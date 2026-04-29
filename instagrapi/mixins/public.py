import json
import logging
import time

try:
    from simplejson.errors import JSONDecodeError
except ImportError:
    from json.decoder import JSONDecodeError

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from instagrapi.exceptions import (
    ClientBadRequestError,
    ClientConnectionError,
    ClientError,
    ClientForbiddenError,
    ClientGraphqlError,
    ClientIncompleteReadError,
    ClientJSONDecodeError,
    ClientLoginRequired,
    ClientNotFoundError,
    ClientThrottledError,
    ClientUnauthorizedError,
)
from instagrapi.utils import random_delay


class PublicRequestMixin:
    public_requests_count = 0
    PUBLIC_API_URL = "https://www.instagram.com/"
    GRAPHQL_PUBLIC_API_URL = "https://www.instagram.com/graphql/query/"
    last_public_response = None
    last_public_json = {}
    public_request_logger = logging.getLogger("public_request")
    request_timeout = 1
    public_request_retries_count = 3
    public_request_retries_timeout = 2
    session_retry_total = 3
    session_retry_backoff_factor = 2
    session_retry_statuses = [429, 500, 502, 503, 504]
    last_response_ts = 0

    def __init__(self, *args, **kwargs):
        session = requests.Session()
        self.public = session
        self.public.verify = False  # fix SSLError/HTTPSConnectionPool
        self.public.headers.update(
            {
                "Connection": "Keep-Alive",
                "Accept": "*/*",
                "Accept-Encoding": "gzip,deflate",
                "Accept-Language": "en-US",
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/605.1.15 "
                    "(KHTML, like Gecko) Version/11.1.2 Safari/605.1.15"
                ),
            }
        )
        self.request_timeout = kwargs.pop(
            "request_timeout", getattr(self, "request_timeout", self.request_timeout)
        )
        self.public_request_retries_count = kwargs.pop(
            "public_request_retries_count",
            getattr(
                self,
                "public_request_retries_count",
                self.public_request_retries_count,
            ),
        )
        self.public_request_retries_timeout = kwargs.pop(
            "public_request_retries_timeout",
            getattr(
                self,
                "public_request_retries_timeout",
                self.public_request_retries_timeout,
            ),
        )
        self.session_retry_total = kwargs.pop(
            "session_retry_total",
            getattr(self, "session_retry_total", self.session_retry_total),
        )
        self.session_retry_backoff_factor = kwargs.pop(
            "session_retry_backoff_factor",
            getattr(
                self,
                "session_retry_backoff_factor",
                self.session_retry_backoff_factor,
            ),
        )
        self.session_retry_statuses = list(
            kwargs.pop(
                "session_retry_statuses",
                getattr(self, "session_retry_statuses", self.session_retry_statuses),
            )
        )
        self._configure_public_session_retry()
        super().__init__(*args, **kwargs)

    def _build_public_session_retry_strategy(self):
        try:
            return Retry(
                total=self.session_retry_total,
                status_forcelist=self.session_retry_statuses,
                allowed_methods=["GET", "POST"],
                backoff_factor=self.session_retry_backoff_factor,
            )
        except TypeError:
            return Retry(
                total=self.session_retry_total,
                status_forcelist=self.session_retry_statuses,
                method_whitelist=["GET", "POST"],
                backoff_factor=self.session_retry_backoff_factor,
            )

    def _configure_public_session_retry(self):
        adapter = HTTPAdapter(max_retries=self._build_public_session_retry_strategy())
        self.public.mount("https://", adapter)
        self.public.mount("http://", adapter)

    def public_head(self, url: str, follow_redirects: bool = False):
        """
        Issue a ``HEAD`` request through the public session — useful
        for resolving short-link redirects without downloading the
        body (e.g. ``instagram.com/share/...`` link expansion).

        Bypasses :meth:`public_request`'s GET/POST machinery so the
        per-call ``follow_redirects`` flag actually takes effect.

        Parameters
        ----------
        url: str
            Absolute URL.
        follow_redirects: bool, default False
            Whether to follow 3xx responses. Default ``False`` means
            callers can read ``response.headers["location"]`` to
            inspect the redirect target without actually fetching it.

        Returns
        -------
        requests.Response
            The raw response. Status code typically 200 / 301 / 302 /
            307 / 308.
        """
        self.public_requests_count += 1
        return self.public.head(
            url,
            allow_redirects=follow_redirects,
            proxies=self.public.proxies,
            timeout=self.request_timeout,
        )

    def public_request(
        self,
        url,
        data=None,
        params=None,
        headers=None,
        update_headers=None,
        return_json=False,
        retries_count=None,
        retries_timeout=None,
    ):
        kwargs = dict(
            data=data,
            params=params,
            headers=headers,
            return_json=return_json,
        )
        retries_count = (
            self.public_request_retries_count
            if retries_count is None
            else retries_count
        )
        retries_timeout = (
            self.public_request_retries_timeout
            if retries_timeout is None
            else retries_timeout
        )
        assert retries_count <= 10, "Retries count is too high"
        assert retries_timeout <= 600, "Retries timeout is too high"
        for iteration in range(retries_count):
            try:
                if self.delay_range:
                    random_delay(delay_range=self.delay_range)
                return self._send_public_request(
                    url, update_headers=update_headers, **kwargs
                )
            except (
                ClientLoginRequired,
                ClientNotFoundError,
                ClientBadRequestError,
            ) as e:
                raise e  # Stop retries
            # except JSONDecodeError as e:
            #     raise ClientJSONDecodeError(e, respones=self.last_public_response)
            except ClientError as e:
                msg = str(e)
                if all(
                    (
                        isinstance(e, ClientConnectionError),
                        "SOCKSHTTPSConnectionPool" in msg,
                        "Max retries exceeded with url" in msg,
                        "Failed to establish a new connection" in msg,
                    )
                ):
                    raise e
                if retries_count > iteration + 1:
                    time.sleep(retries_timeout)
                else:
                    raise e
                continue

    def _send_public_request(
        self,
        url,
        data=None,
        params=None,
        headers=None,
        return_json=False,
        stream=None,
        timeout=None,
        update_headers=None,
    ):
        self.public_requests_count += 1
        if headers:
            if update_headers in [None, True]:
                self.public.headers.update(headers)
            elif update_headers is False:
                pass
        if self.last_response_ts and (time.time() - self.last_response_ts) < 1.0:
            time.sleep(1.0)
        if self.request_timeout:
            time.sleep(self.request_timeout)
        try:
            if data is not None:  # POST
                response = self.public.post(
                    url,
                    data=data,
                    params=params,
                    proxies=self.public.proxies,
                    timeout=timeout,
                )
            else:  # GET
                response = self.public.get(
                    url,
                    params=params,
                    proxies=self.public.proxies,
                    stream=stream,
                    timeout=timeout,
                )

            if stream:
                return response

            expected_length = int(response.headers.get("Content-Length") or 0)
            actual_length = response.raw.tell()
            if actual_length < expected_length:
                raise ClientIncompleteReadError(
                    "Incomplete read ({} bytes read, {} more expected)".format(
                        actual_length, expected_length
                    ),
                    response=response,
                )

            self.public_request_logger.debug(
                "public_request %s: %s", response.status_code, response.url
            )

            self.public_request_logger.info(
                "[%s] [%s] %s %s",
                self.public.proxies.get("https"),
                response.status_code,
                "POST" if data else "GET",
                response.url,
            )
            self.last_public_response = response
            response.raise_for_status()
            if return_json:
                self.last_public_json = response.json()
                return self.last_public_json
            return response.text

        except JSONDecodeError as e:
            if "/login/" in response.url:
                raise ClientLoginRequired(e, response=response)

            self.public_request_logger.error(
                "Status %s: JSONDecodeError in public_request (url=%s) >>> %s",
                response.status_code,
                response.url,
                response.text,
            )
            raise ClientJSONDecodeError(
                "JSONDecodeError {0!s} while opening {1!s}".format(e, url),
                response=response,
            )
        except requests.HTTPError as e:
            if e.response.status_code == 401:
                # HTTPError: 401 Client Error: Unauthorized for url: https://i.instagram.com/api/v1/users....
                raise ClientUnauthorizedError(e, response=e.response)
            elif e.response.status_code == 403:
                raise ClientForbiddenError(e, response=e.response)
            elif e.response.status_code == 400:
                raise ClientBadRequestError(e, response=e.response)
            elif e.response.status_code == 429:
                raise ClientThrottledError(e, response=e.response)
            elif e.response.status_code == 404:
                raise ClientNotFoundError(e, response=e.response)
            raise ClientError(e, response=e.response)

        except requests.ConnectionError as e:
            raise ClientConnectionError("{} {}".format(e.__class__.__name__, str(e)))
        finally:
            self.last_response_ts = time.time()

    def public_a1_request(self, endpoint, data=None, params=None, headers=None):
        url = (self.PUBLIC_API_URL + str(endpoint)).replace(
            ".com//", ".com/"
        )  # (jarrodnorwell) fixed KeyError: 'data', fixed // error
        params = params or {}
        params.update({"__a": 1, "__d": "dis"})

        response = self.public_request(
            url, data=data, params=params, headers=headers, return_json=True
        )
        return response.get("graphql") or response

    def public_a1_request_user_info_by_username(self, username, data=None, params=None):
        params = params or {}
        url = (
            self.PUBLIC_API_URL + f"api/v1/users/web_profile_info/?username={username}"
        )
        headers = {"x-ig-app-id": "936619743392459"}
        response = self.public_request(
            url, data=data, params=params, headers=headers, return_json=True
        )
        return response.get("user") or response

    def public_graphql_request(
        self,
        variables,
        query_hash=None,
        query_id=None,
        data=None,
        params=None,
        headers=None,
    ):
        assert query_id or query_hash, "Must provide valid one of: query_id, query_hash"
        default_params = {"variables": json.dumps(variables, separators=(",", ":"))}
        if query_id:
            default_params["query_id"] = query_id

        if query_hash:
            default_params["query_hash"] = query_hash

        if params:
            params.update(default_params)
        else:
            params = default_params

        try:
            body_json = self.public_request(
                self.GRAPHQL_PUBLIC_API_URL,
                data=data,
                params=params,
                headers=headers,
                return_json=True,
            )

            if body_json.get("status", None) != "ok":
                raise ClientGraphqlError(
                    "Unexpected status '{}' in response. Message: '{}'".format(
                        body_json.get("status", None), body_json.get("message", None)
                    )
                )

            if "data" not in body_json:
                errors = body_json.get("errors") or []
                summary = errors[0].get("summary") if errors else None
                description = errors[0].get("description") if errors else None
                raise ClientGraphqlError(
                    "Missing 'data' in GraphQL response. Summary: '{}'. Description: '{}'".format(
                        summary, description
                    )
                )

            return body_json["data"]

        except ClientBadRequestError as e:
            message = None
            try:
                body_json = e.response.json()
                message = body_json.get("message", None)
            except JSONDecodeError:
                pass
            raise ClientGraphqlError(
                "Error: '{}'. Message: '{}'".format(e, message), response=e.response
            )


class TopSearchesPublicMixin:
    def top_search(self, query):
        """Anonymous IG search request"""
        url = "https://www.instagram.com/web/search/topsearch/"
        params = {
            "context": "blended",
            "query": query,
            "rank_token": 0.7763938004511706,
            "include_reel": "true",
        }
        response = self.public_request(url, params=params, return_json=True)
        return response


class ProfilePublicMixin:
    def location_feed(self, location_id, count=16, end_cursor=None):
        if count > 50:
            raise ValueError("Count cannot be greater than 50")
        variables = {
            "id": location_id,
            "first": int(count),
        }
        if end_cursor:
            variables["after"] = end_cursor
        data = self.public_graphql_request(
            variables, query_hash="1b84447a4d8b6d6d0426fefb34514485"
        )
        return data["location"]

    def profile_related_info(self, profile_id):
        variables = {
            "user_id": profile_id,
            "include_chaining": True,
            "include_reel": True,
            "include_suggested_users": True,
            "include_logged_out_extras": True,
            "include_highlight_reels": True,
            "include_related_profiles": True,
        }
        data = self.public_graphql_request(
            variables, query_hash="e74d51c10ecc0fe6250a295b9bb9db74"
        )
        return data["user"]
