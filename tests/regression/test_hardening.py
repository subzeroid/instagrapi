from instagrapi.exceptions import (
    AccountContactPointRequired,
    AccountEditError,
    BadPassword,
    DirectMessageRequestsDisabled,
)
from tests.helpers import *


class HardeningRegressionTestCase(unittest.TestCase):
    """Hardening fixes for malformed / edge-case IG responses:
    extract_story_v1 fallbacks, _send_private_request 401/404 handling,
    and hashtag-chunk malformed-node skipping."""

    # --- extract_story_v1 fallbacks ---

    @staticmethod
    def _minimal_story_payload(**overrides):
        payload = {
            "pk": "3613500067578544892",
            "id": "3613500067578544892_25025320",
            "code": "Cabc123",
            "taken_at": 1710000000,
            "media_type": 1,
            "user": {
                "pk": "25025320",
                "username": "example",
                "profile_pic_url": "https://example.com/profile.jpg",
            },
        }
        payload.update(overrides)
        return payload

    def test_extract_story_v1_falls_back_to_codec_when_code_missing(self):
        payload = self._minimal_story_payload()
        del payload["code"]

        story = extract_story_v1(payload)

        # InstagramIdCodec.encode("3613500067578544892") is deterministic.
        from instagrapi.utils import InstagramIdCodec

        self.assertEqual(story.code, InstagramIdCodec.encode("3613500067578544892"))

    def test_extract_story_v1_falls_back_to_device_timestamp_when_taken_at_missing(
        self,
    ):
        payload = self._minimal_story_payload()
        del payload["taken_at"]
        payload["device_timestamp"] = 1710000000

        story = extract_story_v1(payload)

        self.assertEqual(int(story.taken_at.timestamp()), 1710000000)

    def test_extract_story_v1_falls_back_to_taken_at_timestamp_when_taken_at_missing(
        self,
    ):
        payload = self._minimal_story_payload()
        del payload["taken_at"]
        payload["taken_at_timestamp"] = 1710000000

        story = extract_story_v1(payload)

        self.assertEqual(int(story.taken_at.timestamp()), 1710000000)

    # --- _send_private_request: 401 / 404 b"Not Found" ---

    def _make_http_error_response(self, status_code, content=b"", json_body=None):
        response = Mock()
        response.status_code = status_code
        response.content = content
        response.headers = {}
        response.url = "https://i.instagram.com/api/v1/test/"
        response.text = content.decode("utf-8", errors="replace") if content else ""
        response.request = Mock(method="GET")
        if json_body is not None:
            response.json.return_value = json_body
        else:
            response.json.side_effect = JSONDecodeError("", "", 0)
        error = requests.HTTPError(response=response)
        response.raise_for_status.side_effect = error
        return response

    def _make_json_response(self, json_body, status_code=200):
        response = Mock()
        response.status_code = status_code
        response.content = json.dumps(json_body).encode()
        response.headers = {}
        response.url = "https://i.instagram.com/api/v1/test/"
        response.text = response.content.decode("utf-8")
        response.request = Mock(method="POST")
        response.json.return_value = json_body
        response.raise_for_status.return_value = None
        return response

    def _build_private_client(self):
        client = Client()
        client.authorization_data = {"ds_user_id": "1"}
        client.last_response = None
        return client

    def test_send_private_request_raises_unauthorized_on_401(self):
        client = self._build_private_client()
        response = self._make_http_error_response(401, content=b"unauthorized")

        with mock.patch.object(client.private, "get", return_value=response):
            with self.assertRaises(ClientUnauthorizedError):
                client._send_private_request("test/")

    def test_send_private_request_preserves_bad_password_message_with_login_context_hint(self):
        client = self._build_private_client()
        raw_message = "The password you entered is incorrect. Please try again."
        response = self._make_http_error_response(
            400,
            json_body={
                "message": raw_message,
                "status": "fail",
                "error_type": "bad_password",
                "exception_name": "UserInvalidCredentials",
            },
        )

        with mock.patch.object(client.private, "post", return_value=response):
            with self.assertRaises(BadPassword) as cm:
                client._send_private_request("accounts/login/", data={"username": "example"}, login=True)

        self.assertTrue(cm.exception.message.startswith(raw_message))
        self.assertIn("proxy/IP", cm.exception.message)
        self.assertIn("device fingerprint", cm.exception.message)
        self.assertNotIn("change your IP", cm.exception.message)
        self.assertNotIn("blacklist", cm.exception.message)

    def test_send_private_request_promotes_404_not_found_body_to_challenge(self):
        client = self._build_private_client()
        response = self._make_http_error_response(404, content=b"Not Found")

        with mock.patch.object(client.private, "get", return_value=response):
            with self.assertRaises(ChallengeRequired):
                client._send_private_request("media/123/comments/")

    def test_send_private_request_keeps_regular_404_as_not_found(self):
        from instagrapi.exceptions import ClientNotFoundError

        client = self._build_private_client()
        # Different body (not the exact "Not Found" sentinel) → standard
        # ClientNotFoundError, not promoted to ChallengeRequired.
        response = self._make_http_error_response(
            404,
            content=b'{"message":"endpoint not found"}',
            json_body={"message": "endpoint not found"},
        )

        with mock.patch.object(client.private, "get", return_value=response):
            with self.assertRaises(ClientNotFoundError):
                client._send_private_request("nonexistent/")

    def test_send_private_request_ignores_non_json_body_on_http_error(self):
        from instagrapi.exceptions import ClientNotFoundError

        client = self._build_private_client()
        response = self._make_http_error_response(404, content=b"<html>not json</html>")
        response.json.side_effect = ValueError("bad json")

        with mock.patch.object(client.private, "get", return_value=response):
            with self.assertRaises(ClientNotFoundError):
                client._send_private_request("nonexistent/")

    def test_send_private_request_promotes_direct_message_requests_disabled_http_error(self):
        client = self._build_private_client()
        payload = {
            "message": "You can't message this account unless they follow you.",
            "status": "fail",
        }
        response = self._make_http_error_response(
            400,
            content=json.dumps(payload).encode(),
            json_body=payload,
        )

        with mock.patch.object(client.private, "post", return_value=response):
            with self.assertRaises(DirectMessageRequestsDisabled) as cm:
                client._send_private_request("direct_v2/threads/broadcast/text/", data={"text": "hi"})

        self.assertEqual(cm.exception.message, payload["message"])
        self.assertEqual(cm.exception.status, "fail")

    def test_send_private_request_promotes_account_edit_contact_point_required_http_error(self):
        client = self._build_private_client()
        payload = {
            "message": {"errors": ["You need an email or confirmed phone number."]},
            "status": "fail",
        }
        response = self._make_http_error_response(
            400,
            content=json.dumps(payload).encode(),
            json_body=payload,
        )

        with mock.patch.object(client.private, "post", return_value=response):
            with self.assertRaises(AccountContactPointRequired) as cm:
                client._send_private_request("accounts/edit_profile/", data={"external_url": ""})

        self.assertEqual(cm.exception.message, payload["message"])
        self.assertEqual(cm.exception.status, "fail")

    def test_send_private_request_promotes_account_edit_contact_point_required_status_fail(self):
        client = self._build_private_client()
        payload = {
            "message": {"errors": ["You need an email or confirmed phone number."]},
            "status": "fail",
        }
        response = self._make_json_response(payload)

        with mock.patch.object(client.private, "post", return_value=response):
            with self.assertRaises(AccountContactPointRequired) as cm:
                client._send_private_request("accounts/edit_profile/", data={"external_url": ""})

        self.assertEqual(cm.exception.message, payload["message"])
        self.assertEqual(cm.exception.status, "fail")

    def test_send_private_request_promotes_account_edit_unknown_server_error(self):
        client = self._build_private_client()
        payload = {
            "message": "Unknown Server Error.",
            "status": "fail",
        }
        response = self._make_http_error_response(
            400,
            content=json.dumps(payload).encode(),
            json_body=payload,
        )

        with mock.patch.object(client.private, "post", return_value=response):
            with self.assertRaises(AccountEditError) as cm:
                client._send_private_request("accounts/edit_profile/", data={"external_url": ""})

        self.assertEqual(cm.exception.message, payload["message"])
        self.assertEqual(cm.exception.status, "fail")

    def test_send_private_request_promotes_direct_message_requests_disabled_status_fail(self):
        client = self._build_private_client()
        payload = {
            "message": "This account can't receive your message because they don't allow new message requests from everyone.",
            "status": "fail",
        }
        response = self._make_json_response(payload)

        with mock.patch.object(client.private, "post", return_value=response):
            with self.assertRaises(DirectMessageRequestsDisabled) as cm:
                client._send_private_request("direct_v2/threads/broadcast/text/", data={"text": "hi"})

        self.assertEqual(cm.exception.message, payload["message"])
        self.assertEqual(cm.exception.status, "fail")

    def test_private_request_retries_chunked_encoding_error_once(self):
        client = self._build_private_client()
        client.request_timeout = 0
        response = self._make_json_response({"status": "ok"})

        with mock.patch.object(
            client.private,
            "post",
            side_effect=[
                requests.exceptions.ChunkedEncodingError(
                    "Connection broken: IncompleteRead(207264 bytes read, 168584 more expected)"
                ),
                response,
            ],
        ) as private_post:
            with mock.patch("instagrapi.mixins.private.time.sleep") as sleep:
                result = client.private_request("test/", data={"_uuid": client.uuid}, with_signature=False)

        self.assertEqual(result, {"status": "ok"})
        self.assertEqual(private_post.call_count, 2)
        self.assertEqual(sleep.call_args_list.count(mock.call(2)), 1)

    # --- hashtag chunk: skip malformed nodes ---

    def test_hashtag_medias_top_v1_chunk_skips_malformed_nodes(self):
        client = Client()
        good_node = {
            "media": {
                "pk": "1",
                "id": "1_2",
                "code": "abc",
                "taken_at": 1710000000,
                "media_type": 1,
                "user": {
                    "pk": "2",
                    "username": "example",
                    "profile_pic_url": "https://example.com/profile.jpg",
                },
                "image_versions2": {
                    "candidates": [
                        {
                            "url": "https://example.com/x.jpg",
                            "width": 100,
                            "height": 100,
                        }
                    ]
                },
            }
        }
        # Missing "media" key → KeyError when extractor accesses node["media"].
        malformed_node = {"unexpected_shape": True}

        client.private_request = lambda *a, **kw: {
            "sections": [{"layout_content": {"medias": [malformed_node, good_node]}}],
            "more_available": False,
            "next_max_id": None,
        }

        medias, next_max_id = client.hashtag_medias_v1_chunk("example", 0, "top")

        # Bad node skipped, good one survives — chunk doesn't lose the page.
        self.assertEqual(len(medias), 1)
        self.assertEqual(medias[0].pk, "1")
        self.assertIsNone(next_max_id)

    def test_location_medias_v1_paginates_until_amount(self):
        client = Client()

        client.location_medias_v1_chunk = Mock(
            side_effect=[
                (["m1", "m2"], "cursor-2"),
                (["m3", "m4"], "cursor-3"),
                (["m5"], None),
            ]
        )

        medias = client.location_medias_v1(123, amount=3, tab_key="recent")

        self.assertEqual(medias, ["m1", "m2", "m3"])
        self.assertEqual(client.location_medias_v1_chunk.call_count, 2)
        self.assertEqual(
            client.location_medias_v1_chunk.call_args_list[0].args,
            (123, 3, "recent", None),
        )
        self.assertEqual(
            client.location_medias_v1_chunk.call_args_list[1].args,
            (123, 3, "recent", "cursor-2"),
        )

    def test_location_medias_v1_amount_zero_paginates_until_cursor_exhausted(self):
        client = Client()

        client.location_medias_v1_chunk = Mock(
            side_effect=[
                (["m1"], "cursor-2"),
                (["m2"], None),
            ]
        )

        medias = client.location_medias_v1(123, amount=0, tab_key="recent")

        self.assertEqual(medias, ["m1", "m2"])
        self.assertEqual(client.location_medias_v1_chunk.call_count, 2)

    def test_location_medias_v1_chunk_stops_when_next_max_id_is_missing(self):
        client = Client()
        client.private_request = Mock(
            return_value={
                "next_page": 335,
                "next_media_ids": [],
                "next_max_id": None,
                "sections": [],
            }
        )

        medias, next_max_id = client.location_medias_v1_chunk(123, tab_key="recent")

        self.assertEqual(medias, [])
        self.assertIsNone(next_max_id)
