from tests.helpers import *


class HashtagRegressionTestCase(unittest.TestCase):
    def test_dead_public_a1_methods_are_removed(self):
        client = Client()
        removed_methods = (
            "public_a1_request",
            "public_a1_request_user_info_by_username",
            "media_info_a1",
            "user_info_by_username_a1",
            "location_info_a1",
            "location_medias_a1_chunk",
            "location_medias_a1",
            "location_medias_top_a1",
            "location_medias_recent_a1",
            "hashtag_info_a1",
            "hashtag_medias_a1_chunk",
            "hashtag_medias_a1",
            "hashtag_medias_top_a1",
            "hashtag_medias_recent_a1",
            "hashtag_related_hashtags",
        )

        for method_name in removed_methods:
            self.assertFalse(hasattr(client, method_name), method_name)

    def test_hashtag_medias_recent_strips_leading_hash_and_warns(self):
        client = Client()
        client.hashtag_medias_recent_v1 = Mock(return_value=["media"])

        with self.assertWarnsRegex(UserWarning, "leading '#'"):
            medias = client.hashtag_medias_recent("#pizza", amount=1)

        self.assertEqual(medias, ["media"])
        client.hashtag_medias_recent_v1.assert_called_once_with("pizza", 1)

    def test_hashtag_name_cannot_be_empty_after_normalization(self):
        client = Client()

        with self.assertRaisesRegex(ValueError, "Hashtag name cannot be empty"):
            client.hashtag_medias_recent("#")
