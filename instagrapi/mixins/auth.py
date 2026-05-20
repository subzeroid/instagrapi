import base64
import hashlib
import hmac
import json
import random
import re
import time
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Union
from uuid import uuid4

import requests
from pydantic import ValidationError

from instagrapi import config
from instagrapi.exceptions import (
    BadCredentials,
    BadPassword,
    ClientThrottledError,
    PleaseWaitFewMinutes,
    PrivateError,
    ReloginAttemptExceeded,
    TwoFactorRequired,
    UnknownError,
)
from instagrapi.utils.auth import gen_token, generate_jazoest
from instagrapi.utils.serialization import dumps

# from instagrapi.zones import CET
TIMELINE_FEED_REASONS = (
    "cold_start_fetch",
    "warm_start_fetch",
    "pagination",
    "pull_to_refresh",
    "auto_refresh",
)
REELS_TRAY_REASONS = ("cold_start", "pull_to_refresh")
try:
    from typing import Literal

    TIMELINE_FEED_REASON = Literal[TIMELINE_FEED_REASONS]
    REELS_TRAY_REASON = Literal[REELS_TRAY_REASONS]
except ImportError:
    # python <= 3.8
    TIMELINE_FEED_REASON = str
    REELS_TRAY_REASON = str


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
        # self.set_contact_point_prefill("prefill")
        # self.get_prefill_candidates(True)
        # self.set_contact_point_prefill("prefill")
        self.sync_launcher(True)
        # self.sync_device_features(True)
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
            "android_device_id": self.android_device_id,
            "client_contact_points": '[{"type":"omnistring","value":"%s","source":"last_login_attempt"}]'
            % self.username,
            "phone_id": self.phone_id,
            "usages": '["account_recovery_omnibox"]',
            "logged_in_user_ids": "[]",  # "[\"123456789\",\"987654321\"]",
            "device_id": self.uuid,
        }
        # if login is False:
        data["_csrftoken"] = self.token
        return self.private_request("accounts/get_prefill_candidates/", data, login=login)

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
            # "experiments": config.LOGIN_EXPERIMENTS,
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
        data = {
            "phone_id": self.phone_id,
            "usage": usage,
            # "_csrftoken": self.token
        }
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
        # chance = random.randint(1, 100) % 2 == 0
        # reason = "pull_to_refresh" if chance else "cold_start"
        check_flow.append(self.get_reels_tray_feed("cold_start"))
        check_flow.append(self.get_timeline_feed(["cold_start_fetch"]))
        return all(check_flow)

    @staticmethod
    def _timeline_media_id(media: Dict) -> str:
        media_id = media.get("id") or media.get("media_id")
        if media_id:
            return str(media_id)

        pk = media.get("pk")
        user = media.get("user") or {}
        user_pk = user.get("pk") or media.get("user_id") or media.get("owner_id")
        if pk and user_pk:
            return f"{pk}_{user_pk}"
        if pk:
            return str(pk)
        return ""

    def _timeline_seen_posts_from_response(self, response: Dict) -> List[str]:
        media_ids = []
        for item in response.get("feed_items") or []:
            if not isinstance(item, dict):
                continue
            media = item.get("media_or_ad") or item.get("media")
            if not isinstance(media, dict):
                continue
            media_id = self._timeline_media_id(media)
            if media_id:
                media_ids.append(media_id)
        return media_ids

    def _remember_timeline_seen_posts(self, response: Dict) -> None:
        remembered = list(getattr(self, "_timeline_seen_posts", []))
        known = set(remembered)
        for media_id in self._timeline_seen_posts_from_response(response):
            if media_id in known:
                continue
            remembered.append(media_id)
            known.add(media_id)
        self._timeline_seen_posts = remembered[-200:]

    @staticmethod
    def _join_timeline_seen_posts(seen_posts: Union[str, Iterable[str], None]) -> str:
        if not seen_posts:
            return ""
        if isinstance(seen_posts, str):
            return seen_posts
        return ",".join(str(media_id) for media_id in seen_posts if media_id)

    @staticmethod
    def _timeline_feed_view_info(media_ids: Iterable[str]) -> List[Dict]:
        latest_timestamp = int(time.time() * 1000)
        return [
            {
                "media_id": str(media_id),
                "version": 24,
                "media_pct": 1.0,
                "time_info": {"10": 1, "25": 1, "50": 1, "75": 1},
                "latest_timestamp": latest_timestamp,
            }
            for media_id in media_ids
        ]

    def _timeline_feed_view_info_json(self, feed_view_info: Union[str, List[Dict], None], seen_posts: str) -> str:
        if feed_view_info is not None:
            if isinstance(feed_view_info, str):
                return feed_view_info
            return json.dumps(feed_view_info)
        if not seen_posts:
            return "[]"
        return json.dumps(self._timeline_feed_view_info(seen_posts.split(",")))

    @staticmethod
    def _timeline_session_level_signals_json() -> str:
        inactive_time = -1
        return dumps(
            {
                "time_since_current_surface_session_start": 0,
                "time_since_fg_session_start": 0,
                "time_since_last_background": 0,
                "num_ad_seen_current_surface_current_session": 0,
                "app_entry": "normal",
                "last_surfaces_visited_current_session": [],
                "video_play_count": 0,
                "video_pause_count": 0,
                "video_dwell_time_sum": 0,
                "video_dwell_time_max": 0,
                "video_view_count": 0,
                "video_intentional_audio_on": 0,
                "video_intentional_audio_off": 0,
                "video_audio_on_count": 0,
                "feed_to_reels_iv_entry": 0,
                "time_since_last_ad_click": inactive_time,
                "time_since_last_ad_like": inactive_time,
                "time_since_last_organic_like": inactive_time,
                "time_since_last_like": inactive_time,
                "time_since_last_organic_business_profile_visit": inactive_time,
                "time_since_last_ad_imp": inactive_time,
                "time_since_last_search": inactive_time,
                "time_since_last_organic_engagement_event": inactive_time,
                "time_since_last_ad_profile_visit": inactive_time,
                "time_since_last_ad_cta": inactive_time,
                "time_since_last_ad_caption_more_click": inactive_time,
                "time_since_last_ad_comment_button": inactive_time,
                "time_since_last_ad_share": inactive_time,
                "time_since_last_ad_media_tap": inactive_time,
                "time_since_last_ad_gesture": inactive_time,
                "time_since_last_search_result_click": inactive_time,
                "time_since_last_serp_click": inactive_time,
                "time_since_last_organic_share": inactive_time,
                "time_since_last_organic_comment": inactive_time,
                "time_since_last_organic_caption_click": inactive_time,
                "time_since_last_organic_media_tap": inactive_time,
                "time_since_last_organic_gesture": inactive_time,
                "num_search_clicks_current_session": 0,
            }
        )

    def get_timeline_feed(
        self,
        reason: TIMELINE_FEED_REASON = "pull_to_refresh",
        max_id: str = None,
        seen_posts: Union[str, Iterable[str], None] = None,
        feed_view_info: Union[str, List[Dict[str, Any]], None] = None,
    ) -> Dict:
        """
        Get your timeline feed

        Parameters
        ----------
        reason: str, optional
            Reason to refresh the feed (cold_start_fetch, paginating, pull_to_refresh); Default "pull_to_refresh"
        max_id: str, optional
            Cursor for the next feed chunk (next cursor can be found in response["next_max_id"])
        seen_posts: str or iterable, optional
            Media ids already rendered by the caller. When omitted during pagination,
            ids from previous get_timeline_feed() responses are reused.
        feed_view_info: str or list, optional
            JSON-serializable view telemetry. When omitted during pagination, a
            minimal view telemetry payload is generated from seen_posts.

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
        request_time_ms = str(int(time.time() * 1000))
        data = {
            "app_start_time": request_time_ms,
            "has_camera_permission": "1",
            "feed_view_info": "[]",  # e.g. [{"media_id":"2634223601739446191_7450075998","version":24,
            # "media_pct":1.0,"time_info":{"10":63124,"25":63124,"50":63124,"75":63124},"latest_timestamp":1628253523186}]
            "client_recorded_request_time_ms": request_time_ms,
            "client_seen_store_media_list": "",
            "client_view_state_media_list": "[]",
            "device_timezone_name": self.timezone_name,
            "feed_reshare_info": "",
            "phone_id": self.phone_id,
            "reason": reason,
            "battery_level": 100,  # Random battery level is not simulating real bahaviour
            "timezone_offset": str(self.timezone_offset),
            # "_csrftoken": self.token, No longer in data
            "device_id": self.uuid,
            "include_attribution_ui_data": "true",
            "push_disabled": self._bool_to_ig_string(self.push_disabled),
            "request_id": self.request_id,
            "request_build_time": request_time_ms,
            "_uuid": self.uuid,
            "is_charging": random.randint(0, 1),
            "is_dark_mode": 1,  # Random dark mode is not simulating real bahaviour
            "will_sound_on": random.randint(0, 1),
            "session_id": self.client_session_id,
            "session_level_signals": self._timeline_session_level_signals_json(),
            "bloks_versioning_id": self.bloks_versioning_id,
        }
        if reason in ["pull_to_refresh", "auto_refresh"]:
            data["is_pull_to_refresh"] = "1"
        else:
            data["is_pull_to_refresh"] = "0"

        if max_id:
            data["max_id"] = max_id
            data["reason"] = "pagination"
            data["organic_realtime_information"] = "[]"
            data["pagination_source"] = "feed_recs"
            data["triggered_by_visible_spinner"] = "false"
            if seen_posts is None:
                seen_posts = getattr(self, "_timeline_seen_posts", [])

        seen_posts_value = self._join_timeline_seen_posts(seen_posts)
        if seen_posts_value:
            data["seen_posts"] = seen_posts_value
        data["feed_view_info"] = self._timeline_feed_view_info_json(feed_view_info, seen_posts_value)

        # if "push_disabled" in options:
        #     data["push_disabled"] = "true"
        # if "recovered_from_crash" in options:
        #     data["recovered_from_crash"] = "1"
        result = self.private_request("feed/timeline/", json.dumps(data), with_signature=False, headers=headers)
        self._remember_timeline_seen_posts(result)
        return result

    def get_reels_tray_feed(self, reason: REELS_TRAY_REASON = "pull_to_refresh") -> Dict:
        """
        Get your reels tray feed

        Parameters
        ----------
        reason: str, optional
            Reason to refresh reels tray fee (cold_start, pull_to_refresh); Default "pull_to_refresh"

        Returns
        -------
        Dict
            A dictionary of response from the call
        """
        data = {
            "supported_capabilities_new": config.SUPPORTED_CAPABILITIES,
            "reason": reason,
            "timezone_offset": str(self.timezone_offset),
            "tray_session_id": self.tray_session_id,
            "request_id": self.request_id,
            # "latest_preloaded_reel_ids": "[]",  # Long JSON array with reel data
            # Example: [{"reel_id":"6009504750","media_count":"15","timestamp":1628253494,"media_ids":"..."}]
            "page_size": 50,
            # "_csrftoken": self.token,
            "_uuid": self.uuid,
        }
        if reason == "cold_start":
            data["reel_tray_impressions"] = {}
        else:
            data["reel_tray_impressions"] = {self.user_id: str(time.time())}
        return self.private_request("feed/reels_tray/", data)


class LoginMixin(PreLoginFlowMixin, PostLoginFlowMixin):
    username = None
    password = None
    authorization_data = {}  # decoded authorization header
    last_login = None
    relogin_attempt = 0
    device_settings = {}
    client_session_id = ""
    tray_session_id = ""
    advertising_id = ""
    android_device_id = ""
    request_id = ""
    phone_id = ""
    app_id = "567067343352427"
    uuid = ""
    mid = ""
    country = "US"
    country_code = 1  # Phone code, default USA
    locale = "en_US"
    timezone_offset: int = -14400  # New York, GMT-4 in seconds
    timezone_name: str = ""
    push_disabled: bool = True
    public_request_retries_count = 3
    public_request_retries_timeout = 2
    session_retry_total = 3
    session_retry_backoff_factor = 2
    session_retry_statuses = [429, 500, 502, 503, 504]
    # Example: CLN,49897488153,1666640702:01f7bdb93090f4f773516fc2cf1424178a58a2295b4c754090ba02cb0a834e2d1f731e20
    ig_u_rur = ""
    ig_www_claim = ""  # e.g. hmac.AR2uidim8es5kYgDiNxY0UG_ZhffFFSt8TGCV5eA1VYYsMNx

    def __init__(self):
        self.bloks_versioning_id = config.APP_SETTINGS[config.DEFAULT_APP_VERSION]["bloks_versioning_id"]
        self.user_agent = None
        self.settings = None
        self.override_app_version = False

    def _clear_session_state(
        self,
        *,
        clear_private_cookies: bool = False,
        clear_public_cookies: bool = False,
        clear_authorization_data: bool = False,
        clear_authorization_header: bool = False,
        clear_last_login: bool = False,
        reset_relogin_attempt: bool = False,
    ) -> None:
        if clear_authorization_data:
            self.authorization_data = {}
        if clear_last_login:
            self.last_login = None
        if reset_relogin_attempt:
            self.relogin_attempt = 0
        if clear_authorization_header:
            self.private.headers.pop("Authorization", None)
        if clear_private_cookies:
            self.private.cookies.clear()
        if clear_public_cookies:
            self.public.cookies.clear()

    def _find_login_response_value(self, data: Any, key: str) -> Any:
        if isinstance(data, dict):
            value = data.get(key)
            if value:
                return value
            for child in data.values():
                value = self._find_login_response_value(child, key)
                if value:
                    return value
        elif isinstance(data, list):
            for child in data:
                value = self._find_login_response_value(child, key)
                if value:
                    return value
        return None

    def _extract_two_step_verification_context(self, data: Dict) -> str:
        value = self._find_login_response_value(data, "two_step_verification_context")
        return value.strip() if isinstance(value, str) else ""

    def _exception_context(self, data: Dict) -> Dict:
        context = deepcopy(data)
        message = context.pop("message", None)
        if message is not None:
            context["instagram_message"] = message
        return context

    def _login_response_bool(self, data: Dict, key: str) -> bool:
        value = self._find_login_response_value(data, key)
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return bool(value)
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes"}
        return False

    def _normalize_backup_code(self, code: str) -> str:
        return re.sub(r"[\s-]+", "", str(code).strip())

    def _looks_like_backup_code(self, code: str) -> bool:
        return bool(re.fullmatch(r"\d{8}", self._normalize_backup_code(code)))

    def _infer_bloks_two_factor_challenge(self, data: Dict, verification_code: str = "") -> str:
        if self._looks_like_backup_code(verification_code):
            return "backup_codes"
        sms_enabled = self._login_response_bool(data, "sms_two_factor_on")
        totp_enabled = self._login_response_bool(data, "totp_two_factor_on")
        if sms_enabled and not totp_enabled:
            return "sms"
        return "totp"

    def _login_with_bloks_two_factor(self, verification_code: str, login_json: Dict, exc: Exception) -> bool:
        context = self._extract_two_step_verification_context(login_json)
        if not context:
            raise TwoFactorRequired(
                "Instagram rejected the legacy two-factor login endpoint and "
                "may require a newer Bloks-based two-factor verification flow, "
                "but the response did not include two_step_verification_context "
                "required for the Bloks two-factor fallback. Complete "
                "verification in the Instagram app or capture a fresh login "
                "response with the current app flow.",
                response=getattr(exc, "response", None),
                **self._exception_context(login_json),
            ) from exc

        challenge = self._infer_bloks_two_factor_challenge(login_json, verification_code)
        self.bloks_two_step_verification_entrypoint(context)
        self.bloks_two_step_verification_method_picker(context)
        self.bloks_two_step_verification_select_method(context, selected_method=challenge)
        if challenge == "backup_codes":
            self.bloks_two_step_verification_enter_backup_code(context)
        code = self._normalize_backup_code(verification_code) if challenge == "backup_codes" else verification_code
        result = self.bloks_two_step_verification_verify_code(
            context,
            code,
            challenge=challenge,
        )
        if self.bloks_apply_login_response(result):
            return True
        raise TwoFactorRequired(
            "Instagram accepted the Bloks two-factor verification request, but "
            "the response did not include an embedded login payload. Inspect "
            "the raw Bloks response and retry with the selected verification "
            "method required by the account.",
            response=getattr(exc, "response", None),
            **self._exception_context(login_json),
        ) from exc

    def _login_with_caa_bloks_two_factor(self, verification_code: str, password: str, exc: Exception) -> bool:
        caa_result = self.bloks_caa_login_send_request(password, login_attempt_count=1)
        context = self.bloks_extract_two_step_verification_context(caa_result)
        login_json = deepcopy(self.last_json) if isinstance(self.last_json, dict) else {}
        if not context:
            raise TwoFactorRequired(
                "Instagram rejected the legacy login endpoint and may require "
                "a newer CAA/Bloks login flow, but the CAA response did not "
                "include two_step_verification_context required for automatic "
                "Bloks two-factor verification. Complete verification in the "
                "Instagram app or inspect the current login response.",
                response=getattr(exc, "response", None),
                **self._exception_context(login_json),
            ) from exc
        login_json["two_step_verification_context"] = context
        return self._login_with_bloks_two_factor(verification_code, login_json, exc)

    def init(self) -> bool:
        """
        Initialize Login helpers

        Returns
        -------
        bool
            A boolean value
        """
        if "cookies" in self.settings:
            self.private.cookies = requests.utils.cookiejar_from_dict(self.settings["cookies"])
        else:
            self._clear_session_state(clear_private_cookies=True)
        self.authorization_data = self.settings.get("authorization_data", {})
        self.last_login = self.settings.get("last_login")
        timezone_offset = self.settings.get("timezone_offset", self.timezone_offset)
        timezone_name = self.settings.get("timezone_name", self.timezone_name)
        push_disabled = self.settings.get("push_disabled", self.push_disabled)
        locale = self.settings.get("locale", self.locale)
        country = self.settings.get("country", self.country)
        country_code = self.settings.get("country_code", self.country_code)
        self.set_tls_verify(self.settings.get("tls_verify", self.tls_verify))
        self.set_retry_config(
            request_timeout=self.settings.get("request_timeout", self.request_timeout),
            public_request_retries_count=self.settings.get(
                "public_request_retries_count", self.public_request_retries_count
            ),
            public_request_retries_timeout=self.settings.get(
                "public_request_retries_timeout", self.public_request_retries_timeout
            ),
            session_retry_total=self.settings.get("session_retry_total", self.session_retry_total),
            session_retry_backoff_factor=self.settings.get(
                "session_retry_backoff_factor", self.session_retry_backoff_factor
            ),
            session_retry_statuses=self.settings.get("session_retry_statuses", self.session_retry_statuses),
            public_transport=self.settings.get("public_transport"),
            public_transport_impersonate=self.settings.get("public_transport_impersonate"),
        )

        self.set_timezone_offset(timezone_offset, timezone_name=timezone_name or None)
        self.set_push_disabled(push_disabled)
        self.set_device(self.settings.get("device_settings"))
        self.set_user_agent(self.settings.get("user_agent"))
        self.set_uuids(self.settings.get("uuids") or {})
        self.set_locale(locale)
        self.set_country(country)
        self.set_country_code(country_code)
        self.mid = self.settings.get("mid", self.cookie_dict.get("mid"))
        self.set_ig_u_rur(self.settings.get("ig_u_rur"))
        self.set_ig_www_claim(self.settings.get("ig_www_claim"))
        # init headers
        headers = self.base_headers
        if self.authorization:
            headers.update({"Authorization": self.authorization})
        else:
            self.private.headers.pop("Authorization", None)
        if not self.ig_u_rur:
            self.private.headers.pop("IG-U-RUR", None)
        self.private.headers.update(headers)
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
        user_match = re.search(r"^\d+", sessionid)
        assert user_match, "Invalid sessionid"
        self.settings["cookies"] = {"sessionid": sessionid}
        self.init()
        user_id = user_match.group()
        self.authorization_data = {
            "ds_user_id": user_id,
            "sessionid": sessionid,
            "should_use_header_over_cookies": True,
        }
        try:
            user = self.user_info_v1(int(user_id))
        except (PrivateError, ValidationError):
            user = self.user_short_gql(int(user_id))
        self.username = user.username
        self.authorization_data["ds_user_id"] = str(user.pk)
        self.private.cookies.set("ds_user_id", str(user.pk))
        self.private.headers.update(self.base_headers)
        self.private.headers.update({"Authorization": self.authorization})
        return True

    def login(
        self,
        username: Union[str, None] = None,
        password: Union[str, None] = None,
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
        verification_code: str
            2FA verification code

        Returns
        -------
        bool
            A boolean value
        """
        if username and password:
            self.username = username
            self.password = password
        if self.username is None or self.password is None:
            raise BadCredentials("Both username and password must be provided.")

        if relogin:
            self._clear_session_state(
                clear_authorization_data=True,
                clear_authorization_header=True,
                clear_private_cookies=True,
                clear_public_cookies=True,
            )
            if self.relogin_attempt > 1:
                raise ReloginAttemptExceeded()
            self.relogin_attempt += 1
        # if self.user_id and self.last_login:
        #     if time.time() - self.last_login < 60 * 60 * 24:
        #        return True  # already login
        if self.user_id and not relogin:
            return True  # already login
        try:
            self.pre_login_flow()
        except (PleaseWaitFewMinutes, ClientThrottledError):
            self.logger.warning("Ignore 429: Continue login")
            # The instagram application ignores this error
            # and continues to log in (repeat this behavior)
        enc_password = self.password_encrypt(self.password)
        data = {
            "jazoest": generate_jazoest(self.phone_id),
            "country_codes": '[{"country_code":"%d","source":["default"]}]' % int(self.country_code),
            "phone_id": self.phone_id,
            "enc_password": enc_password,
            "username": self.username,
            "adid": self.advertising_id,
            "guid": self.uuid,
            "device_id": self.android_device_id,
            "google_tokens": "[]",
            "login_attempt_count": "0",
        }
        try:
            logged = self.private_request("accounts/login/", data, login=True)
            self.authorization_data = self.parse_authorization(self.last_response.headers.get("ig-set-authorization"))
        except BadPassword as exc:
            login_json = deepcopy(self.last_json) if isinstance(self.last_json, dict) else {}
            context = self._extract_two_step_verification_context(login_json)
            if not context and not verification_code.strip():
                raise
            if not verification_code.strip():
                raise TwoFactorRequired(
                    f"{exc} (Instagram returned a Bloks two-factor context; provide verification_code for login)",
                    response=getattr(exc, "response", None),
                    **self._exception_context(login_json),
                ) from exc
            if context:
                logged = self._login_with_bloks_two_factor(verification_code, login_json, exc)
            else:
                logged = self._login_with_caa_bloks_two_factor(verification_code, self.password, exc)
        except TwoFactorRequired as e:
            if not verification_code.strip():
                raise TwoFactorRequired(f"{e} (you did not provide verification_code for login method)")
            two_factor_json = deepcopy(self.last_json) if isinstance(self.last_json, dict) else {}
            if self._looks_like_backup_code(verification_code) and self._extract_two_step_verification_context(
                two_factor_json
            ):
                logged = self._login_with_bloks_two_factor(verification_code, two_factor_json, e)
            else:
                two_factor_identifier = self.last_json.get("two_factor_info", {}).get("two_factor_identifier")
                data = {
                    "verification_code": verification_code,
                    "phone_id": self.phone_id,
                    "_csrftoken": self.token,
                    "two_factor_identifier": two_factor_identifier,
                    "username": self.username,
                    "trust_this_device": "0",
                    "guid": self.uuid,
                    "device_id": self.android_device_id,
                    "waterfall_id": str(uuid4()),
                    "verification_method": "3",
                }
                try:
                    logged = self.private_request("accounts/two_factor_login/", data, login=True)
                except UnknownError as exc:
                    message = getattr(exc, "message", "") or ""
                    if message.strip().lower() == "invalid parameters":
                        logged = self._login_with_bloks_two_factor(verification_code, two_factor_json, exc)
                    else:
                        raise
                else:
                    self.authorization_data = self.parse_authorization(
                        self.last_response.headers.get("ig-set-authorization")
                    )
        if logged:
            self.login_flow()
            self.last_login = time.time()
            self.relogin_attempt = 0
            return True
        return False

    def one_tap_app_login(self, user_id: str, nonce: str) -> bool:
        """One tap login emulation

        Parameters
        ----------
        user_id: str
            User ID
        nonce: str
            Login nonce (from Instagram, e.g. in /logout/)

        Returns
        -------
        bool
            A boolean value
        """
        user_id = int(user_id)
        data = {
            "phone_id": self.phone_id,
            "user_id": user_id,
            "adid": self.advertising_id,
            "guid": self.uuid,
            "device_id": self.uuid,
            "login_nonce": nonce,
            "_csrftoken": self.token,
        }
        return self.private_request("accounts/one_tap_app_login/", data)

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
        sessionid = self.cookie_dict.get("sessionid")
        if not sessionid and self.authorization_data:
            sessionid = self.authorization_data.get("sessionid")
        return sessionid

    @property
    def token(self) -> str:
        """CSRF token
        e.g. vUJGjpst6szjI38mZ6Pb1dROsWVerZelGSYGe0W1tuugpSUefVjRLj2Pom2SWNoA
        """
        if not getattr(self, "_token", None):
            self._token = self.cookie_dict.get("csrftoken", gen_token(64))
        return self._token

    @property
    def rank_token(self) -> str:
        return f"{self.user_id}_{self.uuid}"

    @property
    def user_id(self) -> int:
        user_id = self.cookie_dict.get("ds_user_id")
        if not user_id and self.authorization_data:
            user_id = self.authorization_data.get("ds_user_id")
        if user_id:
            return int(user_id)
        return None

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
                "android_device_id": self.android_device_id,
                # "device_id": self.uuid,
                "request_id": self.request_id,
                "tray_session_id": self.tray_session_id,
            },
            "mid": self.mid,
            "ig_u_rur": self.ig_u_rur,
            "ig_www_claim": self.ig_www_claim,
            "authorization_data": self.authorization_data,
            "cookies": requests.utils.dict_from_cookiejar(self.private.cookies),
            "last_login": self.last_login,
            "device_settings": self.device_settings,
            "user_agent": self.user_agent,
            "country": self.country,
            "country_code": self.country_code,
            "locale": self.locale,
            "timezone_offset": self.timezone_offset,
            "timezone_name": self.timezone_name,
            "push_disabled": self.push_disabled,
            "request_timeout": self.request_timeout,
            "public_request_retries_count": self.public_request_retries_count,
            "public_request_retries_timeout": self.public_request_retries_timeout,
            "session_retry_total": self.session_retry_total,
            "session_retry_backoff_factor": self.session_retry_backoff_factor,
            "session_retry_statuses": self.session_retry_statuses,
            "public_transport": self.public_transport,
            "public_transport_impersonate": self.public_transport_impersonate,
            "tls_verify": self.tls_verify,
        }

    def set_settings(self, settings: Dict) -> bool:
        """
        Set session settings

        Returns
        -------
        Bool
        """
        self.settings = deepcopy(settings)
        self.init()
        return True

    def load_settings(self, path: Union[str, Path], override_app_version: bool = False) -> Dict:
        """
        Load session settings

        Parameters
        ----------
        path: Path
            Path to storage file
        override_app_version: bool, optional
            Mismatched app_version/version_code/bloks_versioning_id may
            increase risk. If True, override with a known version from
            APP_SETTINGS (in memory). Call dump_settings() to persist.


        Returns
        -------
        Dict
            Current session settings as a Dict
        """
        self.override_app_version = override_app_version
        with open(path, "r") as fp:
            self.set_settings(json.load(fp))
            return self.settings

    def dump_settings(self, path: Union[str, Path]) -> bool:
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
            json.dump(self.get_settings(), fp, indent=4)
        return True

    def set_tls_verify(self, tls_verify: Union[bool, str]) -> bool:
        self.tls_verify = tls_verify
        for name in ("public", "private", "graphql"):
            session = getattr(self, name, None)
            if session is not None:
                session.verify = tls_verify
        if self.settings is not None:
            self.settings["tls_verify"] = tls_verify
        return True

    def set_retry_config(
        self,
        request_timeout: Union[int, float, None] = None,
        public_request_retries_count: int = None,
        public_request_retries_timeout: Union[int, float] = None,
        session_retry_total: int = None,
        session_retry_backoff_factor: Union[int, float] = None,
        session_retry_statuses: list = None,
        public_transport: str = None,
        public_transport_impersonate: str = None,
    ) -> bool:
        if request_timeout is not None:
            self.request_timeout = request_timeout
        if public_request_retries_count is not None:
            self.public_request_retries_count = public_request_retries_count
        if public_request_retries_timeout is not None:
            self.public_request_retries_timeout = public_request_retries_timeout
        if session_retry_total is not None:
            self.session_retry_total = session_retry_total
        if session_retry_backoff_factor is not None:
            self.session_retry_backoff_factor = session_retry_backoff_factor
        if session_retry_statuses is not None:
            self.session_retry_statuses = list(session_retry_statuses)
        if public_transport is not None:
            self.public_transport = self._normalize_public_transport(public_transport)
        if public_transport_impersonate is not None:
            self.public_transport_impersonate = public_transport_impersonate
        if public_transport is not None or public_transport_impersonate is not None:
            self.public_user_agent = self._default_public_user_agent(
                self.public_transport, self.public_transport_impersonate
            )
            self.public.headers["User-Agent"] = self.public_user_agent

        self._configure_public_session_retry()
        self._configure_private_session_retry()

        if self.settings is not None:
            self.settings.update(
                {
                    "request_timeout": self.request_timeout,
                    "public_request_retries_count": self.public_request_retries_count,
                    "public_request_retries_timeout": self.public_request_retries_timeout,
                    "session_retry_total": self.session_retry_total,
                    "session_retry_backoff_factor": self.session_retry_backoff_factor,
                    "session_retry_statuses": self.session_retry_statuses,
                    "public_transport": self.public_transport,
                    "public_transport_impersonate": self.public_transport_impersonate,
                }
            )
        return True

    def set_device(self, device: Dict = None, reset: bool = False) -> bool:
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
        device = device or {}
        self.device_settings = dict(config.DEVICE_SETTINGS)
        self.device_settings.update(device)
        seed = None
        if self.settings:
            uuids = self.settings.get("uuids") or {}
            seed = uuids.get("uuid")
        self.set_app(seed=seed)
        self.set_user_agent()
        if reset:
            self.set_uuids({})
        return True

    def set_app(self, app: Union[str, Dict] = None, seed: str = None) -> bool:
        """
        Helper to set app version settings

        Parameters
        ----------
        app: Union[str, Dict], optional
            App version string or settings dict
        seed: str, optional
            Seed used for stable app selection

        Returns
        -------
        bool
            A boolean value
        """
        app_keys = ("app_version", "version_code", "bloks_versioning_id")
        if not getattr(self, "device_settings", None):
            self.device_settings = dict(config.DEVICE_SETTINGS)
        if not config.APP_SETTINGS:
            raise ValueError("APP_SETTINGS is empty")
        override_app_version = bool(getattr(self, "override_app_version", False))

        def apply_settings(app_settings: Dict) -> None:
            for key in app_keys:
                val = app_settings.get(key)
                if val:
                    self.device_settings[key] = val

        def pick_by_seed() -> Dict:
            app_values = list(config.APP_SETTINGS.values())
            if seed:
                digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
                idx = int(digest, 16) % len(app_values)
                return app_values[idx]
            return random.choice(app_values)

        def default_settings() -> Dict:
            return config.APP_SETTINGS.get(config.DEFAULT_APP_VERSION) or pick_by_seed()

        if app:
            if isinstance(app, str):
                matched = config.APP_SETTINGS.get(app)
                if not matched:
                    raise ValueError(f"Unknown app_version: {app}")
                apply_settings(matched)
            else:
                apply_settings(dict(app))
        else:
            app_version = self.device_settings.get("app_version")
            matched = config.APP_SETTINGS.get(app_version) if app_version else None
            if matched and not override_app_version:
                apply_settings(matched)
            else:
                if override_app_version or not app_version:
                    apply_settings(default_settings())

        if override_app_version:
            self.set_user_agent()
        self.bloks_versioning_id = self.device_settings.get("bloks_versioning_id")
        if self.settings is not None:
            self.settings["device_settings"] = self.device_settings
        return True

    def set_user_agent(self, user_agent: str = "", reset: bool = False) -> bool:
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
        data = dict(self.device_settings, locale=self.locale)
        self.user_agent = user_agent or config.USER_AGENT_BASE.format(**data)
        # self.private.headers.update({"User-Agent": self.user_agent})  # changed in base_headers
        self.settings["user_agent"] = self.user_agent
        if reset:
            self.set_uuids({})
            # self.settings = self.get_settings()
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
        self.android_device_id = uuids.get("android_device_id", self.generate_android_device_id())
        self.request_id = uuids.get("request_id", self.generate_uuid())
        self.tray_session_id = uuids.get("tray_session_id", self.generate_uuid())
        # self.device_id = uuids.get("device_id", self.generate_uuid())
        self.settings["uuids"] = uuids
        return True

    def generate_uuid(self, prefix: str = "", suffix: str = "") -> str:
        """
        Helper to generate uuids

        Returns
        -------
        str
            A stringified UUID
        """
        return f"{prefix}{uuid.uuid4()}{suffix}"

    def generate_mutation_token(self) -> str:
        """
        Token used when DM sending and upload media

        Returns
        -------
        str
            A stringified int
        """
        return str(random.randint(6800011111111111111, 6800099999999999999))

    def generate_android_device_id(self) -> str:
        """
        Helper to generate Android Device ID

        Returns
        -------
        str
            A random android device id
        """
        return "android-%s" % hashlib.sha256(str(time.time()).encode()).hexdigest()[:16]

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

    def with_extra_data(self, data: Dict) -> Dict:
        """
        Helper to get extra data

        Returns
        -------
        Dict
            A dictionary of default data
        """
        return self.with_default_data(
            {
                "phone_id": self.phone_id,
                "_uid": str(self.user_id),
                "guid": self.uuid,
                **data,
            }
        )

    def with_default_data(self, data: Dict) -> Dict:
        """
        Helper to get default data

        Returns
        -------
        Dict
            A dictionary of default data
        """
        return {
            "_uuid": self.uuid,
            # "_uid": str(self.user_id),
            # "_csrftoken": self.token,
            "device_id": self.android_device_id,
            **data,
        }

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
            base64.b64encode(hmac.new(key.encode("ascii"), data.encode("ascii"), digestmod=hashlib.sha256).digest()),
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

    def logout(self) -> bool:
        result = self.private_request("accounts/logout/", {"one_tap_app_login": True})
        if result["status"] == "ok":
            self._clear_session_state(
                clear_authorization_data=True,
                clear_last_login=True,
                reset_relogin_attempt=True,
                clear_authorization_header=True,
                clear_private_cookies=True,
                clear_public_cookies=True,
            )
            return True
        return False

    def parse_authorization(self, authorization) -> dict:
        """Parse authorization header"""
        if not authorization:
            return {}
        try:
            b64part = authorization.rsplit(":", 1)[-1]
            if not b64part:
                return {}
            return json.loads(base64.b64decode(b64part))
        except Exception as e:
            self.logger.exception(e)
        return {}

    @property
    def authorization(self) -> str:
        """Build authorization header
        Example: Bearer IGT:2:eaW9u.....aWQiOiI0NzM5=
        """
        if self.authorization_data:
            b64part = base64.b64encode(dumps(self.authorization_data).encode()).decode()
            return f"Bearer IGT:2:{b64part}"
        return ""

    def dump_instaman(self):
        # Example format: helen9151hernandez:AgcXb0GJhAP|Instagram 200.0.0.24.121 Android...
        # Long string with user credentials and device info
        uuids = ";".join(
            [
                self.android_device_id.replace("android-", ""),
                self.uuid,
                self.phone_id,
                self.client_session_id,
            ]
        )
        headers = {
            "X-MID": self.mid,
            "IG-U-DS-USER-ID": self.user_id,
            "IG-U-RUR": self.ig_u_rur,
            "Authorization": self.authorization,
            "X-IG-WWW-Claim": self.ig_www_claim or "0",
        }
        headers = ";".join([f"{key}={value}" for key, value in headers.items()])
        return f"{self.username}:{self.password}|{self.user_agent}|{uuids}|{headers};||"
