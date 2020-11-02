import os
import json
import random
import os.path
import unittest
from datetime import datetime

from instagrapi import Client


ACCOUNT_USERNAME = os.environ.get("IG_USERNAME", "instagrapi2")
ACCOUNT_PASSWORD = os.environ.get("IG_PASSWORD", "yoa5af6deeRujeec")


def cleanup(*paths):
    for path in paths:
        try:
            os.remove(path)
            os.remove(f'{path}.jpg')
        except FileNotFoundError:
            continue


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
        filename = f'/tmp/instagrapi_tests_client_settings_{ACCOUNT_USERNAME}.json'
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
        user = self.api.user_info_gql(1903424587)
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
        user_id = self.api.user_id_from_username("adw0rd")
        user = self.api.user_info(user_id)
        self.assertTrue(user["pk"] == user_id)
        self.assertTrue(user["full_name"] == "Mikhail Andreev")
        self.assertTrue(not user["is_private"])

    def test_user_info_by_username(self):
        user = self.api.user_info_by_username("adw0rd")
        self.assertTrue(user["pk"] == 1903424587)
        self.assertTrue(user["full_name"] == "Mikhail Andreev")
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
        try:
            msg = "Test caption for photo"
            media = self.api.photo_upload(path, msg)
            self.assertEqual(media["caption_text"], msg)
            # Change caption
            media_pk = media['pk']
            msg = "New caption %s" % random.randint(1, 100)
            self.api.media_edit(media_pk, msg)
            media = self.api.media_info(media_pk)
            self.assertEqual(media["caption_text"], msg)
            self.assertTrue(self.api.media_delete(media_pk))
        finally:
            cleanup(path)

    def test_media_edit_igtv(self):
        media_pk = self.api.media_pk_from_url(
            "https://www.instagram.com/tv/B91gKCcpnTk/"
        )
        path = self.api.igtv_download(media_pk)
        try:
            media = self.api.igtv_upload(path, "Test title", "Test caption for IGTV")
            media_pk = media['pk']
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
            self.assertTrue(self.api.media_delete(media["id"]))
        finally:
            cleanup(path)

    def test_media_user(self):
        user = self.api.media_user(2154602296692269830)
        for key, val in {
            "pk": 1903424587,
            "username": "adw0rd",
            "full_name": "Mikhail Andreev",
            "is_private": False,
            "is_verified": False,
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
    def assertLocation(self, one, two):
        for key, val in one.items():
            gql = two[key]
            if isinstance(val, float):
                val, gql = round(val, 4), round(gql, 4)
            self.assertEqual(val, gql)

    def test_two_extract_media_photo(self):
        # Photo with usertags
        media_pk = 2154602296692269830
        media_v1 = self.api.media_info_v1(media_pk)
        media_gql = self.api.media_info_gql(media_pk)
        self.assertTrue(media_v1.pop("thumbnail_url").startswith("https://"))
        self.assertTrue(media_gql.pop("thumbnail_url").startswith("https://"))
        self.assertTrue(media_v1.pop("comment_count") <= media_gql.pop("comment_count"))
        self.assertLocation(media_v1.pop('location'), media_gql.pop('location'))
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
        self.assertLocation(media_v1.pop('location'), media_gql.pop('location'))
        self.assertDictEqual(media_v1, media_gql)

    def test_two_extract_media_album(self):
        media_pk = 1787135824035452364
        media_v1 = self.api.media_info_v1(media_pk)
        media_gql = self.api.media_info_gql(media_pk)
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
        media_pk = 2060572297417487775
        media_v1 = self.api.media_info_v1(media_pk)
        media_gql = self.api.media_info_gql(media_pk)
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
        self.assertTrue(len(media["resources"]) == 0)
        self.assertTrue(media["comment_count"] > 5)
        self.assertTrue(media["like_count"] > 80)
        for key, val in {
            "caption_text": "В гостях у ДК @delai_krasivo_kaifui",
            "thumbnail_url": "https://",
            "pk": 2154602296692269830,
            "code": "B3mr1-OlWMG",
            "media_type": 1,
            "taken_at": 1571068630
        }.items():
            if isinstance(val, str):
                self.assertTrue(media[key].startswith(val))
            else:
                self.assertEqual(media[key], val)
        for key, val in {"pk": 1903424587, "username": "adw0rd"}.items():
            self.assertEqual(media['user'][key], val)

    def test_extract_media_video(self):
        media_pk = self.api.media_pk_from_url(
            "https://www.instagram.com/p/BgRIGUQFltp/"
        )
        media = self.api.media_info(media_pk)
        self.assertTrue(len(media["resources"]) == 0)
        self.assertTrue(media["view_count"] > 150)
        self.assertTrue(media["comment_count"] > 1)
        self.assertTrue(media["like_count"] > 40)
        for key, val in {
            "caption_text": "Веселья ради\n\n@milashensky #dowhill #skateboarding #foros #crimea",
            "pk": 1734202949948037993,
            "code": "BgRIGUQFltp",
            "video_url": "https://",
            "thumbnail_url": "https://",
            "media_type": 2,
            "taken_at": 1520953163
        }.items():
            if isinstance(val, str):
                self.assertTrue(media[key].startswith(val))
            else:
                self.assertEqual(media[key], val)
        for key, val in {"pk": 1903424587, "username": "adw0rd"}.items():
            self.assertEqual(media['user'][key], val)

    def test_extract_media_album(self):
        media_pk = self.api.media_pk_from_url('https://www.instagram.com/p/BjNLpA1AhXM/')
        media = self.api.media_info(media_pk)
        self.assertTrue(len(media["resources"]) == 3)
        video_resource = media["resources"][0]
        photo_resource = media["resources"].pop()
        self.assertTrue(media["view_count"] == 0)
        self.assertTrue(media["comment_count"] == 0)
        self.assertTrue(media["like_count"] > 40)
        for key, val in {
            "caption_text": "@mind__flowers в Форосе под дождём, 24 мая 2018 #downhill #skateboarding #downhillskateboarding #crimea #foros #rememberwheels",
            "pk": 1787135824035452364,
            "code": "BjNLpA1AhXM",
            "media_type": 8,
            "taken_at": 1527263213,
            "product_type": "",
        }.items():
            self.assertEqual(media[key], val)
        for key, val in {"pk": 1903424587, "username": "adw0rd"}.items():
            self.assertEqual(media['user'][key], val)
        for key, val in {
            "video_url": "https://",
            "thumbnail_url": "https://",
            "media_type": 2,
            "pk": 1787135361353462176,
        }.items():
            if isinstance(val, str):
                self.assertTrue(video_resource[key].startswith(val))
            else:
                self.assertEqual(video_resource[key], val)
        for key, val in {
            "video_url": "",
            "thumbnail_url": "https://",
            "media_type": 1,
            "pk": 1787133803186894424,
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
        self.assertTrue(len(media["resources"]) == 0)
        self.assertTrue(media["view_count"] > 200)
        self.assertTrue(media["comment_count"] > 10)
        self.assertTrue(media["like_count"] > 50)
        for key, val in {
            "title": "zr trip, crimea, feb 2017. Edit by @milashensky",
            "caption_text": "Нашёл на диске неопубликованное в инсте произведение @milashensky",
            "pk": 2060572297417487775,
            "video_url": "https://",
            "thumbnail_url": "https://",
            "code": "ByYn5ZNlHWf",
            "media_type": 2,
            "taken_at": 1559859726,
            "product_type": "igtv",
        }.items():
            if isinstance(val, str):
                self.assertTrue(media[key].startswith(val))
            else:
                self.assertEqual(media[key], val)
        for key, val in {"pk": 1903424587, "username": "adw0rd"}.items():
            self.assertEqual(media['user'][key], val)


class ClienUploadTestCase(ClientPrivateTestCase):
    def test_photo_upload_without_location(self):
        media_pk = self.api.media_pk_from_url(
            "https://www.instagram.com/p/BVDOOolFFxg/"
        )
        path = self.api.photo_download(media_pk)
        try:
            media = self.api.photo_upload(path, "Test caption for photo")
            self.assertEqual(media["caption_text"], "Test caption for photo")
            self.assertFalse(media["location"])
        finally:
            cleanup(path)
            self.assertTrue(self.api.media_delete(media["id"]))

    def test_photo_upload(self):
        media_pk = self.api.media_pk_from_url(
            "https://www.instagram.com/p/BVDOOolFFxg/"
        )
        path = self.api.photo_download(media_pk)
        try:
            media = self.api.photo_upload(
                path,
                "Test caption for photo",
                location={'lat': 59.939095, 'lng': 30.315868}
            )
            self.assertEqual(media["caption_text"], "Test caption for photo")
            for key, val in {'pk': 213597007, 'name': 'Palace Square', 'lat': 59.939166666667, 'lng': 30.315833333333}.items():
                self.assertEqual(media["location"][key], val)
        finally:
            cleanup(path)
            self.assertTrue(self.api.media_delete(media["id"]))

    def test_video_upload(self):
        media_pk = self.api.media_pk_from_url(
            "https://www.instagram.com/p/Bk2tOgogq9V/"
        )
        path = self.api.video_download(media_pk)
        try:
            media = self.api.video_upload(
                path,
                "Test caption for video",
                location={'lat': 59.939095, 'lng': 30.315868}
            )
            self.assertEqual(media["caption_text"], "Test caption for video")
            for key, val in {'pk': 213597007, 'name': 'Palace Square', 'lat': 59.939166666667, 'lng': 30.315833333333}.items():
                self.assertEqual(media["location"][key], val)
        finally:
            cleanup(path)
            self.assertTrue(self.api.media_delete(media["id"]))

    def test_album_upload(self):
        media_pk = self.api.media_pk_from_url("https://www.instagram.com/p/BjNLpA1AhXM/")
        paths = self.api.album_download(media_pk)
        try:
            media = self.api.album_upload(
                paths,
                "Test caption for album",
                location={'lat': 59.939095, 'lng': 30.315868}
            )
            self.assertEqual(media["caption_text"], "Test caption for album")
            self.assertEqual(len(media["resources"]), 3)
            for key, val in {'pk': 213597007, 'name': 'Palace Square', 'lat': 59.939166666667, 'lng': 30.315833333333}.items():
                self.assertEqual(media["location"][key], val)
        finally:
            cleanup(*paths)
            self.assertTrue(self.api.media_delete(media["id"]))

    def test_igtv_upload(self):
        media_pk = self.api.media_pk_from_url(
            "https://www.instagram.com/tv/B91gKCcpnTk/"
        )
        path = self.api.igtv_download(media_pk)
        try:
            media = self.api.igtv_upload(
                path,
                "Test title",
                "Test caption for IGTV",
                location={'lat': 59.939095, 'lng': 30.315868}
            )
            self.assertEqual(media["title"], "Test title")
            self.assertEqual(media["caption_text"], "Test caption for IGTV")
            for key, val in {'pk': 213597007, 'name': 'Palace Square', 'lat': 59.939166666667, 'lng': 30.315833333333}.items():
                self.assertEqual(media["location"][key], val)
        finally:
            cleanup(path)
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
