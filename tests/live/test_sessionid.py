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
