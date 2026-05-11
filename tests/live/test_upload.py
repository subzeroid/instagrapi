from tests import helpers as _helpers
from tests.helpers import *


class ClienUploadTestCase(_helpers.ClientPrivateTestCase):
    def get_location(self):
        location = self.cl.location_search(lat=59.939095, lng=30.315868)[0]
        self.assertIsInstance(location, Location)
        return location

    def assertLocation(self, location):
        # Instagram sometimes changes location by GEO coordinates:
        locations = [
            dict(
                pk=213597007,
                name="Palace Square",
                lat=59.939166666667,
                lng=30.315833333333,
            ),
            dict(
                pk=107617247320879,
                name="Russia, Saint-Petersburg",
                address="Russia, Saint-Petersburg",
                lat=59.93318,
                lng=30.30605,
                external_id=107617247320879,
                external_id_source="facebook_places",
            ),
        ]
        for data in locations:
            if data["pk"] == location.pk:
                break
        for key, val in data.items():
            itm = getattr(location, key)
            if isinstance(val, float):
                val = round(val, 2)
                itm = round(itm, 2)
            self.assertEqual(itm, val)

    def test_photo_upload_without_location(self):
        media_pk = self.cl.media_pk_from_url("https://www.instagram.com/p/BVDOOolFFxg/")
        path = self.cl.photo_download(media_pk)
        self.assertIsInstance(path, Path)
        try:
            media = self.cl.photo_upload(path, "Test caption for photo")
            self.assertIsInstance(media, Media)
            self.assertEqual(media.caption_text, "Test caption for photo")
            self.assertFalse(media.location)
        finally:
            cleanup(path)
            self.assertTrue(self.cl.media_delete(media.id))

    def test_photo_upload(self):
        media_pk = self.cl.media_pk_from_url("https://www.instagram.com/p/BVDOOolFFxg/")
        path = self.cl.photo_download(media_pk)
        self.assertIsInstance(path, Path)
        try:
            media = self.cl.photo_upload(path, "Test caption for photo", location=self.get_location())
            self.assertIsInstance(media, Media)
            self.assertEqual(media.caption_text, "Test caption for photo")
            self.assertLocation(media.location)
        finally:
            cleanup(path)
            self.assertTrue(self.cl.media_delete(media.id))

    def test_video_upload(self):
        media_pk = self.cl.media_pk_from_url("https://www.instagram.com/p/Bk2tOgogq9V/")
        path = self.cl.video_download(media_pk)
        self.assertIsInstance(path, Path)
        try:
            media = self.cl.video_upload(path, "Test caption for video", location=self.get_location())
            self.assertIsInstance(media, Media)
            self.assertEqual(media.caption_text, "Test caption for video")
            self.assertLocation(media.location)
        finally:
            cleanup(path)
            self.assertTrue(self.cl.media_delete(media.id))

    def test_album_upload(self):
        media_pk = self.cl.media_pk_from_url("https://www.instagram.com/p/BjNLpA1AhXM/")
        paths = self.cl.album_download(media_pk)
        [self.assertIsInstance(path, Path) for path in paths]
        try:
            instagram = self.user_info_by_username("instagram")
            usertag = Usertag(user=instagram, x=0.5, y=0.5)
            location = self.get_location()
            media = self.cl.album_upload(paths, "Test caption for album", usertags=[usertag], location=location)
            self.assertIsInstance(media, Media)
            self.assertEqual(media.caption_text, "Test caption for album")
            self.assertEqual(len(media.resources), 3)
            self.assertLocation(media.location)
            keep_path(media.usertags[0].user)
            keep_path(usertag.user)
            self.assertEqual(media.usertags, [usertag])
        finally:
            cleanup(*paths)
            self.assertTrue(self.cl.media_delete(media.id))

    def test_igtv_upload(self):
        media_pk = self.cl.media_pk_from_url("https://www.instagram.com/tv/B91gKCcpnTk/")
        path = self.cl.igtv_download(media_pk)
        self.assertIsInstance(path, Path)
        try:
            title = "6/6: The Transceiver Failure"
            caption_text = "Test caption for IGTV"
            media = self.cl.igtv_upload(path, title, caption_text, location=self.get_location())
            self.assertIsInstance(media, Media)
            self.assertEqual(media.title, title)
            self.assertEqual(media.caption_text, caption_text)
            self.assertLocation(media.location)
        finally:
            cleanup(path)
            self.assertTrue(self.cl.media_delete(media.id))

    def test_clip_upload(self):
        # media_type: 2 (video, not IGTV)
        # product_type: clips
        media_pk = self.cl.media_pk_from_url("https://www.instagram.com/p/CEjXskWJ1on/")
        path = self.cl.clip_download(media_pk)
        self.assertIsInstance(path, Path)
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
        finally:
            cleanup(path)
            self.assertTrue(self.cl.media_delete(media.id))

    def test_reel_upload_with_music(self):
        # media_type: 2 (video, not IGTV)
        # product_type: reels

        media_pk = self.cl.media_pk_from_url("https://www.instagram.com/p/CEjXskWJ1on/")
        path = self.cl.clip_download(media_pk)
        self.assertIsInstance(path, Path)
        try:
            title = "Kill My Vibe (feat. Tom G)"
            caption = "Test caption for reel"
            track = self.cl.search_music(title)[0]
            media = self.cl.clip_upload_as_reel_with_music(path, caption, track)
            self.assertIsInstance(media, Media)
            self.assertEqual(media.caption_text, caption)
        finally:
            cleanup(path)
            self.assertTrue(self.cl.media_delete(media.id))


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

    def uploaded_media_payload(self, media):
        result = self.cl.private_request(f"media/{media.pk}/info/")
        items = result.get("items") or []
        self.assertTrue(items)
        return items[0]

    def assertUploadedMediaHasMusic(self, media):
        payload = self.uploaded_media_payload(media)
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

    def setUp(self):
        if not TEST_ACCOUNTS_URL:
            self.skipTest("TEST_ACCOUNTS_URL is required for Trial Reel upload live tests")
        try:
            self.clients = self.fresh_accounts(5)
        except RuntimeError as exc:
            self.skipTest(str(exc))

    def trial_clips_enabled(self, client):
        result = client.private_request(f"users/{client.user_id}/info/")
        user = result.get("user") or {}
        return bool(user.get("trial_clips_enabled"))

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
            finally:
                self.cleanup_uploaded_media(client, media)

            self.assertIsInstance(media, Media)
            self.assertEqual(media.media_type, 2)
            self.assertEqual(media.product_type, "clips")
            return

        if checked:
            self.skipTest(f"Instagram rejected {rejected}/{checked} trial_clips_enabled accounts for trial Clips")
        self.skipTest("No fresh account has trial_clips_enabled")
