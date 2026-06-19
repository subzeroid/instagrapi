import unittest
from inspect import signature
from typing import get_args

from instagrapi.mixins.account import ProfessionalAccountType
from instagrapi.mixins.direct import BOX, SELECTED_FILTER, DirectMixin
from instagrapi.mixins.hashtag import HashtagTab
from instagrapi.mixins.location import LocationTab
from instagrapi.mixins.note import NoteAudience
from instagrapi.mixins.notification import NotificationContentType
from instagrapi.mixins.public import PublicTransport
from instagrapi.types import StoryResizeMode

EXPECTED_NOTIFICATION_CONTENT_TYPES = {
    "mute_all",
    "likes",
    "like_and_comment_on_photo_user_tagged",
    "user_tagged",
    "comments",
    "comment_likes",
    "first_post",
    "new_follower",
    "follow_request_accepted",
    "connection_notification",
    "tagged_in_bio",
    "pending_direct_share",
    "direct_share_activity",
    "direct_group_requests",
    "video_call",
    "rooms",
    "live_broadcast",
    "felix_upload_result",
    "view_count",
    "fundraiser_creator",
    "fundraiser_supporter",
    "notification_reminders",
    "announcements",
    "report_updated",
    "login_notification",
}


class PublicLiteralTypesRegressionTestCase(unittest.TestCase):
    def test_public_literal_aliases_expose_supported_values(self):
        self.assertEqual(set(get_args(ProfessionalAccountType)), {2, 3})
        self.assertEqual(set(get_args(NoteAudience)), {0, 1})
        self.assertEqual(set(get_args(HashtagTab)), {"top", "recent", "clips"})
        self.assertEqual(set(get_args(LocationTab)), {"ranked", "recent"})
        self.assertEqual(set(get_args(NotificationContentType)), EXPECTED_NOTIFICATION_CONTENT_TYPES)
        self.assertEqual(set(get_args(PublicTransport)), {"requests", "curl"})
        self.assertEqual(set(get_args(StoryResizeMode)), {"fill", "fit"})

    def test_direct_thread_filter_literals_remain_optional(self):
        self.assertEqual(set(get_args(SELECTED_FILTER)), {"flagged", "unread"})
        self.assertEqual(set(get_args(BOX)), {"general", "primary"})

        direct_threads = signature(DirectMixin.direct_threads)
        self.assertIsNone(direct_threads.parameters["selected_filter"].default)
        self.assertIsNone(direct_threads.parameters["box"].default)

        direct_threads_chunk = signature(DirectMixin.direct_threads_chunk)
        self.assertIsNone(direct_threads_chunk.parameters["selected_filter"].default)
        self.assertIsNone(direct_threads_chunk.parameters["box"].default)
