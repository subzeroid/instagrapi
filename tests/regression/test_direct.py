from instagrapi.exceptions import DirectMessageNotFound
from tests.helpers import *


class DirectMixinRegressionTestCase(unittest.TestCase):
    def build_client(self):
        client = Client()
        client.settings = {}
        client.authorization_data = {"ds_user_id": "1"}
        client.last_json = {}
        return client

    def test_direct_thread_update_title_posts_unsigned_title(self):
        client = self.build_client()
        client.uuid = "uuid-1"

        with mock.patch.object(client, "private_request", return_value={"status": "ok"}) as private:
            result = client.direct_thread_update_title(123, "Updated title")

        self.assertTrue(result)
        private.assert_called_once_with(
            "direct_v2/threads/123/update_title/",
            data={"_uuid": "uuid-1", "title": "Updated title"},
            with_signature=False,
        )

    def test_direct_thread_create_posts_group_payload(self):
        client = self.build_client()
        client.uuid = "uuid-1"

        with (
            mock.patch.object(client, "generate_mutation_token", return_value="mutation-token"),
            mock.patch.object(client, "private_request", return_value={"thread_id": "3402823668417103"}) as private,
        ):
            result = client.direct_thread_create([42, "43"], title="Group title")

        self.assertEqual(result, "3402823668417103")
        private.assert_called_once_with(
            "direct_v2/create_group_thread/",
            data={
                "_uuid": "uuid-1",
                "_uid": "1",
                "client_context": "mutation-token",
                "is_partnership_folder": "false",
                "recipient_users": "[42,43]",
                "thread_title": "Group title",
            },
        )

    def test_direct_thread_create_accepts_nested_thread_id_response(self):
        client = self.build_client()
        client.uuid = "uuid-1"

        with (
            mock.patch.object(client, "generate_mutation_token", return_value="mutation-token"),
            mock.patch.object(
                client,
                "private_request",
                return_value={"thread": {"thread_id": "3402823668417104"}},
            ),
        ):
            result = client.direct_thread_create([42, 43])

        self.assertEqual(result, "3402823668417104")

    def test_direct_message_returns_matching_message_by_id(self):
        client = self.build_client()
        first = DirectMessage(id="111", user_id="1", timestamp=datetime.fromtimestamp(1))
        expected = DirectMessage(id="222", user_id="1", timestamp=datetime.fromtimestamp(2))

        with mock.patch.object(client, "direct_messages", return_value=[first, expected]) as direct_messages:
            result = client.direct_message(123, "222", amount=50)

        self.assertIs(result, expected)
        direct_messages.assert_called_once_with(123, 50)

    def test_direct_message_raises_when_message_is_missing(self):
        client = self.build_client()
        message = DirectMessage(id="111", user_id="1", timestamp=datetime.fromtimestamp(1))

        with mock.patch.object(client, "direct_messages", return_value=[message]):
            with self.assertRaises(DirectMessageNotFound) as ctx:
                client.direct_message(123, 222, amount=1)

        self.assertIn("222", str(ctx.exception))

    def test_direct_message_unsend_delegates_to_delete_endpoint(self):
        client = self.build_client()

        with mock.patch.object(client, "direct_message_delete", return_value=True) as delete:
            result = client.direct_message_unsend(123, 456)

        self.assertTrue(result)
        delete.assert_called_once_with(123, 456)

    def test_direct_requests_uses_pending_inbox(self):
        client = self.build_client()
        expected = [Mock(spec=DirectThread)]

        with mock.patch.object(client, "direct_pending_inbox", return_value=expected) as pending:
            result = client.direct_requests(amount=7)

        self.assertIs(result, expected)
        pending.assert_called_once_with(7)

    def test_direct_request_approve_delegates_to_pending_approve(self):
        client = self.build_client()

        with mock.patch.object(client, "direct_pending_approve", return_value=True) as approve:
            result = client.direct_request_approve(123)

        self.assertTrue(result)
        approve.assert_called_once_with(123)

    def make_temp_file(self, suffix, content):
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            path = Path(tmp.name)
        self.addCleanup(lambda: path.unlink(missing_ok=True))
        return path

    def make_video_file(self, content=b"video-bytes"):
        return self.make_temp_file(".mp4", content)

    def make_voice_file(self, content=b"voice-bytes"):
        return self.make_temp_file(".m4a", content)

    def direct_payload(self):
        return {
            "payload": {
                "item_id": "1",
                "timestamp": 1761953663000000,
                "user_id": "1",
            }
        }

    def test_direct_send_reply_includes_replied_to_fields(self):
        client = self.build_client()
        client.uuid = "uuid-1"
        client.android_device_id = "android-device"
        reply_to_message = Mock(spec=DirectMessage)
        reply_to_message.id = "30000000000000000000000000000000000"
        reply_to_message.client_context = "reply-client-context"
        expected = Mock(spec=DirectMessage)

        with (
            mock.patch.object(client, "generate_mutation_token", return_value="mutation-token"),
            mock.patch("instagrapi.mixins.direct.extract_direct_message", return_value=expected),
            mock.patch.object(client, "private_request", return_value=self.direct_payload()) as private,
        ):
            result = client.direct_send(
                "reply text",
                thread_ids=[123],
                reply_to_message=reply_to_message,
            )

        self.assertIs(result, expected)
        private.assert_called_once_with(
            "direct_v2/threads/broadcast/text/",
            data=mock.ANY,
            with_signature=False,
        )
        data = private.call_args.kwargs["data"]
        self.assertEqual(json.loads(data["thread_ids"]), [123])
        self.assertEqual(data["replied_to_action_source"], "swipe")
        self.assertEqual(data["replied_to_item_id"], reply_to_message.id)
        self.assertEqual(data["replied_to_client_context"], reply_to_message.client_context)
        self.assertEqual(data["client_context"], "mutation-token")

    def test_direct_send_accepts_scalar_user_id(self):
        client = self.build_client()
        client.uuid = "uuid-1"
        client.android_device_id = "android-device"

        with (
            mock.patch.object(client, "generate_mutation_token", return_value="mutation-token"),
            mock.patch.object(client, "private_request", return_value=self.direct_payload()) as private,
        ):
            client.direct_send("hello", user_ids="42")

        data = private.call_args.kwargs["data"]
        self.assertEqual(json.loads(data["recipient_users"]), [[42]])

    def test_direct_send_accepts_scalar_thread_id(self):
        client = self.build_client()
        client.uuid = "uuid-1"
        client.android_device_id = "android-device"

        with (
            mock.patch.object(client, "generate_mutation_token", return_value="mutation-token"),
            mock.patch.object(client, "private_request", return_value=self.direct_payload()) as private,
        ):
            client.direct_send("hello", thread_ids="340282366841710300949128149448121770626")

        data = private.call_args.kwargs["data"]
        self.assertEqual(json.loads(data["thread_ids"]), [340282366841710300949128149448121770626])

    def test_direct_media_share_accepts_scalar_user_id(self):
        client = self.build_client()
        client.uuid = "uuid-1"
        client.android_device_id = "android-device"

        with (
            mock.patch.object(client, "generate_mutation_token", return_value="mutation-token"),
            mock.patch.object(client, "media_id", return_value="123_1"),
            mock.patch.object(
                client, "private_request", return_value=self.direct_payload() | {"status": "ok"}
            ) as private,
        ):
            client.direct_media_share("123", user_ids=42)

        data = private.call_args.kwargs["data"]
        self.assertEqual(json.loads(data["recipient_users"]), [[42]])

    def test_direct_send_reaction_posts_reaction_payload(self):
        client = self.build_client()
        client.uuid = "uuid-1"
        client.android_device_id = "android-device"

        with (
            mock.patch.object(client, "generate_mutation_token", return_value="mutation-token"),
            mock.patch.object(client, "private_request", return_value={"status": "ok"}) as private,
        ):
            result = client.direct_send_reaction(
                123,
                456,
                emoji="😂",
                client_context="original-client-context",
                action_source="reaction_sheet",
            )

        self.assertTrue(result)
        private.assert_called_once_with(
            "direct_v2/threads/broadcast/reaction/",
            data=mock.ANY,
            with_signature=False,
        )
        data = private.call_args.kwargs["data"]
        self.assertEqual(json.loads(data["thread_ids"]), ["123"])
        self.assertEqual(data["_uuid"], "uuid-1")
        self.assertEqual(data["device_id"], "android-device")
        self.assertEqual(data["client_context"], "mutation-token")
        self.assertEqual(data["offline_threading_id"], "mutation-token")
        self.assertEqual(data["mutation_token"], "mutation-token")
        self.assertEqual(data["action"], "send_item")
        self.assertEqual(data["item_type"], "reaction")
        self.assertEqual(data["reaction_type"], "like")
        self.assertEqual(data["reaction_status"], "created")
        self.assertEqual(data["node_type"], "item")
        self.assertEqual(data["item_id"], "456")
        self.assertEqual(data["emoji"], "😂")
        self.assertEqual(data["reaction_action_source"], "reaction_sheet")
        self.assertEqual(data["original_message_client_context"], "original-client-context")

    def test_direct_message_unlike_posts_deleted_reaction(self):
        client = self.build_client()
        client.uuid = "uuid-1"
        client.android_device_id = "android-device"

        with (
            mock.patch.object(client, "generate_mutation_token", return_value="mutation-token"),
            mock.patch.object(client, "private_request", return_value={"status": "ok"}) as private,
        ):
            result = client.direct_message_unlike(123, 456, client_context="original-client-context")

        self.assertTrue(result)
        data = private.call_args.kwargs["data"]
        self.assertEqual(data["reaction_status"], "deleted")
        self.assertEqual(data["emoji"], "❤")
        self.assertEqual(data["reaction_type"], "like")
        self.assertEqual(data["original_message_client_context"], "original-client-context")

    def fake_rupload_session(self, media_id):
        class FakeResponse:
            status_code = 200
            text = "{}"

            def __init__(self, payload):
                self.payload = payload

            def json(self):
                return self.payload

        class FakeSession:
            def __init__(self):
                self.proxies = {}
                self.calls = []

            def get(self, url, headers, timeout):
                self.calls.append(("GET", url, headers, None))
                return FakeResponse({"offset": 0})

            def post(self, url, data, headers, timeout):
                self.calls.append(("POST", url, headers, data))
                return FakeResponse({"media_id": media_id})

        return FakeSession()

    def test_direct_send_video_uploads_and_broadcasts_for_thread_ids(self):
        client = self.build_client()
        expected = Mock(spec=DirectMessage)
        path = self.make_video_file()

        with (
            mock.patch("instagrapi.mixins.direct.time.time", return_value=1234.567),
            mock.patch("instagrapi.mixins.direct.secrets.token_hex", return_value="a" * 32),
            mock.patch("instagrapi.mixins.direct.random.randint", return_value=111111111111),
            mock.patch.object(client, "_video_rupload", return_value=987654321) as rupload,
            mock.patch.object(client, "generate_mutation_token", return_value="mutation-token"),
            mock.patch("instagrapi.mixins.direct.extract_direct_message", return_value=expected),
            mock.patch.object(client, "private_request", return_value=self.direct_payload()) as private,
        ):
            result = client.direct_send_video(path, thread_ids=[123])

        self.assertIs(result, expected)
        rupload.assert_called_once_with(
            b"video-bytes",
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-0-11-1234567-1234567",
            "111111111111_AAAAAAAAAAAA_Mixed_0",
        )
        private.assert_called_once_with(
            "direct_v2/threads/broadcast/raven_attachment/?video=1",
            data=mock.ANY,
            with_signature=True,
        )
        data = private.call_args.kwargs["data"]
        self.assertEqual(json.loads(data["thread_ids"]), ["123"])
        self.assertEqual(data["recipient_users"], "[]")
        self.assertEqual(data["attachment_fbid"], "987654321")
        self.assertEqual(data["video_result"], "987654321")
        self.assertEqual(data["client_context"], "mutation-token")
        self.assertEqual(data["mutation_token"], "mutation-token")

    def test_direct_send_video_resolves_existing_thread_for_user_ids(self):
        client = self.build_client()
        expected = Mock(spec=DirectMessage)
        path = self.make_video_file()
        thread_id = "340282366841710300949128149448121770626"

        with (
            mock.patch.object(
                client,
                "direct_thread_by_participants",
                return_value={"thread_v2_id": thread_id},
            ) as thread_lookup,
            mock.patch.object(client, "_video_rupload", return_value=123),
            mock.patch.object(client, "generate_mutation_token", return_value="mutation-token"),
            mock.patch("instagrapi.mixins.direct.extract_direct_message", return_value=expected),
            mock.patch.object(client, "private_request", return_value=self.direct_payload()) as private,
        ):
            result = client.direct_send_video(path, user_ids=[42])

        self.assertIs(result, expected)
        thread_lookup.assert_called_once_with([42])
        data = private.call_args.kwargs["data"]
        self.assertEqual(json.loads(data["thread_ids"]), [thread_id])

    def test_direct_send_video_resolves_existing_thread_from_last_json(self):
        client = self.build_client()
        expected = Mock(spec=DirectMessage)
        path = self.make_video_file()
        thread_id = "340282366841710300949128149448121770626"

        def thread_lookup(user_ids):
            client.last_json = {"thread": {"thread_v2_id": thread_id}}
            return {"users": []}

        with (
            mock.patch.object(client, "direct_thread_by_participants", side_effect=thread_lookup) as lookup,
            mock.patch.object(client, "_video_rupload", return_value=123),
            mock.patch.object(client, "generate_mutation_token", return_value="mutation-token"),
            mock.patch("instagrapi.mixins.direct.extract_direct_message", return_value=expected),
            mock.patch.object(client, "private_request", return_value=self.direct_payload()) as private,
        ):
            result = client.direct_send_video(path, user_ids=[42])

        self.assertIs(result, expected)
        lookup.assert_called_once_with([42])
        data = private.call_args.kwargs["data"]
        self.assertEqual(json.loads(data["thread_ids"]), [thread_id])

    def test_direct_send_voice_uploads_and_broadcasts_for_thread_ids(self):
        client = self.build_client()
        expected = Mock(spec=DirectMessage)
        path = self.make_voice_file()

        with (
            mock.patch("instagrapi.mixins.direct.time.time", return_value=1234.567),
            mock.patch("instagrapi.mixins.direct.random.randint", return_value=-99),
            mock.patch.object(client, "_voice_rupload", return_value=987654321) as rupload,
            mock.patch.object(client, "generate_mutation_token", return_value="mutation-token"),
            mock.patch("instagrapi.mixins.direct.extract_direct_message", return_value=expected),
            mock.patch.object(client, "private_request", return_value=self.direct_payload()) as private,
        ):
            result = client.direct_send_voice(path, thread_ids=[123], waveform=[0.1, 0.2])

        self.assertIs(result, expected)
        rupload.assert_called_once_with(b"voice-bytes", "1234567", -99)
        private.assert_called_once_with(
            "direct_v2/threads/broadcast/voice_attachment/",
            data=mock.ANY,
            with_signature=False,
        )
        data = private.call_args.kwargs["data"]
        self.assertEqual(json.loads(data["thread_ids"]), [123])
        self.assertEqual(data["attachment_fbid"], "987654321")
        self.assertEqual(data["client_context"], "mutation-token")
        self.assertEqual(data["mutation_token"], "mutation-token")
        self.assertEqual(data["offline_threading_id"], "mutation-token")
        self.assertEqual(data["upload_id"], "1234567")
        self.assertEqual(json.loads(data["waveform"]), [0.1, 0.2])
        self.assertEqual(data["waveform_sampling_frequency_hz"], "10")

    def test_direct_send_voice_resolves_existing_thread_for_user_ids(self):
        client = self.build_client()
        expected = Mock(spec=DirectMessage)
        path = self.make_voice_file()
        thread_id = "340282366841710300949128149448121770626"

        with (
            mock.patch.object(
                client,
                "direct_thread_by_participants",
                return_value={"thread_v2_id": thread_id},
            ) as thread_lookup,
            mock.patch.object(client, "_voice_rupload", return_value=123),
            mock.patch.object(client, "generate_mutation_token", return_value="mutation-token"),
            mock.patch("instagrapi.mixins.direct.extract_direct_message", return_value=expected),
            mock.patch.object(client, "private_request", return_value=self.direct_payload()) as private,
        ):
            result = client.direct_send_voice(path, user_ids=[42], waveform=[0.3])

        self.assertIs(result, expected)
        thread_lookup.assert_called_once_with([42])
        data = private.call_args.kwargs["data"]
        self.assertEqual(json.loads(data["thread_ids"]), [int(thread_id)])
        self.assertEqual(data["attachment_fbid"], "123")
        self.assertEqual(json.loads(data["waveform"]), [0.3])

    def test_direct_send_voice_resolves_existing_thread_from_last_json(self):
        client = self.build_client()
        expected = Mock(spec=DirectMessage)
        path = self.make_voice_file()
        thread_id = "340282366841710300949128149448121770626"

        def thread_lookup(user_ids):
            client.last_json = {"thread": {"thread_v2_id": thread_id}}
            return {"users": []}

        with (
            mock.patch.object(client, "direct_thread_by_participants", side_effect=thread_lookup) as lookup,
            mock.patch.object(client, "_voice_rupload", return_value=123),
            mock.patch.object(client, "generate_mutation_token", return_value="mutation-token"),
            mock.patch("instagrapi.mixins.direct.extract_direct_message", return_value=expected),
            mock.patch.object(client, "private_request", return_value=self.direct_payload()) as private,
        ):
            result = client.direct_send_voice(path, user_ids=[42], waveform=[0.3])

        self.assertIs(result, expected)
        lookup.assert_called_once_with([42])
        data = private.call_args.kwargs["data"]
        self.assertEqual(json.loads(data["thread_ids"]), [int(thread_id)])

    def test_direct_send_video_raises_when_existing_thread_is_missing(self):
        client = self.build_client()

        with mock.patch.object(client, "direct_thread_by_participants", return_value={}) as thread_lookup:
            with mock.patch.object(client, "_video_rupload") as rupload:
                with self.assertRaises(DirectThreadNotFound):
                    client.direct_send_video("clip.mp4", user_ids=[42])

        thread_lookup.assert_called_once_with([42])
        rupload.assert_not_called()

    def test_direct_send_voice_raises_when_existing_thread_is_missing(self):
        client = self.build_client()
        path = self.make_voice_file()

        with mock.patch.object(client, "direct_thread_by_participants", return_value={}) as thread_lookup:
            with mock.patch.object(client, "_voice_rupload") as rupload:
                with self.assertRaises(DirectThreadNotFound):
                    client.direct_send_voice(path, user_ids=[42])

        thread_lookup.assert_called_once_with([42])
        rupload.assert_not_called()

    def test_video_rupload_uses_client_authorization_fallback(self):
        client = self.build_client()
        client.authorization_data = {"ds_user_id": "123", "sessionid": "raw-session"}
        client.private.headers.pop("Authorization", None)
        session = self.fake_rupload_session(media_id=987654321)

        with mock.patch("requests.Session", return_value=session):
            media_id = client._video_rupload(b"video-bytes", "entity-name", "waterfall-id")

        self.assertEqual(media_id, 987654321)
        self.assertEqual(session.calls[0][2]["authorization"], client.authorization)
        self.assertNotEqual(session.calls[0][2]["authorization"], "Bearer IGT:2:raw-session")

    def test_voice_rupload_uses_client_authorization_fallback(self):
        client = self.build_client()
        client.authorization_data = {"ds_user_id": "123", "sessionid": "raw-session"}
        client.private.headers.pop("Authorization", None)
        session = self.fake_rupload_session(media_id=987654321)

        with mock.patch("requests.Session", return_value=session):
            media_id = client._voice_rupload(b"voice-bytes", "1234567", -99)

        self.assertEqual(media_id, 987654321)
        self.assertEqual(session.calls[0][2]["authorization"], client.authorization)
        self.assertNotEqual(session.calls[0][2]["authorization"], "Bearer IGT:2:raw-session")
