from tests.helpers import *


class TrackMixinRegressionTestCase(unittest.TestCase):
    def test_music_trending_posts_product_payload(self):
        client = Client()
        client.uuid = "uuid-1"

        with mock.patch.object(client, "private_request", return_value={"items": [], "status": "ok"}) as private:
            result = client.music_trending(product="feed_post")

        self.assertEqual(result, {"items": [], "status": "ok"})
        private.assert_called_once_with(
            "music/trending/",
            data={"product": "feed_post", "_uuid": "uuid-1"},
            with_signature=False,
        )

    def test_music_top_trends_posts_page_size(self):
        client = Client()
        client.uuid = "uuid-1"

        with mock.patch.object(client, "private_request", return_value={"items": [], "status": "ok"}) as private:
            result = client.music_top_trends(page_size=15)

        self.assertEqual(result, {"items": [], "status": "ok"})
        private.assert_called_once_with(
            "music/top_trends/",
            data={"product": "music_in_feed", "_uuid": "uuid-1", "page_size": "15"},
            with_signature=False,
        )

    def test_music_search_v2_posts_current_search_payload(self):
        client = Client()
        client.uuid = "uuid-1"

        with (
            mock.patch.object(client, "generate_uuid", side_effect=["search-session", "browse-session"]),
            mock.patch.object(client, "private_request", return_value={"items": [], "status": "ok"}) as private,
        ):
            result = client.music_search_v2("drake")

        self.assertEqual(result, {"items": [], "status": "ok"})
        private.assert_called_once_with(
            "music/search_v2/",
            data={
                "from_typeahead": "false",
                "search_session_id": "search-session",
                "product": "music_in_feed",
                "q": "drake",
                "_uuid": "uuid-1",
                "browse_session_id": "browse-session",
            },
            with_signature=False,
        )

    def test_music_keyword_search_uses_query_params(self):
        client = Client()

        with (
            mock.patch.object(client, "generate_uuid", return_value="browse-session"),
            mock.patch.object(client, "private_request", return_value={"keywords": [], "status": "ok"}) as private,
        ):
            result = client.music_keyword_search("drake")

        self.assertEqual(result, {"keywords": [], "status": "ok"})
        private.assert_called_once_with(
            "music/keyword_search/",
            params={
                "num_keywords": "3",
                "search_session_id": "",
                "product": "music_in_feed",
                "q": "drake",
                "browse_session_id": "browse-session",
            },
        )

    def test_music_bookmark_posts_original_audio_id(self):
        client = Client()
        client.uuid = "uuid-1"

        with mock.patch.object(client, "private_request", return_value={"success": True, "status": "ok"}) as private:
            result = client.music_bookmark("1171063161088391")

        self.assertTrue(result)
        private.assert_called_once_with(
            "music/bookmark_music/",
            data={
                "original_audio_id": "1171063161088391",
                "_uuid": "uuid-1",
                "surface_requested_from": "audio_aggregation_page",
            },
            with_signature=False,
        )

    def test_music_clips_audio_browser_posts_browse_session(self):
        client = Client()
        client.uuid = "uuid-1"

        with (
            mock.patch.object(client, "generate_uuid", return_value="browse-session"),
            mock.patch.object(client, "private_request", return_value={"items": [], "status": "ok"}) as private,
        ):
            result = client.music_clips_audio_browser()

        self.assertEqual(result, {"items": [], "status": "ok"})
        private.assert_called_once_with(
            "music/clips_audio_browser/",
            data={
                "product": "story_camera_clips_v2",
                "_uuid": "uuid-1",
                "browse_session_id": "browse-session",
            },
            with_signature=False,
        )

    def test_music_verify_original_audio_title_returns_valid_flag(self):
        client = Client()
        client.uuid = "uuid-1"

        with mock.patch.object(client, "private_request", return_value={"is_valid": True, "status": "ok"}) as private:
            result = client.music_verify_original_audio_title("Original Audio")

        self.assertTrue(result)
        private.assert_called_once_with(
            "music/verify_original_audio_title/",
            data={"original_audio_name": "Original Audio", "_uuid": "uuid-1"},
            with_signature=False,
        )

    def test_track_stream_info_by_id_sends_expected_endpoint_and_payload(self):
        client = Client()
        with mock.patch.object(client, "private_request", return_value={}) as private_request:
            client.track_stream_info_by_id("18000000000000000")

        private_request.assert_called_once()
        path, data = private_request.call_args.args
        self.assertEqual(path, "clips/stream_clips_pivot_page/")
        self.assertEqual(data["pivot_page_type"], "audio")
        self.assertEqual(data["music_page"]["tab_type"], "clips")
        self.assertEqual(data["music_page"]["audio_asset_id"], "18000000000000000")
        self.assertEqual(data["music_page"]["audio_cluster_id"], "18000000000000000")
        self.assertNotIn("max_id", data["music_page"])

    def test_track_stream_info_by_id_forwards_max_id(self):
        client = Client()
        with mock.patch.object(client, "private_request", return_value={}) as private_request:
            client.track_stream_info_by_id("18000000000000000", max_id="next-page")

        _, data = private_request.call_args.args
        self.assertEqual(data["music_page"]["max_id"], "next-page")
