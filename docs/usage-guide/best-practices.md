# Best Practices

This is a best practices guide around using the Instagram API so that you don't get rate limited or banned.

## Use a Proxy

If you're getting errors like this

- "The username you entered doesn't appear to belong to an account. Please check your username and try again."

Or you notice that Instagram is sending you emails about a suspicious login attempt, you should consider using a proxy. You are getting rate limited by Instagram or they are suspicious of your location.

You should have an IP address that you use consistently per user when making API requests. This will be
less suspicious than using a different IP address every time you make a request.

From our experience, here are safe limits we've seen for various actions:
- using 10 accounts per IP address
- publishing 4-16 posts for each account
- publishing 24-48 stories

The exact proxy provider matters less than consistency and quality. Here is the shape of using a proxy with `instagrapi`:

``` python
from instagrapi import Client

cl = Client()
before_ip = cl._send_public_request("https://api.ipify.org/")
cl.set_proxy("http://<api_key>:wifi;ca;;;toronto@proxy.soax.com:9137")
after_ip = cl._send_public_request("https://api.ipify.org/")

print(f"Before: {before_ip}")
print(f"After: {after_ip}")
```

Notes:

* Keep one stable proxy/IP per account whenever possible.
* Avoid rapidly rotating countries, cities, or carrier/mobile fingerprints for the same account.
* If you do password logins, match proxy, device settings, and account reuse consistently.

## Add Delays

It's recommended you try to mimic the behavior of a real user. This means you should add delays
between requests. The delays should be random and not too long.

The following is a good example of how to add delays between requests.

``` python
from instagrapi import Client

cl = Client()

# adds a random delay between 1 and 3 seconds after each request
cl.delay_range = [1, 3]
```


## Use Sessions

If you call `.login()` from scratch on every run, Instagram sees repeated fresh logins. That is much more suspicious than reusing a stable device session.

The normal pattern is:

1. Login once
2. Save settings with `.dump_settings()`
3. Load them later with `.load_settings()` or `.set_settings()`
4. Reuse the same device/session identifiers across runs

The first time you run your script

``` python
from instagrapi import Client

cl = Client()
cl.login(USERNAME, PASSWORD)
cl.dump_settings("session.json")
```

And on the next run:

``` python
from instagrapi import Client

cl = Client()
cl.load_settings("session.json")
cl.login(USERNAME, PASSWORD)
cl.get_timeline_feed()  # optional session validity check
```

You'll notice we do a call to `cl.get_timeline_feed()` to check if the session is valid. If it's not valid, you'll get an exception.

If you want more explicit control over the loaded settings object:

```python
from instagrapi import Client

cl = Client()
session = cl.load_settings("session.json")
cl.set_settings(session)
cl.login(USERNAME, PASSWORD)
```

Putting this all together, you can write a reusable login helper like this:

``` python
from instagrapi import Client
from instagrapi.exceptions import LoginRequired
import logging

logger = logging.getLogger()

def login_user():
    """
    Attempts to login to Instagram using either the provided session information
    or the provided username and password.
    """

    cl = Client()
    session = cl.load_settings("session.json")

    login_via_session = False
    login_via_pw = False

    if session:
        try:
            cl.set_settings(session)
            cl.login(USERNAME, PASSWORD)

            # check if session is valid
            try:
                cl.get_timeline_feed()
            except LoginRequired:
                logger.info("Session is invalid, need to login via username and password")

                old_session = cl.get_settings()

                # use the same device uuids across logins
                cl.set_settings({})
                cl.set_uuids(old_session["uuids"])

                cl.login(USERNAME, PASSWORD)
            login_via_session = True
        except Exception as e:
            logger.info("Couldn't login user using session information: %s" % e)

    if not login_via_session:
        try:
            logger.info("Attempting to login via username and password. username: %s" % USERNAME)
            if cl.login(USERNAME, PASSWORD):
                login_via_pw = True
        except Exception as e:
            logger.info("Couldn't login user using username and password: %s" % e)

    if not login_via_pw and not login_via_session:
        raise Exception("Couldn't login user with either password or session")

    return cl
```

## Prefer Read/Write Separation

If your workload is mostly data retrieval, keep that path separate from account-changing actions.

In practice:

* Reading data is usually easier to scale and safer to isolate.
* Writing actions such as posting, following, editing profile data, or sending DMs need much stricter operational hygiene.
* When possible, use official Instagram APIs for account-changing actions and keep private API automation focused on the gaps.
