import os

from instagrapi.realtime.fbns import FBNS_HOST
from instagrapi.realtime.mqttot import SocketMQTToTTransport
from tests import helpers as _helpers
from tests.helpers import *


class ClientFbnsLiveTestCase(_helpers.ClientPrivateTestCase):
    def __init__(self, *args, **kwargs):
        self.cl = None
        return unittest.TestCase.__init__(self, *args, **kwargs)

    def setup_method(self, *args, **kwargs):
        return None

    def setUp(self):
        if not TEST_ACCOUNTS_URL:
            self.skipTest("TEST_ACCOUNTS_URL is required for FBNS live tests")
        try:
            self.cl = self.fresh_account()
        except RuntimeError as exc:
            self.skipTest(str(exc))

    def payload_contains(self, payload, expected):
        if isinstance(payload, dict):
            return any(self.payload_contains(value, expected) for value in payload.values())
        if isinstance(payload, (list, tuple)):
            return any(self.payload_contains(value, expected) for value in payload)
        return str(expected) in str(payload)

    def payload_contains_push(self, payload, text, sender_id):
        return self.payload_contains(payload, text) and self.payload_contains(payload, sender_id)

    def test_fbns_connect_register_and_ping_live(self):
        registered = []
        auth_events = []
        transport = SocketMQTToTTransport(FBNS_HOST, timeout=15, proxy=self.cl.proxy)

        self.cl.set_push_disabled(False)
        self.cl.fbns_on("auth", auth_events.append)
        self.cl.fbns_on("registered", registered.append)

        try:
            fbns = self.cl.fbns_connect(transport=transport)

            self.assertTrue(fbns.connected)
            self.assertTrue(auth_events)
            self.assertTrue(fbns.auth.password)
            self.assertTrue(fbns.auth.device_id)
            self.assertTrue(registered)
            self.assertTrue(registered[0]["token"])
            self.assertTrue(self.cl.fbns_ping())
        finally:
            self.cl.fbns_disconnect()

    @unittest.skipUnless(
        os.getenv("IG_RUN_FBNS_PUSH_LIVE") == "1",
        "IG_RUN_FBNS_PUSH_LIVE=1 is required for the nondeterministic FBNS Direct push test",
    )
    def test_fbns_receives_direct_push_live(self):
        receiver = self.cl
        try:
            sender = self.fresh_accounts(1, exclude_user_ids={receiver.user_id})[0]
        except RuntimeError as exc:
            self.skipTest(str(exc))

        registered = []
        pushes = []
        received = []
        message = None
        transport = SocketMQTToTTransport(FBNS_HOST, timeout=10, proxy=receiver.proxy)
        text = f"instagrapi fbns push live {int(time.time())}"

        receiver.set_push_disabled(False)
        receiver.fbns_on("registered", registered.append)
        receiver.fbns_on("push", pushes.append)
        receiver.fbns_on("receive", received.append)

        try:
            fbns = receiver.fbns_connect(transport=transport)
            self.assertTrue(fbns.connected)
            self.assertTrue(registered)
            self.assertTrue(receiver.fbns_ping())

            message = sender.direct_send(text, user_ids=[receiver.user_id])
            self.assertIsInstance(message, DirectMessage)

            deadline = time.time() + 60
            while time.time() < deadline:
                try:
                    receiver.fbns_read_once()
                except TimeoutError:
                    continue
                for payload in pushes:
                    if self.payload_contains_push(payload, text, sender.user_id):
                        return

            self.fail(
                "FBNS did not deliver a Direct push payload for the live Direct message "
                f"(received={len(received)}, pushes={len(pushes)})"
            )
        finally:
            receiver.fbns_disconnect()
            if message:
                try:
                    sender.direct_message_unsend(message.thread_id, message.id)
                except Exception as exc:
                    logger.warning("FBNS Direct push cleanup unsend failed: %s", exc)
                try:
                    sender.direct_thread_hide(message.thread_id)
                except Exception as exc:
                    logger.warning("FBNS Direct push cleanup sender hide failed: %s", exc)
                try:
                    receiver.direct_thread_hide(message.thread_id)
                except Exception as exc:
                    logger.warning("FBNS Direct push cleanup receiver hide failed: %s", exc)
