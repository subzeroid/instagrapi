import hashlib
import json
import random
import time
import urllib
from enum import Enum
from typing import Dict

import requests
from instagrapi.exceptions import (
    ChallengeError, ChallengeHackedLock, ChallengeRedirection, ChallengeRequired,
    ChallengeSelfieCaptcha, ChallengeUnknownStep, LegacyForceSetNewPasswordForm,
    RecaptchaChallengeForm, SelectContactPointRecoveryForm, SubmitPhoneNumberForm
)

WAIT_SECONDS = 5


class ChallengeChoice(Enum):
    SMS = 0
    EMAIL = 1


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
        challenge_context = last_json.get('challenge', {}).get('challenge_context', {})
        try:
            user_id, nonce_code = challenge_url.split("/")[2:4]
            if not challenge_context:
                challenge_context = json.dumps(
                    {
                        "step_name": "",
                        "nonce_code": nonce_code,
                        "user_id": int(user_id),
                        "is_stateless": False
                    }
                )
            params = {
                "guid": self.uuid,
                "device_id": self.android_device_id,
                "challenge_context": challenge_context,
            }
        except ValueError:
            # not enough values to unpack (expected 2, got 1)
            params = challenge_context
        try:
            self._send_private_request(challenge_url[1:], params=params)
        except (Exception, ChallengeRequired):
            pass
#            assert self.last_json["message"] == "challenge_required", self.last_json
#            return self.challenge_resolve_contact_form(challenge_url)
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
        enc_password = "#PWD_INSTAGRAM_BROWSER:0:%s:" % str(int(time.time()))
        instagram_ajax = hashlib.sha256(enc_password.encode()).hexdigest()[:12]
        session = requests.Session()
        session.verify = False  # fix SSLError/HTTPSConnectionPool
        session.proxies = self.private.proxies
        session.headers.update(
            {
                "User-Agent":
                    "Mozilla/5.0 (Linux; Android 8.0.0; MI 5s Build/OPR1.170623.032; wv) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/80.0.3987.149 "
                    "Mobile Safari/537.36 %s" % self.user_agent,
                "upgrade-insecure-requests":
                    "1",
                "sec-fetch-dest":
                    "document",
                "accept":
                    "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
                "x-requested-with":
                    "com.instagram.android",
                "sec-fetch-site":
                    "none",
                "sec-fetch-mode":
                    "navigate",
                "sec-fetch-user":
                    "?1",
                "accept-encoding":
                    "gzip, deflate",
                "accept-language":
                    "en-US,en;q=0.9,en-US;q=0.8,en;q=0.7",
                "pragma":
                    "no-cache",
                "cache-control":
                    "no-cache",
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
        choice = ChallengeChoice.EMAIL
        result = session.post(challenge_url, {"choice": choice})
        result = result.json()

        if result.get("location") == "instagram://checkpoint/dismiss" and True == False:
            endpoint = "bloks/apps/com.bloks.www.checkpoint.ufac.controller/"
            params = {}
            data = f"params={urllib.parse.quote(json.dumps(params))}&nest_data_manifest=true"
            self._send_private_request(endpoint, data=data, with_signature=False)
            components = search_params_in_components(
                self.last_json["layout"]["bloks_payload"]["tree"]["bk.components.screen.Wrapper"]
                ["content"]["bk.components.Flexbox"]
            )
            for clean in [
                "bk.action.i64.Const", "bk.action.map.Make", "bk.action.array.Make",
                "bk.action.core.GetArg", "bk.action.bloks.AsyncActionWithDataManifest",
                "bk.action.bloks.ReplaceChildren", "bk.action.core.TakeLast",
                "bk.action.core.FuncConst", "bk.action.i32.Const", "bk.action.bloks.InflateSync",
                "bk.action.string.JsonEncode"
            ]:
                components = components.replace(clean + ",", "").replace(clean, "")
            components = json.loads(components.replace("(", "[").replace(")", "]"))[-1]

            endpoint = f"bloks/apps/{components[0]}/"
            params = convert_list_2_dict(components[1])

            data = f"params={urllib.parse.quote(json.dumps(params))}&nest_data_manifest=true"
            self._send_private_request(endpoint, data=data, with_signature=False)

        for retry in range(8):
            time.sleep(WAIT_SECONDS)
            try:
                # FORM TO ENTER CODE
                result = self.handle_challenge_result(result)
                break
            except SelectContactPointRecoveryForm as e:
                if choice == ChallengeChoice.SMS:  # last iteration
                    raise e
                choice = ChallengeChoice.SMS
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
            ), f'ChallengeResolve: Data invalid: "{detail}" not in {details}'
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
        msg = ' '.join(
            [
                'Log into your Instagram account from smartphone and change password!',
                *extract_messages(result)
            ]
        )
        raise LegacyForceSetNewPasswordForm(msg)

    def challenge_resolve_delta_acknowledge_approved(self):
        challenge_url = self.last_json["challenge"]["api_path"][1:]
        # Take challenge
        self._send_private_request(challenge_url)
        # Confirm your account was temporary blocked (continue)
        self._send_private_request(
            challenge_url, {
                "challenge_context": self.last_json['challenge_context'],
                "should_promote_account_status": 0
            }
        )
        # Select email for receiving code
        self._send_private_request(
            challenge_url, {
                "choice": 1,
                "challenge_context": self.last_json['challenge_context'],
                "should_promote_account_status": 0
            }
        )

        wait_seconds = 5
        for attempt in range(24):
            code = self.challenge_code_handler(self.username, ChallengeChoice.EMAIL)
            if code:
                break
            time.sleep(wait_seconds)
        print(
            f'Code entered "{code}" for {self.username} ({attempt} attempts by {wait_seconds} seconds)'
        )

        # Input code
        self._send_private_request(
            challenge_url, {
                "security_code": code,
                "challenge_context": self.last_json['challenge_context'],
                "should_promote_account_status": 0
            }
        )

        for attempt in range(24):
            pwd = self.change_password_handler(self.username)
            if pwd:
                break
            time.sleep(wait_seconds)
        print(
            f'Password entered "{pwd}" for {self.username} ({attempt} attempts by {wait_seconds} seconds)'
        )

        enc_pwd = self.password_encrypt(pwd)
        res = self._send_private_request(
            challenge_url,
            {
                "enc_new_password1": enc_pwd,
                "enc_new_password2": enc_pwd,
                "challenge_context": self.last_json['challenge_context'],
                "should_promote_account_status": 0,
            },
        )

        self.authorization_data = {
            "ds_user_id": res["logged_in_user"]["pk"],
            "should_use_header_over_cookies": True
        }

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
            raise SelectContactPointRecoveryForm(" ".join(messages), challenge=challenge)
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
        status = self.last_json.get("status", "")

        if step_name == "delta_login_review" or step_name == "":
            endpoint = "bloks/apps/com.instagram.challenge.navigation.take_challenge/"
            data = 'is_bloks_web=True&challenge_context=%7B%22step_name%22%3A+%22%22%2C+%22is_stateless%22%3A+false%2C+%22present_as_modal%22%3A+false%7D&should_promote_account_status=0&nest_data_manifest=true'
            #            data = f"should_promote_account_status=0&choice=0&_uuid={self.uuid}&bk_client_context=%7B%22bloks_version%22%3A%2254a609be99b71e070ffecba098354aa8615da5ac4ebc1e44bb7be28e5b244972%22%2C%22styles_id%22%3A%22instagram%22%7D&bloks_versioning_id=54a609be99b71e070ffecba098354aa8615da5ac4ebc1e44bb7be28e5b244972"
            accepted = self._send_private_request(endpoint, data=data, with_signature=False)

            data = "choice=1&is_bloks_web=True&challenge_context=%7B%22step_name%22%3A+%22%22%2C+%22is_stateless%22%3A+false%2C+%22present_as_modal%22%3A+false%7D&should_promote_account_status=0&nest_data_manifest=true"
            accepted = self._send_private_request(endpoint, data=data, with_signature=False)


#            return True if accepted.get("status") == "ok" else False
        elif step_name in ("submit_phone", "verify_email", "select_verify_method"):
            params = {"choice": ChallengeChoice.EMAIL, "username": self.username}
            if step_name == "submit_phone":
                choice = ChallengeChoice.SMS
                number = self.change_sms_handler()  # Generate new phone number
                params["id_number"] = number["id"]

                self._send_private_request(
                    challenge_url, {
                        "challenge_context":
                            {
                                "step_name": "",
                                "is_stateless": False,
                                "present_as_modal": False
                            },
                        "phone_number": f"+33{number['number']}",
                        "next": "https://www.instagram.com/?__coig_challenged=1"
                    }
                )

            elif step_name == "select_verify_method":
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
                challenge_url = challenge_url[1:]
                if "email" in steps:
                    self._send_private_request(challenge_url, {"choice": ChallengeChoice.EMAIL})
                elif "phone_number" in steps:
                    self._send_private_request(challenge_url, {"choice": ChallengeChoice.SMS})
                else:
                    raise ChallengeError(
                        f'ChallengeResolve: Choice "email" or "phone_number" (sms) not available to this account {self.last_json}'
                    )
            wait_seconds = 5
            for attempt in range(24):
                code = self.challenge_code_handler(**params)
                if code:
                    break
                time.sleep(wait_seconds)
            print(
                f'Code entered "{code}" for {self.username} ({attempt} attempts by {wait_seconds} seconds)'
            )
            try:
                self._send_private_request(challenge_url, {"security_code": code})
            except BaseException as e:
                self.challenge_resolve_delta_acknowledge_approved()

            # assert 'logged_in_user' in client.last_json
            assert self.last_json.get("action", "") == "close"
            assert self.last_json.get("status", "") == "ok"
            return True
        elif step_name == "select_contact_point_recovery":
            steps = self.last_json["step_data"].keys()
            challenge_url = challenge_url[1:]
            if "email" in steps:
                self._send_private_request(challenge_url, {"choice": ChallengeChoice.EMAIL})
            else:
                raise ChallengeHackedLock(self.last_json)
            wait_seconds = 5
            for attempt in range(24):
                code = self.challenge_code_handler(self.username, ChallengeChoice.EMAIL)
                if code:
                    break
                time.sleep(wait_seconds)
            print(
                f'Code entered "{code}" for {self.username} ({attempt} attempts by {wait_seconds} seconds)'
            )
            self._send_private_request(challenge_url, {"security_code": code})

            time.sleep(3)
            self._send_private_request(
                challenge_url,
                {
                    "choice": 0,
                    "challenge_context": self.last_json['challenge_context'],
                    "should_promote_account_status": 0,
                    "nest_data_manifest": True,
                },
            )
            print(f'Confirmed profile information.')
            return True
        elif step_name == "change_password":
            # Example: {'step_name': 'change_password',
            #  'step_data': {'new_password1': 'None', 'new_password2': 'None'},
            #  'flow_render_type': 3,
            #  'bloks_action': 'com.instagram.challenge.navigation.take_challenge',
            #  'cni': 18226879502000588,
            #  'challenge_context': '{"step_name": "change_password", "cni": 18226879502000588, "is_stateless": false, "challenge_type_enum": "PASSWORD_RESET"}',
            #  'challenge_type_enum_str': 'PASSWORD_RESET',
            #  'status': 'ok'}
            wait_seconds = 5
            for attempt in range(24):
                pwd = self.change_password_handler(self.username)
                if pwd:
                    break
                time.sleep(wait_seconds)
            print(
                f'Password entered "{pwd}" for {self.username} ({attempt} attempts by {wait_seconds} seconds)'
            )

            pwd = self.password_encrypt(pwd)
            old_pwd = self.password_encrypt(self.password)
            self.password = pwd
            self._send_private_request(
                challenge_url[1:],
                {
                    "enc_old_password": old_pwd,
                    "enc_new_password1": pwd,
                    "enc_new_password2": pwd,
                },
            )
            return True
            # return self.bloks_change_password(pwd, self.last_json['challenge_context'])
        elif step_name == "":
            assert self.last_json.get("action", "") == "close"
            assert self.last_json.get("status", "") == "ok"
            return True
        elif step_name == "add_birthday":
            day = random.randint(1, 27)
            month = random.randint(1, 12)
            year = random.randint(1970, 2004)
            self._send_private_request(
                challenge_url[1:], {
                    "birthday_day": day,
                    "birthday_month": month,
                    "birthday_year": year
                }
            )
            print(f"Set birthday for {self.username}: {day}/{month}/{year}")
            return True
        elif step_name == "selfie_captcha":
            raise ChallengeSelfieCaptcha(self.last_json)
        elif step_name == "delta_acknowledge_approved":
            self.challenge_resolve_delta_acknowledge_approved()

            assert self.last_json.get("action", "") == "close"
            assert self.last_json.get("status", "") == "ok"
            return True
        else:
            raise ChallengeUnknownStep(
                f'ChallengeResolve: Unknown step_name "{step_name}" for "{self.username}" in challenge resolver: {self.last_json}'
            )
        return True


def convert_list_2_dict(datas):
    ret = {}
    if isinstance(datas, int):
        return datas
    if len(datas) == 2:
        for i, key in enumerate(datas[0]):
            ret[key] = convert_list_2_dict(datas[1][i])
    else:
        return convert_list_2_dict(datas[0])
    return ret


def search_params_in_components(components):
    data = None
    if isinstance(components, dict):
        data = search_params_in_components(components.get("children"))
    for flexbox in components:
        if "on_click" in flexbox and "challenge_root_id" in components[flexbox]:
            return components[flexbox]
        for key in ["bk.components.Collection", "bk.components.Flexbox"]:
            if key in flexbox:
                data = search_params_in_components(flexbox[key])
    return data
