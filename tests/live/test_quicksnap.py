from tests import helpers as _helpers
from tests.helpers import *


class ClientQuickSnapLiveTestCase(_helpers.ClientPrivateTestCase):
    def __init__(self, *args, **kwargs):
        self.cl = None
        return unittest.TestCase.__init__(self, *args, **kwargs)

    def setup_method(self, *args, **kwargs):
        return None

    def setUp(self):
        if not TEST_ACCOUNTS_URL:
            self.skipTest("TEST_ACCOUNTS_URL is required for QuickSnap live tests")
        try:
            self.cl = _helpers.fresh_test_account(count=50, attempts=20, timeout=30)
        except RuntimeError as exc:
            self.skipTest(str(exc))

    @staticmethod
    def quicksnap_media_id(result):
        for post in result.get("posts") or []:
            media_ids = post.get("media_ids") or []
            if media_ids:
                return str(media_ids[0])
            if post.get("id"):
                return str(post["id"])
        for item in result.get("medias") or []:
            media = item.get("media_dict") or {}
            if media.get("id"):
                return str(media["id"])
            if media.get("pk"):
                return str(media["pk"])
        return None

    @staticmethod
    def quicksnap_media_dict(result):
        for item in result.get("medias") or []:
            media = item.get("media_dict") or {}
            if media:
                return media
        return {}

    def test_quicksnap_history_send_and_delete(self):
        history = self.cl.quicksnap_history(amount=20)
        self.assertIsInstance(history.get("edges"), list)
        self.assertIsInstance(history.get("page_info"), dict)

        media_id = None
        try:
            result = self.cl.quicksnap_send(Path("examples/kanada.jpg"))
            self.assertEqual(result.get("status"), "ok")
            media_id = self.quicksnap_media_id(result)
            self.assertTrue(media_id, "QuickSnap configure response did not include a media id")

            media = self.quicksnap_media_dict(result)
            self.assertEqual(media.get("product_type"), "quick_snap")
            self.assertEqual(media.get("audience"), "mutual_followers")
            self.assertTrue(media.get("expiring_at"))
        finally:
            if media_id:
                self.assertTrue(self.cl.quicksnap_delete(media_id))
