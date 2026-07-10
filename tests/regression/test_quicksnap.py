from tests.helpers import *


class QuickSnapRegressionTestCase(unittest.TestCase):
    def build_client(self):
        client = Client()
        client.private.cookies.set("ds_user_id", "123")
        client.uuid = "uuid-1"
        client.android_device_id = "android-device"
        client.timezone_offset = 19800
        client.set_device(
            {
                "manufacturer": "vivo",
                "model": "vivo 1819",
                "android_version": 30,
                "android_release": "11",
            }
        )
        client.with_default_data = lambda data: data
        return client

    def test_quicksnap_history_returns_paginated_history_payload(self):
        client = self.build_client()
        history = {"edges": [{"node": {"id": "media-1"}}], "page_info": {"has_next_page": False}}
        graphql_response = {
            "data": {
                "viewer": {
                    "__typename": "XDTUser",
                    "1$quick_snap_paginated_history(after:$after,first:$first)": history,
                }
            }
        }

        with mock.patch.object(client, "private_graphql_www_request", return_value=graphql_response) as graphql:
            result = client.quicksnap_history(amount=20, end_cursor="cursor-1")

        graphql.assert_called_once_with(
            friendly_name="IGQuickSnapGetHistoryPaginatedQuery",
            variables={"first": 20, "after": "cursor-1"},
            client_doc_id="202528380816979569862257718136",
        )
        self.assertEqual(result, history)

    def test_quicksnap_send_uploads_photo_and_configures_quick_snap(self):
        client = self.build_client()
        configure_response = {
            "status": "ok",
            "posts": [{"media_ids": ["3931708346854699261"]}],
            "medias": [
                {
                    "media_dict": {
                        "product_type": "quick_snap",
                        "audience": "mutual_followers",
                    }
                }
            ],
        }

        with (
            mock.patch.object(client, "photo_rupload", return_value=("upload-1", 984, 984)) as rupload,
            mock.patch.object(client, "private_request", return_value=configure_response) as private_request,
        ):
            result = client.quicksnap_send(Path("snap.jpg"))

        rupload.assert_called_once_with(Path("snap.jpg"))
        private_request.assert_called_once()
        self.assertEqual(private_request.call_args.args[0], "media/configure_to_quick_snap/")
        data = private_request.call_args.args[1]
        self.assertEqual(data["upload_id"], "upload-1")
        self.assertEqual(data["audience"], "mutual_followers")
        self.assertEqual(data["source_type"], "3")
        self.assertEqual(data["bottom_camera_dial_selected"], "11")
        self.assertEqual(data["publish_id"], "1")
        self.assertEqual(data["product_type"], "quick_snap")
        self.assertEqual(data["_uid"], "123")
        self.assertEqual(data["_uuid"], "uuid-1")
        self.assertEqual(data["device_id"], "android-device")
        self.assertEqual(data["timezone_offset"], "19800")
        self.assertEqual(data["device"]["manufacturer"], "vivo")
        self.assertEqual(data["device"]["model"], "vivo 1819")
        self.assertEqual(data["quick_snap_data"], {})
        self.assertIn("QuickSnapUnifiedFragment:quicksnap_unified_fragment", data["nav_chain"])
        self.assertIn("InsightsHostImpl:quick_snap_audience_picker", data["nav_chain"])
        self.assertEqual(result, configure_response)

    def test_quicksnap_delete_soft_deletes_media(self):
        client = self.build_client()

        with mock.patch.object(client, "private_request", return_value={"did_delete": True, "status": "ok"}) as request:
            result = client.quicksnap_delete("3931708346854699261_123")

        request.assert_called_once_with(
            "media/3931708346854699261_123/soft_delete/",
            {"media_id": "3931708346854699261_123", "_uuid": "uuid-1"},
        )
        self.assertTrue(result)
