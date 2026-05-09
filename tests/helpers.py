import json
import logging
import os
import os.path
import random
import subprocess
import tempfile
import time
import types
import unittest
from datetime import datetime, timedelta
from json.decoder import JSONDecodeError
from pathlib import Path
from unittest import mock
from unittest.mock import Mock
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests
from pydantic import ValidationError
from requests.exceptions import RetryError

from instagrapi import Client
from instagrapi.exceptions import (
    AlbumConfigureError,
    BadCredentials,
    ChallengeError,
    ChallengeRedirection,
    ChallengeRequired,
    ChallengeUnknownStep,
    ClientConnectionError,
    ClientError,
    ClientGraphqlError,
    ClientThrottledError,
    ClientUnauthorizedError,
    ClipConfigureError,
    DirectThreadNotFound,
    IGTVConfigureError,
    PhotoConfigureError,
    PhotoConfigureStoryError,
    PleaseWaitFewMinutes,
    PrivateError,
    RecaptchaChallengeForm,
    ReloginAttemptExceeded,
    SelectContactPointRecoveryForm,
    SubmitPhoneNumberForm,
    TwoFactorRequired,
    UnknownError,
    VideoConfigureError,
    VideoConfigureStoryError,
)
from instagrapi.extractors import (
    extract_direct_message,
    extract_direct_thread,
    extract_resource_v1,
    extract_story_v1,
)
from instagrapi.mixins.user import UserMixin
from instagrapi.story import StoryBuilder
from instagrapi.types import (
    Account,
    Collection,
    Comment,
    DirectMessage,
    DirectThread,
    Hashtag,
    Highlight,
    Location,
    Media,
    MediaOembed,
    Note,
    Share,
    Story,
    StoryHashtag,
    StoryLink,
    StoryMedia,
    StoryMention,
    StorySticker,
    User,
    UserShort,
    Usertag,
)
from instagrapi.utils import dumps, gen_password, generate_jazoest
from instagrapi.zones import UTC

logger = logging.getLogger("instagrapi.tests")
ACCOUNT_USERNAME = os.getenv("IG_USERNAME", "username")
ACCOUNT_PASSWORD = os.getenv("IG_PASSWORD", "password*")
ACCOUNT_SESSIONID = os.getenv("IG_SESSIONID", "")
TEST_ACCOUNTS_URL = os.getenv("TEST_ACCOUNTS_URL")

COMMENT_REPLIES_LIVE_FIXTURES = [
    ("3735285994514812478_640806256", "18097343278673293"),
    ("3735285994514812478_640806256", "18067227320032829"),
    ("3735285994514812478_640806256", "18052801016557024"),
    ("3735285994514812478_640806256", "17944918626046204"),
]

REQUIRED_MEDIA_FIELDS = [
    "pk",
    "taken_at",
    "id",
    "media_type",
    "code",
    "thumbnail_url",
    "location",
    "user",
    "comment_count",
    "like_count",
    "caption_text",
    "usertags",
    "video_url",
    "view_count",
    "video_duration",
    "title",
]
REQUIRED_STORY_FIELDS = [
    "pk",
    "id",
    "code",
    "taken_at",
    "media_type",
    "product_type",
    "thumbnail_url",
    "user",
    "video_url",
    "video_duration",
    "mentions",
    "links",
]


def cleanup(*paths):
    for path in paths:
        try:
            os.remove(path)
            os.remove(f"{path}.jpg")
        except FileNotFoundError:
            continue


def keep_path(user):
    user.profile_pic_url = user.profile_pic_url.path
    return user


class BaseClientMixin:
    def __init__(self, *args, **kwargs):
        if self.cl is None:
            self.cl = Client()
        self.set_proxy_if_exists()
        super().__init__(*args, **kwargs)

    def set_proxy_if_exists(self):
        proxy = os.getenv("IG_PROXY", "")
        if proxy:
            self.cl.set_proxy(proxy)  # "socks5://127.0.0.1:30235"
        return True


class ClientPrivateTestCase(BaseClientMixin, unittest.TestCase):
    cl = None
    _username_cache = {}

    def build_test_accounts_url(self, count=None):
        parts = urlsplit(TEST_ACCOUNTS_URL)
        query = dict(parse_qsl(parts.query, keep_blank_values=True))
        if count is None:
            query.setdefault("count", "5")
        else:
            query["count"] = str(count)
        return urlunsplit(
            (
                parts.scheme,
                parts.netloc,
                parts.path,
                urlencode(query),
                parts.fragment,
            )
        )

    def client_from_test_account(self, acc):
        settings = dict(acc["client_settings"])
        totp_seed = settings.pop("totp_seed", None)
        cl = Client(settings=settings, proxy=os.getenv("IG_PROXY") or acc["proxy"])
        login_kwargs = {
            "username": acc["username"],
            "password": acc["password"],
            "relogin": True,
        }
        if totp_seed:
            totp_code = cl.totp_generate_code(totp_seed)
            cl.totp_seed = totp_seed
            cl.totp_code = totp_code
            login_kwargs["verification_code"] = totp_code
        cl.login(**login_kwargs)
        cl._user_id = acc.get("user_id")
        return cl

    def user_info_by_username(self, username):
        return self.cl.user_info_by_username_v1(username)

    def user_id_from_username(self, username):
        info = self._username_cache.get(username)
        if not info:
            info = self.user_info_by_username(username)
            self._username_cache[username] = info
        return str(info.pk)

    def setup_method(self, *args, **kwargs):
        if TEST_ACCOUNTS_URL:
            self.cl = self.fresh_account()

    def fresh_account(self):
        test_accounts_url = self.build_test_accounts_url()
        print("TEST_ACCOUNTS_URL: configured")
        try:
            resp = requests.get(test_accounts_url, verify=False)
        except requests.RequestException as exc:
            raise RuntimeError(f"Could not fetch TEST_ACCOUNTS_URL: {exc.__class__.__name__}") from None
        print("TEST_ACCOUNTS_URL response code: ", resp.status_code)
        if not 200 <= resp.status_code < 300:
            raise RuntimeError(f"TEST_ACCOUNTS_URL returned HTTP {resp.status_code}")
        last_exc = None
        for attempt, acc in enumerate(resp.json()[:5], start=1):
            print(f"Fresh account attempt {attempt}: %(username)r" % acc)
            try:
                return self.client_from_test_account(acc)
            except Exception as exc:
                last_exc = exc
                print(f"Fresh account attempt {attempt} failed for {acc['username']}: {exc.__class__.__name__} {exc}")
                continue
        raise last_exc or RuntimeError("No usable fresh account returned")

    def fresh_accounts(self, count: int, exclude_user_ids=None):
        exclude_user_ids = {str(user_id) for user_id in (exclude_user_ids or set())}
        request_count = count + len(exclude_user_ids) + 3
        test_accounts_url = self.build_test_accounts_url(count=request_count)
        print("TEST_ACCOUNTS_URL: configured")
        try:
            resp = requests.get(test_accounts_url, verify=False)
        except requests.RequestException as exc:
            raise RuntimeError(f"Could not fetch TEST_ACCOUNTS_URL: {exc.__class__.__name__}") from None
        print("TEST_ACCOUNTS_URL response code: ", resp.status_code)
        if not 200 <= resp.status_code < 300:
            raise RuntimeError(f"TEST_ACCOUNTS_URL returned HTTP {resp.status_code}")

        accounts = []
        seen_user_ids = set(exclude_user_ids)
        last_exc = None
        for attempt, acc in enumerate(resp.json(), start=1):
            print(f"Fresh account attempt {attempt}: %(username)r" % acc)
            try:
                cl = self.client_from_test_account(acc)
            except Exception as exc:
                last_exc = exc
                print(f"Fresh account attempt {attempt} failed for {acc['username']}: {exc.__class__.__name__} {exc}")
                continue
            user_id = str(cl.user_id)
            if user_id in seen_user_ids:
                continue
            seen_user_ids.add(user_id)
            accounts.append(cl)
            if len(accounts) == count:
                return accounts
        raise RuntimeError(f"Could not get {count} usable fresh accounts" + (f": {last_exc}" if last_exc else ""))

    def __init__(self, *args, **kwargs):
        if TEST_ACCOUNTS_URL:
            self.cl = self.fresh_account()
            return super().__init__(*args, **kwargs)
        filename = f"/tmp/instagrapi_tests_client_settings_{ACCOUNT_USERNAME}.json"
        self.cl = Client()
        settings = {}
        try:
            st = os.stat(filename)
            if datetime.fromtimestamp(st.st_mtime) > (datetime.now() - timedelta(seconds=3600)):
                # use only fresh session (5 minutes)
                settings = self.cl.load_settings(filename)
        except FileNotFoundError:
            pass
        except JSONDecodeError as e:
            logger.info("JSONDecodeError when read stored client settings. Use empty settings")
            logger.exception(e)
        self.cl.set_settings(settings)
        # self.cl.set_locale('ru_RU')
        # self.cl.set_timezone_offset(10800)
        self.cl.request_timeout = 1
        self.set_proxy_if_exists()
        if ACCOUNT_SESSIONID:
            self.cl.login_by_sessionid(ACCOUNT_SESSIONID)
        else:
            self.cl.login(ACCOUNT_USERNAME, ACCOUNT_PASSWORD, relogin=True)
        self.cl.dump_settings(filename)
        super().__init__(*args, **kwargs)


_HELPER_ONLY_NAMES = {"BaseClientMixin", "ClientPrivateTestCase"}
__all__ = [name for name in globals() if not name.startswith("_") and name not in _HELPER_ONLY_NAMES]
