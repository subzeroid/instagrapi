import unittest
from unittest.mock import Mock

from instagrapi import Client
from instagrapi.exceptions import ClientGraphqlError


class RelatedProfileSessionTestCase(unittest.TestCase):
    def setUp(self):
        self.client = Client()

    def tearDown(self):
        self.client.public.close()

    def response(self):
        return {
            "status": "ok",
            "data": {
                "user": {
                    "edge_chaining": {
                        "edges": [
                            {
                                "node": {
                                    "id": "2",
                                    "username": "example",
                                    "is_private": False,
                                    "profile_pic_url": "https://example.com/avatar.jpg",
                                }
                            }
                        ]
                    }
                }
            },
        }

    def check_related_cookie(self, expected):
        def request(*args, **kwargs):
            self.assertEqual(self.client.public.cookies.get("sessionid"), expected)
            return self.response()

        self.client.public_request = Mock(side_effect=request)
        users = self.client.user_related_profiles_gql("2")
        self.assertEqual([user.username for user in users], ["example"])
        self.client.public_request.assert_called_once()

    def test_first_related_lookup_uses_saved_authorization(self):
        self.client.authorization_data = {"ds_user_id": "1", "sessionid": "saved-session"}
        self.assertIsNone(self.client.public.cookies.get("sessionid"))
        self.check_related_cookie("saved-session")

    def test_private_cookie_replaces_stale_public_session(self):
        self.client.private.cookies.set("sessionid", "current-session")
        self.client.public.cookies.set("sessionid", "stale-session")
        self.check_related_cookie("current-session")

    def test_without_private_session_preserves_existing_public_cookie(self):
        self.client.public.cookies.set("sessionid", "public-session")
        self.check_related_cookie("public-session")

    def test_anonymous_related_lookup_remains_available(self):
        self.check_related_cookie(None)

    def test_related_error_is_not_retried_or_replaced(self):
        error = ClientGraphqlError("unavailable")
        self.client.public_request = Mock(side_effect=error)
        with self.assertRaises(ClientGraphqlError) as raised:
            self.client.user_related_profiles_gql("2")
        self.assertIs(raised.exception, error)
        self.client.public_request.assert_called_once()

    def test_generic_legacy_graphql_remains_anonymous(self):
        self.client.authorization_data = {"ds_user_id": "1", "sessionid": "saved-session"}
        self.client.public_request = Mock(return_value=self.response())
        self.client.public_graphql_request({"id": "2"}, query_hash="query-placeholder")
        self.assertIsNone(self.client.public.cookies.get("sessionid"))
