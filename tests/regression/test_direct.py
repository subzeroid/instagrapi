from instagrapi.exceptions import DirectMessageNotFound
from instagrapi.extractors import extract_direct_thread
from tests.helpers import *


def direct_thread_with_left_user_payload():
    return {
        "thread_v2_id": "17898572618026348",
        "thread_id": "340282366841510300949128268610842297468",
        "items": [],
        "users": [
            {
                "pk": "123",
                "username": "member",
                "full_name": "Member",
                "profile_pic_url": "https://example.com/member.jpg",
                "is_private": False,
                "is_verified": False,
            }
        ],
        "left_users": [
            {
                "pk": "456",
                "username": "left_user",
                "full_name": "Left User",
                "profile_pic_url": "https://example.com/left.jpg",
                "is_private": False,
                "is_verified": False,
                "friendship_status": {
                    "following": False,
                    "followed_by": False,
                    "is_private": False,
                },
            }
        ],
        "admin_user_ids": [],
        "last_activity_at": 1761953663000000,
        "muted": False,
        "named": False,
        "canonical": True,
        "pending": False,
        "archived": False,
        "thread_type": "private",
        "thread_title": "Thread",
        "folder": 0,
        "vc_muted": False,
        "is_group": False,
        "mentions_muted": False,
        "approval_required_for_new_members": False,
        "input_mode": 0,
        "last_seen_at": {},
    }


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

    def test_direct_thread_add_users_posts_unsigned_user_ids(self):
        client = self.build_client()
        client.uuid = "uuid-1"

        with mock.patch.object(client, "private_request", return_value={"status": "ok"}) as private:
            result = client.direct_thread_add_users(123, [42, "43"])

        self.assertTrue(result)
        private.assert_called_once_with(
            "direct_v2/threads/123/add_user/",
            data={"_uuid": "uuid-1", "user_ids": '["42","43"]'},
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

    def test_extract_direct_thread_normalizes_left_user_friendship_status(self):
        thread = extract_direct_thread(direct_thread_with_left_user_payload())

        self.assertEqual(len(thread.left_users), 1)
        left_user = thread.left_users[0]
        self.assertEqual(left_user.pk, "456")
        self.assertEqual(left_user.friendship_status.user_id, "456")
        self.assertFalse(left_user.friendship_status.incoming_request)
        self.assertFalse(left_user.friendship_status.outgoing_request)

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

    def test_direct_threads_chunk_sends_current_inbox_query_params(self):
        client = self.build_client()

        with mock.patch.object(client, "private_request", return_value={"inbox": {"threads": []}}) as private:
            threads, cursor = client.direct_threads_chunk()

        self.assertEqual(threads, [])
        self.assertIsNone(cursor)
        params = private.call_args.kwargs["params"]
        self.assertEqual(params["eb_device_id"], "0")
        self.assertRegex(params["igd_request_log_tracking_id"], r"^[0-9a-f-]{36}$")
        self.assertEqual(params["fetch_reason"], "initial_snapshot")
        self.assertEqual(params["include_old_mrs"], "false")
        self.assertEqual(params["no_pending_badge"], "true")
        self.assertEqual(params["push_disabled"], "true")

    def test_direct_threads_chunk_uses_configured_push_state(self):
        client = self.build_client()
        client.set_push_disabled(False)

        with mock.patch.object(client, "private_request", return_value={"inbox": {"threads": []}}) as private:
            client.direct_threads_chunk()

        params = private.call_args.kwargs["params"]
        self.assertEqual(params["push_disabled"], "false")
        self.assertFalse(client.get_settings()["push_disabled"])

    def test_direct_threads_chunk_rejects_unsupported_selected_filter(self):
        client = self.build_client()

        with self.assertRaises(ValueError) as ctx:
            client.direct_threads_chunk(selected_filter="archived")

        self.assertIn("selected_filter", str(ctx.exception))
        self.assertIn("flagged", str(ctx.exception))
        self.assertIn("unread", str(ctx.exception))

    def test_direct_search_sends_current_ranked_recipient_limits(self):
        client = self.build_client()

        with mock.patch.object(client, "private_request", return_value={"ranked_recipients": []}) as private:
            result = client.direct_search("alice")

        self.assertEqual(result, [])
        params = private.call_args.kwargs["params"]
        self.assertEqual(params["max_ai_bot_results"], "0")
        self.assertEqual(params["max_ibc_results"], "20")

    def test_direct_message_search_hides_locked_threads(self):
        client = self.build_client()

        with mock.patch.object(
            client,
            "private_request",
            return_value={"status": "ok", "message_search_results": {}},
        ) as private:
            result = client.direct_message_search("alice")

        self.assertEqual(result, [])
        params = private.call_args.kwargs["params"]
        self.assertEqual(params["hide_locked_threads"], '{"message_content":"false"}')

    def test_direct_media_sends_current_thread_media_query_params(self):
        client = self.build_client()

        with mock.patch.object(
            client,
            "private_request",
            return_value={"items": [], "more_available": False},
        ) as private:
            result = client.direct_media(123)

        self.assertEqual(result, [])
        params = private.call_args.kwargs["params"]
        self.assertEqual(params["eb_device_id"], "0")
        self.assertRegex(params["igd_request_log_tracking_id"], r"^[0-9a-f-]{36}$")
        self.assertEqual(params["media_type"], "media_shares")

    def test_direct_pending_requests_preview_uses_current_preview_endpoint(self):
        client = self.build_client()
        response = {
            "pending_requests_total": 1,
            "unread_pending_requests": 1,
            "status": "ok",
        }

        with mock.patch.object(client, "private_request", return_value=response) as private:
            result = client.direct_pending_requests_preview()

        self.assertEqual(result, response)
        private.assert_called_once_with(
            "direct_v2/async_get_pending_requests_preview/",
            params={"pending_inbox_filters": "[]"},
        )

    def test_direct_has_interop_upgraded_returns_boolean_state(self):
        client = self.build_client()

        with mock.patch.object(
            client,
            "private_request",
            return_value={"has_interop_upgraded": False, "status": "ok"},
        ) as private:
            result = client.direct_has_interop_upgraded()

        self.assertFalse(result)
        private.assert_called_once_with("direct_v2/has_interop_upgraded/")

    def test_direct_search_gen_ai_bots_returns_user_results(self):
        client = self.build_client()
        response = {
            "user_search_results": [
                {
                    "pk": 64528677628,
                    "username": "meta_ai",
                    "full_name": "Meta AI",
                    "profile_pic_url": "https://example.com/meta.jpg",
                }
            ],
            "status": "ok",
        }

        with mock.patch.object(client, "private_request", return_value=response) as private:
            result = client.direct_search_gen_ai_bots(amount=5)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].username, "meta_ai")
        private.assert_called_once_with(
            "direct_v2/search_gen_ai_bots/",
            params={"num_ai_bots": "5"},
        )

    def test_direct_channels_uses_authenticated_user_by_default(self):
        client = self.build_client()

        with mock.patch.object(
            client,
            "private_request",
            return_value={"all_channels_list": [{"thread_id": "123"}], "status": "ok"},
        ) as private:
            result = client.direct_channels()

        self.assertEqual(result, [{"thread_id": "123"}])
        private.assert_called_once_with(
            "direct_v2/get_all_channels/",
            params={"user_id": "1", "thread_subtypes": "[29]"},
        )

    def test_direct_set_e2ee_eligibility_posts_unsigned_value(self):
        client = self.build_client()
        client.uuid = "uuid-1"

        with mock.patch.object(client, "private_request", return_value={"status": "ok"}) as private:
            result = client.direct_set_e2ee_eligibility(4)

        self.assertTrue(result)
        private.assert_called_once_with(
            "direct_v2/set_e2ee_eligibility/",
            data={"_uuid": "uuid-1", "e2ee_eligibility": "4"},
            with_signature=False,
        )

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

    def test_direct_media_share_posts_thread_ids(self):
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
            client.direct_media_share("123", thread_ids=[340282366841710300949128149448121770626])

        private.assert_called_once_with(
            "direct_v2/threads/broadcast/media_share/",
            params={"media_type": "photo"},
            data=mock.ANY,
            with_signature=False,
        )
        data = private.call_args.kwargs["data"]
        self.assertNotIn("recipient_users", data)
        self.assertEqual(json.loads(data["thread_ids"]), [340282366841710300949128149448121770626])
        self.assertEqual(data["client_context"], "mutation-token")
        self.assertEqual(data["media_id"], "123_1")

    def test_direct_media_share_rejects_user_ids_and_thread_ids_together(self):
        client = self.build_client()
        client.uuid = "uuid-1"
        client.android_device_id = "android-device"

        with self.assertRaises(AssertionError):
            client.direct_media_share("123", user_ids=[42], thread_ids=[123])

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

    def test_messenger_rupload_headers_merges_common_optional_and_extra_headers(self):
        client = self.build_client()
        client.authorization_data = {"ds_user_id": "123", "sessionid": "raw-session"}
        client.private.headers["Authorization"] = "Bearer token"
        client.private.headers["IG-U-RUR"] = "rur-token"
        client.private.headers["X-MID"] = "mid-token"

        headers = client._messenger_rupload_headers({"audio_type": "FILE_ATTACHMENT"})

        self.assertEqual(headers["authorization"], "Bearer token")
        self.assertEqual(headers["ig-intended-user-id"], "123")
        self.assertEqual(headers["ig-u-ds-user-id"], "123")
        self.assertEqual(headers["accept-encoding"], "gzip")
        self.assertEqual(headers["accept-language"], "en-US")
        self.assertEqual(headers["priority"], "u=6, i")
        self.assertEqual(headers["user-agent"], client.user_agent)
        self.assertEqual(headers["audio_type"], "FILE_ATTACHMENT")
        self.assertEqual(headers["ig-u-rur"], "rur-token")
        self.assertEqual(headers["x-mid"], "mid-token")

    def test_video_rupload_delegates_base_headers_to_helper(self):
        client = self.build_client()
        session = self.fake_rupload_session(media_id=987654321)

        with (
            mock.patch("requests.Session", return_value=session),
            mock.patch.object(
                client, "_messenger_rupload_headers", return_value={"authorization": "Bearer token"}
            ) as headers,
        ):
            media_id = client._video_rupload(b"video-bytes", "entity-name", "waterfall-id")

        self.assertEqual(media_id, 987654321)
        headers.assert_called_once_with(
            {
                "video_type": "FILE_ATTACHMENT",
                "segment-start-offset": "0",
                "segment-type": "3",
                "ephemeral_media_view_mode": "2",
                "ig_raven_metadata": "{}",
                "x_fb_video_waterfall_id": "waterfall-id",
            }
        )

    def test_voice_rupload_delegates_base_headers_to_helper(self):
        client = self.build_client()
        session = self.fake_rupload_session(media_id=987654321)

        with (
            mock.patch("requests.Session", return_value=session),
            mock.patch.object(
                client, "_messenger_rupload_headers", return_value={"authorization": "Bearer token"}
            ) as headers,
        ):
            media_id = client._voice_rupload(b"voice-bytes", "1234567", -99)

        self.assertEqual(media_id, 987654321)
        headers.assert_called_once_with({"audio_type": "FILE_ATTACHMENT"})
