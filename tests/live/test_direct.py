from instagrapi.exceptions import DirectMessageNotFound
from tests import helpers as _helpers
from tests.helpers import *


class ClientDirectTestCase(_helpers.ClientPrivateTestCase):
    def test_direct_thread(self):
        # threads
        threads = self.cl.direct_threads()
        self.assertTrue(len(threads) > 0)
        thread = threads[0]
        self.assertIsInstance(thread, DirectThread)
        # messages
        messages = self.cl.direct_messages(thread.id, 2)
        self.assertTrue(3 > len(messages) > 0)
        # self.assertTrue(thread.is_seen(self.cl.user_id))
        message = messages[0]
        self.assertIsInstance(message, DirectMessage)
        instagram = self.user_id_from_username("instagram")
        ping = self.cl.direct_send("Ping", user_ids=[instagram])
        self.assertIsInstance(ping, DirectMessage)
        pong = self.cl.direct_answer(ping.thread_id, "Pong")
        self.assertIsInstance(pong, DirectMessage)
        self.assertEqual(ping.thread_id, pong.thread_id)
        # send direct photo
        photo = self.cl.direct_send_photo(path="examples/kanada.jpg", user_ids=[instagram])
        self.assertIsInstance(photo, DirectMessage)
        self.assertEqual(photo.thread_id, pong.thread_id)
        # send seen
        seen = self.cl.direct_send_seen(thread_id=thread.id)
        self.assertEqual(seen.status, "ok")
        # mute and unmute thread
        self.assertTrue(self.cl.direct_thread_mute(thread.id))
        self.assertTrue(self.cl.direct_thread_unmute(thread.id))
        # mute video call and unmute
        self.assertTrue(self.cl.direct_thread_mute_video_call(thread.id))
        self.assertTrue(self.cl.direct_thread_unmute_video_call(thread.id))

    def test_direct_send_photo(self):
        instagram = self.user_id_from_username("instagram")
        dm = self.cl.direct_send_photo(path="examples/kanada.jpg", user_ids=[instagram])
        self.assertIsInstance(dm, DirectMessage)

    def test_direct_send_accepts_scalar_user_id_live(self):
        instagram = self.user_id_from_username("instagram")
        dm = self.cl.direct_send("Scalar recipient ping", user_ids=instagram)
        self.assertIsInstance(dm, DirectMessage)

    def test_direct_media_share(self):
        instagram = self.user_id_from_username("instagram")
        media = next(media for media in self.cl.user_medias(instagram, amount=5) if media.id)
        media_type = "video" if media.media_type == 2 else "photo"
        dm = None
        try:
            dm = self.cl.direct_media_share(media.id, user_ids=[instagram], media_type=media_type)
            self.assertIsInstance(dm, DirectMessage)
            self.assertTrue(dm.id)
            self.assertTrue(dm.thread_id)

            shared = None
            for _ in range(6):
                try:
                    shared = self.cl.direct_message(dm.thread_id, dm.id, amount=10)
                except DirectMessageNotFound:
                    time.sleep(2)
                    continue
                if shared.media_share or shared.xma_share or shared.raw_xma:
                    break
                time.sleep(2)
            self.assertIsNotNone(shared)
            self.assertTrue(shared.media_share or shared.xma_share or shared.raw_xma)
        finally:
            if dm and dm.thread_id:
                try:
                    self.cl.direct_message_unsend(dm.thread_id, dm.id)
                    self.cl.direct_thread_hide(dm.thread_id)
                except Exception as exc:
                    logger.warning("Direct media share cleanup failed: %s", exc)

    def test_direct_send_video(self):
        instagram = self.user_id_from_username("instagram")
        path = self.cl.video_download(self.cl.media_pk_from_url("https://www.instagram.com/p/B3rFQPblq40/"))
        dm = self.cl.direct_send_video(path=path, user_ids=[instagram])
        self.assertIsInstance(dm, DirectMessage)

    def test_direct_thread_by_participants(self):
        try:
            self.cl.direct_thread_by_participants([12345])
        except DirectThreadNotFound:
            pass


class ClientDirectMediaLiveTestCase(_helpers.ClientPrivateTestCase):
    def __init__(self, *args, **kwargs):
        self.cl = None
        return unittest.TestCase.__init__(self, *args, **kwargs)

    def setUp(self):
        if not TEST_ACCOUNTS_URL:
            self.skipTest("TEST_ACCOUNTS_URL is required for direct media live tests")
        self.cl = self.fresh_account()

    def make_media_fixture(self, suffix, args):
        try:
            import imageio_ffmpeg
        except ImportError:
            self.skipTest("imageio_ffmpeg is required to generate media fixtures")

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            path = Path(tmp.name)
        self.addCleanup(lambda: path.unlink(missing_ok=True))

        try:
            subprocess.run(
                [imageio_ffmpeg.get_ffmpeg_exe(), "-y", *args, str(path)],
                check=True,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            self.skipTest(f"Could not generate {suffix} fixture: {exc}")
        return path

    def make_voice_m4a(self):
        return self.make_media_fixture(
            ".m4a",
            [
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=880:duration=1",
                "-c:a",
                "aac",
                "-b:a",
                "64k",
                "-ac",
                "1",
                "-ar",
                "44100",
            ],
        )

    def make_video_mp4(self):
        return self.make_media_fixture(
            ".mp4",
            [
                "-f",
                "lavfi",
                "-i",
                "color=c=blue:s=320x568:r=30:d=1",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:duration=1",
                "-shortest",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "64k",
            ],
        )

    def thread_id_by_participants(self, client, user_id):
        thread = client.direct_thread_by_participants([user_id])
        thread_id = thread.get("thread_v2_id") or thread.get("thread_id")
        if not thread_id and isinstance(client.last_json, dict):
            last_thread = client.last_json.get("thread") or {}
            thread_id = last_thread.get("thread_v2_id") or last_thread.get("thread_id")
        return thread_id

    def cleanup_direct_media_messages(self, thread_id, messages, clients):
        for client, message in messages:
            if not getattr(message, "id", None):
                continue
            try:
                client.direct_message_unsend(thread_id, message.id)
            except Exception as exc:
                print(f"Direct media live cleanup direct_message_unsend failed: {exc.__class__.__name__} {exc}")
        for client in clients:
            try:
                client.direct_thread_hide(thread_id)
            except Exception as exc:
                print(f"Direct media live cleanup direct_thread_hide failed: {exc.__class__.__name__} {exc}")

    def direct_message_by_id(self, client, thread_id, message_id, amount=10):
        try:
            return client.direct_message(thread_id, message_id, amount=amount)
        except DirectMessageNotFound:
            return None

    def direct_message_has_reaction(self, message, sender_id, emoji="❤"):
        reactions = getattr(message, "reactions", None)
        for reaction in getattr(reactions, "emojis", []) or []:
            if str(reaction.sender_id) == str(sender_id) and reaction.emoji == emoji:
                return True
        return False

    def test_direct_message_reaction_live(self):
        sender = self.cl
        recipient = self.fresh_accounts(1, exclude_user_ids={sender.user_id})[0]
        sent_messages = []
        thread_id = None

        try:
            seed_message = sender.direct_send(
                f"instagrapi direct reaction live {int(time.time())}",
                user_ids=[recipient.user_id],
            )
            self.assertIsInstance(seed_message, DirectMessage)
            sent_messages.append((sender, seed_message))

            thread_id = seed_message.thread_id or self.thread_id_by_participants(sender, recipient.user_id)
            self.assertTrue(thread_id)

            reply_message = recipient.direct_answer(
                thread_id,
                f"instagrapi direct reaction ack {int(time.time())}",
            )
            self.assertIsInstance(reply_message, DirectMessage)
            sent_messages.append((recipient, reply_message))

            target_message = None
            for _ in range(6):
                target_message = self.direct_message_by_id(recipient, thread_id, seed_message.id)
                if target_message:
                    break
                time.sleep(2)
            self.assertIsNotNone(target_message)

            self.assertTrue(recipient.direct_send_reaction(thread_id, seed_message.id))

            reacted_message = None
            for _ in range(6):
                reacted_message = self.direct_message_by_id(sender, thread_id, seed_message.id)
                if reacted_message and self.direct_message_has_reaction(reacted_message, recipient.user_id):
                    break
                time.sleep(3)
            else:
                self.fail(f"Direct reaction was not visible: {getattr(reacted_message, 'reactions', None)}")

            self.assertTrue(recipient.direct_message_unlike(thread_id, seed_message.id))

            cleared_message = None
            for _ in range(6):
                cleared_message = self.direct_message_by_id(sender, thread_id, seed_message.id)
                if cleared_message and not self.direct_message_has_reaction(cleared_message, recipient.user_id):
                    break
                time.sleep(3)
            else:
                self.fail(f"Direct reaction was still visible: {getattr(cleared_message, 'reactions', None)}")
        finally:
            if thread_id:
                self.cleanup_direct_media_messages(thread_id, sent_messages, [sender, recipient])

    def test_direct_send_voice_and_video_with_thread_and_user_ids(self):
        sender = self.cl
        recipient = self.fresh_accounts(1, exclude_user_ids={sender.user_id})[0]
        voice_path = self.make_voice_m4a()
        video_path = self.make_video_mp4()
        sent_messages = []
        thread_id = None

        try:
            seed_message = sender.direct_send(
                f"instagrapi direct media live warm {int(time.time())}",
                user_ids=[recipient.user_id],
            )
            self.assertIsInstance(seed_message, DirectMessage)
            sent_messages.append((sender, seed_message))

            thread_id = seed_message.thread_id or self.thread_id_by_participants(sender, recipient.user_id)
            self.assertTrue(thread_id)

            reply_message = recipient.direct_send(
                f"instagrapi direct media live reply {int(time.time())}",
                user_ids=[sender.user_id],
            )
            self.assertIsInstance(reply_message, DirectMessage)
            sent_messages.append((recipient, reply_message))

            thread_voice = sender.direct_send_voice(voice_path, thread_ids=[thread_id])
            self.assertIsInstance(thread_voice, DirectMessage)
            self.assertTrue(thread_voice.id)
            sent_messages.append((sender, thread_voice))

            user_voice = sender.direct_send_voice(voice_path, user_ids=[recipient.user_id])
            self.assertIsInstance(user_voice, DirectMessage)
            self.assertTrue(user_voice.id)
            sent_messages.append((sender, user_voice))

            thread_video = sender.direct_send_video(video_path, thread_ids=[thread_id])
            self.assertIsInstance(thread_video, DirectMessage)
            self.assertTrue(thread_video.id)
            sent_messages.append((sender, thread_video))

            user_video = sender.direct_send_video(video_path, user_ids=[recipient.user_id])
            self.assertIsInstance(user_video, DirectMessage)
            self.assertTrue(user_video.id)
            sent_messages.append((sender, user_video))
        finally:
            if thread_id:
                self.cleanup_direct_media_messages(thread_id, sent_messages, [sender, recipient])


class ClientDirectThreadLiveTestCase(_helpers.ClientPrivateTestCase):
    def __init__(self, *args, **kwargs):
        self.cl = None
        self.recipient_clients = []
        return unittest.TestCase.__init__(self, *args, **kwargs)

    def setUp(self):
        if not TEST_ACCOUNTS_URL:
            self.skipTest("TEST_ACCOUNTS_URL is required for direct thread live tests")
        accounts = self.fresh_accounts(4)
        self.cl = accounts[0]
        self.recipient_clients = accounts[1:3]
        self.add_client = accounts[3]

    def test_direct_thread_update_title_live(self):
        initial_title = f"instagrapi-title-{int(time.time())}"
        updated_title = f"{initial_title}-updated"
        thread_id = None

        try:
            thread_id = self.cl.direct_thread_create(
                [int(client.user_id) for client in self.recipient_clients],
                title=initial_title,
            )
            self.assertTrue(thread_id)

            self.assertTrue(self.cl.direct_thread_update_title(thread_id, updated_title))
            thread = self.cl.direct_thread(thread_id, amount=1)
            self.assertEqual(thread.thread_title, updated_title)
        finally:
            if thread_id:
                try:
                    self.cl.direct_thread_hide(thread_id)
                except Exception as exc:
                    logger.warning("Direct thread cleanup failed: %s", exc)

    def test_direct_thread_add_users_live(self):
        title = f"instagrapi-add-users-{int(time.time())}"
        thread_id = None

        try:
            thread_id = self.cl.direct_thread_create(
                [int(client.user_id) for client in self.recipient_clients],
                title=title,
            )
            self.assertTrue(thread_id)

            self.assertTrue(self.cl.direct_thread_add_users(thread_id, [int(self.add_client.user_id)]))
            thread = self.cl.direct_thread(thread_id, amount=1)
            user_ids = {str(user.pk) for user in thread.users}
            self.assertIn(str(self.add_client.user_id), user_ids)
        finally:
            if thread_id:
                try:
                    self.cl.direct_thread_hide(thread_id)
                except Exception as exc:
                    logger.warning("Direct thread cleanup failed: %s", exc)


class ClientDirectMessageTypesTestCase(_helpers.ClientPrivateTestCase):
    """Test that DirectMessage and DirectThread fields use structured Pydantic models instead of raw dictionaries"""

    def test_direct_message_reactions_model(self):
        """Test that DirectMessage.reactions field uses MessageReactions model"""
        from datetime import datetime

        from instagrapi.types import MessageReaction, MessageReactions

        # Get some direct messages
        threads = self.cl.direct_threads(amount=5)
        if not threads:
            self.skipTest("No direct threads available for testing")

        for thread in threads:
            messages = self.cl.direct_messages(thread.id, amount=10)
            for message in messages:
                if message.reactions:
                    # Test that reactions field is now a MessageReactions object
                    self.assertIsInstance(message.reactions, MessageReactions)

                    # Test that reactions have proper structure
                    if hasattr(message.reactions, "emojis") and message.reactions.emojis:
                        for emoji_reaction in message.reactions.emojis:
                            self.assertIsInstance(emoji_reaction, MessageReaction)
                            self.assertIsInstance(emoji_reaction.emoji, str)
                            self.assertIsInstance(emoji_reaction.sender_id, str)
                            self.assertIsInstance(emoji_reaction.timestamp, datetime)

                    # Test backward compatibility - should still work as dict
                    if hasattr(message.reactions, "likes_count"):
                        self.assertIsInstance(message.reactions.likes_count, int)

                    return  # Found one message with reactions, test passed

    def test_direct_message_link_model(self):
        """Test that DirectMessage.link field uses MessageLink model"""
        from instagrapi.types import LinkContext, MessageLink

        # Get some direct messages
        threads = self.cl.direct_threads(amount=5)
        if not threads:
            self.skipTest("No direct threads available for testing")

        for thread in threads:
            messages = self.cl.direct_messages(thread.id, amount=10)
            for message in messages:
                if message.link:
                    # Test that link field is now a MessageLink object
                    self.assertIsInstance(message.link, MessageLink)

                    # Test that link has proper structure
                    if hasattr(message.link, "text"):
                        self.assertIsInstance(message.link.text, str)

                    if hasattr(message.link, "link_context") and message.link.link_context:
                        self.assertIsInstance(message.link.link_context, LinkContext)
                        if hasattr(message.link.link_context, "link_url"):
                            self.assertIsInstance(message.link.link_context.link_url, str)

                    return  # Found one message with link, test passed

    def test_direct_message_visual_media_model(self):
        """Test that DirectMessage.visual_media field uses VisualMedia model"""
        from instagrapi.types import VisualMedia, VisualMediaContent

        # Get some direct messages
        threads = self.cl.direct_threads(amount=5)
        if not threads:
            self.skipTest("No direct threads available for testing")

        for thread in threads:
            messages = self.cl.direct_messages(thread.id, amount=10)
            for message in messages:
                if message.visual_media:
                    # Test that visual_media field is now a VisualMedia object
                    self.assertIsInstance(message.visual_media, VisualMedia)

                    # Test that visual_media has proper structure
                    if hasattr(message.visual_media, "media") and message.visual_media.media:
                        self.assertIsInstance(message.visual_media.media, VisualMediaContent)

                    return  # Found one message with visual media, test passed

    def test_direct_thread_last_seen_at_model(self):
        """Test that DirectThread.last_seen_at field uses LastSeenInfo model"""
        from datetime import datetime

        from instagrapi.types import LastSeenInfo

        # Get some direct threads
        threads = self.cl.direct_threads(amount=5)
        if not threads:
            self.skipTest("No direct threads available for testing")

        for thread in threads:
            if thread.last_seen_at:
                # Test that last_seen_at is now a dict of LastSeenInfo objects
                for user_id, seen_info in thread.last_seen_at.items():
                    self.assertIsInstance(user_id, str)
                    self.assertIsInstance(seen_info, LastSeenInfo)

                    # Test structure of LastSeenInfo
                    if hasattr(seen_info, "timestamp"):
                        self.assertIsInstance(seen_info.timestamp, datetime)
                    if hasattr(seen_info, "created_at"):
                        self.assertIsInstance(seen_info.created_at, datetime)

                    return  # Found one thread with last_seen_at, test passed

    def test_direct_message_clips_metadata_model(self):
        """Test that DirectMessage.clips_metadata field uses ClipsMetadata model"""
        from instagrapi.types import ClipsMetadata

        # Get some direct messages
        threads = self.cl.direct_threads(amount=5)
        if not threads:
            self.skipTest("No direct threads available for testing")

        for thread in threads:
            messages = self.cl.direct_messages(thread.id, amount=10)
            for message in messages:
                if message.clips_metadata:
                    # Test that clips_metadata field is now a ClipsMetadata object
                    self.assertIsInstance(message.clips_metadata, ClipsMetadata)

                    return  # Found one message with clips metadata, test passed

    def test_thread_is_seen_datetime_compatibility(self):
        """Test that DirectThread.is_seen() works with datetime objects"""

        # Get some direct threads
        threads = self.cl.direct_threads(amount=5)
        if not threads:
            self.skipTest("No direct threads available for testing")

        for thread in threads:
            if thread.last_seen_at:
                # Test that is_seen method works with datetime objects
                user_id = str(self.cl.user_id)
                try:
                    is_seen = thread.is_seen(user_id)
                    self.assertIsInstance(is_seen, bool)
                    return  # Successfully tested is_seen method
                except Exception as e:
                    self.fail(f"is_seen() method failed with datetime objects: {e}")

    def test_backward_compatibility_dict_access(self):
        """Test that dict-style access patterns still work for backward compatibility"""
        # Get some direct messages
        threads = self.cl.direct_threads(amount=5)
        if not threads:
            self.skipTest("No direct threads available for testing")

        for thread in threads:
            messages = self.cl.direct_messages(thread.id, amount=10)
            for message in messages:
                # Test that we can still access fields as if they were dicts
                # This should work due to our Pydantic model structure
                try:
                    if message.reactions:
                        # Should work even though it's now a Pydantic model
                        likes_count = getattr(message.reactions, "likes_count", 0)
                        self.assertIsInstance(likes_count, int)

                    if message.link:
                        # Should work even though it's now a Pydantic model
                        link_text = getattr(message.link, "text", "")
                        self.assertIsInstance(link_text, str)

                    return  # Successfully tested backward compatibility
                except Exception as e:
                    self.fail(f"Backward compatibility test failed: {e}")
