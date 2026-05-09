from tests.helpers import *


class TrackMixinRegressionTestCase(unittest.TestCase):
    def test_track_stream_info_by_id_sends_expected_endpoint_and_payload(self):
        client = Client()
        with mock.patch.object(
            client, "private_request", return_value={}
        ) as private_request:
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
        with mock.patch.object(
            client, "private_request", return_value={}
        ) as private_request:
            client.track_stream_info_by_id("18000000000000000", max_id="next-page")

        _, data = private_request.call_args.args
        self.assertEqual(data["music_page"]["max_id"], "next-page")
