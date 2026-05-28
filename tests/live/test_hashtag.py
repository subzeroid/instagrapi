from tests import helpers as _helpers
from tests.helpers import *


class ClientHashtagTestCase(_helpers.ClientPrivateTestCase):
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
        hashtag = self.cl.hashtag_info("instagram")
        hashtag_v1 = self.cl.hashtag_info_v1("instagram")
        self.assertIsInstance(hashtag, Hashtag)
        self.assertIsInstance(hashtag_v1, Hashtag)
        self.assertEqual("instagram", hashtag.name)
        self.assertEqual(hashtag.id, hashtag_v1.id)
        self.assertEqual(hashtag.name, hashtag_v1.name)
        self.assertGreater(hashtag.media_count, 0)
        self.assertGreater(hashtag_v1.media_count, 0)

    def test_hashtag_medias_top(self):
        medias = self.cl.hashtag_medias_top("instagram", amount=2)
        self.assertEqual(len(medias), 2)
        self.assertIsInstance(medias[0], Media)

    def test_extract_hashtag_medias_top(self):
        medias = self.cl.hashtag_medias_top("instagram", amount=9)
        medias_v1 = self.cl.hashtag_medias_top_v1("instagram", amount=9)
        self.assertEqual(len(medias), 9)
        self.assertIsInstance(medias[0], Media)
        self.assertEqual(len(medias_v1), 9)
        self.assertIsInstance(medias_v1[0], Media)

    def test_hashtag_medias_recent(self):
        medias = self.cl.hashtag_medias_recent("instagram", amount=2)
        self.assertEqual(len(medias), 2)
        self.assertIsInstance(medias[0], Media)

    def test_extract_hashtag_medias_recent(self):
        medias_v1 = self.cl.hashtag_medias_recent_v1("instagram", amount=31)
        medias = self.cl.hashtag_medias_recent("instagram", amount=31)
        self.assertEqual(len(medias), 31)
        self.assertIsInstance(medias[0], Media)
        self.assertEqual(len(medias_v1), 31)
        self.assertIsInstance(medias_v1[0], Media)
        for media in [*medias[:10], *medias_v1[:10]]:
            data = media.model_dump()
            for f in self.REQUIRED_MEDIA_FIELDS:
                self.assertIn(f, data)
            self.assertTrue(data["pk"])
            self.assertTrue(data["id"])
            self.assertTrue(data["code"])
            self.assertTrue(data["media_type"])

    def test_hashtag_following(self):
        hashtags = self.cl.hashtag_following(amount=1)
        self.assertIsInstance(hashtags, list)
        if hashtags:
            self.assertIsInstance(hashtags[0], Hashtag)
            self.assertTrue(hashtags[0].id)
            self.assertTrue(hashtags[0].name)
