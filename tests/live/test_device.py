from tests import helpers as _helpers
from tests.helpers import *


class ClientDeviceTestCase(_helpers.ClientPrivateTestCase):
    def test_set_device(self):
        fields = ["uuids", "cookies", "last_login", "device_settings", "user_agent"]
        for field in fields:
            settings = self.cl.get_settings()
            self.assertIn(field, settings)
        device = {
            "app_version": "165.1.0.20.119",
            "android_version": 27,
            "android_release": "8.1.0",
            "dpi": "480dpi",
            "resolution": "1080x1776",
            "manufacturer": "motorola",
            "device": "Moto G (5S)",
            "model": "montana",
            "cpu": "qcom",
            "version_code": "253447809",
        }
        user_agent = "Instagram 165.1.0.29.119 Android (27/8.1.0; 480dpi; 1080x1776; motorola; Moto G (5S); montana; qcom; ru_RU; 253447809)"
        self.cl.set_device(device)
        self.cl.set_user_agent(user_agent)
        settings = self.cl.get_settings()
        self.assertDictEqual(device, settings["device_settings"])
        self.assertEqual(user_agent, settings["user_agent"])
        self.user_info_by_username("example")
        request_user_agent = self.cl.last_response.request.headers.get("User-Agent")
        self.assertEqual(user_agent, request_user_agent)


class ClientDeviceAgentTestCase(_helpers.ClientPrivateTestCase):
    def test_set_device_agent(self):
        device = {
            "app_version": "165.1.0.20.119",
            "android_version": 27,
            "android_release": "8.1.0",
            "dpi": "480dpi",
            "resolution": "1080x1776",
            "manufacturer": "motorola",
            "device": "Moto G (5S)",
            "model": "montana",
            "cpu": "qcom",
            "version_code": "253447809",
        }
        user_agent = "Instagram 165.1.0.29.119 Android (27/8.1.0; 480dpi; 1080x1776; motorola; Moto G (5S); montana; qcom; ru_RU; 253447809)"
        cl = Client()
        cl.set_device(device)
        cl.set_user_agent(user_agent)
        cl.login(ACCOUNT_USERNAME, ACCOUNT_PASSWORD)
        self.assertDictEqual(device, cl.settings["device_settings"])
        self.assertEqual(user_agent, cl.settings["user_agent"])
