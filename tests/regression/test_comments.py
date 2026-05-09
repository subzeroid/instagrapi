from tests.helpers import *


class CommentRepliesRegressionTestCase(unittest.TestCase):
    def _reply_payload(self, pk, text="reply", replied_to_comment_id="100"):
        return {
            "pk": str(pk),
            "text": text,
            "user": {"pk": "1", "username": "example", "full_name": "Example"},
            "created_at_utc": 1_700_000_000,
            "content_type": "comment",
            "status": "Active",
            "replied_to_comment_id": str(replied_to_comment_id),
            "has_liked_comment": False,
            "comment_like_count": 0,
        }

    def test_media_comment_replies_fetches_inline_child_comments(self):
        client = Client()
        with mock.patch.object(
            client,
            "private_request",
            return_value={
                "child_comments": [
                    self._reply_payload("101", "first"),
                    self._reply_payload("102", "second"),
                ],
                "has_more_head_child_comments": False,
                "status": "ok",
            },
        ) as private_request:
            replies = client.media_comment_replies("123_456", "100")

        private_request.assert_called_once_with(
            "media/123_456/comments/100/inline_child_comments/", None
        )
        self.assertEqual([reply.pk for reply in replies], ["101", "102"])
        self.assertTrue(all(isinstance(reply, Comment) for reply in replies))
        self.assertEqual(replies[0].replied_to_comment_id, "100")

    def test_media_comment_replies_chunk_returns_child_cursor(self):
        client = Client()
        with mock.patch.object(
            client,
            "private_request",
            return_value={
                "child_comments": [self._reply_payload("101")],
                "next_min_child_cursor": "cursor-2",
                "has_more_head_child_comments": True,
                "status": "ok",
            },
        ) as private_request:
            replies, cursor = client.media_comment_replies_chunk(
                "123_456", "100", max_amount=10, min_id="cursor-1"
            )

        private_request.assert_called_once_with(
            "media/123_456/comments/100/inline_child_comments/",
            {"min_id": "cursor-1"},
        )
        self.assertEqual([reply.pk for reply in replies], ["101"])
        self.assertEqual(cursor, "cursor-2")

    def test_media_comment_replies_paginates_until_amount(self):
        client = Client()
        responses = [
            {
                "child_comments": [self._reply_payload("101")],
                "next_min_child_cursor": "cursor-2",
                "has_more_head_child_comments": True,
                "status": "ok",
            },
            {
                "child_comments": [self._reply_payload("102")],
                "has_more_head_child_comments": False,
                "status": "ok",
            },
        ]
        with mock.patch.object(
            client, "private_request", side_effect=responses
        ) as private_request:
            replies = client.media_comment_replies("123_456", "100", amount=2)

        self.assertEqual(
            private_request.call_args_list,
            [
                mock.call("media/123_456/comments/100/inline_child_comments/", None),
                mock.call(
                    "media/123_456/comments/100/inline_child_comments/",
                    {"min_id": "cursor-2"},
                ),
            ],
        )
        self.assertEqual([reply.pk for reply in replies], ["101", "102"])
