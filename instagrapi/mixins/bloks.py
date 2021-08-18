from instagrapi.utils import dumps


class BloksMixin:
    bloks_versioning_id = ""

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
