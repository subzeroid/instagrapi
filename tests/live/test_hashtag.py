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
