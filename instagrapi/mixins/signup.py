import random
import time
from uuid import uuid4

from instagrapi.extractors import extract_user_short
from instagrapi.types import UserShort
from instagrapi.exceptions import (
    EmailInvalidError,
    EmailNotAvailableError,
    EmailVerificationSendError,
    AgeEligibilityError,
    CaptchaChallengeRequired,
    ClientError,  # Ensure ClientError is imported if not already
)

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
            if not age_check_result.get("eligible"): # Assuming "eligible": True is success
                raise AgeEligibilityError(f"Account not eligible based on age criteria: {age_check_result}")

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
        # timestamp = datetime.now().strftime("%s")  # Unused variable
        # nonce = f'{username}|{timestamp}|\xb9F"\x8c\xa2I\xaaz|\xf6xz\x86\x92\x91Y\xa5\xaa#f*o%\x7f'  # Unused variable
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
        return self.private_request("accounts/create/", data, domain="www.instagram.com")

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

    def challenge_captcha(self, challenge_json_data):
        api_path = challenge_json_data.get('api_path')
        site_key = challenge_json_data.get('fields', {}).get('sitekey')
        challenge_type = challenge_json_data.get('challengeType')  # For logging/context

        if not site_key or not api_path:
            self.logger.error(f"Malformed captcha challenge data from Instagram: site_key={site_key}, api_path={api_path}")
            raise ClientError("Malformed captcha challenge data from Instagram (missing site_key or api_path).")

        challenge_post_url = f"https://i.instagram.com{api_path}"

        captcha_details_for_solver = {
            'site_key': site_key,
            'challenge_type': challenge_type,
            'raw_challenge_json': challenge_json_data,
            'page_url': 'https://www.instagram.com/accounts/emailsignup/', # Common page for signup captcha
        }

        try:
            # self.captcha_resolve is assumed to be implemented on the main Client class
            # and is expected to raise CaptchaChallengeRequired if it cannot obtain a token.
            g_recaptcha_response = self.captcha_resolve(**captcha_details_for_solver)
        except CaptchaChallengeRequired:
            self.logger.warning("Captcha solution was required by Instagram but not provided/resolved by any configured handler.")
            raise  # Re-raise for the user of instagrapi to handle or be informed.
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during the captcha resolution process: {e}", exc_info=True)
            raise ClientError(f"Captcha resolution process failed: {e}") # Wrap other errors

        # Proceed to POST the g_recaptcha_response:
        resp = self.private.post(
            challenge_post_url,
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
