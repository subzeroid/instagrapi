from tests.helpers import *


class BloksRegressionTestCase(unittest.TestCase):
    def build_client(self):
        client = Client()
        client.uuid = "uuid-1"
        client.bloks_versioning_id = "bloks-version"
        return client

    def test_bloks_async_action_posts_unsigned_bloks_payload(self):
        client = self.build_client()
        params = {"server_params": {"flow": "example_flow"}}
        expected = {"status": "ok"}

        with mock.patch.object(client, "private_request", return_value=expected) as private_request:
            result = client.bloks_async_action("com.example.action", params)

        self.assertEqual(result, expected)
        private_request.assert_called_once_with(
            "bloks/async_action/com.example.action/",
            data={
                "params": dumps(params),
                "_uuid": "uuid-1",
                "bk_client_context": dumps({"bloks_version": "bloks-version", "styles_id": "instagram"}),
                "bloks_versioning_id": "bloks-version",
            },
            with_signature=False,
        )

    def test_bloks_fxcal_link_reels_share_uses_current_flow_payload(self):
        client = self.build_client()
        expected = {"status": "ok"}

        with mock.patch.object(client, "bloks_async_action", return_value=expected) as bloks_async_action:
            result = client.bloks_fxcal_link_reels_share(cds_client_value=2)

        self.assertEqual(result, expected)
        bloks_async_action.assert_called_once_with(
            "com.bloks.www.fxcal.link.async",
            {
                "server_params": {
                    "flow": "ig_fb_reels_composer_rowshare",
                    "logging_event": "linking_flow_initiated",
                    "cds_client_value": 2,
                    "opaque_verified_native_auth_data": None,
                    "native_auth_data": [],
                    "account_type": 0,
                }
            },
            bloks_versioning_id="",
        )
