# Best Practices

This is a best practices guide around using the Instagram API so that you don't get rate limited or banned.

## Use a Stable Proxy Identity

If you're getting errors like this:

- "The username you entered doesn't appear to belong to an account. Please check your username and try again."
- `BadPassword` even though the same password works in another context

Or you notice that Instagram is sending suspicious login emails, review the network identity for that account. Instagram may be rate limiting the IP, distrusting the login location, or challenging the account because the device/session and IP history do not look consistent.

For production automation, the safest baseline is one account per stable proxy/IP. Reusing the same country, city, ASN/mobile carrier, device settings, and saved session is less suspicious than using a different IP address every time you make a request.

Avoid treating any proxy type as a universal fix. Residential, mobile, ISP, and datacenter proxies can all fail if they are abused, shared too widely, or rotated aggressively. The exact provider matters less than consistency, reputation, and whether your request pattern fits the account history.

Here is the shape of using a proxy with `instagrapi`:

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
* Prefer proxy hostnames that resolve through the proxy when using SOCKS, for example `socks5h://...`.
* Match `set_country(...)`, `set_locale(...)`, device settings, and saved sessions to the account's normal environment.
* Do not rotate proxy identity in the middle of a challenge, password reset, or relogin loop.
* Treat a shared IP pool as higher risk; reduce account count and request volume if you cannot dedicate an IP per account.

If `BadPassword` happens with a known-good password, use the [`BadPassword` troubleshooting guide](https://instagrapi.com/guides/errors/bad-password/) to separate real credential problems from Instagram trust/risk rejections.

## Warm Accounts Gradually

New, restored, or previously challenged accounts should not immediately run high-volume actions.

Practical warmup rules:

* Start with read-heavy authenticated actions before write-heavy actions.
* Avoid repeated fresh password logins. Save settings and reuse the same device/session identity.
* Keep early write actions low and human-like: fewer follows, likes, comments, DMs, uploads, and profile edits.
* Increase volume slowly over days, not minutes.
* Stop and inspect the account manually after repeated challenges, forced password changes, or feedback blocks.
* Do not run the same workload across many accounts from the same fresh proxy pool at once.

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

Delays are only one layer. For larger jobs, also limit concurrency per account, per proxy, and per action type. A single account doing many parallel actions is more suspicious than the same work spread out with clear cooldowns.

## Handle Rate Limits and Anti-Abuse Responses Explicitly

Instagram uses several different responses for throttling, suspicious behavior, or temporary restrictions. Treat them differently instead of retrying every error the same way.

### `ClientThrottledError` / HTTP 429

This usually means the current IP or request pattern is too aggressive for that path right now.

Recommended response:

* stop the current burst of requests
* back off before retrying
* reduce concurrency for that account
* if the same account keeps hitting `429`, pause it or move it to a cleaner proxy/IP

### `PleaseWaitFewMinutes`

This is usually more serious than a single `429`. Instagram is telling you to slow down for that account, device, or IP combination.

Recommended response:

* stop write actions for that account for a while
* do not spam retries in a tight loop
* keep the same device settings and only retry later
* if it keeps happening, review proxy quality and account warmup

### `FeedbackRequired`

This often means an action was blocked or the account is temporarily restricted.

Recommended response:

* inspect `client.last_json.get("feedback_message")`
* stop repeating the same action immediately
* freeze the account or action type for a cooldown window
* if you automate multiple action types, disable the offending one first

### `LoginRequired`

This usually means the current private session is no longer valid.

Recommended response:

* relogin with the same saved device/session state
* validate the session with a lightweight authenticated call
* if relogin keeps failing, stop and inspect the account manually instead of forcing repeated fresh logins

### `ChallengeRequired`

This means Instagram wants an additional verification step. Some flows can be automated, but newer challenge paths may still require manual review.

Recommended response:

* call `challenge_resolve(...)` only if you have working handlers for codes/password changes
* if you hit `/auth_platform/` or UFAC web flows, expect manual handling
* do not rotate identity aggressively in the middle of a challenge

### Practical Rules

* Separate read-heavy jobs from write-heavy jobs whenever possible.
* Use one stable proxy/IP per account instead of hopping between locations.
* Persist sessions and device identifiers; avoid password login from scratch on every run.
* Freeze accounts that hit repeated anti-abuse responses instead of hammering them harder.
* Track errors per account, per proxy, and per action type so you can see which variable is actually causing trouble.
* Retry transport errors differently from account restrictions. A timeout may be retried; a challenge or feedback block needs cooldown and investigation.

## Common Anti-Patterns

These patterns often create support issues that are not library bugs:

* logging in with username/password on every script run
* switching proxies after every request
* sharing one noisy IP across many unrelated accounts
* retrying `429`, `PleaseWaitFewMinutes`, `FeedbackRequired`, or challenges in a tight loop
* mixing browser `sessionid` reuse with frequent private API password logins
* changing password, email, phone, profile, and posting behavior from a fresh proxy at the same time
* running write-heavy automation immediately after account creation or recovery
* ignoring `client.last_json` and treating every exception as a generic transient failure

## Separate Library Bugs from Operational Blocks

A library bug usually reproduces consistently for the same endpoint and payload, especially across accounts with healthy sessions. Useful reports include the method called, sanitized request/response data, stack trace, dependency versions, and whether the same account works in the official app.

An operational block is usually account, proxy, session, or action-pattern specific. Signs include `BadPassword` with a known-good password, `429`, `PleaseWaitFewMinutes`, `FeedbackRequired`, suspicious login emails, challenges, forced password changes, or behavior that disappears after cooldown, cleaner proxy identity, or manual app verification.

When reporting an issue, include enough context to distinguish these cases. Remove cookies, session IDs, tokens, passwords, phone numbers, emails, and private user data before sharing logs.

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
