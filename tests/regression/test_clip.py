from tests.helpers import *


class ClipPinRegressionTestCase(unittest.TestCase):
    def test_clip_info_for_creation_sends_device_status(self):
        client = Client()
        expected = {"status": "ok", "trial_config": {"is_enabled": True}}

        with mock.patch.object(
            client,
            "private_request",
            return_value=expected,
        ) as private_request:
            result = client.clip_info_for_creation()

        self.assertEqual(result, expected)
        private_request.assert_called_once()
        self.assertEqual(private_request.call_args.args[0], "clips/clips_info_for_creation/")
        device_status = json.loads(private_request.call_args.kwargs["params"]["device_status"])
        self.assertEqual(device_status["chip_vendor"], "others")
        self.assertFalse(device_status["hw_av1_dec"])

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
