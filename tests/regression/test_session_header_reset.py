import unittest
from copy import deepcopy
from unittest.mock import Mock

from instagrapi import Client


class SessionHeaderResetTestCase(unittest.TestCase):
    def client_with_session(self):
        client = Client()
        settings = client.get_settings()
        settings.update(
            authorization_data={"ds_user_id": "123", "sessionid": "old-session"},
            ig_u_rur="OLD-ROUTE",
            ig_www_claim="old-claim",
            mid="preserved-machine",
        )
        client.set_settings(settings)
        client.usdid_generate()
        client.private.headers["X-Custom"] = "preserved"
        client.private.headers["ig-u-custom-account"] = "old-account"
        client.private.headers["x-ig-www-claim"] = "old-claim"
        client.private.headers["ig-intended-user-id"] = "123"
        return client

    def assert_account_headers_cleared(self, client):
        self.assertFalse([key for key in client.private.headers if key.lower().startswith("ig-u-")])
        headers = {key.lower(): value for key, value in client.private.headers.items()}
        self.assertEqual(headers["ig-intended-user-id"], "0")
        self.assertEqual(headers["x-ig-www-claim"], "0")
        self.assertEqual(client.ig_u_rur, "")
        self.assertEqual(client.ig_www_claim, "")
        self.assertEqual(client.get_settings()["ig_u_rur"], "")
        self.assertEqual(client.get_settings()["ig_www_claim"], "")
        self.assertFalse([key for key in client.base_headers if key.lower().startswith("ig-u-")])

    def test_relogin_clears_account_headers_before_caa(self):
        client = self.client_with_session()
        before = deepcopy(client.get_settings())

        def caa(**kwargs):
            self.assert_account_headers_cleared(client)
            self.assertNotIn("Authorization", client.private.headers)
            return {"logged_in": True}

        client.bloks_caa_login = Mock(side_effect=caa)
        client.login_flow = Mock()
        self.assertTrue(client.login("example", "password", relogin=True))
        after = client.get_settings()
        for key in ("uuids", "device_settings", "mid", "usdid", "private_transport", "tls_verify"):
            self.assertEqual(after[key], before[key], key)
        self.assertEqual(client.private.headers["X-Custom"], "preserved")

    def test_legacy_relogin_clears_account_headers_before_preflight(self):
        client = self.client_with_session()

        def preflight():
            self.assert_account_headers_cleared(client)
            return True

        client.pre_login_flow = Mock(side_effect=preflight)
        client.password_encrypt = Mock(return_value="encrypted-password")
        client.private_request = Mock(return_value=True)
        client.last_response = Mock(headers={})
        client.login_flow = Mock()
        self.assertTrue(client.login_legacy("example", "password", relogin=True))

    def test_successful_logout_clears_account_headers(self):
        client = self.client_with_session()
        client.private_request = Mock(return_value={"status": "ok"})
        self.assertTrue(client.logout())
        self.assert_account_headers_cleared(client)
        self.assertIsNone(client.user_id)
        self.assertEqual(client.private.headers["X-Custom"], "preserved")

    def test_failed_logout_preserves_account_headers(self):
        client = self.client_with_session()
        before = dict(client.private.headers)
        client.private_request = Mock(return_value={"status": "fail"})
        self.assertFalse(client.logout())
        self.assertEqual(dict(client.private.headers), before)
        self.assertEqual(client.user_id, 123)

    def test_existing_session_reuse_preserves_account_headers(self):
        client = self.client_with_session()
        before = dict(client.private.headers)
        client.account_info = Mock(return_value=object())
        self.assertTrue(client.login("example", "password"))
        self.assertEqual(dict(client.private.headers), before)
        self.assertEqual(client.ig_www_claim, "old-claim")

    def test_cookie_only_reset_preserves_account_headers(self):
        client = self.client_with_session()
        before = dict(client.private.headers)
        client._clear_session_state(clear_private_cookies=True, clear_public_cookies=True)
        self.assertEqual(dict(client.private.headers), before)
        self.assertEqual(client.user_id, 123)
        self.assertEqual(client.ig_u_rur, "OLD-ROUTE")

    def test_new_authorization_uses_new_account_headers(self):
        client = self.client_with_session()
        client._clear_session_state(clear_authorization_data=True, clear_authorization_header=True)
        self.assert_account_headers_cleared(client)
        client.authorization_data = {"ds_user_id": "456", "sessionid": "new-session"}
        client.set_ig_u_rur("NEW-ROUTE")
        client.set_ig_www_claim("new-claim")
        client.private.headers.update(client.base_headers)
        self.assertEqual(client.private.headers["IG-U-DS-USER-ID"], "456")
        self.assertEqual(client.private.headers["IG-INTENDED-USER-ID"], "456")
        self.assertEqual(client.private.headers["X-IG-WWW-Claim"], "new-claim")
        self.assertEqual(client.private.headers["IG-U-RUR"].strip('"'), "NEW-ROUTE")
        self.assertNotIn("ig-u-custom-account", client.private.headers)
