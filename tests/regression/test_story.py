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
