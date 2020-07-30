import requests

from json.decoder import JSONDecodeError

from .exceptions import ClientLoginRequired, ClientError
from .utils import gen_csrftoken


class Account:

    def reset_password(self, username):
        response = requests.post(
            "https://www.instagram.com/accounts/account_recovery_send_ajax/",
            data={
                "email_or_username": username,
                "recaptcha_challenge_field": ""
            },
            headers={
                "x-requested-with": "XMLHttpRequest",
                "x-csrftoken": gen_csrftoken(),
                "Connection": "Keep-Alive",
                "Accept": "*/*",
                "Accept-Encoding": "gzip,deflate",
                "Accept-Language": "en-US",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/11.1.2 Safari/605.1.15",
            },
            proxies=self.public.proxies
        )
        try:
            return response.json()
        except JSONDecodeError as e:
            if "/login/" in response.url:
                raise ClientLoginRequired(e, response=response)
            raise ClientError(e, response=response)
