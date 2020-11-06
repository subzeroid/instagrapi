import os
import json
import pytz
import random
import os.path
import unittest
from pathlib import Path
from datetime import datetime

from instagrapi import Client
from instagrapi.types import (
    User, UserShort, Media, MediaOembed, Comment, Collection,
    DirectThread, DirectMessage, Usertag, Location, Account
)


ACCOUNT_USERNAME = os.environ.get("IG_USERNAME", "instagrapi2")
ACCOUNT_PASSWORD = os.environ.get("IG_PASSWORD", "yoa5af6deeRujeec")


REQUIRED_MEDIA_FIELDS = [
    "pk", "taken_at", "id", "media_type", "code", "thumbnail_url", "location",
    "user", "comment_count", "like_count", "caption_text", "usertags",
    "video_url", "view_count", "video_duration", "title"
]


def cleanup(*paths):
    for path in paths:
        try:
            os.remove(path)
            os.remove(f'{path}.jpg')
        except FileNotFoundError:
            continue


class BaseClientMixin:

    def __init__(self, *args, **kwargs):
        if self.api is None:
            self.api = Client()
        self.set_proxy_if_exists()
        super().__init__(*args, **kwargs)

    def set_proxy_if_exists(self):
        proxy = os.environ.get("IG_PROXY", "")
        if proxy:
            self.api.set_proxy(proxy)  # "socks5://127.0.0.1:30235"
        return True


class FakeClientTestCase(BaseClientMixin, unittest.TestCase):
    api = None

    def test_login(self):
        try:
            self.api.login(ACCOUNT_USERNAME, "fakepassword")
        except Exception as e:
            self.assertEqual(
                str(e), "The password you entered is incorrect. Please try again."
            )


class ClientPrivateTestCase(BaseClientMixin, unittest.TestCase):
    api = None

    def __init__(self, *args, **kwargs):
        filename = f'/tmp/instagrapi_tests_client_settings_{ACCOUNT_USERNAME}.json'
        settings = {}
        if os.path.exists(filename):
            settings = json.load(open(filename))
        self.api = Client(settings)
        self.set_proxy_if_exists()
        self.api.login(ACCOUNT_USERNAME, ACCOUNT_PASSWORD)
        json.dump(self.api.get_settings(), open(filename, 'w'))
        super().__init__(*args, **kwargs)


class ClientPublicTestCase(BaseClientMixin, unittest.TestCase):
    api = None

    def test_user_info_gql(self):
        user = self.api.user_info_gql(1903424587)
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


class ClientUserTestCase(ClientPrivateTestCase):
    def test_username_from_user_id(self):
        self.assertEqual(self.api.username_from_user_id(1903424587), "adw0rd")

    def test_user_medias(self):
        user_id = self.api.user_id_from_username("adw0rd")
        medias = self.api.user_medias(user_id, 20)
        self.assertEqual(len(medias), 20)
        media = medias[0]
        self.assertIsInstance(media, Media)
        for field in REQUIRED_MEDIA_FIELDS:
            self.assertTrue(hasattr(media, field))

    def test_user_followers(self):
        user_id = self.api.user_id_from_username("asphalt_kings_lb")
        followers = self.api.user_followers(self.api.user_id)
        self.assertIn(user_id, followers)
        self.assertEqual(followers[user_id].username, "asphalt_kings_lb")

    def test_user_following(self):
        user_id = self.api.user_id_from_username("asphalt_kings_lb")
        following = self.api.user_following(self.api.user_id)
        self.assertIn(user_id, following)
        self.assertEqual(following[user_id].username, "asphalt_kings_lb")

    def test_user_follow_unfollow(self):
        user_id = self.api.user_id_from_username("bmxtravel")
        self.api.user_follow(user_id)
        following = self.api.user_following(self.api.user_id)
        self.assertIn(user_id, following)
        self.api.user_unfollow(user_id)
        following = self.api.user_following(self.api.user_id)
        self.assertNotIn(user_id, following)

    def test_user_info(self):
        user_id = self.api.user_id_from_username("adw0rd")
        user = self.api.user_info(user_id)
        self.assertIsInstance(user, User)
        self.assertEqual(user.pk, user_id)
        self.assertEqual(user.full_name, "Mikhail Andreev")
        self.assertFalse(user.is_private)

    def test_user_info_by_username(self):
        user = self.api.user_info_by_username("adw0rd")
        self.assertIsInstance(user, User)
        self.assertEqual(user.pk, 1903424587)
        self.assertEqual(user.full_name, "Mikhail Andreev")
        self.assertFalse(user.is_private)


class ClientMediaTestCase(ClientPrivateTestCase):
    def test_media_id(self):
        self.assertEqual(
            self.api.media_id(2154602296692269830), "2154602296692269830_1903424587"
        )

    def test_media_pk(self):
        self.assertEqual(
            self.api.media_pk("2154602296692269830_1903424587"), 2154602296692269830
        )

    def test_media_pk_from_code(self):
        self.assertEqual(
            self.api.media_pk_from_code("B-fKL9qpeab"), 2278584739065882267
        )
        self.assertEqual(
            self.api.media_pk_from_code("B8jnuB2HAbyc0q001y3F9CHRSoqEljK_dgkJjo0"),
            2243811726252050162,
        )

    def test_media_pk_from_url(self):
        self.assertEqual(
            self.api.media_pk_from_url("https://instagram.com/p/B1LbfVPlwIA/"),
            2110901750722920960,
        )
        self.assertEqual(
            self.api.media_pk_from_url(
                "https://www.instagram.com/p/B-fKL9qpeab/?igshid=1xm76zkq7o1im"
            ),
            2278584739065882267,
        )

    def test_media_edit(self):
        # Upload photo
        media_pk = self.api.media_pk_from_url("https://www.instagram.com/p/BVDOOolFFxg/")
        path = self.api.photo_download(media_pk)
        self.assertIsInstance(path, Path)
        try:
            msg = "Test caption for photo"
            media = self.api.photo_upload(path, msg)
            self.assertIsInstance(media, Media)
            self.assertEqual(media.caption_text, msg)
            # Change caption
            msg = "New caption %s" % random.randint(1, 100)
            self.api.media_edit(media.pk, msg)
            media = self.api.media_info(media.pk)
            self.assertIsInstance(media, Media)
            self.assertEqual(media.caption_text, msg)
            self.assertTrue(self.api.media_delete(media.pk))
        finally:
            cleanup(path)

    def test_media_edit_igtv(self):
        media_pk = self.api.media_pk_from_url(
            "https://www.instagram.com/tv/B91gKCcpnTk/"
        )
        path = self.api.igtv_download(media_pk)
        self.assertIsInstance(path, Path)
        try:
            media = self.api.igtv_upload(path, "Test title", "Test caption for IGTV")
            self.assertIsInstance(media, Media)
            # Enter title
            title = "Title %s" % random.randint(1, 100)
            msg = "New caption %s" % random.randint(1, 100)
            self.api.media_edit(media.pk, msg, title)
            media = self.api.media_info(media.pk)
            self.assertIsInstance(media, Media)
            self.assertEqual(media.title, title)
            self.assertEqual(media.caption_text, msg)
            # Split caption to title and caption
            title = "Title %s" % random.randint(1, 100)
            msg = "New caption %s" % random.randint(1, 100)
            self.api.media_edit(media.pk, f"{title}\n{msg}")
            media = self.api.media_info(media.pk)
            self.assertIsInstance(media, Media)
            self.assertEqual(media.title, title)
            self.assertEqual(media.caption_text, msg)
            # Empty title (duplicate one-line caption)
            msg = "New caption %s" % random.randint(1, 100)
            self.api.media_edit(media.pk, msg, "")
            media = self.api.media_info(media.pk)
            self.assertIsInstance(media, Media)
            self.assertEqual(media.title, msg)
            self.assertEqual(media.caption_text, msg)
            self.assertTrue(self.api.media_delete(media.id))
        finally:
            cleanup(path)

    def test_media_user(self):
        user = self.api.media_user(2154602296692269830)
        self.assertIsInstance(user, UserShort)
        for key, val in {
            "pk": 1903424587,
            "username": "adw0rd",
            "full_name": "Mikhail Andreev",
        }.items():
            self.assertEqual(getattr(user, key), val)
        self.assertTrue(user.profile_pic_url.startswith("https://"))

    def test_media_oembed(self):
        media_oembed = self.api.media_oembed(
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

    def test_media_comments(self):
        comments = self.api.media_comments(2154602296692269830)
        self.assertTrue(len(comments) > 5)
        comment = comments[0]
        self.assertIsInstance(comment, Comment)
        comment_fields = comment.fields.keys()
        user_fields = comment.user.fields.keys()
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
        now = datetime.now(tz=pytz.UTC)
        comment = self.api.media_comment(2276404890775267248, text)
        self.assertIsInstance(comment, Comment)
        comment = comment.dict()
        for key, val in {
            "text": text,
            "content_type": "comment",
            "status": "Active"
        }.items():
            self.assertEqual(comment[key], val)
        self.assertIn("pk", comment)
        self.assertTrue(comment["created_at_utc"] >= now)
        user_fields = comment['user'].keys()
        for field in ["pk", "username", "full_name", "profile_pic_url"]:
            self.assertIn(field, user_fields)


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

    def media_info(self, media_pk):
        media_v1 = self.api.media_info_v1(media_pk)
        self.assertIsInstance(media_v1, Media)
        media_gql = self.api.media_info_gql(media_pk)
        self.assertIsInstance(media_gql, Media)
        return media_v1.dict(), media_gql.dict()

    def test_two_extract_media_photo(self):
        media_v1, media_gql = self.media_info(
            self.api.media_pk_from_code('B3mr1-OlWMG')
        )
        self.assertTrue(media_v1.pop("thumbnail_url").startswith("https://"))
        self.assertTrue(media_gql.pop("thumbnail_url").startswith("https://"))
        self.assertTrue(media_v1.pop("comment_count") <= media_gql.pop("comment_count"))
        self.assertLocation(media_v1.pop('location'), media_gql.pop('location'))
        self.assertDictEqual(media_v1, media_gql)

    def test_two_extract_media_video(self):
        media_v1, media_gql = self.media_info(
            self.api.media_pk_from_code('B3rFQPblq40')
        )
        self.assertTrue(media_v1.pop("comment_count") <= media_gql.pop("comment_count"))
        self.assertTrue(media_v1.pop("thumbnail_url").startswith("https://"))
        self.assertTrue(media_v1.pop("video_url").startswith("https://"))
        self.assertTrue(media_gql.pop("thumbnail_url").startswith("https://"))
        self.assertTrue(media_gql.pop("video_url").startswith("https://"))
        self.assertLocation(media_v1.pop('location'), media_gql.pop('location'))
        self.assertDictEqual(media_v1, media_gql)

    def test_two_extract_media_album(self):
        media_v1, media_gql = self.media_info(
            self.api.media_pk_from_code('BjNLpA1AhXM')
        )
        self.assertTrue(media_v1.pop("comment_count") <= media_gql.pop("comment_count"))
        for res in media_v1['resources']:
            self.assertTrue(res.pop("thumbnail_url").startswith("https://"))
            if res['media_type'] == 2:
                self.assertTrue(res.pop("video_url").startswith("https://"))
        for res in media_gql['resources']:
            self.assertTrue(res.pop("thumbnail_url").startswith("https://"))
            if res['media_type'] == 2:
                self.assertTrue(res.pop("video_url").startswith("https://"))
        self.assertLocation(media_v1.pop('location'), media_gql.pop('location'))
        self.assertDictEqual(media_v1, media_gql)

    def test_two_extract_media_igtv(self):
        media_v1, media_gql = self.media_info(
            self.api.media_pk_from_code('ByYn5ZNlHWf')
        )
        self.assertTrue(media_v1.pop("comment_count") <= media_gql.pop("comment_count"))
        self.assertTrue(media_v1.pop("thumbnail_url").startswith("https://"))
        self.assertTrue(media_v1.pop("video_url").startswith("https://"))
        self.assertTrue(media_gql.pop("thumbnail_url").startswith("https://"))
        self.assertTrue(media_gql.pop("video_url").startswith("https://"))
        self.assertLocation(media_v1.pop('location'), media_gql.pop('location'))
        self.assertDictEqual(media_v1, media_gql)


class ClientExtractTestCase(ClientPrivateTestCase):
    def test_extract_media_photo(self):
        media_pk = self.api.media_pk_from_url(
            "https://www.instagram.com/p/B3mr1-OlWMG/"
        )
        media = self.api.media_info(media_pk)
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
            "taken_at": datetime(2019, 10, 14, 15, 57, 10, tzinfo=pytz.UTC)
        }.items():
            if isinstance(val, str):
                self.assertTrue(getattr(media, key).startswith(val))
            else:
                self.assertEqual(getattr(media, key), val)
        for key, val in {"pk": 1903424587, "username": "adw0rd"}.items():
            self.assertEqual(getattr(media.user, key), val)

    def test_extract_media_video(self):
        media_pk = self.api.media_pk_from_url(
            "https://www.instagram.com/p/BgRIGUQFltp/"
        )
        media = self.api.media_info(media_pk)
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
            "taken_at": datetime(2018, 3, 13, 14, 59, 23, tzinfo=pytz.UTC)
        }.items():
            if isinstance(val, str):
                self.assertTrue(getattr(media, key).startswith(val))
            else:
                self.assertEqual(getattr(media, key), val)
        for key, val in {"pk": 1903424587, "username": "adw0rd"}.items():
            self.assertEqual(getattr(media.user, key), val)

    def test_extract_media_album(self):
        media_pk = self.api.media_pk_from_url('https://www.instagram.com/p/BjNLpA1AhXM/')
        media = self.api.media_info(media_pk)
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
            "taken_at": datetime(2018, 5, 25, 15, 46, 53, tzinfo=pytz.UTC),
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
        media_pk = self.api.media_pk_from_url(
            "https://www.instagram.com/tv/ByYn5ZNlHWf/"
        )
        media = self.api.media_info(media_pk)
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
            "taken_at": datetime(2019, 6, 6, 22, 22, 6, tzinfo=pytz.UTC),
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
        location = self.api.location_search(lat=59.939095, lng=30.315868)[0]
        self.assertIsInstance(location, Location)
        return location

    def assertLocation(self, location):
        for key, val in {'pk': 213597007, 'name': 'Palace Square', 'lat': 59.939166666667, 'lng': 30.315833333333}.items():
            self.assertEqual(getattr(location, key), val)

    def test_photo_upload_without_location(self):
        media_pk = self.api.media_pk_from_url(
            "https://www.instagram.com/p/BVDOOolFFxg/"
        )
        path = self.api.photo_download(media_pk)
        self.assertIsInstance(path, Path)
        try:
            media = self.api.photo_upload(path, "Test caption for photo")
            self.assertIsInstance(media, Media)
            self.assertEqual(media.caption_text, "Test caption for photo")
            self.assertFalse(media.location)
        finally:
            cleanup(path)
            self.assertTrue(self.api.media_delete(media.id))

    def test_photo_upload(self):
        media_pk = self.api.media_pk_from_url(
            "https://www.instagram.com/p/BVDOOolFFxg/"
        )
        path = self.api.photo_download(media_pk)
        self.assertIsInstance(path, Path)
        try:
            media = self.api.photo_upload(
                path, "Test caption for photo",
                location=self.get_location()
            )
            self.assertIsInstance(media, Media)
            self.assertEqual(media.caption_text, "Test caption for photo")
            self.assertLocation(media.location)
        finally:
            cleanup(path)
            self.assertTrue(self.api.media_delete(media.id))

    def test_video_upload(self):
        media_pk = self.api.media_pk_from_url(
            "https://www.instagram.com/p/Bk2tOgogq9V/"
        )
        path = self.api.video_download(media_pk)
        self.assertIsInstance(path, Path)
        try:
            media = self.api.video_upload(
                path, "Test caption for video",
                location=self.get_location()
            )
            self.assertIsInstance(media, Media)
            self.assertEqual(media.caption_text, "Test caption for video")
            self.assertLocation(media.location)
        finally:
            cleanup(path)
            self.assertTrue(self.api.media_delete(media.id))

    def test_album_upload(self):
        media_pk = self.api.media_pk_from_url("https://www.instagram.com/p/BjNLpA1AhXM/")
        paths = self.api.album_download(media_pk)
        [self.assertIsInstance(path, Path) for path in paths]
        try:
            adw0rd = self.api.user_info_by_username('adw0rd')
            location = self.get_location()
            media = self.api.album_upload(
                paths, "Test caption for album",
                usertags=[Usertag(user=adw0rd, x=0.5, y=0.5)],
                location=location
            )
            self.assertIsInstance(media, Media)
            self.assertEqual(media.caption_text, "Test caption for album")
            self.assertEqual(len(media.resources), 3)
            self.assertLocation(media.location)
        finally:
            cleanup(*paths)
            self.assertTrue(self.api.media_delete(media.id))

    def test_igtv_upload(self):
        media_pk = self.api.media_pk_from_url(
            "https://www.instagram.com/tv/B91gKCcpnTk/"
        )
        path = self.api.igtv_download(media_pk)
        self.assertIsInstance(path, Path)
        try:
            media = self.api.igtv_upload(
                path, "Test title", "Test caption for IGTV",
                location=self.get_location()
            )
            self.assertIsInstance(media, Media)
            self.assertEqual(media.title, "Test title")
            self.assertEqual(media.caption_text, "Test caption for IGTV")
            self.assertLocation(media.location)
        finally:
            cleanup(path)
            self.assertTrue(self.api.media_delete(media.id))


class ClientCollectionTestCase(ClientPrivateTestCase):

    def test_collections(self):
        collections = self.api.collections()
        self.assertTrue(len(collections) > 0)
        collection = collections[0]
        self.assertIsInstance(collection, Collection)
        for field in ('id', 'name', 'type', 'media_count'):
            self.assertTrue(hasattr(collection, field))

    def test_collection_medias_by_name(self):
        medias = self.api.collection_medias_by_name("repost")
        self.assertTrue(len(medias) > 0)
        media = medias[0]
        self.assertIsInstance(media, Media)
        for field in REQUIRED_MEDIA_FIELDS:
            self.assertTrue(hasattr(media, field))


class ClientDirectTestCase(ClientPrivateTestCase):

    def test_direct_thread(self):
        # threads
        threads = self.api.direct_threads()
        self.assertTrue(len(threads) > 0)
        thread = threads[0]
        self.assertIsInstance(thread, DirectThread)
        # messages
        messages = self.api.direct_messages(thread.id, 2)
        self.assertTrue(3 > len(messages) > 0)
        message = messages[0]
        self.assertIsInstance(message, DirectMessage)
        adw0rd = self.api.user_id_from_username('adw0rd')
        ping = self.api.direct_send('Ping', user_ids=[adw0rd])
        self.assertIsInstance(ping, DirectMessage)
        pong = self.api.direct_answer(ping.thread_id, 'Pong')
        self.assertIsInstance(pong, DirectMessage)
        self.assertEqual(ping.thread_id, pong.thread_id)


class ClientAccountTestCase(ClientPrivateTestCase):

    def test_account_edit(self):
        # current
        one = self.api.user_info(self.api.user_id)
        self.assertIsInstance(one, User)
        # change
        url = 'https://trotiq.com/'
        two = self.api.account_edit(external_url=url)
        self.assertIsInstance(two, Account)
        self.assertEqual(str(two.external_url), url)
        # return back
        three = self.api.account_edit(external_url=one.external_url)
        self.assertIsInstance(three, Account)
        self.assertEqual(one.external_url, three.external_url)

    def test_account_change_picture(self):
        # current
        one = self.api.user_info(self.api.user_id)
        self.assertIsInstance(one, User)
        dhbastards = self.api.user_info_by_username('dhbastards')
        # change
        two = self.api.account_change_picture(
            self.api.photo_download_by_url(dhbastards.profile_pic_url)
        )
        self.assertIsInstance(two, UserShort)
        # return back
        three = self.api.account_change_picture(
            self.api.photo_download_by_url(one.profile_pic_url)
        )
        self.assertIsInstance(three, UserShort)


if __name__ == '__main__':
    unittest.main()
