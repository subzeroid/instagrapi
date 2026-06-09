import multiprocessing
import os
import queue
import traceback
from urllib.parse import parse_qs, urlparse

from tests import helpers as _helpers
from tests.helpers import *


class ClientStoryTestCase(_helpers.ClientPrivateTestCase):
    def __init__(self, *args, **kwargs):
        self.cl = None
        return unittest.TestCase.__init__(self, *args, **kwargs)

    def make_story_mp4(self):
        return self.make_video_fixture(label="story video fixture")

    def story_sticker_media_pk(self):
        user_id = self.user_id_from_username("instagram")
        medias = self.cl.user_medias_v1(user_id, amount=1)
        if not medias:
            self.skipTest("instagram account did not return media for story sticker")
        return medias[0].pk

    def uploaded_story_with_media(self, expected_story, media_pk, attempts=8, delay=5):
        expected_media_pk = str(media_pk)
        last_visible_story = None
        last_stories = []
        for attempt in range(attempts):
            if attempt:
                time.sleep(delay)
            last_stories = self.cl.user_stories_v1(self.cl.user_id, amount=20)
            for story in last_stories:
                if str(story.pk) != str(expected_story.pk) and str(story.id) != str(expected_story.id):
                    continue
                last_visible_story = story
                if any(str(media.media_pk) == expected_media_pk for media in story.medias):
                    return story
        if last_visible_story:
            self.fail(
                f"Uploaded story {expected_story.id} did not contain shared media "
                f"{expected_media_pk}: {last_visible_story.medias}"
            )
        self.fail(f"Uploaded story {expected_story.id} was not visible in user stories: {last_stories}")

    def test_story_pk_from_url(self):
        story_pk = self.cl.story_pk_from_url("https://www.instagram.com/stories/instagram/2581281926631793076/")
        self.assertEqual(story_pk, 2581281926631793076)

    def test_upload_photo_story(self):
        media_pk = self.story_sticker_media_pk()
        story = None
        path = Path("examples/background.png")
        self.assertIsInstance(path, Path)
        caption = "Test photo caption"
        instagram = self.user_info_by_username("instagram")
        self.assertIsInstance(instagram, User)
        mentions = [StoryMention(user=self.user_short(instagram))]
        medias = [StoryMedia(media_pk=media_pk, x=0.5, y=0.5, width=0.6, height=0.8)]
        links = [StoryLink(webUri="https://instagram.com/")]
        # hashtags = [StoryHashtag(hashtag=self.cl.hashtag_info('instagram'))]
        # locations = [
        #     StoryLocation(
        #         location=Location(
        #             pk=150300262230285,
        #             name='Blaues Wunder (Dresden)',
        #         )
        #     )
        # ]
        stickers = [
            StorySticker(
                id="Igjf05J559JWuef4N5",
                type="gif",
                x=0.5,
                y=0.5,
                width=0.4,
                height=0.08,
            )
        ]
        try:
            story = self.cl.photo_upload_to_story(
                path,
                caption,
                mentions=mentions,
                links=links,
                # hashtags=hashtags,
                # locations=locations,
                stickers=stickers,
                medias=medias,
            )
            self.assertIsInstance(story, Story)
            self.assertTrue(story)
            self.assertUploadedStoryAccessible(story, media_type=1)
        finally:
            if story:
                self.assertTrue(self.cl.story_delete(story.id))

    def test_media_share_to_story(self):
        media_pk = self.story_sticker_media_pk()
        story = None
        try:
            story = self.cl.media_share_to_story(media_pk, caption="Test media share to story")
            self.assertIsInstance(story, Story)
            self.assertTrue(story)
            self.assertUploadedStoryAccessible(story, media_type=1)
            uploaded_story = self.uploaded_story_with_media(story, media_pk)
            self.assertEqual(str(uploaded_story.id), str(story.id))
        finally:
            if story:
                self.assertTrue(self.cl.story_delete(story.id))

    def test_upload_video_story(self):
        media_pk = self.story_sticker_media_pk()
        story = None
        path = self.make_story_mp4()
        self.assertIsInstance(path, Path)
        caption = "Test video caption"
        instagram = self.user_info_by_username("instagram")
        self.assertIsInstance(instagram, User)
        mentions = [StoryMention(user=self.user_short(instagram))]
        medias = [StoryMedia(media_pk=media_pk, x=0.5, y=0.5, width=0.6, height=0.8)]
        links = [StoryLink(webUri="https://instagram.com/")]
        # hashtags = [StoryHashtag(hashtag=self.cl.hashtag_info('instagram'))]
        # locations = [
        #     StoryLocation(
        #         location=Location(
        #             pk=150300262230285,
        #             name='Blaues Wunder (Dresden)',
        #         )
        #     )
        # ]
        try:
            story = self.cl.video_upload_to_story(
                path,
                caption,
                mentions=mentions,
                links=links,
                # hashtags=hashtags,
                # locations=locations,
                medias=medias,
            )
            self.assertIsInstance(story, Story)
            self.assertTrue(story)
            self.assertUploadedStoryAccessible(story, media_type=2)
        finally:
            if story:
                self.assertTrue(self.cl.story_delete(story.id))

    def test_user_stories(self):
        user_id = self.user_id_from_username("instagram")
        stories = self.cl.user_stories(user_id, 2)
        self.assertEqual(len(stories), 2)
        story = stories[0]
        self.assertIsInstance(story, Story)
        for field in REQUIRED_STORY_FIELDS:
            self.assertTrue(hasattr(story, field))
        stories = self.cl.user_stories(self.user_id_from_username("instagram"))
        self.assertIsInstance(stories, list)

    def test_extract_user_stories(self):
        user_id = self.user_id_from_username("instagram")
        stories_v1 = self.cl.user_stories_v1(user_id, amount=2)
        stories_gql = self.cl.user_stories_gql(user_id, amount=2)
        self.assertEqual(len(stories_v1), 2)
        self.assertIsInstance(stories_v1[0], Story)
        self.assertEqual(len(stories_gql), 2)
        self.assertIsInstance(stories_gql[0], Story)
        for i, gql in enumerate(stories_gql[:2]):
            gql = gql.dict()
            v1 = stories_v1[i].dict()
            for f in REQUIRED_STORY_FIELDS:
                gql_val, v1_val = gql[f], v1[f]
                is_video = v1.get("video_duration") > 0
                if f == "video_url" and is_video:
                    gql_val = gql[f].path.rsplit(".", 1)[1]
                    v1_val = v1[f].path.rsplit(".", 1)[1]
                elif f == "thumbnail_url":
                    self.assertIn(".jpg", gql_val)
                    self.assertIn(".jpg", v1_val)
                    continue
                elif f == "user":
                    gql_val.pop("full_name")
                    v1_val.pop("full_name")
                    gql_val.pop("is_private")
                    v1_val.pop("is_private")
                    gql_val["profile_pic_url"] = gql_val["profile_pic_url"].path
                    v1_val["profile_pic_url"] = v1_val["profile_pic_url"].path
                elif f == "mentions":
                    for item in [*gql_val, *v1_val]:
                        item["user"].pop("pk")
                        item["user"].pop("profile_pic_url")
                        item.pop("width")
                        item.pop("height")
                        item["x"] = round(item["x"], 4)
                        item["y"] = round(item["y"], 4)
                elif f == "links":
                    # [{'webUri': HttpUrl('https://youtu.be/x3GYpar-e64', scheme='https', host='youtu.be', tld='be', host_type='domain', path='/x3GYpar-e64')}]
                    # [{'webUri': HttpUrl('https://l.instagram.com/?u=https%3A%2F%2Fyoutu.be%2Fx3GYpar-e64&e=ATM59nvUNmptw8vUsyoX835T....}]
                    self.assertEqual(len(v1_val), len(gql_val))
                    if gql_val:
                        self.assertIn(gql_val[0]["webUri"].host, v1_val[0]["webUri"].query)
                    continue
                if gql_val != v1_val:
                    import pudb

                    pudb.set_trace()
                self.assertEqual(gql_val, v1_val)

    def test_story_info(self):
        user_id = self.user_id_from_username("instagram")
        stories = self.cl.user_stories(user_id, amount=1)
        story = self.cl.story_info(stories[0].pk)
        self.assertIsInstance(story, Story)
        story = self.cl.story_info(stories[0].id)
        self.assertIsInstance(story, Story)
        self.assertTrue(self.cl.story_seen([story.pk]))


class ClientUserStoriesLiveTestCase(_helpers.ClientPrivateTestCase):
    def __init__(self, *args, **kwargs):
        self.cl = None
        return unittest.TestCase.__init__(self, *args, **kwargs)

    def setup_method(self, *args, **kwargs):
        return None

    def setUp(self):
        if not TEST_ACCOUNTS_URL:
            self.skipTest("TEST_ACCOUNTS_URL is required for user stories live tests")
        try:
            self.cl = self.fresh_account()
        except Exception as exc:
            self.skipTest(str(exc))

    def test_user_stories_uses_private_api_live(self):
        user_id = self.user_id_from_username("instagram")

        with mock.patch.object(
            self.cl,
            "user_stories_gql",
            side_effect=AssertionError("authorized user_stories should not call public GraphQL first"),
        ) as public_lookup:
            stories = self.cl.user_stories(user_id, amount=1)

        self.assertGreater(len(stories), 0)
        self.assertIsInstance(stories[0], Story)
        public_lookup.assert_not_called()


class ClientStoryLocationStickerLiveTestCase(_helpers.ClientPrivateTestCase):
    photo_path = Path("examples/background.png")

    def __init__(self, *args, **kwargs):
        self.cl = None
        return unittest.TestCase.__init__(self, *args, **kwargs)

    def setup_method(self, *args, **kwargs):
        return None

    def setUp(self):
        if not TEST_ACCOUNTS_URL:
            self.skipTest("TEST_ACCOUNTS_URL is required for story location sticker live tests")
        try:
            self.cl = self.fresh_account()
        except Exception as exc:
            self.skipTest(str(exc))

    def get_location(self):
        location = self.cl.location_search(lat=59.939095, lng=30.315868)[0]
        self.assertIsInstance(location, Location)
        return location

    def story_info_with_locations(self, story_pk):
        last_story = None
        for _ in range(5):
            last_story = self.cl.story_info(story_pk)
            self.assertIsInstance(last_story, Story)
            if last_story.locations:
                return last_story
            time.sleep(3)
        return last_story

    def user_story_ids(self):
        return {story.id for story in self.cl.user_stories(self.cl.user_id, amount=10)}

    def uploaded_story(self, existing_story_ids):
        for _ in range(5):
            for story in self.cl.user_stories(self.cl.user_id, amount=10):
                if story.id not in existing_story_ids:
                    return story
            time.sleep(3)
        return None

    def cleanup_uploaded_story(self, story):
        if not story:
            return
        try:
            self.assertTrue(self.cl.story_delete(story.id))
        except Exception as exc:
            print(f"Story location sticker live cleanup story_delete failed: {exc.__class__.__name__} {exc}")

    def test_photo_story_location_sticker_round_trips_live(self):
        location = self.get_location()
        story = None
        existing_story_ids = self.user_story_ids()
        try:
            upload_id, width, height = self.cl.photo_rupload(self.photo_path, for_story=True)
            time.sleep(3)
            configured = self.cl.photo_configure_to_story(
                upload_id=upload_id,
                width=width,
                height=height,
                caption="Story location sticker live test",
                locations=[
                    StoryLocation(
                        location=location,
                        x=0.5,
                        y=0.5,
                        width=0.5,
                        height=0.1,
                    )
                ],
            )
            self.assertEqual(configured.get("status"), "ok")

            story = self.uploaded_story(existing_story_ids)
            self.assertIsInstance(story, Story)
            info = self.story_info_with_locations(story.pk)
            self.assertTrue(info.locations)
            self.assertIsInstance(info.locations[0].location, Location)
            self.assertTrue(info.locations[0].location.name)
        finally:
            self.cleanup_uploaded_story(story)


def _run_photo_story_interactive_metadata_live(result_queue):
    if not TEST_ACCOUNTS_URL:
        result_queue.put({"status": "skip", "reason": "TEST_ACCOUNTS_URL is required for story metadata live tests"})
        return

    cl = None
    story = None
    try:
        cl = fresh_test_account(count=3, attempts=3, timeout=30)
        account = cl.account_info()
        user = UserShort(
            pk=account.pk,
            username=account.username,
            full_name=account.full_name,
            profile_pic_url=account.profile_pic_url,
            is_private=account.is_private,
        )
        locations = cl.location_search(lat=59.939095, lng=30.315868)
        if not locations:
            result_queue.put({"status": "skip", "reason": "location_search returned no locations"})
            return
        hashtag = cl.hashtag_info("instagram")
        existing_story_ids = {item.id for item in cl.user_stories_v1(cl.user_id, amount=20)}

        story = cl.photo_upload_to_story(
            Path("examples/background.png"),
            "Story interactive metadata live test",
            mentions=[StoryMention(user=user, x=0.5, y=0.35, width=0.5, height=0.1)],
            links=[StoryLink(webUri="https://github.com/subzeroid/instagrapi")],
            hashtags=[StoryHashtag(hashtag=hashtag, x=0.5, y=0.45, width=0.4, height=0.1)],
            locations=[StoryLocation(location=locations[0], x=0.5, y=0.55, width=0.5, height=0.1)],
        )

        uploaded_story = None
        for attempt in range(8):
            if attempt:
                time.sleep(3)
            for candidate in cl.user_stories_v1(cl.user_id, amount=20):
                if candidate.id == story.id or candidate.id not in existing_story_ids:
                    uploaded_story = candidate
                    break
            if uploaded_story and (
                uploaded_story.mentions
                and uploaded_story.links
                and uploaded_story.hashtags
                and uploaded_story.locations
            ):
                break

        result_queue.put(
            {
                "status": "ok",
                "story_id": story.id,
                "uploaded_story_id": uploaded_story.id if uploaded_story else None,
                "mention_users": [mention.user.username for mention in uploaded_story.mentions]
                if uploaded_story
                else [],
                "link_urls": [str(link.webUri) for link in uploaded_story.links] if uploaded_story else [],
                "hashtag_names": [item.hashtag.name for item in uploaded_story.hashtags] if uploaded_story else [],
                "location_names": [item.location.name for item in uploaded_story.locations] if uploaded_story else [],
            }
        )
    except Exception:
        result_queue.put({"status": "error", "traceback": traceback.format_exc()})
    finally:
        if cl and story:
            try:
                cl.story_delete(story.id)
            except Exception as exc:
                print(f"Story metadata live cleanup story_delete failed: {exc.__class__.__name__} {exc}")


def _is_instagrapi_github_link(url):
    parsed = urlparse(url)
    if parsed.netloc == "github.com" and parsed.path == "/subzeroid/instagrapi":
        return True
    target_urls = parse_qs(parsed.query).get("u") or []
    for target_url in target_urls:
        target = urlparse(target_url)
        if target.netloc == "github.com" and target.path == "/subzeroid/instagrapi":
            return True
    return False


class ClientStoryInteractiveMetadataLiveTestCase(unittest.TestCase):
    def run_story_metadata_worker(self):
        if not TEST_ACCOUNTS_URL:
            self.skipTest("TEST_ACCOUNTS_URL is required for story metadata live tests")
        ctx = multiprocessing.get_context("spawn")
        result_queue = ctx.Queue()
        process = ctx.Process(target=_run_photo_story_interactive_metadata_live, args=(result_queue,))
        process.start()
        timeout = int(os.getenv("INSTAGRAPI_STORY_METADATA_LIVE_TIMEOUT", "180"))
        process.join(timeout)
        if process.is_alive():
            process.terminate()
            process.join(10)
            self.skipTest(f"Story metadata live workflow timed out after {timeout} seconds")
        try:
            return result_queue.get(timeout=5)
        except queue.Empty:
            if process.exitcode:
                self.fail(f"Story metadata live workflow exited with code {process.exitcode}")
            self.fail("Story metadata live workflow did not return a result")

    def test_photo_story_interactive_metadata_round_trips_live(self):
        result = self.run_story_metadata_worker()
        if result["status"] == "skip":
            self.skipTest(result["reason"])
        if result["status"] == "error":
            self.fail(result["traceback"])
        self.assertEqual(result["story_id"], result["uploaded_story_id"])
        self.assertTrue(result["mention_users"])
        self.assertTrue(result["link_urls"])
        self.assertTrue(result["hashtag_names"])
        self.assertTrue(result["location_names"])
        self.assertIn("instagram", result["hashtag_names"])
        self.assertTrue(any(_is_instagrapi_github_link(url) for url in result["link_urls"]))


class ClientStoryMusicUploadLiveTestCase(_helpers.ClientPrivateTestCase):
    photo_path = Path("examples/background.png")

    def __init__(self, *args, **kwargs):
        self.cl = None
        return unittest.TestCase.__init__(self, *args, **kwargs)

    def setup_method(self, *args, **kwargs):
        return None

    def setUp(self):
        if not TEST_ACCOUNTS_URL:
            self.skipTest("TEST_ACCOUNTS_URL is required for story music upload live tests")
        try:
            self.cl = self.fresh_account()
        except RuntimeError as exc:
            self.skipTest(str(exc))

    def first_music_track(self):
        tracks = self.cl.search_music("Runaway")
        if not tracks:
            self.skipTest("search_music did not return a usable track")
        return tracks[0]

    def make_silent_story_mp4(self, duration=4):
        try:
            import imageio_ffmpeg
        except ImportError:
            self.skipTest("imageio_ffmpeg is required to generate a silent Story fixture")

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
                    f"color=c=black:s=720x1280:r=30:d={duration}",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    str(path),
                ],
                check=True,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            self.skipTest(f"Could not generate silent Story fixture: {exc}")
        return path

    def cleanup_uploaded_story(self, story):
        if not story:
            return
        try:
            self.assertTrue(self.cl.story_delete(story.id))
        except Exception as exc:
            print(f"Story music upload live cleanup story_delete failed: {exc.__class__.__name__} {exc}")

    def uploaded_story_payload(self, story, attempts=8, delay=5):
        last_items = []
        for attempt in range(attempts):
            if attempt:
                time.sleep(delay)
            result = self.cl.private_request(f"feed/user/{self.cl.user_id}/story/")
            reel = result.get("reel") or {}
            last_items = reel.get("items") or []
            for item in last_items:
                if str(item.get("pk")) == str(story.pk) or str(item.get("id")) == str(story.id):
                    return item
        self.fail(f"Uploaded story payload was not visible after {attempts} attempts: {last_items}")

    def download_story_video(self, story):
        info = self.assertUploadedStoryAccessible(story, media_type=2, attempts=8, delay=5)
        self.assertTrue(info.video_url, "Uploaded story did not expose video_url")
        video_path = self.cl.video_download_by_url(str(info.video_url), f"story-{story.pk}", tempfile.gettempdir())
        self.addCleanup(lambda: Path(video_path).unlink(missing_ok=True))
        return info, Path(video_path)

    def assert_video_file_has_audio_stream(self, path):
        try:
            import imageio_ffmpeg
        except ImportError:
            self.skipTest("imageio_ffmpeg is required to inspect uploaded Story audio")
        result = subprocess.run(
            [imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-i", str(path)],
            check=False,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
        streams = result.stderr.decode("utf-8", errors="replace")
        self.assertIn("Audio:", streams)

    def assert_story_music_result(self, story, expected_duration):
        info, downloaded_video = self.download_story_video(story)
        self.assertGreater(info.video_duration, 0)
        self.assertLess(abs(info.video_duration - expected_duration), 1.5)
        payload = self.uploaded_story_payload(story)
        self.assertEqual(payload.get("media_type"), 2)
        self.assertTrue(payload.get("video_versions"), "Uploaded Story payload did not include video_versions")
        self.assert_video_file_has_audio_stream(downloaded_video)
        return payload

    def test_video_upload_to_story_with_music_live(self):
        path = self.make_silent_story_mp4(duration=4)
        track = self.first_music_track()
        story = None
        try:
            story = self.cl.video_upload_to_story_with_music(
                path,
                "Story video music live test",
                track,
                overlap_duration=4000,
            )
            self.assertIsInstance(story, Story)
            self.assertEqual(story.media_type, 2)
            self.assert_story_music_result(story, expected_duration=4)
        finally:
            self.cleanup_uploaded_story(story)

    def test_photo_upload_to_story_with_music_live(self):
        track = self.first_music_track()
        story = None
        try:
            story = self.cl.photo_upload_to_story_with_music(
                self.photo_path,
                "Story photo music live test",
                track,
                duration=7,
                overlap_duration=7000,
            )
            self.assertIsInstance(story, Story)
            self.assertEqual(story.media_type, 2)
            self.assert_story_music_result(story, expected_duration=7)
        finally:
            self.cleanup_uploaded_story(story)


# class BloksTestCase(_helpers.ClientPrivateTestCase):
#
#     def test_bloks_change_password(self):
#         last_json = {
#             'step_name': 'change_password',
#             'step_data': {'new_password1': 'None', 'new_password2': 'None'},
#             'flow_render_type': 3,
#             'bloks_action': 'com.instagram.challenge.navigation.take_challenge',
#             'cni': 12346879508000123,
#             'challenge_context': '{"step_name": "change_password", "cni": 12346879508000123, "is_stateless": false, "challenge_type_enum": "PASSWORD_RESET"}',
#             'challenge_type_enum_str': 'PASSWORD_RESET',
#             'status': 'ok'
#         }
#        self.assertTrue(self.cl.bloks_change_password("2r9j20r9j4230t8hj39tHW4"))
