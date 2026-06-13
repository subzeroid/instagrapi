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
