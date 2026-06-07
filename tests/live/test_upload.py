from instagrapi.exceptions import ClientNotFoundError, ClipNotUpload, MediaNotFound
from tests import helpers as _helpers
from tests.helpers import *


class _ClipMusicMetadataAssertionsMixin:
    @staticmethod
    def music_asset_info(music_info):
        if not isinstance(music_info, dict):
            return {}
        asset_info = music_info.get("music_asset_info")
        if isinstance(asset_info, dict):
            return asset_info
        return {}

    def wait_for_clip_music_metadata(self, media, attempts=8):
        last_clips_metadata = {}
        for attempt in range(attempts):
            if attempt:
                time.sleep(5)
            result = self.cl.private_request(f"media/{media.pk}/info/")
            items = result.get("items") or []
            self.assertTrue(items, "media info did not return items")
            clips_metadata = items[0].get("clips_metadata") or {}
            last_clips_metadata = clips_metadata
            if clips_metadata.get("music_info"):
                return clips_metadata
        self.fail(f"Reel music metadata was not visible after {attempts} media_info attempts: {last_clips_metadata}")

    def assert_clip_uses_music_track(self, media, track):
        clips_metadata = self.wait_for_clip_music_metadata(media)
        self.assertEqual(clips_metadata.get("audio_type"), "licensed_music")
        music_info = clips_metadata.get("music_info") or {}
        self.assertTrue(music_info, "clips_metadata.music_info is empty")
        asset_info = self.music_asset_info(music_info)
        self.assertTrue(asset_info, "clips_metadata.music_info.music_asset_info is empty")

        expected_asset_id = getattr(track, "audio_asset_id", None) or getattr(track, "id", None)
        expected_cluster_id = getattr(track, "audio_cluster_id", None)
        if expected_asset_id:
            self.assertEqual(str(asset_info.get("audio_asset_id")), str(expected_asset_id))
        if expected_cluster_id:
            self.assertEqual(str(asset_info.get("audio_cluster_id")), str(expected_cluster_id))


class ClienUploadTestCase(_ClipMusicMetadataAssertionsMixin, _helpers.ClientPrivateTestCase):
    def __init__(self, *args, **kwargs):
        self.cl = None
        return unittest.TestCase.__init__(self, *args, **kwargs)

    def setup_method(self, *args, **kwargs):
        return None

    def setUp(self):
        if not TEST_ACCOUNTS_URL:
            self.skipTest("TEST_ACCOUNTS_URL is required for upload live tests")
        try:
            self.cl = self.fresh_account()
        except RuntimeError as exc:
            self.skipTest(str(exc))

    def get_location(self):
        location = self.cl.location_search(lat=59.939095, lng=30.315868)[0]
        self.assertIsInstance(location, Location)
        return location

    def assertLocation(self, location):
        self.assertIsInstance(location, Location)
        self.assertTrue(location.pk)
        self.assertTrue(location.name)

    def assertAlbumResourceUsertagsAccessible(self, media, expected_usertags, attempts=8, delay=5):
        last_resources = []
        for attempt in range(attempts):
            if attempt:
                time.sleep(delay)
            info = self.cl.media_info_v1(media.pk)
            last_resources = info.resources
            if len(last_resources) < len(expected_usertags):
                continue
            for resource, expected_tag in zip(last_resources, expected_usertags):
                if not resource.usertags:
                    break
                tag = resource.usertags[0]
                if str(tag.user.pk) != str(expected_tag.user.pk) or tag.x != expected_tag.x or tag.y != expected_tag.y:
                    break
            else:
                return info
        self.fail(f"Album resource usertags were not visible after {attempts} media_info_v1 attempts: {last_resources}")

    def ensure_creator_account(self):
        account = self.cl.account_info()
        if account.account_type == 3:
            return
        account = self.cl.account_convert_to_creator(
            category_id="2347428775505624",
            should_show_category=True,
            should_show_public_contacts=False,
        )
        self.assertEqual(account.account_type, 3)

    def assertScheduledMediaAccessible(
        self, media, schedule_at, caption_text, product_type="feed", attempts=5, delay=3
    ):
        self.assertIsInstance(media, Media)
        last_result = {}
        for attempt in range(attempts):
            if attempt:
                time.sleep(delay)
            result = self.cl.private_request(
                "media/infos/",
                params={"media_ids": media.id, "include_unpublished": "1"},
            )
            last_result = result
            items = result.get("items") or []
            if not items:
                continue
            payload = items[0]
            metadata = payload.get("content_scheduling_metadata") or {}
            self.assertEqual(str(payload.get("id")), str(media.id))
            self.assertEqual(payload.get("product_type"), product_type)
            self.assertEqual((payload.get("caption") or {}).get("text", ""), caption_text)
            self.assertTrue(metadata.get("scheduled_content_id"))
            self.assertEqual(metadata.get("scheduled_publish_time"), schedule_at)
            return payload
        self.fail(f"Scheduled media {media.id} was not accessible through media/infos: {last_result}")

    def skip_unavailable_scheduled_publish(self, exc):
        if exc is None or isinstance(
            exc,
            (ClientNotFoundError, ClientThrottledError, PleaseWaitFewMinutes, RetryError),
        ):
            self.skipTest("No usable scheduled publishing account was available")
        raise exc

    def scheduled_publish_clients(self, additional_count=4):
        seen_user_ids = set()
        if self.cl:
            seen_user_ids.add(str(self.cl.user_id))
            yield self.cl
        for cl in self.fresh_accounts(additional_count, exclude_user_ids=seen_user_ids):
            yield cl

    def upload_with_scheduled_publish(self, upload):
        last_exc = None
        for cl in self.scheduled_publish_clients():
            self.cl = cl
            self.ensure_creator_account()
            try:
                return upload()
            except (ClientNotFoundError, ClientThrottledError, PleaseWaitFewMinutes, RetryError) as exc:
                last_exc = exc
                continue
        self.skip_unavailable_scheduled_publish(last_exc)

    def cleanup_scheduled_media(self, media):
        if not media:
            return
        try:
            deleted = self.cl.media_delete(media.id)
        except Exception as exc:
            print(f"Scheduled media cleanup media_delete failed: {exc.__class__.__name__} {exc}")
            return
        if not deleted:
            print(f"Scheduled media cleanup media_delete returned False for {media.id}")

    def test_photo_upload_without_location(self):
        path = self.copy_media_fixture("examples/kanada.jpg")
        self.assertIsInstance(path, Path)
        media = None
        try:
            caption_text = "Test caption for photo"
            media = self.cl.photo_upload(path, caption_text)
            self.assertIsInstance(media, Media)
            self.assertEqual(media.caption_text, caption_text)
            self.assertFalse(media.location)
            self.assertUploadedMediaAccessible(media, media_type=1, caption_text=caption_text)
        finally:
            if media:
                self.assertTrue(self.cl.media_delete(media.id))

    def test_photo_upload(self):
        path = self.copy_media_fixture("examples/kanada.jpg")
        self.assertIsInstance(path, Path)
        media = None
        try:
            caption_text = "Test caption for photo"
            media = self.cl.photo_upload(path, caption_text, location=self.get_location())
            self.assertIsInstance(media, Media)
            self.assertEqual(media.caption_text, caption_text)
            self.assertLocation(media.location)
            self.assertUploadedMediaAccessible(media, media_type=1, caption_text=caption_text)
        finally:
            if media:
                self.assertTrue(self.cl.media_delete(media.id))

    def test_photo_upload_scheduled(self):
        path = self.copy_media_fixture("examples/kanada.jpg")
        self.assertIsInstance(path, Path)
        media = None
        try:
            schedule_at = int(time.time()) + 3600
            caption_text = f"Test caption for scheduled photo {schedule_at}"
            media = self.upload_with_scheduled_publish(
                lambda: self.cl.photo_upload(path, caption_text, schedule_at=schedule_at)
            )
            self.assertIsInstance(media, Media)
            self.assertEqual(media.caption_text, caption_text)
            self.assertScheduledMediaAccessible(media, schedule_at, caption_text)
            with self.assertRaises(MediaNotFound):
                self.cl.media_info_v1(media.pk)
        finally:
            if media:
                self.cleanup_scheduled_media(media)

    def test_video_upload_scheduled(self):
        path = self.make_video_fixture(label="scheduled feed video fixture")
        self.assertIsInstance(path, Path)
        media = None
        try:
            schedule_at = int(time.time()) + 3600
            caption_text = f"Test caption for scheduled video {schedule_at}"
            media = self.upload_with_scheduled_publish(
                lambda: self.cl.video_upload(path, caption_text, schedule_at=schedule_at)
            )
            self.assertIsInstance(media, Media)
            self.assertEqual(media.caption_text, caption_text)
            self.assertScheduledMediaAccessible(media, schedule_at, caption_text)
            with self.assertRaises(MediaNotFound):
                self.cl.media_info_v1(media.pk)
        finally:
            if media:
                self.cleanup_scheduled_media(media)

    def test_video_upload(self):
        path = self.make_video_fixture(label="feed video fixture")
        self.assertIsInstance(path, Path)
        media = None
        try:
            caption_text = "Test caption for video"
            media = self.cl.video_upload(path, caption_text, location=self.get_location())
            self.assertIsInstance(media, Media)
            self.assertEqual(media.caption_text, caption_text)
            self.assertLocation(media.location)
            self.assertUploadedMediaAccessible(media, media_type=2, caption_text=caption_text)
        finally:
            if media:
                self.assertTrue(self.cl.media_delete(media.id))

    def test_album_upload_scheduled(self):
        paths = [
            self.copy_media_fixture("examples/kanada.jpg"),
            self.copy_media_fixture("examples/background.png"),
        ]
        [self.assertIsInstance(path, Path) for path in paths]
        media = None
        try:
            schedule_at = int(time.time()) + 3600
            caption_text = f"Test caption for scheduled album {schedule_at}"
            media = self.upload_with_scheduled_publish(
                lambda: self.cl.album_upload(paths, caption_text, schedule_at=schedule_at)
            )
            self.assertIsInstance(media, Media)
            self.assertEqual(media.caption_text, caption_text)
            self.assertScheduledMediaAccessible(media, schedule_at, caption_text, product_type="carousel_container")
            with self.assertRaises(MediaNotFound):
                self.cl.media_info_v1(media.pk)
        finally:
            if media:
                self.cleanup_scheduled_media(media)

    def test_album_upload(self):
        paths = [
            self.copy_media_fixture("examples/kanada.jpg"),
            self.copy_media_fixture("examples/background.png"),
        ]
        [self.assertIsInstance(path, Path) for path in paths]
        media = None
        try:
            instagram = self.user_info_by_username("instagram")
            usertag = Usertag(user=self.user_short(instagram), x=0.5, y=0.5)
            location = self.get_location()
            caption_text = "Test caption for album"
            media = self.cl.album_upload(paths, caption_text, usertags=[usertag], location=location)
            self.assertIsInstance(media, Media)
            self.assertEqual(media.caption_text, caption_text)
            self.assertEqual(len(media.resources), 2)
            self.assertLocation(media.location)
            keep_path(media.usertags[0].user)
            keep_path(usertag.user)
            self.assertEqual(media.usertags, [usertag])
            self.assertUploadedMediaAccessible(media, media_type=8, caption_text=caption_text, min_resources=2)
        finally:
            if media:
                self.assertTrue(self.cl.media_delete(media.id))

    def test_album_upload_with_per_slide_usertags_visible_after_media_info(self):
        paths = [
            self.copy_media_fixture("examples/kanada.jpg"),
            self.copy_media_fixture("examples/background.png"),
        ]
        [self.assertIsInstance(path, Path) for path in paths]
        media = None
        try:
            instagram = self.user_short(self.user_info_by_username("instagram"))
            first_tag = Usertag(user=instagram, x=0.25, y=0.75)
            second_tag = Usertag(user=instagram, x=0.75, y=0.25)
            caption_text = "Test caption for album per-slide tags"
            media = self.cl.album_upload(
                paths,
                caption_text,
                usertags=[[first_tag], [second_tag]],
                location=self.get_location(),
            )
            self.assertIsInstance(media, Media)
            self.assertEqual(media.caption_text, caption_text)
            info = self.assertAlbumResourceUsertagsAccessible(media, [first_tag, second_tag])
            self.assertEqual(info.caption_text, caption_text)
            self.assertEqual(len(info.resources), 2)
        finally:
            if media:
                self.assertTrue(self.cl.media_delete(media.id))

    def test_igtv_upload(self):
        path = self.make_video_fixture(label="IGTV fixture", duration=61)
        self.assertIsInstance(path, Path)
        media = None
        try:
            title = "6/6: The Transceiver Failure"
            caption_text = "Test caption for IGTV"
            try:
                media = self.cl.igtv_upload(path, title, caption_text)
            except RetryError as exc:
                if "configure_to_igtv" in str(exc) and "500 error responses" in str(exc):
                    self.skipTest("Instagram returned server 500 for configure_to_igtv")
                raise
            self.assertIsInstance(media, Media)
            self.assertEqual(media.title, title)
            self.assertEqual(media.caption_text, caption_text)
            self.assertUploadedMediaAccessible(media, media_type=2, caption_text=caption_text, title=title)
        finally:
            if media:
                self.assertTrue(self.cl.media_delete(media.id))

    def test_clip_upload(self):
        # media_type: 2 (video, not IGTV)
        # product_type: clips
        path = self.make_video_fixture(label="clip fixture")
        self.assertIsInstance(path, Path)
        media = None
        try:
            # location = self.get_location()
            caption_text = "Upload clip"
            media = self.cl.clip_upload(
                path,
                caption_text,
                # location=location
            )
            self.assertIsInstance(media, Media)
            self.assertEqual(media.caption_text, caption_text)
            # self.assertLocation(media.location)
            payload = self.assertUploadedMediaAccessible(
                media,
                media_type=2,
                product_type="clips",
                caption_text=caption_text,
            )
            self.assertTrue(payload.get("video_versions"))
            self.assertEqual((payload.get("caption") or {}).get("text"), caption_text)
        finally:
            if media:
                self.assertTrue(self.cl.media_delete(media.id))

    def test_clip_upload_direct_failure_reports_response_live(self):
        path = self.make_video_fixture(label="clip upload failure fixture")
        response = requests.Response()
        response.status_code = 400
        response.url = "https://i.instagram.com/upload_settings/test"
        response._content = b'{"message":"media_needs_reupload","status":"fail"}'
        response.request = requests.Request("POST", response.url).prepare()

        with mock.patch.object(self.cl.private, "post", return_value=response):
            with self.assertRaises(ClipNotUpload) as ctx:
                self.cl.clip_upload(path, "Upload clip failure")

        exc = ctx.exception
        self.assertIs(exc.response, response)
        self.assertEqual(exc.stage, "upload_settings")
        self.assertEqual(exc.status_code, 400)
        self.assertEqual(exc.error_response["message"], "media_needs_reupload")
        self.assertNotIn("response': None", str(exc))

    def test_reel_upload_with_music(self):
        # media_type: 2 (video, not IGTV)
        # product_type: reels

        path = self.make_video_fixture(label="music Reel fixture")
        self.assertIsInstance(path, Path)
        media = None
        try:
            title = "Kill My Vibe (feat. Tom G)"
            caption = "Test caption for reel"
            track = self.cl.search_music(title)[0]
            try:
                media = self.cl.clip_upload_as_reel_with_music(path, caption, track)
            except RuntimeError as exc:
                if "requires MoviePy 2.2.1" in str(exc):
                    self.skipTest(str(exc))
                raise
            self.assertIsInstance(media, Media)
            self.assertEqual(media.caption_text, caption)
            self.assertUploadedMediaAccessible(media, media_type=2, product_type="clips", caption_text=caption)
            self.assert_clip_uses_music_track(media, track)
        finally:
            if media:
                self.assertTrue(self.cl.media_delete(media.id))


class ClientClipMusicMetadataUploadLiveTestCase(_ClipMusicMetadataAssertionsMixin, _helpers.ClientPrivateTestCase):
    thumbnail_path = Path("examples/kanada.jpg")

    def __init__(self, *args, **kwargs):
        self.cl = None
        return unittest.TestCase.__init__(self, *args, **kwargs)

    def setup_method(self, *args, **kwargs):
        return None

    def setUp(self):
        if not TEST_ACCOUNTS_URL:
            self.skipTest("TEST_ACCOUNTS_URL is required for Reel music metadata upload live tests")
        try:
            self.cl = self.fresh_account()
        except RuntimeError as exc:
            self.skipTest(str(exc))

    def make_clip_mp4(self):
        try:
            import imageio_ffmpeg
        except ImportError:
            self.skipTest("imageio_ffmpeg is required to generate a Reel fixture")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
            path = Path(tmp.name)
        self.addCleanup(lambda: path.unlink(missing_ok=True))

        try:
            subprocess.run(
                [
                    imageio_ffmpeg.get_ffmpeg_exe(),
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "color=c=black:s=720x1280:r=30:d=4",
                    "-f",
                    "lavfi",
                    "-i",
                    "sine=frequency=440:duration=4",
                    "-shortest",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "64k",
                    str(path),
                ],
                check=True,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            self.skipTest(f"Could not generate Reel fixture: {exc}")
        return path

    def first_music_track(self):
        tracks = self.cl.search_music("Runaway")
        if not tracks:
            self.skipTest("search_music did not return a usable track")
        return tracks[0]

    def cleanup_uploaded_media(self, media):
        if not media:
            return
        try:
            self.assertTrue(self.cl.media_delete(media.id))
        except Exception as exc:
            print(f"Reel music metadata upload cleanup media_delete failed: {exc.__class__.__name__} {exc}")

    def test_clip_upload_with_music_live(self):
        path = self.make_clip_mp4()
        track = self.first_music_track()
        media = None
        try:
            media = self.cl.clip_upload_with_music(
                path,
                "Reel music metadata live test",
                track,
                thumbnail=self.thumbnail_path,
                overlap_duration=4000,
            )
            self.assertIsInstance(media, Media)
            self.assertEqual(media.media_type, 2)
            self.assertEqual(media.product_type, "clips")
            self.assert_clip_uses_music_track(media, track)
        finally:
            self.cleanup_uploaded_media(media)


class ClientFeedMusicUploadLiveTestCase(_helpers.ClientPrivateTestCase):
    photo_path = Path("examples/kanada.jpg")
    album_paths = [Path("examples/kanada.jpg"), Path("examples/background.png")]

    def __init__(self, *args, **kwargs):
        self.cl = None
        return unittest.TestCase.__init__(self, *args, **kwargs)

    def setup_method(self, *args, **kwargs):
        return None

    def setUp(self):
        if not TEST_ACCOUNTS_URL:
            self.skipTest("TEST_ACCOUNTS_URL is required for feed music upload live tests")
        try:
            self.cl = self.fresh_account()
        except RuntimeError as exc:
            self.skipTest(str(exc))

    def iter_track_candidates(self, value):
        if isinstance(value, list):
            for item in value:
                yield from self.iter_track_candidates(item)
            return
        if not isinstance(value, dict):
            return

        track = value.get("track") or value
        if (track.get("audio_asset_id") or track.get("id")) and track.get("audio_cluster_id"):
            yield track

        for key in ("items", "preview_items", "tracks"):
            yield from self.iter_track_candidates(value.get(key) or [])
        yield from self.iter_track_candidates((value.get("playlist") or {}).get("preview_items") or [])

    def feed_music_track(self):
        music = self.cl.music_in_feed_audio_browser()
        self.assertEqual(music.get("status"), "ok")

        alacorn_session_id = music.get("alacorn_session_id")
        if not alacorn_session_id:
            self.skipTest("music_in_feed_audio_browser did not return alacorn_session_id")

        track = next(self.iter_track_candidates(music.get("items") or []), None)
        if not track:
            self.skipTest("music_in_feed_audio_browser did not return a usable track")
        return track, alacorn_session_id

    def assertUploadedMediaHasMusic(self, media):
        payload = self.assertUploadedMediaAccessible(media)
        music_metadata = payload.get("music_metadata") or {}
        self.assertEqual(music_metadata.get("audio_type"), "licensed_music")

    def cleanup_uploaded_media(self, media):
        if not media:
            return
        try:
            self.assertTrue(self.cl.media_delete(media.id))
        except Exception as exc:
            print(f"Feed music upload cleanup media_delete failed: {exc.__class__.__name__} {exc}")

    def test_photo_upload_with_music_live(self):
        track, alacorn_session_id = self.feed_music_track()
        media = None
        try:
            media = self.cl.photo_upload_with_music(
                self.photo_path,
                "",
                track,
                alacorn_session_id=alacorn_session_id,
            )
            self.assertIsInstance(media, Media)
            self.assertEqual(media.media_type, 1)
            self.assertUploadedMediaHasMusic(media)
        finally:
            self.cleanup_uploaded_media(media)

    def test_album_upload_with_music_live(self):
        track, alacorn_session_id = self.feed_music_track()
        media = None
        try:
            media = self.cl.album_upload_with_music(
                self.album_paths,
                "",
                track,
                alacorn_session_id=alacorn_session_id,
            )
            self.assertIsInstance(media, Media)
            self.assertEqual(media.media_type, 8)
            self.assertGreaterEqual(len(media.resources), 2)
            self.assertUploadedMediaHasMusic(media)
        finally:
            self.cleanup_uploaded_media(media)


class ClientTrialReelUploadLiveTestCase(_helpers.ClientPrivateTestCase):
    def __init__(self, *args, **kwargs):
        self.cl = None
        self.clients = []
        return unittest.TestCase.__init__(self, *args, **kwargs)

    def setup_method(self, *args, **kwargs):
        return None

    def setUp(self):
        if not TEST_ACCOUNTS_URL:
            self.skipTest("TEST_ACCOUNTS_URL is required for Trial Reel upload live tests")
        try:
            self.clients = self.fresh_accounts(5)
        except RuntimeError as exc:
            self.skipTest(str(exc))

    def trial_clips_enabled(self, client):
        return client.clip_trial_eligible()

    def make_clip_mp4(self):
        try:
            import imageio_ffmpeg
        except ImportError:
            self.skipTest("imageio_ffmpeg is required to generate a Trial Reel fixture")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
            path = Path(tmp.name)
        self.addCleanup(lambda: path.unlink(missing_ok=True))

        try:
            subprocess.run(
                [
                    imageio_ffmpeg.get_ffmpeg_exe(),
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "color=c=purple:s=720x1280:r=30:d=2",
                    "-f",
                    "lavfi",
                    "-i",
                    "sine=frequency=440:duration=2",
                    "-shortest",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "64k",
                    str(path),
                ],
                check=True,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            self.skipTest(f"Could not generate Trial Reel fixture: {exc}")
        return path

    def cleanup_uploaded_media(self, client, media):
        if not media:
            return
        try:
            self.assertTrue(client.media_delete(media.id))
        except Exception as exc:
            print(f"Trial Reel upload cleanup media_delete failed: {exc.__class__.__name__} {exc}")

    def test_clip_upload_trial_live(self):
        path = self.make_clip_mp4()
        rejected = 0
        checked = 0

        for client in self.clients:
            if not self.trial_clips_enabled(client):
                continue
            checked += 1
            media = None
            try:
                media = client.clip_upload(path, "Trial Reel live test", trial=True)
            except UnknownError as exc:
                if "not eligible for trial Clips" in str(exc):
                    rejected += 1
                    continue
                raise

            try:
                self.assertIsInstance(media, Media)
                self.assertEqual(media.media_type, 2)
                self.assertEqual(media.product_type, "clips")
                self.assertUploadedMediaAccessible(
                    media,
                    media_type=2,
                    product_type="clips",
                    caption_text="Trial Reel live test",
                    client=client,
                )
                return
            finally:
                self.cleanup_uploaded_media(client, media)

        if checked:
            self.skipTest(f"Instagram rejected {rejected}/{checked} clip_trial_eligible accounts for trial Clips")
        self.skipTest("No fresh account has Trial Reels enabled")


class ClientClipCreationPreflightLiveTestCase(_helpers.ClientPrivateTestCase):
    def test_clip_info_for_creation_live(self):
        result = self.cl.clip_info_for_creation()

        self.assertEqual(result.get("status"), "ok")


class ClientFacebookReelCrosspostLiveTestCase(_helpers.ClientPrivateTestCase):
    def __init__(self, *args, **kwargs):
        self.cl = None
        return unittest.TestCase.__init__(self, *args, **kwargs)

    def setup_method(self, *args, **kwargs):
        return None

    def setUp(self):
        if not TEST_ACCOUNTS_URL:
            self.skipTest("TEST_ACCOUNTS_URL is required for Reel Facebook crosspost live tests")
        try:
            self.cl = self.fresh_account()
        except RuntimeError as exc:
            self.skipTest(str(exc))

    def test_clip_share_to_fb_extra_data_live(self):
        config = self.cl.clip_share_to_fb_config()
        self.assertEqual(config.get("status"), "ok")
        try:
            extra_data = self.cl.clip_share_to_fb_extra_data(config=config)
        except ClientError as exc:
            self.skipTest(f"No linked Facebook Reel destination available: {exc}")

        self.assertEqual(extra_data["share_to_facebook"], "1")
        self.assertTrue(extra_data["share_to_facebook_reels"])
        self.assertTrue(extra_data["is_reel_shared_to_fb"])
        self.assertTrue(extra_data["share_to_fb_destination_id"])
        self.assertTrue(extra_data["share_to_fb_destination_type"])
        self.assertIn(extra_data["share_to_fb_destination_type"], {"USER", "PAGE"})
        self.assertEqual(extra_data["xpost_surface"], "IG_REELS_COMPOSER")
        self.assertEqual(extra_data["no_token_crosspost"], "1")
        self.assertTrue(extra_data["attempt_id"])

    def test_clip_share_to_fb_destination_live(self):
        config = self.cl.clip_share_to_fb_config()
        self.assertEqual(config.get("status"), "ok")
        try:
            destination = self.cl.clip_share_to_fb_destination(config=config)
        except ClientError as exc:
            self.skipTest(f"No confirmed Facebook Reel destination available: {exc}")

        self.assertTrue(destination["destination_id"])
        self.assertIn(destination["destination_type"], {"USER", "PAGE"})
        if destination.get("destination_audience_type"):
            self.assertIsInstance(destination["destination_audience_type"], str)
