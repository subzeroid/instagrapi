from instagrapi.exceptions import ClientNotFoundError, UserNotFound
from tests.helpers import *


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

    def test_authorized_user_stories_falls_back_to_public(self):
        client = self.build_private_client()
        stories = [object()]

        with mock.patch.object(
            client,
            "user_stories_v1",
            side_effect=ClientGraphqlError("private lookup failed"),
        ) as private_lookup:
            with mock.patch.object(client, "user_stories_gql", return_value=stories) as public_lookup:
                result = client.user_stories("123", amount=1)

        self.assertEqual(result, stories)
        private_lookup.assert_called_once_with("123", 1)
        public_lookup.assert_called_once_with("123", 1)

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
        story_payload = {
            "id": "1234567890",
            "owner": {
                "id": "123",
                "username": "alice",
                "full_name": "Alice",
                "profile_pic_url": "https://example.com/alice.jpg",
                "is_private": False,
            },
            "display_url": "https://example.com/story.jpg",
            "taken_at_timestamp": 1_700_000_000,
            "is_video": False,
            "tappable_objects": [],
            "edge_media_to_sponsor_user": {"edges": []},
        }

        with mock.patch.object(client, "inject_sessionid_to_public", return_value=True):
            with mock.patch.object(
                client,
                "public_graphql_request",
                return_value={"reels_media": [{"owner": story_payload["owner"], "items": [story_payload]}]},
            ):
                users = client.users_stories_gql(["123"])

        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].pk, "123")
        self.assertEqual(len(users[0].stories), 1)
        self.assertEqual(users[0].stories[0].id, "1234567890_123")

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
