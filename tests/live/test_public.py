from tests import helpers as _helpers
from tests.helpers import *


class PublicTransportLiveTestCase(unittest.TestCase):
    def test_curl_public_transport_user_info_by_username_gql(self):
        try:
            import curl_adapter  # noqa: F401
        except ImportError:
            self.skipTest("instagrapi[curl] is required for curl public transport live tests")

        cl = Client(public_transport="curl", request_timeout=0, public_request_retries_count=2)
        user = cl.user_info_by_username_gql("instagram")

        self.assertIsInstance(user, User)
        self.assertEqual(user.pk, "25025320")
        self.assertEqual(user.username, "instagram")


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


class ClientClipMashupInfoLiveTestCase(unittest.TestCase):
    def live_client(self):
        if not _helpers.TEST_ACCOUNTS_URL:
            self.skipTest("TEST_ACCOUNTS_URL is required for clip mashup info live tests")
        last_error = None
        for account in _helpers.fetch_test_accounts(count=20):
            try:
                return _helpers.client_from_test_account(account)
            except Exception as exc:
                last_error = f"{type(exc).__name__}: {str(exc)[:120]}"
        self.skipTest(f"Could not login with any test account: {last_error}")

    def test_clip_mashup_info_live(self):
        cl = self.live_client()
        media_pk = cl.media_pk_from_url("https://www.instagram.com/p/C_BM2yAN4Rm/")
        result = cl.clip_mashup_info(media_pk)

        self.assertEqual(result.get("status"), "ok")
        mashup_info = result.get("mashup_info")
        self.assertIsInstance(mashup_info, dict)
        self.assertIn("is_reuse_allowed", mashup_info)
        self.assertIn("mashups_allowed", mashup_info)
