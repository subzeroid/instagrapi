from tests.helpers import *


class HashtagRegressionTestCase(unittest.TestCase):
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
