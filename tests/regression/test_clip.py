from tests.helpers import *


class ClipPinRegressionTestCase(unittest.TestCase):
    def test_clip_pin_uses_reels_grid_payload(self):
        client = Client()
        with mock.patch.object(
            client,
            "private_request",
            return_value={"status": "ok"},
        ) as private_request:
            result = client.clip_pin("3894040329476845448")

        self.assertTrue(result)
        private_request.assert_called_once_with(
            "users/pin_timeline_media/",
            data={"post_id": "3894040329476845448", "profile_grid": "clips"},
        )

    def test_clip_unpin_uses_reels_grid_payload(self):
        client = Client()
        with mock.patch.object(
            client,
            "private_request",
            return_value={"status": "ok"},
        ) as private_request:
            result = client.clip_unpin("3894040329476845448")

        self.assertTrue(result)
        private_request.assert_called_once_with(
            "users/unpin_timeline_media/",
            data={"post_id": "3894040329476845448", "profile_grid": "clips"},
        )

    def test_clip_pin_revert_unpins_reels_grid(self):
        client = Client()
        with mock.patch.object(
            client,
            "private_request",
            return_value={"status": "ok"},
        ) as private_request:
            result = client.clip_pin("3894040329476845448", revert=True)

        self.assertTrue(result)
        private_request.assert_called_once_with(
            "users/unpin_timeline_media/",
            data={"post_id": "3894040329476845448", "profile_grid": "clips"},
        )
