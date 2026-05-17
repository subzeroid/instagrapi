from instagrapi.exceptions import ClientNotFoundError
from tests.helpers import *


class HashtagRegressionTestCase(unittest.TestCase):
    def test_hashtag_info_a1_falls_back_to_private_when_public_page_is_gone(self):
        client = Client()
        hashtag = Hashtag(id="1", name="pizza")
        client.public_a1_request = Mock(side_effect=ClientNotFoundError("gone"))
        client.hashtag_info_v1 = Mock(return_value=hashtag)

        result = client.hashtag_info_a1("pizza")

        self.assertEqual(result, hashtag)
        client.public_a1_request.assert_called_once()
        client.hashtag_info_v1.assert_called_once_with("pizza")

    def test_hashtag_medias_a1_chunk_falls_back_to_private_when_public_page_is_gone(self):
        client = Client()
        client.public_a1_request = Mock(side_effect=ClientNotFoundError("gone"))
        client.hashtag_medias_v1_chunk = Mock(return_value=(["media"], "cursor"))

        medias, cursor = client.hashtag_medias_a1_chunk("pizza", max_amount=2, tab_key="recent")

        self.assertEqual(medias, ["media"])
        self.assertEqual(cursor, "cursor")
        client.public_a1_request.assert_called_once()
        client.hashtag_medias_v1_chunk.assert_called_once_with("pizza", 2, "recent", None)

    def test_hashtag_medias_a1_chunk_falls_back_to_private_when_public_page_is_short(self):
        client = Client()
        client.public_a1_request = Mock(return_value={"data": {"recent": {"sections": [], "more_available": False}}})
        client.hashtag_medias_v1_chunk = Mock(return_value=(["media"], "cursor"))

        medias, cursor = client.hashtag_medias_a1_chunk("pizza", max_amount=2, tab_key="recent")

        self.assertEqual(medias, ["media"])
        self.assertEqual(cursor, "cursor")
        client.hashtag_medias_v1_chunk.assert_called_once_with("pizza", 2, "recent", None)

    def test_hashtag_medias_a1_uses_full_private_fallback_when_chunk_is_short(self):
        client = Client()
        client.hashtag_medias_a1_chunk = Mock(return_value=(["media"], "cursor"))
        client.hashtag_medias_v1 = Mock(return_value=["media", "media2"])

        medias = client.hashtag_medias_a1("pizza", amount=2, tab_key="recent")

        self.assertEqual(medias, ["media", "media2"])
        client.hashtag_medias_v1.assert_called_once_with("pizza", 2, "recent")

    def test_hashtag_medias_recent_strips_leading_hash_and_warns(self):
        client = Client()
        client.hashtag_medias_recent_a1 = Mock(return_value=["media"])

        with self.assertWarnsRegex(UserWarning, "leading '#'"):
            medias = client.hashtag_medias_recent("#pizza", amount=1)

        self.assertEqual(medias, ["media"])
        client.hashtag_medias_recent_a1.assert_called_once_with("pizza", 1)

    def test_hashtag_name_cannot_be_empty_after_normalization(self):
        client = Client()

        with self.assertRaisesRegex(ValueError, "Hashtag name cannot be empty"):
            client.hashtag_medias_recent("#")
