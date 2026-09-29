from copy import deepcopy

from pydantic import ValidationError

from instagrapi.extractors import extract_highlight_v1
from instagrapi.types import UserShort
from tests.helpers import *


class HighlightAmountRegressionTestCase(unittest.TestCase):
    @staticmethod
    def valid_highlight(number):
        return {
            "id": f"highlight:{number}",
            "latest_reel_media": 0,
            "cover_media": {},
            "user": {"pk": "123"},
            "title": f"Highlight {number}",
            "created_at": 0,
            "is_pinned_highlight": False,
            "media_count": 0,
            "media_ids": [],
            "items": [],
        }

    def test_user_highlights_amount_preserves_source_order_and_limits_results(self):
        client = Client()
        tray = [self.valid_highlight(number) for number in range(4)]
        with mock.patch.object(client, "private_request", return_value={"tray": tray}):
            for method in (client.user_highlights_v1, client.user_highlights):
                for amount, expected in ((0, 4), (1, 1), (3, 3), (4, 4), (99, 4), (-1, 4), ("1", 1)):
                    highlights = method("123", amount=amount)
                    self.assertEqual(len(highlights), expected)
                    self.assertEqual(
                        [highlight.pk for highlight in highlights], [str(number) for number in range(expected)]
                    )

    def test_user_highlights_amount_handles_empty_and_missing_trays(self):
        client = Client()
        for result in ({"tray": []}, {}):
            with mock.patch.object(client, "private_request", return_value=result):
                for method in (client.user_highlights_v1, client.user_highlights):
                    self.assertEqual(method("123", amount=1), [])

    def test_positive_amount_does_not_extract_discarded_malformed_tail(self):
        client = Client()
        result = {"tray": [self.valid_highlight(1), {"id": "malformed"}]}
        with mock.patch.object(client, "private_request", return_value=result):
            self.assertEqual(client.user_highlights_v1("123", amount=1)[0].pk, "1")
            self.assertEqual(client.user_highlights("123", amount=1)[0].pk, "1")

        with mock.patch.object(client, "private_request", return_value=result):
            with self.assertRaises(IndexError):
                client.user_highlights_v1("123", amount=0)

    def test_highlight_info_normalizes_owner_friendship_status(self):
        client = Client()
        raw = self.valid_highlight(1)
        raw["user"]["friendship_status"] = {
            "following": True,
            "incoming_request": False,
            "is_bestie": False,
            "is_feed_favorite": False,
            "is_private": True,
            "is_restricted": False,
            "outgoing_request": False,
        }
        response = {"reels": {raw["id"]: raw}}
        with mock.patch.object(client, "private_request", return_value=response):
            highlight = client.highlight_info("1")
        self.assertEqual(highlight.user.friendship_status.user_id, "123")
        self.assertTrue(highlight.user.friendship_status.following)
        self.assertTrue(highlight.user.friendship_status.is_private)
        self.assertFalse(highlight.user.friendship_status.outgoing_request)


class HighlightOwnerRegressionTestCase(unittest.TestCase):
    def test_extract_highlight_normalizes_owner_without_mutating_response(self):
        for id_field, user_id in (("pk", "123"), ("pk", 123), ("id", "123")):
            with self.subTest(id_field=id_field, user_id=user_id):
                raw = HighlightAmountRegressionTestCase.valid_highlight(1)
                raw["user"] = {id_field: user_id, "friendship_status": {"following": True}}
                raw["media_count"] = 2
                raw["items"] = [
                    {
                        "pk": str(number),
                        "id": f"{number}_456",
                        "taken_at": 1,
                        "media_type": 1,
                        "user": {"pk": "456", "friendship_status": {"following": False}},
                    }
                    for number in (3, 2)
                ]
                original = deepcopy(raw)
                highlight = extract_highlight_v1(raw)
                self.assertEqual(highlight.pk, "1")
                self.assertEqual(highlight.user.pk, "123")
                self.assertEqual(highlight.user.friendship_status.user_id, "123")
                self.assertTrue(highlight.user.friendship_status.following)
                self.assertEqual([story.pk for story in highlight.items], ["3", "2"])
                self.assertEqual([story.user.friendship_status.user_id for story in highlight.items], ["456", "456"])
                self.assertEqual(raw, original)

    def test_extract_highlight_preserves_normalized_owner(self):
        owner = UserShort(
            pk="123",
            friendship_status={
                "user_id": "456",
                "following": True,
                "incoming_request": True,
                "is_bestie": True,
                "is_feed_favorite": True,
                "is_private": True,
                "is_restricted": True,
                "outgoing_request": True,
            },
        )
        for user in (owner, owner.model_dump()):
            with self.subTest(user_type=type(user).__name__):
                raw = HighlightAmountRegressionTestCase.valid_highlight(1)
                raw["user"] = user
                self.assertEqual(extract_highlight_v1(raw).user.model_dump(), owner.model_dump())

    def test_extract_highlight_still_requires_owner(self):
        for missing in (True, False):
            with self.subTest(missing=missing):
                raw = HighlightAmountRegressionTestCase.valid_highlight(1)
                if missing:
                    del raw["user"]
                else:
                    raw["user"] = None
                with self.assertRaises(ValidationError):
                    extract_highlight_v1(raw)

    def test_extract_highlight_rejects_owner_without_identifier(self):
        for owner in ({}, {"username": "example"}):
            with self.subTest(owner=owner):
                raw = HighlightAmountRegressionTestCase.valid_highlight(1)
                raw["user"] = owner
                with self.assertRaises(AssertionError):
                    extract_highlight_v1(raw)
