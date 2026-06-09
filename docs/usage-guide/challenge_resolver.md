
## Challenge Resolver

Instagrapi lets you attach handlers for common login challenge flows such as code verification and password reset.

## New password challenge

You can automatically change your password to solve the challenge from Instagram.

Declare `change_password_handler` which will return a new password.

``` python
def change_password_handler(username):
    # Simple way to generate a random string
    chars = list("abcdefghijklmnopqrstuvwxyz1234567890!&£@#")
    password = "".join(random.sample(chars, 8))
    return password

cl = Client()
cl.change_password_handler = change_password_handler
cl.login(IG_USERNAME, IG_PASSWORD)
```


## Code verification challenge

You can automatically process the codes sent to you to solve the challenge from Instagram.

You need to declare `challenge_code_handler` which will return the code received from Instagram via Email or SMS:

``` python
from instagrapi.mixins.challenge import ChallengeChoice


def challenge_code_handler(username, choice):
    if choice == ChallengeChoice.SMS:
        return get_code_from_sms(username)
    elif choice == ChallengeChoice.EMAIL:
        return get_code_from_email(username)
    return False

cl = Client()
cl.phone_number = "+15551234567"  # required for submit_phone challenges
cl.challenge_code_handler = challenge_code_handler
cl.login(IG_USERNAME, IG_PASSWORD)
```

Notes:

* `challenge_code_handler(username, choice)` should return the received code as a string. Returning a falsey value means no code is available yet.
* Login `submit_phone` challenges use `client.phone_number`, then call `challenge_code_handler(username, ChallengeChoice.SMS)` for the received code.
* Signup SMS challenges use the `phone_number` passed to `signup(...)` and call `challenge_code_handler(username, ChallengeChoice.SMS)` for the received code.
* Phone-only signup is supported with `signup(username, password, email="", phone_number="+15551234567")`. If both `email` and `phone_number` are provided, instagrapi keeps the email signup flow and uses the phone number only for signup challenges.
* `signup(...)` emits a `RuntimeWarning` because it uses Instagram's legacy account-create flow and should be treated as experimental. On modern Instagram app versions this flow is often rejected with `SignupSpamError` / `feedback_required` because the official app uses additional signup checks that instagrapi does not currently generate. Treat this as a platform rejection, not as a malformed SMS/email code.
* Current `master` raises a clearer `ChallengeRequired` for `/auth_platform/?apc=...` flows. That path is not yet supported automatically and still requires manual verification.
* Bloks redirect checkpoints such as `bloks_action="com.bloks.www.ig.challenge.redirect.async"` or placeholder `step_name="STEP_NAME"` require manual confirmation in the official Instagram app or web flow on a trusted device; instagrapi raises `ChallengeRequired` with the sanitized challenge context instead of treating this as a legacy step.
* For long-running automation, persist client settings around challenge handling so you can retry without rebuilding the entire device/session state.

## Selfie and manual review challenges

`ChallengeSelfieCaptcha` and selfie/manual-review style flows are account review decisions by Instagram. `instagrapi` does not provide a generic bypass for these challenges. When they appear repeatedly during signup or login, stop the automated flow, keep the same account/device/proxy context, and resolve the account manually in the official app if possible.

For bug reports, include sanitized `client.last_json`, the exception class, and the flow that triggered it. Do not share cookies, session IDs, phone numbers, email addresses, passwords, or verification codes.

For example, you can get the code through the IMAP of Gmail:

``` python
def get_code_from_email(username):
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(CHALLENGE_EMAIL, CHALLENGE_PASSWORD)
    mail.select("inbox")
    result, data = mail.search(None, "(UNSEEN)")
    assert result == "OK", "Error1 during get_code_from_email: %s" % result
    ids = data.pop().split()
    for num in reversed(ids):
        mail.store(num, "+FLAGS", "\\Seen")  # mark as read
        result, data = mail.fetch(num, "(RFC822)")
        assert result == "OK", "Error2 during get_code_from_email: %s" % result
        msg = email.message_from_string(data[0][1].decode())
        payloads = msg.get_payload()
        if not isinstance(payloads, list):
            payloads = [msg]
        code = None
        for payload in payloads:
            body = payload.get_payload(decode=True).decode()
            if "<div" not in body:
                continue
            match = re.search(">([^>]*?({u})[^<]*?)<".format(u=username), body)
            if not match:
                continue
            print("Match from email:", match.group(1))
            match = re.search(r">(\d{6})<", body)
            if not match:
                print('Skip this email, "code" not found')
                continue
            code = match.group(1)
            if code:
                return code
    return False
```

All challenges solved in the module [challenge.py](https://github.com/subzeroid/instagrapi/blob/master/instagrapi/mixins/challenge.py)

Automatic submission code from SMS/Email in examples [here](https://github.com/subzeroid/instagrapi/blob/master/examples/challenge_resolvers.py)
