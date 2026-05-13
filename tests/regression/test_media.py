import json

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
