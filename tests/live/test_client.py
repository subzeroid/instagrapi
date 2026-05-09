from tests.helpers import *


class ClientTestCase(unittest.TestCase):
    def test_default_settings_are_not_shared_between_clients(self):
        first = Client()
        second = Client()

        first.set_retry_config(session_retry_total=9)

        self.assertEqual(first.settings["session_retry_total"], 9)
        self.assertEqual(second.settings["session_retry_total"], 3)

    def test_set_device_rebuilds_user_agent(self):
        cl = Client()
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
        expected_user_agent = (
            "Instagram 165.1.0.20.119 Android (27/8.1.0; 480dpi; "
            "1080x1776; motorola; montana; Moto G (5S); qcom; en_US; "
            "253447809)"
        )

        cl.set_device(device)

        self.assertEqual(cl.user_agent, expected_user_agent)
        self.assertEqual(cl.settings["user_agent"], expected_user_agent)

    def test_jazoest(self):
        phone_id = "57d64c41-a916-3fa5-bd7a-3796c1dab122"
        self.assertTrue(generate_jazoest(phone_id), "22413")

    def test_lg(self):
        settings = {
            "uuids": {
                "phone_id": "57d64c41-a916-3fa5-bd7a-3796c1dab122",
                "uuid": "8aa373c6-f316-44d7-b49e-d74563f4a8f3",
                "client_session_id": "6c296d0a-3534-4dce-b5aa-a6a6ab017443",
                "advertising_id": "8dc88b76-dfbc-44dc-abbc-31a6f1d54b04",
                "android_device_id": "android-e021b636049dc0e9",
                "request_id": "72d0f808-b5cd-40e2-910b-01ae7ae60a5b",
                "tray_session_id": "bc44ef1d-c083-4ecd-b369-6f4a9e1a077c",
            },
            "mid": "YA1YMAACAAGtxxnZ1p4AYc8ufNMn",
            "device_settings": {
                "cpu": "h1",
                "dpi": "640dpi",
                "model": "h1",
                "device": "RS988",
                "resolution": "1440x2392",
                "app_version": "269.0.0.19.301",
                "manufacturer": "LGE/lge",
                "version_code": "168361634",
                "android_release": "6.0.1",
                "android_version": 23,
            },
            # "user_agent": "Instagram 117.0.0.28.123 Android (23/6.0.1; US; 168361634)"
            "user_agent": "Instagram 269.0.0.19.301 Android (27/8.1.0; 480dpi; 1080x1776; motorola; Moto G (5S); montana; qcom; ru_RU; 253447809)",
            "country": "RU",
            "locale": "ru_RU",
            "timezone_offset": 10800,  # Moscow, GMT+3
        }
        cl = Client(settings)
        cl.login(ACCOUNT_USERNAME, ACCOUNT_PASSWORD)
        self.assertIsInstance(cl.user_id, int)
        self.assertEqual(cl.username, ACCOUNT_USERNAME)

    def test_country_locale_timezone(self):
        cl = Client()
        # defaults:
        self.assertEqual(cl.country, "US")
        self.assertEqual(cl.locale, "en_US")
        self.assertEqual(cl.timezone_offset, -14400)
        settings = {
            "uuids": {
                "phone_id": "57d64c41-a916-3fa5-bd7a-3796c1dab122",
                "uuid": "8aa373c6-f316-44d7-b49e-d74563f4a8f3",
                "client_session_id": "6c296d0a-3534-4dce-b5aa-a6a6ab017443",
                "advertising_id": "8dc88b76-dfbc-44dc-abbc-31a6f1d54b04",
                "android_device_id": "android-e021b636049dc0e9",
                "request_id": "72d0f808-b5cd-40e2-910b-01ae7ae60a5b",
                "tray_session_id": "bc44ef1d-c083-4ecd-b369-6f4a9e1a077c",
            },
            "mid": "YA1YMAACAAGtxxnZ1p4AYc8ufNMn",
            "device_settings": {
                "app_version": "269.0.0.19.301",
                "android_version": 26,
                "android_release": "8.0.0",
                "dpi": "480dpi",
                "resolution": "1080x1920",
                "manufacturer": "Xiaomi",
                "device": "capricorn",
                "model": "MI 5s",
                "cpu": "qcom",
                "version_code": "301484483",
            },
            "user_agent": "Instagram 269.0.0.19.301 Android (26/8.0.0; 480dpi; 1080x1920; Xiaomi; MI 5s; capricorn; qcom; en_US; 301484483)",
            "country": "UK",
            "locale": "en_US",
            "timezone_offset": 3600,  # London, GMT+1
        }
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
        # change settings
        cl.set_settings(settings)

        def check(country, locale, timezone_offset):
            self.assertDictEqual(cl.get_settings()["uuids"], settings["uuids"])
            self.assertEqual(cl.country, country)
            self.assertEqual(cl.locale, locale)
            self.assertEqual(cl.timezone_offset, timezone_offset)
            self.assertIn(cl.locale, cl.user_agent)

        cl.set_country("AU")  # change only country
        check("AU", "en_US", 3600)
        cl.set_locale("ru_RU")  # locale change country
        check("RU", "ru_RU", 3600)
        cl.set_timezone_offset(10800)  # change timezone_offset
        check("RU", "ru_RU", 10800)
        cl.set_user_agent("TEST")  # change user-agent
        self.assertEqual(cl.get_settings()["user_agent"], "TEST")
        cl.set_device(device)  # change device
        self.assertDictEqual(cl.get_settings()["device_settings"], device)
        cl.set_settings(settings)  # load source settings
        check("UK", "en_US", 3600)
        self.assertEqual(cl.get_settings()["user_agent"], settings["user_agent"])
        self.assertEqual(cl.get_settings()["device_settings"], settings["device_settings"])

    def test_media_pk_from_share_url(self):
        cl = Client()
        response = Mock(headers={"Location": "https://www.instagram.com/p/DC2konOtSse/"})
        with mock.patch.object(cl.public, "get", return_value=response) as public_get:
            self.assertEqual(
                cl.media_pk_from_url("https://www.instagram.com/share/p/BALv9Ep4YH"),
                cl.media_pk_from_code("DC2konOtSse"),
            )
        public_get.assert_called_once()

    def test_set_retry_config_updates_settings_and_session_adapters(self):
        cl = Client()
        cl.set_retry_config(
            request_timeout=0,
            public_request_retries_count=5,
            public_request_retries_timeout=4,
            session_retry_total=6,
            session_retry_backoff_factor=1,
            session_retry_statuses=[429, 500],
        )

        settings = cl.get_settings()
        self.assertEqual(settings["request_timeout"], 0)
        self.assertEqual(settings["public_request_retries_count"], 5)
        self.assertEqual(settings["public_request_retries_timeout"], 4)
        self.assertEqual(settings["session_retry_total"], 6)
        self.assertEqual(settings["session_retry_backoff_factor"], 1)
        self.assertEqual(settings["session_retry_statuses"], [429, 500])

        public_retry = cl.public.adapters["https://"].max_retries
        private_retry = cl.private.adapters["https://"].max_retries
        self.assertEqual(public_retry.total, 6)
        self.assertEqual(private_retry.total, 6)
        self.assertEqual(public_retry.backoff_factor, 1)
        self.assertEqual(private_retry.backoff_factor, 1)
        self.assertEqual(sorted(public_retry.status_forcelist), [429, 500])
        self.assertEqual(sorted(private_retry.status_forcelist), [429, 500])

    def test_settings_round_trip_preserves_retry_config(self):
        settings = {
            "uuids": {},
            "cookies": {},
            "device_settings": {},
            "request_timeout": 0,
            "public_request_retries_count": 4,
            "public_request_retries_timeout": 3,
            "session_retry_total": 7,
            "session_retry_backoff_factor": 1,
            "session_retry_statuses": [429, 503],
        }
        cl = Client()
        cl.set_settings(settings)

        self.assertEqual(cl.request_timeout, 0)
        self.assertEqual(cl.public_request_retries_count, 4)
        self.assertEqual(cl.public_request_retries_timeout, 3)
        self.assertEqual(cl.session_retry_total, 7)
        self.assertEqual(cl.session_retry_backoff_factor, 1)
        self.assertEqual(cl.session_retry_statuses, [429, 503])
        self.assertEqual(cl.public.adapters["https://"].max_retries.total, 7)
        self.assertEqual(cl.private.adapters["https://"].max_retries.total, 7)

    def test_public_request_uses_client_retry_defaults(self):
        cl = Client(
            request_timeout=0,
            public_request_retries_count=4,
            public_request_retries_timeout=0,
        )
        attempts = {"count": 0}

        def fake_send(*args, **kwargs):
            attempts["count"] += 1
            if attempts["count"] < 4:
                raise ClientConnectionError("temporary")
            return {"status": "ok"}

        with mock.patch.object(cl, "_send_public_request", side_effect=fake_send):
            result = cl.public_request("https://example.com", return_json=True)

        self.assertEqual(attempts["count"], 4)
        self.assertEqual(result, {"status": "ok"})
