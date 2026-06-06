from tests import helpers as _helpers
from tests.helpers import *


class SessionIdLoginTestCase(_helpers.ClientPrivateTestCase):
    def test_login_by_sessionid_allows_private_followup_requests(self):
        sessionid = self.cl.sessionid
        if not sessionid:
            self.skipTest("Logged-in test client did not expose sessionid")

        cl = Client(proxy=self.cl.proxy)

        self.assertTrue(cl.login_by_sessionid(sessionid))
        self.assertEqual(str(cl.account_info().pk), str(self.cl.user_id))
        self.assertIsInstance(cl.get_timeline_feed("cold_start_fetch"), dict)

    def test_login_by_sessionid_uses_private_stream_fallback_live(self):
        sessionid = self.cl.sessionid
        if not sessionid:
            self.skipTest("Logged-in test client did not expose sessionid")

        cl = Client(proxy=self.cl.proxy)
        cl.user_info_v1 = Mock(side_effect=PrivateError("force stream fallback"))

        with mock.patch.object(
            cl,
            "user_short_gql",
            side_effect=AssertionError("sessionid login should not call public GraphQL before private stream"),
        ) as public_lookup:
            self.assertTrue(cl.login_by_sessionid(sessionid))

        public_lookup.assert_not_called()
        self.assertEqual(str(cl.account_info().pk), str(self.cl.user_id))
