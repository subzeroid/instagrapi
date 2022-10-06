import datetime
import enum
import json
import random
import string
import time
import urllib


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


class InstagrapiJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, enum.Enum):
            return obj.value
        elif isinstance(obj, datetime.time):
            return obj.strftime("%H:%M")
        elif isinstance(obj, (datetime.datetime, datetime.date)):
            return int(obj.strftime("%s"))
        elif isinstance(obj, set):
            return list(obj)
        return json.JSONEncoder.default(self, obj)


def generate_signature(data):
    """Generate signature of POST data for Private API

    Returns
    -------
    str
        e.g. "signed_body=SIGNATURE.test"
    """
    return "signed_body=SIGNATURE.{data}".format(
        data=urllib.parse.quote_plus(data)
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


def gen_token(size=10, symbols=False):
    """Gen CSRF or something else token
    """
    chars = string.ascii_letters + string.digits
    if symbols:
        chars += string.punctuation
    return "".join(random.choice(chars) for _ in range(size))


def gen_password(size=10):
    """Gen password
    """
    return gen_token(size)


def dumps(data):
    """Json dumps format as required Instagram
    """
    return InstagrapiJSONEncoder(separators=(",", ":")).encode(data)


def generate_jazoest(symbols: str) -> str:
    amount = sum(ord(s) for s in symbols)
    return f'2{amount}'


def date_time_original(localtime):
    # return time.strftime("%Y:%m:%d+%H:%M:%S", localtime)
    return time.strftime("%Y%m%dT%H%M%S.000Z", localtime)


def random_delay(delay_range: list):
    """Trigger sleep of a random floating number in range min_sleep to max_sleep
    """
    return time.sleep(random.uniform(delay_range[0], delay_range[1]))
