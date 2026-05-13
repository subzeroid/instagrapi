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

        private_request.assert_called_once_with("media/123_456/comments/100/inline_child_comments/", None)
        self.assertEqual([reply.pk for reply in replies], ["101", "102"])
        self.assertTrue(all(isinstance(reply, Comment) for reply in replies))
        self.assertEqual(replies[0].replied_to_comment_id, "100")

    def test_media_comments_gql_chunk_posts_doc_id_query(self):
        client = Client()
        client._fb_dtsg = "token"
        with mock.patch.object(
            client,
            "graphql_request",
            return_value={
                "data": {
                    "xdt_media_comments": {
                        "edges": [{"node": {"pk": "101", "text": "hello"}}],
                        "page_info": {"has_next_page": True, "end_cursor": "cursor-2"},
                    }
                }
            },
        ) as graphql_request:
            comments, cursor = client.media_comments_gql_chunk("123", end_cursor="cursor-1")

        self.assertEqual(comments, [{"pk": "101", "text": "hello"}])
        self.assertEqual(cursor, "cursor-2")
        data = graphql_request.call_args.kwargs["data"]
        self.assertEqual(data["doc_id"], "6974885689225067")
        self.assertIn('"media_id":"123"', data["variables"])
        self.assertIn('"after":"cursor-1"', data["variables"])

    def test_media_comments_threaded_gql_chunk_posts_parent_comment_id(self):
        client = Client()
        client._fb_dtsg = "token"
        with mock.patch.object(
            client,
            "graphql_request",
            return_value={
                "data": {
                    "xdt_threaded_comments": {
                        "edges": [{"node": {"pk": "201", "text": "reply"}}],
                        "page_info": {"has_next_page": False, "end_cursor": None},
                    }
                }
            },
        ) as graphql_request:
            comments, cursor = client.media_comments_threaded_gql_chunk("123", "100")

        self.assertEqual(comments, [{"pk": "201", "text": "reply"}])
        self.assertIsNone(cursor)
        data = graphql_request.call_args.kwargs["data"]
        self.assertEqual(data["doc_id"], "7171917939589632")
        self.assertIn('"parent_comment_id":"100"', data["variables"])

    def test_media_comments_v1_chunk_fetches_private_comments_page(self):
        client = Client()
        with mock.patch.object(
            client,
            "private_request",
            return_value={
                "comments": [self._reply_payload("101")],
                "next_min_id": "min-cursor",
                "next_max_id": "max-cursor",
            },
        ) as private_request:
            comments, min_id, max_id = client.media_comments_v1_chunk("123_456", min_id="prev-min", max_id="prev-max")

        private_request.assert_called_once_with(
            "media/123_456/comments/",
            params={
                "can_support_threading": "true",
                "permalink_enabled": "false",
                "min_id": "prev-min",
                "max_id": "prev-max",
            },
        )
        self.assertEqual([comment.pk for comment in comments], ["101"])
        self.assertEqual(min_id, "min-cursor")
        self.assertEqual(max_id, "max-cursor")

    def test_media_stream_comments_v1_chunk_reads_stream_rows(self):
        client = Client()
        with mock.patch.object(
            client,
            "private_request",
            return_value={
                "stream_rows": [{"comments": [self._reply_payload("101")]}],
                "next_min_id": "min-cursor",
                "next_max_id": "max-cursor",
            },
        ) as private_request:
            comments, min_id, max_id = client.media_stream_comments_v1_chunk("123_456")

        private_request.assert_called_once()
        self.assertEqual(private_request.call_args.args[0], "media/123_456/stream_comments/")
        self.assertEqual([comment.pk for comment in comments], ["101"])
        self.assertEqual(min_id, "min-cursor")
        self.assertEqual(max_id, "max-cursor")

    def test_media_comment_infos_joins_media_ids(self):
        client = Client()
        expected = {"comment_infos": []}
        with mock.patch.object(client, "private_request", return_value=expected) as private_request:
            result = client.media_comment_infos(["1_2", "3_4"])

        self.assertEqual(result, expected)
        private_request.assert_called_once_with(
            "media/comment_infos/",
            params={"can_support_carousel_mentions": "false", "media_ids": "1_2,3_4"},
        )

    def test_comment_likers_gql_chunk_uses_comment_likers_query_hash(self):
        client = Client()
        with mock.patch.object(client, "inject_sessionid_to_public", return_value=True):
            with mock.patch.object(
                client,
                "public_graphql_request",
                return_value={
                    "comment": {
                        "edge_liked_by": {
                            "edges": [{"node": {"id": "1", "username": "alice"}}],
                            "page_info": {"has_next_page": True, "end_cursor": "cursor-2"},
                        }
                    }
                },
            ) as public_graphql_request:
                likers, cursor = client.comment_likers_gql_chunk("100", end_cursor="cursor-1")

        self.assertEqual(likers, [{"id": "1", "username": "alice"}])
        self.assertEqual(cursor, "cursor-2")
        public_graphql_request.assert_called_once_with(
            {"comment_id": "100", "first": 50, "after": "cursor-1"},
            query_hash="5f0b1f6281e72053cbc07909c8d154ae",
        )

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
            replies, cursor = client.media_comment_replies_chunk("123_456", "100", max_amount=10, min_id="cursor-1")

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
        with mock.patch.object(client, "private_request", side_effect=responses) as private_request:
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
