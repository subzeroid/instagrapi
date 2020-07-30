import time
import json
import random
import logging
import hashlib
import requests
from json.decoder import JSONDecodeError

from . import config
from .utils import generate_signature
from .exceptions import (
    ClientError,
    ClientConnectionError,
    ClientNotFoundError,
    ClientJSONDecodeError,
    ClientForbiddenError,
    ClientBadRequestError,
    ClientThrottledError,
    ClientRequestTimeout,
    FeedbackRequired,
    ChallengeRequired,
    LoginRequired,
    SentryBlock,
    RateLimitError,
    BadPassword,
    UnknownError,
)


def manual_input_code(self, username, choice=None):
    code = None
    while True:
        code = input("Enter code (6 digits) for %s: " % username).strip()
        if code and code.isdigit():
            break
    return code  # is not int, because it can start from 0


class PrivateRequest:
    handle_exception = None
    challenge_code_handler = manual_input_code
    request_logger = logging.getLogger("private_request")
    request_timeout = 3
    last_response = None
    last_json = {}

    def __init__(self, *args, **kwargs):
        self.private = requests.Session()
        self.email = kwargs.pop("email", None)
        self.phone_number = kwargs.pop("phone_number", None)
        self.request_timeout = kwargs.pop("request_timeout", self.request_timeout)
        super().__init__(*args, **kwargs)

    def small_delay(self):
        time.sleep(random.uniform(0.75, 3.75))

    def very_small_delay(self):
        time.sleep(random.uniform(0.175, 0.875))

    @property
    def base_headers(self):
        """
        Example:
            X-IG-App-Locale	en_US
            X-IG-Device-Locale	en_US
            X-IG-Mapped-Locale	en_US
            X-Pigeon-Session-Id	ec6a2145-3b81-4c88-9b81-6285f0370a3b
            X-Pigeon-Rawclienttime	1586192562.151
            X-IG-Connection-Speed	-1kbps
            X-IG-Bandwidth-Speed-KBPS	2934.670
            X-IG-Bandwidth-TotalBytes-B	53417556
            X-IG-Bandwidth-TotalTime-MS	15113
            X-IG-EU-DC-ENABLED	true
            X-IG-App-Startup-Country	US
            X-Bloks-Version-Id	9963ab1f03b66a2392845416b379bf71e0613103e91d03dabfc2a8b6ccd0f990
            X-Bloks-Is-Layout-RTL	false
            X-IG-Device-ID	c642fece-8663-40d8-8ab7-112df0179e65
            X-IG-Android-ID	android-7d8ad96cc1b71922
            X-IG-Connection-Type	WIFI
            X-IG-Capabilities	3brTvwM=
            X-IG-App-ID	1217981644879628
            User-Agent	Instagram 134.0.0.26.121 Android (26/8.0.0; 480dpi; 1080x1920; Xiaomi; MI 5s; capricorn; qcom; en_US; 205280538)
            Accept-Language	en-US
            Cookie	urlgen={\"91.108.28.92\": 42065}:1jLV8b:MS5-AItdzNM_pp5oR_AidcAVaNQ; ig_direct_region_hint=FRC; ds_user=dhbastards; igfl=dhbastards; ds_user_id=8530598273; mid=XotDHQABAAFsb6GIlQ_RJCSwAaBN; shbts=1586192141.118131; sessionid=8530598273%3AMwtjHRDT0bKJsS%3A4; csrftoken=H8Rk6Ry2ffWcUSwWIBblVK4hHHII2RMk; shbid=3713; rur=VLL; is_starred_enabled=yes
            Authorization	Bearer IGT:2:eyJkc191c2VyX2lkIjoiODUzMDU5ODI3MyIsInNlc3Npb25pZCI6Ijg1MzA1OTgyNzMlM0FNd3RqSFJEVDBiS0pzUyUzQTQifQ==
            X-MID	XotDHQABAAFsb6GIlQ_RJCSwAaBN
            Content-Type	application/x-www-form-urlencoded; charset=UTF-8
            Accept-Encoding	gzip, deflate
            Host	i.instagram.com
            X-FB-HTTP-Engine	Liger
            Connection	keep-alive
            Content-Length	553
            Pragma	no-cache
            Cache-Control	no-cache
            """
        return {
            "X-IG-App-Locale": "en_US",
            "X-IG-Device-Locale": "en_US",
            "X-IG-Mapped-Locale": "en_US",
            "X-Pigeon-Session-Id": self.generate_uuid(),
            "X-Pigeon-Rawclienttime": str(round(time.time() * 1000) / 1000),
            "X-IG-Connection-Speed": "-1kbps",
            "X-IG-Bandwidth-Speed-KBPS": str(random.randint(2900000, 10000000) / 1000),
            "X-IG-Bandwidth-TotalBytes-B": str(random.randint(5000000, 90000000)),
            "X-IG-Bandwidth-TotalTime-MS": str(random.randint(5000, 15000)),
            # "X-IG-EU-DC-ENABLED": "true", # <- type of DC? Eu is euro, but we use US
            # "X-IG-Prefetch-Request": "foreground",  # OLD from instabot
            "X-Bloks-Version-Id": hashlib.sha256(
                json.dumps(self.device_settings).encode()
            ).hexdigest(),
            "X-Bloks-Is-Layout-RTL": "false",
            # "X-Bloks-Enable-RenderCore": "false",  # OLD from instabot
            # "X-IG-WWW-Claim": "0",  # OLD from instabot
            "X-MID": self.mid,  # "XkAyKQABAAHizpYQvHzNeBo4E9nm" in instabot
            "X-IG-Device-ID": self.uuid,
            "X-IG-Android-ID": self.device_id,
            "X-IG-Connection-Type": "WIFI",
            "X-IG-Capabilities": "3brTvwM=",  # "3brTvwE=" in instabot
            "X-IG-App-ID": "567067343352427",
            "X-IG-App-Startup-Country": "US",
            "User-Agent": self.user_agent,
            "Accept-Language": "en-US",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Accept-Encoding": "gzip, deflate",
            "Host": "i.instagram.com",
            "X-FB-HTTP-Engine": "Liger",
            "Connection": "keep-alive",  # "close" in instabot
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
        }

    @staticmethod
    def with_query_params(data, params):
        return dict(data, **{"query_params": json.dumps(params, separators=(",", ":"))})

    def _send_private_request(
        self,
        endpoint,
        data=None,
        params=None,
        login=False,
        with_signature=True,
        headers=None,
        extra_sig=None,
    ):
        self.last_response = None
        self.last_json = last_json = {}  # for Sentry context in traceback
        self.private.headers.update(self.base_headers)
        if endpoint.startswith("/"):
            endpoint = endpoint[1:]
        if headers:
            self.private.headers.update(headers)
        if not login:
            time.sleep(self.request_timeout)
        if self.user_id and login:
            raise Exception("User already login")
        try:
            if data:  # POST
                data = json.dumps(data)
                if with_signature:
                    # Only `send_direct_item` doesn't need a signature
                    data = generate_signature(data)
                    if extra_sig:
                        data += "&".join(extra_sig)
                response = self.private.post(
                    config.API_URL + endpoint, data=data, params=params
                )
            else:  # GET
                response = self.private.get(config.API_URL + endpoint, params=params)
            self.logger.debug(
                "private_request %s: %s (%s)", response.status_code, response.url, response.text
            )
            self.request_log(response)
            self.last_response = response
            response.raise_for_status()
            # last_json - for Sentry context in traceback
            self.last_json = last_json = response.json()
            self.logger.debug("last_json %s", last_json)
        except JSONDecodeError as e:
            self.logger.error(
                "Status %s: JSONDecodeError in private_request (user_id=%s, endpoint=%s) >>> %s",
                response.status_code,
                self.user_id,
                endpoint,
                response.text,
            )
            raise ClientJSONDecodeError(
                "JSONDecodeError {0!s} while opening {1!s}".format(e, response.url),
                response=response,
            )
        except requests.HTTPError as e:
            try:
                self.last_json = last_json = response.json()
            except JSONDecodeError:
                pass
            message = last_json.get("message")
            if e.response.status_code == 403:
                if message == "login_required":
                    raise LoginRequired(response=e.response, **last_json)
                raise ClientForbiddenError(e, response=e.response, **last_json)
            elif e.response.status_code == 400:
                error_type = last_json.get("error_type")
                if message == "challenge_required":
                    raise ChallengeRequired(**last_json)
                elif message == "feedback_required":
                    raise FeedbackRequired(
                        **dict(
                            last_json,
                            message="%s: %s"
                            % (message, last_json.get("feedback_message")),
                        )
                    )
                elif error_type == "sentry_block":
                    raise SentryBlock(**last_json)
                elif error_type == "rate_limit_error":
                    raise RateLimitError(**last_json)
                elif error_type == "bad_password":
                    raise BadPassword(**last_json)
                elif error_type or message:
                    raise UnknownError(**last_json)
                # TODO: Handle last_json with {'message': 'counter get error', 'status': 'fail'}
                self.logger.exception(e)
                self.logger.warning(
                    "Status 400: %s", message or "Maybe Two-factor auth?"
                )
                raise ClientBadRequestError(e, response=e.response, **last_json)
            elif e.response.status_code == 429:
                self.logger.warning("Status 429: Too many requests")
                # TODO: {'message': 'Please wait a few minutes before you try again.', 'status': 'fail'}
                raise ClientThrottledError(e, response=e.response, **last_json)
            elif e.response.status_code == 404:
                self.logger.warning("Status 404: Endpoint %s does not exists", endpoint)
                raise ClientNotFoundError(e, response=e.response, **last_json)
            elif e.response.status_code == 408:
                self.logger.warning("Status 408: Request Timeout")
                raise ClientRequestTimeout(e, response=e.response, **last_json)
            raise ClientError(e, response=e.response, **last_json)
        except requests.ConnectionError as e:
            raise ClientConnectionError("{e.__class__.__name__} {e}".format(e=e))
        if last_json.get("status") == "fail":
            raise ClientError(response=response, **last_json)
        elif "error_title" in last_json:
            """Example: {
            'error_title': 'bad image input extra:{}', <-------------
            'media': {
                'device_timestamp': '1588184737203',
                'upload_id': '1588184737203'
            },
            'message': 'media_needs_reupload', <-------------
            'status': 'ok' <-------------
            }"""
            raise ClientError(response=response, **last_json)
        return last_json

    def request_log(self, response):
        self.request_logger.info(
            "%s [%s] %s %s (%s)",
            self.username,
            response.status_code,
            response.request.method,
            response.url,
            "{app_version}, {manufacturer} {model}".format(**self.device_settings),
        )

    def private_request(
        self,
        endpoint,
        data=None,
        params=None,
        login=False,
        with_signature=True,
        headers=None,
        extra_sig=None,
    ):
        kwargs = dict(
            data=data,
            params=params,
            login=login,
            with_signature=with_signature,
            headers=headers,
            extra_sig=extra_sig,
        )
        try:
            self._send_private_request(endpoint, **kwargs)
        except ClientRequestTimeout:
            print('Wait 60 seconds and try one more time (ClientRequestTimeout)')
            time.sleep(60)
            return self._send_private_request(endpoint, **kwargs)
        except Exception as e:
            if self.handle_exception:
                self.handle_exception(self, e)
            elif isinstance(e, ChallengeRequired):
                self.challenge_resolve(self.last_json)
            if login:
                return self.last_json
            return self._send_private_request(endpoint, **kwargs)

        return self.last_json

    def build_location(self, name, lat, lng, address=""):
        return json.dumps({
            "name": name,
            "address": address,
            "lat": lat,
            "lng": lng,
            # "external_source": "facebook_places",
            # "facebook_places_id" : "111123468912781"
        }, separators=(",", ":"))
