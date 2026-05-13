import json
import time
from json.decoder import JSONDecodeError
from typing import Dict, Optional

import requests

from instagrapi import config
from instagrapi.exceptions import (
    ClientConnectionError,
    ClientError,
    ClientGraphqlError,
    ClientJSONDecodeError,
)


class PrivateGraphQLRequestMixin:
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
