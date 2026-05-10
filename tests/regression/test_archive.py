from instagrapi.types import StoryArchiveDay
from tests.helpers import *


class ArchiveRegressionTestCase(unittest.TestCase):
    @staticmethod
    def media_payload(pk="1", code="abc"):
        return {
            "pk": pk,
            "id": f"{pk}_1",
            "code": code,
            "taken_at": 1710000000,
            "media_type": 1,
            "caption": None,
            "user": {
                "pk": "1",
                "username": "example",
                "profile_pic_url": "https://example.com/profile.jpg",
            },
            "like_count": 0,
            "image_versions2": {
                "candidates": [
                    {
                        "url": "https://example.com/photo.jpg",
                        "width": 720,
                        "height": 720,
                    }
                ]
            },
        }

    @staticmethod
    def story_payload(pk="10"):
        return {
            "pk": pk,
            "id": f"{pk}_1",
            "taken_at": 1710000000,
            "media_type": 1,
            "user": {
                "pk": "1",
                "username": "example",
                "profile_pic_url": "https://example.com/profile.jpg",
            },
            "image_versions2": {
                "candidates": [
                    {
                        "url": "https://example.com/story.jpg",
                        "width": 720,
                        "height": 1280,
                    }
                ]
            },
        }

    def test_archive_medias_fetches_only_me_feed_and_paginates(self):
        client = Client()
        first_media = self.media_payload(pk="1", code="abc")
        second_media = self.media_payload(pk="2", code="def")
        client.private_request = Mock(
            side_effect=[
                {
                    "items": [first_media],
                    "num_results": 1,
                    "more_available": True,
                    "max_id": "next-page",
                    "status": "ok",
                },
                {
                    "items": [second_media],
                    "num_results": 1,
                    "more_available": False,
                    "max_id": None,
                    "status": "ok",
                },
            ]
        )

        medias = client.archive_medias(amount=2)

        self.assertEqual([media.pk for media in medias], ["1", "2"])
        self.assertEqual(client.private_request.call_count, 2)
        first_call = client.private_request.call_args_list[0]
        second_call = client.private_request.call_args_list[1]
        self.assertEqual(first_call.args[0], "feed/only_me_feed/")
        self.assertEqual(first_call.kwargs["params"], {})
        self.assertEqual(second_call.kwargs["params"], {"max_id": "next-page"})

    def test_archive_story_days_fetches_day_shells(self):
        client = Client()
        client.timezone_offset = 10800
        client.private_request = Mock(
            return_value={
                "items": [
                    {
                        "timestamp": 1710000000,
                        "media_count": 1,
                        "id": "archiveDay:123",
                        "reel_type": "archive_day_reel",
                        "latest_reel_media": 1710000123,
                    }
                ],
                "num_results": 1,
                "more_available": False,
                "max_id": None,
                "status": "ok",
            }
        )

        days = client.archive_story_days(amount=1)

        self.assertEqual(len(days), 1)
        self.assertIsInstance(days[0], StoryArchiveDay)
        self.assertEqual(days[0].id, "archiveDay:123")
        request = client.private_request.call_args
        self.assertEqual(request.args[0], "archive/reel/day_shells_paginated/")
        self.assertEqual(
            request.kwargs["params"],
            {"timezone_offset": 10800, "include_memories": "1"},
        )

    def test_archive_stories_fetches_reels_media_stream_for_archive_days(self):
        client = Client()
        client.__dict__["user_id"] = "1"
        client.uuid = "uuid"
        client.timezone_offset = 0
        client.private_request = Mock(
            side_effect=[
                {
                    "items": [
                        {
                            "timestamp": 1710000000,
                            "media_count": 1,
                            "id": "archiveDay:123",
                            "reel_type": "archive_day_reel",
                            "latest_reel_media": 1710000123,
                        }
                    ],
                    "num_results": 1,
                    "more_available": False,
                    "status": "ok",
                },
                {
                    "reels": {
                        "archiveDay:123": {
                            "id": "archiveDay:123",
                            "items": [self.story_payload()],
                        }
                    },
                    "status": "ok",
                },
            ]
        )

        stories = client.archive_stories(amount=1)

        self.assertEqual(len(stories), 1)
        self.assertEqual(stories[0].pk, "10")
        stream_request = client.private_request.call_args_list[1]
        self.assertEqual(stream_request.args[0], "feed/reels_media_stream/")
        self.assertEqual(
            stream_request.kwargs["data"]["reel_ids"],
            ["archiveDay:123"],
        )
        self.assertEqual(stream_request.kwargs["data"]["reason"], "on_tap")
