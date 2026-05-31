import json
import re
import time
from http.cookies import SimpleCookie
from json import JSONDecodeError
from typing import Any, Dict, List, Optional
from uuid import uuid4

from instagrapi.utils.serialization import dumps


class BloksMixin:
    bloks_versioning_id = ""

    def _bloks_payload(self, params: Dict, bloks_versioning_id: str = "") -> Dict[str, str]:
        versioning_id = bloks_versioning_id or self.bloks_versioning_id
        assert versioning_id, "Client.bloks_versioning_id is empty (hash is expected)"
        return {
            "params": dumps(params),
            "_uuid": self.uuid,
            "bk_client_context": dumps({"bloks_version": versioning_id, "styles_id": "instagram"}),
            "bloks_versioning_id": versioning_id,
        }

    def bloks_async_action(self, action: str, params: Dict, bloks_versioning_id: str = "") -> Dict:
        """
        Perform a raw Bloks async action.

        Parameters
        ----------
        action: str
            Async action, for example ``com.bloks.www.fxcal.link.async``.
        params: Dict
            Bloks ``params`` payload.
        bloks_versioning_id: str, optional
            Bloks versioning id. Uses ``Client.bloks_versioning_id`` when omitted.

        Returns
        -------
        Dict
            Raw Instagram response.
        """
        data = self._bloks_payload(params, bloks_versioning_id=bloks_versioning_id)
        return self.private_request(f"bloks/async_action/{action}/", data=data, with_signature=False)

    def bloks_app(self, app: str, params: Dict, bloks_versioning_id: str = "") -> Dict:
        """
        Perform a raw Bloks app request.

        Parameters
        ----------
        app: str
            App name, for example ``com.bloks.www.two_step_verification.entrypoint``.
        params: Dict
            Bloks ``params`` payload.
        bloks_versioning_id: str, optional
            Bloks versioning id. Uses ``Client.bloks_versioning_id`` when omitted.

        Returns
        -------
        Dict
            Raw Instagram response.
        """
        data = self._bloks_payload(params, bloks_versioning_id=bloks_versioning_id)
        return self.private_request(f"bloks/apps/{app}/", data=data, with_signature=False)

    def bloks_challenge_take_challenge(
        self,
        challenge_context: str = "",
        choice: Optional[int] = None,
        has_follow_up_screens: int = 0,
        extra_data: Optional[Dict[str, Any]] = None,
        bloks_versioning_id: str = "",
    ) -> Dict:
        """
        Submit a challenge-navigation Bloks request.

        Instagram may return ``challenge_context`` as an opaque string instead
        of JSON. Pass it through unchanged; it is not decoded by the client.

        Returns
        -------
        Dict
            Raw Instagram response.
        """
        versioning_id = bloks_versioning_id or self.bloks_versioning_id
        assert versioning_id, "Client.bloks_versioning_id is empty (hash is expected)"
        data = {
            "_uuid": self.uuid,
            "has_follow_up_screens": str(has_follow_up_screens),
            "bk_client_context": dumps({"bloks_version": versioning_id, "styles_id": "instagram"}),
            "bloks_versioning_id": versioning_id,
        }
        if challenge_context is not None:
            data["challenge_context"] = challenge_context
        if choice is not None:
            data["choice"] = str(choice)
        if extra_data:
            data.update(extra_data)
        return self.private_request(
            "bloks/apps/com.instagram.challenge.navigation.take_challenge/",
            data=data,
            with_signature=False,
        )

    def bloks_fxcal_link_reels_share(
        self,
        flow: str = "ig_fb_reels_composer_rowshare",
        logging_event: str = "linking_flow_initiated",
        cds_client_value: int = 1,
        opaque_verified_native_auth_data: Optional[str] = None,
        native_auth_data: Optional[List[Dict[str, Any]]] = None,
        account_type: int = 0,
        bloks_versioning_id: str = "",
    ) -> Dict:
        """
        Start the Account Center link flow used by Reel Facebook sharing.

        This exposes the raw app surface. It starts the Bloks linking flow but
        does not guarantee that Facebook linking can be completed without the
        interactive Instagram app UI and native authentication context.

        Returns
        -------
        Dict
            Raw Instagram response.
        """
        params = {
            "server_params": {
                "flow": flow,
                "logging_event": logging_event,
                "cds_client_value": cds_client_value,
                "opaque_verified_native_auth_data": opaque_verified_native_auth_data,
                "native_auth_data": native_auth_data or [],
                "account_type": account_type,
            }
        }
        return self.bloks_async_action(
            "com.bloks.www.fxcal.link.async",
            params,
            bloks_versioning_id=bloks_versioning_id,
        )

    def bloks_two_step_verification_entrypoint(
        self,
        two_step_verification_context: str,
        flow_source: str = "two_factor_login",
        should_fallback_to_sms: bool = False,
        screen_id: Optional[str] = None,
        bloks_versioning_id: str = "",
    ) -> Dict:
        """
        Open the current Bloks two-step verification entrypoint.

        This is a low-level helper for accounts that require the newer
        CAA/Bloks two-factor flow. It requires a ``two_step_verification_context``
        returned by Instagram during login.

        Returns
        -------
        Dict
            Raw Instagram response.
        """
        server_params = {
            "should_fallback_to_sms": int(should_fallback_to_sms),
            "family_device_id": self.phone_id,
            "device_id": self.android_device_id,
            "two_step_verification_context": two_step_verification_context,
            "flow_source": flow_source,
        }
        if screen_id:
            server_params["INTERNAL_INFRA_screen_id"] = screen_id
        params = {
            "client_input_params": {
                "device_id": self.android_device_id,
                "is_whatsapp_installed": 0,
                "machine_id": self.mid,
            },
            "server_params": server_params,
        }
        return self.bloks_app(
            "com.bloks.www.two_step_verification.entrypoint",
            params,
            bloks_versioning_id=bloks_versioning_id,
        )

    def bloks_two_step_verification_method_picker(
        self,
        two_step_verification_context: str,
        flow_source: str = "two_factor_login",
        should_fallback_to_sms: bool = False,
        screen_id: Optional[str] = None,
        bloks_versioning_id: str = "",
    ) -> Dict:
        """
        Open the Bloks two-step verification method picker.

        Returns
        -------
        Dict
            Raw Instagram response.
        """
        server_params = {
            "should_fallback_to_sms": int(should_fallback_to_sms),
            "device_id": self.android_device_id,
            "two_step_verification_context": two_step_verification_context,
            "flow_source": flow_source,
        }
        if screen_id:
            server_params["INTERNAL_INFRA_screen_id"] = screen_id
        params = {
            "client_input_params": {"is_whatsapp_installed": 0},
            "server_params": server_params,
        }
        return self.bloks_app(
            "com.bloks.www.two_step_verification.method_picker",
            params,
            bloks_versioning_id=bloks_versioning_id,
        )

    def bloks_two_step_verification_select_method(
        self,
        two_step_verification_context: str,
        selected_method: str,
        flow_source: str = "two_factor_login",
        should_fallback_to_sms: bool = False,
        latency_qpl_marker_id: Optional[int] = None,
        latency_qpl_instance_id: Optional[int] = None,
        bloks_versioning_id: str = "",
    ) -> Dict:
        """
        Select a two-step verification method such as ``totp`` or ``sms``.

        Returns
        -------
        Dict
            Raw Instagram response.
        """
        server_params = {
            "should_fallback_to_sms": int(should_fallback_to_sms),
            "device_id": self.android_device_id,
            "spectra_reg_login_data": None,
            "two_step_verification_context": two_step_verification_context,
            "flow_source": flow_source,
        }
        if latency_qpl_marker_id is not None:
            server_params["INTERNAL__latency_qpl_marker_id"] = latency_qpl_marker_id
        if latency_qpl_instance_id is not None:
            server_params["INTERNAL__latency_qpl_instance_id"] = latency_qpl_instance_id
        params = {
            "client_input_params": {
                "selected_method": selected_method,
                # Instagram payload field name, not a secret value.
                "cloud_trust_token": None,  # nosec B105
                "network_bssid": None,
            },
            "server_params": server_params,
        }
        return self.bloks_async_action(
            "com.bloks.www.two_step_verification.method_picker.navigation.async",
            params,
            bloks_versioning_id=bloks_versioning_id,
        )

    def bloks_two_step_verification_enter_totp_code(
        self,
        two_step_verification_context: str,
        flow_source: str = "two_factor_login",
        screen_id: Optional[str] = None,
        bloks_versioning_id: str = "",
    ) -> Dict:
        """
        Open the Bloks TOTP code entry app.

        Returns
        -------
        Dict
            Raw Instagram response.
        """
        server_params = {
            "device_id": self.android_device_id,
            "two_step_verification_context": two_step_verification_context,
            "flow_source": flow_source,
        }
        if screen_id:
            server_params["INTERNAL_INFRA_screen_id"] = screen_id
        params = {"server_params": server_params}
        return self.bloks_app(
            "com.bloks.www.two_factor_login.enter_totp_code",
            params,
            bloks_versioning_id=bloks_versioning_id,
        )

    def bloks_two_step_verification_enter_backup_code(
        self,
        two_step_verification_context: str,
        flow_source: str = "two_factor_login",
        screen_id: Optional[str] = None,
        bloks_versioning_id: str = "",
    ) -> Dict:
        """
        Open the Bloks backup-code entry app.

        Returns
        -------
        Dict
            Raw Instagram response.
        """
        server_params = {
            "device_id": self.android_device_id,
            "two_step_verification_context": two_step_verification_context,
            "flow_source": flow_source,
        }
        if screen_id:
            server_params["INTERNAL_INFRA_screen_id"] = screen_id
        params = {"server_params": server_params}
        return self.bloks_app(
            "com.bloks.www.two_factor_login.enter_backup_code",
            params,
            bloks_versioning_id=bloks_versioning_id,
        )

    def bloks_two_step_verification_verify_code(
        self,
        two_step_verification_context: str,
        code: str,
        challenge: str = "totp",
        flow_source: str = "two_factor_login",
        should_trust_device: bool = True,
        should_fallback_to_sms: bool = False,
        auth_secure_device_id: str = "",
        block_store_machine_id: str = "",
        latency_qpl_marker_id: Optional[int] = None,
        latency_qpl_instance_id: Optional[int] = None,
        bloks_versioning_id: str = "",
    ) -> Dict:
        """
        Verify a Bloks two-step verification code.

        ``challenge`` is the selected method name, for example ``totp`` or
        ``sms``. The raw response may contain an embedded login payload; parse it
        with :meth:`bloks_extract_login_response`.

        Returns
        -------
        Dict
            Raw Instagram response.
        """
        server_params = {
            "should_fallback_to_sms": int(should_fallback_to_sms),
            "device_id": self.android_device_id,
            "spectra_reg_login_data": None,
            "challenge": challenge,
            "two_step_verification_context": two_step_verification_context,
            "flow_source": flow_source,
        }
        if latency_qpl_marker_id is not None:
            server_params["INTERNAL__latency_qpl_marker_id"] = latency_qpl_marker_id
        if latency_qpl_instance_id is not None:
            server_params["INTERNAL__latency_qpl_instance_id"] = latency_qpl_instance_id
        params = {
            "client_input_params": {
                "auth_secure_device_id": auth_secure_device_id,
                "block_store_machine_id": block_store_machine_id,
                "code": code,
                "should_trust_device": int(should_trust_device),
                "family_device_id": self.phone_id,
                "device_id": self.android_device_id,
                # Instagram payload field name, not a secret value.
                "cloud_trust_token": None,  # nosec B105
                "network_bssid": None,
                "machine_id": self.mid,
            },
            "server_params": server_params,
        }
        return self.bloks_async_action(
            "com.bloks.www.two_step_verification.verify_code.async",
            params,
            bloks_versioning_id=bloks_versioning_id,
        )

    def bloks_caa_login_send_request(
        self,
        password: str,
        username: str = "",
        login_attempt_count: int = 1,
        try_num: int = 1,
        waterfall_id: str = "",
        offline_experiment_group: str = "caa_iteration_v3_perf_ig_4",
        bloks_versioning_id: str = "",
    ) -> Dict:
        """
        Send the current CAA/Bloks login request used before Bloks 2FA.

        This low-level helper is intentionally conservative: it uses ordinary
        device/session identifiers already available on the client and leaves
        attestation-like fields empty instead of inventing fake values.

        Returns
        -------
        Dict
            Raw Instagram response.
        """
        contact_point = username or self.username
        encrypted_password = password if password.startswith("#PWD_") else self.password_encrypt(password)
        flow_id = waterfall_id or str(uuid4())
        text_input_id = flow_id[:8]
        params = {
            "client_input_params": {
                "blocked_uids": [],
                "aac": dumps(
                    {
                        "aac_init_timestamp": int(time.time()),
                        "aaccs": "",
                        "aacjid": str(uuid4()),
                    }
                ),
                "sim_phones": [],
                "aymh_accounts": [],
                "network_bssid": None,
                "secure_family_device_id": "",
                "has_granted_read_contacts_permissions": 0,
                "auth_secure_device_id": "",
                "has_whatsapp_installed": 0,
                "password": encrypted_password,
                "sso_token_map_json_string": "",  # nosec B105
                "block_store_machine_id": "",
                "ig_vetted_device_nonces": None,
                "cloud_trust_token": None,  # nosec B105
                "event_flow": "login_manual",
                "password_contains_non_ascii": str(not password.isascii()).lower(),
                "client_known_key_hash": "",
                "sso_accounts_auth_data": [],
                "encrypted_msisdn": "",
                "has_granted_read_phone_permissions": 0,
                "app_manager_id": "",
                "should_show_nested_nta_from_aymh": 0,
                "device_id": self.android_device_id,
                "zero_balance_state": "",
                "login_attempt_count": login_attempt_count,
                "machine_id": self.mid,
                "flash_call_permission_status": {
                    "READ_PHONE_STATE": "DENIED",
                    "READ_CALL_LOG": "DENIED",
                    "ANSWER_PHONE_CALLS": "DENIED",
                },
                "accounts_list": [],
                "gms_incoming_call_retriever_eligibility": "not_eligible",
                "family_device_id": self.phone_id,
                "fb_ig_device_id": [],
                "device_emails": [],
                "try_num": try_num,
                "lois_settings": {"lois_token": ""},  # nosec B105
                "event_step": "home_page",
                "headers_infra_flow_id": "",
                "openid_tokens": {},
                "contact_point": contact_point,
            },
            "server_params": {
                "should_trigger_override_login_2fa_action": 0,
                "is_from_logged_out": 0,
                "should_trigger_override_login_success_action": 0,
                "login_credential_type": "none",
                "server_login_source": "login",
                "waterfall_id": flow_id,
                "two_step_login_type": "one_step_login",
                "login_source": "Login",
                "is_platform_login": 0,
                "login_entry_point": "logged_out",
                "INTERNAL__latency_qpl_marker_id": 36707139,
                "is_from_aymh": 0,
                "offline_experiment_group": offline_experiment_group,
                "is_from_landing_page": 0,
                "left_nav_button_action": "NONE",
                "password_text_input_id": f"{text_input_id}:105",
                "is_from_empty_password": 0,  # nosec B105
                "is_from_msplit_fallback": 0,
                "ar_event_source": "login_home_page",
                "qe_device_id": self.uuid,
                "username_text_input_id": f"{text_input_id}:104",
                "layered_homepage_experiment_group": "Deploy: Not in Experiment",
                "device_id": self.android_device_id,
                "login_surface": "login_home",
                "INTERNAL__latency_qpl_instance_id": int(time.time() * 1000),
                "reg_flow_source": "login_home_native_integration_point",
                "is_caa_perf_enabled": 1,
                "credential_type": "password",
                "is_from_password_entry_page": 0,  # nosec B105
                "caller": "gslr",
                "family_device_id": self.phone_id,
                "is_from_assistive_id": 0,
                "access_flow_version": "pre_mt_behavior",
                "is_from_logged_in_switcher": 0,
            },
        }
        return self.bloks_async_action(
            "com.bloks.www.bloks.caa.login.async.send_login_request",
            params,
            bloks_versioning_id=bloks_versioning_id,
        )

    def _find_bloks_value(self, data: Any, key: str) -> Any:
        if isinstance(data, dict):
            value = data.get(key)
            if value:
                return value
            for child in data.values():
                value = self._find_bloks_value(child, key)
                if value:
                    return value
        elif isinstance(data, list):
            for child in data:
                value = self._find_bloks_value(child, key)
                if value:
                    return value
        elif isinstance(data, str) and len(data) < 10000 and key in data:
            try:
                value = self._find_bloks_value(json.loads(data), key)
            except (TypeError, ValueError):
                value = None
            if value:
                return value
        return None

    @staticmethod
    def _extract_first_json_string(value: str, start: int) -> str:
        quote_index = value.find('"', start)
        if quote_index < 0:
            return ""
        try:
            decoded, _ = json.JSONDecoder().raw_decode(value[quote_index:])
        except JSONDecodeError:
            return ""
        return decoded if isinstance(decoded, str) else ""

    def bloks_extract_two_step_verification_context(self, result: Dict) -> str:
        """
        Extract ``two_step_verification_context`` from a CAA/Bloks login result.

        Current app responses can place this context inside the Bloks action
        program that redirects to ``two_step_verification.entrypoint``. This
        helper first checks normal JSON containers, then parses that action
        parameter map without logging or returning any other sensitive fields.
        """
        value = self._find_bloks_value(result, "two_step_verification_context")
        if isinstance(value, str) and value.strip():
            return value.strip()
        action = result.get("layout", {}).get("bloks_payload", {}).get("action", "")
        if not isinstance(action, str) or "two_step_verification.entrypoint" not in action:
            return ""
        marker = '"two_step_verification_context"'
        marker_index = action.find(marker)
        if marker_index < 0:
            return ""
        key_list_end = action.find(")", marker_index)
        if key_list_end < 0:
            return ""
        value_group = re.search(r"\(dkc\s+", action[key_list_end:])
        if not value_group:
            return ""
        return self._extract_first_json_string(action, key_list_end + value_group.start()).strip()

    def bloks_extract_login_response(self, result: Dict) -> Dict[str, Any]:
        """
        Extract an embedded login response from a Bloks action payload.

        Successful CAA/Bloks two-factor responses can place a JSON object inside
        ``layout.bloks_payload.action``. This helper returns the decoded
        ``login_response``, response ``headers``, cookie values, raw cookie
        header text, and raw embedded object. If no payload is found, an empty
        dictionary is returned.

        Returns
        -------
        Dict
            Parsed login payload or ``{}``.
        """
        action = result.get("layout", {}).get("bloks_payload", {}).get("action", "")
        if not isinstance(action, str):
            return {}
        decoder = json.JSONDecoder()
        index = 0
        while index < len(action):
            if action[index] != '"':
                index += 1
                continue
            try:
                value, end = decoder.raw_decode(action[index:])
            except JSONDecodeError:
                index += 1
                continue
            index += max(end, 1)
            if not isinstance(value, str) or "login_response" not in value:
                continue
            try:
                raw = json.loads(value)
                login_response = json.loads(raw["login_response"])
                headers = json.loads(raw.get("headers") or "{}")
            except (KeyError, TypeError, ValueError):
                continue
            raw_cookies = raw.get("cookies") or ""
            cookies = SimpleCookie()
            cookies.load(raw_cookies.replace("Set-Cookie: ", ""))
            return {
                "login_response": login_response,
                "headers": headers,
                "cookies": {name: morsel.value for name, morsel in cookies.items()},
                "raw_cookies": raw_cookies,
                "raw": raw,
            }
        return {}

    def bloks_apply_login_response(self, result: Dict) -> bool:
        """
        Apply a parsed Bloks login response to the client session.

        ``result`` may be either the raw Bloks response returned by
        ``bloks_two_step_verification_verify_code(...)`` or the dictionary
        returned by :meth:`bloks_extract_login_response`.

        Returns
        -------
        bool
            ``True`` when authorization or session cookies were applied.
        """
        parsed = result if "headers" in result or "cookies" in result else self.bloks_extract_login_response(result)
        if not parsed:
            return False
        headers = parsed.get("headers") or {}
        cookies = parsed.get("cookies") or {}
        authorization = headers.get("IG-Set-Authorization") or headers.get("ig-set-authorization")
        if authorization:
            self.authorization_data = self.parse_authorization(authorization)
            if self.authorization:
                self.private.headers["Authorization"] = self.authorization
        for name, value in cookies.items():
            self.private.cookies.set(name, value)
        if cookies.get("sessionid"):
            self.public.cookies.set("sessionid", cookies["sessionid"])
        ig_u_rur = headers.get("ig-set-ig-u-rur") or headers.get("IG-Set-IG-U-RUR")
        if ig_u_rur:
            self.set_ig_u_rur(ig_u_rur)
            self.private.headers["IG-U-RUR"] = ig_u_rur
        ig_www_claim = headers.get("x-ig-set-www-claim") or headers.get("X-IG-Set-WWW-Claim")
        if ig_www_claim:
            self.set_ig_www_claim(ig_www_claim)
            self.private.headers["X-IG-WWW-Claim"] = ig_www_claim
        return bool(authorization or cookies.get("sessionid"))

    def bloks_action(self, action: str, data: dict) -> bool:
        """Performing actions for bloks

        Parameters
        ----------
        action: str
            Action, example "com.instagram.challenge.navigation.take_challenge"
        data: dict
            Additional data

        Returns
        -------
        bool
        """
        result = self.private_request(f"bloks/apps/{action}/", self.with_default_data(data))
        return result["status"] == "ok"

    def bloks_change_password(self, password: str, challenge_context: str) -> bool:
        """
        Change password for challenge

        Parameters
        ----------
        password: str
            New password
        challenge_context: str
            Challenge context returned by Instagram. The value may be opaque
            and is sent back unchanged.

        Returns
        -------
        bool
        """
        enc_password = self.password_encrypt(password)
        result = self.bloks_challenge_take_challenge(
            challenge_context=challenge_context,
            extra_data={
                "enc_new_password1": enc_password,
                "enc_new_password2": enc_password,
            },
        )
        return result["status"] == "ok"
