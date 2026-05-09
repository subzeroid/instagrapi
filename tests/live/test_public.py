from tests import helpers as _helpers
from tests.helpers import *


class ClientPublicTestCase(_helpers.BaseClientMixin, unittest.TestCase):
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
