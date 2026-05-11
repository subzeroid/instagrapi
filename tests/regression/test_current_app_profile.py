from instagrapi import config
from tests.helpers import *


class CurrentAppProfileRegressionTestCase(unittest.TestCase):
    def test_default_client_uses_current_android_app_profile(self):
        client = Client()

        self.assertEqual(client.device_settings["app_version"], config.DEFAULT_APP_VERSION)
        self.assertEqual(client.device_settings["version_code"], "961145276")
        self.assertEqual(
            client.bloks_versioning_id,
            "7189b949425f9bf80ea8bd880cf5a3080b292d9b1c4b38a18d112f7c4b71e7a8",
        )
        self.assertEqual(
            client.user_agent,
            (
                "Instagram 428.0.0.47.67 Android (34/14; 480dpi; 1344x2992; "
                "Google/google; Pixel 8 Pro; husky; husky; en_US; 961145276)"
            ),
        )

    def test_default_device_profile_matches_current_android_baseline(self):
        client = Client()

        self.assertEqual(
            client.device_settings,
            {
                "android_version": 34,
                "android_release": "14",
                "dpi": "480dpi",
                "resolution": "1344x2992",
                "manufacturer": "Google/google",
                "device": "husky",
                "model": "Pixel 8 Pro",
                "cpu": "husky",
                "app_version": "428.0.0.47.67",
                "version_code": "961145276",
                "bloks_versioning_id": "7189b949425f9bf80ea8bd880cf5a3080b292d9b1c4b38a18d112f7c4b71e7a8",
            },
        )

    def test_set_app_can_apply_current_default_profile_explicitly(self):
        client = Client()
        client.set_app("385.0.0.47.74")

        client.set_app(config.DEFAULT_APP_VERSION)

        self.assertEqual(client.device_settings["app_version"], config.DEFAULT_APP_VERSION)
        self.assertEqual(client.device_settings["version_code"], "961145276")
        self.assertEqual(
            client.bloks_versioning_id,
            "7189b949425f9bf80ea8bd880cf5a3080b292d9b1c4b38a18d112f7c4b71e7a8",
        )

    def test_private_headers_use_current_android_transport_values(self):
        client = Client()

        self.assertEqual(client.private.headers["X-FB-HTTP-Engine"], "Tigon/MNS/TCP")
        self.assertEqual(client.private.headers["X-IG-Capabilities"], "3brTv10=")
        self.assertEqual(client.private.headers["X-IG-App-ID"], "567067343352427")
        self.assertEqual(
            client.private.headers["X-Bloks-Version-Id"],
            "7189b949425f9bf80ea8bd880cf5a3080b292d9b1c4b38a18d112f7c4b71e7a8",
        )

    def test_saved_legacy_app_profile_is_not_overridden_by_default(self):
        client = Client(
            {
                "device_settings": {
                    "app_version": "385.0.0.47.74",
                    "version_code": "378906843",
                    "bloks_versioning_id": ("a8973d49a9cc6a6f65a4997c10216ce2a06f65a517010e64885e92029bb19221"),
                },
            }
        )

        self.assertEqual(client.device_settings["app_version"], "385.0.0.47.74")
        self.assertEqual(client.device_settings["version_code"], "378906843")
        self.assertEqual(
            client.bloks_versioning_id,
            "a8973d49a9cc6a6f65a4997c10216ce2a06f65a517010e64885e92029bb19221",
        )

    def test_override_app_version_replaces_saved_profile_with_current_default(self):
        client = Client(
            {
                "device_settings": {
                    "app_version": "385.0.0.47.74",
                    "version_code": "378906843",
                    "bloks_versioning_id": ("a8973d49a9cc6a6f65a4997c10216ce2a06f65a517010e64885e92029bb19221"),
                },
            }
        )

        client.override_app_version = True
        client.set_app()

        self.assertEqual(client.device_settings["app_version"], config.DEFAULT_APP_VERSION)
        self.assertEqual(client.device_settings["version_code"], "961145276")

    def test_constructor_override_app_version_replaces_saved_profile_with_current_default(self):
        client = Client(
            {
                "device_settings": {
                    "app_version": "385.0.0.47.74",
                    "version_code": "378906843",
                    "bloks_versioning_id": ("a8973d49a9cc6a6f65a4997c10216ce2a06f65a517010e64885e92029bb19221"),
                },
            },
            override_app_version=True,
        )

        self.assertEqual(client.device_settings["app_version"], config.DEFAULT_APP_VERSION)
        self.assertEqual(client.device_settings["version_code"], "961145276")
