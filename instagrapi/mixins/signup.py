import json
import random
import re
import secrets
import time
import warnings
from typing import Any, Dict, Iterable, Optional
from urllib.parse import urlsplit
from uuid import uuid4

from instagrapi.exceptions import (
    AgeEligibilityError,
    CaptchaChallengeRequired,
    ChallengeRequired,
    ClientError,
    EmailInvalidError,
    EmailNotAvailableError,
    EmailVerificationSendError,
    FeedbackRequired,
    SignupSpamError,
)
from instagrapi.extractors import extract_user_short
from instagrapi.mixins.challenge import ChallengeChoice
from instagrapi.types import UserShort
from instagrapi.utils.serialization import dumps

CHOICE_EMAIL = 1
LEGACY_SIGNUP_WARNING = (
    "signup() uses Instagram's legacy account-create flow and should be treated as experimental. "
    "Modern Instagram signup often requires additional official-app device trust checks that instagrapi does not currently generate."
)
CAA_REG_GRAPHQL_DOC_ID = "356548512614739681018024088968"
CAA_REG_CONTACTPOINT_DOC_ID = "253360298312778871684788706414"
CAA_REG_CONTACTPOINT_APPS = {
    "com.bloks.www.bloks.caa.reg.contactpoint_phone",
    "com.bloks.www.bloks.caa.reg.contactpoint_email",
    "com.bloks.www.bloks.caa.reg.transition",
}
CAA_REG_FLOW_INFO = {"flow_name": "new_to_family_ig_default", "flow_type": "ntf"}
CAA_REG_OFFLINE_EXPERIMENT_GROUP = "caa_iteration_v3_perf_ig_4"
CAA_REG_LAYERED_HOMEPAGE_EXPERIMENT_GROUP = "Deploy: Not in Experiment"
CAA_REG_VM_TOKEN_RE = re.compile(r'\(|\)|"(?:\\.|[^"\\])*"|[^\s()]+')
CAA_REG_REJECTION_MESSAGE_KEYWORDS = (
    "sorry",
    "went wrong",
    "try again",
    "not eligible",
    "unavailable",
    "too many",
    "invalid",
    "error",
    "problem",
)
CAA_REG_GENERIC_REJECTION_RE = re.compile(
    r"(?:We(?:'|\\'|’)re|We are) sorry, but something went wrong\. Please try again\.",
    re.IGNORECASE,
)


class SignUpMixin:
    waterfall_id = str(uuid4())
    adid = str(uuid4())
    wait_seconds = 5

    @staticmethod
    def _safe_challenge_api_path(api_path: str, field_name: str = "api_path") -> str:
        if not isinstance(api_path, str) or not api_path:
            raise ClientError(f"Malformed challenge data from Instagram (missing {field_name}).")
        parts = urlsplit(api_path)
        has_control_chars = any(ord(char) < 32 or ord(char) == 127 for char in api_path)
        if (
            parts.scheme
            or parts.netloc
            or not api_path.startswith("/")
            or api_path.startswith("//")
            or "\\" in api_path
            or has_control_chars
        ):
            raise ClientError(f"Unsafe challenge path from Instagram: {field_name}")
        return api_path

    def _challenge_url(self, api_path: str, prefix: str = "", field_name: str = "api_path") -> str:
        return f"https://i.instagram.com{prefix}{self._safe_challenge_api_path(api_path, field_name)}"

    def _caa_string_values(self, value: Any) -> Iterable[str]:
        if isinstance(value, dict):
            for item in value.values():
                yield from self._caa_string_values(item)
        elif isinstance(value, list):
            for item in value:
                yield from self._caa_string_values(item)
        elif isinstance(value, str):
            yield value

    def _caa_clean_rejection_message(self, value: str) -> Optional[str]:
        text = re.sub(r"\s+", " ", value.strip())
        if not text:
            return None
        generic_match = CAA_REG_GENERIC_REJECTION_RE.search(text)
        if generic_match:
            return generic_match.group(0).replace("\\'", "'")
        if len(text) > 300 or text.startswith(("{", "[", "(")):
            return None
        lower = text.lower()
        if not any(keyword in lower for keyword in CAA_REG_REJECTION_MESSAGE_KEYWORDS):
            return None
        if any(marker in lower for marker in ("bk.action", "bloks", "optimistic vf", "tr62rb")):
            return None
        return text

    def _caa_extract_rejection_message(self, response: Any) -> Optional[str]:
        payloads = [response]
        seen_payloads = set()
        for payload in payloads:
            payload_id = id(payload)
            if payload_id in seen_payloads:
                continue
            seen_payloads.add(payload_id)
            for value in self._caa_string_values(payload):
                message = self._caa_clean_rejection_message(value)
                if message:
                    return message
                if "bloks_bundle_action" in value or "bloks_payload" in value or "registration_response" in value:
                    for decoded in self._caa_json_objects_from_string(value):
                        if isinstance(decoded, (dict, list)):
                            payloads.append(decoded)
        return None

    def _caa_parse_vm_atom(self, token: str) -> Any:
        if token.startswith('"') and token.endswith('"'):
            try:
                return json.loads(token)
            except json.JSONDecodeError:
                return token[1:-1]
        if token == "true":  # nosec B105
            return True
        if token == "false":  # nosec B105
            return False
        if token == "null":  # nosec B105
            return None
        try:
            return int(token)
        except ValueError:
            return token

    def _caa_parse_vm(self, value: str) -> list:
        root = []
        stack = [root]
        for token in CAA_REG_VM_TOKEN_RE.findall(value):
            if token == "(":  # nosec B105
                child = []
                stack[-1].append(child)
                stack.append(child)
                continue
            if token == ")":  # nosec B105
                if len(stack) > 1:
                    stack.pop()
                continue
            stack[-1].append(self._caa_parse_vm_atom(token))
        return root

    def _caa_iter_vm_lists(self, value: Any) -> Iterable[list]:
        if isinstance(value, list):
            yield value
            for item in value:
                yield from self._caa_iter_vm_lists(item)

    def _caa_extract_dkc_maps(self, value: str) -> Iterable[Dict[str, Any]]:
        if "(dkc" not in value:
            return
        try:
            parsed = self._caa_parse_vm(value)
        except Exception:
            return
        for item in self._caa_iter_vm_lists(parsed):
            if (
                len(item) >= 3
                and item[0] == "f4i"
                and isinstance(item[1], list)
                and isinstance(item[2], list)
                and item[1][:1] == ["dkc"]
                and item[2][:1] == ["dkc"]
            ):
                keys = item[1][1:]
                values = item[2][1:]
                yield {
                    key: values[index] for index, key in enumerate(keys) if isinstance(key, str) and index < len(values)
                }

    def _caa_json_objects_from_string(self, value: str) -> Iterable[Any]:
        stripped = value.strip()
        if stripped.startswith(("{", "[")):
            try:
                yield json.loads(stripped)
            except json.JSONDecodeError:
                pass
        decoder = json.JSONDecoder()
        index = 0
        while True:
            index = value.find('"{', index)
            if index < 0:
                break
            try:
                decoded, consumed = decoder.raw_decode(value[index:])
            except json.JSONDecodeError:
                index += 2
                continue
            if isinstance(decoded, str) and decoded.startswith(("{", "[")):
                try:
                    yield json.loads(decoded)
                except json.JSONDecodeError:
                    pass
            index += max(consumed, 1)

    def _caa_extract_registration_response(self, value: Any) -> Optional[Dict]:
        if isinstance(value, dict):
            if "registration_response" in value:
                response = value["registration_response"]
                if isinstance(response, str):
                    try:
                        parsed = json.loads(response)
                    except json.JSONDecodeError:
                        return None
                    # Only a dict is usable downstream (state["registration_response"]
                    # is read with .get("created_user")); a JSON array/scalar from an
                    # error payload must not flow through as a truthy non-dict.
                    return parsed if isinstance(parsed, dict) else None
                if isinstance(response, dict):
                    return response
            if value.get("account_created") is not None and "created_user" in value:
                return value
            for item in value.values():
                response = self._caa_extract_registration_response(item)
                if response:
                    return response
        elif isinstance(value, list):
            for item in value:
                response = self._caa_extract_registration_response(item)
                if response:
                    return response
        return None

    def _caa_extract_state(self, response: Dict) -> Dict:
        state = {}
        payloads = [response]
        for payload in list(payloads):
            for value in self._caa_string_values(payload):
                if "bloks_bundle_action" in value or "bloks_payload" in value or "registration_response" in value:
                    for decoded in self._caa_json_objects_from_string(value):
                        if isinstance(decoded, (dict, list)):
                            payloads.append(decoded)
        for payload in payloads:
            registration_response = self._caa_extract_registration_response(payload)
            if registration_response:
                state["registration_response"] = registration_response
            for value in self._caa_string_values(payload):
                if not any(key in value for key in ("reg_info", "reg_context", "email_token", "created_user")):
                    continue
                for dkc_map in self._caa_extract_dkc_maps(value) or []:
                    for key in ("reg_info", "reg_context", "email_token", "created_user_id", "created_userid"):
                        if key not in dkc_map or dkc_map[key] in (None, ""):
                            continue
                        if key in ("reg_info", "reg_context", "email_token") and not isinstance(dkc_map[key], str):
                            continue
                        state[key] = dkc_map[key]
                for decoded in self._caa_json_objects_from_string(value):
                    registration_response = self._caa_extract_registration_response(decoded)
                    if registration_response:
                        state["registration_response"] = registration_response
        return state

    def _caa_update_state(self, state: Dict, response: Dict) -> Dict:
        for key, value in self._caa_extract_state(response).items():
            if value not in (None, ""):
                state[key] = value
        return state

    def _caa_initial_state(self, email: str = "") -> Dict:
        device_id = getattr(self, "android_device_id", "") or f"android-{secrets.token_hex(8)}"
        family_device_id = getattr(self, "phone_id", "") or str(uuid4())
        qe_device_id = getattr(self, "uuid", "") or str(uuid4())
        waterfall_id = getattr(self, "waterfall_id", "") or str(uuid4())
        machine_id = getattr(self, "mid", None) or ""
        registration_flow_id = str(uuid4())
        reg_info = {
            "first_name": None,
            "last_name": None,
            "full_name": None,
            "contactpoint": email or None,
            "ar_contactpoint": None,
            "contactpoint_type": "email" if email else None,
            "confirmation_code": None,
            "birthday": None,
            "encrypted_password": None,  # nosec B105
            "username": None,
            "username_prefill": None,
            "device_id": device_id,
            "ig4a_qe_device_id": qe_device_id,
            "family_device_id": family_device_id,
            "machine_id": machine_id or None,
            "registration_flow_id": registration_flow_id,
            "caa_reg_flow_source": "login_home_native_integration_point",
            "is_caa_perf_enabled": True,
            "is_preform": True,
            "screen_visited": [],
        }
        return {
            "device_id": device_id,
            "family_device_id": family_device_id,
            "qe_device_id": qe_device_id,
            "waterfall_id": waterfall_id,
            "machine_id": machine_id,
            "flow_info": dumps(CAA_REG_FLOW_INFO),
            "reg_info": dumps(reg_info),
        }

    def _caa_common_client_input(self, state: Dict) -> Dict:
        return {
            "aac": dumps(
                {
                    "aac_init_timestamp": int(time.time()),
                    "aacjid": str(uuid4()),
                    "aaccs": "",
                }
            ),
            "device_id": state["device_id"],
            "family_device_id": state["family_device_id"],
            "machine_id": state.get("machine_id", ""),
            "lois_settings": {"lois_token": ""},  # nosec B105
            "cloud_trust_token": None,  # nosec B105
            "zero_balance_state": "",
            "network_bssid": None,
            "qe_device_id": state["qe_device_id"],
        }

    def _caa_network_info(self) -> Dict:
        return {
            "active_subscriptions_info": None,
            "default_subscription_info": {
                "network_type": 13,
                "is_data_roaming": 1,
                "is_esim": None,
                "is_gsm_roaming": 0,
                "is_sim_sms_capable": None,
                "is_mobile_data_enabled": 1,
                "sim_carrier_id": 1,
                "sim_carrier_id_name": "T-Mobile - US",
                "sim_state": 5,
                "sim_operator": "310270",
                "sim_operator_name": "T-Mobile",
                "signal_strength": 4,
                "group_id_level_1": None,
                "network_operator": "310260",
            },
            "is_airplane_mode": 0,
            "is_active_network_cellular": 0,
            "is_device_sms_capable": 1,
            "sim_count": 1,
            "is_wifi": 1,
        }

    def _caa_password(self, password: str) -> str:
        # Version 0 (plaintext envelope) is intentional here: the current Android
        # CAA registration flow sends ``encrypted_password`` as ``#PWD_INSTAGRAM:0:``,
        # not the ``:4:`` sealed-box used by login/legacy signup. Verified against a
        # current Android app capture. Do not "fix" this to ``password_encrypt``.
        return f"#PWD_INSTAGRAM:0:{int(time.time())}:{password}"

    def _caa_reg_info_value(self, state: Dict, key: str, default: Any = None) -> Any:
        try:
            reg_info = json.loads(state.get("reg_info") or "{}")
        except json.JSONDecodeError:
            return default
        return reg_info.get(key, default)

    def _caa_common_server_params(self, state: Dict, current_step: int = 0) -> Dict:
        server_params = {
            "event_request_id": str(uuid4()),
            "is_from_logged_out": 0,
            "layered_homepage_experiment_group": CAA_REG_LAYERED_HOMEPAGE_EXPERIMENT_GROUP,
            "device_id": state["device_id"],
            "login_surface": "login_home",
            "waterfall_id": state["waterfall_id"],
            "INTERNAL__latency_qpl_instance_id": random.randint(100000000000000, 999999999999999),
            "flow_info": state["flow_info"],
            "is_platform_login": 0,
            "login_entry_point": "logged_out",
            "INTERNAL__latency_qpl_marker_id": 36707139,
            "reg_info": state["reg_info"],
            "family_device_id": state["family_device_id"],
            "offline_experiment_group": CAA_REG_OFFLINE_EXPERIMENT_GROUP,
            "access_flow_version": "pre_mt_behavior",
            "is_from_logged_in_switcher": 0,
            "current_step": current_step,
            "qe_device_id": state["qe_device_id"],
        }
        if state.get("reg_context"):
            server_params["reg_context"] = state["reg_context"]
        return server_params

    def _caa_params(
        self,
        state: Dict,
        current_step: int = 0,
        client_input_params: Optional[Dict] = None,
        server_params: Optional[Dict] = None,
    ) -> Dict:
        client_inputs = self._caa_common_client_input(state)
        client_inputs.update(client_input_params or {})
        servers = self._caa_common_server_params(state, current_step=current_step)
        servers.update(server_params or {})
        servers = {key: value for key, value in servers.items() if value is not None}
        return {
            "client_input_params": client_inputs,
            "server_params": servers,
        }

    def caa_reg_graphql(
        self,
        app: str,
        state: Optional[Dict] = None,
        current_step: int = 0,
        client_input_params: Optional[Dict] = None,
        server_params: Optional[Dict] = None,
        client_doc_id: Optional[str] = None,
    ) -> Dict:
        state = state or self._caa_initial_state()
        params = self._caa_params(
            state,
            current_step=current_step,
            client_input_params=client_input_params,
            server_params=server_params,
        )
        doc_id = client_doc_id or (
            CAA_REG_CONTACTPOINT_DOC_ID if app in CAA_REG_CONTACTPOINT_APPS else CAA_REG_GRAPHQL_DOC_ID
        )
        return self.bloks_graphql_app(
            app,
            params,
            client_doc_id=doc_id,
            infra_device_id=state["qe_device_id"],
        )

    def caa_reg_async_action(
        self,
        action: str,
        state: Optional[Dict] = None,
        current_step: int = 0,
        client_input_params: Optional[Dict] = None,
        server_params: Optional[Dict] = None,
    ) -> Dict:
        state = state or self._caa_initial_state()
        params = self._caa_params(
            state,
            current_step=current_step,
            client_input_params=client_input_params,
            server_params=server_params,
        )
        return self.bloks_async_action(action, params, domain="b.i.instagram.com")

    def signup_caa_email(
        self,
        username: str,
        password: str,
        email: str,
        full_name: str = "",
        year: int = None,
        month: int = None,
        day: int = None,
        attempts: int = 10,
        wait_seconds: Optional[int] = None,
    ) -> UserShort:
        if not email:
            raise ClientError("email is required for CAA signup")
        year = year or random.randint(1980, 1995)
        month = month or random.randint(1, 12)
        day = day or random.randint(1, 28)
        wait_seconds = self.wait_seconds if wait_seconds is None else wait_seconds
        state = self._caa_initial_state(email=email)

        response = self.caa_reg_graphql(
            "com.bloks.www.bloks.caa.reg.aymh_create_account_button.async",
            state=state,
            current_step=0,
            client_input_params={"accounts_list": [], "device_emails": [], "device_phone_numbers": []},
            server_params={"reg_flow_source": "login_home_native_integration_point", "entrypoint": "login_home"},
        )
        self._caa_update_state(state, response)
        response = self.caa_reg_async_action(
            "com.bloks.www.bloks.caa.reg.async.expose_ntm_experiment.async",
            state=state,
            current_step=0,
            client_input_params={"si_device_param_network_info": ""},
        )
        self._caa_update_state(state, response)
        response = self.caa_reg_graphql(
            "com.bloks.www.bloks.caa.reg.async.contactpoint_prefill.async",
            state=state,
            current_step=0,
            client_input_params={"accounts_list": [], "si_device_param_network_info": ""},
        )
        self._caa_update_state(state, response)
        response = self.caa_reg_graphql(
            "com.bloks.www.bloks.caa.reg.contactpoint_phone",
            state=state,
            current_step=0,
            server_params={"INTERNAL_INFRA_screen_id": str(uuid4())},
        )
        self._caa_update_state(state, response)
        response = self.caa_reg_graphql(
            "com.bloks.www.bloks.caa.reg.contactpoint_email",
            state=state,
            current_step=0,
            server_params={
                "root_screen_id": "CAA_REG_CONTACT_POINT_PHONE",
                "INTERNAL_INFRA_screen_id": str(uuid4()),
                "reg_context": None,
            },
        )
        self._caa_update_state(state, response)
        response = self.caa_reg_async_action(
            "com.bloks.www.bloks.caa.reg.async.contactpoint_email_new.async",
            state=state,
            current_step=0,
            client_input_params={
                "accounts_list": [],
                "email": email,
                "email_prefilled": 0,
                "confirmed_cp_and_code": {},
                "is_from_device_emails": 0,
                "prefetch_version": 11,
                "si_device_param_network_info": self._caa_network_info(),
                "block_store_machine_id": "",
                "fb_ig_device_id": [],
            },
            server_params={
                "cp_funnel": 0,
                "cp_source": 0,
                "prefetch_on_field": 1,
                "text_input_id": random.randint(100000000000000, 999999999999999),
                "reg_context": None,
            },
        )
        self._caa_update_state(state, response)
        response = self.caa_reg_async_action(
            "com.bloks.www.bloks.caa.reg.send_confirmation_email.async",
            state=state,
            current_step=0,
            client_input_params={"email_token": state.get("email_token", "")},
            server_params={"is_from_unified_cp_screen": False, "is_direct_from_conf": False, "accounts_list": []},
        )
        self._caa_update_state(state, response)

        code = ""
        for attempt in range(attempts):
            code = self.challenge_code_handler(username, CHOICE_EMAIL)
            if code:
                break
            # Skip the backoff after the final attempt: no further poll follows it.
            if wait_seconds and attempt < attempts - 1:
                time.sleep(wait_seconds * (attempt + 1))
        if not code:
            raise ClientError("email confirmation code is required for CAA signup")

        response = self.caa_reg_graphql(
            "com.bloks.www.bloks.caa.reg.confirmation.async",
            state=state,
            current_step=3,
            client_input_params={"code": code, "confirmed_cp_and_code": {"contactpoint": email, "code": code}},
            server_params={"text_input_id": str(uuid4()), "wa_timer_id": str(uuid4())},
        )
        self._caa_update_state(state, response)
        response = self.caa_reg_graphql(
            "com.bloks.www.bloks.caa.reg.password.async",
            state=state,
            current_step=4,
            client_input_params={
                "encrypted_password": self._caa_password(password),
                "spi_action": 1,
                "whatsapp_installed_on_client": False,
                "safetynet_token": self._caa_reg_info_value(state, "safetynet_token", ""),
                "safetynet_response": self._caa_reg_info_value(
                    state,
                    "safetynet_response",
                    "GOOGLE_PLAY_UNAVAILABLE: SERVICE_INVALID",
                ),
                "system_permissions_status": {
                    "READ_CONTACTS": "DENIED",
                    "GET_ACCOUNTS": "DENIED",
                    "READ_PHONE_STATE": "DENIED",
                    "READ_PHONE_NUMBERS": "DENIED",
                },
            },
            server_params={"flow_modifier": state["flow_info"], "si_device_param_network_info": ""},
        )
        self._caa_update_state(state, response)
        birthday = f"{day:02d}-{month:02d}-{year:04d}"
        response = self.caa_reg_graphql(
            "com.bloks.www.bloks.caa.reg.birthday.async",
            state=state,
            current_step=6,
            client_input_params={
                "accounts_list": [],
                "client_timezone": getattr(self, "timezone_offset", 0),
                "birthday_or_current_date_string": birthday,
                "birthday_timestamp": int(time.time()),
                "os_age_range": "o18",
                "should_skip_youth_tos": False,
                "is_youth_regulation_flow_complete": False,
            },
            server_params={"si_device_param_network_info": ""},
        )
        self._caa_update_state(state, response)
        response = self.caa_reg_async_action(
            "com.bloks.www.bloks.caa.reg.name_vtwo.async",
            state=state,
            current_step=7,
            client_input_params={"accounts_list": [], "name": full_name or username},
            server_params={"si_device_param_network_info": ""},
        )
        self._caa_update_state(state, response)
        response = self.caa_reg_graphql(
            "com.bloks.www.bloks.caa.reg.username.async",
            state=state,
            current_step=8,
            client_input_params={"validation_text": username},
            server_params={
                "action": 1,
                "post_tos": 0,
                "text_input_id": random.randint(100000000000000, 999999999999999),
                "suggestions_container_id": random.randint(100000000000000, 999999999999999),
                "screen_id": random.randint(100000000000000, 999999999999999),
                "input_id": random.randint(100000000000000, 999999999999999),
            },
        )
        self._caa_update_state(state, response)
        response = self.caa_reg_graphql(
            "com.bloks.www.bloks.caa.reg.create.account.async",
            state=state,
            current_step=9,
            client_input_params={
                "passkey_eligible_device": 0,
                "ck_error": "",
                "failed_birthday_year_count": "",
                "headers_last_infra_flow_id": "",
                "ig_partially_created_account_nonce_expiry": 0,
                "should_ignore_existing_login": 0,
                "reached_from_tos_screen": 1,
                "ig_partially_created_account_nonce": "",
                "has_dismissed_suma_pre_conf": 0,
                "ck_nonce": "",
                "force_sessionless_nux_experience": 0,
                "ig_partially_created_account_user_id": 0,
                "ck_id": "",
                "no_contact_perm_email_oauth_token": "",  # nosec B105
                "encrypted_msisdn": "",
            },
            server_params={
                "sa_prefetch_callback_id": "",
                "should_ignore_suma_check": 0,
                "bloks_controller_source": "bk_caa_reg_tos_screen",
                "app_id": 0,
            },
        )
        self._caa_update_state(state, response)
        registration_response = state.get("registration_response")
        if not registration_response or not registration_response.get("created_user"):
            rejection_message = self._caa_extract_rejection_message(response)
            if rejection_message:
                raise ClientError(f"CAA signup was rejected by Instagram: {rejection_message}")
            raise ClientError("CAA signup did not return created_user")
        if registration_response.get("account_created") is False:
            raise ClientError(f"CAA signup did not create an account: {registration_response}")
        return extract_user_short(registration_response["created_user"])

    def signup(
        self,
        username: str,
        password: str,
        email: str = "",
        phone_number: str = "",
        full_name: str = "",
        year: int = None,
        month: int = None,
        day: int = None,
    ) -> UserShort:
        if not (email or phone_number):
            raise ClientError("Use email or phone_number for signup")
        warnings.warn(LEGACY_SIGNUP_WARNING, RuntimeWarning, stacklevel=2)

        self.get_signup_config()
        kwargs = {
            "username": username,
            "password": password,
            "full_name": full_name,
            "year": year,
            "month": month,
            "day": day,
        }

        if email:
            check = self.check_email(email)
            if not check.get("valid"):
                raise EmailInvalidError(f"Email not valid: {check.get('error_title', check)}")
            if not check.get("available"):
                raise EmailNotAvailableError(f"Email not available: {check.get('feedback_message', check)}")
            sent = self.send_verify_email(email)
            if not sent.get("email_sent"):
                raise EmailVerificationSendError(f"Failed to send verification email: {sent}")

            # Date of Birth (DOB) Age Eligibility Check
            if year and month and day:
                age_check_result = self.check_age_eligibility(year, month, day)
                # IG returns "eligible_to_register"; keep "eligible" as a fallback
                eligible = age_check_result.get("eligible_to_register", age_check_result.get("eligible"))
                if not eligible:
                    raise AgeEligibilityError(f"Account not eligible based on age criteria: {age_check_result}")

            # send code confirmation
            code = ""
            for attempt in range(1, 11):
                code = self.challenge_code_handler(username, CHOICE_EMAIL)
                if code:
                    break
                time.sleep(self.wait_seconds * attempt)
            print(f'Enter code "{code}" for {username} ({attempt} attempts, by {self.wait_seconds} seconds)')
            signup_code = self.check_confirmation_code(email, code).get("signup_code")
            kwargs["email"] = email
            kwargs["signup_code"] = signup_code

        if phone_number and not email:
            kwargs["phone_number"] = phone_number
            check = self.check_phone_number(phone_number)
            if check.get("status") != "ok" and not check.get("valid"):
                raise ClientError(f"Phone number not valid ({check})")
            sms = self.send_signup_sms_code(phone_number)
            if sms.get("status") != "ok":
                raise ClientError(f"Error when verify phone number ({sms})")
            attempt = 1
            if "verification_code" in sms:
                code = sms["verification_code"]
            else:
                code = ""
                for attempt in range(1, 11):
                    code = self.challenge_code_handler(username, ChallengeChoice.SMS)
                    if code:
                        break
                    time.sleep(self.wait_seconds * attempt)
            print(f'Enter code "{code}" for {username} ({attempt} attempts, by {self.wait_seconds} seconds)')
            kwargs["phone_code"] = code

        retries = 0
        while retries < 3:
            data = self.accounts_create(**kwargs)
            if data.get("message") != "challenge_required":
                break
            if self.challenge_flow(data["challenge"], phone_number=phone_number, username=username):
                kwargs.update({"suggestedUsername": "", "sn_result": "MLA"})
            retries += 1
        return extract_user_short(data["created_user"])

    def get_signup_config(self) -> dict:
        return self.private_request(
            "consent/get_signup_config/",
            params={"guid": self.uuid, "main_account_selected": False},
        )

    def check_email(self, email) -> dict:
        """Check available (free, not registred) email"""
        return self.private_request(
            "users/check_email/",
            {
                "android_device_id": self.android_device_id,
                "login_nonce_map": "{}",
                "login_nonces": "[]",
                "email": email,
                "qe_id": str(uuid4()),
                "waterfall_id": self.waterfall_id,
            },
        )

    def check_username(self, username):
        return self.private_request("users/check_username/", data={"username": username, "_uuid": self.uuid})

    def check_phone_number(self, phone_number: str):
        return self.private_request(
            "accounts/check_phone_number/",
            data={
                "phone_id": self.phone_id,
                "login_nonce_map": "{}",
                "phone_number": phone_number.replace(" ", "+"),
                "guid": self.uuid,
                "device_id": self.android_device_id,
                "prefill_shown": "False",
            },
        )

    def send_signup_sms_code(self, phone_number: str):
        return self.private_request(
            "accounts/send_signup_sms_code/",
            data={
                "phone_id": self.phone_id,
                "phone_number": phone_number.replace(" ", "+"),
                "guid": self.uuid,
                "device_id": self.android_device_id,
                "android_build_type": "release",
                "waterfall_id": self.waterfall_id,
            },
        )

    def send_verify_email(self, email) -> dict:
        """Send request to receive code to email"""
        return self.private_request(
            "accounts/send_verify_email/",
            {
                "phone_id": self.phone_id,
                "device_id": self.android_device_id,
                "email": email,
                "waterfall_id": self.waterfall_id,
                "auto_confirm_only": "false",
            },
        )

    def check_confirmation_code(self, email, code) -> dict:
        """Enter code from email"""
        return self.private_request(
            "accounts/check_confirmation_code/",
            {
                "code": code,
                "device_id": self.android_device_id,
                "email": email,
                "waterfall_id": self.waterfall_id,
            },
        )

    def check_age_eligibility(self, year, month, day):
        return self.private_request(
            "consent/check_age_eligibility/",
            data={"_csrftoken": self.token, "day": day, "year": year, "month": month},
            with_signature=False,
        ).json()

    def accounts_create(
        self,
        username: str,
        password: str,
        email: str = "",
        signup_code: str = "",
        phone_number: str = "",
        phone_code: str = "",
        full_name: str = "",
        year: int = None,
        month: int = None,
        day: int = None,
        **kwargs,
    ) -> dict:
        if not (email or phone_number):
            raise ClientError("Use email or phone_number for signup")

        # timestamp = datetime.now().strftime("%s")  # Unused variable
        data = {
            "jazoest": str(int(random.randint(22300, 22399))),  # "22341",
            "tos_version": "row",
            "suggestedUsername": "",
            "sn_result": "",
            "do_not_auto_login_if_credentials_match": "false",
            "phone_id": self.phone_id,
            "enc_password": self.password_encrypt(password),
            "username": str(username),
            "first_name": str(full_name),
            "adid": self.adid,
            "guid": self.uuid,
            "day": day,
            "month": month,
            "year": year,
            "device_id": self.android_device_id,
            "_uuid": self.uuid,
            "waterfall_id": self.waterfall_id,
            "one_tap_opt_in": "true",
            **kwargs,
        }
        if email and not phone_number:
            endpoint = "accounts/create/"
            domain = "www.instagram.com"
            data.update(
                {
                    "email": email,
                    "force_sign_up_code": signup_code,
                    "qs_stamp": "",
                    "sn_nonce": bytes(f"{email}|{str(int(time.time()))}|{secrets.token_bytes(24)}", "utf-8"),
                }
            )
        else:
            endpoint = "accounts/create_validated/"
            domain = None
            data.update(
                {
                    "phone_number": phone_number,
                    "verification_code": phone_code,
                    "force_sign_up_code": "",
                    "has_sms_consent": "true",
                }
            )
            if data.get("logged_in_user_id"):
                data["is_secondary_account_creation"] = "true"
        try:
            return self.private_request(endpoint, data, domain=domain)
        except FeedbackRequired as exc:
            if getattr(exc, "spam", False):
                details = vars(exc).copy()
                details.pop("message", None)
                raise SignupSpamError(
                    "Instagram rejected the legacy signup flow as spam. "
                    "Modern app signup uses additional device trust checks that instagrapi does not currently generate.",
                    **details,
                ) from exc
            raise

    def challenge_flow(
        self,
        data,
        phone_number: str = "",
        username: str = "",
        wait_seconds: Optional[int] = None,
        attempts: int = 10,
    ) -> bool:
        data = self.challenge_api(data)
        wait_seconds = self.wait_seconds if wait_seconds is None else wait_seconds
        username = username or getattr(self, "username", "")

        for _ in range(10):
            if data.get("status") == "ok":
                return True
            if data.get("message") == "challenge_required":
                data = self.challenge_captcha(data["challenge"])
                continue
            if data.get("challengeType") == "SubmitPhoneNumberForm":
                if not phone_number:
                    raise ClientError("phone_number is required for signup SMS challenge")
                data = self.challenge_submit_phone_number(data, phone_number)
                continue
            if data.get("challengeType") == "VerifySMSCodeFormForSMSCaptcha":
                security_code = ""
                for attempt in range(attempts):
                    security_code = self.challenge_code_handler(username, ChallengeChoice.SMS)
                    if security_code:
                        break
                    if wait_seconds:
                        time.sleep(wait_seconds * (attempt + 1))
                if not security_code:
                    raise ChallengeRequired("SMS code required for signup challenge")
                data = self.challenge_verify_sms_captcha(data, security_code)
                continue
            raise ClientError(f"Unsupported signup challenge step: {data}")
        raise ClientError(f"Signup challenge flow did not complete: {data}")

    def challenge_api(self, data):
        resp = self.private.get(
            self._challenge_url(data.get("api_path"), prefix="/api/v1"),
            params={
                "guid": self.uuid,
                "device_id": self.android_device_id,
                "challenge_context": data["challenge_context"],
            },
        )
        return resp.json()

    def challenge_captcha(self, challenge_json_data):
        api_path = challenge_json_data.get("api_path")
        site_key = challenge_json_data.get("fields", {}).get("sitekey")
        challenge_type = challenge_json_data.get("challengeType")  # For logging/context

        if not site_key or not api_path:
            self.logger.error(
                f"Malformed captcha challenge data from Instagram: site_key={site_key}, api_path={api_path}"
            )
            raise ClientError("Malformed captcha challenge data from Instagram (missing site_key or api_path).")

        challenge_post_url = self._challenge_url(api_path)
        captcha_details_for_solver = {
            "site_key": site_key,
            "challenge_type": challenge_type,
            "raw_challenge_json": challenge_json_data,
            "page_url": "https://www.instagram.com/accounts/emailsignup/",  # Common page for signup captcha
        }

        try:
            # self.captcha_resolve is assumed to be implemented on the main Client class
            # and is expected to raise CaptchaChallengeRequired if it cannot obtain a token.
            g_recaptcha_response = self.captcha_resolve(**captcha_details_for_solver)
        except CaptchaChallengeRequired:
            self.logger.warning(
                "Captcha solution was required by Instagram but not provided/resolved by any configured handler."
            )
            raise  # Re-raise for the user of instagrapi to handle or be informed.
        except Exception as e:
            self.logger.error(
                f"An unexpected error occurred during the captcha resolution process: {e}",
                exc_info=True,
            )
            raise ClientError(f"Captcha resolution process failed: {e}")  # Wrap other errors

        # Proceed to POST the g_recaptcha_response:
        resp = self.private.post(
            challenge_post_url,
            data={"g-recaptcha-response": g_recaptcha_response},
        )
        return resp.json()

    def challenge_submit_phone_number(self, data, phone_number):
        api_path = data.get("navigation", {}).get("forward")
        resp = self.private.post(
            self._challenge_url(api_path, field_name="navigation.forward"),
            data={
                "phone_number": phone_number,
                "challenge_context": data["challenge_context"],
            },
        )
        return resp.json()

    def challenge_verify_sms_captcha(self, data, security_code):
        api_path = data.get("navigation", {}).get("forward")
        resp = self.private.post(
            self._challenge_url(api_path, field_name="navigation.forward"),
            data={
                "security_code": security_code,
                "challenge_context": data["challenge_context"],
            },
        )
        return resp.json()
