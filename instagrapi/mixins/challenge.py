import hashlib
import json
import time
from datetime import datetime
from typing import Dict

import requests

from instagrapi.exceptions import (
    ChallengeError,
    ChallengeRedirection,
    ChallengeRequired,
    LegacyForceSetNewPasswordForm,
    RecaptchaChallengeForm,
    SelectContactPointRecoveryForm,
    SubmitPhoneNumberForm,
)

CHOICE_SMS = 0
CHOICE_EMAIL = 1
WAIT_SECONDS = 5


def extract_messages(challenge):
    messages = []
    for item in challenge["extraData"].get("content"):
        message = item.get("title", item.get("text"))
        if message:
            dot = "" if message.endswith(".") else "."
            messages.append(f"{message}{dot}")
    return messages


class ChallengeResolveMixin:
    """
    Helpers for resolving login challenge
    """

    def challenge_resolve(self, last_json: Dict) -> bool:
        """
        Start challenge resolve

        Returns
        -------
        bool
            A boolean value
        """
        # START GET REQUEST to challenge_url
        challenge_url = last_json["challenge"]["api_path"]
        try:
            user_id, nonce_code = challenge_url.split("/")[2:4]
            params = {
                "guid": self.uuid,
                "device_id": self.device_id,
                "challenge_context": json.dumps(
                    {"step_name": "", "nonce_code": nonce_code, "user_id": user_id}
                ),
            }
        except ValueError:
            # not enough values to unpack (expected 2, got 1)
            params = {}
        try:
            self._send_private_request(
                challenge_url[1:],
                None,
                params=params,
                with_signature=False,
            )
        except ChallengeRequired:
            assert self.last_json["message"] == "challenge_required", self.last_json
            return self.challenge_resolve_contact_form(challenge_url)
        return self.challenge_resolve_simple(challenge_url)

    def challenge_resolve_contact_form(self, challenge_url: str) -> bool:
        """
        Start challenge resolve

        Помогите нам удостовериться, что вы владеете этим аккаунтом
        > CODE
        Верна ли информация вашего профиля?
        Мы заметили подозрительные действия в вашем аккаунте.
        В целях безопасности сообщите, верна ли информация вашего профиля.
        > I AGREE

        Help us make sure you own this account
        > CODE
        Is your profile information correct?
        We have noticed suspicious activity on your account.
        For security reasons, please let us know if your profile information is correct.
        > I AGREE

        Parameters
        ----------
        challenge_url: str
            Challenge URL

        Returns
        -------
        bool
            A boolean value
        """
        result = self.last_json
        challenge_url = "https://i.instagram.com%s" % challenge_url
        enc_password = "#PWD_INSTAGRAM_BROWSER:0:%s:" % datetime.now().strftime("%s")
        instagram_ajax = hashlib.md5(enc_password.encode()).hexdigest()[:12]
        session = requests.Session()
        session.proxies = self.private.proxies
        session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Linux; Android 8.0.0; MI 5s Build/OPR1.170623.032; wv) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/80.0.3987.149 "
                "Mobile Safari/537.36 %s" % self.user_agent,
                "upgrade-insecure-requests": "1",
                "sec-fetch-dest": "document",
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
                "x-requested-with": "com.instagram.android",
                "sec-fetch-site": "none",
                "sec-fetch-mode": "navigate",
                "sec-fetch-user": "?1",
                "accept-encoding": "gzip, deflate",
                "accept-language": "en-US,en;q=0.9,en-US;q=0.8,en;q=0.7",
                "pragma": "no-cache",
                "cache-control": "no-cache",
            }
        )
        for key, value in self.private.cookies.items():
            if key in ["mid", "csrftoken"]:
                session.cookies.set(key, value)
        time.sleep(WAIT_SECONDS)
        result = session.get(challenge_url)  # render html form
        session.headers.update(
            {
                "x-ig-www-claim": "0",
                "x-instagram-ajax": instagram_ajax,
                "content-type": "application/x-www-form-urlencoded",
                "accept": "*/*",
                "sec-fetch-dest": "empty",
                "x-requested-with": "XMLHttpRequest",
                "x-csrftoken": session.cookies.get_dict().get("csrftoken"),
                "x-ig-app-id": self.private.headers.get("X-IG-App-ID"),
                "sec-fetch-site": "same-origin",
                "sec-fetch-mode": "cors",
                "referer": challenge_url,
            }
        )
        time.sleep(WAIT_SECONDS)
        choice = CHOICE_EMAIL
        result = session.post(challenge_url, {"choice": choice})
        result = result.json()
        for retry in range(8):
            time.sleep(WAIT_SECONDS)
            try:
                # FORM TO ENTER CODE
                result = self.handle_challenge_result(result)
                break
            except SelectContactPointRecoveryForm as e:
                if choice == CHOICE_SMS:  # last iteration
                    raise e
                choice = CHOICE_SMS
                result = session.post(challenge_url, {"choice": choice})
                result = result.json()
                continue  # next choice attempt
            except SubmitPhoneNumberForm as e:
                result = session.post(
                    challenge_url,
                    {
                        "phone_number": e.challenge["fields"]["phone_number"],
                        "challenge_context": e.challenge["challenge_context"],
                    },
                )
                result = result.json()
                break
            except ChallengeRedirection:
                return True  # instagram redirect
        assert result.get("challengeType") in (
            "VerifyEmailCodeForm",
            "VerifySMSCodeForm",
            "VerifySMSCodeFormForSMSCaptcha",
        ), result
        for retry_code in range(5):
            for attempt in range(1, 11):
                code = self.challenge_code_handler(self.username, choice)
                if code:
                    break
                time.sleep(WAIT_SECONDS * attempt)
            # SEND CODE
            time.sleep(WAIT_SECONDS)
            result = session.post(challenge_url, {"security_code": code}).json()
            result = result.get("challenge", result)
            if (
                "Please check the code we sent you and try again"
                not in (result.get("errors") or [""])[0]
            ):
                break
        # FORM TO APPROVE CONTACT DATA
        challenge_type = result.get("challengeType")
        if challenge_type == "LegacyForceSetNewPasswordForm":
            self.challenge_resolve_new_password_form(result)
        assert result.get("challengeType") == "ReviewContactPointChangeForm", result
        details = []
        for data in result["extraData"]["content"]:
            for entry in data.get("labeled_list_entries", []):
                val = entry["list_item_text"]
                if "@" not in val:
                    val = val.replace(" ", "").replace("-", "")
                details.append(val)
        # CHECK ACCOUNT DATA
        for detail in [self.username, self.email, self.phone_number]:
            assert (
                not detail or detail in details
            ), 'ChallengeResolve: Data invalid: "%s" not in %s' % (detail, details)
        time.sleep(WAIT_SECONDS)
        result = session.post(
            "https://i.instagram.com%s" % result.get("navigation").get("forward"),
            {
                "choice": 0,  # I AGREE
                "enc_new_password1": enc_password,
                "new_password1": "",
                "enc_new_password2": enc_password,
                "new_password2": "",
            },
        ).json()
        assert result.get("type") == "CHALLENGE_REDIRECTION", result
        assert result.get("status") == "ok", result
        return True

    def challenge_resolve_new_password_form(self, result):
        msg = ' '.join([
            'Log into your Instagram account from smartphone and change password!',
            *extract_messages(result)
        ])
        raise LegacyForceSetNewPasswordForm(msg)

    def handle_challenge_result(self, challenge: Dict):
        """
        Handle challenge result

        Parameters
        ----------
        challenge: Dict
            Dict

        Returns
        -------
        bool
            A boolean value
        """
        messages = []
        if "challenge" in challenge:
            """
            Иногда в JSON есть вложенность,
            вместо {challege_object}
            приходит {"challenge": {challenge_object}}
            Sometimes there is nesting in JSON,
            instead of {challege_object}
            comes {"challenge": {challenge_object}}
            """
            challenge = challenge["challenge"]
        challenge_type = challenge.get("challengeType")
        if challenge_type == "SelectContactPointRecoveryForm":
            """
            Помогите нам удостовериться, что вы владеете этим аккаунтом
            Чтобы защитить свой аккаунт, запросите помощь со входом.
            {'message': '',
            'challenge': {'challengeType': 'SelectContactPointRecoveryForm',
            'errors': ['Select a valid choice. 1 is not one of the available choices.'],
            'experiments': {},
            'extraData': {'__typename': 'GraphChallengePage',
            'content': [{'__typename': 'GraphChallengePageHeader',
            'description': None,
            'title': 'Help Us Confirm You Own This Account'},
            {'__typename': 'GraphChallengePageText',
            'alignment': 'center',
            'html': None,
            'text': 'To secure your account, you need to request help logging in.'},
            {'__typename': 'GraphChallengePageForm',
            'call_to_action': 'Get Help Logging In',
            'display': 'inline',
            'fields': None,
            'href': 'https://help.instagram.com/358911864194456'}]},
            'fields': {'choice': 'None'},
            'navigation': {'forward': '/challenge/8530598273/PlWAX2OMVk/',
            'replay': '/challenge/replay/8530598273/PlWAX2OMVk/',
            'dismiss': 'instagram://checkpoint/dismiss'},
            'privacyPolicyUrl': '/about/legal/privacy/',
            'type': 'CHALLENGE'},
            'status': 'fail'}
            """
            if "extraData" in challenge:
                messages += extract_messages(challenge)
            if "errors" in challenge:
                for error in challenge["errors"]:
                    messages.append(error)
            raise SelectContactPointRecoveryForm(
                " ".join(messages), challenge=challenge
            )
        elif challenge_type == "RecaptchaChallengeForm":
            """
            Example:
            {'message': '',
            'challenge': {
            'challengeType': 'RecaptchaChallengeForm',
            'errors': ['Неправильная Captcha. Попробуйте еще раз.'],
            'experiments': {},
            'extraData': None,
            'fields': {'g-recaptcha-response': 'None',
            'disable_num_days_remaining': -60,
            'sitekey': '6LebnxwUAAAAAGm3yH06pfqQtcMH0AYDwlsXnh-u'},
            'navigation': {'forward': '/challenge/32708972491/CE6QdsYZyB/',
            'replay': '/challenge/replay/32708972491/CE6QdsYZyB/',
            'dismiss': 'instagram://checkpoint/dismiss'},
            'privacyPolicyUrl': '/about/legal/privacy/',
            'type': 'CHALLENGE'},
            'status': 'fail'}
            """
            raise RecaptchaChallengeForm(". ".join(challenge.get("errors", [])))
        elif challenge_type in ("VerifyEmailCodeForm", "VerifySMSCodeForm"):
            # Success. Next step
            return challenge
        elif challenge_type == "SubmitPhoneNumberForm":
            raise SubmitPhoneNumberForm(challenge=challenge)
        elif challenge_type:
            # Unknown challenge_type
            messages.append(challenge_type)
            if "errors" in challenge:
                messages.append("\n".join(challenge["errors"]))
            messages.append("(Please manual login)")
            raise ChallengeError(" ".join(messages))
        elif challenge.get("type") == "CHALLENGE_REDIRECTION":
            """
            Example:
            {'location': 'instagram://checkpoint/dismiss',
            'status': 'ok',
            'type': 'CHALLENGE_REDIRECTION'}
            """
            raise ChallengeRedirection()
        return challenge

    def challenge_resolve_simple(self, challenge_url: str) -> bool:
        """
        Old type (through private api) challenge resolver
        Помогите нам удостовериться, что вы владеете этим аккаунтом

        Parameters
        ----------
        challenge_url : str
            Challenge URL

        Returns
        -------
        bool
            A boolean value
        """
        step_name = self.last_json.get("step_name", "")
        if step_name == "delta_login_review":
            # IT WAS ME (by GEO)
            self._send_private_request(challenge_url, {"choice": "0"})
            return True
        elif step_name in ("verify_email", "select_verify_method"):
            if step_name == "select_verify_method":
                """
                {'step_name': 'select_verify_method',
                'step_data': {'choice': '0',
                'fb_access_token': 'None',
                'big_blue_token': 'None',
                'google_oauth_token': 'true',
                'vetted_device': 'None',
                'phone_number': '+7 *** ***-**-09',
                'email': 'x****g@y*****.com'},     <------------- choice
                'nonce_code': 'DrW8V4m5Ec',
                'user_id': 12060121299,
                'status': 'ok'}
                """
                steps = self.last_json["step_data"].keys()
                if "email" in steps:
                    self._send_private_request(challenge_url, {"choice": CHOICE_EMAIL})
                elif "phone_number" in steps:
                    self._send_private_request(challenge_url, {"choice": CHOICE_SMS})
                else:
                    raise ChallengeError(
                        'ChallengeResolve: Choice "email" or "phone_number" (sms) not available to this account %s'
                        % self.last_json
                    )
            wait_seconds = 5
            for attempt in range(24):
                code = self.challenge_code_handler(self.username, CHOICE_EMAIL)
                if code:
                    break
                time.sleep(wait_seconds)
            print(
                'Enter code "%s" for %s (%d attempts by %d seconds)'
                % (code, self.username, attempt, wait_seconds)
            )
            self._send_private_request(challenge_url, {"security_code": code})
            # assert 'logged_in_user' in client.last_json
            assert self.last_json.get("action", "") == "close"
            assert self.last_json.get("status", "") == "ok"
            return True
        elif step_name == "":
            assert self.last_json.get("action", "") == "close"
            assert self.last_json.get("status", "") == "ok"
            return True
        else:
            raise Exception(
                'ChallengeResolve: Unknown step_name "%s" for "%s" in challenge resolver: %s'
                % (step_name, self.username, self.last_json)
            )
        return True
