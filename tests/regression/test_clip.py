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
        self.assertNotIn("progress_impressions", payload)

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

    def test_clip_seen_posts_reported_progress(self):
        client = Client()
        client.private.cookies.set("ds_user_id", "42")
        with (
            mock.patch.object(client, "private_request", return_value={"status": "ok"}) as private_request,
            mock.patch("instagrapi.mixins.clip.time.time", return_value=1_700_000_000.125),
        ):
            result = client.clip_seen(
                ["3917361171492779700_25025320"],
                ["3917361171492779701"],
                progress=[
                    ("3917361171492779700_25025320", 1_000),
                    ("3917361171492779701", 2**31),
                    ("3917361171492779702", 1_234),
                    ("3917361171492779700_25025320", 0),
                ],
            )

        assert result is True
        private_request.assert_called_once()
        assert private_request.call_args.args == ("clips/write_seen_state/",)
        data = private_request.call_args.kwargs["data"]
        assert json.loads(data["impressions"]) == ["3917361171492779700"]
        assert json.loads(data["blend_impressions"]) == ["3917361171492779701"]
        expected = [
            {"media_id": "3917361171492779700_25025320", "position_ms": 0, "updated_at_ms": 1_700_000_000_125},
            {"media_id": "3917361171492779701", "position_ms": 2**31 - 1, "updated_at_ms": 1_700_000_000_125},
            {"media_id": "3917361171492779702", "position_ms": 1_234, "updated_at_ms": 1_700_000_000_125},
        ]
        assert data["progress_impressions"] == json.dumps(expected, separators=(",", ":"))

    def test_clip_seen_omits_empty_progress(self):
        client = Client()
        client.private.cookies.set("ds_user_id", "42")
        with mock.patch.object(client, "private_request", return_value={"status": "ok"}) as private_request:
            assert client.clip_seen(["3917361171492779700"], progress=[])

        assert "progress_impressions" not in private_request.call_args.kwargs["data"]

    def test_clip_seen_rejects_invalid_progress_before_dispatch(self):
        client = Client()
        client.private.cookies.set("ds_user_id", "42")
        with mock.patch.object(client, "private_request") as private_request:
            for row in (
                ("", 0),
                (12, 0),
                ("3917361171492779700", -1),
                ("3917361171492779700", 1.5),
                ("3917361171492779700", True),
            ):
                with self.subTest(row=row), self.assertRaises(ValueError):
                    client.clip_seen([], progress=[row])

        private_request.assert_not_called()

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


class ClipConfigurePayloadRegressionTestCase(unittest.TestCase):
    def test_clip_configure_payload_matches_current_app_shape(self):
        client = Client()
        with mock.patch.object(client, "photo_rupload", return_value=("1778346423000", 1080, 1920)):
            with mock.patch.object(
                client,
                "private_request",
                return_value={"status": "ok"},
            ) as private_request:
                client.clip_configure(
                    "1778346423000",
                    Path("thumbnail.jpg"),
                    1080,
                    1920,
                    5,
                    "caption",
                )

        private_request.assert_called_once()
        self.assertEqual(private_request.call_args.args[0], "media/configure_to_clips/?video=1")
        payload = private_request.call_args.args[1]

        segments_metadata = payload["clips_segments_metadata"]
        self.assertEqual(segments_metadata["num_segments"], 1)
        segment = segments_metadata["clips_segments"][0]
        self.assertEqual(segment["index"], 0)
        self.assertEqual(segment["duration_ms"], 5000)
        self.assertEqual(segment["audio_type"], "original")
        self.assertEqual(segment["media_type"], "video")
        self.assertEqual(segment["original_media_type"], 2)

        self.assertEqual(payload["clips_audio_metadata"]["original"]["volume_level"], 1.0)

        self.assertEqual(payload["additional_audio_info"], {"has_voiceover_attribution": 0})
        self.assertEqual(payload["edits"], {"filter_type": 0, "filter_strength": 1.0})
        self.assertEqual(payload["capture_type"], "clips_v2")
        self.assertEqual(payload["clips_creation_entry_point"], "clips")
        self.assertEqual(payload["camera_entry_point"], "71")
        self.assertEqual(payload["audience"], "default")
        self.assertEqual(payload["include_e2ee_mentioned_user_list"], "1")
        self.assertEqual(payload["hide_from_profile_grid"], "false")
        self.assertEqual(payload["original_width"], 1080)
        self.assertEqual(payload["original_height"], 1920)

        for legacy_key in ("media_folder", "date_time_original", "clips"):
            self.assertNotIn(legacy_key, payload)
