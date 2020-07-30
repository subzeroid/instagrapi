import json
import pytz
import random
import os.path
import unittest
from datetime import datetime

from client import Client


ACCOUNT_USERNAME = "instagrapi"
ACCOUNT_PASSWORD = "qwerty123456"


class FakeClientTestCase(unittest.TestCase):
    api = None

    def __init__(self, *args, **kwargs):
        self.api = Client()
        super().__init__(*args, **kwargs)

    def test_login(self):
        try:
            self.api.login(ACCOUNT_USERNAME, "fakepassword")
        except Exception as e:
            self.assertEqual(
                str(e), "The password you entered is incorrect. Please try again."
            )


class ClientPrivateTestCase(unittest.TestCase):
    api = None

    def __init__(self, *args, **kwargs):
        filename = '/tmp/instagrapi_tests_client_settings.json'
        settings = {}
        if os.path.exists(filename):
            settings = json.load(open(filename))
        self.api = Client(settings)
        # self.api.set_proxy("socks5://127.0.0.1:30235")
        self.api.login(ACCOUNT_USERNAME, ACCOUNT_PASSWORD)
        json.dump(self.api.get_settings(), open(filename, 'w'))
        super().__init__(*args, **kwargs)


class ClientPublicTestCase(unittest.TestCase):
    api = Client()

    def test_user_info_gql(self):
        user = self.api._user_info_gql(1903424587)
        for key, value in {
            "biography": "Engineer: Python, JavaScript, Erlang...",
            "blocked_by_viewer": False,
            "restricted_by_viewer": None,
            "country_block": False,
            "external_url": "https://adw0rd.com/",
            "external_url_linkshimmed": "https://...",
            "followed_by_viewer": False,
            "follows_viewer": False,
            "full_name": "Mikhail Andreev",
            "has_ar_effects": False,
            "has_channel": False,
            "has_blocked_viewer": False,
            "highlight_reel_count": 35,
            "has_requested_viewer": False,
            "id": "1903424587",
            "is_business_account": False,
            "is_joined_recently": False,
            "business_category_name": None,
            "category_id": None,
            "overall_category_name": None,
            "is_private": False,
            "is_verified": False,
            "profile_pic_url": "https://...",
            "profile_pic_url_hd": "https://...",
            "requested_by_viewer": False,
            "username": "adw0rd",
            "connected_fb_page": None,
        }.items():
            if isinstance(value, str) and "..." in value:
                self.assertTrue(value.replace("...", "") in user[key])
            else:
                self.assertEqual(value, user[key])


class ClientUserTestCase(ClientPrivateTestCase):
    def test_username_from_user_id(self):
        self.assertEqual(self.api.username_from_user_id(1903424587), "adw0rd")

    def test_user_medias(self):
        user_id = self.api.user_id_from_username("adw0rd")
        medias = self.api.user_medias(user_id, 20)
        self.assertEqual(len(medias), 20)
        media = medias[0]
        self.assertTrue("pk" in media)
        self.assertTrue("taken_at" in media)
        self.assertTrue("id" in media)
        self.assertTrue("media_type" in media)
        self.assertTrue("code" in media)
        self.assertTrue("thumbnail_url" in media)
        self.assertTrue("location" in media)
        self.assertTrue("user" in media)
        self.assertTrue("comment_count" in media)
        self.assertTrue("like_count" in media)
        self.assertTrue("caption_text" in media)
        self.assertTrue("usertags" in media)
        self.assertTrue("video_url" in media)
        self.assertTrue("view_count" in media)
        self.assertTrue("video_duration" in media)
        self.assertTrue("title" in media)

    def test_user_followers(self):
        user_id = self.api.user_id_from_username("asphalt_kings_lb")
        followers = self.api.user_followers(self.api.user_id)
        self.assertIn(user_id, followers)
        self.assertEqual(followers[user_id]["username"], "asphalt_kings_lb")

    def test_user_following(self):
        user_id = self.api.user_id_from_username("asphalt_kings_lb")
        following = self.api.user_following(self.api.user_id)
        self.assertIn(user_id, following)
        self.assertEqual(following[user_id]["username"], "asphalt_kings_lb")

    def test_user_follow_unfollow(self):
        user_id = self.api.user_id_from_username("bmxtravel")
        self.api.user_follow(user_id)
        following = self.api.user_following(self.api.user_id)
        self.assertIn(user_id, following)
        self.api.user_unfollow(user_id)
        following = self.api.user_following(self.api.user_id)
        self.assertNotIn(user_id, following)

    def test_user_info(self):
        user_id = self.api.user_id_from_username("test_instagrapi")
        user = self.api.user_info(user_id)
        self.assertTrue(user["pk"] == user_id)
        self.assertTrue(user["full_name"] == "test instagrapi")
        self.assertTrue(not user["is_private"])

    def test_user_info_by_username(self):
        user = self.api.user_info_by_username("test_instagrapi")
        self.assertTrue(user["pk"] == 32459437900)
        self.assertTrue(user["full_name"] == "test instagrapi")
        self.assertTrue(not user["is_private"])


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
            839509635015590664996804136478816097084804158656270576480243413301812,
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
        media_pk = self.api.media_pk_from_url(
            "https://www.instagram.com/p/B-Xai_vnyew/"
        )
        msg = "New caption %s" % random.randint(1, 100)
        self.api.media_edit(media_pk, msg)
        media = self.api.media_info(media_pk)
        self.assertEqual(media["caption_text"], msg)

    def test_media_edit_igtv(self):
        media_pk = self.api.media_pk_from_url(
            "https://www.instagram.com/p/B--LFQAHLeM/"
        )
        # Enter title
        title = "Title %s" % random.randint(1, 100)
        msg = "New caption %s" % random.randint(1, 100)
        self.api.media_edit(media_pk, msg, title)
        media = self.api.media_info(media_pk)
        self.assertEqual(media["title"], title)
        self.assertEqual(media["caption_text"], msg)
        # Split caption to title and caption
        title = "Title %s" % random.randint(1, 100)
        msg = "New caption %s" % random.randint(1, 100)
        self.api.media_edit(media_pk, f"{title}\n{msg}")
        media = self.api.media_info(media_pk)
        self.assertEqual(media["title"], title)
        self.assertEqual(media["caption_text"], msg)
        # Empty title (duplicate one-line caption)
        msg = "New caption %s" % random.randint(1, 100)
        self.api.media_edit(media_pk, msg, "")
        media = self.api.media_info(media_pk)
        self.assertEqual(media["title"], msg)
        self.assertEqual(media["caption_text"], msg)

    def test_media_user(self):
        user = self.api.media_user(2154602296692269830)
        for key, val in {
            "pk": 1903424587,
            "username": "adw0rd",
            "full_name": "Mikhail Andreev",
            "is_private": False,
            "is_verified": False,
            "is_unpublished": False,
        }.items():
            self.assertEqual(user[key], val)
        self.assertTrue(user["profile_pic_url"].startswith("https://"))

    def test_media_oembed(self):
        media = self.api.media_oembed("https://www.instagram.com/p/B3mr1-OlWMG/")
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
            self.assertEqual(media[key], val)
        self.assertIn("thumbnail_url", media)

    def test_media_comments(self):
        comments = self.api.media_comments(2154602296692269830)
        self.assertTrue(len(comments) > 5)
        comment_fields = comments[0].keys()
        user_fields = comments[0]["user"].keys()
        for field in [
            "pk",
            "user_id",
            "text",
            "type",
            "created_at",
            "created_at_utc",
            "content_type",
            "status",
            "bit_flags",
            "did_report_as_spam",
            "share_enabled",
            "user",
            "has_liked_comment",
            "comment_like_count",
            "inline_composer_display_condition",
        ]:
            self.assertIn(field, comment_fields)
        for field in [
            "pk",
            "username",
            "full_name",
            "is_private",
            "profile_pic_url",
            "is_verified",
        ]:
            self.assertIn(field, user_fields)

    def test_media_comment(self):
        text = "Test text [%s]" % datetime.now().strftime("%s")
        comment = self.api.media_comment(2276404890775267248, text)
        user_fields = comment.pop("user").keys()
        for key, val in {
            "content_type": "comment",
            "text": text,
            "type": 0,
            "media_id": 2276404890775267248,
            "status": "Active",
            "share_enabled": False,
        }.items():
            self.assertEqual(comment[key], val)
        self.assertIn("pk", comment)
        self.assertTrue(comment["created_at"] > 1586957900)
        self.assertTrue(comment["created_at_utc"] > 1586986700)
        for field in [
            "pk",
            "username",
            "full_name",
            "is_private",
            "profile_pic_url",
            "is_verified",
        ]:
            self.assertIn(field, user_fields)


class ClientCompareExtractTestCase(ClientPrivateTestCase):
    def test_two_extract_media_photo(self):
        # Photo with usertags
        media_pk = 2154602296692269830
        media_v1 = self.api.media_info_v1(media_pk)
        media_gql = self.api.media_info_gql(media_pk)
        self.assertTrue(media_v1.pop("thumbnail_url").startswith("https://"))
        self.assertTrue(media_gql.pop("thumbnail_url").startswith("https://"))
        self.assertTrue(media_v1.pop("comment_count") <= media_gql.pop("comment_count"))
        self.assertDictEqual(media_v1, media_gql)

    def test_two_extract_media_video(self):
        media_pk = 2155839952940084788
        media_v1 = self.api.media_info_v1(media_pk)
        media_gql = self.api.media_info_gql(media_pk)
        self.assertTrue(media_v1.pop("comment_count") <= media_gql.pop("comment_count"))
        self.assertTrue(media_v1.pop("thumbnail_url").startswith("https://"))
        self.assertTrue(media_v1.pop("video_url").startswith("https://"))
        self.assertTrue(media_gql.pop("thumbnail_url").startswith("https://"))
        self.assertTrue(media_gql.pop("video_url").startswith("https://"))
        self.assertDictEqual(media_v1, media_gql)

    def test_two_extract_media_album(self):
        media_pk = 1787135824035452364
        media_v1 = self.api.media_info_v1(media_pk)
        media_gql = self.api.media_info_gql(media_pk)
        self.assertTrue(media_v1.pop("comment_count") <= media_gql.pop("comment_count"))
        self.assertTrue(media_v1.pop("thumbnail_url").startswith("https://"))
        self.assertTrue(media_v1.pop("video_url").startswith("https://"))
        self.assertTrue(media_gql.pop("thumbnail_url").startswith("https://"))
        self.assertTrue(media_gql.pop("video_url").startswith("https://"))
        self.assertDictEqual(media_v1, media_gql)

    def test_two_extract_media_igtv(self):
        media_pk = 2060572297417487775
        media_v1 = self.api.media_info_v1(media_pk)
        media_gql = self.api.media_info_gql(media_pk)
        self.assertTrue(media_v1.pop("comment_count") <= media_gql.pop("comment_count"))
        self.assertTrue(media_v1.pop("thumbnail_url").startswith("https://"))
        self.assertTrue(media_v1.pop("video_url").startswith("https://"))
        self.assertTrue(media_gql.pop("thumbnail_url").startswith("https://"))
        self.assertTrue(media_gql.pop("video_url").startswith("https://"))
        self.assertDictEqual(media_v1, media_gql)


class ClientExtractTestCase(ClientPrivateTestCase):
    def test_extract_media_photo(self):
        media_pk = self.api.media_pk_from_url(
            "https://www.instagram.com/p/B3mr1-OlWMG/"
        )
        media = self.api.media_info(media_pk)
        self.assertTrue(len(media["resources"]) == 1)
        resource = media["resources"].pop()
        self.assertTrue(media["comments_cnt"] > 5)
        self.assertTrue(media["likes_cnt"] > 80)
        for key, val in {
            "text": "В гостях у ДК @delai_krasivo_kaifui",
            "media_pk": 2154602296692269830,
            "shortcode": "B3mr1-OlWMG",
            "owner_id": 1903424587,
            "owner_username": "adw0rd",
            "media_type": 1,
            "taken_at": datetime(2019, 10, 14, 15, 57, 10, tzinfo=pytz.UTC),
        }.items():
            self.assertEqual(media[key], val)
        for key, val in {
            "thumbnail_src": "https://",
            "media_type": 1,
            "media_pk": 2154602296692269830,
        }.items():
            if isinstance(val, str):
                self.assertTrue(resource[key].startswith(val))
            else:
                self.assertEqual(resource[key], val)

    def test_extract_media_video(self):
        media_pk = self.api.media_pk_from_url(
            "https://www.instagram.com/p/BgRIGUQFltp/"
        )
        media = self.api.media_info(media_pk)
        self.assertTrue(len(media["resources"]) == 1)
        resource = media["resources"].pop()
        self.assertTrue(media["views_cnt"] > 150)
        self.assertTrue(media["comments_cnt"] > 1)
        self.assertTrue(media["likes_cnt"] > 40)
        for key, val in {
            "text": "Веселья ради\n\n@milashensky #dowhill #skateboarding #foros #crimea",
            "media_pk": 1734202949948037993,
            "shortcode": "BgRIGUQFltp",
            "owner_id": 1903424587,
            "owner_username": "adw0rd",
            "media_type": 2,
            "taken_at": datetime(2018, 3, 13, 14, 59, 23, tzinfo=pytz.UTC),
        }.items():
            self.assertEqual(media[key], val)
        for key, val in {
            "video_url": "https://",
            "thumbnail_src": "https://",
            "media_type": 2,
            "media_pk": 1734202949948037993,
        }.items():
            if isinstance(val, str):
                self.assertTrue(resource[key].startswith(val))
            else:
                self.assertEqual(resource[key], val)

    def test_extract_media_album(self):
        media_pk = self.api.media_pk_from_url('https://www.instagram.com/p/BjNLpA1AhXM/')
        media = self.api.media_info(media_pk)
        self.assertTrue(len(media["resources"]) == 3)
        video_resource = media["resources"][0]
        photo_resource = media["resources"].pop()
        self.assertTrue(media["views_cnt"] == 0)
        self.assertTrue(media["comments_cnt"] == 0)
        self.assertTrue(media["likes_cnt"] > 40)
        for key, val in {
            "text": "@mind__flowers в Форосе под дождём, 24 мая 2018 #downhill #skateboarding #downhillskateboarding #crimea #foros #rememberwheels",
            "media_pk": 1787135824035452364,
            "shortcode": "BjNLpA1AhXM",
            "owner_id": 1903424587,
            "owner_username": "adw0rd",
            "media_type": 8,
            "taken_at": datetime(2018, 5, 25, 15, 46, 53, tzinfo=pytz.UTC),
            "product_type": "",
        }.items():
            self.assertEqual(media[key], val)
        for key, val in {
            "video_url": "https://",
            "thumbnail_src": "https://",
            "media_type": 2,
            "media_pk": 1787135361353462176,
        }.items():
            if isinstance(val, str):
                self.assertTrue(video_resource[key].startswith(val))
            else:
                self.assertEqual(video_resource[key], val)
        for key, val in {
            "video_url": "",
            "thumbnail_src": "https://",
            "media_type": 1,
            "media_pk": 1787133803186894424,
        }.items():
            if isinstance(val, str):
                self.assertTrue(photo_resource[key].startswith(val))
            else:
                self.assertEqual(photo_resource[key], val)

    def test_extract_media_igtv(self):
        media_pk = self.api.media_pk_from_url(
            "https://www.instagram.com/tv/ByYn5ZNlHWf/"
        )
        media = self.api.media_info(media_pk)
        self.assertTrue(len(media["resources"]) == 1)
        resource = media["resources"].pop()
        self.assertTrue(media["views_cnt"] > 200)
        self.assertTrue(media["comments_cnt"] > 10)
        self.assertTrue(media["likes_cnt"] > 50)
        for key, val in {
            "title": "zr trip, crimea, feb 2017. Edit by @milashensky",
            "text": "Нашёл на диске неопубликованное в инсте произведение @milashensky",
            "media_pk": 2060572297417487775,
            "shortcode": "ByYn5ZNlHWf",
            "owner_id": 1903424587,
            "owner_username": "adw0rd",
            "media_type": 99,
            "taken_at": datetime(2019, 6, 6, 22, 22, 6, tzinfo=pytz.UTC),
            "product_type": "igtv",
        }.items():
            self.assertEqual(media[key], val)
        for key, val in {
            "video_url": "https://",
            "thumbnail_src": "https://",
            "media_type": 99,
            "media_pk": 2060572297417487775,
        }.items():
            if isinstance(val, str):
                self.assertTrue(resource[key].startswith(val))
            else:
                self.assertEqual(resource[key], val)


class ClienUploadTestCase(ClientPrivateTestCase):
    def test_photo_upload(self):
        media_pk = self.api.media_pk_from_url(
            "https://www.instagram.com/p/BVDOOolFFxg/"
        )
        path = self.api.photo_download(media_pk)
        media = self.api.photo_upload(path, "Test caption for photo")
        self.assertEqual(media["caption_text"], "Test caption for photo")
        self.assertTrue(self.api.media_delete(media["id"]))

    def test_video_upload(self):
        media_pk = self.api.media_pk_from_url(
            "https://www.instagram.com/p/Bk2tOgogq9V/"
        )
        path = self.api.video_download(media_pk)
        media = self.api.video_upload(path, "Test caption for video")
        self.assertEqual(media["caption_text"], "Test caption for video")
        self.assertTrue(self.api.media_delete(media["id"]))

    def test_album_upload(self):
        media_pk = self.api.media_pk_from_url("https://www.instagram.com/p/BjNLpA1AhXM/")
        paths = self.api.album_download(media_pk)
        media = self.api.album_upload(paths, "Test caption for album")
        self.assertEqual(media["caption_text"], "Test caption for album")
        self.assertEqual(len(media["resources"]), 3)
        self.assertTrue(self.api.media_delete(media["id"]))

    def test_igtv_upload(self):
        media_pk = self.api.media_pk_from_url(
            "https://www.instagram.com/tv/B91gKCcpnTk/"
        )
        path = self.api.igtv_download(media_pk)
        media = self.api.igtv_upload(path, "Test title", "Test caption for IGTV")
        self.assertEqual(media["title"], "Test title")
        self.assertEqual(media["caption_text"], "Test caption for IGTV")
        self.assertTrue(self.api.media_delete(media["id"]))


class ClientCollectionTestCase(ClientPrivateTestCase):
    def test_collection_medias_by_name(self):
        medias = self.api.collection_medias_by_name("repost")
        self.assertTrue(len(medias) > 0)
        media = medias[0]
        for field in [
            "taken_at",
            "pk",
            "id",
            "media_type",
            "code",
            "user",
        ]:
            self.assertTrue(media[field])


if __name__ == '__main__':
    unittest.main()
