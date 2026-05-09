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

    def test_clip_share_to_fb_config_requests_reel_facebook_config(self):
        client = self.build_client()
        expected = {"status": "ok", "eligible": True}

        with mock.patch.object(
            client, "private_request", return_value=expected
        ) as private_request:
            result = client.clip_share_to_fb_config()

        private_request.assert_called_once()
        endpoint = private_request.call_args.args[0]
        params = private_request.call_args.kwargs["params"]
        self.assertEqual(endpoint, "clips/user/share_to_fb_config/")
        device_status = json.loads(params["device_status"])
        self.assertEqual(device_status["chip_vendor"], "others")
        self.assertFalse(device_status["hw_av1_dec"])
        self.assertEqual(result, expected)

    def test_photo_upload_raises_clear_error_when_configure_has_no_media(self):
        client = self.build_client()

        with mock.patch.object(client, "photo_rupload", return_value=("1", 720, 720)):
            with mock.patch.object(
                client, "photo_configure", return_value={"status": "ok"}
            ):
                with mock.patch("time.sleep"):
                    with self.assertRaises(PhotoConfigureError) as ctx:
                        client.photo_upload(Path("example.jpg"), "caption")

        self.assertIn("without media payload", str(ctx.exception))

    def test_video_upload_raises_clear_error_when_configure_has_no_media(self):
        client = self.build_client()

        with mock.patch.object(
            client,
            "video_rupload",
            return_value=("1", 720, 1280, 5, Path("/tmp/thumb.jpg")),
        ):
            with mock.patch.object(
                client, "video_configure", return_value={"status": "ok"}
            ):
                with mock.patch("time.sleep"):
                    with self.assertRaises(VideoConfigureError) as ctx:
                        client.video_upload(Path("example.mp4"), "caption")

        self.assertIn("without media payload", str(ctx.exception))

    def test_album_upload_raises_clear_error_when_configure_has_no_media(self):
        client = self.build_client()

        with mock.patch.object(client, "photo_rupload", return_value=("1", 720, 720)):
            with mock.patch.object(
                client, "album_configure", return_value={"status": "ok"}
            ):
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

    def test_photo_story_upload_raises_clear_error_when_configure_has_no_media(self):
        client = self.build_client()

        with mock.patch.object(client, "photo_rupload", return_value=("1", 720, 1280)):
            with mock.patch.object(
                client, "photo_configure_to_story", return_value={"status": "ok"}
            ):
                with mock.patch("time.sleep"):
                    with self.assertRaises(PhotoConfigureStoryError) as ctx:
                        client.photo_upload_to_story(Path("story.jpg"))

        self.assertIn("without media payload", str(ctx.exception))

    def test_clip_upload_falls_back_to_last_json_media_payload(self):
        client = self.build_client()
        client.last_json = {"media": self.build_media_payload()}
        ok_response = Mock(status_code=200)

        with mock.patch(
            "instagrapi.mixins.clip.analyze_video",
            return_value=(Path("/tmp/thumb.jpg"), 720, 1280, 5),
        ):
            with mock.patch.object(client.private, "get", return_value=ok_response):
                with mock.patch.object(
                    client.private, "post", return_value=ok_response
                ):
                    with mock.patch.object(
                        client, "clip_configure", return_value={"status": "ok"}
                    ):
                        with mock.patch(
                            "builtins.open", mock.mock_open(read_data=b"video-bytes")
                        ):
                            with mock.patch("time.sleep"):
                                media = client.clip_upload(
                                    Path("example.mp4"), "caption"
                                )

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
                with mock.patch.object(
                    client.private, "get", return_value=ok_response
                ) as private_get:
                    with mock.patch.object(
                        client.private,
                        "post",
                        side_effect=[ok_response, ok_response],
                    ) as private_post:
                        with mock.patch.object(
                            client, "clip_configure", return_value={"status": "ok"}
                        ):
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

    def test_video_story_upload_raises_clear_error_when_configure_has_no_media(self):
        client = self.build_client()

        with mock.patch.object(
            client,
            "video_rupload",
            return_value=("1", 720, 1280, 5, Path("/tmp/thumb.jpg")),
        ):
            with mock.patch.object(
                client, "video_configure_to_story", return_value={"status": "ok"}
            ):
                with mock.patch("time.sleep"):
                    with self.assertRaises(VideoConfigureStoryError) as ctx:
                        client.video_upload_to_story(Path("story.mp4"))

        self.assertIn("without media payload", str(ctx.exception))

    def test_video_direct_upload_raises_clear_error_when_configure_has_no_message(self):
        client = self.build_client()

        with mock.patch.object(
            client,
            "video_rupload",
            return_value=("1", 720, 1280, 5, Path("/tmp/thumb.jpg")),
        ):
            with mock.patch.object(
                client, "video_configure_to_story", return_value={"status": "ok"}
            ):
                with mock.patch("time.sleep"):
                    with self.assertRaises(VideoConfigureStoryError) as ctx:
                        client.video_upload_to_direct(
                            Path("story.mp4"),
                            thread_ids=[123],
                        )

        self.assertIn("without message_metadata payload", str(ctx.exception))

    def test_cutout_sticker_upload_raises_clear_error_when_configure_has_no_media(self):
        client = self.build_client()

        with mock.patch.object(
            client, "private_request", return_value={"status": "ok"}
        ):
            with self.assertRaises(PrivateError) as ctx:
                client.media_configure_to_cutout_sticker(
                    "1", manual_box=[0.0, 0.0, 1.0, 1.0]
                )

        self.assertIn("without media payload", str(ctx.exception))

    def test_cutout_sticker_upload_uses_returned_media_payload(self):
        client = self.build_client()
        media_payload = self.build_media_payload(media_type=1)

        with mock.patch.object(
            client,
            "private_request",
            return_value={"status": "ok", "media": media_payload},
        ):
            media = client.media_configure_to_cutout_sticker(
                "1", manual_box=[0.0, 0.0, 1.0, 1.0]
            )

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

            def subclip(self, start, end):
                return self

            def close(self):
                return None

        class FakeVideoClip:
            def __init__(self, path):
                self.path = path
                self.duration = 2.5

            def set_audio(self, audio_clip):
                self.audio_clip = audio_clip
                return self

            def write_videofile(self, path):
                Path(path).write_bytes(b"video")

            def close(self):
                return None

        fake_mp = types.ModuleType("moviepy.editor")
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
                    "moviepy.editor": fake_mp,
                },
            ):
                with mock.patch(
                    "tempfile.mktemp", side_effect=[str(audio_path), str(video_path)]
                ):
                    with mock.patch.object(
                        client, "track_download_by_url", return_value=audio_path
                    ):
                        with mock.patch.object(
                            client, "clip_upload", return_value="uploaded"
                        ) as clip_upload:
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

            def subclip(self, start, end):
                return self

            def close(self):
                return None

        class FakeVideoClip:
            def __init__(self, path):
                self.path = path
                self.duration = 2.5

            def set_audio(self, audio_clip):
                self.audio_clip = audio_clip
                return self

            def write_videofile(self, path):
                Path(path).write_bytes(b"video")

            def close(self):
                return None

        fake_mp = types.ModuleType("moviepy.editor")
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
                    "moviepy.editor": fake_mp,
                },
            ):
                with mock.patch(
                    "tempfile.mktemp", side_effect=[str(audio_path), str(video_path)]
                ):
                    with mock.patch.object(
                        client, "track_download_by_url", return_value=audio_path
                    ):
                        with mock.patch.object(
                            client, "clip_upload", return_value="uploaded"
                        ) as clip_upload:
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

            def subclip(self, start, end):
                return self

            def close(self):
                return None

        class FakeVideoClip:
            def __init__(self, path):
                self.path = path
                self.duration = 2.5

            def set_audio(self, audio_clip):
                self.audio_clip = audio_clip
                return self

            def write_videofile(self, path):
                Path(path).write_bytes(b"video")

            def close(self):
                return None

        fake_mp = types.ModuleType("moviepy.editor")
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
                    "moviepy.editor": fake_mp,
                },
            ):
                with mock.patch(
                    "tempfile.mktemp", side_effect=[str(audio_path), str(video_path)]
                ):
                    with mock.patch.object(
                        client, "track_download_by_url", return_value=audio_path
                    ):
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

        fake_mp = types.ModuleType("moviepy.editor")
        fake_mp.VideoFileClip = FakeVideoClip

        with mock.patch.dict(
            "sys.modules",
            {
                "moviepy": fake_mp,
                "moviepy.editor": fake_mp,
            },
        ):
            result = clip_mixin.analyze_video(
                Path("input.mp4"), thumbnail=Path("thumb.jpg")
            )

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

        fake_mp = types.ModuleType("moviepy.editor")
        fake_mp.VideoFileClip = FakeVideoClip

        with mock.patch.dict(
            "sys.modules",
            {
                "moviepy": fake_mp,
                "moviepy.editor": fake_mp,
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

        fake_mp = types.ModuleType("moviepy.editor")
        fake_mp.VideoFileClip = FakeVideoClip

        with mock.patch.dict(
            "sys.modules",
            {
                "moviepy": fake_mp,
                "moviepy.editor": fake_mp,
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
