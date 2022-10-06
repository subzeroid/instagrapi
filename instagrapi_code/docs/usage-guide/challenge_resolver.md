
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
cl.challenge_code_handler = challenge_code_handler
cl.login(IG_USERNAME, IG_PASSWORD)
```

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

All challenges solved in the module [challenge.py](https://github.com/adw0rd/instagrapi/blob/master/instagrapi/mixins/challenge.py)

Automatic submission code from SMS/Email in examples [here](https://github.com/adw0rd/instagrapi/blob/master/examples/challenge_resolvers.py)
