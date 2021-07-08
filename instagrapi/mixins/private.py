import hashlib
import json
import logging
import random
import time
from json.decoder import JSONDecodeError

import requests

from instagrapi import config
from instagrapi.exceptions import (
    BadPassword,
    ChallengeRequired,
    ClientBadRequestError,
    ClientConnectionError,
    ClientError,
    ClientForbiddenError,
    ClientJSONDecodeError,
    ClientNotFoundError,
    ClientRequestTimeout,
    ClientThrottledError,
    FeedbackRequired,
    LoginRequired,
    PleaseWaitFewMinutes,
    RateLimitError,
    SentryBlock,
    TwoFactorRequired,
    UnknownError,
    VideoTooLongException,
)
from instagrapi.utils import dumps, generate_signature


def manual_input_code(self, username: str, choice=None):
    """
    Manual security code helper

    Parameters
    ----------
    username: str
        User name of a Instagram account
    choice: optional
        Whether sms or email

    Returns
    -------
    str
        Code
    """
    code = None
    choice_name = {0: 'sms', 1: 'email'}.get(choice)
    while True:
        code = input(f"Enter code (6 digits) for {username} ({choice_name}): ").strip()
        if code and code.isdigit():
            break
    return code  # is not int, because it can start from 0


class PrivateRequestMixin:
    """
    Helpers for private request
    """
    private_requests_count = 0
    handle_exception = None
    challenge_code_handler = manual_input_code
    request_logger = logging.getLogger("private_request")
    request_timeout = 1
    last_response = None
    last_json = {}

    def __init__(self, *args, **kwargs):
        self.private = requests.Session()
        self.email = kwargs.pop("email", None)
        self.phone_number = kwargs.pop("phone_number", None)
        self.request_timeout = kwargs.pop(
            "request_timeout", self.request_timeout)
        super().__init__(*args, **kwargs)

    def small_delay(self):
        """
        Small Delay

        Returns
        -------
        Void
        """
        time.sleep(random.uniform(0.75, 3.75))

    def very_small_delay(self):
        """
        Very small delay

        Returns
        -------
        Void
        """
        time.sleep(random.uniform(0.175, 0.875))

    @property
    def base_headers(self):
        locale = self.locale.replace("-", "_")
        return {
            "X-IG-App-Locale": locale,
            "X-IG-Device-Locale": locale,
            "X-IG-Mapped-Locale": locale,
            "X-Pigeon-Session-Id": self.generate_uuid(),
            "X-Pigeon-Rawclienttime": str(round(time.time() * 1000) / 1000),
            "X-IG-Connection-Speed": "-1kbps",
            "X-IG-Bandwidth-Speed-KBPS": "-1.000",  # str(random.randint(2900000, 10000000) / 1000),
            "X-IG-Bandwidth-TotalBytes-B": "0",  # str(random.randint(5000000, 90000000)),
            "X-IG-Bandwidth-TotalTime-MS": "0",  # str(random.randint(5000, 15000)),
            # "X-IG-EU-DC-ENABLED": "true", # <- type of DC? Eu is euro, but we use US
            # "X-IG-Prefetch-Request": "foreground",  # OLD from instabot
            "X-IG-App-Startup-Country": self.country.upper(),
            "X-Bloks-Version-Id": hashlib.sha256(
                json.dumps(self.device_settings).encode()
            ).hexdigest(),
            "X-IG-WWW-Claim": "0",
            "X-Bloks-Is-Layout-RTL": "false",
            # "X-Bloks-Enable-RenderCore": "false",  # OLD from instabot
            "X-MID": self.mid,  # "XkAyKQABAAHizpYQvHzNeBo4E9nm" in instabot
            "X-Bloks-Is-Panorama-Enabled": "true",
            "X-IG-Device-ID": self.uuid,
            "X-IG-Android-ID": self.device_id,
            "X-IG-Connection-Type": "WIFI",
            "X-IG-Capabilities": "3brTvwM=",  # "3brTvwE=" in instabot
            "X-IG-App-ID": "567067343352427",
            "User-Agent": self.user_agent,
            "Accept-Language": locale.replace("_", "-"),
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Accept-Encoding": "gzip, deflate",
            # "Host": "i.instagram.com",
            "X-FB-HTTP-Engine": "Liger",
            "Connection": "keep-alive",  # "close" in instabot
            # "Pragma": "no-cache",
            # "Cache-Control": "no-cache",
            "X-FB-Client-IP": "True",
        }

    def set_country(self, country: str = "US"):
        """Set you country code (ISO 3166-1/3166-2)

        Parameters
        ----------
        country: str
            Your country code (ISO 3166-1/3166-2) string identifier (e.g. US, UK, RU)
            Advise to specify the country code of your proxy

        Returns
        -------
        bool
            A boolean value
        """
        self.country = country
        return True

    def set_locale(self, locale: str = "en_US"):
        """Set you locale (ISO 3166-1/3166-2)

        Parameters
        ----------
        locale: str
            Your locale code (ISO 3166-1/3166-2) string identifier (e.g. US, UK, RU)
            Advise to specify the locale code of your proxy

        Returns
        -------
        bool
            A boolean value
        """
        self.locale = locale
        return True

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
        if headers:
            self.private.headers.update(headers)
        if not login:
            time.sleep(self.request_timeout)
        if self.user_id and login:
            raise Exception(f"User already login ({self.user_id})")
        try:
            if not endpoint.startswith('/'):
                endpoint = f"/v1/{endpoint}"
            api_url = f"https://{config.API_DOMAIN}/api{endpoint}"
            if data:  # POST
                # Client.direct_answer raw dict
                # data = json.dumps(data)
                if with_signature:
                    # Client.direct_answer doesn't need a signature
                    data = generate_signature(dumps(data))
                    if extra_sig:
                        data += "&".join(extra_sig)
                response = self.private.post(
                    api_url, data=data, params=params
                )
            else:  # GET
                response = self.private.get(api_url, params=params)
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
                "JSONDecodeError {0!s} while opening {1!s}".format(
                    e, response.url),
                response=response,
            )
        except requests.HTTPError as e:
            try:
                self.last_json = last_json = response.json()
            except JSONDecodeError:
                pass
            message = last_json.get("message", "")
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
                elif error_type == "two_factor_required":
                    if not last_json['message']:
                        last_json['message'] = "Two-factor authentication required"
                    raise TwoFactorRequired(**last_json)
                elif "Please wait a few minutes before you try again" in message:
                    raise PleaseWaitFewMinutes(e, response=e.response, **last_json)
                elif "VideoTooLongException" in message:
                    raise VideoTooLongException(e, response=e.response, **last_json)
                elif error_type or message:
                    raise UnknownError(**last_json)
                # TODO: Handle last_json with {'message': 'counter get error', 'status': 'fail'}
                self.logger.exception(e)
                self.logger.warning(
                    "Status 400: %s", message or "Empty response message. Maybe enabled Two-factor auth?"
                )
                raise ClientBadRequestError(
                    e, response=e.response, **last_json)
            elif e.response.status_code == 429:
                self.logger.warning("Status 429: Too many requests")
                if "Please wait a few minutes before you try again" in message:
                    raise PleaseWaitFewMinutes(e, response=e.response, **last_json)
                raise ClientThrottledError(e, response=e.response, **last_json)
            elif e.response.status_code == 404:
                self.logger.warning(
                    "Status 404: Endpoint %s does not exists", endpoint)
                raise ClientNotFoundError(e, response=e.response, **last_json)
            elif e.response.status_code == 408:
                self.logger.warning("Status 408: Request Timeout")
                raise ClientRequestTimeout(e, response=e.response, **last_json)
            raise ClientError(e, response=e.response, **last_json)
        except requests.ConnectionError as e:
            raise ClientConnectionError(
                "{e.__class__.__name__} {e}".format(e=e))
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
            "{app_version}, {manufacturer} {model}".format(
                **self.device_settings),
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
        if self.authorization:
            if not headers:
                headers = {}
            if 'authorization' not in headers:
                headers.update({'Authorization': self.authorization})
        kwargs = dict(
            data=data,
            params=params,
            login=login,
            with_signature=with_signature,
            headers=headers,
            extra_sig=extra_sig,
        )
        try:
            self.private_requests_count += 1
            self._send_private_request(endpoint, **kwargs)
        except ClientRequestTimeout:
            print('Wait 60 seconds and try one more time (ClientRequestTimeout)')
            time.sleep(60)
            return self._send_private_request(endpoint, **kwargs)
        # except BadPassword as e:
        #     raise e
        except Exception as e:
            if self.handle_exception:
                self.handle_exception(self, e)
            elif isinstance(e, ChallengeRequired):
                self.challenge_resolve(self.last_json)
            else:
                raise e
            if login and self.user_id:
                # After challenge resolve return last_json
                return self.last_json
            return self._send_private_request(endpoint, **kwargs)
        return self.last_json
