from tests import helpers as _helpers
from tests.helpers import *


class ClientTimelineLiveTestCase(_helpers.ClientPrivateTestCase):
    def test_friends_reels_live_endpoint(self):
        result = self.cl.private_request(
            "clips/discover/social/",
            data=" ",
            params={"max_id": ""},
        )

        self.assertEqual(result.get("status"), "ok")
        self.assertIn("items", result)
        self.assertIn("paging_info", result)
        self.assertIsInstance(result["items"], list)

        medias = self.cl.friends_reels(amount=3)

        self.assertIsInstance(medias, list)
        for media in medias:
            self.assertIsInstance(media, Media)
