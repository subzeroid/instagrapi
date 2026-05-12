from tests.helpers import *


class ExtractorsRegressionTestCase(unittest.TestCase):
    def test_extract_resource_v1_handles_empty_candidates(self):
        resource = extract_resource_v1({"pk": "1", "media_type": 1, "image_versions2": {"candidates": []}})
        self.assertIsNone(resource.thumbnail_url)
        self.assertEqual(resource.pk, "1")


class DirectExtractorRegressionTestCase(unittest.TestCase):
    def test_xma_share_without_target_url_is_ignored(self):
        message = extract_direct_message(
            {
                "item_id": "1",
                "user_id": "2",
                "timestamp": 1761953663000000,
                "item_type": "xma_media_share",
                "text": "",
                "xma_media_share": [
                    {
                        "header_icon_url": "",
                        "title_text": "Shared content",
                    }
                ],
            }
        )

        self.assertIsNone(message.xma_share)

    def test_xma_share_accepts_empty_header_icon_url(self):
        message = extract_direct_message(
            {
                "item_id": "1",
                "user_id": "2",
                "timestamp": 1761953663000000,
                "item_type": "xma_media_share",
                "text": "",
                "xma_media_share": [
                    {
                        "target_url": "https://example.com/reel",
                        "header_icon_url": "",
                        "title_text": "Shared content",
                    }
                ],
            }
        )

        self.assertIsNotNone(message.xma_share)
        self.assertEqual(str(message.xma_share.video_url), "https://example.com/reel")
        self.assertIsNone(message.xma_share.header_icon_url)

    def test_generic_xma_collects_multiple_items(self):
        message = extract_direct_message(
            {
                "item_id": "1",
                "user_id": "2",
                "timestamp": 1761953663000000,
                "item_type": "generic_xma",
                "text": "",
                "generic_xma": [
                    {
                        "target_url": "https://example.com/first",
                        "title_text": "First item",
                    },
                    {
                        "title_text": "Missing target url should be ignored",
                    },
                    {
                        "target_url": "https://example.com/second",
                        "title_text": "Second item",
                    },
                ],
            }
        )

        self.assertIsNotNone(message.generic_xma)
        self.assertEqual(len(message.generic_xma), 2)
        self.assertEqual(str(message.generic_xma[0].video_url), "https://example.com/first")
        self.assertEqual(str(message.generic_xma[1].video_url), "https://example.com/second")

    def test_reply_visual_media_timestamp_uses_microseconds(self):
        message = extract_direct_message(
            {
                "item_id": "1",
                "user_id": "2",
                "timestamp": 1761953663000000,
                "item_type": "text",
                "text": "reply wrapper",
                "replied_to_message": {
                    "item_id": "3",
                    "user_id": "4",
                    "timestamp": 1761953663000000,
                    "item_type": "visual_media",
                    "visual_media": {
                        "view_mode": "permanent",
                        "seen_user_ids": [],
                        "seen_count": 0,
                        "media": {
                            "media_type": 1,
                            "expiring_media_action_summary": {
                                "type": "replay",
                                "timestamp": 1761953663000000,
                                "count": 1,
                            },
                        },
                    },
                },
            }
        )

        self.assertEqual(message.reply.id, "3")
        self.assertEqual(
            message.reply.visual_media.media.expiring_media_action_summary.timestamp,
            datetime.fromtimestamp(1761953663000000 // 1_000_000),
        )

    def test_reply_message_accepts_string_microsecond_timestamp(self):
        message = extract_direct_message(
            {
                "item_id": "1",
                "user_id": "2",
                "timestamp": 1761953663000000,
                "item_type": "text",
                "text": "reply wrapper",
                "replied_to_message": {
                    "item_id": "3",
                    "user_id": "4",
                    "timestamp": "1761953663000000",
                    "item_type": "text",
                    "text": "reply",
                },
            }
        )

        self.assertEqual(
            message.reply.timestamp,
            datetime.fromtimestamp(1761953663000000 // 1_000_000),
        )

    def test_direct_thread_defaults_missing_is_close_friend_thread(self):
        thread = extract_direct_thread(
            {
                "thread_v2_id": "1",
                "thread_id": "2",
                "items": [],
                "users": [
                    {
                        "pk": "3",
                        "username": "example",
                        "profile_pic_url": "https://example.com/pic.jpg",
                    }
                ],
                "left_users": [],
                "admin_user_ids": [],
                "last_activity_at": 1761953663000000,
                "muted": False,
                "named": False,
                "canonical": False,
                "pending": False,
                "archived": False,
                "thread_type": "private",
                "thread_title": "",
                "folder": 0,
                "vc_muted": False,
                "is_group": False,
                "mentions_muted": False,
                "approval_required_for_new_members": False,
                "input_mode": 0,
                "business_thread_folder": 0,
                "read_state": 0,
                "assigned_admin_id": 0,
                "shh_mode_enabled": False,
                "last_seen_at": {},
            }
        )

        self.assertFalse(thread.is_close_friend_thread)

    def test_direct_thread_accepts_string_last_activity_at(self):
        thread = extract_direct_thread(
            {
                "thread_v2_id": "1",
                "thread_id": "2",
                "items": [],
                "users": [
                    {
                        "pk": "3",
                        "username": "example",
                        "profile_pic_url": "https://example.com/pic.jpg",
                    }
                ],
                "left_users": [],
                "admin_user_ids": [],
                "last_activity_at": "1761953663000000",
                "muted": False,
                "named": False,
                "canonical": False,
                "pending": False,
                "archived": False,
                "thread_type": "private",
                "thread_title": "",
                "folder": 0,
                "vc_muted": False,
                "is_group": False,
                "mentions_muted": False,
                "approval_required_for_new_members": False,
                "input_mode": 0,
                "business_thread_folder": 0,
                "read_state": 0,
                "assigned_admin_id": 0,
                "shh_mode_enabled": False,
                "last_seen_at": {},
            }
        )

        self.assertEqual(
            thread.last_activity_at,
            datetime.fromtimestamp(1761953663000000 // 1_000_000),
        )

    def test_direct_thread_parses_when_optional_fields_missing(self):
        """IG omits business_thread_folder / read_state / assigned_admin_id /
        shh_mode_enabled in older inbox shapes and Threads-app threads.
        Parser must not raise ValidationError on those payloads."""
        thread = extract_direct_thread(
            {
                "thread_v2_id": "1",
                "thread_id": "2",
                "items": [],
                "users": [
                    {
                        "pk": "3",
                        "username": "example",
                        "profile_pic_url": "https://example.com/pic.jpg",
                    }
                ],
                "left_users": [],
                "admin_user_ids": [],
                "last_activity_at": 1761953663000000,
                "muted": False,
                "named": False,
                "canonical": False,
                "pending": False,
                "archived": False,
                "thread_type": "private",
                "thread_title": "",
                "folder": 0,
                "vc_muted": False,
                "is_group": False,
                "mentions_muted": False,
                "approval_required_for_new_members": False,
                "input_mode": 0,
                "last_seen_at": {},
            }
        )

        self.assertIsNone(thread.business_thread_folder)
        self.assertIsNone(thread.read_state)
        self.assertIsNone(thread.assigned_admin_id)
        self.assertIsNone(thread.shh_mode_enabled)
