import json
import os
import os.path
import random
import unittest
from datetime import datetime, timedelta
from json.decoder import JSONDecodeError
from pathlib import Path

from instagrapi import Client
from instagrapi.exceptions import DirectThreadNotFound
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
    Share,
    Story,
    StoryLink,
    StoryMedia,
    StoryMention,
    StorySticker,
    User,
    UserShort,
    Usertag,
)
from instagrapi.utils import generate_jazoest
from instagrapi.zones import UTC

ACCOUNT_USERNAME = os.environ.get("IG_USERNAME", "instagrapi2")
ACCOUNT_PASSWORD = os.environ.get("IG_PASSWORD", "yoa5af6deeRujeec")
ACCOUNT_SESSIONID = os.environ.get("IG_SESSIONID", "")

REQUIRED_MEDIA_FIELDS = [
    "pk", "taken_at", "id", "media_type", "code", "thumbnail_url", "location",
    "user", "comment_count", "like_count", "caption_text", "usertags",
    "video_url", "view_count", "video_duration", "title"
]
REQUIRED_STORY_FIELDS = [
    'pk', 'id', 'code', 'taken_at', 'media_type', 'product_type',
    'thumbnail_url', 'user', 'video_url', 'video_duration', 'mentions',
    'links'
]


def cleanup(*paths):
    for path in paths:
        try:
            os.remove(path)
            os.remove(f'{path}.jpg')
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
        proxy = os.environ.get("IG_PROXY", "")
        if proxy:
            self.cl.set_proxy(proxy)  # "socks5://127.0.0.1:30235"
        return True


class FakeClientTestCase(BaseClientMixin, unittest.TestCase):
    cl = None

    def test_login(self):
        try:
            self.cl.login(ACCOUNT_USERNAME, "fakepassword")
        except Exception as e:
            self.assertEqual(
                str(e), "The password you entered is incorrect. Please try again."
            )


class ClientPrivateTestCase(BaseClientMixin, unittest.TestCase):
    cl = None

    def __init__(self, *args, **kwargs):
        filename = f'/tmp/instagrapi_tests_client_settings_{ACCOUNT_USERNAME}.json'
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
            print('JSONDecodeError when read stored client settings. Use empty settings')
            print(str(e))
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
            'pk': 1532130876531694688,
            'id': '1532130876531694688_1903424587',
            'code': 'BVDOOolFFxg',
            'taken_at': datetime(2017, 6, 7, 19, 37, 35, tzinfo=UTC()),
            'media_type': 1,
            'product_type': '',
            'thumbnail_url': 'https://...',
            'location': None,
            'comment_count': 6,
            'like_count': 79,
            'has_liked': None,
            'caption_text': '#creepy #creepyclothing',
            'usertags': [],
            'video_url': None,
            'view_count': 0,
            'video_duration': 0.0,
            'title': '',
            'resources': []
        }
        self.assertDict(m.dict(), media)
        user = {
            'pk': 1903424587,
            'username': 'adw0rd',
            'full_name': 'Mikhail Andreev',
            'profile_pic_url': 'https://...',
        }
        self.assertDict(m.user.dict(), user)


class ClientTestCase(unittest.TestCase):

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
                "app_version": "117.0.0.28.123",
                "manufacturer": "LGE/lge",
                "version_code": "168361634",
                "android_release": "6.0.1",
                "android_version": 23
            },
            # "user_agent": "Instagram 117.0.0.28.123 Android (23/6.0.1; US; 168361634)"
            "user_agent": "Instagram 117.1.0.29.119 Android (27/8.1.0; 480dpi; 1080x1776; motorola; Moto G (5S); montana; qcom; ru_RU; 253447809)",
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
                "app_version": "194.0.0.36.172",
                "android_version": 26,
                "android_release": "8.0.0",
                "dpi": "480dpi",
                "resolution": "1080x1920",
                "manufacturer": "Xiaomi",
                "device": "MI 5s",
                "model": "capricorn",
                "cpu": "qcom",
                "version_code": "301484483"
            },
            "user_agent": "Instagram 194.0.0.36.172 Android (26/8.0.0; 480dpi; 1080x1920; Xiaomi; MI 5s; capricorn; qcom; en_US; 301484483)",
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
        self.assertEqual(cl.get_settings()["device_settings"], settings["device_settings"])


class ClientDeviceTestCase(ClientPrivateTestCase):

    def test_set_device(self):
        fields = ['uuids', 'cookies', 'last_login', 'device_settings', 'user_agent']
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
        self.assertDictEqual(device, settings['device_settings'])
        self.assertEqual(user_agent, settings['user_agent'])
        self.cl.user_info_by_username_v1('adw0rd')
        request_user_agent = self.cl.last_response.request.headers.get('User-Agent')
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
        self.assertDictEqual(device, cl.settings['device_settings'])
        self.assertEqual(user_agent, cl.settings['user_agent'])


class ClientUserTestCase(ClientPrivateTestCase):
    def test_username_from_user_id(self):
        self.assertEqual(self.cl.username_from_user_id(1903424587), "adw0rd")

    def test_user_medias(self):
        user_id = self.cl.user_id_from_username("adw0rd")
        medias = self.cl.user_medias(user_id)
        self.assertGreater(len(medias), 100)
        media = medias[0]
        self.assertIsInstance(media, Media)
        for field in REQUIRED_MEDIA_FIELDS:
            self.assertTrue(hasattr(media, field))

    def test_usertag_medias(self):
        user_id = self.cl.user_id_from_username("adw0rd")
        medias = self.cl.usertag_medias(user_id)
        self.assertGreater(len(medias), 50)
        media = medias[0]
        self.assertIsInstance(media, Media)
        for field in REQUIRED_MEDIA_FIELDS:
            self.assertTrue(hasattr(media, field))

    def test_user_followers(self):
        user_id = self.cl.user_id_from_username("asphalt_kings_lb")
        followers = self.cl.user_followers(self.cl.user_id)
        self.assertIn(user_id, followers)
        self.assertEqual(followers[user_id].username, "asphalt_kings_lb")

    def test_user_followers_amount(self):
        user_id = self.cl.user_id_from_username("adw0rd")
        followers = self.cl.user_followers(user_id, amount=10)
        self.assertTrue(len(followers) == 10)
        self.assertIsInstance(list(followers.values())[0], UserShort)

    def test_user_following(self):
        user_id = self.cl.user_id_from_username("asphalt_kings_lb")
        following = self.cl.user_following(self.cl.user_id)
        self.assertIn(user_id, following)
        self.assertEqual(following[user_id].username, "asphalt_kings_lb")

    def test_user_following_amount(self):
        user_id = self.cl.user_id_from_username("adw0rd")
        following = self.cl.user_following(user_id, amount=10)
        self.assertTrue(len(following) == 10)
        self.assertIsInstance(list(following.values())[0], UserShort)

    def test_user_follow_unfollow(self):
        user_id = self.cl.user_id_from_username("bmxtravel")
        self.cl.user_follow(user_id)
        following = self.cl.user_following(self.cl.user_id)
        self.assertIn(user_id, following)
        self.cl.user_unfollow(user_id)
        following = self.cl.user_following(self.cl.user_id)
        self.assertNotIn(user_id, following)

    def test_user_info(self):
        user_id = self.cl.user_id_from_username("adw0rd")
        user = self.cl.user_info(user_id)
        self.assertIsInstance(user, User)
        for key, value in {
            "biography": "Engineer: Python, JavaScript, Erlang...",
            "external_url": "https://adw0rd.com/",
            "full_name": "Mikhail Andreev",
            "pk": 1903424587,
            "is_private": False,
            "is_verified": False,
            "profile_pic_url": "https://...",
            "username": "adw0rd",
        }.items():
            if isinstance(value, str) and "..." in value:
                self.assertTrue(value.replace("...", "") in getattr(user, key))
            else:
                self.assertEqual(value, getattr(user, key))

    def test_user_info_by_username(self):
        user = self.cl.user_info_by_username("adw0rd")
        self.assertIsInstance(user, User)
        self.assertEqual(user.pk, 1903424587)
        self.assertEqual(user.full_name, "Mikhail Andreev")
        self.assertFalse(user.is_private)

    def test_age_restricted_user_info_by_username(self):
        user = self.cl.user_info_by_username("philippe_jury_")
        self.assertIsInstance(user, User)
        self.assertEqual(user.pk, 5802433335)
        self.assertEqual(user.full_name, "Philippe Jury")
        self.assertFalse(user.is_private)


class ClientMediaTestCase(ClientPrivateTestCase):
    def test_media_id(self):
        self.assertEqual(
            self.cl.media_id(2154602296692269830), "2154602296692269830_1903424587"
        )

    def test_media_pk(self):
        self.assertEqual(
            self.cl.media_pk("2154602296692269830_1903424587"), 2154602296692269830
        )

    def test_media_pk_from_code(self):
        self.assertEqual(
            self.cl.media_pk_from_code("B-fKL9qpeab"), 2278584739065882267
        )
        self.assertEqual(
            self.cl.media_pk_from_code("B8jnuB2HAbyc0q001y3F9CHRSoqEljK_dgkJjo0"),
            2243811726252050162,
        )

    def test_code_from_media_pk(self):
        self.assertEqual(
            self.cl.media_code_from_pk(2278584739065882267), "B-fKL9qpeab"
        )
        self.assertEqual(
            self.cl.media_code_from_pk(2243811726252050162), "B8jnuB2HAby"
        )

    def test_media_pk_from_url(self):
        self.assertEqual(
            self.cl.media_pk_from_url("https://instagram.com/p/B1LbfVPlwIA/"),
            2110901750722920960,
        )
        self.assertEqual(
            self.cl.media_pk_from_url(
                "https://www.instagram.com/p/B-fKL9qpeab/?igshid=1xm76zkq7o1im"
            ),
            2278584739065882267,
        )

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

    def test_media_user(self):
        user = self.cl.media_user(2154602296692269830)
        self.assertIsInstance(user, UserShort)
        for key, val in {
            "pk": 1903424587,
            "username": "adw0rd",
            "full_name": "Mikhail Andreev",
            "is_private": False,
        }.items():
            self.assertEqual(getattr(user, key), val)
        self.assertTrue(user.profile_pic_url.startswith("https://"))

    def test_media_oembed(self):
        media_oembed = self.cl.media_oembed(
            "https://www.instagram.com/p/B3mr1-OlWMG/"
        )
        self.assertIsInstance(media_oembed, MediaOembed)
        for key, val in {
            "title": "В гостях у ДК @delai_krasivo_kaifui",
            "author_name": "adw0rd",
            "author_url": "https://www.instagram.com/adw0rd",
            "author_id": 1903424587,
            "media_id": "2154602296692269830_1903424587",
            "width": 658,
            "height": None,
            "thumbnail_width": 640,
            "thumbnail_height": 480,
            "can_view": True,
        }.items():
            self.assertEqual(getattr(media_oembed, key), val)
        self.assertTrue(media_oembed.thumbnail_url.startswith('http'))

    def test_media_like_by_pk(self):
        media_pk = self.cl.media_pk_from_url(
            "https://www.instagram.com/p/ByU3LAslgWY/"
        )
        self.assertTrue(
            self.cl.media_like(media_pk)
        )

    def test_media_like_and_unlike(self):
        media_pk = self.cl.media_pk_from_url(
            "https://www.instagram.com/p/B3mr1-OlWMG/"
        )
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

    def test_media_likers(self):
        media = self.cl.user_medias(self.cl.user_id, amount=3)[-1]
        self.assertIsInstance(media, Media)
        likers = self.cl.media_likers(media.pk)
        self.assertTrue(len(likers) > 0)
        self.assertIsInstance(likers[0], UserShort)


class ClientCommentTestCase(ClientPrivateTestCase):

    def test_media_comments_amount(self):
        comments = self.cl.media_comments(2154602296692269830, amount=2)
        self.assertTrue(len(comments) == 2)
        comments = self.cl.media_comments(2154602296692269830, amount=0)
        self.assertTrue(len(comments) > 2)

    def test_media_comments(self):
        comments = self.cl.media_comments(2154602296692269830)
        self.assertTrue(len(comments) > 5)
        comment = comments[0]
        self.assertIsInstance(comment, Comment)
        comment_fields = comment.__fields__.keys()
        user_fields = comment.user.__fields__.keys()
        for field in [
            "pk",
            "text",
            "created_at_utc",
            "content_type",
            "status",
            "user"
        ]:
            self.assertIn(field, comment_fields)
        for field in [
            "pk",
            "username",
            "full_name",
            "profile_pic_url",
        ]:
            self.assertIn(field, user_fields)

    def test_media_comment(self):
        text = "Test text [%s]" % datetime.now().strftime("%s")
        now = datetime.now(tz=UTC())
        comment = self.cl.media_comment(2276404890775267248, text)
        self.assertIsInstance(comment, Comment)
        comment = comment.dict()
        for key, val in {
            "text": text,
            "content_type": "comment",
            "status": "Active"
        }.items():
            self.assertEqual(comment[key], val)
        self.assertIn("pk", comment)
        # The comment was written no more than 120 seconds ago
        self.assertTrue(
            abs((now - comment["created_at_utc"]).total_seconds()) <= 120
        )
        user_fields = comment['user'].keys()
        for field in ["pk", "username", "full_name", "profile_pic_url"]:
            self.assertIn(field, user_fields)

    def test_comment_like_and_unlike(self):
        media_pk = self.cl.media_pk_from_url(
            "https://www.instagram.com/p/B3mr1-OlWMG/"
        )
        comment = self.cl.media_comments(media_pk)[0]
        if comment.has_liked:
            self.assertTrue(
                self.cl.comment_unlike(comment.pk)
            )
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
            if key == 'external_id':
                continue  # id may differ
            gql_val = gql[key]
            if isinstance(val, float):
                val, gql_val = round(val, 4), round(gql_val, 4)
            self.assertEqual(val, gql_val)

    def assertMedia(self, v1, gql):
        self.assertTrue(v1.pop("comment_count") <= gql.pop("comment_count"))
        self.assertLocation(v1.pop('location'), gql.pop('location'))
        v1.pop('has_liked')
        gql.pop('has_liked')
        self.assertDictEqual(v1, gql)

    def media_info(self, media_pk):
        media_v1 = self.cl.media_info_v1(media_pk)
        self.assertIsInstance(media_v1, Media)
        media_gql = self.cl.media_info_gql(media_pk)
        self.assertIsInstance(media_gql, Media)
        return media_v1.dict(), media_gql.dict()

    def test_two_extract_media_photo(self):
        media_v1, media_gql = self.media_info(
            self.cl.media_pk_from_code('B3mr1-OlWMG')
        )
        self.assertTrue(media_v1.pop("thumbnail_url").startswith("https://"))
        self.assertTrue(media_gql.pop("thumbnail_url").startswith("https://"))
        self.assertMedia(media_v1, media_gql)

    def test_two_extract_media_video(self):
        media_v1, media_gql = self.media_info(
            self.cl.media_pk_from_code('B3rFQPblq40')
        )
        self.assertTrue(media_v1.pop("video_url").startswith("https://"))
        self.assertTrue(media_gql.pop("video_url").startswith("https://"))
        self.assertTrue(media_v1.pop("thumbnail_url").startswith("https://"))
        self.assertTrue(media_gql.pop("thumbnail_url").startswith("https://"))
        self.assertMedia(media_v1, media_gql)

    def test_two_extract_media_album(self):
        media_v1, media_gql = self.media_info(
            self.cl.media_pk_from_code('BjNLpA1AhXM')
        )
        for res in media_v1['resources']:
            self.assertTrue(res.pop("thumbnail_url").startswith("https://"))
            if res['media_type'] == 2:
                self.assertTrue(res.pop("video_url").startswith("https://"))
        for res in media_gql['resources']:
            self.assertTrue(res.pop("thumbnail_url").startswith("https://"))
            if res['media_type'] == 2:
                self.assertTrue(res.pop("video_url").startswith("https://"))
        self.assertMedia(media_v1, media_gql)

    def test_two_extract_media_igtv(self):
        media_v1, media_gql = self.media_info(
            self.cl.media_pk_from_code('ByYn5ZNlHWf')
        )
        self.assertTrue(media_v1.pop("video_url").startswith("https://"))
        self.assertTrue(media_gql.pop("video_url").startswith("https://"))
        self.assertTrue(media_v1.pop("thumbnail_url").startswith("https://"))
        self.assertTrue(media_gql.pop("thumbnail_url").startswith("https://"))
        self.assertMedia(media_v1, media_gql)

    def test_two_extract_user(self):
        user_v1 = self.cl.user_info_v1(1903424587)
        user_gql = self.cl.user_info_gql(1903424587)
        self.assertIsInstance(user_v1, User)
        self.assertIsInstance(user_gql, User)
        user_v1, user_gql = user_v1.dict(), user_gql.dict()
        self.assertTrue(user_v1.pop("profile_pic_url").startswith("https://"))
        self.assertTrue(user_gql.pop("profile_pic_url").startswith("https://"))
        self.assertDictEqual(user_v1, user_gql)


class ClientExtractTestCase(ClientPrivateTestCase):
    def test_extract_media_photo(self):
        media_pk = self.cl.media_pk_from_url(
            "https://www.instagram.com/p/B3mr1-OlWMG/"
        )
        media = self.cl.media_info(media_pk)
        self.assertIsInstance(media, Media)
        self.assertTrue(len(media.resources) == 0)
        self.assertTrue(media.comment_count > 5)
        self.assertTrue(media.like_count > 80)
        for key, val in {
            "caption_text": "В гостях у ДК @delai_krasivo_kaifui",
            "thumbnail_url": "https://",
            "pk": 2154602296692269830,
            "code": "B3mr1-OlWMG",
            "media_type": 1,
            "taken_at": datetime(2019, 10, 14, 15, 57, 10, tzinfo=UTC())
        }.items():
            if isinstance(val, str):
                self.assertTrue(getattr(media, key).startswith(val))
            else:
                self.assertEqual(getattr(media, key), val)
        for key, val in {"pk": 1903424587, "username": "adw0rd"}.items():
            self.assertEqual(getattr(media.user, key), val)

    def test_extract_media_video(self):
        media_pk = self.cl.media_pk_from_url(
            "https://www.instagram.com/p/BgRIGUQFltp/"
        )
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
            "taken_at": datetime(2018, 3, 13, 14, 59, 23, tzinfo=UTC())
        }.items():
            if isinstance(val, str):
                self.assertTrue(getattr(media, key).startswith(val))
            else:
                self.assertEqual(getattr(media, key), val)
        for key, val in {"pk": 1903424587, "username": "adw0rd"}.items():
            self.assertEqual(getattr(media.user, key), val)

    def test_extract_media_album(self):
        media_pk = self.cl.media_pk_from_url('https://www.instagram.com/p/BjNLpA1AhXM/')
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
        for key, val in {"pk": 1903424587, "username": "adw0rd"}.items():
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
        for key, val in {"pk": 1903424587, "username": "adw0rd"}.items():
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
                name='Palace Square',
                lat=59.939166666667,
                lng=30.315833333333
            ),
            dict(
                pk=107617247320879,
                name='Russia, Saint-Petersburg',
                address='Russia, Saint-Petersburg',
                lat=59.93318,
                lng=30.30605,
                external_id=107617247320879,
                external_id_source='facebook_places'
            )
        ]
        for data in locations:
            if data['pk'] == location.pk:
                break
        for key, val in data.items():
            itm = getattr(location, key)
            if isinstance(val, float):
                val = round(val, 2)
                itm = round(itm, 2)
            self.assertEqual(itm, val)

    def test_photo_upload_without_location(self):
        media_pk = self.cl.media_pk_from_url(
            "https://www.instagram.com/p/BVDOOolFFxg/"
        )
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
        media_pk = self.cl.media_pk_from_url(
            "https://www.instagram.com/p/BVDOOolFFxg/"
        )
        path = self.cl.photo_download(media_pk)
        self.assertIsInstance(path, Path)
        try:
            media = self.cl.photo_upload(
                path, "Test caption for photo",
                location=self.get_location()
            )
            self.assertIsInstance(media, Media)
            self.assertEqual(media.caption_text, "Test caption for photo")
            self.assertLocation(media.location)
        finally:
            cleanup(path)
            self.assertTrue(self.cl.media_delete(media.id))

    def test_video_upload(self):
        media_pk = self.cl.media_pk_from_url(
            "https://www.instagram.com/p/Bk2tOgogq9V/"
        )
        path = self.cl.video_download(media_pk)
        self.assertIsInstance(path, Path)
        try:
            media = self.cl.video_upload(
                path, "Test caption for video",
                location=self.get_location()
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
            adw0rd = self.cl.user_info_by_username('adw0rd')
            usertag = Usertag(user=adw0rd, x=0.5, y=0.5)
            location = self.get_location()
            media = self.cl.album_upload(
                paths, "Test caption for album",
                usertags=[usertag],
                location=location
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
                path, title, caption_text,
                location=self.get_location()
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
                path, caption_text,
                # location=location
            )
            self.assertIsInstance(media, Media)
            self.assertEqual(media.caption_text, caption_text)
            # self.assertLocation(media.location)
        finally:
            cleanup(path)
            self.assertTrue(self.cl.media_delete(media.id))


class ClientCollectionTestCase(ClientPrivateTestCase):

    def test_collections(self):
        collections = self.cl.collections()
        self.assertTrue(len(collections) > 0)
        collection = collections[0]
        self.assertIsInstance(collection, Collection)
        for field in ('id', 'name', 'type', 'media_count'):
            self.assertTrue(hasattr(collection, field))

    def test_collection_medias_by_name(self):
        medias = self.cl.collection_medias_by_name("Repost")
        self.assertTrue(len(medias) > 0)
        media = medias[0]
        self.assertIsInstance(media, Media)
        for field in REQUIRED_MEDIA_FIELDS:
            self.assertTrue(hasattr(media, field))

    def test_media_save_to_collection(self):
        media_pk = self.cl.media_pk_from_url(
            "https://www.instagram.com/p/B3mr1-OlWMG/"
        )
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
        adw0rd = self.cl.user_id_from_username('adw0rd')
        ping = self.cl.direct_send('Ping', user_ids=[adw0rd])
        self.assertIsInstance(ping, DirectMessage)
        pong = self.cl.direct_answer(ping.thread_id, 'Pong')
        self.assertIsInstance(pong, DirectMessage)
        self.assertEqual(ping.thread_id, pong.thread_id)
        # send direct photo
        photo = self.cl.direct_send_photo(path='examples/kanada.jpg', user_ids=[adw0rd])
        self.assertIsInstance(photo, DirectMessage)
        self.assertEqual(photo.thread_id, pong.thread_id)
        # send seen
        seen = self.cl.direct_send_seen(thread_id=thread.id)
        self.assertEqual(seen.status, 'ok')
        # mute and unmute thread
        self.assertTrue(self.cl.direct_thread_mute(thread.id))
        self.assertTrue(self.cl.direct_thread_unmute(thread.id))
        # mute video call and unmute
        self.assertTrue(self.cl.direct_thread_mute_video_call(thread.id))
        self.assertTrue(self.cl.direct_thread_unmute_video_call(thread.id))

    def test_direct_send_photo(self):
        adw0rd = self.cl.user_id_from_username('adw0rd')
        dm = self.cl.direct_send_photo(
            path='examples/kanada.jpg',
            user_ids=[adw0rd]
        )
        self.assertIsInstance(dm, DirectMessage)

    def test_direct_send_video(self):
        adw0rd = self.cl.user_id_from_username('adw0rd')
        path = self.cl.video_download(
            self.cl.media_pk_from_url('https://www.instagram.com/p/B3rFQPblq40/')
        )
        dm = self.cl.direct_send_video(path=path, user_ids=[adw0rd])
        self.assertIsInstance(dm, DirectMessage)

    def test_direct_thread_by_participants(self):
        try:
            self.cl.direct_thread_by_participants([12345])
        except DirectThreadNotFound:
            pass


class ClientAccountTestCase(ClientPrivateTestCase):

    def test_account_edit(self):
        # current
        one = self.cl.user_info(self.cl.user_id)
        self.assertIsInstance(one, User)
        # change
        url = 'https://trotiq.com/'
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
        adw0rd = self.cl.user_info_by_username('adw0rd')
        # change
        two = self.cl.account_change_picture(
            self.cl.photo_download_by_url(adw0rd.profile_pic_url)
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
        self.assertIn('Dresden', loc.name)
        self.assertIn('Dresden', loc.address)
        self.assertEqual(150300262230285, loc.external_id)
        self.assertEqual('facebook_places', loc.external_id_source)

    def test_location_complete_pk(self):
        source = Location(
            name='Daily Surf Supply',
            external_id=533689780360041,
            external_id_source='facebook_places'
        )
        result = self.cl.location_complete(source)
        self.assertIsInstance(result, Location)
        self.assertEqual(result.pk, 533689780360041)

    def test_location_complete_lat_lng(self):
        source = Location(
            pk=150300262230285,
            name='Blaues Wunder (Dresden)',
        )
        result = self.cl.location_complete(source)
        self.assertIsInstance(result, Location)
        self.assertEqual(result.lat, 51.0536111111)
        self.assertEqual(result.lng, 13.8108333333)

    def test_location_complete_external_id(self):
        source = Location(
            name='Blaues Wunder (Dresden)',
            lat=51.0536111111,
            lng=13.8108333333
        )
        result = self.cl.location_complete(source)
        self.assertIsInstance(result, Location)
        self.assertEqual(result.external_id, 150300262230285)
        self.assertEqual(result.external_id_source, 'facebook_places')

    def test_location_build(self):
        loc = self.cl.location_info(150300262230285)
        self.assertIsInstance(loc, Location)
        json_data = self.cl.location_build(loc)
        self.assertIsInstance(json_data, str)
        data = json.loads(json_data)
        self.assertIsInstance(data, dict)
        self.assertDictEqual(
            data, {
                "name": "Blaues Wunder (Dresden)",
                "address": "Dresden, Germany",
                "lat": 51.053611111111,
                "lng": 13.810833333333,
                "facebook_places_id": 150300262230285,
                "external_source": "facebook_places",
            }
        )

    def test_location_info(self):
        loc = self.cl.location_info(150300262230285)
        self.assertIsInstance(loc, Location)
        self.assertEqual(loc.pk, 150300262230285)
        self.assertEqual(loc.name, 'Blaues Wunder (Dresden)')
        self.assertEqual(loc.lng, 13.8108333333)
        self.assertEqual(loc.lat, 51.0536111111)

    def test_location_info_without_lat_lng(self):
        loc = self.cl.location_info(197780767581661)
        self.assertIsInstance(loc, Location)
        self.assertEqual(loc.pk, 197780767581661)
        self.assertEqual(loc.name, 'In The Clouds')

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


class ClientHashtagTestCase(ClientPrivateTestCase):
    REQUIRED_MEDIA_FIELDS = [
        "pk", "taken_at", "id", "media_type", "code", "thumbnail_url",
        "like_count", "caption_text", "video_url", "view_count",
        "video_duration", "title"
    ]

    def test_hashtag_info(self):
        hashtag = self.cl.hashtag_info('dhbastards')
        self.assertIsInstance(hashtag, Hashtag)
        self.assertEqual('dhbastards', hashtag.name)

    def test_extract_hashtag_info(self):
        hashtag_a1 = self.cl.hashtag_info_a1('dhbastards')
        hashtag_v1 = self.cl.hashtag_info_v1('dhbastards')
        self.assertIsInstance(hashtag_a1, Hashtag)
        self.assertIsInstance(hashtag_v1, Hashtag)
        self.assertEqual('dhbastards', hashtag_a1.name)
        self.assertEqual(hashtag_a1.id, hashtag_v1.id)
        self.assertEqual(hashtag_a1.name, hashtag_v1.name)
        self.assertEqual(hashtag_a1.media_count, hashtag_v1.media_count)

    def test_hashtag_medias_top(self):
        medias = self.cl.hashtag_medias_top('dhbastards', amount=2)
        self.assertEqual(len(medias), 2)
        self.assertIsInstance(medias[0], Media)

    def test_extract_hashtag_medias_top(self):
        medias_a1 = self.cl.hashtag_medias_top_a1('dhbastards', amount=9)
        medias_v1 = self.cl.hashtag_medias_top_v1('dhbastards', amount=9)
        self.assertEqual(len(medias_a1), 9)
        self.assertIsInstance(medias_a1[0], Media)
        self.assertEqual(len(medias_v1), 9)
        self.assertIsInstance(medias_v1[0], Media)

    def test_hashtag_medias_recent(self):
        medias = self.cl.hashtag_medias_recent('dhbastards', amount=2)
        self.assertEqual(len(medias), 2)
        self.assertIsInstance(medias[0], Media)

    def test_extract_hashtag_medias_recent(self):
        medias_v1 = self.cl.hashtag_medias_recent_v1('dhbastards', amount=31)
        medias_a1 = self.cl.hashtag_medias_recent_a1('dhbastards', amount=31)
        self.assertEqual(len(medias_a1), 31)
        self.assertIsInstance(medias_a1[0], Media)
        self.assertEqual(len(medias_v1), 31)
        self.assertIsInstance(medias_v1[0], Media)
        for i, a1 in enumerate(medias_a1[:10]):
            a1 = a1.dict()
            v1 = medias_v1[i].dict()
            for f in self.REQUIRED_MEDIA_FIELDS:
                a1_val, v1_val = a1[f], v1[f]
                is_album = a1['media_type'] == 8
                is_video = v1.get('video_duration') > 0
                if f == 'thumbnail_url' and not is_album:
                    a1_val = a1[f].path.rsplit('/', 1)[1]
                    v1_val = v1[f].path.rsplit('/', 1)[1]
                if f == 'video_url' and is_video:
                    a1_val = a1[f].path.rsplit('.', 1)[1]
                    v1_val = v1[f].path.rsplit('.', 1)[1]
                if f in ('view_count', 'like_count'):
                    # instagram can different counts for public and private
                    if f == 'view_count' and not is_video:
                        continue
                    self.assertTrue(a1_val > 1)
                    self.assertTrue(v1_val > 1)
                    continue
                self.assertEqual(a1_val, v1_val)


class ClientStoryTestCase(ClientPrivateTestCase):

    def test_story_pk_from_url(self):
        story_pk = self.cl.story_pk_from_url(
            "https://www.instagram.com/stories/dhbastards/2581281926631793076/"
        )
        self.assertEqual(story_pk, 2581281926631793076)

    def test_upload_photo_story(self):
        media_pk = self.cl.media_pk_from_url(
            "https://www.instagram.com/p/B3mr1-OlWMG/"
        )
        path = self.cl.photo_download(media_pk)
        self.assertIsInstance(path, Path)
        caption = 'Test photo caption'
        adw0rd = self.cl.user_info_by_username('adw0rd')
        self.assertIsInstance(adw0rd, User)
        mentions = [StoryMention(user=adw0rd)]
        medias = [StoryMedia(media_pk=media_pk, x=0.5, y=0.5, width=0.6, height=0.8)]
        links = [StoryLink(webUri='https://adw0rd.com/')]
        # hashtags = [StoryHashtag(hashtag=self.cl.hashtag_info('dhbastards'))]
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
                height=0.08
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
                medias=medias
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
        media_pk = self.cl.media_pk_from_url(
            "https://www.instagram.com/p/Bk2tOgogq9V/"
        )
        story = None
        path = self.cl.video_download(media_pk)
        self.assertIsInstance(path, Path)
        caption = 'Test video caption'
        adw0rd = self.cl.user_info_by_username('adw0rd')
        self.assertIsInstance(adw0rd, User)
        mentions = [StoryMention(user=adw0rd)]
        medias = [StoryMedia(media_pk=media_pk, x=0.5, y=0.5, width=0.6, height=0.8)]
        links = [StoryLink(webUri='https://adw0rd.com/')]
        # hashtags = [StoryHashtag(hashtag=self.cl.hashtag_info('dhbastards'))]
        # locations = [
        #     StoryLocation(
        #         location=Location(
        #             pk=150300262230285,
        #             name='Blaues Wunder (Dresden)',
        #         )
        #     )
        # ]
        try:
            buildout = StoryBuilder(path, caption, mentions, Path('./examples/background.png')).video(1)
            story = self.cl.video_upload_to_story(
                buildout.path,
                caption,
                mentions=buildout.mentions,
                links=links,
                # hashtags=hashtags,
                # locations=locations,
                medias=medias
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
        user_id = self.cl.user_id_from_username("dhbastards")
        stories = self.cl.user_stories(user_id, 2)
        self.assertEqual(len(stories), 2)
        story = stories[0]
        self.assertIsInstance(story, Story)
        for field in REQUIRED_STORY_FIELDS:
            self.assertTrue(hasattr(story, field))
        stories = self.cl.user_stories(
            self.cl.user_id_from_username("adw0rd")
        )
        self.assertIsInstance(stories, list)

    def test_extract_user_stories(self):
        user_id = self.cl.user_id_from_username('dhbastards')
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
                is_video = v1.get('video_duration') > 0
                if f == 'video_url' and is_video:
                    gql_val = gql[f].path.rsplit('.', 1)[1]
                    v1_val = v1[f].path.rsplit('.', 1)[1]
                elif f == "thumbnail_url":
                    self.assertIn(".jpg", gql_val)
                    self.assertIn(".jpg", v1_val)
                    continue
                elif f == "user":
                    gql_val.pop('full_name')
                    v1_val.pop('full_name')
                    gql_val.pop('is_private')
                    v1_val.pop('is_private')
                    gql_val["profile_pic_url"] = gql_val["profile_pic_url"].path
                    v1_val["profile_pic_url"] = v1_val["profile_pic_url"].path
                elif f == "mentions":
                    for item in [*gql_val, *v1_val]:
                        item['user'].pop('pk')
                        item['user'].pop('profile_pic_url')
                        item.pop('width')
                        item.pop('height')
                        item['x'] = round(item['x'], 4)
                        item['y'] = round(item['y'], 4)
                elif f == "links":
                    # [{'webUri': HttpUrl('https://youtu.be/x3GYpar-e64', scheme='https', host='youtu.be', tld='be', host_type='domain', path='/x3GYpar-e64')}]
                    # [{'webUri': HttpUrl('https://l.instagram.com/?u=https%3A%2F%2Fyoutu.be%2Fx3GYpar-e64&e=ATM59nvUNmptw8vUsyoX835T....}]
                    self.assertEqual(len(v1_val), len(gql_val))
                    if gql_val:
                        self.assertIn(
                            gql_val[0]['webUri'].host,
                            v1_val[0]['webUri'].query
                        )
                    continue
                if gql_val != v1_val:
                    import pudb;pudb.set_trace()
                self.assertEqual(gql_val, v1_val)

    def test_story_info(self):
        user_id = self.cl.user_id_from_username("dhbastards")
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
            "https://www.instagram.com/stories/highlights/17933911816568671/"
        )
        self.assertEqual(highlight_pk, 17933911816568671)

    def test_highlight_info(self):
        highlight = self.cl.highlight_info(17933911816568671)
        self.assertIsInstance(highlight, Highlight)
        self.assertEqual(highlight.pk, 17933911816568671)
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
        self.assertEqual(share.pk, 17933911816568671)
        self.assertEqual(share.type, "highlight")

    def test_share_info(self):
        share = self.cl.share_info("aGlnaGxpZ2h0OjE3OTMzOTExODE2NTY4Njcx")
        self.assertIsInstance(share, Share)
        self.assertEqual(share.pk, 17933911816568671)
        self.assertEqual(share.type, "highlight")
        # UnicodeDecodeError: 'utf-8' codec can't decode byte 0xb1 in position 6: invalid start byte
        share = self.cl.share_info("aGlnaGxpsdsdZ2h0OjE3OTg4MDg5NjI5MzgzNzcw")
        self.assertIsInstance(share, Share)
        self.assertEqual(share.pk, 17988089629383770)
        self.assertEqual(share.type, "highlight")



if __name__ == '__main__':
    unittest.main()
