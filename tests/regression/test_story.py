import json
from copy import deepcopy

from instagrapi.exceptions import ClientGraphqlError, ClientNotFoundError, UserNotFound
from instagrapi.extractors import extract_story_web
from instagrapi.mixins.graphql import PrivateGraphQLRequestMixin
from tests.helpers import *


def web_story_payload():
    return {
        "pk": 314159265358979,
        "id": "314159265358979_271828182845904",
        "code": "web-story-code",
        "taken_at": 1700000000,
        "media_type": 2,
        "user": {
            "pk": 271828182845904,
            "username": "web-story-user",
            "profile_pic_url": "https://example.com/profile.jpg",
        },
        "video_versions": [
            {"type": 101, "url": "https://example.com/first.mp4"},
            {"type": 102, "url": "https://example.com/second.mp4"},
        ],
        "image_versions2": {
            "candidates": [
                {
                    "url": "https://example.com/thumb.jpg",
                    "width": 720,
                    "height": 1280,
                }
            ]
        },
        "story_locations": None,
        "story_hashtags": None,
        "story_cta": None,
        "sponsor_tags": None,
        "story_feed_media": None,
        "story_link_stickers": None,
    }


class StoryMixinRegressionTestCase(unittest.TestCase):
    def build_private_client(self):
        client = Client()
        client.settings = {}
        client.authorization_data = {"ds_user_id": "1"}
        return client

    def test_authorized_user_stories_uses_private_before_public(self):
        client = self.build_private_client()
        stories = [object()]

        with mock.patch.object(client, "user_stories_v1", return_value=stories) as private_lookup:
            with mock.patch.object(
                client,
                "user_stories_gql",
                side_effect=AssertionError("authorized lookup should use private API first"),
            ) as public_lookup:
                result = client.user_stories("123", amount=1)

        self.assertEqual(result, stories)
        private_lookup.assert_called_once_with("123", 1)
        public_lookup.assert_not_called()

    def test_authorized_user_stories_preserves_private_error(self):
        client = self.build_private_client()
        with (
            mock.patch.object(client, "user_stories_v1", side_effect=ClientError("primary unavailable")),
            mock.patch.object(client, "user_stories_gql") as legacy,
        ):
            with self.assertRaisesRegex(ClientError, "primary unavailable"):
                client.user_stories("123", amount=1)
        legacy.assert_not_called()

    def test_unauthorized_user_stories_keeps_public_first(self):
        client = Client()
        stories = [object()]

        with mock.patch.object(client, "user_stories_gql", return_value=stories) as public_lookup:
            with mock.patch.object(
                client,
                "user_stories_v1",
                side_effect=AssertionError("unauthorized lookup should use public API first"),
            ) as private_lookup:
                result = client.user_stories("123", amount=1)

        self.assertEqual(result, stories)
        public_lookup.assert_called_once_with("123", 1)
        private_lookup.assert_not_called()

    def test_unauthorized_user_stories_keeps_public_not_found_mapping(self):
        client = Client()
        client.last_json = {"status": "fail"}

        with mock.patch.object(client, "user_stories_gql", side_effect=ClientNotFoundError("missing")):
            with self.assertRaises(UserNotFound):
                client.user_stories("123")

    def test_users_stories_gql_populates_user_short_stories(self):
        client = Client()
        client.public_graphql_request = mock.Mock(side_effect=AssertionError("legacy query must not be used"))
        client._fb_dtsg = "token"
        body = {
            "data": {
                "xdt_api__v1__feed__reels_media": {
                    "reels_media": [{"items": [web_story_payload(), web_story_payload()]}]
                }
            }
        }
        with mock.patch.object(client, "graphql_request", return_value=body) as request:
            users = client.users_stories_gql(["271828182845904"], amount=1)

        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].pk, "271828182845904")
        self.assertEqual(len(users[0].stories), 1)
        self.assertEqual(users[0].stories[0].pk, "314159265358979")
        request.assert_called_once_with(
            data={
                "variables": json.dumps(
                    {
                        "reel_ids_arr": ["271828182845904"],
                        "__relay_internal__pv__PolarisCommunityNoteStoriesLabelEnabledrelayprovider": True,
                    }
                ),
                "doc_id": "29184890191114309",
                "fb_dtsg": "token",
                "fb_api_caller_class": "RelayModern",
                "fb_api_req_friendly_name": "PolarisStoriesV3ReelPageStandaloneQuery",
                "server_timestamps": "true",
            }
        )

    def test_users_stories_gql_validates_modern_response_and_preserves_errors(self):
        client = Client()
        client.public_graphql_request = mock.Mock(side_effect=AssertionError("legacy query must not be used"))
        client._fb_dtsg = "token"
        empty = {"data": {"xdt_api__v1__feed__reels_media": {"reels_media": [{"items": []}]}}}
        with mock.patch.object(client, "graphql_request", return_value=empty):
            self.assertEqual(client.users_stories_gql(["123"]), [])

        bodies = [
            {},
            {"data": {}},
            {"data": {"xdt_api__v1__feed__reels_media": None}},
            {"data": {"xdt_api__v1__feed__reels_media": {"reels_media": None}}},
            {"data": {"xdt_api__v1__feed__reels_media": {"reels_media": [{}]}}},
        ]
        for body in bodies:
            with self.subTest(body=body):
                with mock.patch.object(client, "graphql_request", return_value=body):
                    with self.assertRaises(ClientGraphqlError):
                        client.users_stories_gql(["123"])

        error = ClientGraphqlError("request failed")
        with mock.patch.object(client, "graphql_request", side_effect=error):
            with self.assertRaises(ClientGraphqlError) as caught:
                client.users_stories_gql(["123"])
        self.assertIs(caught.exception, error)

    def test_extract_story_v1_reads_poll_stickers(self):
        story = extract_story_v1(
            {
                "pk": "1",
                "id": "1_2",
                "code": "abc",
                "taken_at": 1710000000,
                "media_type": 1,
                "image_versions2": {
                    "candidates": [
                        {
                            "url": "https://example.com/thumbnail.jpg",
                            "width": 720,
                            "height": 1280,
                        }
                    ]
                },
                "user": {
                    "pk": "2",
                    "username": "example",
                    "profile_pic_url": "https://example.com/profile.jpg",
                },
                "story_polls": [
                    {
                        "x": 0.5,
                        "y": 0.5,
                        "z": 0,
                        "width": 0.7,
                        "height": 0.3,
                        "rotation": 0.0,
                        "poll_sticker": {
                            "poll_id": "17895695668004550",
                            "question": "Pick one",
                            "viewer_can_vote": True,
                            "finished": False,
                            "tallies": [
                                {"text": "Yes", "count": 1},
                                {"text": "No", "count": 0},
                            ],
                        },
                    }
                ],
            }
        )

        self.assertEqual(len(story.polls), 1)
        self.assertEqual(story.polls[0].id, "17895695668004550")
        self.assertEqual(story.polls[0].question, "Pick one")
        self.assertEqual(story.polls[0].options, ["Yes", "No"])
        self.assertTrue(story.polls[0].viewer_can_vote)

    def test_extract_story_v1_normalizes_sponsor_tag_friendship_status(self):
        story = extract_story_v1(
            {
                "pk": "1",
                "id": "1_2",
                "code": "abc",
                "taken_at": 1710000000,
                "media_type": 1,
                "image_versions2": {
                    "candidates": [
                        {
                            "url": "https://example.com/thumbnail.jpg",
                            "width": 720,
                            "height": 1280,
                        }
                    ]
                },
                "user": {
                    "pk": "2",
                    "username": "example",
                    "profile_pic_url": "https://example.com/profile.jpg",
                },
                "sponsor_tags": [
                    {
                        "sponsor": {
                            "pk": "3",
                            "username": "sponsor",
                            "profile_pic_url": "https://example.com/sponsor.jpg",
                            "friendship_status": {"following": False},
                        }
                    }
                ],
            }
        )

        self.assertEqual(story.sponsor_tags[0].pk, "3")
        self.assertEqual(story.sponsor_tags[0].friendship_status.user_id, "3")
        self.assertFalse(story.sponsor_tags[0].friendship_status.following)
        self.assertFalse(story.sponsor_tags[0].friendship_status.incoming_request)

    def test_story_poll_vote_posts_vote_to_poll_endpoint(self):
        client = self.build_private_client()
        client._user_id = "1"

        with mock.patch.object(client, "private_request", return_value={"status": "ok"}) as private_request:
            result = client.story_poll_vote("1234567890_1", "17895695668004550", 1)

        self.assertTrue(result)
        private_request.assert_called_once()
        endpoint, data = private_request.call_args.args
        self.assertEqual(endpoint, "media/1234567890_1/17895695668004550/story_poll_vote/")
        self.assertEqual(data["_uid"], "1")
        self.assertEqual(data["vote"], "1")
        self.assertEqual(data["radio_type"], "wifi-none")

    def test_story_likers_chunk_filters_liked_viewers_and_deduplicates_users(self):
        client = self.build_private_client()
        responses = [
            {
                "viewers": [
                    {
                        "has_liked": True,
                        "user": {
                            "pk": "10",
                            "username": "liked_1",
                            "profile_pic_url": "https://example.com/liked_1.jpg",
                        },
                    },
                    {
                        "has_liked": False,
                        "user": {
                            "pk": "20",
                            "username": "viewer_only",
                            "profile_pic_url": "https://example.com/viewer_only.jpg",
                        },
                    },
                ],
                "next_max_id": "page-2",
            },
            {
                "viewers": [
                    {
                        "has_liked": True,
                        "user": {
                            "pk": "10",
                            "username": "liked_1_duplicate",
                            "profile_pic_url": "https://example.com/liked_1_duplicate.jpg",
                        },
                    },
                    {
                        "has_liked": True,
                        "user": {
                            "pk": "30",
                            "username": "liked_2",
                            "profile_pic_url": "https://example.com/liked_2.jpg",
                        },
                    },
                ],
            },
        ]

        with mock.patch.object(client, "private_request", side_effect=responses) as private_request:
            likers, max_id = client.story_likers_chunk("1234567890_1")

        self.assertEqual([liker.pk for liker in likers], ["10", "30"])
        self.assertEqual([liker.username for liker in likers], ["liked_1", "liked_2"])
        self.assertIsNone(max_id)
        self.assertEqual(private_request.call_args_list[0].args[0], "media/1234567890/list_reel_media_viewer/")
        self.assertIn("supported_capabilities_new", private_request.call_args_list[0].kwargs["params"])
        self.assertEqual(private_request.call_args_list[1].kwargs["params"]["max_id"], "page-2")

    def test_story_likers_limits_amount(self):
        client = self.build_private_client()
        responses = [
            {
                "viewers": [
                    {
                        "has_liked": True,
                        "user": {
                            "pk": "10",
                            "username": "liked_1",
                            "profile_pic_url": "https://example.com/liked_1.jpg",
                        },
                    },
                    {
                        "has_liked": True,
                        "user": {
                            "pk": "20",
                            "username": "liked_2",
                            "profile_pic_url": "https://example.com/liked_2.jpg",
                        },
                    },
                ],
            }
        ]

        with mock.patch.object(client, "private_request", side_effect=responses):
            likers = client.story_likers("1234567890_1", amount=1)

        self.assertEqual([liker.pk for liker in likers], ["10"])

    def test_story_likers_handles_viewer_payload_without_viewers(self):
        client = self.build_private_client()

        with mock.patch.object(
            client,
            "private_request",
            return_value={"status": "ok", "user_count": 0, "total_viewer_count": 0},
        ):
            likers = client.story_likers("1234567890_1")

        self.assertEqual(likers, [])

    def test_story_like_marks_story_seen_before_liking(self):
        client = self.build_private_client()
        client._user_id = "1"

        with mock.patch.object(client, "story_seen", return_value=True) as story_seen:
            with mock.patch.object(client, "private_request", return_value={"status": "ok"}) as private_request:
                result = client.story_like("1234567890_1")

        self.assertTrue(result)
        story_seen.assert_called_once_with(["1234567890"])
        private_request.assert_called_once()
        self.assertEqual(private_request.call_args.args[0], "story_interactions/send_story_like")

    def test_story_like_can_skip_mark_seen(self):
        client = self.build_private_client()
        client._user_id = "1"

        with mock.patch.object(client, "story_seen", return_value=True) as story_seen:
            with mock.patch.object(client, "private_request", return_value={"status": "ok"}):
                result = client.story_like("1234567890_1", mark_seen=False)

        self.assertTrue(result)
        story_seen.assert_not_called()

    def test_story_unlike_does_not_mark_story_seen(self):
        client = self.build_private_client()
        client._user_id = "1"

        with mock.patch.object(client, "story_seen", return_value=True) as story_seen:
            with mock.patch.object(client, "private_request", return_value={"status": "ok"}) as private_request:
                result = client.story_unlike("1234567890_1")

        self.assertTrue(result)
        story_seen.assert_not_called()
        self.assertEqual(private_request.call_args.args[0], "story_interactions/unsend_story_like")

    def test_extract_story_web_normalizes_capture_shape(self):
        payload = web_story_payload()
        original = deepcopy(payload)

        story = extract_story_web(payload)

        self.assertEqual(payload, original)
        self.assertEqual(story.pk, str(payload["pk"]))
        self.assertEqual(story.id, payload["id"])
        self.assertEqual(int(story.taken_at.timestamp()), payload["taken_at"])
        self.assertEqual(story.media_type, payload["media_type"])
        self.assertEqual(story.user.pk, str(payload["user"]["pk"]))
        self.assertEqual(str(story.video_url), "https://example.com/first.mp4")
        self.assertEqual(str(story.thumbnail_url), "https://example.com/thumb.jpg")
        for field in ("locations", "hashtags", "links", "sponsor_tags", "medias", "stickers"):
            self.assertEqual(getattr(story, field), [])

    def test_extract_story_web_requires_identifiers(self):
        for kind in ("story", "user"):
            payload = web_story_payload()
            if kind == "story":
                payload.pop("pk")
            else:
                payload["user"].pop("pk")
                payload["user"].pop("id", None)
            with self.subTest(kind=kind):
                with self.assertRaises(KeyError):
                    extract_story_web(payload)

    def test_graphql_fetch_fb_dtsg_uses_instagram_homepage(self):
        client = Client()
        response = mock.Mock()
        response.content = b'<html><script id="__eqmc">{"f":"synthetic-dtsg"}</script></html>'
        with (
            mock.patch.object(client, "inject_sessionid_to_public") as inject,
            mock.patch.object(client.graphql, "get", return_value=response) as get,
        ):
            self.assertEqual(PrivateGraphQLRequestMixin.fetch_fb_dtsg(client), "synthetic-dtsg")
        get.assert_called_once_with("https://www.instagram.com/", proxies=client.graphql.proxies)
        inject.assert_called_once_with()

    def test_user_stories_web_uses_modern_query_and_typed_response(self):
        client = Client()
        client._fb_dtsg = "token"
        body = {
            "data": {
                "xdt_api__v1__feed__reels_media": {
                    "reels_media": [{"items": [web_story_payload(), web_story_payload()]}]
                }
            }
        }

        with mock.patch.object(client, "graphql_request", return_value=body) as request:
            stories = client.user_stories_web("271828182845904", amount=1)

        self.assertEqual(len(stories), 1)
        self.assertEqual(stories[0].pk, "314159265358979")
        request.assert_called_once_with(
            data={
                "variables": json.dumps(
                    {
                        "reel_ids_arr": ["271828182845904"],
                        "__relay_internal__pv__PolarisCommunityNoteStoriesLabelEnabledrelayprovider": True,
                    }
                ),
                "doc_id": "29184890191114309",
                "fb_dtsg": "token",
                "fb_api_caller_class": "RelayModern",
                "fb_api_req_friendly_name": "PolarisStoriesV3ReelPageStandaloneQuery",
                "server_timestamps": "true",
            }
        )

    def test_user_stories_web_empty_and_malformed_roots(self):
        client = Client()
        client._fb_dtsg = "token"
        empty = {"data": {"xdt_api__v1__feed__reels_media": {"reels_media": []}}}
        with mock.patch.object(client, "graphql_request", return_value=empty):
            self.assertEqual(client.user_stories_web("271828182845904"), [])

        bodies = [
            {"data": {}},
            {"data": {"xdt_api__v1__feed__reels_media": None}},
            {"data": {"xdt_api__v1__feed__reels_media": {"reels_media": None}}},
            {"data": {"xdt_api__v1__feed__reels_media": {"reels_media": [{}]}}},
        ]
        for body in bodies:
            with self.subTest(body=body):
                with mock.patch.object(client, "graphql_request", return_value=body):
                    with self.assertRaises(ClientGraphqlError):
                        client.user_stories_web("271828182845904")

    def test_extract_story_web_skips_empty_dimensionless_urls(self):
        payload = web_story_payload()
        payload["video_versions"][0]["url"] = ""

        story = extract_story_web(payload)

        self.assertEqual(str(story.video_url), "https://example.com/second.mp4")

    def test_extract_story_web_keeps_dimensioned_video_selection(self):
        payload = web_story_payload()
        payload["video_versions"] = [
            {"url": "https://example.com/small.mp4", "width": 320, "height": 480},
            {"url": "https://example.com/large.mp4", "width": 720, "height": 1280},
        ]

        story = extract_story_web(payload)

        self.assertEqual(str(story.video_url), "https://example.com/large.mp4")

    def test_user_stories_web_preserves_request_errors_and_empty_items(self):
        client = Client()
        client._fb_dtsg = "token"
        error = ClientGraphqlError("request failed")
        with mock.patch.object(client, "graphql_request", side_effect=error):
            with self.assertRaises(ClientGraphqlError) as caught:
                client.user_stories_web("271828182845904")
        self.assertIs(caught.exception, error)

        empty = {"data": {"xdt_api__v1__feed__reels_media": {"reels_media": [{"items": []}]}}}
        with mock.patch.object(client, "graphql_request", return_value=empty):
            self.assertEqual(client.user_stories_web("271828182845904"), [])
