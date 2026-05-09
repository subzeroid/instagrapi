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
