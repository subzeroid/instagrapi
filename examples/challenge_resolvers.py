"""
Django-based example to handle Email/SMS challenges
"""
import re
import time
import email
import imaplib

from django.conf import settings

from instagrapi import Client

from .models import Account


CHOICE_SMS = 0
CHOICE_EMAIL = 1


def get_code_from_email(username):
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(settings.CHALLENGE_EMAIL, settings.CHALLENGE_PASSWORD)
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
        return code
    return False


def get_code_from_sms(username):
    account = Account.objects.get(username=username)
    sms = account.sms_codes.last()
    for retry in range(24):
        # wait when user type sms code in Django Admin
        sms.refresh_from_db()
        if sms.code:
            return sms.code
        time.sleep(2)
    return False


def challenge_code_handler(username, choice):
    if choice == CHOICE_SMS:
        return get_code_from_sms(username)
    elif choice == CHOICE_EMAIL:
        return get_code_from_email(username)
    return False


if __name__ == '__main__':
    account = Account.objects.first()
    cl = Client()
    cl.challenge_code_handler = challenge_code_handler
    cl.login(account.username, account.password)
