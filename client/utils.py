import hmac
import json
import random
import string
import hashlib
import urllib

from . import config


class InstagramIdCodec:
    ENCODING_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"

    @staticmethod
    def encode(num, alphabet=ENCODING_CHARS):
        """Covert a numeric value to a shortcode."""
        num = int(num)
        if num == 0:
            return alphabet[0]
        arr = []
        base = len(alphabet)
        while num:
            rem = num % base
            num //= base
            arr.append(alphabet[rem])
        arr.reverse()
        return "".join(arr)

    @staticmethod
    def decode(shortcode, alphabet=ENCODING_CHARS):
        """Covert a shortcode to a numeric value."""
        base = len(alphabet)
        strlen = len(shortcode)
        num = 0
        idx = 0
        for char in shortcode:
            power = strlen - (idx + 1)
            num += alphabet.index(char) * (base ** power)
            idx += 1
        return num


def generate_signature(data):
    """Generate signature of POST data for Private API
    """
    body = hmac.new(
        config.IG_SIG_KEY.encode("utf-8"), data.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return "signed_body={body}.{data}&ig_sig_key_version={sig_key}".format(
        body=body, data=urllib.parse.quote(data), sig_key=config.SIG_KEY_VERSION,
    )


def json_value(data, *args, default=None):
    cur = data
    for a in args:
        try:
            if isinstance(a, int):
                cur = cur[a]
            else:
                cur = cur.get(a)
        except (IndexError, KeyError, TypeError, AttributeError):
            return default
    return cur


def gen_password(size=10, symbols=False):
    chars = string.ascii_letters + string.digits
    if symbols:
        chars += string.punctuation
    return ''.join(random.choice(chars) for _ in range(size))


def gen_csrftoken(size=32):
    return gen_password(size, symbols=False)


def dumps(data):
    return json.dumps(data, separators=(",", ":"))
