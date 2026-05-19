from tests import helpers as _helpers
from tests.helpers import *


class ClientTrackLiveTestCase(_helpers.ClientPrivateTestCase):
    def __init__(self, *args, **kwargs):
        self.cl = None
        return unittest.TestCase.__init__(self, *args, **kwargs)

    def setUp(self):
        if not TEST_ACCOUNTS_URL:
            self.skipTest("TEST_ACCOUNTS_URL is required for Track live tests")
        try:
            self.cl = self.fresh_account()
        except RuntimeError as exc:
            self.skipTest(str(exc))

    def test_music_app_surfaces_live(self):
        self.assertTrue(self.cl.music_verify_original_audio_title("Original Audio"))

        trending = self.cl.music_trending()
        self.assertEqual(trending.get("status"), "ok")
        self.assertIsInstance(trending.get("items"), list)

        search = self.cl.music_search_v2("love")
        self.assertEqual(search.get("status"), "ok")
