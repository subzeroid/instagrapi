import json
import logging
import time
from json.decoder import JSONDecodeError
from typing import Dict, Optional

import requests

from instagrapi import config
from instagrapi.exceptions import (
    ChallengeRequired,
    ClientBadRequestError,
    ClientConnectionError,
    ClientError,
    ClientForbiddenError,
    ClientGraphqlError,
    ClientJSONDecodeError,
    ClientLoginRequired,
    ClientNotFoundError,
    ClientThrottledError,
    ClientUnauthorizedError,
    FeedbackRequired,
    LoginRequired,
    PrivateAccount,
    RateLimitError,
    SentryBlock,
    UserNotFound,
)
from instagrapi.utils.logging import truncate_log_text
from instagrapi.utils.timing import random_delay

GRAPHQL_API_URL = "https://www.instagram.com/api/graphql"
PRIVATE_GRAPHQL_QUERY_URL = "https://i.instagram.com/graphql/query"
PRIVATE_GRAPHQL_WWW_DOMAIN = "b.i.instagram.com"

GQL_STUFF = {
    "av": "17841464591314721",
    "__d": "www",
    "__user": "0",
    "__a": "1",
    "__req": "q",
    "__hs": "19768.HYP:instagram_web_pkg.2.1..0.1",
    "dpr": "2",
    "__ccg": "UNKNOWN",
    "__rev": "1011444902",
    "__s": "x82a1q:agr3gd:4nh4nl",
    "__hsi": "7335888108907652597",
    "__dyn": (
        "7xeUjG1mxu1syUbFp40NonwgU7SbzEdF8aUco2qwJxS0k24o0B-"
        "q1ew65xO0FE2awt81s8hwGwQwoEcE7O2l0Fwqo31w9O7U2cxe0E"
        "UjwGzEaE7622362W2K0zK5o4q3y1Sx-0iS2Sq2-azqwt8dUaob8"
        "2cwMwrUdUbGwmk0KU6O1FwlE6PhA6bxy4VUKUnAwHw"
    ),
    "__csr": (
        "g9cj5kxfs8lifTitQDqhdhalmDEAJaKBRJFdkAGHBkPy9HgCA-A"
        "rtucm5bCBBGpyAoz-mLJpXJufKWGQ9hHhAhnKECuFUZ3Q8Jkmmp"
        "eWyGAzkEj_CjyoZUgK-E8bwYzaxy00ktMGx20XU3gw4KAo3MChU"
        "jw3N80poolwiA1d7G2yu2ucxi1nwEw16OE1JsS043Etw63wkSEgg1Mu00yiU"
    ),
    "__comet_req": "7",
    "lsd": "6b2800R9u4biJOYjcdXFEI",
    "__spin_r": "1011444902",
    "__spin_b": "trunk",
    "__spin_t": "1708019550",
    "fb_api_caller_class": "RelayModern",
    "fb_api_req_friendly_name": "PolarisPostCommentsPaginationQuery",
    "server_timestamps": "true",
}


class PrivateGraphQLRequestMixin:
    _fb_dtsg = None
    graphql_requests_count = 0
    last_graphql_response = None
    last_graphql_json = {}
    request_logger = logging.getLogger("graphql_request")

    def __init__(self, *args, **kwargs):
        self.graphql = requests.Session()
        self.graphql.verify = getattr(self, "tls_verify", True)
        self.graphql.headers.update(
            {
                "Connection": "Keep-Alive",
                "Accept": "*/*",
                "Accept-Encoding": "gzip,deflate",
                "Accept-Language": "en-US,en;q=0.9",
                "origin": "https://www.instagram.com",
                "authority": "www.instagram.com",
                "sec-fetch-site": "same-origin",
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/121.0.0.0 Safari/537.36"
                ),
            }
        )
        super().__init__(*args, **kwargs)

    def _merge_incremental_graphql_payload(self, base: Dict, payload: Dict) -> None:
        path = payload.get("path")
        if not isinstance(path, list) or not path or "data" not in payload:
            return
        target = base
        if path and path[0] != "data":
            target = base.get("data", {})
        elif path and path[0] == "data":
            path = path[1:]
        if not path:
            return
        try:
            for key in path[:-1]:
                target = target[key]
        except (KeyError, IndexError, TypeError):
            return
        key = path[-1]
        value = payload["data"]
        if isinstance(target, list):
            if not isinstance(key, int):
                return
            try:
                current = target[key]
            except IndexError:
                return
            if isinstance(current, dict) and isinstance(value, dict):
                current.update(value)
            else:
                target[key] = value
            return
        current = target.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            current.update(value)
        else:
            target[key] = value

    @property
    def fb_dtsg(self):
        if not self._fb_dtsg:
            self._fb_dtsg = self.fetch_fb_dtsg()
        return self._fb_dtsg

    def fetch_fb_dtsg(self):
        self.inject_sessionid_to_public()
        response = self.graphql.get(GRAPHQL_API_URL, proxies=self.graphql.proxies)
        html = response.content.decode() if response.content else ""
        if html:
            s = html.find("__eqmc")
            e = s + 1000
            eqmc = html[s:e]
            s, e = eqmc.find("{"), eqmc.find("</script>")
            eqmc = eqmc[s:e]
            if eqmc:
                return json.loads(eqmc)["f"]
        return None

    def _json_from_graphql_response(self, response):
        try:
            return response.json()
        except JSONDecodeError:
            chunks = [json.loads(line) for line in response.text.splitlines() if line.strip()]
            if not chunks:
                raise
            body = chunks[0]
            for chunk in chunks[1:]:
                self._merge_incremental_graphql_payload(body, chunk)
            return body

    def graphql_request(
        self,
        data=None,
        params=None,
        headers=None,
        return_json=True,
        retries_count=1,
        retries_timeout=2,
    ):
        kwargs = dict(data=data, params=params, headers=headers, return_json=return_json)
        assert retries_count <= 10, "Retries count is too high"
        assert retries_timeout <= 600, "Retries timeout is too high"
        self.inject_sessionid_to_public()
        for iteration in range(retries_count):
            try:
                if self.delay_range:
                    random_delay(delay_range=self.delay_range)
                return self._send_graphql_request(**kwargs)
            except (
                ClientLoginRequired,
                ClientNotFoundError,
                ClientBadRequestError,
            ) as e:
                raise e
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

    def _send_graphql_request(self, data=None, params=None, headers=None, return_json=False):
        self.last_graphql_response = None
        self.graphql_requests_count += 1
        if headers:
            self.graphql.headers.update(headers)
        if self.last_response_ts and (time.time() - self.last_response_ts) < 1.0:
            time.sleep(1.0)
        try:
            if data is not None:
                response = self.graphql.post(
                    GRAPHQL_API_URL,
                    data=data,
                    params=params,
                    proxies=self.graphql.proxies,
                )
            else:
                response = self.graphql.get(
                    GRAPHQL_API_URL,
                    params=params,
                    proxies=self.graphql.proxies,
                )
            self.request_logger.debug("graphql_request %s: %s", response.status_code, response.url)
            self.request_logger.info(
                "GraphQL: [%s] [%s] %s %s",
                self.graphql.proxies.get("https"),
                response.status_code,
                "POST" if data else "GET",
                response.url,
            )
            self.last_graphql_response = response
            response.raise_for_status()
            if return_json:
                self.last_graphql_json = response.json()
                return self.last_graphql_json
            return response.text
        except JSONDecodeError as e:
            url = str(response.url)
            if "/login/" in url:
                raise ClientLoginRequired(e, response=response)
            self.request_logger.error(
                "Status %s: JSONDecodeError in graphql_request (url=%s) >>> %s",
                response.status_code,
                url,
                truncate_log_text(response.text),
            )
            raise ClientJSONDecodeError(
                "JSONDecodeError {0!s} while opening {1!s}".format(e, url),
                response=response,
            )
        except requests.HTTPError as e:
            status_code = getattr(self.last_graphql_response, "status_code", None)
            if status_code == 401:
                exc = ClientUnauthorizedError
            elif status_code == 403:
                exc = ClientForbiddenError
            elif status_code == 400:
                exc = ClientBadRequestError
            elif status_code == 429:
                exc = ClientThrottledError
            elif status_code == 404:
                exc = ClientNotFoundError
            else:
                exc = ClientError
            raise exc(e, response=self.last_graphql_response)
        except requests.ConnectionError as e:
            raise ClientConnectionError("{} {}".format(e.__class__.__name__, str(e)))
        finally:
            self.last_response_ts = time.time()

    def private_graphql_request(self, data: Dict, headers: Optional[Dict] = None, domain: Optional[str] = None) -> Dict:
        self.last_response = None
        self.last_json = {}
        response = None
        self.private.headers.update(self.base_headers)
        self.private.headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
        if self.authorization:
            self.private.headers["Authorization"] = self.authorization
        friendly_name = data.get("fb_api_req_friendly_name")
        if friendly_name:
            self.private.headers["X-FB-Friendly-Name"] = friendly_name
        if headers:
            self.private.headers.update(headers)
        if self.request_timeout:
            time.sleep(self.request_timeout)
        url = f"https://{domain or config.API_DOMAIN}/graphql/query"
        try:
            self.private_requests_count += 1
            response = self.private.post(url, data=data, proxies=self.private.proxies)
            self.request_log(response)
            self.last_response = response
            response.raise_for_status()
            self.last_json = self._json_from_graphql_response(response)
        except JSONDecodeError as exc:
            url = response.url if response else url
            raise ClientJSONDecodeError(
                "JSONDecodeError {0!s} while opening {1!s}".format(exc, url),
                response=response,
            )
        except requests.HTTPError as exc:
            raise ClientError(exc, response=exc.response)
        except requests.ConnectionError as exc:
            raise ClientConnectionError("{} {}".format(exc.__class__.__name__, str(exc)))
        if self.last_json.get("errors"):
            raise ClientGraphqlError(self.last_json.get("errors"))
        if self.last_json.get("status") == "fail":
            raise ClientError(response=response, **self.last_json)
        return self.last_json

    def private_graphql_www_request(
        self,
        friendly_name: str,
        variables: Optional[Dict] = None,
        client_doc_id: Optional[str] = None,
        domain: str = PRIVATE_GRAPHQL_WWW_DOMAIN,
        extra_headers: Optional[Dict] = None,
    ) -> Dict:
        data = {
            "method": "post",
            "pretty": "false",
            "format": "json",
            "server_timestamps": "true",
            "locale": "user",
            "purpose": "fetch",
            "fb_api_req_friendly_name": friendly_name,
            "enable_canonical_naming": "true",
            "enable_canonical_variable_overrides": "true",
            "enable_canonical_naming_ambiguous_type_prefixing": "true",
            "variables": json.dumps(variables or {}, separators=(",", ":")),
        }
        if client_doc_id:
            data["client_doc_id"] = str(client_doc_id)
        headers = {
            "X-FB-Friendly-Name": friendly_name,
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }
        if client_doc_id:
            headers["X-Client-Doc-Id"] = str(client_doc_id)
        if extra_headers:
            headers.update(extra_headers)
        merged = dict(self.base_headers)
        merged.update(headers)
        merged["Host"] = domain
        if self.authorization:
            merged.setdefault("Authorization", self.authorization)
        if self.request_timeout:
            time.sleep(self.request_timeout)
        url = f"https://{domain}/graphql_www"
        response = None
        try:
            self.private_requests_count += 1
            response = self.private.post(url, data=data, headers=merged, proxies=self.private.proxies)
            self.request_log(response)
            self.last_response = response
            response.raise_for_status()
            self.last_json = self._json_from_graphql_response(response)
        except JSONDecodeError as exc:
            url = response.url if response else url
            raise ClientJSONDecodeError(
                "JSONDecodeError {0!s} while opening {1!s}".format(exc, url),
                response=response,
            )
        except requests.HTTPError as exc:
            raise ClientError(exc, response=exc.response)
        except requests.ConnectionError as exc:
            raise ClientConnectionError("{} {}".format(exc.__class__.__name__, str(exc)))
        if self.last_json.get("errors"):
            raise ClientGraphqlError(self.last_json.get("errors"))
        if self.last_json.get("status") == "fail":
            raise ClientError(response=response, **self.last_json)
        return self.last_json

    def private_graphql_query_request(
        self,
        friendly_name: str,
        root_field_name: str,
        variables: dict = None,
        client_doc_id: str = None,
        priority: str = None,
        extra_headers: dict = None,
    ) -> dict:
        data = {
            "method": "post",
            "pretty": "false",
            "format": "json",
            "server_timestamps": "true",
            "locale": "user",
            "fb_api_req_friendly_name": friendly_name,
            "enable_canonical_naming": "true",
            "enable_canonical_variable_overrides": "true",
            "enable_canonical_naming_ambiguous_type_prefixing": "true",
            "variables": json.dumps(variables or {}, separators=(",", ":")),
        }
        if client_doc_id:
            data["client_doc_id"] = client_doc_id
        headers = {
            "X-FB-Friendly-Name": friendly_name,
            "X-Root-Field-Name": root_field_name,
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }
        if client_doc_id:
            headers["X-Client-Doc-Id"] = str(client_doc_id)
        if priority:
            headers["Priority"] = priority
        if extra_headers:
            headers.update(extra_headers)
        merged = dict(self.base_headers)
        merged.update(headers)
        if self.authorization:
            merged.setdefault("Authorization", self.authorization)
        self.last_json = {}
        response = self.private.post(
            PRIVATE_GRAPHQL_QUERY_URL,
            data=data,
            headers=merged,
            proxies=self.private.proxies,
        )
        self.last_response = response
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            try:
                body_json = response.json()
                if isinstance(body_json, dict):
                    self.last_json = body_json
                    last_json = body_json
                else:
                    last_json = {}
            except Exception:
                last_json = {}
            message = ""
            error_type = None
            if isinstance(last_json, dict):
                message = (last_json.get("message") or "").lower()
                error_type = last_json.get("error_type")
            if message == "login_required":
                raise LoginRequired(e, response=response, **last_json)
            if message == "challenge_required":
                raise ChallengeRequired(**last_json)
            if message == "feedback_required":
                raise FeedbackRequired(e, response=response, **last_json)
            if error_type == "rate_limit_error":
                raise RateLimitError(e, response=response, **last_json)
            if message == "user_blocked":
                raise SentryBlock(e, response=response, **last_json)
            if "not authorized to view user" in message:
                raise PrivateAccount(e, response=response, **last_json)
            if "unable to fetch followers" in message or "error generating user info response" in message:
                raise UserNotFound(e, response=response, **last_json)
            if getattr(response, "status_code", None) == 404 and getattr(response, "content", None) == b"Not Found":
                raise ChallengeRequired(**last_json)
            status_code = getattr(response, "status_code", None)
            if status_code == 400:
                exc = ClientBadRequestError
            elif status_code == 401:
                exc = ClientUnauthorizedError
            elif status_code == 403:
                exc = ClientForbiddenError
            elif status_code == 404:
                exc = ClientNotFoundError
            elif status_code == 429:
                exc = ClientThrottledError
            else:
                exc = ClientError
            raise exc(e, response=response, **last_json)
        try:
            body = response.json()
        except JSONDecodeError:
            text = response.text.strip()
            rows = [json.loads(item if item.endswith('"}') else f'{item}"}}') for item in text.split('"}\n') if item]
            body = {"stream_rows": rows}
        self.last_json = body
        return body

    def private_graphql_memories_pog(
        self,
        client_doc_id: str = "4160563056814166588457451196",
        direct_region_hint: str = None,
    ) -> dict:
        extra_headers = None
        if direct_region_hint:
            extra_headers = {"ig-u-ig-direct-region-hint": direct_region_hint}
        return self.private_graphql_query_request(
            friendly_name="MemoriesPogQuery",
            root_field_name="xdt_get_story_memories_pog",
            variables={"request": {"user_id": 0}},
            client_doc_id=client_doc_id,
            extra_headers=extra_headers,
        )

    def private_graphql_realtime_region_hint(
        self,
        client_doc_id: str = "52232106018313849661757113193",
    ) -> dict:
        return self.private_graphql_query_request(
            friendly_name="IGRealtimeRegionHintQuery",
            root_field_name="xdt_igd_msg_region",
            variables={},
            client_doc_id=client_doc_id,
            priority="u=3, i",
        )

    def private_graphql_top_audio_trends_eligible_categories(
        self,
        client_doc_id: str = "10243243298540497152200027985",
    ) -> dict:
        return self.private_graphql_query_request(
            friendly_name="GetTopAudioTrendsEligibleCategories",
            root_field_name="xdt_top_audio_trends_eligible_tabs",
            variables={},
            client_doc_id=client_doc_id,
        )

    def private_graphql_update_inbox_tray_last_seen(
        self,
        client_doc_id: str = "41048505499858972910914091441",
    ) -> dict:
        return self.private_graphql_query_request(
            friendly_name="UpdateInboxTrayLastSeenTimestamp",
            root_field_name="__typename",
            variables={},
            client_doc_id=client_doc_id,
        )
