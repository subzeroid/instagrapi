import json
from pathlib import Path
from typing import Dict, Optional, Union

from instagrapi.extractors import extract_account, extract_user_short
from instagrapi.types import Account, UserShort
from instagrapi.utils.auth import gen_token, generate_signature
from instagrapi.utils.serialization import dumps


class AccountMixin:
    """
    Helper class to manage your account
    """

    def send_password_reset(self, identifier: str, recaptcha_challenge_field: str = "") -> Dict:
        """
        Send a password reset link or code to the account email or phone.

        Parameters
        ----------
        identifier: str
            Username, email address, or phone number for the account.
        recaptcha_challenge_field: str, default ""
            Recaptcha challenge token when Instagram asks for one.

        Returns
        -------
        Dict
            Jsonified response from Instagram
        """
        csrf_token = self.public.cookies.get("csrftoken") or gen_token()
        return self.public_request(
            "https://www.instagram.com/accounts/account_recovery_send_ajax/",
            data={"email_or_username": identifier, "recaptcha_challenge_field": recaptcha_challenge_field},
            headers={
                "x-requested-with": "XMLHttpRequest",
                "x-csrftoken": csrf_token,
            },
            return_json=True,
            update_headers=False,
        )

    def reset_password(self, username: str) -> Dict:
        """
        Send a password reset link or code.

        This method is kept for backward compatibility. Use
        :meth:`send_password_reset` in new code.
        """
        return self.send_password_reset(username)

    def account_info(self) -> Account:
        """
        Fetch your account info

        Returns
        -------
        Account
            An object of Account class
        """
        result = self.private_request("accounts/current_user/?edit=true")
        return extract_account(result["user"])

    def account_convert_to_professional(
        self,
        to_account_type: int = 3,
        category_id: Union[str, int] = "2347428775505624",
        should_show_category: bool = True,
        should_show_public_contacts: bool = False,
        entry_point: str = "setting",
        creator_destination_migration: bool = False,
        extra_data: Optional[Dict] = None,
    ) -> Account:
        """
        Convert the current account to a professional account.

        Parameters
        ----------
        to_account_type: int, default 3
            Instagram professional account type. ``2`` is business and ``3`` is creator.
        category_id: str or int, default "2347428775505624"
            Professional category id selected during conversion.
        should_show_category: bool, default True
            Whether to show the category on the profile.
        should_show_public_contacts: bool, default False
            Whether to show public contact buttons on the profile.
        entry_point: str, default "setting"
            Instagram entry point name sent with the conversion request.
        creator_destination_migration: bool, default False
            Preserve Instagram's creator migration flag for compatible request shape.
        extra_data: Dict, optional
            Additional fields to merge into the conversion payload.

        Returns
        -------
        Account
            Refreshed account info after the conversion request.
        """
        if to_account_type not in (2, 3):
            raise ValueError("to_account_type must be 2 (business) or 3 (creator)")
        data = {
            "entry_point": entry_point,
            "creator_destination_migration": self._account_bool_value(creator_destination_migration),
            "to_account_type": str(to_account_type),
            "category_id": str(category_id),
            "should_show_category": self._account_bool_flag(should_show_category),
            "should_show_public_contacts": self._account_bool_flag(should_show_public_contacts),
        }
        data.update(extra_data or {})
        self.private_request(
            "business/account/convert_account/",
            data=self.with_default_data(data),
        )
        return self.account_info()

    def account_convert_to_business(
        self,
        category_id: Union[str, int] = "2347428775505624",
        should_show_category: bool = True,
        should_show_public_contacts: bool = False,
        **kwargs,
    ) -> Account:
        """
        Convert the current account to a business professional account.
        """
        return self.account_convert_to_professional(
            to_account_type=2,
            category_id=category_id,
            should_show_category=should_show_category,
            should_show_public_contacts=should_show_public_contacts,
            **kwargs,
        )

    def account_convert_to_creator(
        self,
        category_id: Union[str, int] = "2347428775505624",
        should_show_category: bool = True,
        should_show_public_contacts: bool = False,
        **kwargs,
    ) -> Account:
        """
        Convert the current account to a creator professional account.
        """
        return self.account_convert_to_professional(
            to_account_type=3,
            category_id=category_id,
            should_show_category=should_show_category,
            should_show_public_contacts=should_show_public_contacts,
            **kwargs,
        )

    @staticmethod
    def _account_bool_flag(value: bool) -> str:
        return "1" if value else "0"

    @staticmethod
    def _account_bool_value(value: bool) -> str:
        return "true" if value else "false"

    def change_password(
        self,
        old_password: str,
        new_password: str,
    ) -> bool:
        """
        Change password

        Parameters
        ----------
        new_password: str
            New password
        old_password: str
            Old password

        Returns
        -------
        bool
            A boolean value
        """
        try:
            enc_old_password = self.password_encrypt(old_password)
            enc_new_password = self.password_encrypt(new_password)
            data = {
                "enc_old_password": enc_old_password,
                "enc_new_password1": enc_new_password,
                "enc_new_password2": enc_new_password,
            }
            self.with_action_data(
                {
                    "_uid": self.user_id,
                    "_uuid": self.uuid,
                    "_csrftoken": self.token,
                }
            )
            result = self.private_request("accounts/change_password/", data=data)
            return result
        except Exception as e:
            self.logger.exception(e)
            return False

    def remove_bio_links(self, link_ids: list[int]) -> dict:
        signed_body = {
            "signed_body": "SIGNATURE." + json.dumps({"_uid": self.user_id, "_uuid": self.uuid, "link_ids": link_ids})
        }
        return self.private_request("accounts/remove_bio_links/", data=signed_body, with_signature=False)

    def set_external_url(self, external_url) -> dict:
        """
        Set new biography
        """
        data = dumps(
            {
                "updated_links": dumps([{"url": external_url, "title": "", "link_type": "external"}]),
                "_uid": self.user_id,
                "_uuid": self.uuid,
            }
        )
        return self.private_request(
            "accounts/update_bio_links/",
            data=generate_signature(data),
            with_signature=False,
        )

    def account_set_private(self) -> bool:
        """
        Sets your account private

        Returns
        -------
        Account
            An object of Account class
        """
        assert self.user_id, "Login required"
        user_id = str(self.user_id)
        data = self.with_action_data({"_uid": user_id, "_uuid": self.uuid})
        result = self.private_request("accounts/set_private/", data)
        return result["status"] == "ok"

    def account_set_public(self) -> bool:
        """
        Sets your account public

        Returns
        -------
        Account
            An object of Account class
        """
        assert self.user_id, "Login required"
        user_id = str(self.user_id)
        data = self.with_action_data({"_uid": user_id, "_uuid": self.uuid})
        result = self.private_request("accounts/set_public/", data)
        return result["status"] == "ok"

    def account_security_info(self) -> dict:
        """
        Fetch your account security info

        Returns
        -------
        dict
            Contains useful information on security settings: {
            "is_phone_confirmed": true,
            "is_two_factor_enabled": false,
            "is_totp_two_factor_enabled": true,
            "is_trusted_notifications_enabled": true,
            "is_eligible_for_whatsapp_two_factor": true,
            "is_whatsapp_two_factor_enabled": false,
            "backup_codes": [...],
            "trusted_devices": [],
            "has_reachable_email": true,
            "eligible_for_trusted_notifications": true,
            "is_eligible_for_multiple_totp": false,
            "totp_seeds": [],
            "can_add_additional_totp_seed": false
            }
        """
        return self.private_request("accounts/account_security_info/", self.with_default_data({}))

    def account_edit(self, **data: Dict) -> Account:
        """
        Edit your profile (authorized account)

        Parameters
        ----------
        data: Dict
            Fields you want to edit in your account as key and value pairs

        Returns
        -------
        Account
            An object of Account class
        """
        fields = (
            "external_url",
            "username",
            "full_name",
            "biography",
            "phone_number",
            "email",
        )
        # if "email" in data:
        #     # email is handled separately
        #     self.send_confirm_email(data.pop("email"))
        # if "phone_number" in data:
        #     # phone_number is handled separately
        #     self.send_confirm_phone_number(data.pop("phone_number"))
        data = {key: val for key, val in data.items() if key in fields}
        if "email" not in data or "phone_number" not in data:
            # Instagram Error: You need an email or confirmed phone number.
            user_data = self.account_info().dict()
            user_data = {field: user_data[field] for field in fields}
            data = dict(user_data, **data)
        full_name = data.pop("full_name", None)
        if full_name:
            # Instagram original field-name for full user name is "first_name"
            data["first_name"] = full_name
        # Biography with entities (markup)
        result = self.private_request("accounts/edit_profile/", self.with_default_data(data))
        biography = data.get("biography")
        if biography:
            self.account_set_biography(biography)
        return extract_account(result["user"])

    def account_set_biography(self, biography: str) -> bool:
        """
        Set biography with entities (markup)

        Parameters
        ----------
        biography: str
            Biography raw text

        Returns
        -------
        bool
            A boolean value
        """
        data = {"logged_in_uids": dumps([str(self.user_id)]), "raw_text": biography}
        result = self.private_request("accounts/set_biography/", self.with_default_data(data))
        return result["status"] == "ok"

    def account_change_picture(self, path: Path) -> UserShort:
        """
        Change photo for your profile (authorized account)

        Parameters
        ----------
        path: Path
            Path to the image you want to update as your profile picture

        Returns
        -------
        UserShort
            An object of UserShort class
        """
        upload_id, _, _ = self.photo_rupload(Path(path))
        result = self.private_request(
            "accounts/change_profile_picture/",
            self.with_default_data({"use_fbuploader": True, "upload_id": upload_id}),
        )
        return extract_user_short(result["user"])

    def news_inbox_v1(self, mark_as_seen: bool = False) -> dict:
        """
        Get old and new stories as is

        Parameters
        ----------
        mark_as_seen: bool
            Mark as seen or not

        Returns
        -------
        dict
        """
        return self.private_request("news/inbox/", params={"mark_as_seen": mark_as_seen})

    def send_confirm_email(self, email: str) -> dict:
        """
        Send confirmation code to new email address

        Parameters
        ----------
        email: str
            Email address

        Returns
        -------
        dict
        """
        return self.private_request(
            "accounts/send_confirm_email/",
            self.with_extra_data({"send_source": "personal_information", "email": email}),
        )

    def confirm_email(self, email: str, code: str) -> dict:
        """
        Confirm new email address by code

        Parameters
        ----------
        email: str
            Email address
        code: str
            Confirmation code

        Returns
        -------
        dict
        """
        return self.private_request(
            "accounts/verify_email_code/",
            self.with_extra_data({"email": email, "code": code}),
        )

    def send_confirm_phone_number(self, phone_number: str) -> dict:
        """
        Send confirmation code to new phone number

        Parameters
        ----------
        phone_number: str
            Phone number

        Returns
        -------
        dict
        """
        return self.private_request(
            "accounts/initiate_phone_number_confirmation/",
            self.with_extra_data(
                {
                    "android_build_type": "release",
                    "send_source": "edit_profile",
                    "phone_number": phone_number,
                }
            ),
        )
