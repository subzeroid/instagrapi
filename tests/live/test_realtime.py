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
        transport = SocketMQTToTTransport(REALTIME_HOST, timeout=15, proxy=self.cl.proxy)

        try:
            realtime = self.cl.realtime_connect(transport=transport)

            self.assertTrue(realtime.connected)
            self.assertTrue(self.cl.realtime_ping())
        finally:
            self.cl.realtime_disconnect()

    def payload_contains(self, payload, expected):
        if isinstance(payload, dict):
            return any(self.payload_contains(value, expected) for value in payload.values())
        if isinstance(payload, (list, tuple)):
            return any(self.payload_contains(value, expected) for value in payload)
        return str(expected) in str(payload)

    def payload_contains_message(self, payload, text, sender_id):
        return self.payload_contains(payload, text) and self.payload_contains(payload, sender_id)

    def direct_message_visible(self, client, thread_id, text, sender_id):
        try:
            messages = client.direct_messages(thread_id, amount=10)
        except Exception:
            messages = []
        for message in messages:
            if message.text == text and str(message.user_id) == str(sender_id):
                return message
        try:
            request_threads = client.direct_requests(amount=10)
        except Exception:
            request_threads = []
        for thread in request_threads:
            if str(thread.id) != str(thread_id):
                continue
            for message in thread.messages:
                if message.text == text and str(message.user_id) == str(sender_id):
                    return message
        return None

    def test_realtime_receives_direct_message_sync_live(self):
        receiver = self.cl
        try:
            sender = self.fresh_accounts(1, exclude_user_ids={receiver.user_id})[0]
        except RuntimeError as exc:
            self.skipTest(str(exc))

        received_payloads = []
        message = None
        transport = SocketMQTToTTransport(REALTIME_HOST, timeout=10, proxy=receiver.proxy)
        text = f"instagrapi realtime live {int(time.time())}"

        receiver.realtime_on("message", received_payloads.append)
        try:
            realtime = receiver.realtime_connect(transport=transport)
            self.assertTrue(receiver.realtime_ping())
            try:
                realtime.direct_subscribe()
            except RuntimeError as exc:
                self.skipTest(str(exc))

            message = sender.direct_send(text, user_ids=[receiver.user_id])
            self.assertIsInstance(message, DirectMessage)

            deadline = time.time() + 45
            while time.time() < deadline:
                try:
                    receiver.realtime_read_once()
                except TimeoutError:
                    continue
                for payload in received_payloads:
                    if self.payload_contains_message(payload, text, sender.user_id):
                        return

            self.fail("Realtime MQTT did not deliver the Direct message sync payload")
        finally:
            receiver.realtime_disconnect()
            if message:
                try:
                    sender.direct_message_unsend(message.thread_id, message.id)
                except Exception as exc:
                    logger.warning("Realtime Direct message cleanup unsend failed: %s", exc)
                try:
                    sender.direct_thread_hide(message.thread_id)
                except Exception as exc:
                    logger.warning("Realtime Direct message cleanup sender hide failed: %s", exc)
                try:
                    receiver.direct_thread_hide(message.thread_id)
                except Exception as exc:
                    logger.warning("Realtime Direct message cleanup receiver hide failed: %s", exc)

    def test_realtime_direct_send_text_live(self):
        sender = self.cl
        try:
            receiver = self.fresh_accounts(1, exclude_user_ids={sender.user_id})[0]
        except RuntimeError as exc:
            self.skipTest(str(exc))

        setup_message = None
        mqtt_message = None
        thread_id = None
        transport = SocketMQTToTTransport(REALTIME_HOST, timeout=10, proxy=sender.proxy)
        setup_text = f"instagrapi realtime setup {int(time.time())}"
        text = f"instagrapi mqtt send live {int(time.time())}"

        try:
            setup_message = sender.direct_send(setup_text, user_ids=[receiver.user_id])
            self.assertIsInstance(setup_message, DirectMessage)
            thread_id = setup_message.thread_id

            realtime = sender.realtime_connect(transport=transport)
            self.assertTrue(realtime.connected)
            self.assertTrue(sender.realtime_ping())

            command = realtime.direct_send_text(thread_id, text)

            deadline = time.time() + 45
            while time.time() < deadline:
                try:
                    sender.realtime_read_once()
                except TimeoutError:
                    pass
                mqtt_message = self.direct_message_visible(receiver, thread_id, text, sender.user_id)
                if mqtt_message:
                    self.assertEqual(command["thread_id"], str(thread_id))
                    self.assertEqual(mqtt_message.text, text)
                    return
                time.sleep(2)

            self.fail("Realtime MQTT direct_send_text did not create a visible Direct message")
        finally:
            sender.realtime_disconnect()
            for message in (mqtt_message, setup_message):
                if not message or not thread_id:
                    continue
                try:
                    sender.direct_message_unsend(thread_id, message.id)
                except Exception as exc:
                    logger.warning("Realtime MQTT Direct send cleanup unsend failed: %s", exc)
            if thread_id:
                try:
                    sender.direct_thread_hide(thread_id)
                except Exception as exc:
                    logger.warning("Realtime MQTT Direct send cleanup sender hide failed: %s", exc)
                try:
                    receiver.direct_thread_hide(thread_id)
                except Exception as exc:
                    logger.warning("Realtime MQTT Direct send cleanup receiver hide failed: %s", exc)
