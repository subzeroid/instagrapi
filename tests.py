import json
import logging
import os
import os.path
import random
import tempfile
import types
import unittest
from unittest import mock
from unittest.mock import Mock
from datetime import datetime, timedelta
from json.decoder import JSONDecodeError
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests
from pydantic import ValidationError
from requests.exceptions import RetryError

from instagrapi import Client
from instagrapi.extractors import (
    extract_direct_message,
    extract_direct_thread,
    extract_resource_v1,
    extract_story_v1,
)
from instagrapi.exceptions import (
    AlbumConfigureError,
    BadCredentials,
    ChallengeError,
    ChallengeRedirection,
    ChallengeRequired,
    ChallengeUnknownStep,
    ClipConfigureError,
    ClientConnectionError,
    ClientGraphqlError,
    ClientUnauthorizedError,
    ClientThrottledError,
    DirectThreadNotFound,
    IGTVConfigureError,
    PleaseWaitFewMinutes,
    PhotoConfigureError,
    PhotoConfigureStoryError,
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
from instagrapi.utils import gen_password, generate_jazoest
from instagrapi.zones import UTC

logger = logging.getLogger("instagrapi.tests")
ACCOUNT_USERNAME = os.getenv("IG_USERNAME", "username")
ACCOUNT_PASSWORD = os.getenv("IG_PASSWORD", "password*")
ACCOUNT_SESSIONID = os.getenv("IG_SESSIONID", "")
TEST_ACCOUNTS_URL = os.getenv("TEST_ACCOUNTS_URL")

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

    def test_accounts_url(self):
        parts = urlsplit(TEST_ACCOUNTS_URL)
        query = dict(parse_qsl(parts.query, keep_blank_values=True))
        query.setdefault("count", "5")
        return urlunsplit(
            (
                parts.scheme,
                parts.netloc,
                parts.path,
                urlencode(query),
                parts.fragment,
            )
        )

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
        test_accounts_url = self.test_accounts_url()
        print(f"TEST_ACCOUNTS_URL: {test_accounts_url[:8]}...{test_accounts_url[-8:]}")
        resp = requests.get(test_accounts_url, verify=False)
        print("TEST_ACCOUNTS_URL response code: ", resp.status_code)
        last_exc = None
        for attempt, acc in enumerate(resp.json()[:5], start=1):
            print(f"Fresh account attempt {attempt}: %(username)r" % acc)
            settings = dict(acc["client_settings"])
            totp_seed = settings.pop("totp_seed", None)
            cl = Client(settings=settings, proxy=acc["proxy"])
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
            try:
                cl.login(**login_kwargs)
            except Exception as exc:
                last_exc = exc
                print(
                    f"Fresh account attempt {attempt} failed for {acc['username']}: "
                    f"{exc.__class__.__name__} {exc}"
                )
                continue
            cl._user_id = acc.get("user_id")
            return cl
        raise last_exc or RuntimeError("No usable fresh account returned")

    def __init__(self, *args, **kwargs):
        if TEST_ACCOUNTS_URL:
            self.cl = self.fresh_account()
            return super().__init__(*args, **kwargs)
        filename = f"/tmp/instagrapi_tests_client_settings_{ACCOUNT_USERNAME}.json"
        self.cl = Client()
        settings = {}
        try:
            st = os.stat(filename)
            if datetime.fromtimestamp(st.st_mtime) > (
                datetime.now() - timedelta(seconds=3600)
            ):
                # use only fresh session (5 minutes)
                settings = self.cl.load_settings(filename)
        except FileNotFoundError:
            pass
        except JSONDecodeError as e:
            logger.info(
                "JSONDecodeError when read stored client settings. Use empty settings"
            )
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


class ClientPublicTestCase(BaseClientMixin, unittest.TestCase):
    cl = None

    def assertDict(self, obj, data):
        for key, value in data.items():
            if isinstance(value, str) and "..." in value:
                self.assertTrue(value.replace("...", "") in obj[key])
            elif isinstance(value, int):
                self.assertTrue(obj[key] >= value)
            else:
                self.assertEqual(obj[key], value)

    def test_media_info_gql(self):
        media_pk = self.cl.media_pk_from_url("https://www.instagram.com/p/BVDOOolFFxg/")
        m = self.cl.media_info_gql(media_pk)
        self.assertIsInstance(m, Media)
        media = {
            "pk": 1532130876531694688,
            "id": "1532130876531694688_25025320",
            "code": "BVDOOolFFxg",
            "taken_at": datetime(2017, 6, 7, 19, 37, 35, tzinfo=UTC()),
            "media_type": 1,
            "product_type": "",
            "thumbnail_url": "https://...",
            "location": None,
            "comment_count": 6,
            "like_count": 79,
            "has_liked": None,
            "caption_text": "#creepy #creepyclothing",
            "usertags": [],
            "video_url": None,
            "view_count": 0,
            "video_duration": 0.0,
            "title": "",
            "resources": [],
        }
        self.assertDict(m.dict(), media)


class ExtractorsRegressionTestCase(unittest.TestCase):
    def test_extract_resource_v1_handles_empty_candidates(self):
        resource = extract_resource_v1(
            {"pk": "1", "media_type": 1, "image_versions2": {"candidates": []}}
        )
        self.assertIsNone(resource.thumbnail_url)
        self.assertEqual(resource.pk, "1")


class PublicRegressionTestCase(unittest.TestCase):
    def test_public_request_uses_post_for_post_bodies(self):
        client = Client()
        response = Mock()
        response.headers = {"Content-Length": "0"}
        response.raw.tell.return_value = 0
        response.status_code = 200
        response.url = "https://www.instagram.com/api/graphql"
        response.json.return_value = {"status": "ok", "data": {"user": {}}}
        response.raise_for_status.return_value = None

        with mock.patch.object(client.public, "post", return_value=response) as post:
            body = client.public_request(
                "https://www.instagram.com/api/graphql",
                data={"doc_id": "1"},
                return_json=True,
            )

        self.assertEqual(body["status"], "ok")
        post.assert_called_once()

    def test_public_graphql_request_raises_client_graphql_error_when_data_missing(self):
        client = Client()
        body = {
            "errors": [
                {
                    "message": "execution error",
                    "summary": "Incorrect Query",
                    "description": "The query provided was invalid.",
                }
            ],
            "status": "ok",
        }

        with mock.patch.object(client, "public_request", return_value=body):
            with self.assertRaises(ClientGraphqlError) as cm:
                client.public_graphql_request(
                    {"user_id": "123", "include_reel": True},
                    query_hash="ad99dd9d3646cc3c0dda65debcd266a7",
                )

        self.assertIn("Missing 'data' in GraphQL response", str(cm.exception))
        self.assertIn("Incorrect Query", str(cm.exception))

    def test_user_stories_anonymous_does_not_fallback_to_private(self):
        client = Client()

        with mock.patch.object(
            client,
            "user_stories_gql",
            side_effect=ClientGraphqlError("Incorrect Query"),
        ):
            with mock.patch.object(client, "user_stories_v1") as private_fallback:
                with self.assertRaises(ClientGraphqlError) as cm:
                    client.user_stories("4776134209", amount=5)

        private_fallback.assert_not_called()
        self.assertIn("Incorrect Query", str(cm.exception))

    def test_media_info_gql_falls_back_to_a1_on_public_401(self):
        client = Client()
        expected = Mock(spec=Media)

        with mock.patch.object(
            client,
            "public_graphql_request",
            side_effect=ClientUnauthorizedError("401", response=Mock(status_code=401)),
        ):
            with mock.patch.object(
                client, "media_info_a1", return_value=expected
            ) as fallback:
                result = client.media_info_gql("2110901750722920960")

        self.assertIs(result, expected)
        fallback.assert_called_once_with("2110901750722920960")


class NoteMixinRegressionTestCase(unittest.TestCase):
    def test_get_note_helpers_by_user(self):
        client = Client()
        notes = [
            Note(
                id="1",
                text="hello",
                user_id="10",
                user=UserShort(pk="10", username="example"),
                audience=0,
                created_at=datetime(2024, 1, 1, tzinfo=UTC()),
                expires_at=datetime(2024, 1, 2, tzinfo=UTC()),
                is_emoji_only=False,
                has_translation=False,
                note_style=0,
            )
        ]

        note = client.get_note_by_user(notes, "Example")
        self.assertIsNotNone(note)
        self.assertEqual(note.id, "1")
        self.assertEqual(client.get_note_text_by_user(notes, "example"), "hello")
        self.assertIsNone(client.get_note_by_user(notes, "missing"))
        self.assertIsNone(client.get_note_text_by_user(notes, "missing"))


class LocationMixinRegressionTestCase(unittest.TestCase):
    def test_location_search_name_handles_top_search_place_wrapper(self):
        client = Client()
        client.top_search = lambda query: {
            "places": [
                {
                    "place": {
                        "location": {
                            "pk": "123",
                            "name": "Choroni",
                            "address": "Aragua, Venezuela",
                            "lat": 10.5,
                            "lng": -67.6,
                            "facebook_places_id": 456,
                            "external_source": "facebook_places",
                        }
                    }
                }
            ]
        }

        locations = client.location_search_name("Choroni")
        self.assertEqual(len(locations), 1)
        self.assertEqual(locations[0].pk, 123)
        self.assertEqual(locations[0].external_id, 456)

    def test_location_search_pk_returns_exact_match(self):
        client = Client()
        client.location_info = lambda pk: Location(pk=str(pk), name="Choroni")
        client.top_search = lambda query: {
            "places": [
                {"place": {"location": {"pk": "111", "name": "Choroni"}}},
                {
                    "place": {
                        "location": {
                            "pk": "239130043",
                            "name": "Choroni",
                            "facebook_places_id": 108835465815492,
                            "external_source": "facebook_places",
                        }
                    }
                },
            ]
        }

        location = client.location_search_pk(239130043)
        self.assertEqual(location.pk, 239130043)
        self.assertEqual(location.external_id, 108835465815492)


class ChallengeRegressionTestCase(unittest.TestCase):
    def test_auth_platform_challenge_raises_clear_manual_verification_error(self):
        client = Client()
        last_json = {
            "message": "challenge_required",
            "challenge": {"api_path": "/auth_platform/?apc=test-token"},
            "status": "fail",
        }

        with self.assertRaises(ChallengeRequired) as cm:
            client.challenge_resolve(last_json)

        self.assertIn("Manual verification required", str(cm.exception))

    def test_challenge_resolve_simple_fails_fast_when_handler_has_no_code(self):
        client = Client()
        client.username = "example"
        client.last_json = {
            "message": "challenge_required",
            "status": "fail",
            "step_name": "verify_email",
            "step_data": {"email": "e***@example.com"},
        }
        client.challenge_code_handler = lambda *args, **kwargs: False

        with mock.patch("instagrapi.mixins.challenge.time.sleep") as sleep:
            with self.assertRaises(ChallengeRequired) as cm:
                client.challenge_resolve_simple("challenge/test/")

        self.assertIn("Challenge code required", str(cm.exception))
        sleep.assert_not_called()

    def test_challenge_resolve_simple_ufac_www_bloks_raises_clear_manual_error(self):
        client = Client()
        client.username = "example"
        client.last_json = {
            "message": "challenge_required",
            "status": "ok",
            "step_name": "ufac_www_bloks",
            "step_data": {"screen_data": '{"screen_output_payload":{}}'},
            "challenge_context": "dummy",
            "challenge_type_enum_str": "UFAC_WWW_BLOKS",
        }

        with self.assertRaises(ChallengeRequired) as cm:
            client.challenge_resolve_simple("challenge/test/")

        self.assertIn("UFAC web bloks checkpoint", str(cm.exception))

    def test_challenge_resolve_uses_default_context_when_missing(self):
        client = Client()
        client.uuid = "uuid-1"
        client.android_device_id = "android-1"
        last_json = {
            "message": "challenge_required",
            "challenge": {"api_path": "/challenge/12345/nonce-code/"},
            "status": "fail",
        }

        with mock.patch.object(client, "_send_private_request") as send_request:
            with mock.patch.object(
                client, "challenge_resolve_simple", return_value=True
            ) as resolve_simple:
                result = client.challenge_resolve(last_json)

        self.assertTrue(result)
        send_request.assert_called_once()
        self.assertEqual(send_request.call_args.args[0], "challenge/12345/nonce-code/")
        self.assertEqual(
            send_request.call_args.kwargs["params"]["challenge_context"],
            '{"step_name": "", "nonce_code": "nonce-code", "user_id": 12345, "is_stateless": false}',
        )
        resolve_simple.assert_called_once_with("/challenge/12345/nonce-code/")

    def test_challenge_resolve_falls_back_to_contact_form(self):
        client = Client()
        client.last_json = {"message": "challenge_required", "status": "fail"}
        last_json = {
            "message": "challenge_required",
            "challenge": {"api_path": "/challenge/test/"},
            "status": "fail",
        }

        with mock.patch.object(
            client, "_send_private_request", side_effect=ChallengeRequired
        ):
            with mock.patch.object(
                client, "challenge_resolve_contact_form", return_value=True
            ) as contact_form:
                result = client.challenge_resolve(last_json)

        self.assertTrue(result)
        contact_form.assert_called_once_with("/challenge/test/")

    def test_challenge_resolve_contact_form_posts_numeric_email_choice(self):
        client = Client()
        client.user_agent = "Instagram Test"
        fake_session = Mock()
        fake_session.cookies = requests.cookies.cookiejar_from_dict(
            {"csrftoken": "token"}
        )
        fake_session.get.return_value = Mock()
        fake_session.post.return_value = Mock(json=Mock(return_value={}))

        with mock.patch(
            "instagrapi.mixins.challenge.requests.Session", return_value=fake_session
        ):
            with mock.patch("instagrapi.mixins.challenge.time.sleep"):
                with mock.patch.object(
                    client,
                    "handle_challenge_result",
                    side_effect=ChallengeRedirection(),
                ):
                    result = client.challenge_resolve_contact_form("/challenge/test/")

        self.assertTrue(result)
        self.assertEqual(
            fake_session.post.call_args_list[0].args[1]["choice"],
            1,
        )

    def test_challenge_resolve_contact_form_posts_numeric_sms_choice_on_fallback(self):
        client = Client()
        client.user_agent = "Instagram Test"
        fake_session = Mock()
        fake_session.cookies = requests.cookies.cookiejar_from_dict(
            {"csrftoken": "token"}
        )
        fake_session.get.return_value = Mock()
        fake_session.post.side_effect = [
            Mock(json=Mock(return_value={})),
            Mock(json=Mock(return_value={})),
        ]

        with mock.patch(
            "instagrapi.mixins.challenge.requests.Session", return_value=fake_session
        ):
            with mock.patch("instagrapi.mixins.challenge.time.sleep"):
                with mock.patch.object(
                    client,
                    "handle_challenge_result",
                    side_effect=[
                        SelectContactPointRecoveryForm("Need SMS", challenge={}),
                        ChallengeRedirection(),
                    ],
                ):
                    result = client.challenge_resolve_contact_form("/challenge/test/")

        self.assertTrue(result)
        self.assertEqual(fake_session.post.call_args_list[0].args[1]["choice"], 1)
        self.assertEqual(fake_session.post.call_args_list[1].args[1]["choice"], 0)

    def test_handle_challenge_result_raises_recaptcha_form(self):
        client = Client()
        challenge = {
            "challengeType": "RecaptchaChallengeForm",
            "errors": ["Captcha failed"],
        }

        with self.assertRaises(RecaptchaChallengeForm) as cm:
            client.handle_challenge_result(challenge)

        self.assertIn("Captcha failed", str(cm.exception))

    def test_handle_challenge_result_raises_select_contact_point_recovery_form(self):
        client = Client()
        challenge = {
            "challengeType": "SelectContactPointRecoveryForm",
            "errors": ["Need recovery"],
            "extraData": {
                "content": [{"title": "Help us confirm you own this account"}]
            },
        }

        with self.assertRaises(SelectContactPointRecoveryForm) as cm:
            client.handle_challenge_result(challenge)

        self.assertIn("Need recovery", str(cm.exception))

    def test_handle_challenge_result_raises_submit_phone_number_form(self):
        client = Client()
        challenge = {
            "challengeType": "SubmitPhoneNumberForm",
            "fields": {"phone_number": "None"},
        }

        with self.assertRaises(SubmitPhoneNumberForm):
            client.handle_challenge_result(challenge)

    def test_handle_challenge_result_allows_sms_captcha_verification_form(self):
        client = Client()
        challenge = {"challenge": {"challengeType": "VerifySMSCodeFormForSMSCaptcha"}}

        result = client.handle_challenge_result(challenge)

        self.assertEqual(result["challengeType"], "VerifySMSCodeFormForSMSCaptcha")

    def test_handle_challenge_result_rejects_malformed_nested_payload(self):
        client = Client()

        with self.assertRaises(ChallengeError) as cm:
            client.handle_challenge_result({"challenge": "broken"})

        self.assertIn("Malformed nested challenge payload", str(cm.exception))

    def test_handle_challenge_result_unknown_type_includes_context(self):
        client = Client()
        challenge = {
            "challengeType": "SomeNewChallengeForm",
            "errors": ["Need manual action"],
            "extraData": {"content": [{"text": "Open Instagram to continue"}]},
        }

        with self.assertRaises(ChallengeError) as cm:
            client.handle_challenge_result(challenge)

        self.assertIn(
            "Unsupported challenge type: SomeNewChallengeForm", str(cm.exception)
        )
        self.assertIn("Need manual action", str(cm.exception))

    def test_challenge_resolve_simple_select_verify_method_uses_sms_choice_for_code(
        self,
    ):
        client = Client()
        client.last_json = {
            "step_name": "select_verify_method",
            "step_data": {"phone_number": "+1 *** *** 1234"},
            "action": "close",
            "status": "ok",
        }
        client._send_private_request = Mock()
        client.challenge_code_or_raised = Mock(return_value="123456")

        result = client.challenge_resolve_simple("/challenge/test/")

        self.assertTrue(result)
        self.assertEqual(
            client._send_private_request.call_args_list[0].args[1]["choice"], "0"
        )
        self.assertEqual(client.challenge_code_or_raised.call_args.args[0].name, "SMS")
        self.assertEqual(
            client.challenge_code_or_raised.call_args.kwargs["wait_seconds"], 5
        )
        self.assertEqual(
            client.challenge_code_or_raised.call_args.kwargs["attempts"], 24
        )

    def test_challenge_resolve_simple_select_contact_point_recovery_uses_sms_choice_for_code(
        self,
    ):
        client = Client()
        client.last_json = {
            "step_name": "select_contact_point_recovery",
            "step_data": {"phone_number": "+1 *** *** 1234"},
            "action": "close",
            "status": "ok",
        }
        client._send_private_request = Mock(
            side_effect=[
                None,
                None,
            ]
        )
        client.challenge_code_or_raised = Mock(return_value="123456")

        result = client.challenge_resolve_simple("/challenge/test/")

        self.assertTrue(result)
        self.assertEqual(
            client._send_private_request.call_args_list[0].args[1]["choice"], "0"
        )
        self.assertEqual(client.challenge_code_or_raised.call_args.args[0].name, "SMS")

    def test_challenge_resolve_simple_unknown_step_raises_clear_error(self):
        client = Client()
        client.username = "example"
        client.last_json = {
            "step_name": "mystery_step",
            "status": "ok",
        }

        with self.assertRaises(ChallengeUnknownStep) as cm:
            client.challenge_resolve_simple("/challenge/test/")

        self.assertIn('Unknown step_name "mystery_step"', str(cm.exception))

    def test_challenge_resolve_simple_change_password_requires_handler_output(self):
        client = Client()
        client.username = "example"
        client.last_json = {
            "step_name": "change_password",
            "challenge_context": '{"step_name":"change_password"}',
            "status": "ok",
        }
        client.change_password_handler = Mock(return_value="")

        with mock.patch("instagrapi.mixins.challenge.time.sleep"):
            with self.assertRaises(ChallengeRequired) as cm:
                client.challenge_resolve_simple("/challenge/test/")

        self.assertIn("Password change required", str(cm.exception))

    def test_challenge_resolve_simple_recovery_final_step_has_clear_error(self):
        client = Client()
        client.last_json = {
            "step_name": "select_contact_point_recovery",
            "step_data": {"phone_number": "+1 *** *** 1234"},
            "status": "ok",
        }

        def fake_send_private_request(*args, **kwargs):
            if "security_code" in (args[1] if len(args) > 1 else {}):
                client.last_json = {"step_name": "unexpected_step", "status": "ok"}

        client._send_private_request = Mock(side_effect=fake_send_private_request)
        client.challenge_code_or_raised = Mock(return_value="123456")

        with self.assertRaises(ChallengeError) as cm:
            client.challenge_resolve_simple("/challenge/test/")

        self.assertIn("Unexpected final challenge step", str(cm.exception))

    def test_challenge_resolve_contact_form_raises_clear_error_for_unexpected_verify_step(
        self,
    ):
        client = Client()
        client.user_agent = "Instagram Test"
        fake_session = Mock()
        fake_session.cookies = requests.cookies.cookiejar_from_dict(
            {"csrftoken": "token"}
        )
        fake_session.get.return_value = Mock()
        fake_session.post.return_value = Mock(json=Mock(return_value={}))

        with mock.patch(
            "instagrapi.mixins.challenge.requests.Session", return_value=fake_session
        ):
            with mock.patch("instagrapi.mixins.challenge.time.sleep"):
                with mock.patch.object(
                    client,
                    "handle_challenge_result",
                    return_value={"challengeType": "UnexpectedForm"},
                ):
                    with self.assertRaises(ChallengeError) as cm:
                        client.challenge_resolve_contact_form("/challenge/test/")

        self.assertIn("Unexpected contact-form challenge step", str(cm.exception))

    def test_challenge_resolve_contact_form_raises_clear_error_for_detail_mismatch(
        self,
    ):
        client = Client()
        client.user_agent = "Instagram Test"
        client.username = "expected-user"
        fake_session = Mock()
        fake_session.cookies = requests.cookies.cookiejar_from_dict(
            {"csrftoken": "token"}
        )
        fake_session.get.return_value = Mock()
        fake_session.post.side_effect = [
            Mock(json=Mock(return_value={})),
            Mock(
                json=Mock(
                    return_value={
                        "challengeType": "ReviewContactPointChangeForm",
                        "extraData": {"content": []},
                        "navigation": {"forward": "/challenge/forward/"},
                    }
                )
            ),
        ]

        with mock.patch(
            "instagrapi.mixins.challenge.requests.Session", return_value=fake_session
        ):
            with mock.patch("instagrapi.mixins.challenge.time.sleep"):
                with mock.patch.object(
                    client,
                    "handle_challenge_result",
                    return_value={"challengeType": "VerifySMSCodeFormForSMSCaptcha"},
                ):
                    with mock.patch.object(
                        client, "challenge_code_handler", return_value="123456"
                    ):
                        with self.assertRaises(ChallengeError) as cm:
                            client.challenge_resolve_contact_form("/challenge/test/")

        self.assertIn("Data invalid", str(cm.exception))

    def test_challenge_resolve_contact_form_raises_clear_error_for_bad_final_response(
        self,
    ):
        client = Client()
        client.user_agent = "Instagram Test"
        fake_session = Mock()
        fake_session.cookies = requests.cookies.cookiejar_from_dict(
            {"csrftoken": "token"}
        )
        fake_session.get.return_value = Mock()
        fake_session.post.side_effect = [
            Mock(json=Mock(return_value={})),
            Mock(
                json=Mock(
                    return_value={
                        "challengeType": "ReviewContactPointChangeForm",
                        "extraData": {"content": []},
                        "navigation": {"forward": "/challenge/forward/"},
                    }
                )
            ),
            Mock(json=Mock(return_value={"type": "NOPE", "status": "fail"})),
        ]

        with mock.patch(
            "instagrapi.mixins.challenge.requests.Session", return_value=fake_session
        ):
            with mock.patch("instagrapi.mixins.challenge.time.sleep"):
                with mock.patch.object(
                    client,
                    "handle_challenge_result",
                    return_value={"challengeType": "VerifySMSCodeFormForSMSCaptcha"},
                ):
                    with mock.patch.object(
                        client, "challenge_code_handler", return_value="123456"
                    ):
                        with self.assertRaises(ChallengeError) as cm:
                            client.challenge_resolve_contact_form("/challenge/test/")

        self.assertIn(
            "Unexpected final response after contact-form approval", str(cm.exception)
        )


class AuthAndStoryRegressionTestCase(unittest.TestCase):
    def test_login_requires_username_and_password(self):
        client = Client()

        with self.assertRaises(BadCredentials):
            client.login()

    def test_login_continues_after_pre_login_throttling(self):
        client = Client()
        client.username = "example"
        client.password = "password"
        client.authorization_data = {}
        client.last_response = Mock(headers={"ig-set-authorization": "Bearer token"})
        client.parse_authorization = Mock(return_value={"sessionid": "abc"})
        client.pre_login_flow = Mock(side_effect=PleaseWaitFewMinutes())
        client.private_request = Mock(return_value=True)
        client.login_flow = Mock()
        client.password_encrypt = Mock(return_value="enc-password")

        result = client.login()

        self.assertTrue(result)
        client.pre_login_flow.assert_called_once_with()
        client.private_request.assert_called_once()
        client.login_flow.assert_called_once_with()

    def test_login_continues_after_client_throttled_error(self):
        client = Client()
        client.username = "example"
        client.password = "password"
        client.authorization_data = {}
        client.last_response = Mock(headers={"ig-set-authorization": "Bearer token"})
        client.parse_authorization = Mock(return_value={"sessionid": "abc"})
        client.pre_login_flow = Mock(side_effect=ClientThrottledError())
        client.private_request = Mock(return_value=True)
        client.login_flow = Mock()
        client.password_encrypt = Mock(return_value="enc-password")

        result = client.login()

        self.assertTrue(result)
        client.pre_login_flow.assert_called_once_with()
        client.private_request.assert_called_once()
        client.login_flow.assert_called_once_with()

    def test_login_relogin_guard_raises_before_network_calls(self):
        client = Client()
        client.username = "example"
        client.password = "password"
        client.relogin_attempt = 2
        client.private.cookies.set("sessionid", "stale")
        client.public.cookies.set("sessionid", "public-stale")
        client.private.headers["Authorization"] = "Bearer stale"

        with self.assertRaises(ReloginAttemptExceeded):
            client.login(relogin=True)

        self.assertEqual(client.authorization_data, {})
        self.assertNotIn("Authorization", client.private.headers)
        self.assertEqual(client.private.cookies.get_dict(), {})
        self.assertEqual(client.public.cookies.get_dict(), {})

    def test_login_returns_early_when_user_is_already_authorized(self):
        client = Client()
        client.authorization_data = {"ds_user_id": "123"}
        client.pre_login_flow = Mock()
        client.private_request = Mock()

        result = client.login("example", "password")

        self.assertTrue(result)
        client.pre_login_flow.assert_not_called()
        client.private_request.assert_not_called()

    def test_login_uses_stored_username_when_called_without_args(self):
        client = Client()
        client.username = "example"
        client.password = "password"
        client.authorization_data = {}
        client.last_response = Mock(headers={"ig-set-authorization": "Bearer token"})
        client.parse_authorization = Mock(return_value={"sessionid": "abc"})
        client.pre_login_flow = Mock(return_value=True)
        client.private_request = Mock(return_value=True)
        client.login_flow = Mock()
        client.password_encrypt = Mock(return_value="enc-password")

        result = client.login()

        self.assertTrue(result)
        payload = client.private_request.call_args.args[1]
        self.assertEqual(payload["username"], "example")

    def test_login_two_factor_requires_verification_code(self):
        client = Client()
        client.username = "example"
        client.password = "password"
        client.pre_login_flow = Mock(return_value=True)
        client.private_request = Mock(
            side_effect=TwoFactorRequired("Two-factor authentication required")
        )
        client.password_encrypt = Mock(return_value="enc-password")

        with self.assertRaises(TwoFactorRequired) as cm:
            client.login()

        self.assertIn("you did not provide verification_code", str(cm.exception))

    def test_login_two_factor_uses_verification_code_flow(self):
        client = Client()
        client.username = "example"
        client.password = "password"
        client.authorization_data = {}
        client.uuid = "uuid-1"
        client.phone_id = "phone-1"
        client.android_device_id = "android-1"
        client._token = "csrftoken"
        client.last_json = {
            "two_factor_info": {"two_factor_identifier": "two-factor-id"}
        }
        client.last_response = Mock(headers={"ig-set-authorization": "Bearer second"})
        client.parse_authorization = Mock(return_value={"sessionid": "abc"})
        client.pre_login_flow = Mock(return_value=True)
        client.password_encrypt = Mock(return_value="enc-password")
        client.login_flow = Mock()
        client.private_request = Mock(
            side_effect=[
                TwoFactorRequired("Two-factor authentication required"),
                True,
            ]
        )

        result = client.login(verification_code="123456")

        self.assertTrue(result)
        self.assertEqual(client.private_request.call_count, 2)
        first_call = client.private_request.call_args_list[0]
        self.assertEqual(first_call.args[0], "accounts/login/")
        second_call = client.private_request.call_args_list[1]
        self.assertEqual(second_call.args[0], "accounts/two_factor_login/")
        self.assertEqual(second_call.args[1]["verification_code"], "123456")
        self.assertEqual(second_call.args[1]["two_factor_identifier"], "two-factor-id")
        self.assertEqual(second_call.args[1]["username"], "example")
        client.login_flow.assert_called_once_with()

    def test_login_two_factor_invalid_parameters_raises_clear_bloks_hint(self):
        client = Client()
        client.username = "example"
        client.password = "password"
        client.authorization_data = {}
        client.uuid = "uuid-1"
        client.phone_id = "phone-1"
        client.android_device_id = "android-1"
        client._token = "csrftoken"
        client.last_json = {
            "two_factor_info": {"two_factor_identifier": "two-factor-id"}
        }
        client.pre_login_flow = Mock(return_value=True)
        client.password_encrypt = Mock(return_value="enc-password")
        client.private_request = Mock(
            side_effect=[
                TwoFactorRequired("Two-factor authentication required"),
                UnknownError("Invalid Parameters", response=Mock(status_code=400)),
            ]
        )

        with self.assertRaises(TwoFactorRequired) as cm:
            client.login(verification_code="123456")

        self.assertIn("Bloks-based two-factor verification flow", str(cm.exception))
        self.assertEqual(client.private_request.call_count, 2)

    def test_login_by_sessionid_falls_back_to_user_short_gql(self):
        client = Client()
        sessionid = "1234567890123456789012345678901%3Atoken"
        client.user_info_v1 = Mock(side_effect=PrivateError("boom"))
        client.user_short_gql = Mock(
            return_value=UserShort(pk="1234567890123456789", username="example")
        )

        result = client.login_by_sessionid(sessionid)

        self.assertTrue(result)
        client.user_info_v1.assert_called_once_with(1234567890123456789012345678901)
        client.user_short_gql.assert_called_once_with(1234567890123456789012345678901)
        self.assertEqual(client.username, "example")
        self.assertEqual(client.authorization_data["sessionid"], sessionid)
        self.assertEqual(client.cookie_dict["ds_user_id"], "1234567890123456789")

    def test_login_by_sessionid_uses_user_info_v1_when_available(self):
        client = Client()
        sessionid = "1234567890123456789012345678901%3Atoken"
        user = User(
            pk="1234567890123456789",
            username="example",
            full_name="Example",
            is_private=False,
            profile_pic_url="https://example.com/pic.jpg",
            is_verified=False,
            media_count=0,
            follower_count=0,
            following_count=0,
            is_business=False,
        )
        client.user_info_v1 = Mock(return_value=user)
        client.user_short_gql = Mock()

        result = client.login_by_sessionid(sessionid)

        self.assertTrue(result)
        client.user_info_v1.assert_called_once_with(1234567890123456789012345678901)
        client.user_short_gql.assert_not_called()
        self.assertEqual(client.username, "example")
        self.assertEqual(client.cookie_dict["ds_user_id"], "1234567890123456789")

    def test_login_by_sessionid_falls_back_to_user_short_gql_on_validation_error(self):
        client = Client()
        sessionid = "1234567890123456789012345678901%3Atoken"
        client.user_info_v1 = Mock(
            side_effect=ValidationError.from_exception_data("User", [])
        )
        client.user_short_gql = Mock(
            return_value=UserShort(pk="1234567890123456789", username="example")
        )

        result = client.login_by_sessionid(sessionid)

        self.assertTrue(result)
        client.user_info_v1.assert_called_once_with(1234567890123456789012345678901)
        client.user_short_gql.assert_called_once_with(1234567890123456789012345678901)
        self.assertEqual(client.username, "example")

    def test_login_by_sessionid_rejects_invalid_sessionid(self):
        client = Client()

        with self.assertRaises(AssertionError):
            client.login_by_sessionid("short")

    def test_login_by_sessionid_rejects_sessionid_without_numeric_prefix(self):
        client = Client()

        with self.assertRaises(AssertionError):
            client.login_by_sessionid("abcdefghijklmnopqrstuvwxyz123456")

    def test_login_resets_relogin_attempt_after_success(self):
        client = Client()
        client.username = "example"
        client.password = "password"
        client.authorization_data = {}
        client.relogin_attempt = 1
        client.last_response = Mock(headers={"ig-set-authorization": "Bearer token"})
        client.parse_authorization = Mock(return_value={"sessionid": "abc"})
        client.pre_login_flow = Mock(return_value=True)
        client.private_request = Mock(return_value=True)
        client.login_flow = Mock()
        client.password_encrypt = Mock(return_value="enc-password")

        result = client.login(relogin=True)

        self.assertTrue(result)
        self.assertEqual(client.relogin_attempt, 0)

    def test_user_stories_authenticated_falls_back_to_private(self):
        client = Client()
        client.authorization_data = {"ds_user_id": "123"}
        expected = [Mock(spec=Story)]

        with mock.patch.object(
            client,
            "user_stories_gql",
            side_effect=ClientGraphqlError("Incorrect Query"),
        ):
            with mock.patch.object(
                client, "user_stories_v1", return_value=expected
            ) as private_fallback:
                result = client.user_stories("4776134209", amount=5)

        private_fallback.assert_called_once_with("4776134209", 5)
        self.assertEqual(result, expected)

    def test_init_does_not_leave_blank_authorization_header(self):
        client = Client()
        client.set_settings({})
        client.private.headers["Authorization"] = "Bearer stale"

        client.init()

        self.assertNotIn("Authorization", client.private.headers)

    def test_init_clears_stale_private_cookies_when_settings_have_no_cookies(self):
        client = Client()
        client.private.cookies.set("sessionid", "stale-session")
        client.private.cookies.set("ds_user_id", "12345")
        client.set_settings({})

        self.assertEqual(client.private.cookies.get_dict(), {})
        self.assertIsNone(client.sessionid)
        self.assertIsNone(client.user_id)

    def test_init_clears_stale_ig_u_rur_header_when_settings_have_no_value(self):
        client = Client()
        client.private.headers["IG-U-RUR"] = "stale-rur"
        client.set_settings({})

        self.assertNotIn("IG-U-RUR", client.private.headers)

    def test_sessionid_falls_back_to_authorization_data(self):
        client = Client()
        client.private.cookies.clear()
        client.authorization_data = {"sessionid": "auth-session"}

        self.assertEqual(client.sessionid, "auth-session")

    def test_user_id_falls_back_to_authorization_data(self):
        client = Client()
        client.private.cookies.clear()
        client.authorization_data = {"ds_user_id": "12345"}

        self.assertEqual(client.user_id, 12345)

    def test_inject_sessionid_to_public_uses_authorization_fallback(self):
        client = Client()
        client.private.cookies.clear()
        client.authorization_data = {"sessionid": "auth-session"}

        result = client.inject_sessionid_to_public()

        self.assertTrue(result)
        self.assertEqual(client.public.cookies.get("sessionid"), "auth-session")

    def test_inject_sessionid_to_public_returns_false_without_sessionid(self):
        client = Client()

        result = client.inject_sessionid_to_public()

        self.assertFalse(result)
        self.assertIsNone(client.public.cookies.get("sessionid"))

    def test_logout_clears_local_session_state_after_success(self):
        client = Client()
        client.authorization_data = {"sessionid": "auth-session", "ds_user_id": "12345"}
        client.last_login = 123.0
        client.relogin_attempt = 1
        client.private.headers["Authorization"] = "Bearer stale"
        client.private.cookies.set("sessionid", "private-session")
        client.public.cookies.set("sessionid", "public-session")
        client.private_request = Mock(return_value={"status": "ok"})

        result = client.logout()

        self.assertTrue(result)
        self.assertEqual(client.authorization_data, {})
        self.assertIsNone(client.last_login)
        self.assertEqual(client.relogin_attempt, 0)
        self.assertNotIn("Authorization", client.private.headers)
        self.assertEqual(client.private.cookies.get_dict(), {})
        self.assertEqual(client.public.cookies.get_dict(), {})

    def test_parse_authorization_returns_empty_dict_for_missing_header(self):
        client = Client()
        client.logger = Mock()

        result = client.parse_authorization(None)

        self.assertEqual(result, {})
        client.logger.exception.assert_not_called()

    def test_parse_authorization_decodes_valid_bearer_header(self):
        client = Client()
        authorization = (
            "Bearer IGT:2:eyJzZXNzaW9uaWQiOiAiYWJjIiwgImRzX3VzZXJfaWQiOiAiMTIzIn0="
        )

        result = client.parse_authorization(authorization)

        self.assertEqual(result, {"sessionid": "abc", "ds_user_id": "123"})


class ClientTestCase(unittest.TestCase):
    def test_default_settings_are_not_shared_between_clients(self):
        first = Client()
        second = Client()

        first.set_retry_config(session_retry_total=9)

        self.assertEqual(first.settings["session_retry_total"], 9)
        self.assertEqual(second.settings["session_retry_total"], 3)

    def test_jazoest(self):
        phone_id = "57d64c41-a916-3fa5-bd7a-3796c1dab122"
        self.assertTrue(generate_jazoest(phone_id), "22413")

    def test_lg(self):
        settings = {
            "uuids": {
                "phone_id": "57d64c41-a916-3fa5-bd7a-3796c1dab122",
                "uuid": "8aa373c6-f316-44d7-b49e-d74563f4a8f3",
                "client_session_id": "6c296d0a-3534-4dce-b5aa-a6a6ab017443",
                "advertising_id": "8dc88b76-dfbc-44dc-abbc-31a6f1d54b04",
                "android_device_id": "android-e021b636049dc0e9",
                "request_id": "72d0f808-b5cd-40e2-910b-01ae7ae60a5b",
                "tray_session_id": "bc44ef1d-c083-4ecd-b369-6f4a9e1a077c",
            },
            "mid": "YA1YMAACAAGtxxnZ1p4AYc8ufNMn",
            "device_settings": {
                "cpu": "h1",
                "dpi": "640dpi",
                "model": "h1",
                "device": "RS988",
                "resolution": "1440x2392",
                "app_version": "269.0.0.19.301",
                "manufacturer": "LGE/lge",
                "version_code": "168361634",
                "android_release": "6.0.1",
                "android_version": 23,
            },
            # "user_agent": "Instagram 117.0.0.28.123 Android (23/6.0.1; US; 168361634)"
            "user_agent": "Instagram 269.0.0.19.301 Android (27/8.1.0; 480dpi; 1080x1776; motorola; Moto G (5S); montana; qcom; ru_RU; 253447809)",
            "country": "RU",
            "locale": "ru_RU",
            "timezone_offset": 10800,  # Moscow, GMT+3
        }
        cl = Client(settings)
        cl.login(ACCOUNT_USERNAME, ACCOUNT_PASSWORD)
        self.assertIsInstance(cl.user_id, int)
        self.assertEqual(cl.username, ACCOUNT_USERNAME)

    def test_country_locale_timezone(self):
        cl = Client()
        # defaults:
        self.assertEqual(cl.country, "US")
        self.assertEqual(cl.locale, "en_US")
        self.assertEqual(cl.timezone_offset, -14400)
        settings = {
            "uuids": {
                "phone_id": "57d64c41-a916-3fa5-bd7a-3796c1dab122",
                "uuid": "8aa373c6-f316-44d7-b49e-d74563f4a8f3",
                "client_session_id": "6c296d0a-3534-4dce-b5aa-a6a6ab017443",
                "advertising_id": "8dc88b76-dfbc-44dc-abbc-31a6f1d54b04",
                "android_device_id": "android-e021b636049dc0e9",
                "request_id": "72d0f808-b5cd-40e2-910b-01ae7ae60a5b",
                "tray_session_id": "bc44ef1d-c083-4ecd-b369-6f4a9e1a077c",
            },
            "mid": "YA1YMAACAAGtxxnZ1p4AYc8ufNMn",
            "device_settings": {
                "app_version": "269.0.0.19.301",
                "android_version": 26,
                "android_release": "8.0.0",
                "dpi": "480dpi",
                "resolution": "1080x1920",
                "manufacturer": "Xiaomi",
                "device": "capricorn",
                "model": "MI 5s",
                "cpu": "qcom",
                "version_code": "301484483",
            },
            "user_agent": "Instagram 269.0.0.19.301 Android (26/8.0.0; 480dpi; 1080x1920; Xiaomi; MI 5s; capricorn; qcom; en_US; 301484483)",
            "country": "UK",
            "locale": "en_US",
            "timezone_offset": 3600,  # London, GMT+1
        }
        device = {
            "app_version": "165.1.0.20.119",
            "android_version": 27,
            "android_release": "8.1.0",
            "dpi": "480dpi",
            "resolution": "1080x1776",
            "manufacturer": "motorola",
            "device": "Moto G (5S)",
            "model": "montana",
            "cpu": "qcom",
            "version_code": "253447809",
        }
        # change settings
        cl.set_settings(settings)

        def check(country, locale, timezone_offset):
            self.assertDictEqual(cl.get_settings()["uuids"], settings["uuids"])
            self.assertEqual(cl.country, country)
            self.assertEqual(cl.locale, locale)
            self.assertEqual(cl.timezone_offset, timezone_offset)
            self.assertIn(cl.locale, cl.user_agent)

        cl.set_country("AU")  # change only country
        check("AU", "en_US", 3600)
        cl.set_locale("ru_RU")  # locale change country
        check("RU", "ru_RU", 3600)
        cl.set_timezone_offset(10800)  # change timezone_offset
        check("RU", "ru_RU", 10800)
        cl.set_user_agent("TEST")  # change user-agent
        self.assertEqual(cl.get_settings()["user_agent"], "TEST")
        cl.set_device(device)  # change device
        self.assertDictEqual(cl.get_settings()["device_settings"], device)
        cl.set_settings(settings)  # load source settings
        check("UK", "en_US", 3600)
        self.assertEqual(cl.get_settings()["user_agent"], settings["user_agent"])
        self.assertEqual(
            cl.get_settings()["device_settings"], settings["device_settings"]
        )

    def test_media_pk_from_share_url(self):
        cl = Client()
        response = Mock(
            headers={"Location": "https://www.instagram.com/p/DC2konOtSse/"}
        )
        with mock.patch.object(cl.public, "get", return_value=response) as public_get:
            self.assertEqual(
                cl.media_pk_from_url("https://www.instagram.com/share/p/BALv9Ep4YH"),
                cl.media_pk_from_code("DC2konOtSse"),
            )
        public_get.assert_called_once()

    def test_set_retry_config_updates_settings_and_session_adapters(self):
        cl = Client()
        cl.set_retry_config(
            request_timeout=0,
            public_request_retries_count=5,
            public_request_retries_timeout=4,
            session_retry_total=6,
            session_retry_backoff_factor=1,
            session_retry_statuses=[429, 500],
        )

        settings = cl.get_settings()
        self.assertEqual(settings["request_timeout"], 0)
        self.assertEqual(settings["public_request_retries_count"], 5)
        self.assertEqual(settings["public_request_retries_timeout"], 4)
        self.assertEqual(settings["session_retry_total"], 6)
        self.assertEqual(settings["session_retry_backoff_factor"], 1)
        self.assertEqual(settings["session_retry_statuses"], [429, 500])

        public_retry = cl.public.adapters["https://"].max_retries
        private_retry = cl.private.adapters["https://"].max_retries
        self.assertEqual(public_retry.total, 6)
        self.assertEqual(private_retry.total, 6)
        self.assertEqual(public_retry.backoff_factor, 1)
        self.assertEqual(private_retry.backoff_factor, 1)
        self.assertEqual(sorted(public_retry.status_forcelist), [429, 500])
        self.assertEqual(sorted(private_retry.status_forcelist), [429, 500])

    def test_settings_round_trip_preserves_retry_config(self):
        settings = {
            "uuids": {},
            "cookies": {},
            "device_settings": {},
            "request_timeout": 0,
            "public_request_retries_count": 4,
            "public_request_retries_timeout": 3,
            "session_retry_total": 7,
            "session_retry_backoff_factor": 1,
            "session_retry_statuses": [429, 503],
        }
        cl = Client()
        cl.set_settings(settings)

        self.assertEqual(cl.request_timeout, 0)
        self.assertEqual(cl.public_request_retries_count, 4)
        self.assertEqual(cl.public_request_retries_timeout, 3)
        self.assertEqual(cl.session_retry_total, 7)
        self.assertEqual(cl.session_retry_backoff_factor, 1)
        self.assertEqual(cl.session_retry_statuses, [429, 503])
        self.assertEqual(cl.public.adapters["https://"].max_retries.total, 7)
        self.assertEqual(cl.private.adapters["https://"].max_retries.total, 7)

    def test_public_request_uses_client_retry_defaults(self):
        cl = Client(
            request_timeout=0,
            public_request_retries_count=4,
            public_request_retries_timeout=0,
        )
        attempts = {"count": 0}

        def fake_send(*args, **kwargs):
            attempts["count"] += 1
            if attempts["count"] < 4:
                raise ClientConnectionError("temporary")
            return {"status": "ok"}

        with mock.patch.object(cl, "_send_public_request", side_effect=fake_send):
            result = cl.public_request("https://example.com", return_json=True)

        self.assertEqual(attempts["count"], 4)
        self.assertEqual(result, {"status": "ok"})


class DownloadRegressionTestCase(unittest.TestCase):
    def test_photo_download_by_url_skips_existing_file_when_overwrite_disabled(self):
        client = Client()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "photo.jpg"
            path.write_bytes(b"existing-photo")

            with mock.patch("instagrapi.mixins.photo.requests.get") as get:
                result = client.photo_download_by_url(
                    "https://example.com/photo.jpg",
                    folder=tmpdir,
                    overwrite=False,
                )

            get.assert_not_called()
            self.assertEqual(result, path.resolve())
            self.assertEqual(path.read_bytes(), b"existing-photo")

    def test_video_download_by_url_skips_existing_file_when_overwrite_disabled(self):
        client = Client()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "video.mp4"
            path.write_bytes(b"existing-video")

            with mock.patch("instagrapi.mixins.video.requests.get") as get:
                result = client.video_download_by_url(
                    "https://example.com/video.mp4",
                    folder=tmpdir,
                    overwrite=False,
                )

            get.assert_not_called()
            self.assertEqual(result, path.resolve())
            self.assertEqual(path.read_bytes(), b"existing-video")

    def test_album_download_by_urls_propagates_overwrite_flag(self):
        client = Client()
        with mock.patch.object(client, "photo_download_by_url") as photo_download:
            with mock.patch.object(client, "video_download_by_url") as video_download:
                client.album_download_by_urls(
                    [
                        "https://example.com/picture.jpg",
                        "https://example.com/movie.mp4",
                    ],
                    folder="/tmp",
                    overwrite=False,
                )

        photo_download.assert_called_once_with(
            "https://example.com/picture.jpg",
            "picture.jpg",
            "/tmp",
            overwrite=False,
        )
        video_download.assert_called_once_with(
            "https://example.com/movie.mp4",
            "movie.mp4",
            "/tmp",
            overwrite=False,
        )


class ClientDeviceTestCase(ClientPrivateTestCase):
    def test_set_device(self):
        fields = ["uuids", "cookies", "last_login", "device_settings", "user_agent"]
        for field in fields:
            settings = self.cl.get_settings()
            self.assertIn(field, settings)
        device = {
            "app_version": "165.1.0.20.119",
            "android_version": 27,
            "android_release": "8.1.0",
            "dpi": "480dpi",
            "resolution": "1080x1776",
            "manufacturer": "motorola",
            "device": "Moto G (5S)",
            "model": "montana",
            "cpu": "qcom",
            "version_code": "253447809",
        }
        user_agent = "Instagram 165.1.0.29.119 Android (27/8.1.0; 480dpi; 1080x1776; motorola; Moto G (5S); montana; qcom; ru_RU; 253447809)"
        self.cl.set_device(device)
        self.cl.set_user_agent(user_agent)
        settings = self.cl.get_settings()
        self.assertDictEqual(device, settings["device_settings"])
        self.assertEqual(user_agent, settings["user_agent"])
        self.user_info_by_username("example")
        request_user_agent = self.cl.last_response.request.headers.get("User-Agent")
        self.assertEqual(user_agent, request_user_agent)


class ClientDeviceAgentTestCase(ClientPrivateTestCase):
    def test_set_device_agent(self):
        device = {
            "app_version": "165.1.0.20.119",
            "android_version": 27,
            "android_release": "8.1.0",
            "dpi": "480dpi",
            "resolution": "1080x1776",
            "manufacturer": "motorola",
            "device": "Moto G (5S)",
            "model": "montana",
            "cpu": "qcom",
            "version_code": "253447809",
        }
        user_agent = "Instagram 165.1.0.29.119 Android (27/8.1.0; 480dpi; 1080x1776; motorola; Moto G (5S); montana; qcom; ru_RU; 253447809)"
        cl = Client()
        cl.set_device(device)
        cl.set_user_agent(user_agent)
        cl.login(ACCOUNT_USERNAME, ACCOUNT_PASSWORD)
        self.assertDictEqual(device, cl.settings["device_settings"])
        self.assertEqual(user_agent, cl.settings["user_agent"])


class ClientUserTestCase(ClientPrivateTestCase):
    def test_user_followers(self):
        user_id = self.user_id_from_username("instagram")
        followers = self.cl.user_followers(user_id, amount=10)
        self.assertTrue(len(followers) == 10)
        self.assertIsInstance(list(followers.values())[0], UserShort)


class ClientUserExtendTestCase(ClientPrivateTestCase):
    def test_username_from_user_id(self):
        self.assertEqual(self.cl.username_from_user_id(25025320), "instagram")

    def test_user_following(self):
        user_id = self.user_id_from_username("instagram")
        self.cl.user_follow(user_id)
        following = self.cl.user_following(self.cl.user_id, amount=1)
        self.assertIn(user_id, following)
        self.assertEqual(following[user_id].username, "instagram")
        self.assertTrue(len(following) == 1)
        self.assertIsInstance(list(following.values())[0], UserShort)

    def test_user_info(self):
        user_id = self.user_id_from_username("instagram")
        user = self.cl.user_info(user_id)
        self.assertIsInstance(user, User)
        for key, value in {
            "biography": "...Instagram...",
            "external_url": "https://...",
            "full_name": "Instagram",
            "pk": "25025320",
            "is_private": False,
            "is_verified": True,
            "profile_pic_url": "https://...",
            "username": "instagram",
        }.items():
            if isinstance(value, str) and "..." in value:
                self.assertTrue(value.replace("...", "") in getattr(user, key))
            else:
                self.assertEqual(value, getattr(user, key))

    def test_user_info_by_username(self):
        user = self.user_info_by_username("instagram")
        self.assertIsInstance(user, User)
        self.assertEqual(user.pk, "25025320")
        self.assertEqual(user.full_name, "Instagram")
        self.assertFalse(user.is_private)

    def test_user_medias(self):
        user_id = self.user_id_from_username("instagram")
        medias = self.cl.user_medias(user_id, amount=10)
        self.assertGreater(len(medias), 5)
        media = medias[0]
        self.assertIsInstance(media, Media)
        for field in REQUIRED_MEDIA_FIELDS:
            self.assertTrue(hasattr(media, field))

    def test_usertag_medias(self):
        user_id = self.user_id_from_username("instagram")
        medias = self.cl.usertag_medias(user_id, amount=10)
        self.assertGreater(len(medias), 5)
        media = medias[0]
        self.assertIsInstance(media, Media)
        for field in REQUIRED_MEDIA_FIELDS:
            self.assertTrue(hasattr(media, field))

    def test_user_follow_unfollow(self):
        user_id = self.user_id_from_username("instagram")
        self.cl.user_follow(user_id)
        following = self.cl.user_following(self.cl.user_id)
        self.assertIn(user_id, following)
        self.cl.user_unfollow(user_id)
        following = self.cl.user_following(self.cl.user_id)
        self.assertNotIn(user_id, following)

    # def test_send_new_note(self):
    #     self.cl.create_note("Hello from Instagrapi!", 0)


class ClientMediaTestCase(ClientPrivateTestCase):
    def test_media_id(self):
        self.assertEqual(
            self.cl.media_id(3258619191829745894), "3258619191829745894_25025320"
        )

    def test_media_pk(self):
        self.assertEqual(
            self.cl.media_pk("2154602296692269830_25025320"), "2154602296692269830"
        )

    def test_media_pk_from_code(self):
        self.assertEqual(
            self.cl.media_pk_from_code("B-fKL9qpeab"), "2278584739065882267"
        )
        self.assertEqual(
            self.cl.media_pk_from_code("B8jnuB2HAbyc0q001y3F9CHRSoqEljK_dgkJjo0"),
            "2243811726252050162",
        )

    def test_code_from_media_pk(self):
        self.assertEqual(self.cl.media_code_from_pk(2278584739065882267), "B-fKL9qpeab")
        self.assertEqual(self.cl.media_code_from_pk(2243811726252050162), "B8jnuB2HAby")

    def test_media_pk_from_url(self):
        self.assertEqual(
            self.cl.media_pk_from_url("https://instagram.com/p/B1LbfVPlwIA/"),
            "2110901750722920960",
        )
        self.assertEqual(
            self.cl.media_pk_from_url(
                "https://www.instagram.com/p/B-fKL9qpeab/?igshid=1xm76zkq7o1im"
            ),
            "2278584739065882267",
        )


class ClientMediaExtendTestCase(ClientPrivateTestCase):
    def test_media_user(self):
        user = self.cl.media_user(2154602296692269830)
        self.assertIsInstance(user, UserShort)
        for key, val in {
            "pk": "25025320",
            "username": "instagram",
            "full_name": "Instagram",
            "is_private": False,
        }.items():
            self.assertEqual(getattr(user, key), val)
        self.assertTrue(user.profile_pic_url.startswith("https://"))

    def test_media_oembed(self):
        media_oembed = self.cl.media_oembed("https://www.instagram.com/p/B3mr1-OlWMG/")
        self.assertIsInstance(media_oembed, MediaOembed)
        for key, val in {
            "title": "В гостях у ДК @delai_krasivo_kaifui",
            "author_name": "instagram",
            "author_url": "https://www.instagram.com/instagram",
            "author_id": "25025320",
            "media_id": "2154602296692269830_25025320",
            "width": 658,
            "height": None,
            "thumbnail_width": 640,
            "thumbnail_height": 480,
            "can_view": True,
        }.items():
            self.assertEqual(getattr(media_oembed, key), val)
        self.assertTrue(media_oembed.thumbnail_url.startswith("http"))

    def test_media_likers(self):
        media = self.cl.user_medias(self.cl.user_id, amount=3)[-1]
        self.assertIsInstance(media, Media)
        likers = self.cl.media_likers(media.pk)
        self.assertTrue(len(likers) > 0)
        self.assertIsInstance(likers[0], UserShort)

    def test_media_like_by_pk(self):
        media_pk = self.cl.media_pk_from_url("https://www.instagram.com/p/ByU3LAslgWY/")
        self.assertTrue(self.cl.media_like(media_pk))

    def test_media_edit(self):
        # Upload photo
        media_pk = self.cl.media_pk_from_url("https://www.instagram.com/p/BVDOOolFFxg/")
        path = self.cl.photo_download(media_pk)
        self.assertIsInstance(path, Path)
        try:
            msg = "Test caption for photo"
            media = self.cl.photo_upload(path, msg)
            self.assertIsInstance(media, Media)
            self.assertEqual(media.caption_text, msg)
            # Change caption
            msg = "New caption %s" % random.randint(1, 100)
            self.cl.media_edit(media.pk, msg)
            media = self.cl.media_info(media.pk)
            self.assertIsInstance(media, Media)
            self.assertEqual(media.caption_text, msg)
            self.assertTrue(self.cl.media_delete(media.pk))
        finally:
            cleanup(path)

    def test_media_edit_igtv(self):
        media_pk = self.cl.media_pk_from_url(
            "https://www.instagram.com/tv/B91gKCcpnTk/"
        )
        path = self.cl.igtv_download(media_pk)
        self.assertIsInstance(path, Path)
        try:
            media = self.cl.igtv_upload(path, "Test title", "Test caption for IGTV")
            self.assertIsInstance(media, Media)
            # Enter title
            title = "Title %s" % random.randint(1, 100)
            msg = "New caption %s" % random.randint(1, 100)
            self.cl.media_edit(media.pk, msg, title)
            media = self.cl.media_info(media.pk)
            self.assertIsInstance(media, Media)
            self.assertEqual(media.title, title)
            self.assertEqual(media.caption_text, msg)
            # Split caption to title and caption
            title = "Title %s" % random.randint(1, 100)
            msg = "New caption %s" % random.randint(1, 100)
            self.cl.media_edit(media.pk, f"{title}\n{msg}")
            media = self.cl.media_info(media.pk)
            self.assertIsInstance(media, Media)
            self.assertEqual(media.title, title)
            self.assertEqual(media.caption_text, msg)
            # Empty title (duplicate one-line caption)
            msg = "New caption %s" % random.randint(1, 100)
            self.cl.media_edit(media.pk, msg, "")
            media = self.cl.media_info(media.pk)
            self.assertIsInstance(media, Media)
            self.assertEqual(media.title, msg)
            self.assertEqual(media.caption_text, msg)
            self.assertTrue(self.cl.media_delete(media.id))
        finally:
            cleanup(path)

    def test_media_like_and_unlike(self):
        media_pk = self.cl.media_pk_from_url("https://www.instagram.com/p/B3mr1-OlWMG/")
        self.assertTrue(self.cl.media_unlike(media_pk))
        media = self.cl.media_info_v1(media_pk)
        like_count = int(media.like_count)
        # like
        self.assertTrue(self.cl.media_like(media.id))
        media = self.cl.media_info_v1(media_pk)  # refresh after like
        new_like_count = int(media.like_count)
        self.assertEqual(new_like_count, like_count + 1)
        # unlike
        self.assertTrue(self.cl.media_unlike(media.id))
        media = self.cl.media_info_v1(media_pk)  # refresh after unlike
        self.assertEqual(media.like_count, like_count)


class ClientCommentTestCase(ClientPrivateTestCase):
    def test_media_comments_amount(self):
        comments = self.cl.media_comments_v1(2154602296692269830, amount=2)
        self.assertTrue(len(comments) == 2)
        comments = self.cl.media_comments_v1(2154602296692269830, amount=0)
        self.assertTrue(len(comments) > 2)

    def test_media_comments(self):
        comments = self.cl.media_comments_v1(2154602296692269830)
        self.assertTrue(len(comments) > 5)
        comment = comments[0]
        self.assertIsInstance(comment, Comment)
        comment_fields = comment.__fields__.keys()
        user_fields = comment.user.__fields__.keys()
        for field in ["pk", "text", "created_at_utc", "content_type", "status", "user"]:
            self.assertIn(field, comment_fields)
        for field in [
            "pk",
            "username",
            "full_name",
            "profile_pic_url",
        ]:
            self.assertIn(field, user_fields)


class ClientCommentExtendTestCase(ClientPrivateTestCase):
    def test_media_comment(self):
        text = "Test text [%s]" % datetime.now().strftime("%s")
        now = datetime.now(tz=UTC())
        comment = self.cl.media_comment_v1(2276404890775267248, text)
        self.assertIsInstance(comment, Comment)
        comment = comment.dict()
        for key, val in {
            "text": text,
            "content_type": "comment",
            "status": "Active",
        }.items():
            self.assertEqual(comment[key], val)
        self.assertIn("pk", comment)
        # The comment was written no more than 120 seconds ago
        self.assertTrue(abs((now - comment["created_at_utc"]).total_seconds()) <= 120)
        user_fields = comment["user"].keys()
        for field in ["pk", "username", "full_name", "profile_pic_url"]:
            self.assertIn(field, user_fields)

    def test_comment_like_and_unlike(self):
        media_pk = self.cl.media_pk_from_url("https://www.instagram.com/p/B3mr1-OlWMG/")
        comment = self.cl.media_comments_v1(media_pk)[0]
        if comment.has_liked:
            self.assertTrue(self.cl.comment_unlike(comment.pk))
        like_count = int(comment.like_count)
        # like
        self.assertTrue(self.cl.comment_like(comment.pk))
        comment = self.cl.media_comments(media_pk)[0]
        new_like_count = int(comment.like_count)
        self.assertEqual(new_like_count, like_count + 1)
        # unlike
        self.assertTrue(self.cl.comment_unlike(comment.pk))
        comment = self.cl.media_comments(media_pk)[0]
        self.assertEqual(comment.like_count, like_count)


class ClientCompareExtractTestCase(ClientPrivateTestCase):
    def assertLocation(self, v1, gql):
        if not isinstance(v1, dict):
            return self.assertEqual(v1, gql)
        for key, val in v1.items():
            if key == "external_id":
                continue  # id may differ
            gql_val = gql[key]
            if isinstance(val, float):
                val, gql_val = round(val, 4), round(gql_val, 4)
            self.assertEqual(val, gql_val)

    def assertMedia(self, v1, gql):
        self.assertTrue(v1.pop("comment_count") <= gql.pop("comment_count"))
        self.assertLocation(v1.pop("location"), gql.pop("location"))
        v1.pop("has_liked")
        gql.pop("has_liked")
        self.assertDictEqual(v1, gql)

    def media_info(self, media_pk):
        media_v1 = self.cl.media_info_v1(media_pk)
        self.assertIsInstance(media_v1, Media)
        media_gql = self.cl.media_info_gql(media_pk)
        self.assertIsInstance(media_gql, Media)
        return media_v1.dict(), media_gql.dict()

    def test_two_extract_media_photo(self):
        media_v1, media_gql = self.media_info(self.cl.media_pk_from_code("B3mr1-OlWMG"))
        self.assertTrue(media_v1.pop("thumbnail_url").startswith("https://"))
        self.assertTrue(media_gql.pop("thumbnail_url").startswith("https://"))
        self.assertMedia(media_v1, media_gql)

    def test_two_extract_media_video(self):
        media_v1, media_gql = self.media_info(self.cl.media_pk_from_code("B3rFQPblq40"))
        self.assertTrue(media_v1.pop("video_url").startswith("https://"))
        self.assertTrue(media_gql.pop("video_url").startswith("https://"))
        self.assertTrue(media_v1.pop("thumbnail_url").startswith("https://"))
        self.assertTrue(media_gql.pop("thumbnail_url").startswith("https://"))
        self.assertMedia(media_v1, media_gql)

    def test_two_extract_media_album(self):
        media_v1, media_gql = self.media_info(self.cl.media_pk_from_code("BjNLpA1AhXM"))
        for res in media_v1["resources"]:
            self.assertTrue(res.pop("thumbnail_url").startswith("https://"))
            if res["media_type"] == 2:
                self.assertTrue(res.pop("video_url").startswith("https://"))
        for res in media_gql["resources"]:
            self.assertTrue(res.pop("thumbnail_url").startswith("https://"))
            if res["media_type"] == 2:
                self.assertTrue(res.pop("video_url").startswith("https://"))
        self.assertMedia(media_v1, media_gql)

    def test_two_extract_media_igtv(self):
        media_v1, media_gql = self.media_info(self.cl.media_pk_from_code("ByYn5ZNlHWf"))
        self.assertTrue(media_v1.pop("video_url").startswith("https://"))
        self.assertTrue(media_gql.pop("video_url").startswith("https://"))
        self.assertTrue(media_v1.pop("thumbnail_url").startswith("https://"))
        self.assertTrue(media_gql.pop("thumbnail_url").startswith("https://"))
        self.assertMedia(media_v1, media_gql)

    def test_two_extract_user(self):
        user_v1 = self.cl.user_info_v1(25025320)
        user_gql = self.cl.user_info_gql(25025320)
        self.assertIsInstance(user_v1, User)
        self.assertIsInstance(user_gql, User)
        user_v1, user_gql = user_v1.dict(), user_gql.dict()
        self.assertTrue(user_v1.pop("profile_pic_url").startswith("https://"))
        self.assertTrue(user_gql.pop("profile_pic_url").startswith("https://"))
        self.assertDictEqual(user_v1, user_gql)


class ClientExtractTestCase(ClientPrivateTestCase):
    def test_extract_media_photo(self):
        media_pk = self.cl.media_pk_from_url("https://www.instagram.com/p/B3mr1-OlWMG/")
        media = self.cl.media_info(media_pk)
        self.assertIsInstance(media, Media)
        self.assertTrue(len(media.resources) == 0)
        self.assertTrue(media.comment_count > 5)
        self.assertTrue(media.like_count > 80)
        for key, val in {
            "caption_text": "В гостях у ДК @delai_krasivo_kaifui",
            "thumbnail_url": "https://",
            "pk": "2154602296692269830",
            "code": "B3mr1-OlWMG",
            "media_type": 1,
            "taken_at": datetime(2019, 10, 14, 15, 57, 10, tzinfo=UTC()),
        }.items():
            if isinstance(val, str):
                self.assertTrue(getattr(media, key).startswith(val))
            else:
                self.assertEqual(getattr(media, key), val)
        for key, val in {"pk": "25025320", "username": "instagram"}.items():
            self.assertEqual(getattr(media.user, key), val)

    def test_extract_media_video(self):
        media_pk = self.cl.media_pk_from_url("https://www.instagram.com/p/BgRIGUQFltp/")
        media = self.cl.media_info(media_pk)
        self.assertIsInstance(media, Media)
        self.assertTrue(len(media.resources) == 0)
        self.assertTrue(media.view_count > 150)
        self.assertTrue(media.comment_count > 1)
        self.assertTrue(media.like_count > 40)
        for key, val in {
            "caption_text": "Веселья ради\n\n@milashensky #dowhill #skateboarding #foros #crimea",
            "pk": 1734202949948037993,
            "code": "BgRIGUQFltp",
            "video_url": "https://",
            "thumbnail_url": "https://",
            "media_type": 2,
            "taken_at": datetime(2018, 3, 13, 14, 59, 23, tzinfo=UTC()),
        }.items():
            if isinstance(val, str):
                self.assertTrue(getattr(media, key).startswith(val))
            else:
                self.assertEqual(getattr(media, key), val)
        for key, val in {"pk": "25025320", "username": "instagram"}.items():
            self.assertEqual(getattr(media.user, key), val)

    def test_extract_media_album(self):
        media_pk = self.cl.media_pk_from_url("https://www.instagram.com/p/BjNLpA1AhXM/")
        media = self.cl.media_info(media_pk)
        self.assertIsInstance(media, Media)
        self.assertTrue(len(media.resources) == 3)
        video_resource = media.resources[0]
        photo_resource = media.resources.pop()
        self.assertTrue(media.view_count == 0)
        self.assertTrue(media.comment_count == 0)
        self.assertTrue(media.like_count > 40)
        for key, val in {
            "caption_text": "@mind__flowers в Форосе под дождём, 24 мая 2018 #downhill "
            "#skateboarding #downhillskateboarding #crimea #foros #rememberwheels",
            "pk": 1787135824035452364,
            "code": "BjNLpA1AhXM",
            "media_type": 8,
            "taken_at": datetime(2018, 5, 25, 15, 46, 53, tzinfo=UTC()),
            "product_type": "",
        }.items():
            self.assertEqual(getattr(media, key), val)
        for key, val in {"pk": "25025320", "username": "instagram"}.items():
            self.assertEqual(getattr(media.user, key), val)
        for key, val in {
            "video_url": "https://",
            "thumbnail_url": "https://",
            "media_type": 2,
            "pk": 1787135361353462176,
        }.items():
            if isinstance(val, str):
                self.assertTrue(getattr(video_resource, key).startswith(val))
            else:
                self.assertEqual(getattr(video_resource, key), val)
        for key, val in {
            "video_url": None,
            "thumbnail_url": "https://",
            "media_type": 1,
            "pk": 1787133803186894424,
        }.items():
            if isinstance(val, str):
                self.assertTrue(getattr(photo_resource, key).startswith(val))
            else:
                self.assertEqual(getattr(photo_resource, key), val)

    def test_extract_media_igtv(self):
        media_pk = self.cl.media_pk_from_url(
            "https://www.instagram.com/tv/ByYn5ZNlHWf/"
        )
        media = self.cl.media_info(media_pk)
        self.assertIsInstance(media, Media)
        self.assertTrue(len(media.resources) == 0)
        self.assertTrue(media.view_count > 200)
        self.assertTrue(media.comment_count > 10)
        self.assertTrue(media.like_count > 50)
        for key, val in {
            "title": "zr trip, crimea, feb 2017. Edit by @milashensky",
            "caption_text": "Нашёл на диске неопубликованное в инсте произведение @milashensky",
            "pk": 2060572297417487775,
            "video_url": "https://",
            "thumbnail_url": "https://",
            "code": "ByYn5ZNlHWf",
            "media_type": 2,
            "taken_at": datetime(2019, 6, 6, 22, 22, 6, tzinfo=UTC()),
            "product_type": "igtv",
        }.items():
            if isinstance(val, str):
                self.assertTrue(getattr(media, key).startswith(val))
            else:
                self.assertEqual(getattr(media, key), val)
        for key, val in {"pk": "25025320", "username": "instagram"}.items():
            self.assertEqual(getattr(media.user, key), val)


class ClienUploadTestCase(ClientPrivateTestCase):
    def get_location(self):
        location = self.cl.location_search(lat=59.939095, lng=30.315868)[0]
        self.assertIsInstance(location, Location)
        return location

    def assertLocation(self, location):
        # Instagram sometimes changes location by GEO coordinates:
        locations = [
            dict(
                pk=213597007,
                name="Palace Square",
                lat=59.939166666667,
                lng=30.315833333333,
            ),
            dict(
                pk=107617247320879,
                name="Russia, Saint-Petersburg",
                address="Russia, Saint-Petersburg",
                lat=59.93318,
                lng=30.30605,
                external_id=107617247320879,
                external_id_source="facebook_places",
            ),
        ]
        for data in locations:
            if data["pk"] == location.pk:
                break
        for key, val in data.items():
            itm = getattr(location, key)
            if isinstance(val, float):
                val = round(val, 2)
                itm = round(itm, 2)
            self.assertEqual(itm, val)

    def test_photo_upload_without_location(self):
        media_pk = self.cl.media_pk_from_url("https://www.instagram.com/p/BVDOOolFFxg/")
        path = self.cl.photo_download(media_pk)
        self.assertIsInstance(path, Path)
        try:
            media = self.cl.photo_upload(path, "Test caption for photo")
            self.assertIsInstance(media, Media)
            self.assertEqual(media.caption_text, "Test caption for photo")
            self.assertFalse(media.location)
        finally:
            cleanup(path)
            self.assertTrue(self.cl.media_delete(media.id))

    def test_photo_upload(self):
        media_pk = self.cl.media_pk_from_url("https://www.instagram.com/p/BVDOOolFFxg/")
        path = self.cl.photo_download(media_pk)
        self.assertIsInstance(path, Path)
        try:
            media = self.cl.photo_upload(
                path, "Test caption for photo", location=self.get_location()
            )
            self.assertIsInstance(media, Media)
            self.assertEqual(media.caption_text, "Test caption for photo")
            self.assertLocation(media.location)
        finally:
            cleanup(path)
            self.assertTrue(self.cl.media_delete(media.id))

    def test_video_upload(self):
        media_pk = self.cl.media_pk_from_url("https://www.instagram.com/p/Bk2tOgogq9V/")
        path = self.cl.video_download(media_pk)
        self.assertIsInstance(path, Path)
        try:
            media = self.cl.video_upload(
                path, "Test caption for video", location=self.get_location()
            )
            self.assertIsInstance(media, Media)
            self.assertEqual(media.caption_text, "Test caption for video")
            self.assertLocation(media.location)
        finally:
            cleanup(path)
            self.assertTrue(self.cl.media_delete(media.id))

    def test_album_upload(self):
        media_pk = self.cl.media_pk_from_url("https://www.instagram.com/p/BjNLpA1AhXM/")
        paths = self.cl.album_download(media_pk)
        [self.assertIsInstance(path, Path) for path in paths]
        try:
            instagram = self.user_info_by_username("instagram")
            usertag = Usertag(user=instagram, x=0.5, y=0.5)
            location = self.get_location()
            media = self.cl.album_upload(
                paths, "Test caption for album", usertags=[usertag], location=location
            )
            self.assertIsInstance(media, Media)
            self.assertEqual(media.caption_text, "Test caption for album")
            self.assertEqual(len(media.resources), 3)
            self.assertLocation(media.location)
            keep_path(media.usertags[0].user)
            keep_path(usertag.user)
            self.assertEqual(media.usertags, [usertag])
        finally:
            cleanup(*paths)
            self.assertTrue(self.cl.media_delete(media.id))

    def test_igtv_upload(self):
        media_pk = self.cl.media_pk_from_url(
            "https://www.instagram.com/tv/B91gKCcpnTk/"
        )
        path = self.cl.igtv_download(media_pk)
        self.assertIsInstance(path, Path)
        try:
            title = "6/6: The Transceiver Failure"
            caption_text = "Test caption for IGTV"
            media = self.cl.igtv_upload(
                path, title, caption_text, location=self.get_location()
            )
            self.assertIsInstance(media, Media)
            self.assertEqual(media.title, title)
            self.assertEqual(media.caption_text, caption_text)
            self.assertLocation(media.location)
        finally:
            cleanup(path)
            self.assertTrue(self.cl.media_delete(media.id))

    def test_clip_upload(self):
        # media_type: 2 (video, not IGTV)
        # product_type: clips
        media_pk = self.cl.media_pk_from_url("https://www.instagram.com/p/CEjXskWJ1on/")
        path = self.cl.clip_download(media_pk)
        self.assertIsInstance(path, Path)
        try:
            # location = self.get_location()
            caption_text = "Upload clip"
            media = self.cl.clip_upload(
                path,
                caption_text,
                # location=location
            )
            self.assertIsInstance(media, Media)
            self.assertEqual(media.caption_text, caption_text)
            # self.assertLocation(media.location)
        finally:
            cleanup(path)
            self.assertTrue(self.cl.media_delete(media.id))

    def test_reel_upload_with_music(self):
        # media_type: 2 (video, not IGTV)
        # product_type: reels

        media_pk = self.cl.media_pk_from_url("https://www.instagram.com/p/CEjXskWJ1on/")
        path = self.cl.clip_download(media_pk)
        self.assertIsInstance(path, Path)
        try:
            title = "Kill My Vibe (feat. Tom G)"
            caption = "Test caption for reel"
            track = self.cl.search_music(title)[0]
            media = self.cl.clip_upload_as_reel_with_music(path, caption, track)
            self.assertIsInstance(media, Media)
            self.assertEqual(media.caption_text, caption)
        finally:
            cleanup(path)
            self.assertTrue(self.cl.media_delete(media.id))


class ClientCollectionTestCase(ClientPrivateTestCase):
    def test_collections(self):
        collections = self.cl.collections()
        self.assertTrue(len(collections) > 0)
        collection = collections[0]
        self.assertIsInstance(collection, Collection)
        for field in ("id", "name", "type", "media_count"):
            self.assertTrue(hasattr(collection, field))

    def test_collection_medias_by_name(self):
        medias = self.cl.collection_medias_by_name("Repost")
        self.assertTrue(len(medias) > 0)
        media = medias[0]
        self.assertIsInstance(media, Media)
        for field in REQUIRED_MEDIA_FIELDS:
            self.assertTrue(hasattr(media, field))

    def test_media_save_to_collection(self):
        media_pk = self.cl.media_pk_from_url("https://www.instagram.com/p/B3mr1-OlWMG/")
        collection_pk = self.cl.collection_pk_by_name("Repost")
        # clear and check
        self.cl.media_unsave(media_pk)
        medias = self.cl.collection_medias(collection_pk)
        self.assertNotIn(media_pk, [m.pk for m in medias])
        # save
        self.cl.media_save(media_pk, collection_pk)
        medias = self.cl.collection_medias(collection_pk)
        self.assertIn(media_pk, [m.pk for m in medias])
        # unsave
        self.cl.media_unsave(media_pk, collection_pk)
        medias = self.cl.collection_medias(collection_pk)
        self.assertNotIn(media_pk, [m.pk for m in medias])


class ClientDirectTestCase(ClientPrivateTestCase):
    def test_direct_thread(self):
        # threads
        threads = self.cl.direct_threads()
        self.assertTrue(len(threads) > 0)
        thread = threads[0]
        self.assertIsInstance(thread, DirectThread)
        # messages
        messages = self.cl.direct_messages(thread.id, 2)
        self.assertTrue(3 > len(messages) > 0)
        # self.assertTrue(thread.is_seen(self.cl.user_id))
        message = messages[0]
        self.assertIsInstance(message, DirectMessage)
        instagram = self.user_id_from_username("instagram")
        ping = self.cl.direct_send("Ping", user_ids=[instagram])
        self.assertIsInstance(ping, DirectMessage)
        pong = self.cl.direct_answer(ping.thread_id, "Pong")
        self.assertIsInstance(pong, DirectMessage)
        self.assertEqual(ping.thread_id, pong.thread_id)
        # send direct photo
        photo = self.cl.direct_send_photo(
            path="examples/kanada.jpg", user_ids=[instagram]
        )
        self.assertIsInstance(photo, DirectMessage)
        self.assertEqual(photo.thread_id, pong.thread_id)
        # send seen
        seen = self.cl.direct_send_seen(thread_id=thread.id)
        self.assertEqual(seen.status, "ok")
        # mute and unmute thread
        self.assertTrue(self.cl.direct_thread_mute(thread.id))
        self.assertTrue(self.cl.direct_thread_unmute(thread.id))
        # mute video call and unmute
        self.assertTrue(self.cl.direct_thread_mute_video_call(thread.id))
        self.assertTrue(self.cl.direct_thread_unmute_video_call(thread.id))

    def test_direct_send_photo(self):
        instagram = self.user_id_from_username("instagram")
        dm = self.cl.direct_send_photo(path="examples/kanada.jpg", user_ids=[instagram])
        self.assertIsInstance(dm, DirectMessage)

    def test_direct_send_video(self):
        instagram = self.user_id_from_username("instagram")
        path = self.cl.video_download(
            self.cl.media_pk_from_url("https://www.instagram.com/p/B3rFQPblq40/")
        )
        dm = self.cl.direct_send_video(path=path, user_ids=[instagram])
        self.assertIsInstance(dm, DirectMessage)

    def test_direct_thread_by_participants(self):
        try:
            self.cl.direct_thread_by_participants([12345])
        except DirectThreadNotFound:
            pass


class ClientDirectMessageTypesTestCase(ClientPrivateTestCase):
    """Test that DirectMessage and DirectThread fields use structured Pydantic models instead of raw dictionaries"""

    def test_direct_message_reactions_model(self):
        """Test that DirectMessage.reactions field uses MessageReactions model"""
        from datetime import datetime

        from instagrapi.types import MessageReaction, MessageReactions

        # Get some direct messages
        threads = self.cl.direct_threads(amount=5)
        if not threads:
            self.skipTest("No direct threads available for testing")

        for thread in threads:
            messages = self.cl.direct_messages(thread.id, amount=10)
            for message in messages:
                if message.reactions:
                    # Test that reactions field is now a MessageReactions object
                    self.assertIsInstance(message.reactions, MessageReactions)

                    # Test that reactions have proper structure
                    if (
                        hasattr(message.reactions, "emojis")
                        and message.reactions.emojis
                    ):
                        for emoji_reaction in message.reactions.emojis:
                            self.assertIsInstance(emoji_reaction, MessageReaction)
                            self.assertIsInstance(emoji_reaction.emoji, str)
                            self.assertIsInstance(emoji_reaction.sender_id, str)
                            self.assertIsInstance(emoji_reaction.timestamp, datetime)

                    # Test backward compatibility - should still work as dict
                    if hasattr(message.reactions, "likes_count"):
                        self.assertIsInstance(message.reactions.likes_count, int)

                    return  # Found one message with reactions, test passed

    def test_direct_message_link_model(self):
        """Test that DirectMessage.link field uses MessageLink model"""
        from instagrapi.types import LinkContext, MessageLink

        # Get some direct messages
        threads = self.cl.direct_threads(amount=5)
        if not threads:
            self.skipTest("No direct threads available for testing")

        for thread in threads:
            messages = self.cl.direct_messages(thread.id, amount=10)
            for message in messages:
                if message.link:
                    # Test that link field is now a MessageLink object
                    self.assertIsInstance(message.link, MessageLink)

                    # Test that link has proper structure
                    if hasattr(message.link, "text"):
                        self.assertIsInstance(message.link.text, str)

                    if (
                        hasattr(message.link, "link_context")
                        and message.link.link_context
                    ):
                        self.assertIsInstance(message.link.link_context, LinkContext)
                        if hasattr(message.link.link_context, "link_url"):
                            self.assertIsInstance(
                                message.link.link_context.link_url, str
                            )

                    return  # Found one message with link, test passed

    def test_direct_message_visual_media_model(self):
        """Test that DirectMessage.visual_media field uses VisualMedia model"""
        from instagrapi.types import VisualMedia, VisualMediaContent

        # Get some direct messages
        threads = self.cl.direct_threads(amount=5)
        if not threads:
            self.skipTest("No direct threads available for testing")

        for thread in threads:
            messages = self.cl.direct_messages(thread.id, amount=10)
            for message in messages:
                if message.visual_media:
                    # Test that visual_media field is now a VisualMedia object
                    self.assertIsInstance(message.visual_media, VisualMedia)

                    # Test that visual_media has proper structure
                    if (
                        hasattr(message.visual_media, "media")
                        and message.visual_media.media
                    ):
                        self.assertIsInstance(
                            message.visual_media.media, VisualMediaContent
                        )

                    return  # Found one message with visual media, test passed

    def test_direct_thread_last_seen_at_model(self):
        """Test that DirectThread.last_seen_at field uses LastSeenInfo model"""
        from datetime import datetime

        from instagrapi.types import LastSeenInfo

        # Get some direct threads
        threads = self.cl.direct_threads(amount=5)
        if not threads:
            self.skipTest("No direct threads available for testing")

        for thread in threads:
            if thread.last_seen_at:
                # Test that last_seen_at is now a dict of LastSeenInfo objects
                for user_id, seen_info in thread.last_seen_at.items():
                    self.assertIsInstance(user_id, str)
                    self.assertIsInstance(seen_info, LastSeenInfo)

                    # Test structure of LastSeenInfo
                    if hasattr(seen_info, "timestamp"):
                        self.assertIsInstance(seen_info.timestamp, datetime)
                    if hasattr(seen_info, "created_at"):
                        self.assertIsInstance(seen_info.created_at, datetime)

                    return  # Found one thread with last_seen_at, test passed

    def test_direct_message_clips_metadata_model(self):
        """Test that DirectMessage.clips_metadata field uses ClipsMetadata model"""
        from instagrapi.types import ClipsMetadata

        # Get some direct messages
        threads = self.cl.direct_threads(amount=5)
        if not threads:
            self.skipTest("No direct threads available for testing")

        for thread in threads:
            messages = self.cl.direct_messages(thread.id, amount=10)
            for message in messages:
                if message.clips_metadata:
                    # Test that clips_metadata field is now a ClipsMetadata object
                    self.assertIsInstance(message.clips_metadata, ClipsMetadata)

                    return  # Found one message with clips metadata, test passed

    def test_thread_is_seen_datetime_compatibility(self):
        """Test that DirectThread.is_seen() works with datetime objects"""

        # Get some direct threads
        threads = self.cl.direct_threads(amount=5)
        if not threads:
            self.skipTest("No direct threads available for testing")

        for thread in threads:
            if thread.last_seen_at:
                # Test that is_seen method works with datetime objects
                user_id = str(self.cl.user_id)
                try:
                    is_seen = thread.is_seen(user_id)
                    self.assertIsInstance(is_seen, bool)
                    return  # Successfully tested is_seen method
                except Exception as e:
                    self.fail(f"is_seen() method failed with datetime objects: {e}")

    def test_backward_compatibility_dict_access(self):
        """Test that dict-style access patterns still work for backward compatibility"""
        # Get some direct messages
        threads = self.cl.direct_threads(amount=5)
        if not threads:
            self.skipTest("No direct threads available for testing")

        for thread in threads:
            messages = self.cl.direct_messages(thread.id, amount=10)
            for message in messages:
                # Test that we can still access fields as if they were dicts
                # This should work due to our Pydantic model structure
                try:
                    if message.reactions:
                        # Should work even though it's now a Pydantic model
                        likes_count = getattr(message.reactions, "likes_count", 0)
                        self.assertIsInstance(likes_count, int)

                    if message.link:
                        # Should work even though it's now a Pydantic model
                        link_text = getattr(message.link, "text", "")
                        self.assertIsInstance(link_text, str)

                    return  # Successfully tested backward compatibility
                except Exception as e:
                    self.fail(f"Backward compatibility test failed: {e}")


class DirectExtractorRegressionTestCase(unittest.TestCase):
    def test_xma_share_without_target_url_is_ignored(self):
        message = extract_direct_message(
            {
                "item_id": "1",
                "user_id": "2",
                "timestamp": 1761953663000000,
                "item_type": "xma_media_share",
                "text": "",
                "xma_media_share": [
                    {
                        "header_icon_url": "",
                        "title_text": "Shared content",
                    }
                ],
            }
        )

        self.assertIsNone(message.xma_share)

    def test_xma_share_accepts_empty_header_icon_url(self):
        message = extract_direct_message(
            {
                "item_id": "1",
                "user_id": "2",
                "timestamp": 1761953663000000,
                "item_type": "xma_media_share",
                "text": "",
                "xma_media_share": [
                    {
                        "target_url": "https://example.com/reel",
                        "header_icon_url": "",
                        "title_text": "Shared content",
                    }
                ],
            }
        )

        self.assertIsNotNone(message.xma_share)
        self.assertEqual(str(message.xma_share.video_url), "https://example.com/reel")
        self.assertIsNone(message.xma_share.header_icon_url)

    def test_generic_xma_collects_multiple_items(self):
        message = extract_direct_message(
            {
                "item_id": "1",
                "user_id": "2",
                "timestamp": 1761953663000000,
                "item_type": "generic_xma",
                "text": "",
                "generic_xma": [
                    {
                        "target_url": "https://example.com/first",
                        "title_text": "First item",
                    },
                    {
                        "title_text": "Missing target url should be ignored",
                    },
                    {
                        "target_url": "https://example.com/second",
                        "title_text": "Second item",
                    },
                ],
            }
        )

        self.assertIsNotNone(message.generic_xma)
        self.assertEqual(len(message.generic_xma), 2)
        self.assertEqual(
            str(message.generic_xma[0].video_url), "https://example.com/first"
        )
        self.assertEqual(
            str(message.generic_xma[1].video_url), "https://example.com/second"
        )

    def test_reply_visual_media_timestamp_uses_microseconds(self):
        message = extract_direct_message(
            {
                "item_id": "1",
                "user_id": "2",
                "timestamp": 1761953663000000,
                "item_type": "text",
                "text": "reply wrapper",
                "replied_to_message": {
                    "item_id": "3",
                    "user_id": "4",
                    "timestamp": 1761953663000000,
                    "item_type": "visual_media",
                    "visual_media": {
                        "view_mode": "permanent",
                        "seen_user_ids": [],
                        "seen_count": 0,
                        "media": {
                            "media_type": 1,
                            "expiring_media_action_summary": {
                                "type": "replay",
                                "timestamp": 1761953663000000,
                                "count": 1,
                            },
                        },
                    },
                },
            }
        )

        self.assertEqual(message.reply.id, "3")
        self.assertEqual(
            message.reply.visual_media.media.expiring_media_action_summary.timestamp,
            datetime(2025, 10, 31, 23, 34, 23),
        )

    def test_direct_thread_defaults_missing_is_close_friend_thread(self):
        thread = extract_direct_thread(
            {
                "thread_v2_id": "1",
                "thread_id": "2",
                "items": [],
                "users": [
                    {
                        "pk": "3",
                        "username": "example",
                        "profile_pic_url": "https://example.com/pic.jpg",
                    }
                ],
                "left_users": [],
                "admin_user_ids": [],
                "last_activity_at": 1761953663000000,
                "muted": False,
                "named": False,
                "canonical": False,
                "pending": False,
                "archived": False,
                "thread_type": "private",
                "thread_title": "",
                "folder": 0,
                "vc_muted": False,
                "is_group": False,
                "mentions_muted": False,
                "approval_required_for_new_members": False,
                "input_mode": 0,
                "business_thread_folder": 0,
                "read_state": 0,
                "assigned_admin_id": 0,
                "shh_mode_enabled": False,
                "last_seen_at": {},
            }
        )

        self.assertFalse(thread.is_close_friend_thread)

    def test_direct_thread_parses_when_optional_fields_missing(self):
        """IG omits business_thread_folder / read_state / assigned_admin_id /
        shh_mode_enabled in older inbox shapes and Threads-app threads.
        Parser must not raise ValidationError on those payloads."""
        thread = extract_direct_thread(
            {
                "thread_v2_id": "1",
                "thread_id": "2",
                "items": [],
                "users": [
                    {
                        "pk": "3",
                        "username": "example",
                        "profile_pic_url": "https://example.com/pic.jpg",
                    }
                ],
                "left_users": [],
                "admin_user_ids": [],
                "last_activity_at": 1761953663000000,
                "muted": False,
                "named": False,
                "canonical": False,
                "pending": False,
                "archived": False,
                "thread_type": "private",
                "thread_title": "",
                "folder": 0,
                "vc_muted": False,
                "is_group": False,
                "mentions_muted": False,
                "approval_required_for_new_members": False,
                "input_mode": 0,
                "last_seen_at": {},
            }
        )

        self.assertIsNone(thread.business_thread_folder)
        self.assertIsNone(thread.read_state)
        self.assertIsNone(thread.assigned_admin_id)
        self.assertIsNone(thread.shh_mode_enabled)


class DirectMixinRegressionTestCase(unittest.TestCase):
    def build_client(self):
        client = Client()
        client.settings = {}
        client.authorization_data = {"ds_user_id": "1"}
        client.last_json = {}
        return client

    def test_direct_send_video_uses_direct_story_flow_for_thread_ids(self):
        client = self.build_client()
        expected = Mock(spec=DirectMessage)

        with mock.patch.object(
            client, "video_upload_to_direct", return_value=expected
        ) as video_upload:
            result = client.direct_send_video("clip.mp4", thread_ids=[123])

        self.assertIs(result, expected)
        video_upload.assert_called_once_with(Path("clip.mp4"), thread_ids=[123])

    def test_direct_send_video_resolves_existing_thread_for_user_ids(self):
        client = self.build_client()
        expected = Mock(spec=DirectMessage)

        with mock.patch.object(
            client,
            "direct_thread_by_participants",
            return_value={"thread_v2_id": "340282366841710300949128149448121770626"},
        ) as thread_lookup:
            with mock.patch.object(
                client, "video_upload_to_direct", return_value=expected
            ) as video_upload:
                result = client.direct_send_video("clip.mp4", user_ids=[42])

        self.assertIs(result, expected)
        thread_lookup.assert_called_once_with([42])
        video_upload.assert_called_once_with(
            Path("clip.mp4"),
            thread_ids=[340282366841710300949128149448121770626],
        )

    def test_direct_send_video_raises_when_existing_thread_is_missing(self):
        client = self.build_client()

        with mock.patch.object(
            client, "direct_thread_by_participants", return_value={}
        ) as thread_lookup:
            with mock.patch.object(client, "video_upload_to_direct") as video_upload:
                with self.assertRaises(DirectThreadNotFound):
                    client.direct_send_video("clip.mp4", user_ids=[42])

        thread_lookup.assert_called_once_with([42])
        video_upload.assert_not_called()


class UserMixinRegressionTestCase(unittest.TestCase):
    def build_private_client(self):
        client = Client()
        client.settings = {}
        client.authorization_data = {"ds_user_id": "1"}
        client.uuid = "uuid"
        return client

    @staticmethod
    def build_web_profile_user(**overrides):
        user = {
            "id": "123",
            "username": "example",
            "full_name": "Example",
            "is_private": False,
            "is_verified": False,
            "profile_pic_url_hd": None,
            "profile_pic_url": "https://example.com/pic.jpg",
            "edge_owner_to_timeline_media": {"count": 0},
            "edge_followed_by": {"count": 0},
            "edge_follow": {"count": 0},
            "is_business_account": False,
            "business_email": None,
            "business_phone_number": None,
            "biography": "",
            "bio_links": [],
            "external_url": None,
            "business_category_name": None,
            "category_name": None,
            "fbid": "123",
            "pinned_channels_info": {"pinned_channels_list": []},
        }
        user.update(overrides)
        return {"data": {"user": user}}

    def test_user_short_gql_falls_back_to_web_profile_graphql(self):
        client = Client()
        web_user = {
            "id": "25025320",
            "username": "instagram",
            "full_name": "Instagram",
            "is_private": False,
            "profile_pic_url": "https://example.com/pic.jpg",
        }

        with mock.patch.object(
            client,
            "public_graphql_request",
            side_effect=ClientGraphqlError("Incorrect Query"),
        ):
            with mock.patch.object(
                client, "user_web_profile_info_gql", return_value=web_user
            ) as fallback:
                user = client.user_short_gql("25025320", use_cache=False)

        self.assertEqual(user.username, "instagram")
        fallback.assert_called_once_with("25025320")

    def test_user_info_by_username_gql_parses_web_profile_without_update_headers_kwarg(
        self,
    ):
        class DummyClient(UserMixin):
            response_body = None

            def __init__(self):
                self.public_request_calls = []

            def public_request(self, url, headers=None, **kwargs):
                self.public_request_calls.append(
                    {"url": url, "headers": headers, "kwargs": kwargs}
                )
                return json.dumps(self.response_body)

        client = DummyClient()
        client.response_body = self.build_web_profile_user()
        user = client.user_info_by_username_gql("Example")
        self.assertEqual(user.pk, "123")
        self.assertEqual(user.username, "example")
        self.assertEqual(len(client.public_request_calls), 1)
        self.assertEqual(client.public_request_calls[0]["kwargs"], {})
        self.assertIn(
            "web_profile_info/?username=example", client.public_request_calls[0]["url"]
        )

    def test_user_info_by_username_suppresses_traceback_for_public_retry_error(self):
        client = Client()
        client._usernames_cache = {}
        client._users_cache = {}
        client.logger = Mock()
        fallback_user = User(
            pk="123",
            username="example",
            full_name="Example",
            is_private=False,
            is_verified=False,
            profile_pic_url="https://example.com/pic.jpg",
            media_count=0,
            follower_count=0,
            following_count=0,
            is_business=False,
        )

        with mock.patch.object(
            client,
            "user_info_by_username_gql",
            side_effect=RetryError("too many 429 error responses"),
        ):
            with mock.patch.object(
                client, "user_info_by_username_v1", return_value=fallback_user
            ) as fallback:
                with mock.patch.object(
                    client, "user_info", return_value=fallback_user
                ) as user_info:
                    user = client.user_info_by_username("Example", use_cache=False)

        self.assertEqual(user.pk, "123")
        fallback.assert_called_once_with("example")
        user_info.assert_called_once_with("123")
        client.logger.exception.assert_not_called()
        client.logger.warning.assert_called_once()

    def test_user_info_by_username_gql_handles_missing_pinned_channels_info(self):
        class DummyClient(UserMixin):
            response_body = None

            def public_request(self, url, headers=None, **kwargs):
                return json.dumps(self.response_body)

        client = DummyClient()
        client.response_body = self.build_web_profile_user()
        client.response_body["data"]["user"].pop("pinned_channels_info")

        user = client.user_info_by_username_gql("Example")

        self.assertEqual(user.broadcast_channel, [])

    def test_user_info_by_username_gql_handles_bio_links_without_link_id(self):
        class DummyClient(UserMixin):
            response_body = None

            def public_request(self, url, headers=None, **kwargs):
                return json.dumps(self.response_body)

        client = DummyClient()
        client.response_body = self.build_web_profile_user(
            bio_links=[{"url": "https://example.com", "title": "Example"}]
        )

        user = client.user_info_by_username_gql("Example")

        self.assertEqual(len(user.bio_links), 1)
        self.assertIsNone(user.bio_links[0].link_id)
        self.assertEqual(user.bio_links[0].url, "https://example.com")

    def test_user_followers_v1_chunk_omits_empty_max_id_on_first_page(self):
        client = self.build_private_client()

        with mock.patch.object(
            client,
            "private_request",
            return_value={"users": [], "next_max_id": None},
        ) as private_request:
            client.user_followers_v1_chunk("123")

        params = private_request.call_args.kwargs["params"]
        self.assertNotIn("max_id", params)

    def test_user_followers_v1_chunk_sends_non_empty_max_id_on_next_page(self):
        client = self.build_private_client()

        with mock.patch.object(
            client,
            "private_request",
            return_value={"users": [], "next_max_id": None},
        ) as private_request:
            client.user_followers_v1_chunk("123", max_id="cursor")

        params = private_request.call_args.kwargs["params"]
        self.assertEqual(params["max_id"], "cursor")

    def test_user_following_v1_chunk_omits_empty_max_id_on_first_page(self):
        client = self.build_private_client()

        with mock.patch.object(
            client,
            "private_request",
            return_value={"users": [], "next_max_id": None},
        ) as private_request:
            client.user_following_v1_chunk("123")

        params = private_request.call_args.kwargs["params"]
        self.assertNotIn("max_id", params)


class TimelineRegressionTestCase(unittest.TestCase):
    @staticmethod
    def build_media_payload(pk="1", code="abc"):
        return {
            "pk": pk,
            "id": f"{pk}_1",
            "code": code,
            "taken_at": 1710000000,
            "media_type": 2,
            "caption": {"text": "caption"},
            "user": {
                "pk": "1",
                "username": "example",
                "profile_pic_url": "https://example.com/profile.jpg",
            },
            "like_count": 0,
            "video_versions": [
                {
                    "url": "https://example.com/video.mp4",
                    "width": 720,
                    "height": 1280,
                }
            ],
            "image_versions2": {
                "candidates": [
                    {
                        "url": "https://example.com/thumbnail.jpg",
                        "width": 720,
                        "height": 1280,
                    }
                ]
            },
        }

    def test_reels_timeline_media_returns_empty_for_unsupported_collection(self):
        client = Client()
        client.logger = Mock()
        client.private_request = Mock()

        result = client.reels_timeline_media(123456789)

        self.assertEqual(result, [])
        client.private_request.assert_not_called()
        client.logger.warning.assert_called_once()

    def test_reels_timeline_media_uses_paging_info_max_id_for_pagination(self):
        client = Client()
        client.logger = Mock()
        first_media = self.build_media_payload(pk="1", code="abc")
        second_media = self.build_media_payload(pk="2", code="def")
        client.private_request = Mock(
            side_effect=[
                {
                    "items": [{"media": first_media}],
                    "paging_info": {"more_available": True, "max_id": "next-page"},
                },
                {
                    "items": [{"media": second_media}],
                    "paging_info": {"more_available": False},
                },
            ]
        )

        result = client.reels_timeline_media("reels", amount=2)

        self.assertEqual(len(result), 2)
        self.assertEqual(client.private_request.call_count, 2)
        first_call = client.private_request.call_args_list[0]
        second_call = client.private_request.call_args_list[1]
        self.assertEqual(first_call.args[0], "clips/connected/")
        self.assertEqual(first_call.kwargs["params"]["max_id"], "")
        self.assertEqual(second_call.kwargs["params"]["max_id"], "next-page")


class StoryConfigureRegressionTestCase(unittest.TestCase):
    def build_client(self):
        client = Client()
        client.settings = {}
        client._user_id = "1"
        client.uuid = "uuid"
        client.android_device_id = "device"
        client.client_session_id = "client-session"
        client.timezone_offset = 0
        client.set_device({})
        client.with_default_data = lambda data: data
        return client

    def test_photo_story_sticker_ids_include_all_stickers(self):
        client = self.build_client()

        with mock.patch.object(client, "private_request") as private_request:
            private_request.side_effect = [
                {"status": "ok"},
                {"status": "ok"},
            ]
            client.photo_configure_to_story(
                upload_id="1",
                width=720,
                height=1280,
                caption="",
                links=[StoryLink(webUri="https://example.com")],
                hashtags=[
                    StoryHashtag(
                        hashtag=Hashtag(id="1", name="example"),
                        x=0.2,
                        y=0.3,
                        width=0.5,
                        height=0.2,
                    )
                ],
            )

        validate_args, _ = private_request.call_args_list[0]
        self.assertEqual(validate_args[1]["url"], "https://example.com/")
        configure_args, _ = private_request.call_args_list[1]
        self.assertEqual(
            configure_args[1]["story_sticker_ids"],
            "hashtag_sticker,link_sticker_default",
        )


class UploadRegressionTestCase(unittest.TestCase):
    def build_client(self):
        client = Client()
        client.settings = {}
        client._user_id = "1"
        client.uuid = "uuid"
        client.android_device_id = "device"
        client.client_session_id = "client-session"
        client.timezone_offset = 0
        client.last_json = {}
        client.last_response = None
        client.set_device({})
        client.with_default_data = lambda data: data
        client.request_log = lambda response: None
        client.expose = lambda: None
        return client

    def build_media_payload(self, media_type=2):
        payload = {
            "pk": "1",
            "id": "1_1",
            "code": "abc",
            "taken_at": 1710000000,
            "media_type": media_type,
            "caption": {"text": "caption"},
            "user": {
                "pk": "1",
                "username": "example",
                "profile_pic_url": "https://example.com/profile.jpg",
            },
            "like_count": 0,
        }
        if media_type == 2:
            payload["video_versions"] = [
                {
                    "url": "https://example.com/video.mp4",
                    "width": 720,
                    "height": 1280,
                }
            ]
            payload["image_versions2"] = {
                "candidates": [
                    {
                        "url": "https://example.com/thumbnail.jpg",
                        "width": 720,
                        "height": 1280,
                    }
                ]
            }
        else:
            payload["image_versions2"] = {
                "candidates": [
                    {
                        "url": "https://example.com/photo.jpg",
                        "width": 720,
                        "height": 720,
                    }
                ]
            }
        return payload

    def test_photo_upload_raises_clear_error_when_configure_has_no_media(self):
        client = self.build_client()

        with mock.patch.object(client, "photo_rupload", return_value=("1", 720, 720)):
            with mock.patch.object(
                client, "photo_configure", return_value={"status": "ok"}
            ):
                with mock.patch("time.sleep"):
                    with self.assertRaises(PhotoConfigureError) as ctx:
                        client.photo_upload(Path("example.jpg"), "caption")

        self.assertIn("without media payload", str(ctx.exception))

    def test_video_upload_raises_clear_error_when_configure_has_no_media(self):
        client = self.build_client()

        with mock.patch.object(
            client,
            "video_rupload",
            return_value=("1", 720, 1280, 5, Path("/tmp/thumb.jpg")),
        ):
            with mock.patch.object(
                client, "video_configure", return_value={"status": "ok"}
            ):
                with mock.patch("time.sleep"):
                    with self.assertRaises(VideoConfigureError) as ctx:
                        client.video_upload(Path("example.mp4"), "caption")

        self.assertIn("without media payload", str(ctx.exception))

    def test_album_upload_raises_clear_error_when_configure_has_no_media(self):
        client = self.build_client()

        with mock.patch.object(client, "photo_rupload", return_value=("1", 720, 720)):
            with mock.patch.object(
                client, "album_configure", return_value={"status": "ok"}
            ):
                with mock.patch("time.sleep"):
                    with self.assertRaises(AlbumConfigureError) as ctx:
                        client.album_upload([Path("one.jpg")], "caption")

        self.assertIn("without media payload", str(ctx.exception))

    def test_album_upload_rejects_empty_paths_with_clear_error(self):
        client = self.build_client()

        with self.assertRaises(PrivateError) as ctx:
            client.album_upload([], "caption")

        self.assertIn("requires at least one media path", str(ctx.exception))

    def test_album_upload_rejects_unknown_format_with_filename_in_error(self):
        client = self.build_client()

        with self.assertRaises(PrivateError) as ctx:
            client.album_upload([Path("clip.mov")], "caption")

        self.assertIn('Unsupported album media format ".mov"', str(ctx.exception))
        self.assertIn("clip.mov", str(ctx.exception))

    def test_album_upload_accepts_png_via_photo_rupload(self):
        client = self.build_client()
        media_payload = self.build_media_payload(media_type=8)
        media_payload["carousel_media"] = [self.build_media_payload(media_type=1)]

        with mock.patch.object(
            client,
            "photo_rupload",
            return_value=("1", 720, 720),
        ) as photo_rupload:
            with mock.patch.object(
                client,
                "album_configure",
                return_value={"status": "ok", "media": media_payload},
            ):
                with mock.patch("time.sleep"):
                    media = client.album_upload([Path("slide.png")], "caption")

        self.assertIsInstance(media, Media)
        photo_rupload.assert_called_once_with(Path("slide.png"), to_album=True)

    def test_photo_story_upload_raises_clear_error_when_configure_has_no_media(self):
        client = self.build_client()

        with mock.patch.object(client, "photo_rupload", return_value=("1", 720, 1280)):
            with mock.patch.object(
                client, "photo_configure_to_story", return_value={"status": "ok"}
            ):
                with mock.patch("time.sleep"):
                    with self.assertRaises(PhotoConfigureStoryError) as ctx:
                        client.photo_upload_to_story(Path("story.jpg"))

        self.assertIn("without media payload", str(ctx.exception))

    def test_clip_upload_falls_back_to_last_json_media_payload(self):
        client = self.build_client()
        client.last_json = {"media": self.build_media_payload()}
        ok_response = Mock(status_code=200)

        with mock.patch(
            "instagrapi.mixins.clip.analyze_video",
            return_value=(Path("/tmp/thumb.jpg"), 720, 1280, 5),
        ):
            with mock.patch.object(client.private, "get", return_value=ok_response):
                with mock.patch.object(
                    client.private, "post", return_value=ok_response
                ):
                    with mock.patch.object(
                        client, "clip_configure", return_value={"status": "ok"}
                    ):
                        with mock.patch(
                            "builtins.open", mock.mock_open(read_data=b"video-bytes")
                        ):
                            with mock.patch("time.sleep"):
                                media = client.clip_upload(
                                    Path("example.mp4"), "caption"
                                )

        self.assertIsInstance(media, Media)
        self.assertEqual(str(media.video_url), "https://example.com/video.mp4")

    def test_video_story_upload_raises_clear_error_when_configure_has_no_media(self):
        client = self.build_client()

        with mock.patch.object(
            client,
            "video_rupload",
            return_value=("1", 720, 1280, 5, Path("/tmp/thumb.jpg")),
        ):
            with mock.patch.object(
                client, "video_configure_to_story", return_value={"status": "ok"}
            ):
                with mock.patch("time.sleep"):
                    with self.assertRaises(VideoConfigureStoryError) as ctx:
                        client.video_upload_to_story(Path("story.mp4"))

        self.assertIn("without media payload", str(ctx.exception))

    def test_video_direct_upload_raises_clear_error_when_configure_has_no_message(self):
        client = self.build_client()

        with mock.patch.object(
            client,
            "video_rupload",
            return_value=("1", 720, 1280, 5, Path("/tmp/thumb.jpg")),
        ):
            with mock.patch.object(
                client, "video_configure_to_story", return_value={"status": "ok"}
            ):
                with mock.patch("time.sleep"):
                    with self.assertRaises(VideoConfigureStoryError) as ctx:
                        client.video_upload_to_direct(
                            Path("story.mp4"),
                            thread_ids=[123],
                        )

        self.assertIn("without message_metadata payload", str(ctx.exception))

    def test_cutout_sticker_upload_raises_clear_error_when_configure_has_no_media(self):
        client = self.build_client()

        with mock.patch.object(
            client, "private_request", return_value={"status": "ok"}
        ):
            with self.assertRaises(PrivateError) as ctx:
                client.media_configure_to_cutout_sticker(
                    "1", manual_box=[0.0, 0.0, 1.0, 1.0]
                )

        self.assertIn("without media payload", str(ctx.exception))

    def test_cutout_sticker_upload_uses_returned_media_payload(self):
        client = self.build_client()
        media_payload = self.build_media_payload(media_type=1)

        with mock.patch.object(
            client,
            "private_request",
            return_value={"status": "ok", "media": media_payload},
        ):
            media = client.media_configure_to_cutout_sticker(
                "1", manual_box=[0.0, 0.0, 1.0, 1.0]
            )

        self.assertIsInstance(media, Media)
        self.assertEqual(media.media_type, 1)

    def test_clip_upload_as_reel_with_music_does_not_mutate_extra_data(self):
        client = self.build_client()
        extra_data = {"share_to_facebook": 1}
        track = Mock(
            uri="https://example.com/track.m4a",
            highlight_start_times_in_ms=[1500],
            display_artist="Artist",
            id="track-id",
            audio_cluster_id="cluster-id",
            title="Track title",
        )

        class FakeAudioClip:
            def __init__(self, path):
                self.path = path

            def subclip(self, start, end):
                return self

            def close(self):
                return None

        class FakeVideoClip:
            def __init__(self, path):
                self.path = path
                self.duration = 2.5

            def set_audio(self, audio_clip):
                self.audio_clip = audio_clip
                return self

            def write_videofile(self, path):
                Path(path).write_bytes(b"video")

            def close(self):
                return None

        fake_mp = types.ModuleType("moviepy.editor")
        fake_mp.VideoFileClip = FakeVideoClip
        fake_mp.AudioFileClip = FakeAudioClip

        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = Path(tmpdir) / "track.m4a"
            audio_path.write_bytes(b"audio")
            video_path = Path(tmpdir) / "output.mp4"
            with mock.patch.dict(
                "sys.modules",
                {
                    "moviepy": fake_mp,
                    "moviepy.editor": fake_mp,
                },
            ):
                with mock.patch(
                    "tempfile.mktemp", side_effect=[str(audio_path), str(video_path)]
                ):
                    with mock.patch.object(
                        client, "track_download_by_url", return_value=audio_path
                    ):
                        with mock.patch.object(
                            client, "clip_upload", return_value="uploaded"
                        ) as clip_upload:
                            result = client.clip_upload_as_reel_with_music(
                                Path("input.mp4"),
                                "caption",
                                track,
                                extra_data=extra_data,
                            )

        self.assertEqual(result, "uploaded")
        self.assertEqual(extra_data, {"share_to_facebook": 1})
        upload_extra = clip_upload.call_args.kwargs["extra_data"]
        self.assertEqual(upload_extra["share_to_facebook"], 1)
        self.assertIn("clips_audio_metadata", upload_extra)
        self.assertIn("music_params", upload_extra)

    def test_clip_upload_as_reel_with_music_includes_music_canonical_id(self):
        client = self.build_client()
        track = Mock(
            uri="https://example.com/track.m4a",
            highlight_start_times_in_ms=[1500],
            display_artist="Artist",
            id="track-id",
            audio_cluster_id="cluster-id",
            music_canonical_id="canonical-id",
            title="Track title",
        )

        class FakeAudioClip:
            def __init__(self, path):
                self.path = path

            def subclip(self, start, end):
                return self

            def close(self):
                return None

        class FakeVideoClip:
            def __init__(self, path):
                self.path = path
                self.duration = 2.5

            def set_audio(self, audio_clip):
                self.audio_clip = audio_clip
                return self

            def write_videofile(self, path):
                Path(path).write_bytes(b"video")

            def close(self):
                return None

        fake_mp = types.ModuleType("moviepy.editor")
        fake_mp.VideoFileClip = FakeVideoClip
        fake_mp.AudioFileClip = FakeAudioClip

        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = Path(tmpdir) / "track.m4a"
            audio_path.write_bytes(b"audio")
            video_path = Path(tmpdir) / "output.mp4"
            with mock.patch.dict(
                "sys.modules",
                {
                    "moviepy": fake_mp,
                    "moviepy.editor": fake_mp,
                },
            ):
                with mock.patch(
                    "tempfile.mktemp", side_effect=[str(audio_path), str(video_path)]
                ):
                    with mock.patch.object(
                        client, "track_download_by_url", return_value=audio_path
                    ):
                        with mock.patch.object(
                            client, "clip_upload", return_value="uploaded"
                        ) as clip_upload:
                            client.clip_upload_as_reel_with_music(
                                Path("input.mp4"),
                                "caption",
                                track,
                            )

        upload_extra = clip_upload.call_args.kwargs["extra_data"]
        self.assertEqual(
            upload_extra["clips_audio_metadata"]["song"]["music_canonical_id"],
            "canonical-id",
        )
        self.assertEqual(
            upload_extra["music_params"]["music_canonical_id"],
            "canonical-id",
        )

    def test_clip_upload_as_reel_with_music_cleans_temp_files_on_failure(self):
        client = self.build_client()
        track = Mock(
            uri="https://example.com/track.m4a",
            highlight_start_times_in_ms=[0],
            display_artist="Artist",
            id="track-id",
            audio_cluster_id="cluster-id",
            title="Track title",
        )

        class FakeAudioClip:
            def __init__(self, path):
                self.path = path

            def subclip(self, start, end):
                return self

            def close(self):
                return None

        class FakeVideoClip:
            def __init__(self, path):
                self.path = path
                self.duration = 2.5

            def set_audio(self, audio_clip):
                self.audio_clip = audio_clip
                return self

            def write_videofile(self, path):
                Path(path).write_bytes(b"video")

            def close(self):
                return None

        fake_mp = types.ModuleType("moviepy.editor")
        fake_mp.VideoFileClip = FakeVideoClip
        fake_mp.AudioFileClip = FakeAudioClip

        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = Path(tmpdir) / "track.m4a"
            audio_path.write_bytes(b"audio")
            video_path = Path(tmpdir) / "output.mp4"
            with mock.patch.dict(
                "sys.modules",
                {
                    "moviepy": fake_mp,
                    "moviepy.editor": fake_mp,
                },
            ):
                with mock.patch(
                    "tempfile.mktemp", side_effect=[str(audio_path), str(video_path)]
                ):
                    with mock.patch.object(
                        client, "track_download_by_url", return_value=audio_path
                    ):
                        with mock.patch.object(
                            client,
                            "clip_upload",
                            side_effect=ClipConfigureError("boom"),
                        ):
                            with self.assertRaises(ClipConfigureError):
                                client.clip_upload_as_reel_with_music(
                                    Path("input.mp4"),
                                    "caption",
                                    track,
                                )

            self.assertFalse(audio_path.exists())
            self.assertFalse(video_path.exists())

    def test_clip_analyze_video_closes_video_file(self):
        import instagrapi.mixins.clip as clip_mixin

        closed = {"value": False}

        class FakeVideoClip:
            def __init__(self, path):
                self.size = (720, 1280)
                self.duration = 5

            def close(self):
                closed["value"] = True

        fake_mp = types.ModuleType("moviepy.editor")
        fake_mp.VideoFileClip = FakeVideoClip

        with mock.patch.dict(
            "sys.modules",
            {
                "moviepy": fake_mp,
                "moviepy.editor": fake_mp,
            },
        ):
            result = clip_mixin.analyze_video(
                Path("input.mp4"), thumbnail=Path("thumb.jpg")
            )

        self.assertEqual(result, (Path("thumb.jpg"), 720, 1280, 5))
        self.assertTrue(closed["value"])

    def test_video_analyze_video_closes_video_file_on_save_frame_error(self):
        import instagrapi.mixins.video as video_mixin

        closed = {"value": False}

        class FakeVideoClip:
            def __init__(self, path):
                self.size = (720, 1280)
                self.duration = 5

            def save_frame(self, path, t):
                raise RuntimeError("save failed")

            def close(self):
                closed["value"] = True

        fake_mp = types.ModuleType("moviepy.editor")
        fake_mp.VideoFileClip = FakeVideoClip

        with mock.patch.dict(
            "sys.modules",
            {
                "moviepy": fake_mp,
                "moviepy.editor": fake_mp,
            },
        ):
            with self.assertRaises(RuntimeError):
                video_mixin.analyze_video(Path("input.mp4"))

        self.assertTrue(closed["value"])

    def test_clip_analyze_video_closes_video_file_on_save_frame_error(self):
        import instagrapi.mixins.clip as clip_mixin

        closed = {"value": False}

        class FakeVideoClip:
            def __init__(self, path):
                self.size = (720, 1280)
                self.duration = 5

            def save_frame(self, path, t):
                raise RuntimeError("save failed")

            def close(self):
                closed["value"] = True

        fake_mp = types.ModuleType("moviepy.editor")
        fake_mp.VideoFileClip = FakeVideoClip

        with mock.patch.dict(
            "sys.modules",
            {
                "moviepy": fake_mp,
                "moviepy.editor": fake_mp,
            },
        ):
            with self.assertRaises(RuntimeError):
                clip_mixin.analyze_video(Path("input.mp4"))

        self.assertTrue(closed["value"])

    def test_video_story_sticker_ids_include_all_stickers(self):
        client = self.build_client()

        with mock.patch.object(client, "private_request") as private_request:
            private_request.side_effect = [
                {"status": "ok"},
                {"status": "ok"},
            ]
            client.video_configure_to_story(
                upload_id="1",
                width=720,
                height=1280,
                duration=5,
                thumbnail=Path("/tmp/placeholder.jpg"),
                caption="",
                links=[StoryLink(webUri="https://example.com")],
                hashtags=[
                    StoryHashtag(
                        hashtag=Hashtag(id="1", name="example"),
                        x=0.2,
                        y=0.3,
                        width=0.5,
                        height=0.2,
                    )
                ],
            )

        configure_args, _ = private_request.call_args_list[1]
        self.assertEqual(
            configure_args[1]["story_sticker_ids"],
            "hashtag_sticker,link_sticker_default",
        )

    def test_extract_story_v1_reads_links_from_story_link_stickers(self):
        story = extract_story_v1(
            {
                "pk": "1",
                "id": "1_2",
                "code": "abc",
                "taken_at": 1710000000,
                "media_type": 1,
                "image_versions2": {
                    "candidates": [
                        {
                            "url": "https://example.com/thumbnail.jpg",
                            "width": 720,
                            "height": 1280,
                        }
                    ]
                },
                "user": {
                    "pk": "2",
                    "username": "example",
                    "profile_pic_url": "https://example.com/profile.jpg",
                },
                "story_link_stickers": [
                    {
                        "x": 0.5,
                        "y": 0.5,
                        "width": 0.5,
                        "height": 0.2,
                        "rotation": 0.0,
                        "story_link": {
                            "url": "https://example.com/story-link",
                            "link_type": "web",
                        },
                    }
                ],
                "story_hashtags": [
                    {
                        "x": 0.2,
                        "y": 0.3,
                        "width": 0.5,
                        "height": 0.2,
                        "rotation": 0.0,
                        "hashtag": {"id": "1", "name": "example"},
                    }
                ],
            }
        )

        self.assertEqual(len(story.links), 1)
        self.assertEqual(str(story.links[0].webUri), "https://example.com/story-link")
        self.assertEqual(len(story.stickers), 1)
        self.assertEqual(len(story.hashtags), 1)
        self.assertEqual(story.hashtags[0].hashtag.name, "example")


class ClientAccountTestCase(ClientPrivateTestCase):
    def test_account_edit(self):
        # current
        one = self.cl.user_info(self.cl.user_id)
        self.assertIsInstance(one, User)
        # change
        url = "https://trotiq.com/"
        two = self.cl.account_edit(external_url=url)
        self.assertIsInstance(two, Account)
        self.assertEqual(str(two.external_url), url)
        # return back
        three = self.cl.account_edit(external_url=one.external_url)
        self.assertIsInstance(three, Account)
        self.assertEqual(one.external_url, three.external_url)

    def test_account_change_picture(self):
        # current
        one = self.cl.user_info(self.cl.user_id)
        self.assertIsInstance(one, User)
        instagram = self.user_info_by_username("instagram")
        # change
        two = self.cl.account_change_picture(
            self.cl.photo_download_by_url(instagram.profile_pic_url)
        )
        self.assertIsInstance(two, UserShort)
        # return back
        three = self.cl.account_change_picture(
            self.cl.photo_download_by_url(one.profile_pic_url)
        )
        self.assertIsInstance(three, UserShort)


class ClientLocationTestCase(ClientPrivateTestCase):
    def test_location_search(self):
        loc = self.cl.location_search(51.0536111111, 13.8108333333)[0]
        self.assertIsInstance(loc, Location)
        self.assertIn("Dresden", loc.name)
        self.assertIn("Dresden", loc.address)
        self.assertEqual(150300262230285, loc.external_id)
        self.assertEqual("facebook_places", loc.external_id_source)

    def test_location_complete_pk(self):
        source = Location(
            name="Daily Surf Supply",
            external_id=533689780360041,
            external_id_source="facebook_places",
        )
        result = self.cl.location_complete(source)
        self.assertIsInstance(result, Location)
        self.assertEqual(result.pk, 533689780360041)

    def test_location_complete_lat_lng(self):
        source = Location(
            pk=150300262230285,
            name="Blaues Wunder (Dresden)",
        )
        result = self.cl.location_complete(source)
        self.assertIsInstance(result, Location)
        self.assertEqual(result.lat, 51.0536111111)
        self.assertEqual(result.lng, 13.8108333333)

    def test_location_complete_external_id(self):
        source = Location(
            name="Blaues Wunder (Dresden)", lat=51.0536111111, lng=13.8108333333
        )
        result = self.cl.location_complete(source)
        self.assertIsInstance(result, Location)
        self.assertEqual(result.external_id, 150300262230285)
        self.assertEqual(result.external_id_source, "facebook_places")

    def test_location_build(self):
        loc = self.cl.location_info(150300262230285)
        self.assertIsInstance(loc, Location)
        json_data = self.cl.location_build(loc)
        self.assertIsInstance(json_data, str)
        data = json.loads(json_data)
        self.assertIsInstance(data, dict)
        self.assertDictEqual(
            data,
            {
                "name": "Blaues Wunder (Dresden)",
                "address": "Dresden, Germany",
                "lat": 51.053611111111,
                "lng": 13.810833333333,
                "facebook_places_id": 150300262230285,
                "external_source": "facebook_places",
            },
        )

    def test_location_info(self):
        loc = self.cl.location_info(150300262230285)
        self.assertIsInstance(loc, Location)
        self.assertEqual(loc.pk, 150300262230285)
        self.assertEqual(loc.name, "Blaues Wunder (Dresden)")
        self.assertEqual(loc.lng, 13.8108333333)
        self.assertEqual(loc.lat, 51.0536111111)

    def test_location_info_without_lat_lng(self):
        loc = self.cl.location_info(197780767581661)
        self.assertIsInstance(loc, Location)
        self.assertEqual(loc.pk, 197780767581661)
        self.assertEqual(loc.name, "In The Clouds")

    def test_location_medias_top(self):
        medias = self.cl.location_medias_top(197780767581661, amount=2)
        self.assertEqual(len(medias), 2)
        self.assertIsInstance(medias[0], Media)

    # def test_extract_location_medias_top(self):
    #     medias_a1 = self.cl.location_medias_top_a1(197780767581661, amount=9)
    #     medias_v1 = self.cl.location_medias_top_v1(197780767581661, amount=9)
    #     self.assertEqual(len(medias_a1), 9)
    #     self.assertIsInstance(medias_a1[0], Media)
    #     self.assertEqual(len(medias_v1), 9)
    #     self.assertIsInstance(medias_v1[0], Media)

    def test_location_medias_recent(self):
        medias = self.cl.location_medias_recent(197780767581661, amount=2)
        self.assertEqual(len(medias), 2)
        self.assertIsInstance(medias[0], Media)


class SignUpTestCase(unittest.TestCase):
    def test_password_enrypt(self):
        cl = Client()
        enc_password = cl.password_encrypt("test")
        parts = enc_password.split(":")
        self.assertEqual(parts[0], "#PWD_INSTAGRAM")
        self.assertEqual(parts[1], "4")
        self.assertTrue(int(parts[2]) > 1607612345)
        self.assertTrue(len(parts[3]) == 392)

    def test_signup(self):
        cl = Client()
        username = gen_password()
        password = gen_password(12, symbols=True)
        email = f"{username}@gmail.com"
        phone_number = os.environ.get("IG_PHONE_NUMBER")
        full_name = f"John {username}"
        user = cl.signup(
            username,
            password,
            email,
            phone_number,
            full_name,
            year=random.randint(1980, 1990),
            month=random.randint(1, 12),
            day=random.randint(1, 30),
        )
        self.assertIsInstance(user, UserShort)
        for key, val in {"username": username, "full_name": full_name}.items():
            self.assertEqual(getattr(user, key), val)
        self.assertTrue(user.profile_pic_url.startswith("https://"))


class ClientHashtagTestCase(ClientPrivateTestCase):
    REQUIRED_MEDIA_FIELDS = [
        "pk",
        "taken_at",
        "id",
        "media_type",
        "code",
        "thumbnail_url",
        "like_count",
        "caption_text",
        "video_url",
        "view_count",
        "video_duration",
        "title",
    ]

    def test_hashtag_info(self):
        hashtag = self.cl.hashtag_info("instagram")
        self.assertIsInstance(hashtag, Hashtag)
        self.assertEqual("instagram", hashtag.name)

    def test_extract_hashtag_info(self):
        hashtag_a1 = self.cl.hashtag_info_a1("instagram")
        hashtag_v1 = self.cl.hashtag_info_v1("instagram")
        self.assertIsInstance(hashtag_a1, Hashtag)
        self.assertIsInstance(hashtag_v1, Hashtag)
        self.assertEqual("instagram", hashtag_a1.name)
        self.assertEqual(hashtag_a1.id, hashtag_v1.id)
        self.assertEqual(hashtag_a1.name, hashtag_v1.name)
        self.assertEqual(hashtag_a1.media_count, hashtag_v1.media_count)

    def test_hashtag_medias_top(self):
        medias = self.cl.hashtag_medias_top("instagram", amount=2)
        self.assertEqual(len(medias), 2)
        self.assertIsInstance(medias[0], Media)

    def test_extract_hashtag_medias_top(self):
        medias_a1 = self.cl.hashtag_medias_top_a1("instagram", amount=9)
        medias_v1 = self.cl.hashtag_medias_top_v1("instagram", amount=9)
        self.assertEqual(len(medias_a1), 9)
        self.assertIsInstance(medias_a1[0], Media)
        self.assertEqual(len(medias_v1), 9)
        self.assertIsInstance(medias_v1[0], Media)

    def test_hashtag_medias_recent(self):
        medias = self.cl.hashtag_medias_recent("instagram", amount=2)
        self.assertEqual(len(medias), 2)
        self.assertIsInstance(medias[0], Media)

    def test_extract_hashtag_medias_recent(self):
        medias_v1 = self.cl.hashtag_medias_recent_v1("instagram", amount=31)
        medias_a1 = self.cl.hashtag_medias_recent_a1("instagram", amount=31)
        self.assertEqual(len(medias_a1), 31)
        self.assertIsInstance(medias_a1[0], Media)
        self.assertEqual(len(medias_v1), 31)
        self.assertIsInstance(medias_v1[0], Media)
        for i, a1 in enumerate(medias_a1[:10]):
            a1 = a1.dict()
            v1 = medias_v1[i].dict()
            for f in self.REQUIRED_MEDIA_FIELDS:
                a1_val, v1_val = a1[f], v1[f]
                is_album = a1["media_type"] == 8
                is_video = v1.get("video_duration") > 0
                if f == "thumbnail_url" and not is_album:
                    a1_val = a1[f].path.rsplit("/", 1)[1]
                    v1_val = v1[f].path.rsplit("/", 1)[1]
                if f == "video_url" and is_video:
                    a1_val = a1[f].path.rsplit(".", 1)[1]
                    v1_val = v1[f].path.rsplit(".", 1)[1]
                if f in ("view_count", "like_count"):
                    # instagram can different counts for public and private
                    if f == "view_count" and not is_video:
                        continue
                    self.assertTrue(a1_val > 1)
                    self.assertTrue(v1_val > 1)
                    continue
                self.assertEqual(a1_val, v1_val)


class ClientStoryTestCase(ClientPrivateTestCase):
    def test_story_pk_from_url(self):
        story_pk = self.cl.story_pk_from_url(
            "https://www.instagram.com/stories/instagram/2581281926631793076/"
        )
        self.assertEqual(story_pk, 2581281926631793076)

    def test_upload_photo_story(self):
        media_pk = self.cl.media_pk_from_url("https://www.instagram.com/p/B3mr1-OlWMG/")
        path = self.cl.photo_download(media_pk)
        self.assertIsInstance(path, Path)
        caption = "Test photo caption"
        instagram = self.user_info_by_username("instagram")
        self.assertIsInstance(instagram, User)
        mentions = [StoryMention(user=instagram)]
        medias = [StoryMedia(media_pk=media_pk, x=0.5, y=0.5, width=0.6, height=0.8)]
        links = [StoryLink(webUri="https://instagram.com/")]
        # hashtags = [StoryHashtag(hashtag=self.cl.hashtag_info('instagram'))]
        # locations = [
        #     StoryLocation(
        #         location=Location(
        #             pk=150300262230285,
        #             name='Blaues Wunder (Dresden)',
        #         )
        #     )
        # ]
        stickers = [
            StorySticker(
                id="Igjf05J559JWuef4N5",
                type="gif",
                x=0.5,
                y=0.5,
                width=0.4,
                height=0.08,
            )
        ]
        try:
            story = self.cl.photo_upload_to_story(
                path,
                caption,
                mentions=mentions,
                links=links,
                # hashtags=hashtags,
                # locations=locations,
                stickers=stickers,
                medias=medias,
            )
            self.assertIsInstance(story, Story)
            self.assertTrue(story)
            s = self.cl.story_info(story.pk)
            self.assertIsInstance(s, Story)
            self.assertTrue(s)
            m, sm = medias[0], s.medias[0]
            self.assertEqual(m.media_pk, sm.media_pk)
            self.assertEqual(m.x, sm.x)
            self.assertEqual(m.y, sm.y)
        finally:
            if path:
                cleanup(path)
            self.assertTrue(self.cl.story_delete(story.id))

    def test_upload_video_story(self):
        media_pk = self.cl.media_pk_from_url("https://www.instagram.com/p/Bk2tOgogq9V/")
        story = None
        path = self.cl.video_download(media_pk)
        self.assertIsInstance(path, Path)
        caption = "Test video caption"
        instagram = self.user_info_by_username("instagram")
        self.assertIsInstance(instagram, User)
        mentions = [StoryMention(user=instagram)]
        medias = [StoryMedia(media_pk=media_pk, x=0.5, y=0.5, width=0.6, height=0.8)]
        links = [StoryLink(webUri="https://instagram.com/")]
        # hashtags = [StoryHashtag(hashtag=self.cl.hashtag_info('instagram'))]
        # locations = [
        #     StoryLocation(
        #         location=Location(
        #             pk=150300262230285,
        #             name='Blaues Wunder (Dresden)',
        #         )
        #     )
        # ]
        try:
            buildout = StoryBuilder(
                path, caption, mentions, Path("./examples/background.png")
            ).video(1)
            story = self.cl.video_upload_to_story(
                buildout.path,
                caption,
                mentions=buildout.mentions,
                links=links,
                # hashtags=hashtags,
                # locations=locations,
                medias=medias,
            )
            self.assertIsInstance(story, Story)
            self.assertTrue(story)
            s = self.cl.story_info(story.pk)
            self.assertIsInstance(s, Story)
            self.assertTrue(s)
            m, sm = medias[0], s.medias[0]
            self.assertEqual(m.media_pk, sm.media_pk)
            self.assertEqual(m.x, sm.x)
            self.assertEqual(m.y, sm.y)
        finally:
            cleanup(path)
            if story:
                self.assertTrue(self.cl.story_delete(story.id))

    def test_user_stories(self):
        user_id = self.user_id_from_username("instagram")
        stories = self.cl.user_stories(user_id, 2)
        self.assertEqual(len(stories), 2)
        story = stories[0]
        self.assertIsInstance(story, Story)
        for field in REQUIRED_STORY_FIELDS:
            self.assertTrue(hasattr(story, field))
        stories = self.cl.user_stories(self.user_id_from_username("instagram"))
        self.assertIsInstance(stories, list)

    def test_extract_user_stories(self):
        user_id = self.user_id_from_username("instagram")
        stories_v1 = self.cl.user_stories_v1(user_id, amount=2)
        stories_gql = self.cl.user_stories_gql(user_id, amount=2)
        self.assertEqual(len(stories_v1), 2)
        self.assertIsInstance(stories_v1[0], Story)
        self.assertEqual(len(stories_gql), 2)
        self.assertIsInstance(stories_gql[0], Story)
        for i, gql in enumerate(stories_gql[:2]):
            gql = gql.dict()
            v1 = stories_v1[i].dict()
            for f in REQUIRED_STORY_FIELDS:
                gql_val, v1_val = gql[f], v1[f]
                is_video = v1.get("video_duration") > 0
                if f == "video_url" and is_video:
                    gql_val = gql[f].path.rsplit(".", 1)[1]
                    v1_val = v1[f].path.rsplit(".", 1)[1]
                elif f == "thumbnail_url":
                    self.assertIn(".jpg", gql_val)
                    self.assertIn(".jpg", v1_val)
                    continue
                elif f == "user":
                    gql_val.pop("full_name")
                    v1_val.pop("full_name")
                    gql_val.pop("is_private")
                    v1_val.pop("is_private")
                    gql_val["profile_pic_url"] = gql_val["profile_pic_url"].path
                    v1_val["profile_pic_url"] = v1_val["profile_pic_url"].path
                elif f == "mentions":
                    for item in [*gql_val, *v1_val]:
                        item["user"].pop("pk")
                        item["user"].pop("profile_pic_url")
                        item.pop("width")
                        item.pop("height")
                        item["x"] = round(item["x"], 4)
                        item["y"] = round(item["y"], 4)
                elif f == "links":
                    # [{'webUri': HttpUrl('https://youtu.be/x3GYpar-e64', scheme='https', host='youtu.be', tld='be', host_type='domain', path='/x3GYpar-e64')}]
                    # [{'webUri': HttpUrl('https://l.instagram.com/?u=https%3A%2F%2Fyoutu.be%2Fx3GYpar-e64&e=ATM59nvUNmptw8vUsyoX835T....}]
                    self.assertEqual(len(v1_val), len(gql_val))
                    if gql_val:
                        self.assertIn(
                            gql_val[0]["webUri"].host, v1_val[0]["webUri"].query
                        )
                    continue
                if gql_val != v1_val:
                    import pudb

                    pudb.set_trace()
                self.assertEqual(gql_val, v1_val)

    def test_story_info(self):
        user_id = self.user_id_from_username("instagram")
        stories = self.cl.user_stories(user_id, amount=1)
        story = self.cl.story_info(stories[0].pk)
        self.assertIsInstance(story, Story)
        story = self.cl.story_info(stories[0].id)
        self.assertIsInstance(story, Story)
        self.assertTrue(self.cl.story_seen([story.pk]))


# class BloksTestCase(ClientPrivateTestCase):
#
#     def test_bloks_change_password(self):
#         last_json = {
#             'step_name': 'change_password',
#             'step_data': {'new_password1': 'None', 'new_password2': 'None'},
#             'flow_render_type': 3,
#             'bloks_action': 'com.instagram.challenge.navigation.take_challenge',
#             'cni': 12346879508000123,
#             'challenge_context': '{"step_name": "change_password", "cni": 12346879508000123, "is_stateless": false, "challenge_type_enum": "PASSWORD_RESET"}',
#             'challenge_type_enum_str': 'PASSWORD_RESET',
#             'status': 'ok'
#         }
#        self.assertTrue(self.cl.bloks_change_password("2r9j20r9j4230t8hj39tHW4"))


class TOTPTestCase(ClientPrivateTestCase):
    def test_totp_code(self):
        seed = self.cl.totp_generate_seed()
        code = self.cl.totp_generate_code(seed)
        self.assertIsInstance(code, str)
        self.assertTrue(code.isdigit())
        self.assertEqual(len(code), 6)


class ClientHighlightTestCase(ClientPrivateTestCase):
    def test_highlight_pk_from_url(self):
        highlight_pk = self.cl.highlight_pk_from_url(
            "https://www.instagram.com/stories/highlights/17983407089364361/"
        )
        self.assertEqual(highlight_pk, "17983407089364361")

    def test_highlight_info(self):
        highlight = self.cl.highlight_info(17983407089364361)
        self.assertIsInstance(highlight, Highlight)
        self.assertEqual(highlight.pk, "17983407089364361")
        self.assertTrue(len(highlight.items) > 0)
        self.assertEqual(len(highlight.items), highlight.media_count)
        self.assertEqual(len(highlight.items), len(highlight.media_ids))


class ClientShareTestCase(ClientPrivateTestCase):
    def test_share_code_from_url(self):
        url = "https://www.instagram.com/s/aGlnaGxpZ2h0OjE3OTMzOTExODE2NTY4Njcx?utm_medium=share_sheet"
        code = self.cl.share_code_from_url(url)
        self.assertEqual(code, "aGlnaGxpZ2h0OjE3OTMzOTExODE2NTY4Njcx")

    def test_share_info_by_url(self):
        url = "https://www.instagram.com/s/aGlnaGxpZ2h0OjE3OTMzOTExODE2NTY4Njcx?utm_medium=share_sheet"
        share = self.cl.share_info_by_url(url)
        self.assertIsInstance(share, Share)
        self.assertEqual(share.pk, "17933911816568671")
        self.assertEqual(share.type, "highlight")

    def test_share_info(self):
        share = self.cl.share_info("aGlnaGxpZ2h0OjE3OTMzOTExODE2NTY4Njcx")
        self.assertIsInstance(share, Share)
        self.assertEqual(share.pk, "17933911816568671")
        self.assertEqual(share.type, "highlight")
        # UnicodeDecodeError: 'utf-8' codec can't decode byte 0xb1 in position 6: invalid start byte
        share = self.cl.share_info("aGlnaGxpsdsdZ2h0OjE3OTg4MDg5NjI5MzgzNzcw")
        self.assertIsInstance(share, Share)
        self.assertEqual(share.pk, "17988089629383770")
        self.assertEqual(share.type, "highlight")


class ClientCutoutStickerTestCase(ClientPrivateTestCase):
    """Test cases for Cutout Sticker functionality (PR #2342)"""

    def test_photo_upload_to_cutout_sticker_bypass_ai(self):
        """Test uploading a photo as cutout sticker with AI bypass (full image selection)"""
        # Download a test photo
        media_pk = self.cl.media_pk_from_url("https://www.instagram.com/p/BVDOOolFFxg/")
        path = self.cl.photo_download(media_pk)
        self.assertIsInstance(path, Path)
        media = None
        try:
            # Upload as cutout sticker with bypass_ai=True (default)
            media = self.cl.photo_upload_to_cutout_sticker(path, bypass_ai=True)
            self.assertIsInstance(media, Media)
            # Cutout stickers should have product_type "custom_sticker"
            self.assertEqual(media.product_type, "custom_sticker")
        finally:
            cleanup(path)
            if media:
                self.cl.media_delete(media.id)

    def test_photo_upload_to_cutout_sticker_with_ai(self):
        """Test uploading a photo as cutout sticker with AI detection"""
        # Download a test photo
        media_pk = self.cl.media_pk_from_url("https://www.instagram.com/p/BVDOOolFFxg/")
        path = self.cl.photo_download(media_pk)
        self.assertIsInstance(path, Path)
        media = None
        try:
            # Upload as cutout sticker with AI detection
            media = self.cl.photo_upload_to_cutout_sticker(path, bypass_ai=False)
            self.assertIsInstance(media, Media)
            self.assertEqual(media.product_type, "custom_sticker")
        finally:
            cleanup(path)
            if media:
                self.cl.media_delete(media.id)


if __name__ == "__main__":
    unittest.main()
