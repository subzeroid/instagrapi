You can handle any exceptions using a generic handler:

``` python
import json
import logging

from instagrapi import Client
from instagrapi.exceptions import (
    BadPassword, ReloginAttemptExceeded, ChallengeRequired,
    SelectContactPointRecoveryForm, RecaptchaChallengeForm,
    FeedbackRequired, PleaseWaitFewMinutes, LoginRequired,
    ClientThrottledError,
)
from instagrapi.utils import json_value

logger = logging.getLogger(__name__)

def handle_exception(client: Client, e: Exception):
    if isinstance(e, BadPassword):
        client.logger.exception(e)
        if client.relogin_attempt > 0:
            raise ReloginAttemptExceeded(e)
        raise e
    elif isinstance(e, LoginRequired):
        client.logger.exception(e)
        client.relogin()
        return True
    elif isinstance(e, ChallengeRequired):
        api_path = json_value(client.last_json, "challenge", "api_path")
        if api_path == "/challenge/":
            logger.warning("Generic challenge flow requires manual handling or a custom resolver")
        else:
            try:
                client.challenge_resolve(client.last_json)
            except ChallengeRequired as e:
                raise e
            except (ChallengeRequired, SelectContactPointRecoveryForm, RecaptchaChallengeForm) as e:
                raise e
        return True
    elif isinstance(e, FeedbackRequired):
        message = client.last_json.get("feedback_message", "")
        if "This action was blocked. Please try again later" in message:
            logger.warning("Action blocked by Instagram: %s", message)
        elif "We restrict certain activity to protect our community" in message:
            logger.warning("Temporary activity restriction: %s", message)
        elif "Your account has been temporarily blocked" in message:
            logger.warning("Temporary account block: %s", message)
    elif isinstance(e, ClientThrottledError):
        logger.warning("HTTP 429 from Instagram, back off and review proxy/account pressure")
    elif isinstance(e, PleaseWaitFewMinutes):
        logger.warning("Please wait before retrying: %s", e)
    raise e

cl = Client()
cl.handle_exception = handle_exception
cl.login(USERNAME, PASSWORD)
```

In this way, you can centrally handle errors and not repeat handlers throughout your code. In a real application, you would usually extend this with your own proxy rotation, account freeze/backoff storage, or metrics hooks.

For a practical playbook around `429`, `feedback_required`, `PleaseWaitFewMinutes`, and session/challenge handling, see [Best Practices](best-practices.md).

Full example [here](https://github.com/subzeroid/instagrapi/blob/master/examples/handle_exception.py)
