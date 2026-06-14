from tests.helpers import *


class CollectionRegressionTestCase(unittest.TestCase):
    @staticmethod
    def build_media_payload(pk="1", code="abc"):
        return {
            "pk": pk,
            "id": f"{pk}_1",
            "code": code,
            "taken_at": 1710000000,
            "media_type": 1,
            "caption": {"text": "caption"},
            "user": {
                "pk": "1",
                "username": "example",
                "profile_pic_url": "https://example.com/profile.jpg",
            },
            "image_versions2": {
                "candidates": [
                    {
                        "url": "https://example.com/thumbnail.jpg",
                        "width": 720,
                        "height": 1280,
                    }
                ]
            },
        }

    def test_collections_uses_max_id_cursor_fallback(self):
        client = Client()
        client.private_request = Mock(
            side_effect=[
                {
                    "items": [
                        {
                            "collection_id": "1",
                            "collection_name": "First",
                            "collection_type": "MEDIA",
                            "collection_media_count": 1,
                        }
                    ],
                    "more_available": True,
                    "max_id": "cursor-2",
                },
                {
                    "items": [
                        {
                            "collection_id": "2",
                            "collection_name": "Second",
                            "collection_type": "MEDIA",
                            "collection_media_count": 1,
                        }
                    ],
                    "more_available": False,
                },
            ]
        )

        collections = client.collections()

        self.assertEqual([collection.id for collection in collections], ["1", "2"])
        self.assertEqual(client.private_request.call_count, 2)
        self.assertEqual(client.private_request.call_args_list[0].kwargs["params"]["max_id"], "")
        self.assertEqual(client.private_request.call_args_list[1].kwargs["params"]["max_id"], "cursor-2")

    def test_collection_medias_chunk_uses_max_id_cursor_fallback(self):
        client = Client()
        client.private_request = Mock(
            return_value={
                "items": [{"media": self.build_media_payload()}],
                "max_id": "cursor-2",
            }
        )

        medias, next_max_id = client.collection_medias_v1_chunk("123")

        self.assertEqual([media.pk for media in medias], ["1"])
        self.assertEqual(next_max_id, "cursor-2")

    def test_collection_medias_uses_max_id_cursor_fallback_for_pagination(self):
        client = Client()
        client.private_request = Mock(
            side_effect=[
                {
                    "items": [{"media": self.build_media_payload(pk="1", code="abc")}],
                    "max_id": "cursor-2",
                },
                {
                    "items": [{"media": self.build_media_payload(pk="2", code="def")}],
                },
            ]
        )

        medias = client.collection_medias("123", amount=2)

        self.assertEqual([media.pk for media in medias], ["1", "2"])
        self.assertEqual(client.private_request.call_count, 2)
        self.assertNotIn("max_id", client.private_request.call_args_list[0].kwargs["params"])
        self.assertEqual(client.private_request.call_args_list[1].kwargs["params"]["max_id"], "cursor-2")
