from tests.helpers import *


class TimelineRegressionTestCase(unittest.TestCase):
    @staticmethod
    def build_media_payload(pk="1", code="abc"):
        return {
            "pk": pk,
            "id": f"{pk}_1",
            "code": code,
            "taken_at": 1710000000,
            "media_type": 2,
            "caption": {"text": "caption"},
            "user": {
                "pk": "1",
                "username": "example",
                "profile_pic_url": "https://example.com/profile.jpg",
            },
            "like_count": 0,
            "video_versions": [
                {
                    "url": "https://example.com/video.mp4",
                    "width": 720,
                    "height": 1280,
                }
            ],
            "image_versions2": {
                "candidates": [
                    {
                        "url": "https://example.com/thumbnail.jpg",
                        "width": 720,
                        "height": 1280,
                    }
                ]
            },
        }

    def test_reels_timeline_media_returns_empty_for_unsupported_collection(self):
        client = Client()
        client.logger = Mock()
        client.private_request = Mock()

        result = client.reels_timeline_media(123456789)

        self.assertEqual(result, [])
        client.private_request.assert_not_called()
        client.logger.warning.assert_called_once()

    def test_reels_timeline_media_uses_paging_info_max_id_for_pagination(self):
        client = Client()
        client.logger = Mock()
        first_media = self.build_media_payload(pk="1", code="abc")
        second_media = self.build_media_payload(pk="2", code="def")
        client.private_request = Mock(
            side_effect=[
                {
                    "items": [{"media": first_media}],
                    "paging_info": {"more_available": True, "max_id": "next-page"},
                },
                {
                    "items": [{"media": second_media}],
                    "paging_info": {"more_available": False},
                },
            ]
        )

        result = client.reels_timeline_media("reels", amount=2)

        self.assertEqual(len(result), 2)
        self.assertEqual(client.private_request.call_count, 2)
        first_call = client.private_request.call_args_list[0]
        second_call = client.private_request.call_args_list[1]
        self.assertEqual(first_call.args[0], "clips/connected/")
        self.assertEqual(first_call.kwargs["params"]["max_id"], "")
        self.assertEqual(second_call.kwargs["params"]["max_id"], "next-page")

    def test_friends_reels_uses_social_discover_endpoint(self):
        client = Client()
        client.logger = Mock()
        media = self.build_media_payload(pk="3", code="ghi")
        client.private_request = Mock(
            return_value={
                "items": [{"media": media}],
                "paging_info": {"more_available": False},
            }
        )

        result = client.friends_reels(amount=1)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].pk, "3")
        private_request = client.private_request.call_args
        self.assertEqual(private_request.args[0], "clips/discover/social/")
        self.assertEqual(private_request.kwargs["data"], " ")
        self.assertEqual(private_request.kwargs["params"]["max_id"], "")

    def test_get_timeline_feed_sends_seen_posts_when_paginating(self):
        client = Client()
        client.private_request = Mock(
            side_effect=[
                {
                    "feed_items": [
                        {"media_or_ad": {"id": "111_1"}},
                        {"media_or_ad": {"pk": "222", "user": {"pk": "1"}}},
                    ],
                    "next_max_id": "next-page",
                },
                {"feed_items": []},
            ]
        )

        client.get_timeline_feed("cold_start_fetch")
        client.get_timeline_feed("pull_to_refresh", max_id="next-page")

        first_data = json.loads(client.private_request.call_args_list[0].args[1])
        second_data = json.loads(client.private_request.call_args_list[1].args[1])
        self.assertEqual(first_data["feed_view_info"], "[]")
        self.assertNotIn("seen_posts", first_data)
        self.assertEqual(second_data["reason"], "pagination")
        self.assertEqual(second_data["max_id"], "next-page")
        self.assertEqual(second_data["seen_posts"], "111_1,222_1")
        feed_view_info = json.loads(second_data["feed_view_info"])
        self.assertEqual([item["media_id"] for item in feed_view_info], ["111_1", "222_1"])

    def test_get_timeline_feed_sends_current_app_request_metadata(self):
        client = Client()
        client.private_request = Mock(return_value={"feed_items": []})

        with mock.patch("instagrapi.mixins.auth.time.time", return_value=1778379170.083):
            client.get_timeline_feed("cold_start_fetch")

        data = json.loads(client.private_request.call_args.args[1])
        self.assertEqual(data["app_start_time"], "1778379170083")
        self.assertEqual(data["client_recorded_request_time_ms"], "1778379170083")
        self.assertEqual(data["client_seen_store_media_list"], "")
        self.assertEqual(data["client_view_state_media_list"], "[]")
        self.assertEqual(data["device_timezone_name"], "GMT")
        self.assertEqual(data["feed_reshare_info"], "")
        self.assertEqual(data["include_attribution_ui_data"], "true")
        self.assertEqual(data["push_disabled"], "true")
        self.assertEqual(data["request_build_time"], "1778379170083")
        session_level_signals = json.loads(data["session_level_signals"])
        self.assertEqual(session_level_signals["app_entry"], "normal")
        self.assertEqual(session_level_signals["video_play_count"], 0)

    def test_get_timeline_feed_sends_current_app_pagination_metadata(self):
        client = Client()
        client.private_request = Mock(
            side_effect=[
                {"feed_items": [{"media_or_ad": {"id": "111_1"}}], "next_max_id": "next-page"},
                {"feed_items": []},
            ]
        )

        client.get_timeline_feed("cold_start_fetch")
        client.get_timeline_feed(max_id="next-page")

        data = json.loads(client.private_request.call_args_list[1].args[1])
        self.assertEqual(data["organic_realtime_information"], "[]")
        self.assertEqual(data["pagination_source"], "feed_recs")
        self.assertEqual(data["triggered_by_visible_spinner"], "false")
