from tests import helpers as _helpers
from tests.helpers import *


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

        self.fail(
            "Could not fetch live comment replies from known public fixtures: "
            + "; ".join(errors)
        )


class ClientCommentExtendTestCase(_helpers.ClientPrivateTestCase):
    def test_media_comment(self):
        text = "Test text [%s]" % datetime.now().strftime("%s")
        now = datetime.now(tz=UTC())
        comment = self.cl.media_comment_v1(2276404890775267248, text)
        self.assertIsInstance(comment, Comment)
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
