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
from instagrapi.utils import dumps, generate_signature, random_delay


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
    while True:
        code = input(f"Enter code (6 digits) for {username} ({choice}): ").strip()
        if code and code.isdigit():
            break
    return code  # is not int, because it can start from 0


def manual_change_password(self, username: str):
    pwd = None
    while not pwd:
        pwd = input(f"Enter password for {username}: ").strip()
    return pwd


class PrivateRequestMixin:
    """
    Helpers for private request
    """
    private_requests_count = 0
    handle_exception = None
    challenge_code_handler = manual_input_code
    change_password_handler = manual_change_password
    request_logger = logging.getLogger("private_request")
    request_timeout = 1
    last_response = None
    last_json = {}

    def __init__(self, *args, **kwargs):
        self.private = requests.Session()
        self.private.verify = False  # fix SSLError/HTTPSConnectionPool
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
        accept_language = ['en-US']
        if locale:
            lang = locale.replace("_", "-")
            if lang not in accept_language:
                accept_language.insert(0, lang)
        headers = {
            "X-IG-App-Locale": locale,
            "X-IG-Device-Locale": locale,
            "X-IG-Mapped-Locale": locale,
            "X-Pigeon-Session-Id": self.generate_uuid('UFS-', '-1'),
            "X-Pigeon-Rawclienttime": str(round(time.time(), 3)),
            # "X-IG-Connection-Speed": "-1kbps",
            "X-IG-Bandwidth-Speed-KBPS": str(random.randint(2500000, 3000000) / 1000),  # "-1.000"
            "X-IG-Bandwidth-TotalBytes-B": str(random.randint(5000000, 90000000)),  # "0"
            "X-IG-Bandwidth-TotalTime-MS": str(random.randint(2000, 9000)),  # "0"
            # "X-IG-EU-DC-ENABLED": "true", # <- type of DC? Eu is euro, but we use US
            # "X-IG-Prefetch-Request": "foreground",  # OLD from instabot
            "X-IG-App-Startup-Country": self.country.upper(),
            "X-Bloks-Version-Id": self.bloks_versioning_id,
            "X-IG-WWW-Claim": "0",
            # X-IG-WWW-Claim: hmac.AR3zruvyGTlwHvVd2ACpGCWLluOppXX4NAVDV-iYslo9CaDd
            "X-Bloks-Is-Layout-RTL": "false",
            "X-Bloks-Is-Panorama-Enabled": "true",
            "X-IG-Device-ID": self.uuid,
            "X-IG-Family-Device-ID": self.phone_id,
            "X-IG-Android-ID": self.android_device_id,
            "X-IG-Timezone-Offset": str(self.timezone_offset),
            "X-IG-Connection-Type": "WIFI",
            "X-IG-Capabilities": "3brTvx0=",  # "3brTvwE=" in instabot
            "X-IG-App-ID": self.app_id,
            "Priority": "u=3",
            "User-Agent": self.user_agent,
            "Accept-Language": ', '.join(accept_language),
            "X-MID": self.mid,  # e.g. X--ijgABABFjLLQ1NTEe0A6JSN7o, YRwa1QABBAF-ZA-1tPmnd0bEniTe
            "Accept-Encoding": "gzip, deflate",  # ignore zstd
            "Host": config.API_DOMAIN,
            "X-FB-HTTP-Engine": "Liger",
            "Connection": "keep-alive",
            # "Pragma": "no-cache",
            # "Cache-Control": "no-cache",
            "X-FB-Client-IP": "True",
            "X-FB-Server-Cluster": "True",
            "IG-INTENDED-USER-ID": str(self.user_id or 0),
            "X-IG-Nav-Chain": "9MV:self_profile:2,ProfileMediaTabFragment:self_profile:3,9Xf:self_following:4",
            "X-IG-SALT-IDS": str(random.randint(1061162222, 1061262222)),
        }
        if self.user_id:
            next_year = time.time() + 31536000  # + 1 year in seconds
            headers.update({
                "IG-U-DS-USER-ID": str(self.user_id),
                # Direct:
                "IG-U-IG-DIRECT-REGION-HINT": f"LLA,{self.user_id},{next_year}:01f7bae7d8b131877d8e0ae1493252280d72f6d0d554447cb1dc9049b6b2c507c08605b7",
                "IG-U-SHBID": f"12695,{self.user_id},{next_year}:01f778d9c9f7546cf3722578fbf9b85143cd6e5132723e5c93f40f55ca0459c8ef8a0d9f",
                "IG-U-SHBTS": f"{int(time.time())},{self.user_id},{next_year}:01f7ace11925d0388080078d0282b75b8059844855da27e23c90a362270fddfb3fae7e28",
                "IG-U-RUR": f"RVA,{self.user_id},{next_year}:01f7f627f9ae4ce2874b2e04463efdb184340968b1b006fa88cb4cc69a942a04201e544c", 
            })
        if self.ig_u_rur:
            headers.update({"IG-U-RUR": self.ig_u_rur})
        if self.ig_www_claim:
            headers.update({"X-IG-WWW-Claim": self.ig_www_claim})
        return headers

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
        self.settings['country'] = self.country = str(country)
        return True

    def set_country_code(self, country_code: int = 1):
        """Set country calling code

        Parameters
        ----------
        country_code: int

        Returns
        -------
        bool
            A boolean value
        """
        self.settings['country_code'] = self.country_code = int(country_code)
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
        user_agent = (self.settings.get("user_agent") or "").replace(self.locale, locale)
        self.settings['locale'] = self.locale = str(locale)
        self.set_user_agent(user_agent)  # update locale in user_agent
        if '_' in locale:
            self.set_country(locale.rsplit('_', 1)[1])
        return True

    def set_timezone_offset(self, seconds: int = 0):
        """Set you timezone offset in seconds

        Parameters
        ----------
        seconds: int
            Specify the offset in seconds from UTC

        Returns
        -------
        bool
            A boolean value
        """
        self.settings['timezone_offset'] = self.timezone_offset = int(seconds)
        return True

    def set_ig_u_rur(self, value):
        self.settings['ig_u_rur'] = self.ig_u_rur = value
        return True

    def set_ig_www_claim(self, value):
        self.settings['ig_www_claim'] = self.ig_www_claim = value
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
        # if self.user_id and login:
        #     raise Exception(f"User already logged ({self.user_id})")
        try:
            if not endpoint.startswith('/'):
                endpoint = f"/v1/{endpoint}"
            api_url = f"https://{config.API_DOMAIN}/api{endpoint}"
            if data:  # POST
                # Client.direct_answer raw dict
                # data = json.dumps(data)
                self.private.headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
                if with_signature:
                    # Client.direct_answer doesn't need a signature
                    data = generate_signature(dumps(data))
                    if extra_sig:
                        data += "&".join(extra_sig)
                response = self.private.post(
                    api_url, data=data, params=params
                )
            else:  # GET
                self.private.headers.pop('Content-Type', None)
                response = self.private.get(api_url, params=params)
            self.logger.debug(
                "private_request %s: %s (%s)", response.status_code, response.url, response.text
            )
            mid = response.headers.get("ig-set-x-mid")
            if mid:
                self.mid = mid
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
                if len(e.response.text) < 512:
                    last_json['message'] = e.response.text
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
                app_version=self.device_settings.get("app_version"),
                manufacturer=self.device_settings.get("manufacturer"),
                model=self.device_settings.get("model"),
            ),
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
            if self.delay_range:
                random_delay(delay_range=self.delay_range)
            self.private_requests_count += 1
            self._send_private_request(endpoint, **kwargs)
        except ClientRequestTimeout:
            self.logger.info('Wait 60 seconds and try one more time (ClientRequestTimeout)')
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
