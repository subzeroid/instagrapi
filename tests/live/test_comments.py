from instagrapi.exceptions import (
    ClientForbiddenError,
    ClientGraphqlError,
    ClientLoginRequired,
    ClientThrottledError,
    ClientUnauthorizedError,
)
from tests import helpers as _helpers
from tests.helpers import *


class ClientPublicCommentTestCase(unittest.TestCase):
    def test_media_comments_public_gql_live(self):
        code = "C_BM2yAN4Rm"
        transports = ["requests"]
        try:
            import curl_adapter  # noqa: F401
        except ImportError:
            pass
        else:
            transports.append("curl")

        errors = []
        for transport in transports:
            client = Client(public_transport=transport, request_timeout=0, public_request_retries_count=1)
            try:
                comments = client.media_comments_public_gql(code, amount=3, max_requests=1)
            except (
                ClientForbiddenError,
                ClientGraphqlError,
                ClientLoginRequired,
                ClientThrottledError,
                ClientUnauthorizedError,
            ) as exc:
                errors.append(f"{transport}: {exc.__class__.__name__}")
                continue
            break
        else:
            self.skipTest("Instagram public comments endpoint is gated: " + "; ".join(errors))

        self.assertTrue(comments)
        self.assertLessEqual(len(comments), 3)
        self.assertTrue(comments[0].get("id") or comments[0].get("pk"))
        self.assertTrue(comments[0].get("text"))


class ClientCommentTestCase(_helpers.ClientPrivateTestCase):
    def test_media_comments_amount(self):
        comments = self.cl.media_comments_v1(2154602296692269830, amount=2)
        self.assertTrue(len(comments) == 2)
        comments = self.cl.media_comments_v1(2154602296692269830, amount=0)
        self.assertTrue(len(comments) > 2)

    def test_media_comments(self):
        comments = self.cl.media_comments_v1(2154602296692269830)
        self.assertTrue(len(comments) > 5)
        comment = comments[0]
        self.assertIsInstance(comment, Comment)
        comment_fields = comment.__fields__.keys()
        user_fields = comment.user.__fields__.keys()
        for field in ["pk", "text", "created_at_utc", "content_type", "status", "user"]:
            self.assertIn(field, comment_fields)
        for field in [
            "pk",
            "username",
            "full_name",
            "profile_pic_url",
        ]:
            self.assertIn(field, user_fields)


class ClientCommentRepliesLiveTestCase(_helpers.ClientPrivateTestCase):
    def test_media_comment_replies_live(self):
        errors = []
        for media_id, comment_id in COMMENT_REPLIES_LIVE_FIXTURES:
            try:
                replies = self.cl.media_comment_replies(media_id, comment_id, amount=1)
            except ClientError as e:
                errors.append(f"{media_id}/{comment_id}: {e.__class__.__name__} {e}")
                continue
            if not replies:
                errors.append(f"{media_id}/{comment_id}: no replies")
                continue

            reply = replies[0]
            self.assertIsInstance(reply, Comment)
            self.assertEqual(reply.replied_to_comment_id, comment_id)
            self.assertTrue(reply.pk)
            self.assertTrue(reply.text)
            return

        self.fail("Could not fetch live comment replies from known public fixtures: " + "; ".join(errors))


class ClientCommentExtendTestCase(_helpers.ClientPrivateTestCase):
    def cleanup_comment(self, media_id, comment_pk):
        try:
            self.cl.comment_bulk_delete(media_id, [comment_pk])
        except Exception as exc:
            print(f"Comment live cleanup comment_bulk_delete failed: {exc.__class__.__name__} {exc}")

    def cleanup_media(self, media_id):
        try:
            self.cl.media_delete(media_id)
        except Exception as exc:
            print(f"Comment live cleanup media_delete failed: {exc.__class__.__name__} {exc}")

    def assertCommentAccessible(self, media_id, comment_pk, text, attempts=5, delay=3):
        last_error = None
        for attempt in range(attempts):
            if attempt:
                time.sleep(delay)
            try:
                comments = self.cl.media_comments_v1(media_id, amount=20)
            except Exception as exc:
                last_error = exc
                continue
            for item in comments:
                if str(item.pk) == str(comment_pk) and item.text == text:
                    return item
        self.fail(f"Comment {comment_pk} was not readable after {attempts} attempts: {last_error}")

    def assertCommentPreflightAllows(self, media_id, text):
        result = self.cl.media_check_offensive_comment_v2(media_id, text)
        self.assertIsInstance(result, dict)
        self.assertIn("is_offensive", result)
        self.assertFalse(result["is_offensive"])
        if "status" in result:
            self.assertEqual(result["status"], "ok")
        return result

    def test_media_comment(self):
        text = "Test text [%s]" % datetime.now().strftime("%s")
        now = datetime.now(tz=UTC())
        caption_text = "Comment live fixture [%s]" % datetime.now().strftime("%s")
        path = self.copy_media_fixture("examples/kanada.jpg")
        media = self.cl.photo_upload(path, caption_text)
        self.addCleanup(self.cleanup_media, media.id)
        self.assertUploadedMediaAccessible(media, media_type=1, caption_text=caption_text)
        media_id = media.id
        self.assertCommentPreflightAllows(media_id, text)
        comment = self.cl.media_comment(media_id, text)
        self.addCleanup(self.cleanup_comment, media_id, comment.pk)
        self.assertIsInstance(comment, Comment)
        self.assertCommentAccessible(media_id, comment.pk, text)
        comment = comment.dict()
        for key, val in {
            "text": text,
            "content_type": "comment",
            "status": "Active",
        }.items():
            self.assertEqual(comment[key], val)
        self.assertIn("pk", comment)
        # The comment was written no more than 120 seconds ago
        self.assertTrue(abs((now - comment["created_at_utc"]).total_seconds()) <= 120)
        user_fields = comment["user"].keys()
        for field in ["pk", "username", "full_name", "profile_pic_url"]:
            self.assertIn(field, user_fields)

    def test_comment_pin_and_unpin(self):
        text = "Pin live fixture [%s]" % datetime.now().strftime("%s")
        caption_text = "Comment pin media fixture [%s]" % datetime.now().strftime("%s")
        path = self.copy_media_fixture("examples/kanada.jpg")
        media = self.cl.photo_upload(path, caption_text)
        self.addCleanup(self.cleanup_media, media.id)
        self.assertUploadedMediaAccessible(media, media_type=1, caption_text=caption_text)
        comment = self.cl.media_comment(media.id, text)
        self.addCleanup(self.cleanup_comment, media.id, comment.pk)
        self.assertCommentAccessible(media.id, comment.pk, text)

        self.assertTrue(self.cl.comment_pin(media.id, comment.pk))
        self.assertTrue(self.cl.comment_unpin(media.id, comment.pk))

    def test_comment_like_and_unlike(self):
        media_pk = self.cl.media_pk_from_url("https://www.instagram.com/p/B3mr1-OlWMG/")
        comment = self.cl.media_comments_v1(media_pk)[0]
        if comment.has_liked:
            self.assertTrue(self.cl.comment_unlike(comment.pk))
        like_count = int(comment.like_count)
        # like
        self.assertTrue(self.cl.comment_like(comment.pk))
        comment = self.cl.media_comments(media_pk)[0]
        new_like_count = int(comment.like_count)
        self.assertEqual(new_like_count, like_count + 1)
        # unlike
        self.assertTrue(self.cl.comment_unlike(comment.pk))
        comment = self.cl.media_comments(media_pk)[0]
        self.assertEqual(comment.like_count, like_count)
