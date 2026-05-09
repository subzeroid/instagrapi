from tests.helpers import *


class MediaInfoV2RegressionTestCase(unittest.TestCase):
    def _media_or_ad_payload(self):
        return {
            "pk": "1",
            "id": "1_2",
            "code": "abc",
            "taken_at": 1710000000,
            "media_type": 1,
            "user": {
                "pk": "2",
                "username": "example",
                "profile_pic_url": "https://example.com/profile.jpg",
            },
            "image_versions2": {
                "candidates": [
                    {"url": "https://example.com/x.jpg", "width": 100, "height": 100}
                ]
            },
        }

    def test_media_info_v2_strips_userid_suffix(self):
        client = Client()
        with mock.patch.object(
            client,
            "private_request",
            return_value={"media_or_ad": self._media_or_ad_payload()},
        ) as private_request:
            media = client.media_info_v2("3613500067578544892_25025320")

        private_request.assert_called_once_with(
            "discover/media_metadata/",
            params={"media_id": "3613500067578544892"},
        )
        self.assertEqual(media.pk, "1")

    def test_media_info_v2_passes_pk_only_unchanged(self):
        client = Client()
        with mock.patch.object(
            client,
            "private_request",
            return_value={"media_or_ad": self._media_or_ad_payload()},
        ) as private_request:
            client.media_info_v2("3613500067578544892")

        params = private_request.call_args.kwargs["params"]
        self.assertEqual(params["media_id"], "3613500067578544892")

    def test_media_info_v2_raises_media_not_found_when_payload_empty(self):
        from instagrapi.exceptions import MediaNotFound

        client = Client()
        client.last_json = {}
        with mock.patch.object(client, "private_request", return_value={}):
            with self.assertRaises(MediaNotFound):
                client.media_info_v2("9_8")


class CheckOffensiveCommentV2RegressionTestCase(unittest.TestCase):
    def _build_logged_in_client(self):
        client = Client()
        client.authorization_data = {"ds_user_id": "1"}
        return client

    def test_v2_payload_is_lighter_than_v1(self):
        client = self._build_logged_in_client()
        with mock.patch.object(
            client,
            "private_request",
            return_value={"is_offensive": True, "category": "harassment"},
        ) as private_request:
            result = client.media_check_offensive_comment_v2("9_8", "rude")

        private_request.assert_called_once()
        path, kwargs = (
            private_request.call_args.args[0],
            private_request.call_args.kwargs,
        )
        self.assertEqual(path, "media/comment/check_offensive_comment/")
        # data passed as keyword to mirror aiograpi shape
        self.assertEqual(kwargs["data"]["comment_text"], "rude")
        self.assertEqual(kwargs["data"]["media_id"], "9_8")
        self.assertIn("_uuid", kwargs["data"])
        # No with_action_data wrapping → no _csrftoken / _uid /
        # user_breadcrumb in the payload.
        self.assertNotIn("_csrftoken", kwargs["data"])
        self.assertNotIn("_uid", kwargs["data"])
        self.assertNotIn("user_breadcrumb", kwargs["data"])
        # Raw response is returned, not just bool.
        self.assertEqual(result, {"is_offensive": True, "category": "harassment"})

    def test_v2_requires_login(self):
        client = Client()
        # No authorization_data → user_id property returns None.
        with self.assertRaises(AssertionError):
            client.media_check_offensive_comment_v2("9_8", "rude")
