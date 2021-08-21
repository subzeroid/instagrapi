import base64
import datetime
import hashlib
import hmac
import time
from typing import Any, List, Optional


class TOTP:
    """
    Base class for OTP handlers.
    """
    def __init__(self, s: str, digits: int = 6, digest: Any = hashlib.sha1, name: Optional[str] = None,
                 issuer: Optional[str] = None) -> None:
        self.digits = digits
        self.digest = digest
        self.secret = s
        self.name = name or 'Secret'
        self.issuer = issuer
        self.interval = 30

    def generate_otp(self, input: int) -> str:
        """
            :param input: the HMAC counter value to use as the OTP input.
            Usually either the counter, or the computed integer based on the Unix timestamp
        """
        if input < 0:
            raise ValueError('input must be positive integer')
        hasher = hmac.new(self.byte_secret(), self.int_to_bytestring(input), self.digest)
        hmac_hash = bytearray(hasher.digest())
        offset = hmac_hash[-1] & 0xf
        code = ((hmac_hash[offset] & 0x7f) << 24 |
                (hmac_hash[offset + 1] & 0xff) << 16 |
                (hmac_hash[offset + 2] & 0xff) << 8 |
                (hmac_hash[offset + 3] & 0xff))
        str_code = str(code % 10 ** self.digits)
        while len(str_code) < self.digits:
            str_code = '0' + str_code
        return str_code

    def byte_secret(self) -> bytes:
        secret = self.secret
        missing_padding = len(secret) % 8
        if missing_padding != 0:
            secret += '=' * (8 - missing_padding)
        return base64.b32decode(secret, casefold=True)

    @staticmethod
    def int_to_bytestring(i: int, padding: int = 8) -> bytes:
        """
        Turns an integer to the OATH specified
        bytestring, which is fed to the HMAC
        along with the secret
        """
        result = bytearray()
        while i != 0:
            result.append(i & 0xFF)
            i >>= 8
            # It's necessary to convert the final result from bytearray to bytes
            # because the hmac functions in python 2.6 and 3.3 don't work with
            # bytearray
        return bytes(bytearray(reversed(result)).rjust(padding, b'\0'))

    def code(self):
        """
        Generate TOTP code
        """
        now = datetime.datetime.now()
        timecode = int(time.mktime(now.timetuple()) / self.interval)
        return self.generate_otp(timecode)


class TOTPMixin:

    def totp_generate_seed(self) -> str:
        """
        Generate 2FA TOTP seed

        Returns
        -------
        str
            TOTP seed (also known as "token" and "secret key")
        """
        result = self.private_request(
            "accounts/generate_two_factor_totp_key/",
            data=self.with_default_data({})
        )
        return result["totp_seed"]

    def totp_enable(self, verification_code: str) -> List[str]:
        """
        Enable TOTP 2FA

        Parameters
        ----------
        verification_code: str
            2FA verification code

        Returns
        -------
        List[str]
            Backup codes
        """
        result = self.private_request(
            "accounts/enable_totp_two_factor/",
            data=self.with_default_data({'verification_code': verification_code})
        )
        return result["backup_codes"]

    def totp_disable(self) -> bool:
        """
        Disable TOTP 2FA

        Returns
        -------
        bool
        """
        result = self.private_request(
            "accounts/disable_totp_two_factor/",
            data=self.with_default_data({})
        )
        return result["status"] == "ok"

    def totp_generate_code(self, seed: str) -> str:
        """
        Generate 2FA TOTP code

        Parameters
        ----------
        seed: str
            TOTP seed (token, secret key)

        Returns
        -------
        str
            TOTP code
        """
        return TOTP(seed).code()
