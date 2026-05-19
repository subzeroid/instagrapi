from typing import Any, Dict, List, Optional

from instagrapi.utils.serialization import dumps


class BloksMixin:
    bloks_versioning_id = ""

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
        versioning_id = bloks_versioning_id or self.bloks_versioning_id
        assert versioning_id, "Client.bloks_versioning_id is empty (hash is expected)"
        data = {
            "params": dumps(params),
            "_uuid": self.uuid,
            "bk_client_context": dumps({"bloks_version": versioning_id, "styles_id": "instagram"}),
            "bloks_versioning_id": versioning_id,
        }
        return self.private_request(f"bloks/async_action/{action}/", data=data, with_signature=False)

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
