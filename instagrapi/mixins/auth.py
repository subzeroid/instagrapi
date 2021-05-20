import base64
import datetime
import hashlib
import hmac
import json
import random
import re
import time
import uuid
from pathlib import Path
from typing import Dict, List
from uuid import uuid4

import requests

from instagrapi import config
from instagrapi.exceptions import (
    PleaseWaitFewMinutes,
    PrivateError,
    ReloginAttemptExceeded,
    TwoFactorRequired,
)
from instagrapi.utils import generate_jazoest
from instagrapi.zones import CET

from json.decoder import JSONDecodeError

from instagrapi.exceptions import (
    BadPassword,
    ChallengeRequired,
    ClientBadRequestError,
    InactiveUserError,
    TwoFactorRequiredError,
    InvalidUserError,
    IPBlockError,
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
    UnknownError,
    VideoTooLongException,
)


class PreLoginFlowMixin:
    """
    Helpers for pre login flow
    """

    def pre_login_flow(self) -> bool:
        """
        Emulation mobile app behavior before login

        Returns
        -------
        bool
            A boolean value
        """
        self.set_contact_point_prefill("prefill")
        self.get_prefill_candidates(True)
        self.set_contact_point_prefill("prefill")
        self.sync_launcher(True)
        self.sync_device_features(True)
        return True

    def get_prefill_candidates(self, login: bool = False) -> Dict:
        """
        Get prefill candidates value from Instagram

        Parameters
        ----------
        login: bool, optional
            Whether to login or not

        Returns
        -------
        bool
            A boolean value
        """
        data = {
            "android_device_id": self.device_id,
            "client_contact_points": '[{"type":"omnistring","value":"%s","source":"last_login_attempt"}]'
            % self.username,
            "phone_id": self.phone_id,
            "usages": '["account_recovery_omnibox"]',
            "device_id": self.device_id,
        }
        # if login is False:
        data["_csrftoken"] = self.token
        return self.private_request(
            "accounts/get_prefill_candidates/", data, login=login
        )

    def sync_device_features(self, login: bool = False) -> Dict:
        """
        Sync device features to your Instagram account

        Parameters
        ----------
        login: bool, optional
            Whether to login or not

        Returns
        -------
        Dict
            A dictionary of response from the call
        """
        data = {
            "id": self.uuid,
            "server_config_retrieval": "1",
            "experiments": config.LOGIN_EXPERIMENTS,
        }
        if login is False:
            data["_uuid"] = self.uuid
            data["_uid"] = self.user_id
            data["_csrftoken"] = self.token
        # headers={"X-DEVICE-ID": self.uuid}
        return self.private_request("qe/sync/", data, login=login)

    def sync_launcher(self, login: bool = False) -> Dict:
        """
        Sync Launcher

        Parameters
        ----------
        login: bool, optional
            Whether to login or not

        Returns
        -------
        Dict
            A dictionary of response from the call
        """
        data = {
            "id": self.uuid,
            "server_config_retrieval": "1",
        }
        if login is False:
            data["_uid"] = self.user_id
            data["_uuid"] = self.uuid
            data["_csrftoken"] = self.token
        return self.private_request("launcher/sync/", data, login=login)

    def set_contact_point_prefill(self, usage: str = "prefill") -> Dict:
        """
        Sync Launcher

        Parameters
        ----------
        usage: str, optional
            Default "prefill"

        Returns
        -------
        Dict
            A dictionary of response from the call
        """
        data = {"phone_id": self.phone_id, "usage": usage, "_csrftoken": self.token}
        return self.private_request("accounts/contact_point_prefill/", data, login=True)


class PostLoginFlowMixin:
    """
    Helpers for post login flow
    """

    def login_flow(self) -> bool:
        """
        Emulation mobile app behaivor after login

        Returns
        -------
        bool
            A boolean value
        """
        check_flow = []
        chance = random.randint(1, 100) % 2 == 0
        check_flow.append(self.get_timeline_feed([chance and "is_pull_to_refresh"]))
        check_flow.append(
            self.get_reels_tray_feed(
                reason="pull_to_refresh" if chance else "cold_start"
            )
        )
        return all(check_flow)

    def get_timeline_feed(self, options: List[Dict] = []) -> Dict:
        """
        Get your timeline feed

        Parameters
        ----------
        options: List, optional
            Configurable options

        Returns
        -------
        Dict
            A dictionary of response from the call
        """
        headers = {
            "X-Ads-Opt-Out": "0",
            "X-DEVICE-ID": self.uuid,
            "X-CM-Bandwidth-KBPS": "-1.000",  # str(random.randint(2000, 5000)),
            "X-CM-Latency": str(random.randint(1, 5)),
        }
        data = {
            "feed_view_info": "",
            "phone_id": self.phone_id,
            "battery_level": random.randint(25, 100),
            "timezone_offset": datetime.datetime.now(CET()).strftime("%z"),
            "_csrftoken": self.token,
            "device_id": self.uuid,
            "request_id": self.device_id,
            "_uuid": self.uuid,
            "is_charging": random.randint(0, 1),
            "will_sound_on": random.randint(0, 1),
            "session_id": self.client_session_id,
            "bloks_versioning_id": "e538d4591f238824118bfcb9528c8d005f2ea3becd947a3973c030ac971bb88e",
        }

        if "is_pull_to_refresh" in options:
            data["reason"] = "pull_to_refresh"
            data["is_pull_to_refresh"] = "1"
        elif "is_pull_to_refresh" not in options:
            data["reason"] = "cold_start_fetch"
            data["is_pull_to_refresh"] = "0"

        if "push_disabled" in options:
            data["push_disabled"] = "true"

        if "recovered_from_crash" in options:
            data["recovered_from_crash"] = "1"

        return self.private_request(
            "feed/timeline/", json.dumps(data), with_signature=False, headers=headers
        )

    def get_reels_tray_feed(self, reason: str = "pull_to_refresh") -> Dict:
        """
        Get your reels tray feed

        Parameters
        ----------
        reason: str, optional
            Default "pull_to_refresh"

        Returns
        -------
        Dict
            A dictionary of response from the call
        """
        data = {
            "supported_capabilities_new": config.SUPPORTED_CAPABILITIES,
            "reason": reason,
            "_csrftoken": self.token,
            "_uuid": self.uuid,
        }
        return self.private_request("feed/reels_tray/", data)


class LoginMixin(PreLoginFlowMixin, PostLoginFlowMixin):
    username = None
    password = None
    last_login = None
    relogin_attempt = 0
    device_settings = {}
    client_session_id = ""
    advertising_id = ""
    device_id = ""
    phone_id = ""
    uuid = ""

    def __init__(self):
        self.user_agent = None
        self.settings = None

    def init(self) -> bool:
        """
        Initialize Login helpers

        Returns
        -------
        bool
            A boolean value
        """
        if "cookies" in self.settings:
            self.private.cookies = requests.utils.cookiejar_from_dict(
                self.settings["cookies"]
            )
            self.public.cookie = requests.utils.cookiejar_from_dict(
                self.settings["cookies"]
            )
        self.last_login = self.settings.get("last_login")
        self.set_device(self.settings.get("device_settings"))
        self.set_user_agent(self.settings.get("user_agent"))
        self.set_uuids(self.settings.get("uuids", {}))
        self.username = self.settings.get("username", "")
        self.web_user_agent = self.settings.get(
            "web_user_agent",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/11.1.2 Safari/605.1.15",
        )
        return True

    def login_by_web(self, username: str, password: str) -> dict:
        """Login via the website, get a cookie and login via sessionid

        Args:
            username (str): login username
            password (str): password

        Returns:
            dict: cookies
        """

        def encrypt_password(app_id, key_id, public_key, password):
            import base64
            from nacl.public import PublicKey, SealedBox
            from Crypto import Random
            from Crypto.Cipher import AES

            timestamp = str(int(datetime.now().timestamp()))

            # create a random key of length 32 bytes (for AES 256)
            key = Random.get_random_bytes(32)
            # create a buffer of length 12 bytes filled with 0
            iv = bytearray(12)

            aes = AES.new(key, AES.MODE_GCM, nonce=iv)
            aes.update(bytearray(timestamp, "utf-8"))
            ciphertext, tag = aes.encrypt_and_digest(bytearray(password, "utf-8"))

            # get a byte array of the given public key
            public_key_seal = PublicKey(bytes.fromhex(public_key))
            sealed_box = SealedBox(public_key_seal)
            sealed = sealed_box.encrypt(key)

            enc_password = bytearray()
            enc_password += (
                bytearray([1, int(key_id), len(sealed) & 255, (len(sealed) >> 8) & 255])
                + sealed
                + tag
                + ciphertext
            )

            return f"#PWD_INSTAGRAM_BROWSER:{app_id}:{timestamp}:{str(base64.b64encode(enc_password), 'utf-8')}"

        # https://github.com/instaloader/instaloader/issues/615

        BASE_URL = "https://www.instagram.com/"

        session = requests.Session()
        session.headers = {"user-agent": self.web_user_agent}
        session.cookies["ig_pr"] = "1"
        session.headers["Referer"] = BASE_URL
        session.proxies.update({"http": self.proxy, "https": self.proxy})

        try:
            req = session.get(BASE_URL + "accounts/login/")
            session.headers["X-CSRFToken"] = req.cookies["csrftoken"]
            session.headers["mid"] = mid = req.cookies["mid"]

            enc_password = encrypt_password(
                req.headers.get("ig-set-password-encryption-web-key-version"),
                req.headers.get("ig-set-password-encryption-web-key-id"),
                req.headers.get("ig-set-password-encryption-web-pub-key"),
                password,
            )

            time.sleep(random.uniform(1.175, 2.875))

            response = session.post(
                BASE_URL + "accounts/login/ajax/",
                data={
                    "username": username,
                    "enc_password": enc_password,
                },
                allow_redirects=True,
            )

            last_json = response.json()
        except JSONDecodeError:
            pass
        message = last_json.get("message", "")
        if response.status_code == 403:
            if message == "login_required":
                raise LoginRequired(response=response, **last_json)
            if (
                "Looks like you requested to delete this account" in message
                or "Your account has been disabled for violating our terms" in message
            ):
                raise InvalidUserError(response=response, **last_json)
            raise ClientForbiddenError(response=response, **last_json)
        elif response.status_code == 400:
            error_type = last_json.get("error_type")
            if message == "challenge_required" or message == "checkpoint_required":
                raise ChallengeRequired(**last_json)
            elif message == "feedback_required":
                raise FeedbackRequired(
                    **dict(
                        last_json,
                        message="%s: %s" % (message, last_json.get("feedback_message")),
                    )
                )
            elif error_type == "sentry_block":
                raise SentryBlock(**last_json)
            elif error_type == "rate_limit_error":
                raise RateLimitError(**last_json)
            elif error_type == "bad_password":
                raise BadPassword(**last_json)
            elif error_type == "inactive user":
                raise InactiveUserError(**last_json)
            elif error_type == "two_factor_required":
                raise TwoFactorRequiredError(**last_json)
            elif error_type == "invalid_user":
                raise InvalidUserError(**last_json)
            elif error_type == "ip_block":
                raise IPBlockError(**last_json)
            elif "Please wait a few minutes before you try again" in message:
                raise PleaseWaitFewMinutes(response=response, **last_json)
            elif "VideoTooLongException" in message:
                raise VideoTooLongException(response=response, **last_json)
            elif error_type or message:
                raise UnknownError(**last_json)
            raise ClientBadRequestError(response=response, **last_json)
        elif response.status_code == 429:
            if "Please wait a few minutes before you try again" in message:
                raise PleaseWaitFewMinutes(response=response, **last_json)
            raise ClientThrottledError(response=response, **last_json)
        elif response.status_code == 404:
            raise ClientNotFoundError(response=response, **last_json)
        elif response.status_code == 408:
            raise ClientRequestTimeout(response=response, **last_json)

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
        elif not response.json().get("authenticated"):
            raise BadPassword(**last_json)

        cookies = response.cookies.get_dict()
        cookies["mid"] = mid

        self.settings.update({"cookies": cookies})

        self.init()
        self.inject_sessionid_to_public()

        if not self.username:
            user_id = re.search(r"^\d+", cookies["sessionid"]).group()
            user = self.user_info_v1(int(user_id))
            self.username = user.username

        self.last_login = time.time()

        return cookies

    def login_by_settings(self, settings: str) -> bool:
        self.settings = json.loads(settings)
        self.init()
        self.inject_sessionid_to_public()
        self.last_login = time.time()
        return True

    def login_by_sessionid(self, sessionid: str) -> bool:
        """
        Login using session id

        Parameters
        ----------
        sessionid: str
            Session ID

        Returns
        -------
        bool
            A boolean value
        """
        assert isinstance(sessionid, str) and len(sessionid) > 30, "Invalid sessionid"
        self.settings.update({"cookies": {"sessionid": sessionid}})
        self.init()
        user_id = re.search(r"^\d+", sessionid).group()
        try:
            user = self.user_info_v1(int(user_id))
        except PrivateError:
            user = self.user_short_gql(int(user_id))
        self.username = user.username
        self.cookie_dict["ds_user_id"] = user.pk
        return True

    def login(
        self,
        username: str,
        password: str,
        relogin: bool = False,
        verification_code: str = "",
    ) -> bool:
        """
        Login

        Parameters
        ----------
        username: str
            Instagram Username

        password: str
            Instagram Password

        relogin: bool
            Whether or not to re login, default False

        Returns
        -------
        bool
            A boolean value
        """
        self.username = username
        self.password = password
        self.init()
        if relogin:
            self.private.cookies.clear()
            if self.relogin_attempt > 1:
                raise ReloginAttemptExceeded()
            self.relogin_attempt += 1
        # if self.user_id and self.last_login:
        #     if time.time() - self.last_login < 60 * 60 * 24:
        #        return True  # already login
        if self.user_id:
            return True  # already login
        try:
            self.pre_login_flow()
        except PleaseWaitFewMinutes:
            # The instagram application ignores this error
            # and continues to log in (repeat this behavior)
            pass
        enc_password = self.password_encrypt(password)
        data = {
            "jazoest": generate_jazoest(self.phone_id),
            # "country_codes": "[{\"country_code\":\"7\",\"source\":[\"default\"]}]",
            "phone_id": self.phone_id,
            "enc_password": enc_password,
            # "_csrftoken": self.token,
            "username": username,
            "adid": self.advertising_id,
            "guid": self.uuid,
            "device_id": self.device_id,
            "google_tokens": "[]",
            "login_attempt_count": "0",
        }
        try:
            logged = self.private_request("accounts/login/", data, login=True)
        except TwoFactorRequired as e:
            if not verification_code.strip():
                raise TwoFactorRequired(
                    f"{e} (you did not provide verification_code for login method)"
                )
            two_factor_identifier = self.last_json.get("two_factor_info", {}).get(
                "two_factor_identifier"
            )
            data = {
                "verification_code": verification_code,
                "phone_id": self.phone_id,
                "_csrftoken": self.token,
                "two_factor_identifier": two_factor_identifier,
                "username": username,
                "trust_this_device": "0",
                "guid": self.uuid,
                "device_id": self.device_id,
                "waterfall_id": str(uuid4()),
                "verification_method": "3",
            }
            logged = self.private_request(
                "accounts/two_factor_login/", data, login=True
            )
        if logged:
            self.login_flow()
            self.last_login = time.time()
            return True
        return False

    def relogin(self) -> bool:
        """
        Relogin helper

        Returns
        -------
        bool
            A boolean value
        """
        return self.login(self.username, self.password, relogin=True)

    @property
    def cookie_dict(self) -> dict:
        return self.private.cookies.get_dict()

    @property
    def sessionid(self) -> str:
        return self.cookie_dict.get("sessionid")

    @property
    def token(self) -> str:
        return self.cookie_dict.get("csrftoken")

    @property
    def rank_token(self) -> str:
        return f"{self.user_id}_{self.uuid}"

    @property
    def user_id(self) -> int:
        user_id = self.cookie_dict.get("ds_user_id")
        if user_id:
            return int(user_id)
        return None

    # @property
    # def username(self):
    #     return self.cookie_dict.get("ds_user")

    @property
    def mid(self) -> str:
        return self.cookie_dict.get("mid")

    @property
    def device(self) -> dict:
        return {
            key: val
            for key, val in self.device_settings.items()
            if key in ["manufacturer", "model", "android_version", "android_release"]
        }

    def get_settings(self) -> Dict:
        """
        Get current session settings

        Returns
        -------
        Dict
            Current session settings as a Dict
        """
        return {
            "uuids": {
                "phone_id": self.phone_id,
                "uuid": self.uuid,
                "client_session_id": self.client_session_id,
                "advertising_id": self.advertising_id,
                "device_id": self.device_id,
            },
            "cookies": requests.utils.dict_from_cookiejar(self.private.cookies),
            "last_login": self.last_login,
            "device_settings": self.device_settings,
            "user_agent": self.user_agent,
            "web_user_agent": self.web_user_agent,
            "username": self.username,
        }

    def set_settings(self, settings: Dict) -> bool:
        """
        Set session settings

        Returns
        -------
        Bool
        """
        self.settings = settings
        return True

    def load_settings(self, path: Path) -> Dict:
        """
        Load session settings

        Parameters
        ----------
        path: Path
            Path to storage file

        Returns
        -------
        Dict
            Current session settings as a Dict
        """
        with open(path, "r") as fp:
            self.set_settings(json.load(fp))
            return self.settings
        return None

    def dump_settings(self, path: Path) -> bool:
        """
        Serialize and save session settings

        Parameters
        ----------
        path: Path
            Path to storage file

        Returns
        -------
        Bool
        """
        with open(path, "w") as fp:
            json.dump(self.get_settings(), fp)
        return True

    def set_device(self, device: Dict = None) -> bool:
        """
        Helper to set a device for login

        Parameters
        ----------
        device: Dict, optional
            Dict of device settings, default is None

        Returns
        -------
        bool
            A boolean value
        """
        self.device_settings = device or {
            "app_version": "169.3.0.30.135",
            "android_version": 26,
            "android_release": "8.0.0",
            "dpi": "640dpi",
            "resolution": "1440x2560",
            "manufacturer": "Xiaomi",
            "device": "MI 5s",
            "model": "capricorn",
            "cpu": "qcom",
            "version_code": "264009049",
        }
        self.settings["device_settings"] = self.device_settings
        self.set_uuids({})
        return True

    def set_user_agent(self, user_agent: str = "") -> bool:
        """
        Helper to set user agent

        Parameters
        ----------
        user_agent: str, optional
            User agent, default is ""

        Returns
        -------
        bool
            A boolean value
        """
        self.user_agent = user_agent or config.USER_AGENT_BASE.format(
            **self.device_settings
        )
        self.private.headers.update({"User-Agent": self.user_agent})
        self.settings["user_agent"] = self.user_agent
        self.set_uuids({})
        return True

    def set_uuids(self, uuids: Dict = None) -> bool:
        """
        Helper to set uuids

        Parameters
        ----------
        uuids: Dict, optional
            UUIDs, default is None

        Returns
        -------
        bool
            A boolean value
        """
        self.phone_id = uuids.get("phone_id", self.generate_uuid())
        self.uuid = uuids.get("uuid", self.generate_uuid())
        self.client_session_id = uuids.get("client_session_id", self.generate_uuid())
        self.advertising_id = uuids.get("advertising_id", self.generate_uuid())
        self.device_id = uuids.get("device_id", self.generate_device_id())
        return True

    def generate_uuid(self) -> str:
        """
        Helper to generate uuids

        Returns
        -------
        str
            A stringified UUID
        """
        return str(uuid.uuid4())

    def generate_device_id(self) -> str:
        """
        Helper to generate Device ID

        Returns
        -------
        str
            A random android device id
        """
        return "android-%s" % hashlib.md5(str(time.time()).encode()).hexdigest()[:16]

    def expose(self) -> Dict:
        """
        Helper to expose

        Returns
        -------
        Dict
            A dictionary of response from the call
        """
        data = {"id": self.uuid, "experiment": "ig_android_profile_contextual_feed"}
        return self.private_request("qe/expose/", self.with_default_data(data))

    def with_default_data(self, data: Dict) -> Dict:
        """
        Helper to get default data

        Returns
        -------
        Dict
            A dictionary of default data
        """
        return dict(
            {
                "_uuid": self.uuid,
                "_uid": str(self.user_id),
                "_csrftoken": self.token,
                "device_id": self.device_id,
            },
            **data,
        )

    def with_action_data(self, data: Dict) -> Dict:
        """
        Helper to get action data

        Returns
        -------
        Dict
            A dictionary of action data
        """
        return dict(self.with_default_data({"radio_type": "wifi-none"}), **data)

    def gen_user_breadcrumb(self, size: int) -> str:
        """
        Helper to generate user breadcrumbs

        Parameters
        ----------
        size: int
            Integer value

        Returns
        -------
        Str
            A string
        """
        key = "iN4$aGr0m"
        dt = int(time.time() * 1000)
        time_elapsed = random.randint(500, 1500) + size * random.randint(500, 1500)
        text_change_event_count = max(1, size / random.randint(3, 5))
        data = "{size!s} {elapsed!s} {count!s} {dt!s}".format(
            **{
                "size": size,
                "elapsed": time_elapsed,
                "count": text_change_event_count,
                "dt": dt,
            }
        )
        return "{!s}\n{!s}\n".format(
            base64.b64encode(
                hmac.new(
                    key.encode("ascii"), data.encode("ascii"), digestmod=hashlib.sha256
                ).digest()
            ),
            base64.b64encode(data.encode("ascii")),
        )

    def inject_sessionid_to_public(self) -> bool:
        """
        Inject sessionid from private session to public session

        Returns
        -------
        bool
            A boolean value
        """
        if self.sessionid:
            self.public.cookies.set("sessionid", self.sessionid)
            return True
        return False
