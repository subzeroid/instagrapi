from tests import helpers as _helpers
from tests.helpers import *


class ClientPublicTestCase(_helpers.ClientPrivateTestCase):
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
        media_pk = self.cl.media_pk_from_url("https://www.instagram.com/p/C_BM2yAN4Rm/")
        m = self.cl.media_info_gql(media_pk)
        self.assertIsInstance(m, Media)
        self.assertEqual(m.pk, "3441088131388376166")
        self.assertEqual(m.code, "C_BM2yAN4Rm")
        self.assertEqual(m.media_type, 2)
        self.assertEqual(m.product_type, "clips")
        self.assertGreaterEqual(m.comment_count, 3)
        self.assertGreaterEqual(m.play_count, 1)
        self.assertGreaterEqual(m.view_count, 0)
        self.assertGreaterEqual(m.like_count, -1)
        self.assertTrue(m.thumbnail_url)
        self.assertTrue(m.video_url)
