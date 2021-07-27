"""
An example when you need to change proxy

https://github.com/adw0rd/instagrapi/discussions/299
"""

from urllib3.exceptions import HTTPError
from requests.exceptions import ProxyError
from instagrapi.exceptions import (
    GenericRequestError, ClientConnectionError,
    SentryBlock, RateLimitError, ClientThrottledError,
    ClientLoginRequired, PleaseWaitFewMinutes
)

def next_proxy():
    return random.choices([
        'http://username:password@147.123123.123:412345',
        'http://username:password@147.123123.123:412346',
        'http://username:password@147.123123.123:412347'
    ])

cl = Client()

try:
    cl.login()
except (ProxyError, HTTPError, GenericRequestError, ClientConnectionError):
    # Network level
    cl.set_proxy(next_proxy())
except (SentryBlock, RateLimitError, ClientThrottledError):
    # Instagram limit level
    cl.set_proxy(next_proxy())
except (ClientLoginRequired, PleaseWaitFewMinutes):
    # Logical level
    cl.set_proxy(next_proxy())
