from tests.helpers import *


class ClipPinRegressionTestCase(unittest.TestCase):
    def test_clip_seen_posts_write_seen_state_payload(self):
        client = Client()
        client.private.cookies.set("ds_user_id", "29060001803")
        client.uuid = "uuid"

        with mock.patch.object(client, "private_request", return_value={"status": "ok"}) as private_request:
            result = client.clip_seen(
                ["3917361171492779700_25025320", "3917361171492779701"],
                blend_media_ids=["3917361171492779702_25025320"],
            )

        self.assertTrue(result)
        private_request.assert_called_once()
        self.assertEqual(private_request.call_args.args[0], "clips/write_seen_state/")
        payload = private_request.call_args.kwargs["data"]
        self.assertEqual(json.loads(payload["impressions"]), ["3917361171492779700", "3917361171492779701"])
        self.assertEqual(json.loads(payload["blend_impressions"]), ["3917361171492779702"])
        self.assertEqual(payload["_uid"], "29060001803")
        self.assertEqual(payload["_uuid"], "uuid")

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

    def test_clip_mashup_info_posts_media_id_and_identity(self):
        client = Client()
        client.private.cookies.set("ds_user_id", "29060001803")
        client.uuid = "uuid"
        expected = {
            "mashup_info": {
                "is_reuse_allowed": True,
                "mashups_allowed": True,
            },
            "status": "ok",
        }

        with mock.patch.object(client, "private_request", return_value=expected) as private_request:
            result = client.clip_mashup_info("3894040329476845448")

        self.assertEqual(result, expected)
        private_request.assert_called_once_with(
            "clips/get_mashup_info_for_media/",
            data={
                "media_id": "3894040329476845448",
                "_uid": "29060001803",
                "_uuid": "uuid",
            },
        )

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

    def test_clip_change_cover_uploads_photo_and_configures_reel_cover(self):
        client = Client()
        with mock.patch.object(client, "photo_rupload", return_value=("1778346423000", 720, 1280)) as photo_rupload:
            with mock.patch.object(
                client,
                "private_request",
                return_value={"success": True, "status": "ok"},
            ) as private_request:
                result = client.clip_change_cover("3914574283211484216", Path("cover.jpg"))

        self.assertTrue(result)
        photo_rupload.assert_called_once_with(Path("cover.jpg"))
        private_request.assert_called_once_with(
            "media/configure_to_clips_cover_image/",
            data={"upload_id": "1778346423000", "clips_media_id": "3914574283211484216"},
        )
