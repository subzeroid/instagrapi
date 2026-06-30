import json

from instagrapi.extractors import extract_media_gql, extract_media_v1
from tests.helpers import *


class MediaInfoV2RegressionTestCase(unittest.TestCase):
    def _media_or_ad_payload(self):
        return {
            "pk": "1",
            "id": "1_2",
            "code": "abc",
            "taken_at": 1710000000,
            "media_type": 1,
            "usertags": None,
            "carousel_media": None,
            "user": {
                "pk": "2",
                "username": "example",
                "profile_pic_url": "https://example.com/profile.jpg",
            },
            "image_versions2": {
                "candidates": [{"url": "https://example.com/x.jpg", "width": 100, "height": 100}],
                "scrubber_spritesheet_info_candidates": {"default": {"video_length": 15.4}},
            },
        }

    def _clips_metadata_payload(self, **overrides):
        payload = {
            "clips_creation_entry_point": "clips",
            "achievements_info": {"num_earned_achievements": None, "show_achievements": False},
            "additional_audio_info": {
                "additional_audio_username": None,
                "audio_reattribution_info": {"should_allow_restore": False},
            },
            "audio_ranking_info": {"best_audio_cluster_id": ""},
            "audio_type": "original_sounds",
            "branded_content_tag_info": {"can_add_tag": True},
            "content_appreciation_info": {"enabled": False},
            "music_canonical_id": "",
        }
        payload.update(overrides)
        return payload

    def test_extract_media_v1_normalizes_video_view_count(self):
        payload = self._media_or_ad_payload()
        payload.update(
            {
                "media_type": 2,
                "product_type": "clips",
                "video_view_count": 1234,
                "video_play_count": 5678,
            }
        )

        media = extract_media_v1(payload)

        self.assertEqual(media.view_count, 1234)
        self.assertEqual(media.play_count, 5678)

    def test_extract_media_v1_normalizes_sponsor_tag_friendship_status(self):
        payload = self._media_or_ad_payload()
        payload["sponsor_tags"] = [
            {
                "sponsor": {
                    "pk": "3",
                    "username": "sponsor",
                    "profile_pic_url": "https://example.com/sponsor.jpg",
                    "friendship_status": {"following": False},
                }
            }
        ]

        media = extract_media_v1(payload)

        self.assertEqual(media.sponsor_tags[0].pk, "3")
        self.assertEqual(media.sponsor_tags[0].friendship_status.user_id, "3")
        self.assertFalse(media.sponsor_tags[0].friendship_status.following)
        self.assertFalse(media.sponsor_tags[0].friendship_status.incoming_request)

    def test_media_info_v2_strips_userid_suffix(self):
        client = Client()
        with mock.patch.object(
            client,
            "private_request",
            return_value={"media_or_ad": self._media_or_ad_payload()},
        ) as private_request:
            media = client.media_info_v2("3613500067578544892_25025320")

        private_request.assert_called_once_with(
            "discover/media_metadata/",
            params={"media_id": "3613500067578544892"},
        )
        self.assertEqual(media.pk, "1")

    def test_media_info_v2_passes_pk_only_unchanged(self):
        client = Client()
        with mock.patch.object(
            client,
            "private_request",
            return_value={"media_or_ad": self._media_or_ad_payload()},
        ) as private_request:
            client.media_info_v2("3613500067578544892")

        params = private_request.call_args.kwargs["params"]
        self.assertEqual(params["media_id"], "3613500067578544892")

    def test_media_info_v2_raises_media_not_found_when_payload_empty(self):
        from instagrapi.exceptions import MediaNotFound

        client = Client()
        client.last_json = {}
        with mock.patch.object(client, "private_request", return_value={}):
            with self.assertRaises(MediaNotFound):
                client.media_info_v2("9_8")

    def test_extract_media_v1_preserves_album_resource_usertags(self):
        payload = self._media_or_ad_payload()
        payload["media_type"] = 8
        payload["carousel_media"] = [
            {
                "pk": "10",
                "id": "10_2",
                "media_type": 1,
                "image_versions2": {
                    "candidates": [{"url": "https://example.com/one.jpg", "width": 100, "height": 100}],
                },
                "usertags": {
                    "in": [
                        {
                            "user": {
                                "pk": "100",
                                "username": "first",
                                "profile_pic_url": "https://example.com/first.jpg",
                            },
                            "position": [0.25, 0.75],
                        }
                    ]
                },
            },
            {
                "pk": "20",
                "id": "20_2",
                "media_type": 1,
                "image_versions2": {
                    "candidates": [{"url": "https://example.com/two.jpg", "width": 100, "height": 100}],
                },
                "usertags": {
                    "in": [
                        {
                            "user": {
                                "pk": "200",
                                "username": "second",
                                "profile_pic_url": "https://example.com/second.jpg",
                            },
                            "position": [0.5, 0.5],
                        }
                    ]
                },
            },
        ]

        media = extract_media_v1(payload)

        self.assertEqual(media.resources[0].usertags[0].user.pk, "100")
        self.assertEqual(media.resources[0].usertags[0].x, 0.25)
        self.assertEqual(media.resources[1].usertags[0].user.pk, "200")
        self.assertEqual(media.resources[1].usertags[0].y, 0.5)

    def test_extract_media_v1_preserves_coauthor_producers(self):
        payload = self._media_or_ad_payload()
        payload["coauthor_producers"] = [
            {
                "id": "100",
                "username": "collab_user",
                "full_name": "Collab User",
                "profile_pic_url": "https://example.com/collab.jpg",
                "is_private": False,
                "is_verified": True,
            }
        ]

        media = extract_media_v1(payload)

        self.assertEqual(len(media.coauthor_producers), 1)
        coauthor = media.coauthor_producers[0]
        self.assertIsInstance(coauthor, UserShort)
        self.assertEqual(coauthor.pk, "100")
        self.assertEqual(coauthor.username, "collab_user")
        self.assertTrue(coauthor.is_verified)

    def test_extract_media_v1_preserves_extended_media_fields(self):
        payload = self._media_or_ad_payload()
        payload.update(
            {
                "caption_is_edited": True,
                "dimensions": {"height": 1916, "width": 1080},
                "has_audio": True,
                "like_and_view_counts_disabled": True,
                "viewer_can_reshare": True,
                "viewer_has_saved": True,
                "is_paid_partnership": True,
                "is_affiliate": True,
                "dash_info": {
                    "is_dash_eligible": False,
                    "video_dash_manifest": None,
                    "number_of_qualities": 0,
                },
                "clips_music_attribution_info": {
                    "artist_name": "example",
                    "song_name": "Original audio",
                    "uses_original_audio": True,
                    "should_mute_audio": False,
                    "should_mute_audio_reason": "",
                    "audio_id": "1192260532058807",
                },
            }
        )

        media = extract_media_v1(payload)

        self.assertTrue(media.caption_is_edited)
        self.assertEqual(media.dimensions.height, 1916)
        self.assertEqual(media.dimensions.width, 1080)
        self.assertTrue(media.has_audio)
        self.assertTrue(media.like_and_view_counts_disabled)
        self.assertTrue(media.viewer_can_reshare)
        self.assertTrue(media.viewer_has_saved)
        self.assertTrue(media.is_paid_partnership)
        self.assertTrue(media.is_affiliate)
        self.assertFalse(media.dash_info.is_dash_eligible)
        self.assertEqual(media.dash_info.number_of_qualities, 0)
        self.assertEqual(media.clips_music_attribution_info.artist_name, "example")
        self.assertTrue(media.clips_music_attribution_info.uses_original_audio)

    def test_extract_media_v1_does_not_default_missing_clips_shared_to_fb_to_false(self):
        payload = self._media_or_ad_payload()
        payload["media_type"] = 2
        payload["product_type"] = "clips"
        payload["clips_metadata"] = self._clips_metadata_payload()

        media = extract_media_v1(payload)

        self.assertIsNone(media.clips_metadata.is_shared_to_fb)
        self.assertIsNone(media.model_dump()["clips_metadata"]["is_shared_to_fb"])

    def test_extract_media_v1_preserves_clips_shared_to_fb_when_present(self):
        for value in (False, True):
            with self.subTest(value=value):
                payload = self._media_or_ad_payload()
                payload["media_type"] = 2
                payload["product_type"] = "clips"
                payload["clips_metadata"] = self._clips_metadata_payload(is_shared_to_fb=value)

                media = extract_media_v1(payload)

                self.assertIs(media.clips_metadata.is_shared_to_fb, value)
                self.assertIs(media.model_dump()["clips_metadata"]["is_shared_to_fb"], value)

    def test_extract_media_gql_preserves_inline_comment_preview(self):
        def comment_node(comment_id, text, user_id, username):
            return {
                "id": comment_id,
                "text": text,
                "created_at": 1710000000,
                "did_report_as_spam": False,
                "owner": {
                    "id": user_id,
                    "username": username,
                    "profile_pic_url": f"https://example.com/{username}.jpg",
                    "is_verified": False,
                },
                "viewer_has_liked": False,
                "edge_liked_by": {"count": 2},
                "is_restricted_pending": False,
                "edge_threaded_comments": {"count": 0, "page_info": {"has_next_page": False}, "edges": []},
            }

        parent = comment_node("c1", "parent", "10", "parent_user")
        reply = comment_node("r1", "reply", "11", "reply_user")
        parent["edge_threaded_comments"] = {
            "count": 1,
            "page_info": {"has_next_page": False, "end_cursor": None},
            "edges": [{"node": reply}],
        }
        hoisted = comment_node("h1", "hoisted", "12", "hoisted_user")
        payload = {
            "__typename": "GraphImage",
            "id": "1",
            "shortcode": "abc",
            "taken_at_timestamp": 1710000000,
            "owner": {
                "id": "2",
                "username": "example",
                "profile_pic_url": "https://example.com/profile.jpg",
            },
            "display_resources": [],
            "edge_media_to_comment": {"count": 1},
            "edge_media_preview_like": {"count": 0},
            "edge_media_to_caption": {"edges": []},
            "edge_media_to_tagged_user": {"edges": []},
            "edge_sidecar_to_children": {"edges": []},
            "edge_media_to_sponsor_user": {"edges": []},
            "edge_media_to_parent_comment": {
                "count": 1,
                "page_info": {"has_next_page": True, "end_cursor": "cursor"},
                "edges": [{"node": parent}],
            },
            "edge_media_to_hoisted_comment": {"edges": [{"node": hoisted}]},
        }

        media = extract_media_gql(payload)

        self.assertEqual(media.comments_preview.count, 1)
        self.assertTrue(media.comments_preview.has_next_page)
        self.assertEqual(media.comments_preview.end_cursor, "cursor")
        comment = media.comments_preview.comments[0]
        self.assertEqual(comment.pk, "c1")
        self.assertEqual(comment.text, "parent")
        self.assertEqual(comment.user.pk, "10")
        self.assertEqual(comment.user.username, "parent_user")
        self.assertEqual(comment.like_count, 2)
        self.assertFalse(comment.has_liked)
        self.assertFalse(comment.is_restricted_pending)
        self.assertEqual(comment.replies_count, 1)
        self.assertEqual(comment.replies[0].pk, "r1")
        self.assertEqual(comment.replies[0].replied_to_comment_id, "c1")
        self.assertEqual(media.hoisted_comments[0].pk, "h1")
        self.assertEqual(media.hoisted_comments[0].text, "hoisted")


class MediaInfoPrivateFirstRegressionTestCase(unittest.TestCase):
    def build_private_client(self):
        client = Client()
        client.authorization_data = {"ds_user_id": "1"}
        client._medias_cache = {}
        return client

    def build_media(self):
        return Media(
            pk="123",
            id="123_456",
            code="abc",
            taken_at=datetime.now(UTC()),
            media_type=1,
            user=UserShort(pk="456", username="example", profile_pic_url="https://example.com/profile.jpg"),
            like_count=0,
            caption_text="",
            usertags=[],
            sponsor_tags=[],
        )

    def test_authorized_media_info_uses_private_before_public(self):
        client = self.build_private_client()
        media = self.build_media()

        with mock.patch.object(client, "media_info_v1", return_value=media) as private_lookup:
            with mock.patch.object(
                client,
                "media_info_gql",
                side_effect=AssertionError("authorized lookup should use private API first"),
            ) as public_lookup:
                result = client.media_info("123", use_cache=False)

        self.assertEqual(result.pk, "123")
        private_lookup.assert_called_once_with("123")
        public_lookup.assert_not_called()

    def test_cookie_session_media_info_uses_private_before_public(self):
        client = Client()
        client.private.cookies.set("sessionid", "1" * 40)
        client._medias_cache = {}
        media = self.build_media()

        with mock.patch.object(client, "media_info_v1", return_value=media) as private_lookup:
            with mock.patch.object(
                client,
                "media_info_gql",
                side_effect=AssertionError("cookie session lookup should use private API first"),
            ) as public_lookup:
                result = client.media_info("123", use_cache=False)

        self.assertEqual(result.pk, "123")
        private_lookup.assert_called_once_with("123")
        public_lookup.assert_not_called()

    def test_authorized_media_info_falls_back_to_public(self):
        client = self.build_private_client()
        media = self.build_media()

        with mock.patch.object(
            client, "media_info_v1", side_effect=ClientError("private lookup failed")
        ) as private_lookup:
            with mock.patch.object(client, "media_info_gql", return_value=media) as public_lookup:
                result = client.media_info("123", use_cache=False)

        self.assertEqual(result.pk, "123")
        private_lookup.assert_called_once_with("123")
        public_lookup.assert_called_once_with("123")

    def test_unauthorized_media_info_keeps_public_first(self):
        client = Client()
        client._medias_cache = {}
        media = self.build_media()

        with mock.patch.object(client, "media_info_gql", return_value=media) as public_lookup:
            with mock.patch.object(
                client,
                "media_info_v1",
                side_effect=AssertionError("unauthorized lookup should use public API first"),
            ) as private_lookup:
                result = client.media_info("123", use_cache=False)

        self.assertEqual(result.pk, "123")
        public_lookup.assert_called_once_with("123")
        private_lookup.assert_not_called()


class UsertagMediasPrivateFirstRegressionTestCase(unittest.TestCase):
    def build_private_client(self):
        client = Client()
        client.authorization_data = {"ds_user_id": "1"}
        return client

    def build_media(self, pk="123"):
        return Media(
            pk=pk,
            id=f"{pk}_456",
            code="abc",
            taken_at=datetime.now(UTC()),
            media_type=1,
            user=UserShort(pk="456", username="example", profile_pic_url="https://example.com/profile.jpg"),
            like_count=0,
            caption_text="",
            usertags=[],
            sponsor_tags=[],
        )

    def test_authorized_usertag_medias_paginated_uses_private_before_public(self):
        client = self.build_private_client()
        page = [self.build_media()]

        with mock.patch.object(client, "usertag_medias_paginated_v1", return_value=(page, "cursor")) as private_lookup:
            with mock.patch.object(
                client,
                "usertag_medias_paginated_gql",
                side_effect=AssertionError("authorized lookup should use private API first"),
            ) as public_lookup:
                medias, end_cursor = client.usertag_medias_paginated("456", amount=2)

        self.assertEqual(medias, page)
        self.assertEqual(end_cursor, "cursor")
        private_lookup.assert_called_once_with(456, 2, end_cursor="")
        public_lookup.assert_not_called()

    def test_authorized_usertag_medias_paginated_falls_back_to_public(self):
        client = self.build_private_client()
        page = [self.build_media()]

        with mock.patch.object(
            client,
            "usertag_medias_paginated_v1",
            side_effect=ClientError("private lookup failed"),
        ) as private_lookup:
            with mock.patch.object(
                client, "usertag_medias_paginated_gql", return_value=(page, "web-cursor")
            ) as public_lookup:
                medias, end_cursor = client.usertag_medias_paginated("456", amount=2)

        self.assertEqual(medias, page)
        self.assertEqual(end_cursor, "web-cursor")
        private_lookup.assert_called_once_with(456, 2, end_cursor="")
        public_lookup.assert_called_once_with(456, 2, end_cursor="")

    def test_unauthorized_usertag_medias_paginated_keeps_public_first(self):
        client = Client()
        page = [self.build_media()]

        with mock.patch.object(
            client, "usertag_medias_paginated_gql", return_value=(page, "web-cursor")
        ) as public_lookup:
            with mock.patch.object(
                client,
                "usertag_medias_paginated_v1",
                side_effect=AssertionError("unauthorized lookup should use public API first"),
            ) as private_lookup:
                medias, end_cursor = client.usertag_medias_paginated("456", amount=2)

        self.assertEqual(medias, page)
        self.assertEqual(end_cursor, "web-cursor")
        public_lookup.assert_called_once_with(456, 2, end_cursor="")
        private_lookup.assert_not_called()

    def test_authorized_usertag_medias_uses_private_before_public(self):
        client = self.build_private_client()
        medias = [self.build_media()]

        with mock.patch.object(client, "usertag_medias_v1", return_value=medias) as private_lookup:
            with mock.patch.object(
                client,
                "usertag_medias_gql",
                side_effect=AssertionError("authorized lookup should use private API first"),
            ) as public_lookup:
                result = client.usertag_medias("456", amount=2)

        self.assertEqual(result, medias)
        private_lookup.assert_called_once_with(456, 2)
        public_lookup.assert_not_called()

    def test_cookie_session_usertag_medias_uses_private_before_public(self):
        client = Client()
        client.private.cookies.set("sessionid", "1" * 40)
        medias = [self.build_media()]

        with mock.patch.object(client, "usertag_medias_v1", return_value=medias) as private_lookup:
            with mock.patch.object(
                client,
                "usertag_medias_gql",
                side_effect=AssertionError("cookie session lookup should use private API first"),
            ) as public_lookup:
                result = client.usertag_medias("456", amount=2)

        self.assertEqual(result, medias)
        private_lookup.assert_called_once_with(456, 2)
        public_lookup.assert_not_called()

    def test_unauthorized_usertag_medias_keeps_public_first(self):
        client = Client()
        medias = [self.build_media()]

        with mock.patch.object(client, "usertag_medias_gql", return_value=medias) as public_lookup:
            with mock.patch.object(
                client,
                "usertag_medias_v1",
                side_effect=AssertionError("unauthorized lookup should use public API first"),
            ) as private_lookup:
                result = client.usertag_medias("456", amount=2)

        self.assertEqual(result, medias)
        public_lookup.assert_called_once_with(456, 2)
        private_lookup.assert_not_called()


class UserMediasPrivateFirstRegressionTestCase(unittest.TestCase):
    def build_private_client(self):
        client = Client()
        client.authorization_data = {"ds_user_id": "1"}
        return client

    def build_media(self, pk="123"):
        return Media(
            pk=pk,
            id=f"{pk}_456",
            code="abc",
            taken_at=datetime.now(UTC()),
            media_type=1,
            user=UserShort(pk="456", username="example", profile_pic_url="https://example.com/profile.jpg"),
            like_count=0,
            caption_text="",
            usertags=[],
            sponsor_tags=[],
        )

    def test_authorized_user_medias_paginated_uses_private_before_public(self):
        client = self.build_private_client()
        page = [self.build_media()]

        with mock.patch.object(client, "user_medias_paginated_v1", return_value=(page, "v1-cursor")) as private_lookup:
            with mock.patch.object(
                client,
                "user_medias_paginated_gql",
                side_effect=AssertionError("authorized lookup should use private API first"),
            ) as public_lookup:
                medias, end_cursor = client.user_medias_paginated("456", amount=2)

        self.assertEqual(medias, page)
        self.assertEqual(end_cursor, "v1-cursor")
        private_lookup.assert_called_once_with("456", 2, end_cursor="")
        public_lookup.assert_not_called()

    def test_authorized_user_medias_paginated_falls_back_to_public(self):
        client = self.build_private_client()
        page = [self.build_media()]

        with mock.patch.object(
            client,
            "user_medias_paginated_v1",
            side_effect=ClientError("private lookup failed"),
        ) as private_lookup:
            with mock.patch.object(
                client, "user_medias_paginated_gql", return_value=(page, "web-cursor")
            ) as public_lookup:
                medias, end_cursor = client.user_medias_paginated("456", amount=2)

        self.assertEqual(medias, page)
        self.assertEqual(end_cursor, "web-cursor")
        private_lookup.assert_called_once_with("456", 2, end_cursor="")
        public_lookup.assert_called_once_with("456", 2, end_cursor="")

    def test_unauthorized_user_medias_paginated_keeps_public_first(self):
        client = Client()
        page = [self.build_media()]

        with mock.patch.object(client, "user_medias_paginated_gql", return_value=(page, "web-cursor")) as public_lookup:
            with mock.patch.object(
                client,
                "user_medias_paginated_v1",
                side_effect=AssertionError("unauthorized lookup should use public API first"),
            ) as private_lookup:
                medias, end_cursor = client.user_medias_paginated("456", amount=2)

        self.assertEqual(medias, page)
        self.assertEqual(end_cursor, "web-cursor")
        public_lookup.assert_called_once_with("456", 2, end_cursor="")
        private_lookup.assert_not_called()

    def test_v1_cursor_user_medias_paginated_uses_private_even_without_auth(self):
        client = Client()
        page = [self.build_media()]

        with mock.patch.object(client, "user_medias_paginated_v1", return_value=(page, "")) as private_lookup:
            with mock.patch.object(
                client,
                "user_medias_paginated_gql",
                side_effect=AssertionError("v1 cursor should continue through private API"),
            ) as public_lookup:
                medias, end_cursor = client.user_medias_paginated("456", amount=2, end_cursor="123_456")

        self.assertEqual(medias, page)
        self.assertEqual(end_cursor, "")
        private_lookup.assert_called_once_with("456", 2, end_cursor="123_456")
        public_lookup.assert_not_called()

    def test_v1_cursor_user_medias_paginated_does_not_fall_back_to_public(self):
        client = self.build_private_client()

        with mock.patch.object(
            client,
            "user_medias_paginated_v1",
            side_effect=ClientError("private cursor lookup failed"),
        ) as private_lookup:
            with mock.patch.object(
                client,
                "user_medias_paginated_gql",
                side_effect=AssertionError("v1 cursor should not be retried through public API"),
            ) as public_lookup:
                with self.assertRaises(ClientError):
                    client.user_medias_paginated("456", amount=2, end_cursor="123_456")

        private_lookup.assert_called_once_with("456", 2, end_cursor="123_456")
        public_lookup.assert_not_called()

    def test_iter_user_medias_streams_paginated_pages_and_respects_amount(self):
        client = self.build_private_client()
        medias = [self.build_media(pk=str(i)) for i in range(1, 5)]

        with mock.patch.object(
            client,
            "user_medias_paginated",
            side_effect=[(medias[:2], "cursor-1"), (medias[2:], "cursor-2")],
        ) as paginated:
            result = list(client.iter_user_medias("456", amount=3, page_size=2))

        self.assertEqual([media.pk for media in result], ["1", "2", "3"])
        paginated.assert_has_calls(
            [
                mock.call("456", amount=2, end_cursor=""),
                mock.call("456", amount=1, end_cursor="cursor-1"),
            ]
        )
        self.assertEqual(paginated.call_count, 2)

    def test_authorized_user_medias_uses_private_before_public(self):
        client = self.build_private_client()
        medias = [self.build_media()]

        with mock.patch.object(client, "user_medias_v1", return_value=medias) as private_lookup:
            with mock.patch.object(
                client,
                "user_medias_gql",
                side_effect=AssertionError("authorized lookup should use private API first"),
            ) as public_lookup:
                result = client.user_medias("456", amount=2)

        self.assertEqual(result, medias)
        private_lookup.assert_called_once_with(456, 2)
        public_lookup.assert_not_called()

    def test_cookie_session_user_medias_uses_private_before_public(self):
        client = Client()
        client.private.cookies.set("sessionid", "1" * 40)
        medias = [self.build_media()]

        with mock.patch.object(client, "user_medias_v1", return_value=medias) as private_lookup:
            with mock.patch.object(
                client,
                "user_medias_gql",
                side_effect=AssertionError("cookie session lookup should use private API first"),
            ) as public_lookup:
                result = client.user_medias("456", amount=2)

        self.assertEqual(result, medias)
        private_lookup.assert_called_once_with(456, 2)
        public_lookup.assert_not_called()

    def test_authorized_user_medias_falls_back_to_public(self):
        client = self.build_private_client()
        medias = [self.build_media()]

        with mock.patch.object(
            client, "user_medias_v1", side_effect=ClientError("private lookup failed")
        ) as private_lookup:
            with mock.patch.object(client, "user_medias_gql", return_value=medias) as public_lookup:
                result = client.user_medias("456", amount=2)

        self.assertEqual(result, medias)
        private_lookup.assert_called_once_with(456, 2)
        public_lookup.assert_called_once_with(456, 2, 0)

    def test_unauthorized_user_medias_keeps_public_first(self):
        client = Client()
        medias = [self.build_media()]

        with mock.patch.object(client, "user_medias_gql", return_value=medias) as public_lookup:
            with mock.patch.object(
                client,
                "user_medias_v1",
                side_effect=AssertionError("unauthorized lookup should use public API first"),
            ) as private_lookup:
                result = client.user_medias("456", amount=2)

        self.assertEqual(result, medias)
        public_lookup.assert_called_once_with(456, 2, 0)
        private_lookup.assert_not_called()


class MediaShareToStoryRegressionTestCase(unittest.TestCase):
    def test_media_share_to_story_uses_existing_media_as_story_sticker(self):
        client = Client()
        client.authorization_data = {"ds_user_id": "1"}
        background = Path("background.jpg")
        story = Story(
            pk="10",
            id="10_1",
            code="story10",
            taken_at=datetime.now(UTC()),
            media_type=1,
            product_type="story",
            thumbnail_url="https://example.com/story.jpg",
            user=UserShort(pk="1", username="example", profile_pic_url="https://example.com/profile.jpg"),
            sponsor_tags=[],
            mentions=[],
            links=[],
            hashtags=[],
            locations=[],
            stickers=[],
        )
        client.photo_upload_to_story = Mock(return_value=story)

        result = client.media_share_to_story(
            "123_456",
            background=background,
            caption="caption",
            x=0.4,
            y=0.45,
            width=0.7,
            height=0.55,
        )

        self.assertEqual(result, story)
        client.photo_upload_to_story.assert_called_once()
        args, kwargs = client.photo_upload_to_story.call_args
        self.assertEqual(args[:2], (background, "caption"))
        self.assertEqual(len(kwargs["medias"]), 1)
        media_sticker = kwargs["medias"][0]
        self.assertIsInstance(media_sticker, StoryMedia)
        self.assertEqual(media_sticker.media_pk, 123)
        self.assertEqual(media_sticker.user_id, 456)
        self.assertEqual(media_sticker.x, 0.4)
        self.assertEqual(media_sticker.y, 0.45)
        self.assertEqual(media_sticker.width, 0.7)
        self.assertEqual(media_sticker.height, 0.55)


class CheckOffensiveCommentV2RegressionTestCase(unittest.TestCase):
    def _build_logged_in_client(self):
        client = Client()
        client.authorization_data = {"ds_user_id": "1"}
        return client

    def test_v2_payload_is_lighter_than_v1(self):
        client = self._build_logged_in_client()
        with mock.patch.object(
            client,
            "private_request",
            return_value={"is_offensive": True, "category": "harassment"},
        ) as private_request:
            result = client.media_check_offensive_comment_v2("9_8", "rude")

        private_request.assert_called_once()
        path, kwargs = (
            private_request.call_args.args[0],
            private_request.call_args.kwargs,
        )
        self.assertEqual(path, "media/comment/check_offensive_comment/")
        # data passed as keyword to mirror aiograpi shape
        self.assertEqual(kwargs["data"]["comment_text"], "rude")
        self.assertEqual(kwargs["data"]["media_id"], "9_8")
        self.assertIn("_uuid", kwargs["data"])
        # No with_action_data wrapping → no _csrftoken / _uid /
        # user_breadcrumb in the payload.
        self.assertNotIn("_csrftoken", kwargs["data"])
        self.assertNotIn("_uid", kwargs["data"])
        self.assertNotIn("user_breadcrumb", kwargs["data"])
        # Raw response is returned, not just bool.
        self.assertEqual(result, {"is_offensive": True, "category": "harassment"})

    def test_v2_requires_login(self):
        client = Client()
        # No authorization_data → user_id property returns None.
        with self.assertRaises(AssertionError):
            client.media_check_offensive_comment_v2("9_8", "rude")


class MediaActionPayloadRegressionTestCase(unittest.TestCase):
    def _build_logged_in_client(self):
        client = Client()
        client.authorization_data = {"ds_user_id": "1"}
        client.uuid = "uuid"
        client.android_device_id = "android-device"
        return client

    def test_media_like_preserves_full_media_id_and_posts_current_action_context(self):
        client = self._build_logged_in_client()
        with mock.patch.object(
            client,
            "private_request",
            return_value={"status": "ok"},
        ) as private_request:
            self.assertTrue(client.media_like("123_456"))

        endpoint, data = private_request.call_args.args
        self.assertEqual(endpoint, "media/123_456/like/")
        self.assertEqual(data["media_id"], "123_456")
        self.assertEqual(data["_uid"], "1")
        self.assertEqual(data["device_id"], "android-device")
        self.assertEqual(data["radio_type"], "wifi-none")
        self.assertEqual(data["delivery_class"], "organic")
        self.assertEqual(data["tap_source"], "button")
        self.assertEqual(data["is_2m_enabled"], "false")
        self.assertEqual(data["is_from_swipe"], "false")
        self.assertEqual(data["floating_context_items"], "[]")
        self.assertEqual(data["media_pct_watched"], "0")
        self.assertEqual(data["container_module"], "feed_timeline")
        self.assertIn(data["feed_position"], {str(i) for i in range(7)})

    def test_media_note_create_posts_current_v2_payload(self):
        client = self._build_logged_in_client()
        expected = {
            "id": "17881913307564398",
            "media_id": "3884795301060104481",
            "text": "seen this",
            "status": "ok",
        }

        with mock.patch.object(client, "private_request", return_value=expected) as private_request:
            result = client.media_note_create(
                "3884795301060104481_52448022913",
                text="seen this",
                extra_data={"ranking_info_token": "rank-token"},
            )

        self.assertEqual(result, expected)
        private_request.assert_called_once_with(
            "media/create_note/v2/",
            data={
                "inventory_source": "recommended_clips_chaining_model",
                "media_client_position": "0",
                "media_id": "3884795301060104481_52448022913",
                "note_style": "13",
                "carousel_index": "-1",
                "text": "seen this",
                "_uuid": "uuid",
                "audience": "7",
                "event_source": "ufi",
                "container_module": "clips_viewer_clips_tab",
                "ranking_info_token": "rank-token",
            },
            with_signature=False,
        )

    def test_media_note_delete_posts_current_v2_payload(self):
        client = self._build_logged_in_client()

        with mock.patch.object(client, "private_request", return_value={"status": "ok"}) as private_request:
            result = client.media_note_delete("17881913307564398", extra_data={"ranking_info_token": "rank-token"})

        self.assertTrue(result)
        private_request.assert_called_once_with(
            "media/delete_note/",
            data={
                "inventory_source": "recommended_clips_chaining_model",
                "carousel_index": "-1",
                "_uuid": "uuid",
                "event_source": "ufi",
                "container_module": "clips_viewer_clips_tab",
                "note_id": "17881913307564398",
                "ranking_info_token": "rank-token",
            },
            with_signature=False,
        )

    def test_media_link_reel_posts_linked_media_info(self):
        client = self._build_logged_in_client()
        client._medias_cache = {"111": object()}

        with mock.patch.object(client, "private_request", return_value={"status": "ok"}) as private_request:
            result = client.media_link_reel("111_222", "333_444", link_name="Watch Part 1")

        self.assertTrue(result)
        endpoint, data = private_request.call_args.args
        self.assertEqual(endpoint, "media/111_222/edit_media/")
        self.assertEqual(data["_uid"], "1")
        self.assertEqual(data["_uuid"], "uuid")
        self.assertEqual(data["device_id"], "android-device")
        self.assertEqual(data["radio_type"], "wifi-none")
        self.assertEqual(
            json.loads(data["linked_media_info"]),
            {"media_id": "333_444", "link_name": "Watch Part 1"},
        )
        self.assertNotIn("111", client._medias_cache)

    def test_media_link_reel_normalizes_origin_and_target_media_ids(self):
        client = self._build_logged_in_client()

        with (
            mock.patch.object(
                client,
                "media_user",
                side_effect=[
                    UserShort(pk="222", username="origin", profile_pic_url="https://example.com/origin.jpg"),
                    UserShort(pk="444", username="target", profile_pic_url="https://example.com/target.jpg"),
                ],
            ),
            mock.patch.object(client, "private_request", return_value={"status": "ok"}) as private_request,
        ):
            self.assertTrue(client.media_link_reel("111", "333"))

        endpoint, data = private_request.call_args.args
        self.assertEqual(endpoint, "media/111_222/edit_media/")
        self.assertEqual(json.loads(data["linked_media_info"])["media_id"], "333_444")

    def test_media_unlink_reel_posts_empty_linked_media_info(self):
        client = self._build_logged_in_client()
        client._medias_cache = {"111": object()}

        with mock.patch.object(client, "private_request", return_value={"status": "ok"}) as private_request:
            result = client.media_unlink_reel("111_222")

        self.assertTrue(result)
        endpoint, data = private_request.call_args.args
        self.assertEqual(endpoint, "media/111_222/edit_media/")
        self.assertEqual(data["_uid"], "1")
        self.assertEqual(data["_uuid"], "uuid")
        self.assertEqual(data["device_id"], "android-device")
        self.assertEqual(data["radio_type"], "wifi-none")
        self.assertEqual(data["linked_media_info"], "")
        self.assertNotIn("111", client._medias_cache)


class UsertagMediasPaginationRegressionTestCase(unittest.TestCase):
    def _media_v1_payload(self, pk="1"):
        return {
            "pk": pk,
            "id": f"{pk}_2",
            "code": "abc",
            "taken_at": 1710000000,
            "media_type": 1,
            "user": {
                "pk": "2",
                "username": "example",
                "profile_pic_url": "https://example.com/profile.jpg",
            },
            "image_versions2": {
                "candidates": [{"url": "https://example.com/x.jpg", "width": 100, "height": 100}],
                "scrubber_spritesheet_info_candidates": {"default": {"video_length": 15.4}},
            },
        }

    def _media_gql_payload(self, pk="1"):
        return {
            "__typename": "GraphImage",
            "id": pk,
            "shortcode": "abc",
            "taken_at_timestamp": 1710000000,
            "owner": {
                "id": "2",
                "username": "example",
                "profile_pic_url": "https://example.com/profile.jpg",
            },
            "display_resources": [{"src": "https://example.com/x.jpg", "config_width": 100, "config_height": 100}],
            "edge_media_to_comment": {"count": 0},
            "edge_media_preview_like": {"count": 0},
            "edge_media_to_caption": {"edges": []},
            "edge_media_to_tagged_user": {"edges": []},
        }

    def test_usertag_medias_paginated_gql_returns_page_and_cursor(self):
        client = Client()
        payload = self._media_gql_payload()

        with mock.patch.object(
            client,
            "public_graphql_request",
            return_value={
                "user": {
                    "edge_user_to_photos_of_you": {
                        "page_info": {"end_cursor": "next-page"},
                        "edges": [{"node": payload}],
                    }
                }
            },
        ) as public_graphql_request:
            medias, end_cursor = client.usertag_medias_paginated_gql("123", amount=1, end_cursor="cursor-1")

        public_graphql_request.assert_called_once_with(
            {"id": 123, "first": 1, "after": "cursor-1"},
            query_hash="be13233562af2d229b008d2976b998b5",
        )
        self.assertEqual(end_cursor, "next-page")
        self.assertEqual([media.pk for media in medias], ["1"])

    def test_usertag_medias_paginated_v1_returns_page_and_cursor(self):
        client = Client()
        payload = self._media_v1_payload()

        with mock.patch.object(
            client,
            "private_request",
            return_value={"items": [payload], "next_max_id": "next-page"},
        ) as private_request:
            medias, end_cursor = client.usertag_medias_paginated_v1("123", amount=1, end_cursor="cursor-1")

        private_request.assert_called_once_with("usertags/123/feed/", params={"max_id": "cursor-1"})
        self.assertEqual(end_cursor, "next-page")
        self.assertEqual([media.pk for media in medias], ["1"])

    def test_usertag_medias_paginated_falls_back_to_v1(self):
        client = Client()

        with mock.patch.object(
            client,
            "usertag_medias_paginated_gql",
            side_effect=ClientError("public unavailable"),
        ) as gql:
            with mock.patch.object(
                client,
                "usertag_medias_paginated_v1",
                return_value=(["m1"], "next-page"),
            ) as v1:
                medias, end_cursor = client.usertag_medias_paginated("123", amount=5, end_cursor="cursor-1")

        gql.assert_called_once_with(123, 5, end_cursor="cursor-1")
        v1.assert_called_once_with(123, 5, end_cursor="cursor-1")
        self.assertEqual(medias, ["m1"])
        self.assertEqual(end_cursor, "next-page")


class UserMediasGraphQLRegressionTestCase(unittest.TestCase):
    def _xdt_media_payload(self):
        return {
            "id": "1",
            "code": "abc",
            "1ltaken_at": 1710000000,
            "media_type": 1,
            "usertags": None,
            "carousel_media": None,
            "user": {
                "pk": "2",
                "username": "example",
                "profile_pic_url": "https://example.com/profile.jpg",
            },
            "image_versions2": {"candidates": [{"url": "https://example.com/x.jpg", "width": 100, "height": 100}]},
        }

    def test_user_medias_paginated_gql_uses_app_timeline_doc_id(self):
        client = Client()
        response = {
            "data": {
                "xdt_api__v1__profile_timeline": {
                    "profile_grid_items": [{"media": self._xdt_media_payload()}],
                    "more_available": True,
                    "next_max_id": "next-page",
                }
            }
        }

        with mock.patch.object(client, "private_graphql_request", return_value=response) as private_graphql:
            with mock.patch.object(
                client,
                "public_graphql_request",
                side_effect=AssertionError("legacy query_hash should not be used"),
            ) as public_graphql:
                medias, end_cursor = client.user_medias_paginated_gql("123", amount=1, end_cursor="cursor-1")

        private_graphql.assert_called_once()
        public_graphql.assert_not_called()
        data = private_graphql.call_args.args[0]
        variables = json.loads(data["variables"])
        self.assertEqual(data["fb_api_req_friendly_name"], "IGProfileTimelineQuery")
        self.assertEqual(data["client_doc_id"], "56030350814417327502004290437")
        self.assertEqual(variables["user_id"], "123")
        self.assertEqual(variables["count"], 1)
        self.assertEqual(variables["max_id"], "cursor-1")
        self.assertEqual(end_cursor, "next-page")
        self.assertEqual([media.pk for media in medias], ["1"])
        self.assertEqual(medias[0].id, "1_2")

    def test_aiograpi_chunk_aliases_delegate_to_paginated_helpers(self):
        client = Client()
        with mock.patch.object(client, "user_medias_paginated_gql", return_value=(["gql"], "gql-next")) as gql:
            self.assertEqual(
                client.user_medias_chunk_gql("123", sleep=1, end_cursor="cursor", amount=7), (["gql"], "gql-next")
            )
        gql.assert_called_once_with("123", amount=7, sleep=1, end_cursor="cursor")

        with mock.patch.object(client, "user_medias_paginated_v1", return_value=(["v1"], "v1-next")) as medias_v1:
            self.assertEqual(client.user_medias_chunk_v1("123", end_cursor="cursor"), (["v1"], "v1-next"))
        medias_v1.assert_called_once_with("123", amount=33, end_cursor="cursor")

        with mock.patch.object(client, "user_videos_paginated_v1", return_value=(["video"], "video-next")) as videos_v1:
            self.assertEqual(client.user_videos_chunk_v1("123", end_cursor="cursor"), (["video"], "video-next"))
        videos_v1.assert_called_once_with("123", amount=50, end_cursor="cursor")

        with mock.patch.object(client, "user_clips_paginated_v1", return_value=(["clip"], "clip-next")) as clips_v1:
            self.assertEqual(client.user_clips_chunk_v1("123", end_cursor="cursor"), (["clip"], "clip-next"))
        clips_v1.assert_called_once_with("123", amount=50, end_cursor="cursor")

        with mock.patch.object(client, "usertag_medias_paginated_v1", return_value=(["tag"], "tag-next")) as tags_v1:
            self.assertEqual(client.usertag_medias_v1_chunk("123", max_id="cursor"), (["tag"], "tag-next"))
        tags_v1.assert_called_once_with("123", amount=0, end_cursor="cursor")

    def test_user_medias_chunk_delegates_to_paginated(self):
        client = Client()
        with mock.patch.object(client, "user_medias_paginated", return_value=(["media"], "next")) as paginated:
            result = client.user_medias_chunk("123", end_cursor="cursor")

        self.assertEqual(result, (["media"], "next"))
        paginated.assert_called_once_with("123", amount=0, end_cursor="cursor")

    def test_media_likers_gql_chunk_posts_doc_id_query(self):
        client = Client()
        client._fb_dtsg = "token"
        with mock.patch.object(
            client,
            "graphql_request",
            return_value={
                "data": {"xdt_api__v1__likes__media_id__likers": {"users": [{"id": "1", "username": "alice"}]}}
            },
        ) as graphql_request:
            users = client.media_likers_gql_chunk("123")

        self.assertEqual(users, [{"id": "1", "username": "alice"}])
        data = graphql_request.call_args.kwargs["data"]
        self.assertEqual(data["doc_id"], "24452425501069647")
        self.assertIn('"id":"123"', data["variables"])

    def test_media_template_v1_posts_template_media_id(self):
        client = Client()
        client.uuid = "uuid"
        expected = {"template": {"media_id": "123_456"}}
        with mock.patch.object(client, "private_request", return_value=expected) as private_request:
            result = client.media_template_v1("123_456")

        self.assertEqual(result, expected)
        private_request.assert_called_once_with(
            "clips/template/",
            data={
                "should_show_friends_media_at_top": "false",
                "template_clips_media_id": "123_456",
                "_uuid": "uuid",
            },
        )
