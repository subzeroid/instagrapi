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
