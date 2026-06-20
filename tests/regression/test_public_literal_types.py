import unittest
from inspect import signature
from pathlib import Path
from typing import get_args

from instagrapi.mixins.account import ProfessionalAccountType
from instagrapi.mixins.clip import UploadClipMixin
from instagrapi.mixins.direct import BOX, SELECTED_FILTER, SEND_ATTRIBUTE_MEDIA, DirectMediaType, DirectMixin
from instagrapi.mixins.hashtag import HashtagTab
from instagrapi.mixins.insights import DATA_ORDERING, POST_TYPE, TIME_FRAME, InsightsMixin
from instagrapi.mixins.location import LocationTab
from instagrapi.mixins.note import NoteAudience
from instagrapi.mixins.notification import NotificationContentType
from instagrapi.mixins.public import PublicTransport
from instagrapi.mixins.track import MUSIC_PRODUCT, TrackMixin
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
EXPECTED_DIRECT_MEDIA_SEND_ATTRIBUTES = {
    "feed_timeline",
    "feed_contextual_chain",
    "feed_short_url",
    "feed_contextual_self_profile",
    "feed_contextual_profile",
}
EXPECTED_MUSIC_PRODUCTS = {
    "feed_post",
    "music_in_feed",
    "story_camera_clips_v2",
}


class PublicLiteralTypesRegressionTestCase(unittest.TestCase):
    def test_public_literal_aliases_expose_supported_values(self):
        self.assertEqual(set(get_args(ProfessionalAccountType)), {2, 3})
        self.assertEqual(set(get_args(NoteAudience)), {0, 1})
        self.assertEqual(set(get_args(HashtagTab)), {"top", "recent", "clips"})
        self.assertEqual(set(get_args(LocationTab)), {"ranked", "recent"})
        self.assertEqual(set(get_args(NotificationContentType)), EXPECTED_NOTIFICATION_CONTENT_TYPES)
        self.assertEqual(set(get_args(PublicTransport)), {"requests", "curl"})
        self.assertEqual(set(get_args(SEND_ATTRIBUTE_MEDIA)), EXPECTED_DIRECT_MEDIA_SEND_ATTRIBUTES)
        self.assertEqual(set(get_args(DirectMediaType)), {"photo", "video"})
        self.assertEqual(set(get_args(MUSIC_PRODUCT)), EXPECTED_MUSIC_PRODUCTS)
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

    def test_direct_media_share_uses_public_send_attribute_literal(self):
        direct_media_share = signature(DirectMixin.direct_media_share)

        self.assertEqual(direct_media_share.parameters["send_attribute"].annotation, SEND_ATTRIBUTE_MEDIA)

    def test_direct_media_methods_use_public_media_type_literal(self):
        direct_send_file = signature(DirectMixin.direct_send_file)
        direct_media_share = signature(DirectMixin.direct_media_share)

        self.assertEqual(direct_send_file.parameters["content_type"].annotation, DirectMediaType)
        self.assertEqual(direct_media_share.parameters["media_type"].annotation, DirectMediaType)

    def test_direct_usage_guide_documents_public_media_type_literal(self):
        docs = Path("docs/usage-guide/direct.md").read_text()

        self.assertIn('media_type: DirectMediaType = "photo"', docs)
        self.assertIn("### Option types", docs)
        self.assertIn('DirectMediaType = Literal["photo", "video"]', docs)
        self.assertIn(
            '| `DirectMediaType` | `"photo"`, `"video"` | `direct_send_file(content_type=...)`, '
            "`direct_media_share(media_type=...)` |",
            docs,
        )

    def test_insights_media_feed_all_uses_public_literal_aliases(self):
        insights_media_feed_all = signature(InsightsMixin.insights_media_feed_all)

        self.assertEqual(insights_media_feed_all.parameters["post_type"].annotation, POST_TYPE)
        self.assertEqual(insights_media_feed_all.parameters["time_frame"].annotation, TIME_FRAME)
        self.assertEqual(insights_media_feed_all.parameters["data_ordering"].annotation, DATA_ORDERING)

    def test_insights_usage_guide_documents_public_literal_aliases(self):
        docs = Path("docs/usage-guide/insight.md").read_text()

        self.assertIn(
            'insights_media_feed_all(post_type: POST_TYPE = "ALL", time_frame: TIME_FRAME = "TWO_YEARS", '
            'data_ordering: DATA_ORDERING = "REACH_COUNT"',
            docs,
        )
        self.assertNotIn(
            'post_type: str = "ALL", time_frame: str = "TWO_YEARS", data_ordering: str = "REACH_COUNT"',
            docs,
        )

    def test_track_music_methods_use_public_product_literal_alias(self):
        for method_name in (
            "music_trending",
            "music_top_trends",
            "music_search_v2",
            "music_keyword_search",
            "music_clips_audio_browser",
        ):
            with self.subTest(method_name=method_name):
                method = signature(getattr(TrackMixin, method_name))

                self.assertEqual(method.parameters["product"].annotation, MUSIC_PRODUCT)

    def test_clip_music_methods_use_public_product_literal_alias(self):
        for method_name in ("clip_music_extra_data", "clip_upload_with_music"):
            with self.subTest(method_name=method_name):
                method = signature(getattr(UploadClipMixin, method_name))

                self.assertEqual(method.parameters["product"].annotation, MUSIC_PRODUCT)

    def test_track_usage_guide_documents_public_product_literal_alias(self):
        docs = Path("docs/usage-guide/track.md").read_text()

        self.assertIn('music_trending(product: MUSIC_PRODUCT = "feed_post")', docs)
        self.assertIn('music_top_trends(product: MUSIC_PRODUCT = "music_in_feed", page_size: int = 15)', docs)
        self.assertIn('music_clips_audio_browser(product: MUSIC_PRODUCT = "story_camera_clips_v2"', docs)
        self.assertNotIn('product: str = "feed_post"', docs)
        self.assertNotIn('product: str = "music_in_feed"', docs)
        self.assertNotIn('product: str = "story_camera_clips_v2"', docs)

    def test_media_usage_guide_documents_public_music_product_literal_alias(self):
        docs = Path("docs/usage-guide/media.md").read_text()

        self.assertIn(
            'clip_music_extra_data(track: Track or dict, product: MUSIC_PRODUCT = "story_camera_clips_v2"',
            docs,
        )
        self.assertIn(
            "clip_upload_with_music(path: Path, caption: str, track: Track or dict, thumbnail: Path = None, "
            'product: MUSIC_PRODUCT = "story_camera_clips_v2"',
            docs,
        )
