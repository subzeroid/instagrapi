import json
import unittest
from copy import deepcopy
from unittest.mock import Mock

from instagrapi import Client
from instagrapi.types import User, UserShort

PROFILE_USER = {
    "id": "123",
    "pk": "123",
    "username": "example",
    "full_name": "Example",
    "is_private": False,
    "is_verified": True,
    "profile_pic_url": "https://example.com/pic.jpg",
    "media_count": 7,
    "follower_count": 11,
    "following_count": 3,
    "is_business_account": True,
    "category_name": "Creator",
    "friendship_status": {"following": True, "followed_by": False},
}


class ProfileGraphQLRegressionTestCase(unittest.TestCase):
    maxDiff = None

    def build_client(self):
        client = Client()
        client.authorization_data = {"ds_user_id": "42", "sessionid": "test-session"}
        client.public_request = Mock(return_value={"data": {"user": deepcopy(PROFILE_USER)}})
        return client

    def assert_current_profile_request(self, client):
        client.public_request.assert_called_once()
        call = client.public_request.call_args
        self.assertEqual(call.args, (client.GRAPHQL_PUBLIC_API_URL,))
        self.assertNotIn("X-FB-Friendly-Name", call.kwargs["headers"])
        self.assertTrue(call.kwargs["return_json"])
        self.assertEqual(call.kwargs["data"]["server_timestamps"], "true")
        self.assertEqual(
            {
                "doc_id": call.kwargs["data"]["doc_id"],
                "variables": json.loads(call.kwargs["data"]["variables"]),
            },
            {
                "doc_id": "28036671149327607",
                "variables": {
                    "id": "123",
                    "enable_integrity_filters": True,
                    "render_surface": "PROFILE",
                    "__relay_internal__pv__PolarisCannesGuardianExperienceEnabledrelayprovider": True,
                    "__relay_internal__pv__PolarisCASB976ProfileEnabledrelayprovider": False,
                    "__relay_internal__pv__PolarisWebSchoolsEnabledrelayprovider": False,
                    "__relay_internal__pv__PolarisRepostsConsumptionEnabledrelayprovider": False,
                    "__relay_internal__pv__PolarisShortDramaEnabledrelayprovider": False,
                },
            },
        )

    def test_user_short_gql_uses_current_profile_query(self):
        client = self.build_client()

        user = client.user_short_gql("123")

        self.assertIsInstance(user, UserShort)
        self.assertEqual(user.pk, "123")
        self.assertEqual(user.username, "example")
        self.assertTrue(user.is_verified)
        self.assert_current_profile_request(client)

    def test_user_info_v2_gql_uses_current_profile_query(self):
        client = self.build_client()

        user = client.user_info_v2_gql("123")

        self.assertIsInstance(user, User)
        self.assertEqual(user.pk, "123")
        self.assertEqual(user.username, "example")
        self.assertEqual((user.media_count, user.follower_count, user.following_count), (7, 11, 3))
        self.assertTrue(user.is_business)
        self.assertEqual(user.category, "Creator")
        self.assert_current_profile_request(client)
