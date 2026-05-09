from tests import helpers as _helpers
from tests.helpers import *


class ClientMediaTestCase(_helpers.ClientPrivateTestCase):
    def test_media_id(self):
        self.assertEqual(self.cl.media_id(3258619191829745894), "3258619191829745894_25025320")

    def test_media_pk(self):
        self.assertEqual(self.cl.media_pk("2154602296692269830_25025320"), "2154602296692269830")

    def test_media_pk_from_code(self):
        self.assertEqual(self.cl.media_pk_from_code("B-fKL9qpeab"), "2278584739065882267")
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
            self.cl.media_pk_from_url("https://www.instagram.com/p/B-fKL9qpeab/?igshid=1xm76zkq7o1im"),
            "2278584739065882267",
        )


class ClientMediaExtendTestCase(_helpers.ClientPrivateTestCase):
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
        media_pk = self.cl.media_pk_from_url("https://www.instagram.com/tv/B91gKCcpnTk/")
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


class ClientCompareExtractTestCase(_helpers.ClientPrivateTestCase):
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


class ClientExtractTestCase(_helpers.ClientPrivateTestCase):
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
        media_pk = self.cl.media_pk_from_url("https://www.instagram.com/tv/ByYn5ZNlHWf/")
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
