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
    def private_graphql_request(
        self, data: Dict, headers: Optional[Dict] = None, domain: Optional[str] = None
    ) -> Dict:
        self.last_response = None
        self.last_json = {}
        response = None
        self.private.headers.update(self.base_headers)
        self.private.headers["Content-Type"] = (
            "application/x-www-form-urlencoded; charset=UTF-8"
        )
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
            self.last_json = response.json()
        except JSONDecodeError as exc:
            url = response.url if response else url
            raise ClientJSONDecodeError(
                "JSONDecodeError {0!s} while opening {1!s}".format(exc, url),
                response=response,
            )
        except requests.HTTPError as exc:
            raise ClientError(exc, response=exc.response)
        except requests.ConnectionError as exc:
            raise ClientConnectionError(
                "{} {}".format(exc.__class__.__name__, str(exc))
            )
        if self.last_json.get("errors"):
            raise ClientGraphqlError(self.last_json.get("errors"))
        if self.last_json.get("status") == "fail":
            raise ClientError(response=response, **self.last_json)
        return self.last_json
