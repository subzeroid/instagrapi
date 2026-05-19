import json
from http.cookies import SimpleCookie
from json import JSONDecodeError
from typing import Any, Dict, List, Optional

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

    def bloks_change_password(self, password: str, challenge_context: dict) -> bool:
        """
        Change password for challenge

        Parameters
        ----------
        passwrd: str
            New password

        Returns
        -------
        bool
        """
        assert self.bloks_versioning_id, "Client.bloks_versioning_id is empty (hash is expected)"
        enc_password = self.password_encrypt(password)
        data = {
            "bk_client_context": dumps({"bloks_version": self.bloks_versioning_id, "styles_id": "instagram"}),
            "challenge_context": challenge_context,
            "bloks_versioning_id": self.bloks_versioning_id,
            "enc_new_password1": enc_password,
            "enc_new_password2": enc_password,
        }
        return self.bloks_action("com.instagram.challenge.navigation.take_challenge", data)
