from instagrapi.extractors import extract_media_v1
from tests.helpers import *


class UploadRegressionTestCase(unittest.TestCase):
    def build_client(self):
        client = Client()
        client.settings = {}
        client._user_id = "1"
        client.uuid = "uuid"
        client.android_device_id = "device"
        client.client_session_id = "client-session"
        client.timezone_offset = 0
        client.last_json = {}
        client.last_response = None
        client.set_device({})
        client.with_default_data = lambda data: data
        client.request_log = lambda response: None
        client.expose = lambda: None
        return client

    def build_media_payload(self, media_type=2):
        payload = {
            "pk": "1",
            "id": "1_1",
            "code": "abc",
            "taken_at": 1710000000,
            "media_type": media_type,
            "caption": {"text": "caption"},
            "user": {
                "pk": "1",
                "username": "example",
                "profile_pic_url": "https://example.com/profile.jpg",
            },
            "like_count": 0,
        }
        if media_type == 2:
            payload["video_versions"] = [
                {
                    "url": "https://example.com/video.mp4",
                    "width": 720,
                    "height": 1280,
                }
            ]
            payload["image_versions2"] = {
                "candidates": [
                    {
                        "url": "https://example.com/thumbnail.jpg",
                        "width": 720,
                        "height": 1280,
                    }
                ]
            }
        else:
            payload["image_versions2"] = {
                "candidates": [
                    {
                        "url": "https://example.com/photo.jpg",
                        "width": 720,
                        "height": 720,
                    }
                ]
            }
        return payload

    def build_story(self, story_pk="10", media_type=1):
        return Story(
            pk=str(story_pk),
            id=f"{story_pk}_1",
            code=f"story{story_pk}",
            taken_at=datetime.now(UTC()),
            media_type=media_type,
            product_type="story",
            thumbnail_url="https://example.com/story.jpg",
            user=UserShort(
                pk="1",
                username="example",
                profile_pic_url="https://example.com/profile.jpg",
            ),
            sponsor_tags=[],
            mentions=[],
            links=[],
            hashtags=[],
            locations=[],
            stickers=[],
        )

    def test_clip_share_to_fb_config_requests_reel_facebook_config(self):
        client = self.build_client()
        expected = {"status": "ok", "eligible": True}

        with mock.patch.object(client, "private_request", return_value=expected) as private_request:
            result = client.clip_share_to_fb_config()

        private_request.assert_called_once()
        endpoint = private_request.call_args.args[0]
        params = private_request.call_args.kwargs["params"]
        self.assertEqual(endpoint, "clips/user/share_to_fb_config/")
        device_status = json.loads(params["device_status"])
        self.assertEqual(device_status["chip_vendor"], "others")
        self.assertFalse(device_status["hw_av1_dec"])
        self.assertEqual(result, expected)

    def test_clip_share_to_fb_extra_data_builds_current_reel_crosspost_payload(self):
        client = self.build_client()
        config = {
            "enabled": True,
            "is_account_linked": True,
            "reels_share_to_facebook": True,
            "reels_destination_id": "fb-destination-id",
            "posting_type": "USER",
            "reels_cross_app_share_type": "CROSSPOST",
            "reels_cross_app_share_fb_validation_check_bypass": True,
            "status": "ok",
        }

        result = client.clip_share_to_fb_extra_data(config=config, attempt_id="attempt-id")

        self.assertEqual(
            result,
            {
                "share_to_facebook": "1",
                "is_reel_shared_to_fb": True,
                "share_to_facebook_reels": True,
                "share_to_fb_destination_id": "fb-destination-id",
                "share_to_fb_destination_type": "USER",
                "cross_app_share_fb_validation_check_bypass": True,
                "xpost_surface": "IG_REELS_COMPOSER",
                "no_token_crosspost": "1",
                "attempt_id": "attempt-id",
            },
        )

    def test_clip_share_to_fb_extra_data_allows_explicit_destination_when_preflight_is_unavailable(self):
        client = self.build_client()

        result = client.clip_share_to_fb_extra_data(
            config={
                "share_to_fb_unavailable": True,
                "status": "ok",
            },
            destination_id="fb-destination-id",
            destination_type="USER",
            attempt_id="attempt-id",
        )

        self.assertEqual(result["share_to_fb_destination_id"], "fb-destination-id")
        self.assertEqual(result["share_to_fb_destination_type"], "USER")
        self.assertEqual(result["attempt_id"], "attempt-id")

    def test_clip_share_to_fb_extra_data_allows_config_destination_when_preflight_is_unavailable(self):
        client = self.build_client()

        result = client.clip_share_to_fb_extra_data(
            config={
                "share_to_fb_unavailable": True,
                "reels_destination_id": "fb-destination-id",
                "posting_type": "PAGE",
                "status": "ok",
            },
            attempt_id="attempt-id",
        )

        self.assertEqual(result["share_to_fb_destination_id"], "fb-destination-id")
        self.assertEqual(result["share_to_fb_destination_type"], "PAGE")

    def test_clip_share_to_fb_extra_data_does_not_use_cross_app_share_type_as_destination_type(self):
        client = self.build_client()

        with self.assertRaises(ClientError) as ctx:
            client.clip_share_to_fb_extra_data(
                config={
                    "enabled": True,
                    "is_account_linked": True,
                    "reels_destination_id": "fb-destination-id",
                    "reels_cross_app_share_type": "CROSSPOST",
                    "status": "ok",
                }
            )

        self.assertIn("destination type", str(ctx.exception))

    def test_clip_share_to_fb_extra_data_raises_without_destination(self):
        client = self.build_client()

        with self.assertRaises(ClientError) as ctx:
            client.clip_share_to_fb_extra_data(
                config={
                    "enabled": True,
                    "default_share_to_fb_enabled": False,
                    "status": "ok",
                }
            )

        self.assertIn("Facebook Reel sharing configuration has no destination", str(ctx.exception))

    def test_clip_info_for_creation_requests_reel_creation_config(self):
        client = self.build_client()
        expected = {
            "trial_config": {"is_enabled": True},
            "auto_reshare_to_story_config": {
                "is_enabled_for_reels": False,
                "is_enabled_for_feed_posts": False,
            },
            "status": "ok",
        }

        with mock.patch.object(client, "private_request", return_value=expected) as private_request:
            result = client.clip_info_for_creation()

        private_request.assert_called_once()
        self.assertEqual(private_request.call_args.args[0], "clips/clips_info_for_creation/")
        device_status = json.loads(private_request.call_args.kwargs["params"]["device_status"])
        self.assertEqual(device_status["chip_vendor"], "others")
        self.assertFalse(device_status["hw_av1_dec"])
        self.assertEqual(result, expected)

    def test_clip_trial_eligible_reads_creation_trial_config(self):
        client = self.build_client()

        with mock.patch.object(
            client,
            "clip_info_for_creation",
            return_value={"trial_config": {"is_enabled": True}, "status": "ok"},
        ):
            self.assertTrue(client.clip_trial_eligible())

    def test_clip_trial_eligible_returns_false_when_creation_trial_config_is_missing(self):
        client = self.build_client()

        with mock.patch.object(client, "clip_info_for_creation", return_value={"status": "ok"}):
            self.assertFalse(client.clip_trial_eligible())

    def test_photo_upload_falls_back_to_recent_media_when_configure_has_no_media(self):
        client = self.build_client()
        existing_media = extract_media_v1(self.build_media_payload(media_type=1))
        uploaded_media = extract_media_v1(dict(self.build_media_payload(media_type=1), pk="2", id="2_1", code="def"))

        with mock.patch.object(client, "photo_rupload", return_value=("1", 720, 720)):
            with mock.patch.object(client, "photo_configure", return_value={"status": "ok"}):
                with mock.patch.object(
                    client, "user_medias_v1", side_effect=[[existing_media], [uploaded_media, existing_media]]
                ):
                    with mock.patch("time.sleep"):
                        media = client.photo_upload(Path("example.jpg"), "caption")

        self.assertEqual(media.id, uploaded_media.id)

    def test_photo_upload_raises_clear_error_when_configure_has_no_media_and_recent_media_missing(self):
        client = self.build_client()

        with mock.patch.object(client, "photo_rupload", return_value=("1", 720, 720)):
            with mock.patch.object(client, "photo_configure", return_value={"status": "ok"}):
                with mock.patch.object(client, "user_medias_v1", return_value=[]):
                    with mock.patch("time.sleep"):
                        with self.assertRaises(PhotoConfigureError) as ctx:
                            client.photo_upload(Path("example.jpg"), "caption")

        self.assertIn("without media payload and uploaded media was not visible", str(ctx.exception))

    def test_photo_upload_extracts_configure_media_when_expose_overwrites_last_json(self):
        client = self.build_client()
        media_payload = self.build_media_payload(media_type=1)

        def expose():
            client.last_json = {"status": "ok"}
            return client.last_json

        client.expose = expose
        with mock.patch.object(client, "photo_rupload", return_value=("1", 720, 720)):
            with mock.patch.object(client, "photo_configure", return_value={"status": "ok", "media": media_payload}):
                with mock.patch("time.sleep"):
                    media = client.photo_upload(Path("example.jpg"), "caption")

        self.assertIsInstance(media, Media)
        self.assertEqual(media.pk, "1")

    def test_video_upload_raises_clear_error_when_configure_has_no_media(self):
        client = self.build_client()

        with mock.patch.object(
            client,
            "video_rupload",
            return_value=("1", 720, 1280, 5, Path("/tmp/thumb.jpg")),
        ):
            with mock.patch.object(client, "video_configure", return_value={"status": "ok"}):
                with mock.patch("time.sleep"):
                    with self.assertRaises(VideoConfigureError) as ctx:
                        client.video_upload(Path("example.mp4"), "caption")

        self.assertIn("without media payload", str(ctx.exception))

    def test_album_upload_raises_clear_error_when_configure_has_no_media(self):
        client = self.build_client()

        with mock.patch.object(client, "photo_rupload", return_value=("1", 720, 720)):
            with mock.patch.object(client, "album_configure", return_value={"status": "ok"}):
                with mock.patch("time.sleep"):
                    with self.assertRaises(AlbumConfigureError) as ctx:
                        client.album_upload([Path("one.jpg")], "caption")

        self.assertIn("without media payload", str(ctx.exception))

    def test_album_upload_rejects_empty_paths_with_clear_error(self):
        client = self.build_client()

        with self.assertRaises(PrivateError) as ctx:
            client.album_upload([], "caption")

        self.assertIn("requires at least one media path", str(ctx.exception))

    def test_album_upload_rejects_unknown_format_with_filename_in_error(self):
        client = self.build_client()

        with self.assertRaises(PrivateError) as ctx:
            client.album_upload([Path("clip.mov")], "caption")

        self.assertIn('Unsupported album media format ".mov"', str(ctx.exception))
        self.assertIn("clip.mov", str(ctx.exception))

    def test_album_upload_accepts_png_via_photo_rupload(self):
        client = self.build_client()
        media_payload = self.build_media_payload(media_type=8)
        media_payload["carousel_media"] = [self.build_media_payload(media_type=1)]

        with mock.patch.object(
            client,
            "photo_rupload",
            return_value=("1", 720, 720),
        ) as photo_rupload:
            with mock.patch.object(
                client,
                "album_configure",
                return_value={"status": "ok", "media": media_payload},
            ):
                with mock.patch("time.sleep"):
                    media = client.album_upload([Path("slide.png")], "caption")

        self.assertIsInstance(media, Media)
        photo_rupload.assert_called_once_with(Path("slide.png"), to_album=True)

    def test_album_configure_assigns_nested_usertags_by_carousel_index(self):
        client = self.build_client()
        first_user = UserShort(pk="10", username="first")
        second_user = UserShort(pk="20", username="second")
        children = [{"upload_id": "1"}, {"upload_id": "2"}]

        with mock.patch.object(client, "private_request", return_value={"status": "ok"}) as private_request:
            client.album_configure(
                children,
                "caption",
                usertags=[
                    [Usertag(user=first_user, x=0.25, y=0.75)],
                    [Usertag(user=second_user, x=0.5, y=0.5)],
                ],
            )

        metadata = private_request.call_args.args[1]["children_metadata"]
        first_tags = json.loads(metadata[0]["usertags"])
        second_tags = json.loads(metadata[1]["usertags"])
        self.assertEqual(first_tags, {"in": [{"user_id": "10", "position": [0.25, 0.75]}]})
        self.assertEqual(second_tags, {"in": [{"user_id": "20", "position": [0.5, 0.5]}]})

    def test_album_configure_keeps_flat_usertags_on_first_carousel_item(self):
        client = self.build_client()
        user = UserShort(pk="10", username="first")
        children = [{"upload_id": "1"}, {"upload_id": "2"}]

        with mock.patch.object(client, "private_request", return_value={"status": "ok"}) as private_request:
            client.album_configure(children, "caption", usertags=[Usertag(user=user, x=0.25, y=0.75)])

        metadata = private_request.call_args.args[1]["children_metadata"]
        first_tags = json.loads(metadata[0]["usertags"])
        self.assertEqual(first_tags, {"in": [{"user_id": "10", "position": [0.25, 0.75]}]})
        self.assertNotIn("usertags", metadata[1])

    def test_music_in_feed_audio_browser_requests_feed_music_product(self):
        client = self.build_client()
        expected = {"status": "ok", "alacorn_session_id": "alacorn-1"}

        with mock.patch.object(client, "private_request", return_value=expected) as private_request:
            result = client.music_in_feed_audio_browser(browse_session_id="browse-1")

        self.assertEqual(result, expected)
        private_request.assert_called_once_with(
            "music/music_in_feed_audio_browser/",
            data={
                "product": "music_in_feed",
                "_uuid": "uuid",
                "browse_session_id": "browse-1",
            },
            with_signature=False,
        )

    def test_photo_upload_with_music_adds_music_params_without_mutating_extra_data(self):
        client = self.build_client()
        track = types.SimpleNamespace(
            id="track-id",
            audio_asset_id="asset-id",
            audio_cluster_id="cluster-id",
            highlight_start_times_in_ms=[58000],
            title="Memories",
            display_artist="Justin Lee",
        )
        extra_data = {"share_to_facebook": 1}

        with mock.patch.object(client, "photo_upload", return_value="uploaded") as photo_upload:
            result = client.photo_upload_with_music(
                Path("photo.jpg"),
                "caption",
                track,
                extra_data=extra_data,
                alacorn_session_id="alacorn-1",
            )

        self.assertEqual(result, "uploaded")
        self.assertEqual(extra_data, {"share_to_facebook": 1})
        upload_extra = photo_upload.call_args.kwargs["extra_data"]
        self.assertEqual(upload_extra["share_to_facebook"], 1)
        self.assertEqual(
            upload_extra["music_params"],
            {
                "audio_asset_id": "asset-id",
                "audio_cluster_id": "cluster-id",
                "audio_asset_start_time_in_ms": 58000,
                "derived_content_start_time_in_ms": 0,
                "overlap_duration_in_ms": 30000,
                "browse_session_id": None,
                "product": "music_in_feed",
                "song_name": "Memories",
                "artist_name": "Justin Lee",
                "alacorn_session_id": "alacorn-1",
                "audio_apply_source": 0,
            },
        )

    def test_album_upload_with_music_adds_music_params_without_mutating_extra_data(self):
        client = self.build_client()
        track = {
            "id": "track-id",
            "audio_cluster_id": "cluster-id",
            "highlight_start_times_in_ms": [12000],
            "title": "Album song",
            "display_artist": "Album artist",
        }
        extra_data = {"disable_comments": 1}

        with mock.patch.object(client, "album_upload", return_value="uploaded") as album_upload:
            result = client.album_upload_with_music(
                [Path("one.jpg"), Path("two.jpg")],
                "caption",
                track,
                extra_data=extra_data,
                alacorn_session_id="alacorn-1",
                browse_session_id="browse-1",
                overlap_duration=15000,
            )

        self.assertEqual(result, "uploaded")
        self.assertEqual(extra_data, {"disable_comments": 1})
        upload_extra = album_upload.call_args.kwargs["extra_data"]
        self.assertEqual(upload_extra["disable_comments"], 1)
        self.assertEqual(upload_extra["music_params"]["audio_asset_id"], "track-id")
        self.assertEqual(upload_extra["music_params"]["audio_cluster_id"], "cluster-id")
        self.assertEqual(upload_extra["music_params"]["audio_asset_start_time_in_ms"], 12000)
        self.assertEqual(upload_extra["music_params"]["overlap_duration_in_ms"], 15000)
        self.assertEqual(upload_extra["music_params"]["browse_session_id"], "browse-1")
        self.assertEqual(upload_extra["music_params"]["product"], "music_in_feed")
        self.assertEqual(upload_extra["music_params"]["song_name"], "Album song")
        self.assertEqual(upload_extra["music_params"]["artist_name"], "Album artist")
        self.assertEqual(upload_extra["music_params"]["alacorn_session_id"], "alacorn-1")

    def test_clip_music_extra_data_builds_reels_music_payload_from_dict(self):
        client = self.build_client()
        track = {
            "id": "track-id",
            "audio_cluster_id": "cluster-id",
            "highlight_start_times_in_ms": [40500],
            "title": "Runaway",
            "display_artist": "AURORA",
            "music_canonical_id": "canonical-id",
        }

        result = client.clip_music_extra_data(track, overlap_duration=34000)

        self.assertEqual(
            result["clips_audio_metadata"],
            {
                "original": {"volume_level": 1.0},
                "song": {
                    "volume_level": 1.0,
                    "is_saved": "0",
                    "artist_name": "AURORA",
                    "audio_asset_id": "track-id",
                    "audio_cluster_id": "cluster-id",
                    "track_name": "Runaway",
                    "is_picked_precapture": "1",
                    "music_canonical_id": "canonical-id",
                },
            },
        )
        self.assertEqual(
            result["music_params"],
            {
                "audio_asset_id": "track-id",
                "audio_cluster_id": "cluster-id",
                "audio_asset_start_time_in_ms": 40500,
                "derived_content_start_time_in_ms": 0,
                "overlap_duration_in_ms": 34000,
                "product": "story_camera_clips_v2",
                "song_name": "Runaway",
                "artist_name": "AURORA",
                "alacorn_session_id": "null",
                "music_canonical_id": "canonical-id",
            },
        )

    def test_clip_upload_with_music_adds_reels_music_metadata_without_mutating_extra_data(self):
        client = self.build_client()
        extra_data = {"disable_comments": 1}
        track = types.SimpleNamespace(
            id="track-id",
            audio_cluster_id="cluster-id",
            highlight_start_times_in_ms=[1500],
            title="Track title",
            display_artist="Artist",
        )

        with mock.patch.object(client, "clip_upload", return_value="uploaded") as clip_upload:
            result = client.clip_upload_with_music(
                Path("clip.mp4"),
                "caption",
                track,
                extra_data=extra_data,
                overlap_duration=2500,
            )

        self.assertEqual(result, "uploaded")
        self.assertEqual(extra_data, {"disable_comments": 1})
        clip_upload.assert_called_once()
        self.assertEqual(clip_upload.call_args.args[:2], (Path("clip.mp4"), "caption"))
        upload_extra = clip_upload.call_args.kwargs["extra_data"]
        self.assertEqual(upload_extra["disable_comments"], 1)
        self.assertEqual(upload_extra["music_params"]["audio_asset_id"], "track-id")
        self.assertEqual(upload_extra["music_params"]["audio_cluster_id"], "cluster-id")
        self.assertEqual(upload_extra["music_params"]["audio_asset_start_time_in_ms"], 1500)
        self.assertEqual(upload_extra["music_params"]["overlap_duration_in_ms"], 2500)
        self.assertIn("clips_audio_metadata", upload_extra)

    def test_story_music_extra_data_builds_story_music_payload_from_dict(self):
        client = self.build_client()
        track = {
            "id": "track-id",
            "audio_asset_id": "asset-id",
            "audio_cluster_id": "cluster-id",
            "highlight_start_times_in_ms": [40500],
            "title": "Runaway",
            "display_artist": "AURORA",
            "music_canonical_id": "canonical-id",
        }
        extra_data = {
            "share_to_facebook": "1",
            "edits": {"crop_zoom": 1.0},
        }

        result = client.story_music_extra_data(
            track,
            extra_data=extra_data,
            overlap_duration=34000,
            audio_overlay_uuid="overlay-id",
        )

        self.assertEqual(extra_data, {"share_to_facebook": "1", "edits": {"crop_zoom": 1.0}})
        self.assertEqual(result["share_to_facebook"], "1")
        self.assertEqual(result["edits"]["crop_zoom"], 1.0)
        self.assertEqual(
            json.loads(result["music_burnin_params"]),
            {"asset_fbid": "asset-id", "offset_ms": 40500},
        )
        self.assertEqual(
            result["music_params"],
            {
                "audio_asset_id": "asset-id",
                "audio_cluster_id": "cluster-id",
                "audio_asset_start_time_in_ms": 40500,
                "overlap_duration_in_ms": 34000,
                "product": "story_camera_music_overlay_post_capture",
                "song_name": "Runaway",
                "artist_name": "AURORA",
                "alacorn_session_id": "null",
                "music_canonical_id": "canonical-id",
            },
        )
        self.assertEqual(
            result["edits"]["audio_state_edits"],
            {
                "has_music_sticker": True,
                "is_music_burned_into_video": True,
                "is_video_muted": False,
                "did_user_mute_audio": False,
                "force_play_video_audio": True,
            },
        )
        self.assertEqual(
            result["edits"]["media_audio_overlay_info"],
            {
                "audio_mix_burned_in": True,
                "video_volume": 0.0,
                "media_audio_overlays": [
                    {
                        "audio_asset_id": "asset-id",
                        "audio_overlay_uuid": "overlay-id",
                        "audio_volume": 1.0,
                        "seek_time_ms": 40500,
                        "start_at_time_ms": 0,
                        "audio_duration_ms": 34000,
                        "media_audio_overlay_type": "audio_track",
                    }
                ],
            },
        )

    def test_video_upload_to_story_with_music_muxes_track_and_uploads_story(self):
        client = self.build_client()
        extra_data = {"share_to_facebook": "1"}
        track = {
            "id": "track-id",
            "audio_cluster_id": "cluster-id",
            "highlight_start_times_in_ms": [1500],
            "title": "Story song",
            "display_artist": "Story artist",
            "uri": "https://example.com/track.m4a",
        }
        audio_segments = []
        video_paths_seen = []

        class FakeAudioClip:
            def __init__(self, path):
                self.path = path

            def subclipped(self, start, end):
                audio_segments.append((start, end))
                return self

            def close(self):
                return None

        class FakeVideoClip:
            def __init__(self, path):
                self.path = path
                self.duration = 2.5

            def with_audio(self, audio_clip):
                self.audio_clip = audio_clip
                return self

            def write_videofile(self, path):
                Path(path).write_bytes(b"video")

            def close(self):
                return None

        fake_mp = types.ModuleType("moviepy")
        fake_mp.VideoFileClip = FakeVideoClip
        fake_mp.AudioFileClip = FakeAudioClip

        def upload_side_effect(path, caption="", **kwargs):
            video_paths_seen.append(Path(path))
            self.assertTrue(Path(path).exists())
            return "uploaded"

        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = Path(tmpdir) / "track.m4a"
            audio_path.write_bytes(b"audio")
            with mock.patch.dict("sys.modules", {"moviepy": fake_mp}):
                with mock.patch.object(client, "track_download_by_url", return_value=audio_path) as download:
                    with mock.patch.object(
                        client,
                        "video_upload_to_story",
                        side_effect=upload_side_effect,
                    ) as upload:
                        result = client.video_upload_to_story_with_music(
                            Path("input.mp4"),
                            "caption",
                            track,
                            extra_data=extra_data,
                        )

        self.assertEqual(result, "uploaded")
        self.assertEqual(extra_data, {"share_to_facebook": "1"})
        download.assert_called_once()
        self.assertEqual(download.call_args.args[0], "https://example.com/track.m4a")
        self.assertEqual(audio_segments, [(1.5, 4.0)])
        self.assertEqual(len(video_paths_seen), 1)
        upload.assert_called_once()
        self.assertEqual(upload.call_args.args[:2], (video_paths_seen[0], "caption"))
        upload_extra = upload.call_args.kwargs["extra_data"]
        self.assertEqual(upload_extra["share_to_facebook"], "1")
        self.assertEqual(upload_extra["music_params"]["audio_asset_start_time_in_ms"], 1500)
        self.assertEqual(upload_extra["music_params"]["overlap_duration_in_ms"], 2500)
        self.assertEqual(upload_extra["edits"]["media_audio_overlay_info"]["video_volume"], 0.0)

    def test_photo_upload_to_story_with_music_renders_photo_story_video(self):
        client = self.build_client()
        track = {
            "id": "track-id",
            "audio_cluster_id": "cluster-id",
            "highlight_start_times_in_ms": [0],
            "title": "Photo song",
            "display_artist": "Photo artist",
            "progressive_download_url": "https://example.com/track.m4a",
        }
        audio_segments = []
        image_durations = []
        image_clips = []

        class FakeAudioClip:
            def __init__(self, path):
                self.path = path

            def subclipped(self, start, end):
                audio_segments.append((start, end))
                return self

            def close(self):
                return None

        class FakeImageClip:
            def __init__(self, path):
                self.path = path
                self.duration = None
                self.fps = None
                image_clips.append(self)

            def with_duration(self, duration):
                self.duration = duration
                image_durations.append(duration)
                return self

            def with_audio(self, audio_clip):
                self.audio_clip = audio_clip
                return self

            def write_videofile(self, path):
                Path(path).write_bytes(b"video")

            def close(self):
                return None

        fake_mp = types.ModuleType("moviepy")
        fake_mp.ImageClip = FakeImageClip
        fake_mp.AudioFileClip = FakeAudioClip

        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = Path(tmpdir) / "track.m4a"
            audio_path.write_bytes(b"audio")
            with mock.patch.dict("sys.modules", {"moviepy": fake_mp}):
                with mock.patch.object(client, "track_download_by_url", return_value=audio_path):
                    with mock.patch.object(client, "video_upload_to_story", return_value="uploaded") as upload:
                        result = client.photo_upload_to_story_with_music(
                            Path("story.jpg"),
                            "caption",
                            track,
                            duration=7,
                        )

        self.assertEqual(result, "uploaded")
        self.assertEqual(image_durations, [7])
        self.assertEqual(audio_segments, [(0.0, 7.0)])
        self.assertEqual(image_clips[0].fps, 30)
        self.assertEqual(upload.call_args.kwargs["extra_data"]["music_params"]["overlap_duration_in_ms"], 7000)
        upload.assert_called_once()
        self.assertEqual(upload.call_args.args[1], "caption")

    def test_photo_story_upload_falls_back_to_recent_story_when_configure_has_no_media(self):
        client = self.build_client()
        existing = self.build_story("10")
        uploaded = self.build_story("11")

        with mock.patch.object(client, "photo_rupload", return_value=("1", 720, 1280)):
            with mock.patch.object(client, "photo_configure_to_story", return_value={"status": "ok"}):
                with mock.patch.object(client, "user_stories", side_effect=[[existing], [uploaded, existing]]):
                    with mock.patch("time.sleep"):
                        result = client.photo_upload_to_story(Path("story.jpg"))

        self.assertEqual(result.id, uploaded.id)

    def test_clip_upload_falls_back_to_last_json_media_payload(self):
        client = self.build_client()
        client.last_json = {"media": self.build_media_payload()}
        ok_response = Mock(status_code=200)

        with mock.patch(
            "instagrapi.mixins.clip.analyze_video",
            return_value=(Path("/tmp/thumb.jpg"), 720, 1280, 5),
        ):
            with mock.patch.object(client.private, "get", return_value=ok_response):
                with mock.patch.object(client.private, "post", return_value=ok_response):
                    with mock.patch.object(client, "clip_configure", return_value={"status": "ok"}):
                        with mock.patch("builtins.open", mock.mock_open(read_data=b"video-bytes")):
                            with mock.patch("time.sleep"):
                                media = client.clip_upload(Path("example.mp4"), "caption")

        self.assertIsInstance(media, Media)
        self.assertEqual(str(media.video_url), "https://example.com/video.mp4")

    def test_clip_upload_uses_current_reels_rupload_shape(self):
        client = self.build_client()
        client.last_json = {"media": self.build_media_payload()}
        ok_response = Mock(status_code=200)

        with mock.patch(
            "instagrapi.mixins.clip.analyze_video",
            return_value=(Path("/tmp/thumb.jpg"), 720, 1280, 6.023),
        ):
            with mock.patch("time.time", return_value=1778346423.0):
                with mock.patch.object(client.private, "get", return_value=ok_response) as private_get:
                    with mock.patch.object(
                        client.private,
                        "post",
                        side_effect=[ok_response, ok_response],
                    ) as private_post:
                        with mock.patch.object(client, "clip_configure", return_value={"status": "ok"}):
                            with mock.patch(
                                "builtins.open",
                                mock.mock_open(read_data=b"video-bytes"),
                            ):
                                with mock.patch("time.sleep"):
                                    client.clip_upload(Path("example.mp4"), "caption")

        post_calls = private_post.call_args_list
        self.assertEqual(len(post_calls), 2)
        upload_settings_call, video_upload_call = post_calls
        self.assertRegex(
            upload_settings_call.args[0],
            r"https://i\.instagram\.com/upload_settings/[0-9a-f-]{36}$",
        )
        settings_headers = upload_settings_call.kwargs["headers"]
        self.assertEqual(settings_headers["Content-Type"], "application/json")
        self.assertEqual(settings_headers["X-Entity-Name"], "upload_settings")
        self.assertEqual(settings_headers["X-Entity-Type"], "application/json")
        self.assertEqual(settings_headers["Offset"], "0")
        self.assertEqual(
            settings_headers["Content-Length"],
            settings_headers["X-Entity-Length"],
        )
        settings_payload = json.loads(upload_settings_call.kwargs["data"])
        self.assertEqual(
            settings_payload["composer_session_id"],
            upload_settings_call.args[0].rsplit("/", 1)[-1],
        )
        settings_properties = settings_payload["upload_setting_properties"]
        self.assertEqual(settings_properties["context"]["source_type"], "clips")
        self.assertEqual(settings_properties["context"]["target_id"], 1)
        self.assertEqual(settings_properties["video"]["video_width"], 720)
        self.assertEqual(settings_properties["video"]["video_height"], 1280)
        self.assertEqual(settings_properties["video"]["video_original_file_size"], 11)
        self.assertEqual(settings_payload["preview_spec"]["video_dur_ms"], 6023)

        upload_url = video_upload_call.args[0]
        upload_name = upload_url.rsplit("/", 1)[-1]
        self.assertRegex(
            upload_name,
            r"^[0-9a-f]{32}-0-11-1778346423000-1778346423000$",
        )
        self.assertTrue(private_get.call_args.args[0].endswith(upload_name))

        headers = video_upload_call.kwargs["headers"]
        self.assertEqual(headers["Content-Type"], "application/octet-stream")
        self.assertEqual(headers["X-Entity-Type"], "video/mp4")
        self.assertEqual(headers["X-Entity-Length"], "11")
        self.assertEqual(headers["X-Entity-Name"], upload_name)
        self.assertEqual(headers["Offset"], "0")
        self.assertEqual(headers["Segment-Start-Offset"], "0")
        self.assertEqual(headers["Segment-Type"], "3")

        rupload_params = json.loads(headers["X-Instagram-Rupload-Params"])
        self.assertEqual(rupload_params["share_type"], "reels")
        self.assertEqual(rupload_params["is_optimistic_upload"], "true")
        self.assertEqual(rupload_params["content_tags"], "use_default_cover")
        self.assertEqual(rupload_params["xsharing_user_ids"], "[]")
        self.assertEqual(rupload_params["upload_media_duration_ms"], "6023")
        self.assertEqual(rupload_params["session_id"], rupload_params["upload_id"])

    def test_clip_upload_trial_adds_trial_params_without_mutating_extra_data(self):
        client = self.build_client()
        client.last_json = {"media": self.build_media_payload()}
        ok_response = Mock(status_code=200)
        extra_data = {"share_to_facebook": 1}

        with mock.patch(
            "instagrapi.mixins.clip.analyze_video",
            return_value=(Path("/tmp/thumb.jpg"), 720, 1280, 6.023),
        ):
            with mock.patch.object(client.private, "get", return_value=ok_response):
                with mock.patch.object(
                    client.private,
                    "post",
                    side_effect=[ok_response, ok_response],
                ):
                    with mock.patch.object(client, "clip_configure", return_value={"status": "ok"}) as clip_configure:
                        with mock.patch(
                            "builtins.open",
                            mock.mock_open(read_data=b"video-bytes"),
                        ):
                            with mock.patch("time.sleep"):
                                client.clip_upload(
                                    Path("example.mp4"),
                                    "caption",
                                    trial=True,
                                    trial_graduation_strategy="manual",
                                    extra_data=extra_data,
                                )

        self.assertEqual(extra_data, {"share_to_facebook": 1})
        self.assertEqual(clip_configure.call_args.args[8], "0")
        configure_extra = clip_configure.call_args.kwargs["extra_data"]
        self.assertEqual(configure_extra["share_to_facebook"], 1)
        self.assertEqual(
            configure_extra["trial_params"],
            {"graduation_strategy": "manual"},
        )

    def test_clip_upload_trial_preserves_explicit_trial_params(self):
        client = self.build_client()
        client.last_json = {"media": self.build_media_payload()}
        ok_response = Mock(status_code=200)
        extra_data = {
            "trial_params": {
                "graduation_strategy": "ss_performance",
                "custom_field": "1",
            },
        }

        with mock.patch(
            "instagrapi.mixins.clip.analyze_video",
            return_value=(Path("/tmp/thumb.jpg"), 720, 1280, 6.023),
        ):
            with mock.patch.object(client.private, "get", return_value=ok_response):
                with mock.patch.object(
                    client.private,
                    "post",
                    side_effect=[ok_response, ok_response],
                ):
                    with mock.patch.object(client, "clip_configure", return_value={"status": "ok"}) as clip_configure:
                        with mock.patch(
                            "builtins.open",
                            mock.mock_open(read_data=b"video-bytes"),
                        ):
                            with mock.patch("time.sleep"):
                                client.clip_upload(
                                    Path("example.mp4"),
                                    "caption",
                                    trial=True,
                                    extra_data=extra_data,
                                )

        self.assertEqual(clip_configure.call_args.args[8], "0")
        configure_extra = clip_configure.call_args.kwargs["extra_data"]
        self.assertEqual(
            configure_extra["trial_params"],
            {
                "graduation_strategy": "ss_performance",
                "custom_field": "1",
            },
        )

    def test_clip_upload_share_to_facebook_adds_crosspost_params_before_upload(self):
        client = self.build_client()
        client.last_json = {"media": self.build_media_payload()}
        ok_response = Mock(status_code=200)
        extra_data = {"disable_comments": "1"}
        fb_extra = {
            "share_to_facebook": "1",
            "is_reel_shared_to_fb": True,
            "share_to_facebook_reels": True,
            "share_to_fb_destination_id": "fb-destination-id",
            "share_to_fb_destination_type": "USER",
            "cross_app_share_fb_validation_check_bypass": False,
            "xpost_surface": "IG_REELS_COMPOSER",
            "no_token_crosspost": "1",
            "attempt_id": "attempt-id",
        }

        with mock.patch.object(client, "clip_share_to_fb_extra_data", return_value=fb_extra) as share_to_fb_extra:
            with mock.patch(
                "instagrapi.mixins.clip.analyze_video",
                return_value=(Path("/tmp/thumb.jpg"), 720, 1280, 6.023),
            ) as analyze_video:
                with mock.patch.object(client.private, "get", return_value=ok_response):
                    with mock.patch.object(
                        client.private,
                        "post",
                        side_effect=[ok_response, ok_response],
                    ):
                        with mock.patch.object(
                            client, "clip_configure", return_value={"status": "ok"}
                        ) as clip_configure:
                            with mock.patch(
                                "builtins.open",
                                mock.mock_open(read_data=b"video-bytes"),
                            ):
                                with mock.patch("time.sleep"):
                                    client.clip_upload(
                                        Path("example.mp4"),
                                        "caption",
                                        share_to_facebook=True,
                                        extra_data=extra_data,
                                    )

        share_to_fb_extra.assert_called_once()
        analyze_video.assert_called_once()
        self.assertEqual(extra_data, {"disable_comments": "1"})
        configure_extra = clip_configure.call_args.kwargs["extra_data"]
        self.assertEqual(configure_extra["disable_comments"], "1")
        self.assertEqual(configure_extra["share_to_fb_destination_id"], "fb-destination-id")
        self.assertTrue(configure_extra["share_to_facebook_reels"])
        self.assertEqual(configure_extra["xpost_surface"], "IG_REELS_COMPOSER")

    def test_video_story_upload_falls_back_to_recent_story_when_configure_has_no_media(self):
        client = self.build_client()
        existing = self.build_story("20", media_type=2)
        uploaded = self.build_story("21", media_type=2)

        with mock.patch.object(
            client,
            "video_rupload",
            return_value=("1", 720, 1280, 5, Path("/tmp/thumb.jpg")),
        ):
            with mock.patch.object(client, "video_configure_to_story", return_value={"status": "ok"}):
                with mock.patch.object(client, "user_stories", side_effect=[[existing], [uploaded, existing]]):
                    with mock.patch("time.sleep"):
                        result = client.video_upload_to_story(Path("story.mp4"))

        self.assertEqual(result.id, uploaded.id)

    def test_video_direct_upload_raises_clear_error_when_configure_has_no_message(self):
        client = self.build_client()

        with mock.patch.object(
            client,
            "video_rupload",
            return_value=("1", 720, 1280, 5, Path("/tmp/thumb.jpg")),
        ):
            with mock.patch.object(client, "video_configure_to_story", return_value={"status": "ok"}):
                with mock.patch("time.sleep"):
                    with self.assertRaises(VideoConfigureStoryError) as ctx:
                        client.video_upload_to_direct(
                            Path("story.mp4"),
                            thread_ids=[123],
                        )

        self.assertIn("without message_metadata payload", str(ctx.exception))

    def test_cutout_sticker_upload_raises_clear_error_when_configure_has_no_media(self):
        client = self.build_client()

        with mock.patch.object(client, "private_request", return_value={"status": "ok"}):
            with self.assertRaises(PrivateError) as ctx:
                client.media_configure_to_cutout_sticker("1", manual_box=[0.0, 0.0, 1.0, 1.0])

        self.assertIn("without media payload", str(ctx.exception))

    def test_cutout_sticker_upload_uses_returned_media_payload(self):
        client = self.build_client()
        media_payload = self.build_media_payload(media_type=1)

        with mock.patch.object(
            client,
            "private_request",
            return_value={"status": "ok", "media": media_payload},
        ):
            media = client.media_configure_to_cutout_sticker("1", manual_box=[0.0, 0.0, 1.0, 1.0])

        self.assertIsInstance(media, Media)
        self.assertEqual(media.media_type, 1)

    def test_clip_upload_as_reel_with_music_does_not_mutate_extra_data(self):
        client = self.build_client()
        extra_data = {"share_to_facebook": 1}
        track = Mock(
            uri="https://example.com/track.m4a",
            highlight_start_times_in_ms=[1500],
            display_artist="Artist",
            id="track-id",
            audio_cluster_id="cluster-id",
            title="Track title",
        )

        class FakeAudioClip:
            def __init__(self, path):
                self.path = path

            def subclipped(self, start, end):
                return self

            def close(self):
                return None

        class FakeVideoClip:
            def __init__(self, path):
                self.path = path
                self.duration = 2.5

            def with_audio(self, audio_clip):
                self.audio_clip = audio_clip
                return self

            def write_videofile(self, path):
                Path(path).write_bytes(b"video")

            def close(self):
                return None

        fake_mp = types.ModuleType("moviepy")
        fake_mp.VideoFileClip = FakeVideoClip
        fake_mp.AudioFileClip = FakeAudioClip

        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = Path(tmpdir) / "track.m4a"
            audio_path.write_bytes(b"audio")
            video_path = Path(tmpdir) / "output.mp4"
            with mock.patch.dict(
                "sys.modules",
                {
                    "moviepy": fake_mp,
                },
            ):
                with mock.patch("tempfile.mktemp", side_effect=[str(audio_path), str(video_path)]):
                    with mock.patch.object(client, "track_download_by_url", return_value=audio_path):
                        with mock.patch.object(client, "clip_upload", return_value="uploaded") as clip_upload:
                            result = client.clip_upload_as_reel_with_music(
                                Path("input.mp4"),
                                "caption",
                                track,
                                extra_data=extra_data,
                            )

        self.assertEqual(result, "uploaded")
        self.assertEqual(extra_data, {"share_to_facebook": 1})
        upload_extra = clip_upload.call_args.kwargs["extra_data"]
        self.assertEqual(upload_extra["share_to_facebook"], 1)
        self.assertIn("clips_audio_metadata", upload_extra)
        self.assertIn("music_params", upload_extra)

    def test_clip_upload_as_reel_with_music_includes_music_canonical_id(self):
        client = self.build_client()
        track = Mock(
            uri="https://example.com/track.m4a",
            highlight_start_times_in_ms=[1500],
            display_artist="Artist",
            id="track-id",
            audio_cluster_id="cluster-id",
            music_canonical_id="canonical-id",
            title="Track title",
        )

        class FakeAudioClip:
            def __init__(self, path):
                self.path = path

            def subclipped(self, start, end):
                return self

            def close(self):
                return None

        class FakeVideoClip:
            def __init__(self, path):
                self.path = path
                self.duration = 2.5

            def with_audio(self, audio_clip):
                self.audio_clip = audio_clip
                return self

            def write_videofile(self, path):
                Path(path).write_bytes(b"video")

            def close(self):
                return None

        fake_mp = types.ModuleType("moviepy")
        fake_mp.VideoFileClip = FakeVideoClip
        fake_mp.AudioFileClip = FakeAudioClip

        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = Path(tmpdir) / "track.m4a"
            audio_path.write_bytes(b"audio")
            video_path = Path(tmpdir) / "output.mp4"
            with mock.patch.dict(
                "sys.modules",
                {
                    "moviepy": fake_mp,
                },
            ):
                with mock.patch("tempfile.mktemp", side_effect=[str(audio_path), str(video_path)]):
                    with mock.patch.object(client, "track_download_by_url", return_value=audio_path):
                        with mock.patch.object(client, "clip_upload", return_value="uploaded") as clip_upload:
                            client.clip_upload_as_reel_with_music(
                                Path("input.mp4"),
                                "caption",
                                track,
                            )

        upload_extra = clip_upload.call_args.kwargs["extra_data"]
        self.assertEqual(
            upload_extra["clips_audio_metadata"]["song"]["music_canonical_id"],
            "canonical-id",
        )
        self.assertEqual(
            upload_extra["music_params"]["music_canonical_id"],
            "canonical-id",
        )

    def test_clip_upload_as_reel_with_music_cleans_temp_files_on_failure(self):
        client = self.build_client()
        track = Mock(
            uri="https://example.com/track.m4a",
            highlight_start_times_in_ms=[0],
            display_artist="Artist",
            id="track-id",
            audio_cluster_id="cluster-id",
            title="Track title",
        )

        class FakeAudioClip:
            def __init__(self, path):
                self.path = path

            def subclipped(self, start, end):
                return self

            def close(self):
                return None

        class FakeVideoClip:
            def __init__(self, path):
                self.path = path
                self.duration = 2.5

            def with_audio(self, audio_clip):
                self.audio_clip = audio_clip
                return self

            def write_videofile(self, path):
                Path(path).write_bytes(b"video")

            def close(self):
                return None

        fake_mp = types.ModuleType("moviepy")
        fake_mp.VideoFileClip = FakeVideoClip
        fake_mp.AudioFileClip = FakeAudioClip

        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = Path(tmpdir) / "track.m4a"
            audio_path.write_bytes(b"audio")
            video_path = Path(tmpdir) / "output.mp4"
            with mock.patch.dict(
                "sys.modules",
                {
                    "moviepy": fake_mp,
                },
            ):
                with mock.patch("tempfile.mktemp", side_effect=[str(audio_path), str(video_path)]):
                    with mock.patch.object(client, "track_download_by_url", return_value=audio_path):
                        with mock.patch.object(
                            client,
                            "clip_upload",
                            side_effect=ClipConfigureError("boom"),
                        ):
                            with self.assertRaises(ClipConfigureError):
                                client.clip_upload_as_reel_with_music(
                                    Path("input.mp4"),
                                    "caption",
                                    track,
                                )

            self.assertFalse(audio_path.exists())
            self.assertFalse(video_path.exists())

    def test_clip_analyze_video_closes_video_file(self):
        import instagrapi.mixins.clip as clip_mixin

        closed = {"value": False}

        class FakeVideoClip:
            def __init__(self, path):
                self.size = (720, 1280)
                self.duration = 5

            def close(self):
                closed["value"] = True

        fake_mp = types.ModuleType("moviepy")
        fake_mp.VideoFileClip = FakeVideoClip

        with mock.patch.dict(
            "sys.modules",
            {
                "moviepy": fake_mp,
            },
        ):
            result = clip_mixin.analyze_video(Path("input.mp4"), thumbnail=Path("thumb.jpg"))

        self.assertEqual(result, (Path("thumb.jpg"), 720, 1280, 5))
        self.assertTrue(closed["value"])

    def test_video_analyze_video_closes_video_file_on_save_frame_error(self):
        import instagrapi.mixins.video as video_mixin

        closed = {"value": False}

        class FakeVideoClip:
            def __init__(self, path):
                self.size = (720, 1280)
                self.duration = 5

            def save_frame(self, path, t):
                raise RuntimeError("save failed")

            def close(self):
                closed["value"] = True

        fake_mp = types.ModuleType("moviepy")
        fake_mp.VideoFileClip = FakeVideoClip

        with mock.patch.dict(
            "sys.modules",
            {
                "moviepy": fake_mp,
            },
        ):
            with self.assertRaises(RuntimeError):
                video_mixin.analyze_video(Path("input.mp4"))

        self.assertTrue(closed["value"])

    def test_clip_analyze_video_closes_video_file_on_save_frame_error(self):
        import instagrapi.mixins.clip as clip_mixin

        closed = {"value": False}

        class FakeVideoClip:
            def __init__(self, path):
                self.size = (720, 1280)
                self.duration = 5

            def save_frame(self, path, t):
                raise RuntimeError("save failed")

            def close(self):
                closed["value"] = True

        fake_mp = types.ModuleType("moviepy")
        fake_mp.VideoFileClip = FakeVideoClip

        with mock.patch.dict(
            "sys.modules",
            {
                "moviepy": fake_mp,
            },
        ):
            with self.assertRaises(RuntimeError):
                clip_mixin.analyze_video(Path("input.mp4"))

        self.assertTrue(closed["value"])

    def test_video_story_sticker_ids_include_all_stickers(self):
        client = self.build_client()

        with mock.patch.object(client, "private_request") as private_request:
            private_request.side_effect = [
                {"status": "ok"},
                {"status": "ok"},
            ]
            client.video_configure_to_story(
                upload_id="1",
                width=720,
                height=1280,
                duration=5,
                thumbnail=Path("/tmp/placeholder.jpg"),
                caption="",
                links=[StoryLink(webUri="https://example.com")],
                hashtags=[
                    StoryHashtag(
                        hashtag=Hashtag(id="1", name="example"),
                        x=0.2,
                        y=0.3,
                        width=0.5,
                        height=0.2,
                    )
                ],
            )

        configure_args, _ = private_request.call_args_list[1]
        self.assertEqual(
            configure_args[1]["story_sticker_ids"],
            "hashtag_sticker,link_sticker_default",
        )

    def test_extract_story_v1_reads_links_from_story_link_stickers(self):
        story = extract_story_v1(
            {
                "pk": "1",
                "id": "1_2",
                "code": "abc",
                "taken_at": 1710000000,
                "media_type": 1,
                "image_versions2": {
                    "candidates": [
                        {
                            "url": "https://example.com/thumbnail.jpg",
                            "width": 720,
                            "height": 1280,
                        }
                    ]
                },
                "user": {
                    "pk": "2",
                    "username": "example",
                    "profile_pic_url": "https://example.com/profile.jpg",
                },
                "story_link_stickers": [
                    {
                        "x": 0.5,
                        "y": 0.5,
                        "width": 0.5,
                        "height": 0.2,
                        "rotation": 0.0,
                        "story_link": {
                            "url": "https://example.com/story-link",
                            "link_type": "web",
                        },
                    }
                ],
                "story_hashtags": [
                    {
                        "x": 0.2,
                        "y": 0.3,
                        "width": 0.5,
                        "height": 0.2,
                        "rotation": 0.0,
                        "hashtag": {"id": "1", "name": "example"},
                    }
                ],
            }
        )

        self.assertEqual(len(story.links), 1)
        self.assertEqual(str(story.links[0].webUri), "https://example.com/story-link")
        self.assertEqual(len(story.stickers), 1)
        self.assertEqual(len(story.hashtags), 1)
        self.assertEqual(story.hashtags[0].hashtag.name, "example")
