"""
An example when you need to change proxy

https://github.com/adw0rd/instagrapi/discussions/299
"""
import random

from requests.exceptions import ProxyError
from urllib3.exceptions import HTTPError

from instagrapi import Client
from instagrapi.exceptions import (
    ClientConnectionError,
    ClientForbiddenError,
    ClientLoginRequired,
    ClientThrottledError,
    GenericRequestError,
    PleaseWaitFewMinutes,
    RateLimitError,
    SentryBlock,
)


def next_proxy():
    return random.choices([
        'http://username:password@147.123123.123:412345',
        'http://username:password@147.123123.123:412346',
        'http://username:password@147.123123.123:412347'
    ])

cl = Client(proxy=next_proxy())

try:
    cl.login('USERNAME', 'PASSWORD')
except (ProxyError, HTTPError, GenericRequestError, ClientConnectionError):
    # Network level
    cl.set_proxy(next_proxy())
except (SentryBlock, RateLimitError, ClientThrottledError):
    # Instagram limit level
    cl.set_proxy(next_proxy())
except (ClientLoginRequired, PleaseWaitFewMinutes, ClientForbiddenError):
    # Logical level
    cl.set_proxy(next_proxy())
