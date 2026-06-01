from instagrapi.realtime.client import REALTIME_HOST
from instagrapi.realtime.mqttot import SocketMQTToTTransport
from tests import helpers as _helpers
from tests.helpers import *


class ClientRealtimeLiveTestCase(_helpers.ClientPrivateTestCase):
    def __init__(self, *args, **kwargs):
        self.cl = None
        return unittest.TestCase.__init__(self, *args, **kwargs)

    def setup_method(self, *args, **kwargs):
        return None

    def setUp(self):
        if not TEST_ACCOUNTS_URL:
            self.skipTest("TEST_ACCOUNTS_URL is required for Realtime live tests")
        try:
            self.cl = self.fresh_account()
        except RuntimeError as exc:
            self.skipTest(str(exc))

    def test_realtime_connect_and_ping_live(self):
        transport = SocketMQTToTTransport(REALTIME_HOST, timeout=15)

        try:
            realtime = self.cl.realtime_connect(transport=transport)

            self.assertTrue(realtime.connected)
            self.assertTrue(self.cl.realtime_ping())
        finally:
            self.cl.realtime_disconnect()
