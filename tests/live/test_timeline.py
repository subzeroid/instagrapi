from tests import helpers as _helpers
from tests.helpers import *


class ClientTimelineLiveTestCase(_helpers.ClientPrivateTestCase):
    @staticmethod
    def _feed_media_ids(result):
        media_ids = []
        for item in result.get("feed_items") or []:
            media = item.get("media_or_ad") or item.get("media") or {}
            media_id = media.get("id")
            if media_id:
                media_ids.append(str(media_id))
        return media_ids

    def test_friends_reels_live_endpoint(self):
        result = self.cl.private_request(
            "clips/discover/social/",
            data=" ",
            params={"max_id": ""},
        )

        self.assertEqual(result.get("status"), "ok")
        self.assertIn("items", result)
        self.assertIn("paging_info", result)
        self.assertIsInstance(result["items"], list)

        medias = self.cl.friends_reels(amount=3)

        self.assertIsInstance(medias, list)
        for media in medias:
            self.assertIsInstance(media, Media)

    def test_get_timeline_feed_live_paginates_with_seen_posts(self):
        calls = []
        private_request = self.cl.private_request

        def recording_private_request(endpoint, data=None, *args, **kwargs):
            if endpoint == "feed/timeline/":
                calls.append(data)
            return private_request(endpoint, data, *args, **kwargs)

        self.cl.private_request = recording_private_request
        try:
            first_page = self.cl.get_timeline_feed("cold_start_fetch")
            next_max_id = first_page.get("next_max_id")
            if not next_max_id:
                self.skipTest("Timeline feed did not return next_max_id")
            seen_posts = self._feed_media_ids(first_page) or ["0_0"]
            second_page = self.cl.get_timeline_feed(max_id=next_max_id, seen_posts=seen_posts)
        finally:
            self.cl.private_request = private_request

        self.assertEqual(second_page.get("status"), "ok")
        self.assertGreaterEqual(len(calls), 2)
        second_payload = json.loads(calls[1])
        self.assertEqual(second_payload["reason"], "pagination")
        self.assertEqual(second_payload["max_id"], next_max_id)
        self.assertEqual(second_payload["seen_posts"], ",".join(seen_posts))
        self.assertNotEqual(second_payload["feed_view_info"], "[]")
