"""Native Instagram reposts use media notes, not a second media upload."""

import unittest
from unittest.mock import patch

from instagrapi import Client
from instagrapi.exceptions import ClientError


class MediaRepostTestCase(unittest.TestCase):
    def setUp(self):
        self.client = Client()
        self.client.authorization_data = {"ds_user_id": "1"}
        self.client.uuid = "uuid"

    def test_repost_creates_the_media_note_used_by_the_native_button(self):
        receipt = {"id": "987", "media_id": "123", "audience": 7, "note_style": 13, "status": "ok"}
        with patch.object(self.client, "private_request", return_value=receipt) as request:
            self.assertEqual(self.client.media_repost("123_456", text="Worth watching"), receipt)
        request.assert_called_once_with(
            "media/create_note/v2/",
            data={
                "inventory_source": "recommended_clips_chaining_model",
                "media_client_position": "0",
                "media_id": "123_456",
                "note_style": "13",
                "carousel_index": "-1",
                "text": "Worth watching",
                "_uuid": "uuid",
                "audience": "7",
                "event_source": "ufi",
                "container_module": "clips_viewer_clips_tab",
            },
            with_signature=False,
        )

    def test_repost_defaults_to_no_comment_and_passes_surface_context(self):
        with patch.object(self.client, "private_request", return_value={"status": "ok"}) as request:
            self.client.media_repost("123_456", extra_data={"ranking_info_token": "context"})
        self.assertEqual(request.call_args.kwargs["data"]["text"], "")
        self.assertEqual(request.call_args.kwargs["data"]["ranking_info_token"], "context")

    def test_unrepost_deletes_the_repost_receipt_id_not_the_media(self):
        with patch.object(self.client, "private_request", return_value={"status": "ok"}) as request:
            self.assertTrue(self.client.media_unrepost("987", extra_data={"ranking_info_token": "context"}))
        request.assert_called_once_with(
            "media/delete_note/",
            data={
                "inventory_source": "recommended_clips_chaining_model",
                "carousel_index": "-1",
                "_uuid": "uuid",
                "event_source": "ufi",
                "container_module": "clips_viewer_clips_tab",
                "note_id": "987",
                "ranking_info_token": "context",
            },
            with_signature=False,
        )

    def test_repost_propagates_instagram_errors_without_repeating_a_mutation(self):
        with patch.object(self.client, "private_request", side_effect=ClientError("Rejected")) as request:
            with self.assertRaises(ClientError):
                self.client.media_repost("123_456")
        self.assertEqual(request.call_count, 1)

    def test_unrepost_does_not_report_a_failed_response_as_success(self):
        with patch.object(self.client, "private_request", return_value={"status": "fail"}):
            self.assertFalse(self.client.media_unrepost("987"))

    def test_repost_requires_login_before_sending_a_request(self):
        self.client.authorization_data = {}
        with patch.object(self.client, "private_request") as request:
            with self.assertRaises(AssertionError):
                self.client.media_repost("123_456")
        request.assert_not_called()
