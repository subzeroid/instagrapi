from tests.helpers import *


class FbSearchRegressionTestCase(unittest.TestCase):
    """Offline regression tests for FbSearchMixin v2 SERP endpoints
    and the typeahead-stream flattener."""

    def _build_client(self):
        client = Client()
        client.__dict__["timezone_offset"] = 10800
        return client

    def test_fbsearch_accounts_v2_omits_page_token_when_absent(self):
        client = self._build_client()
        with mock.patch.object(client, "private_request", return_value={"users": []}) as private_request:
            client.fbsearch_accounts_v2("alice")

        private_request.assert_called_once_with(
            "fbsearch/account_serp/",
            params={
                "search_surface": "account_serp",
                "timezone_offset": 10800,
                "query": "alice",
            },
        )

    def test_fbsearch_accounts_v2_forwards_page_token(self):
        client = self._build_client()
        with mock.patch.object(client, "private_request", return_value={"users": []}) as private_request:
            client.fbsearch_accounts_v2("alice", page_token="abc==")

        params = private_request.call_args.kwargs["params"]
        self.assertEqual(params["page_token"], "abc==")

    def test_fbsearch_reels_v2_forwards_optional_cursors(self):
        client = self._build_client()
        with mock.patch.object(client, "private_request", return_value={}) as private_request:
            client.fbsearch_reels_v2("dance", reels_max_id="next-page", rank_token="rt-x")

        private_request.assert_called_once_with(
            "fbsearch/reels_serp/",
            params={
                "search_surface": "clips_search_page",
                "timezone_offset": 10800,
                "query": "dance",
                "reels_max_id": "next-page",
                "rank_token": "rt-x",
            },
        )

    def test_fbsearch_topsearch_v2_uses_self_rank_token_by_default(self):
        client = self._build_client()
        with mock.patch.object(client, "private_request", return_value={}) as private_request:
            client.fbsearch_topsearch_v2("alice")

        params = private_request.call_args.kwargs["params"]
        # Default rank_token mirrors self.rank_token (computed from
        # user_id + uuid). Just assert the wiring, not a specific value.
        self.assertEqual(params["rank_token"], client.rank_token)
        self.assertEqual(params["search_surface"], "top_serp")
        self.assertNotIn("next_max_id", params)
        self.assertNotIn("reels_max_id", params)

    def test_fbsearch_topsearch_v2_explicit_rank_token_overrides_default(self):
        client = self._build_client()
        with mock.patch.object(client, "private_request", return_value={}) as private_request:
            client.fbsearch_topsearch_v2(
                "alice",
                next_max_id="cursor-1",
                reels_max_id="cursor-2",
                rank_token="custom-rt",
            )

        params = private_request.call_args.kwargs["params"]
        self.assertEqual(params["rank_token"], "custom-rt")
        self.assertEqual(params["next_max_id"], "cursor-1")
        self.assertEqual(params["reels_max_id"], "cursor-2")

    def test_fbsearch_typehead_flattens_stream_rows(self):
        client = self._build_client()
        with mock.patch.object(
            client,
            "private_request",
            return_value={
                "stream_rows": [
                    {"users": [{"pk": "1"}, {"pk": "2"}]},
                    {"users": [{"pk": "3"}]},
                    {"users": []},
                ]
            },
        ):
            users = client.fbsearch_typehead("ali")

        self.assertEqual([u["pk"] for u in users], ["1", "2", "3"])

    def test_fbsearch_typehead_handles_missing_stream_rows(self):
        client = self._build_client()
        with mock.patch.object(client, "private_request", return_value={}):
            users = client.fbsearch_typehead("ali")

        self.assertEqual(users, [])

    def test_web_search_topsearch_sends_expected_params(self):
        client = self._build_client()
        expected = {"hashtags": []}
        with mock.patch.object(client, "private_request", return_value=expected) as private_request:
            result = client.web_search_topsearch("alice")

        self.assertEqual(result, expected)
        private_request.assert_called_once_with(
            "web/search/topsearch/",
            params={
                "search_surface": "web_top_search",
                "context": "blended",
                "include_reel": "true",
                "query": "alice",
            },
        )

    def test_web_search_topsearch_hashtags_extracts_hashtags(self):
        client = self._build_client()
        with mock.patch.object(
            client,
            "web_search_topsearch",
            return_value={"hashtags": [{"hashtag": {"id": "1", "name": "python", "media_count": 10}}]},
        ):
            hashtags = client.web_search_topsearch_hashtags("python")

        self.assertEqual([hashtag.name for hashtag in hashtags], ["python"])

    def test_search_music_skips_non_track_items(self):
        client = self._build_client()
        with mock.patch.object(
            client,
            "private_request",
            return_value={
                "items": [
                    {"artist": {"pk": "123", "username": "hanszimmer"}, "track": None},
                    {"playlist": {"id": "456", "title": "Hans Zimmer Essentials"}},
                    {
                        "track": {
                            "id": "789",
                            "title": "Time",
                            "subtitle": "Hans Zimmer",
                            "display_artist": "Hans Zimmer",
                            "audio_cluster_id": 111,
                            "cover_artwork_uri": None,
                            "cover_artwork_thumbnail_uri": None,
                            "highlight_start_times_in_ms": [0],
                            "is_explicit": False,
                            "dash_manifest": "",
                            "has_lyrics": False,
                            "audio_asset_id": 222,
                            "duration_in_ms": 123000,
                            "allows_saving": True,
                        }
                    },
                ]
            },
        ) as private_request:
            tracks = client.search_music("Hans Zimmer")

        self.assertEqual([track.title for track in tracks], ["Time"])
        private_request.assert_called_once()
        self.assertEqual(private_request.call_args.args[0], "music/audio_global_search/")
        self.assertIn("params", private_request.call_args.kwargs)

    def test_fbsearch_item_forwards_optional_cursors(self):
        client = self._build_client()
        with mock.patch.object(client, "private_request", return_value={"items": []}) as private_request:
            result = client.fbsearch_item(
                "clips_serp_page",
                "clips_serp_page",
                "#dance",
                timezone_offset=10800,
                count=12,
                reels_page_index=2,
                has_more_reels="true",
                reels_max_id="reels-cursor",
                next_max_id="next-cursor",
                rank_token="rank-token",
                page_index=3,
                page_token="page-token",
                paging_token="paging-token",
            )

        self.assertEqual(result, {"items": []})
        private_request.assert_called_once_with(
            "fbsearch/clips_serp_page/",
            params={
                "search_surface": "clips_serp_page",
                "query": "#dance",
                "timezone_offset": 10800,
                "count": 12,
                "reels_page_index": 2,
                "has_more_reels": "true",
                "reels_max_id": "reels-cursor",
                "next_max_id": "next-cursor",
                "rank_token": "rank-token",
                "page_index": 3,
                "page_token": "page-token",
                "paging_token": "paging-token",
            },
        )

    def test_fbsearch_keyword_typeahead_sends_blended_context(self):
        client = self._build_client()
        with mock.patch.object(client, "private_request", return_value={"keywords": []}) as private_request:
            client.fbsearch_keyword_typeahead("ali", timezone_offset=10800, count=5)

        private_request.assert_called_once_with(
            "fbsearch/keyword_typeahead/",
            params={
                "search_surface": "typeahead_search_page",
                "query": "ali",
                "context": "blended",
                "timezone_offset": 10800,
                "count": 5,
            },
        )

    def test_fbsearch_typeahead_stream_sends_blended_context(self):
        client = self._build_client()
        with mock.patch.object(client, "private_request", return_value={"stream_rows": []}) as private_request:
            client.fbsearch_typeahead_stream("ali", timezone_offset=10800, count=5)

        private_request.assert_called_once_with(
            "fbsearch/typeahead_stream/",
            params={
                "search_surface": "typeahead_search_page",
                "query": "ali",
                "context": "blended",
                "timezone_offset": 10800,
                "count": 5,
            },
        )
