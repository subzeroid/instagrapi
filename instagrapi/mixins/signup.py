import base64
import random
import time
from datetime import datetime
from uuid import uuid4

from instagrapi.extractors import extract_user_short
from instagrapi.types import UserShort

CHOICE_EMAIL = 1


class SignUpMixin:
    waterfall_id = str(uuid4())
    adid = str(uuid4())
    wait_seconds = 5

    def signup(
        self,
        username: str,
        password: str,
        email: str,
        phone_number: str,
        full_name: str = "",
        year: int = None,
        month: int = None,
        day: int = None,
    ) -> UserShort:
        self.get_signup_config()
        check = self.check_email(email)
        assert check.get("valid"), f"Email not valid ({check})"
        assert check.get("available"), f"Email not available ({check})"
        sent = self.send_verify_email(email)
        assert sent.get("email_sent"), "Email not sent ({sent})"
        # send code confirmation
        code = ""
        for attempt in range(1, 11):
            code = self.challenge_code_handler(username, CHOICE_EMAIL)
            if code:
                break
            time.sleep(self.wait_seconds * attempt)
        print(
            f'Enter code "{code}" for {username} '
            f"({attempt} attempts, by {self.wait_seconds} seconds)"
        )
        signup_code = self.check_confirmation_code(email, code).get("signup_code")
        retries = 0
        kwargs = {
            "username": username,
            "password": password,
            "email": email,
            "signup_code": signup_code,
            "full_name": full_name,
            "year": year,
            "month": month,
            "day": day,
        }
        while retries < 3:
            data = self.accounts_create(**kwargs)
            if data.get("message") != "challenge_required":
                break
            if self.challenge_flow(data["challenge"]):
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
                "android_device_id": self.device_id,
                "login_nonce_map": "{}",
                "login_nonces": "[]",
                "email": email,
                "qe_id": str(uuid4()),
                "waterfall_id": self.waterfall_id,
            },
        )

    def send_verify_email(self, email) -> dict:
        """Send request to receive code to email"""
        return self.private_request(
            "accounts/send_verify_email/",
            {
                "phone_id": self.phone_id,
                "device_id": self.device_id,
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
                "device_id": self.device_id,
                "email": email,
                "waterfall_id": self.waterfall_id,
            },
        )

    def check_age_eligibility(self, year, month, day):
        return self.private.post(
            "consent/check_age_eligibility/",
            data={"_csrftoken": self.token, "day": day, "year": year, "month": month},
        ).json()

    def accounts_create(
        self,
        username: str,
        password: str,
        email: str,
        signup_code: str,
        full_name: str = "",
        year: int = None,
        month: int = None,
        day: int = None,
        **kwargs,
    ) -> dict:
        timestamp = datetime.now().strftime("%s")
        nonce = f'{username}|{timestamp}|\xb9F"\x8c\xa2I\xaaz|\xf6xz\x86\x92\x91Y\xa5\xaa#f*o%\x7f'
        sn_nonce = base64.encodebytes(nonce.encode()).decode().strip()
        data = {
            "is_secondary_account_creation": "true",
            "jazoest": str(int(random.randint(22300, 22399))),  # "22341",
            "suggestedUsername": "sn_result",
            "do_not_auto_login_if_credentials_match": "false",
            "phone_id": self.phone_id,
            "enc_password": self.password_encrypt(password),
            "username": str(username),
            "first_name": str(full_name),
            "adid": self.adid,
            "guid": self.uuid,
            "device_id": self.device_id,
            "_uuid": self.uuid,
            "email": email,
            "force_sign_up_code": signup_code,
            "waterfall_id": self.waterfall_id,
            "one_tap_opt_in": "true",
            **kwargs,
        }
        return self.private_request("accounts/create/", data, domain= "www.instagram.com")

    def challenge_flow(self, data):
        data = self.challenge_api(data)
        while True:
            if data.get("message") == "challenge_required":
                data = self.challenge_captcha(data["challenge"])
                continue
            elif data.get("challengeType") == "SubmitPhoneNumberForm":
                data = self.challenge_submit_phone_number(data)
                continue
            elif data.get("challengeType") == "VerifySMSCodeFormForSMSCaptcha":
                data = self.challenge_verify_sms_captcha(data)
                continue

    def challenge_api(self, data):
        resp = self.private.get(
            f"https://i.instagram.com/api/v1{data['api_path']}",
            params={
                "guid": self.uuid,
                "device_id": self.device_id,
                "challenge_context": data["challenge_context"],
            },
        )
        return resp.json()

    def challenge_captcha(self, data):
        g_recaptcha_response = self.captcha_resolve()
        resp = self.private.post(
            f"https://i.instagram.com{data['api_path']}",
            data={"g-recaptcha-response": g_recaptcha_response},
        )
        return resp.json()

    def challenge_submit_phone_number(self, data, phone_number):
        api_path = data.get("navigation", {}).get("forward")
        resp = self.private.post(
            f"https://i.instagram.com{api_path}",
            data={
                "phone_number": phone_number,
                "challenge_context": data["challenge_context"],
            },
        )
        return resp.json()

    def challenge_verify_sms_captcha(self, data, security_code):
        api_path = data.get("navigation", {}).get("forward")
        resp = self.private.post(
            f"https://i.instagram.com{api_path}",
            data={
                "security_code": security_code,
                "challenge_context": data["challenge_context"],
            },
        )
        return resp.json()
