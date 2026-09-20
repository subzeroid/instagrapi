from copy import deepcopy
from unittest import TestCase, mock

from instagrapi import Client
from instagrapi.extractors import extract_media_v1
from instagrapi.types import Media, UserShort


def media_payload():
    return {
        "pk": "1",
        "id": "1_2",
        "code": "example",
        "taken_at": 1,
        "media_type": 1,
        "crosspost": [],
        "user": {"pk": "2", "username": "owner"},
    }


class MediaCoauthorsRegressionTestCase(TestCase):
    def test_null_coauthors_become_an_empty_list_without_mutating_payload(self):
        payload = media_payload()
        payload["coauthor_producers"] = None
        original = deepcopy(payload)

        media = extract_media_v1(payload)

        self.assertEqual(media.coauthor_producers, [])
        self.assertEqual(payload, original)

    def test_missing_coauthors_remain_an_empty_list(self):
        payload = media_payload()
        original = deepcopy(payload)

        media = extract_media_v1(payload)

        self.assertEqual(media.coauthor_producers, [])
        self.assertEqual(payload, original)

    def test_empty_coauthors_remain_an_empty_list(self):
        payload = media_payload()
        payload["coauthor_producers"] = []
        original = deepcopy(payload)

        media = extract_media_v1(payload)

        self.assertEqual(media.coauthor_producers, [])
        self.assertEqual(payload, original)

    def test_valid_coauthors_preserve_order_and_fields_without_mutating_payload(self):
        payload = media_payload()
        payload["coauthor_producers"] = [
            {"id": "3", "username": "first", "full_name": "First Author", "is_verified": True},
            {"pk": "4", "username": "second", "full_name": "Second Author", "is_verified": False},
        ]
        original = deepcopy(payload)

        media = extract_media_v1(payload)

        self.assertIsInstance(media.coauthor_producers, list)
        self.assertTrue(all(isinstance(user, UserShort) for user in media.coauthor_producers))
        self.assertEqual([user.pk for user in media.coauthor_producers], ["3", "4"])
        self.assertEqual([user.username for user in media.coauthor_producers], ["first", "second"])
        self.assertEqual([user.full_name for user in media.coauthor_producers], ["First Author", "Second Author"])
        self.assertEqual([user.is_verified for user in media.coauthor_producers], [True, False])
        self.assertEqual(payload, original)

    def test_false_coauthors_are_not_silently_normalized(self):
        payload = media_payload()
        payload["coauthor_producers"] = False
        original = deepcopy(payload)

        with self.assertRaises(TypeError):
            extract_media_v1(payload)

        self.assertEqual(payload, original)


class MediaCoauthorsTimelineRegressionTestCase(TestCase):
    def test_user_medias_gql_accepts_null_coauthors_without_mutating_timeline(self):
        client = Client()
        for session in (client.public, client.private, client.graphql):
            self.addCleanup(session.close)
        payload = media_payload()
        payload.pop("pk")
        payload["id"] = "1"
        payload["1ltaken_at"] = payload.pop("taken_at")
        payload["coauthor_producers"] = None
        response = {
            "data": {
                "xdt_api__v1__profile_timeline": {
                    "profile_grid_items": [{"media": payload}],
                    "more_available": False,
                }
            }
        }
        original = deepcopy(response)
        client.private_graphql_request = mock.Mock(return_value=response)
        client._user_medias_paginated_public_gql = mock.Mock(
            side_effect=AssertionError("The app timeline should not require a public fallback")
        )

        medias = client.user_medias_gql("2", amount=1)

        self.assertEqual(len(medias), 1)
        self.assertIsInstance(medias[0], Media)
        self.assertEqual(medias[0].id, "1_2")
        self.assertEqual(medias[0].coauthor_producers, [])
        self.assertEqual(response, original)
