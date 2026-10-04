import json
import unittest
from unittest.mock import patch

from instagrapi import Client, config


class CaaLoginPayloadContractTestCase(unittest.TestCase):
    def serialized_params(self, app_version=None):
        settings = {"device_settings": dict(config.APP_SETTINGS[app_version])} if app_version else {}
        client = Client(settings)
        self.assertEqual(client.device_settings["app_version"], app_version or "449.0.0.52.84")
        client.uuid = "synthetic-client-uuid"
        client.android_device_id = "android-synthetic-device"
        client.phone_id = "synthetic-family-device"
        client.mid = "synthetic-machine"
        client.caa_aac = '{"aaccs":"synthetic-context"}'
        password = "#PWD_INSTAGRAM:4:1:synthetic-encrypted-password"

        with patch.object(client, "private_request", return_value={"status": "ok"}) as private_request:
            client.bloks_caa_login_send_request(
                password,
                username="synthetic-user",
                waterfall_id="synthetic-flow",
                auto_prepare=False,
            )

        private_request.assert_called_once()
        self.assertEqual(
            private_request.call_args.args,
            ("bloks/async_action/com.bloks.www.bloks.caa.login.async.send_login_request/",),
        )
        data = private_request.call_args.kwargs["data"]
        self.assertIsInstance(data["params"], str)
        self.assertEqual(data["_uuid"], client.uuid)
        self.assertEqual(data["bloks_versioning_id"], client.bloks_versioning_id)
        self.assertEqual(
            json.loads(data["bk_client_context"]),
            {"bloks_version": client.bloks_versioning_id, "styles_id": "instagram"},
        )
        params = json.loads(data["params"])
        self.assertEqual(params["client_input_params"]["aac"], client.caa_aac)
        self.assertEqual(params["client_input_params"]["password"], password)
        self.assertEqual(params["server_params"]["waterfall_id"], "synthetic-flow")
        return params

    def assert_qpl_contract(self, params):
        # The QPL merge was independently checked against the current Android dispatcher.
        server = params["server_params"]
        with self.subTest(field="INTERNAL__latency_qpl_marker_id"):
            self.assertIn("INTERNAL__latency_qpl_marker_id", server)
            self.assertEqual(server["INTERNAL__latency_qpl_marker_id"], 36707139)
        with self.subTest(field="INTERNAL__latency_qpl_instance_id"):
            self.assertIn("INTERNAL__latency_qpl_instance_id", server)
            self.assertIs(type(server["INTERNAL__latency_qpl_instance_id"]), int)

    def assert_direct_home_contract(self, params):
        with self.subTest(field="client_input_params.should_show_nested_nta_from_aymh"):
            self.assertEqual(params["client_input_params"].get("should_show_nested_nta_from_aymh"), 0)
        expected_server = {
            "is_from_empty_password": 0,
            "login_surface": "login_home",
            "reg_flow_source": "login_home_native_integration_point",
            "login_entry_point": "logged_out",
            "qe_device_id": "synthetic-client-uuid",
        }
        for field, expected in expected_server.items():
            with self.subTest(field=f"server_params.{field}"):
                self.assertEqual(params["server_params"].get(field), expected)
        with self.subTest(field="server_params.should_show_nested_nta_from_aymh"):
            self.assertNotIn("should_show_nested_nta_from_aymh", params["server_params"])

    def test_default_449_serializes_server_qpl_fields(self):
        self.assert_qpl_contract(self.serialized_params())

    def test_retained_448_serializes_server_qpl_fields(self):
        self.assert_qpl_contract(self.serialized_params("448.0.0.0.20"))

    def test_default_449_preserves_direct_home_context(self):
        self.assert_direct_home_contract(self.serialized_params())

    def test_retained_448_preserves_direct_home_context(self):
        self.assert_direct_home_contract(self.serialized_params("448.0.0.0.20"))
