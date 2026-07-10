from instagrapi.exceptions import BadPassword
from tests.helpers import *


class AuthAndStoryRegressionTestCase(unittest.TestCase):
    def test_login_requires_username_and_password(self):
        client = Client()

        with self.assertRaises(BadCredentials):
            client.login()

    def test_login_continues_after_pre_login_throttling(self):
        client = Client()
        client.username = "example"
        client.password = "password"
        client.authorization_data = {}
        client.last_response = Mock(headers={"ig-set-authorization": "Bearer token"})
        client.parse_authorization = Mock(return_value={"sessionid": "abc"})
        client.pre_login_flow = Mock(side_effect=PleaseWaitFewMinutes())
        client.private_request = Mock(return_value=True)
        client.login_flow = Mock()
        client.password_encrypt = Mock(return_value="enc-password")

        result = client.login()

        self.assertTrue(result)
        client.pre_login_flow.assert_called_once_with()
        client.private_request.assert_called_once()
        client.login_flow.assert_called_once_with()

    def test_login_continues_after_client_throttled_error(self):
        client = Client()
        client.username = "example"
        client.password = "password"
        client.authorization_data = {}
        client.last_response = Mock(headers={"ig-set-authorization": "Bearer token"})
        client.parse_authorization = Mock(return_value={"sessionid": "abc"})
        client.pre_login_flow = Mock(side_effect=ClientThrottledError())
        client.private_request = Mock(return_value=True)
        client.login_flow = Mock()
        client.password_encrypt = Mock(return_value="enc-password")

        result = client.login()

        self.assertTrue(result)
        client.pre_login_flow.assert_called_once_with()
        client.private_request.assert_called_once()
        client.login_flow.assert_called_once_with()

    def test_login_relogin_guard_raises_before_network_calls(self):
        client = Client()
        client.username = "example"
        client.password = "password"
        client.relogin_attempt = 2
        client.private.cookies.set("sessionid", "stale")
        client.public.cookies.set("sessionid", "public-stale")
        client.private.headers["Authorization"] = "Bearer stale"

        with self.assertRaises(ReloginAttemptExceeded):
            client.login(relogin=True)

        self.assertEqual(client.authorization_data, {})
        self.assertNotIn("Authorization", client.private.headers)
        self.assertEqual(client.private.cookies.get_dict(), {})
        self.assertEqual(client.public.cookies.get_dict(), {})

    def test_login_returns_early_when_user_is_already_authorized(self):
        client = Client()
        client.authorization_data = {"ds_user_id": "123"}
        client.pre_login_flow = Mock()
        client.private_request = Mock()

        result = client.login("example", "password")

        self.assertTrue(result)
        client.pre_login_flow.assert_not_called()
        client.private_request.assert_not_called()

    def test_login_uses_stored_username_when_called_without_args(self):
        client = Client()
        client.username = "example"
        client.password = "password"
        client.authorization_data = {}
        client.last_response = Mock(headers={"ig-set-authorization": "Bearer token"})
        client.parse_authorization = Mock(return_value={"sessionid": "abc"})
        client.pre_login_flow = Mock(return_value=True)
        client.private_request = Mock(return_value=True)
        client.login_flow = Mock()
        client.password_encrypt = Mock(return_value="enc-password")

        result = client.login()

        self.assertTrue(result)
        payload = client.private_request.call_args.args[1]
        self.assertEqual(payload["username"], "example")

    def test_login_two_factor_requires_verification_code(self):
        client = Client()
        client.username = "example"
        client.password = "password"
        client.pre_login_flow = Mock(return_value=True)
        client.private_request = Mock(side_effect=TwoFactorRequired("Two-factor authentication required"))
        client.password_encrypt = Mock(return_value="enc-password")

        with self.assertRaises(TwoFactorRequired) as cm:
            client.login()

        self.assertIn("you did not provide verification_code", str(cm.exception))

    def test_login_two_factor_uses_verification_code_flow(self):
        client = Client()
        client.username = "example"
        client.password = "password"
        client.authorization_data = {}
        client.uuid = "uuid-1"
        client.phone_id = "phone-1"
        client.android_device_id = "android-1"
        client._token = "csrftoken"
        client.last_json = {"two_factor_info": {"two_factor_identifier": "two-factor-id"}}
        client.last_response = Mock(headers={"ig-set-authorization": "Bearer second"})
        client.parse_authorization = Mock(return_value={"sessionid": "abc"})
        client.pre_login_flow = Mock(return_value=True)
        client.password_encrypt = Mock(return_value="enc-password")
        client.login_flow = Mock()
        client.private_request = Mock(
            side_effect=[
                TwoFactorRequired("Two-factor authentication required"),
                True,
            ]
        )

        result = client.login(verification_code="123456")

        self.assertTrue(result)
        self.assertEqual(client.private_request.call_count, 2)
        first_call = client.private_request.call_args_list[0]
        self.assertEqual(first_call.args[0], "accounts/login/")
        second_call = client.private_request.call_args_list[1]
        self.assertEqual(second_call.args[0], "accounts/two_factor_login/")
        self.assertEqual(second_call.args[1]["verification_code"], "123456")
        self.assertEqual(second_call.args[1]["two_factor_identifier"], "two-factor-id")
        self.assertEqual(second_call.args[1]["username"], "example")
        client.login_flow.assert_called_once_with()

    def test_login_two_factor_invalid_parameters_raises_clear_bloks_hint(self):
        client = Client()
        client.username = "example"
        client.password = "password"
        client.authorization_data = {}
        client.uuid = "uuid-1"
        client.phone_id = "phone-1"
        client.android_device_id = "android-1"
        client._token = "csrftoken"
        client.last_json = {"two_factor_info": {"two_factor_identifier": "two-factor-id"}}
        client.pre_login_flow = Mock(return_value=True)
        client.password_encrypt = Mock(return_value="enc-password")
        client.private_request = Mock(
            side_effect=[
                TwoFactorRequired("Two-factor authentication required"),
                UnknownError("Invalid Parameters", response=Mock(status_code=400)),
            ]
        )

        with self.assertRaises(TwoFactorRequired) as cm:
            client.login(verification_code="123456")

        self.assertIn("Bloks-based two-factor verification flow", str(cm.exception))
        self.assertEqual(client.private_request.call_count, 2)

    def test_login_two_factor_invalid_parameters_falls_back_to_bloks_when_context_available(self):
        client = Client()
        client.username = "example"
        client.password = "password"
        client.authorization_data = {}
        client.uuid = "uuid-1"
        client.phone_id = "phone-1"
        client.android_device_id = "android-1"
        client._token = "csrftoken"
        client.last_json = {
            "two_factor_info": {
                "two_factor_identifier": "two-factor-id",
                "two_step_verification_context": "context-1",
                "totp_two_factor_on": True,
                "sms_two_factor_on": False,
            }
        }
        client.pre_login_flow = Mock(return_value=True)
        client.password_encrypt = Mock(return_value="enc-password")
        client.login_flow = Mock()
        client.private_request = Mock(
            side_effect=[
                TwoFactorRequired("Two-factor authentication required"),
                UnknownError("Invalid Parameters", response=Mock(status_code=400)),
            ]
        )
        client.bloks_two_step_verification_entrypoint = Mock(return_value={"status": "ok"})
        client.bloks_two_step_verification_method_picker = Mock(return_value={"status": "ok"})
        client.bloks_two_step_verification_select_method = Mock(return_value={"status": "ok"})
        client.bloks_two_step_verification_verify_code = Mock(return_value={"layout": {}})
        client.bloks_apply_login_response = Mock(return_value=True)

        result = client.login(verification_code="123456")

        self.assertTrue(result)
        self.assertEqual(client.private_request.call_count, 2)
        client.bloks_two_step_verification_entrypoint.assert_called_once_with("context-1")
        client.bloks_two_step_verification_method_picker.assert_called_once_with("context-1")
        client.bloks_two_step_verification_select_method.assert_called_once_with("context-1", selected_method="totp")
        client.bloks_two_step_verification_verify_code.assert_called_once_with(
            "context-1",
            "123456",
            challenge="totp",
        )
        client.bloks_apply_login_response.assert_called_once_with({"layout": {}})
        client.login_flow.assert_called_once_with()

    def test_login_two_factor_backup_code_with_context_uses_bloks_without_legacy_two_factor_request(self):
        client = Client()
        client.username = "example"
        client.password = "password"
        client.authorization_data = {}
        client.uuid = "uuid-1"
        client.phone_id = "phone-1"
        client.android_device_id = "android-1"
        client._token = "csrftoken"
        client.last_json = {
            "two_factor_info": {
                "two_factor_identifier": "two-factor-id",
                "two_step_verification_context": "context-1",
                "totp_two_factor_on": True,
                "sms_two_factor_on": False,
            }
        }
        client.pre_login_flow = Mock(return_value=True)
        client.password_encrypt = Mock(return_value="enc-password")
        client.login_flow = Mock()
        client.private_request = Mock(side_effect=[TwoFactorRequired("Two-factor authentication required")])
        client.bloks_two_step_verification_entrypoint = Mock(return_value={"status": "ok"})
        client.bloks_two_step_verification_method_picker = Mock(return_value={"status": "ok"})
        client.bloks_two_step_verification_select_method = Mock(return_value={"status": "ok"})
        client.bloks_two_step_verification_enter_backup_code = Mock(return_value={"status": "ok"})
        client.bloks_two_step_verification_verify_code = Mock(return_value={"layout": {}})
        client.bloks_apply_login_response = Mock(return_value=True)

        result = client.login(verification_code="1234 5678")

        self.assertTrue(result)
        self.assertEqual(client.private_request.call_count, 1)
        client.bloks_two_step_verification_select_method.assert_called_once_with(
            "context-1",
            selected_method="backup_codes",
        )
        client.bloks_two_step_verification_enter_backup_code.assert_called_once_with("context-1")
        client.bloks_two_step_verification_verify_code.assert_called_once_with(
            "context-1",
            "12345678",
            challenge="backup_codes",
        )
        client.login_flow.assert_called_once_with()

    def test_login_two_factor_invalid_parameters_without_context_keeps_clear_error(self):
        client = Client()
        client.username = "example"
        client.password = "password"
        client.authorization_data = {}
        client.uuid = "uuid-1"
        client.phone_id = "phone-1"
        client.android_device_id = "android-1"
        client._token = "csrftoken"
        client.last_json = {"two_factor_info": {"two_factor_identifier": "two-factor-id"}}
        client.pre_login_flow = Mock(return_value=True)
        client.password_encrypt = Mock(return_value="enc-password")
        client.private_request = Mock(
            side_effect=[
                TwoFactorRequired("Two-factor authentication required"),
                UnknownError("Invalid Parameters", response=Mock(status_code=400)),
            ]
        )
        client.bloks_two_step_verification_verify_code = Mock()

        with self.assertRaises(TwoFactorRequired) as cm:
            client.login(verification_code="123456")

        self.assertIn("two_step_verification_context", str(cm.exception))
        client.bloks_two_step_verification_verify_code.assert_not_called()

    def test_login_bad_password_with_bloks_context_and_code_falls_back_to_bloks(self):
        client = Client()
        client.username = "example"
        client.password = "password"
        client.authorization_data = {}
        client.last_json = {
            "two_step_verification_context": "context-1",
            "sms_two_factor_on": True,
            "totp_two_factor_on": False,
        }
        client.pre_login_flow = Mock(return_value=True)
        client.password_encrypt = Mock(return_value="enc-password")
        client.login_flow = Mock()
        client.private_request = Mock(side_effect=BadPassword("Bad Password", response=Mock(status_code=400)))
        client.bloks_two_step_verification_entrypoint = Mock(return_value={"status": "ok"})
        client.bloks_two_step_verification_method_picker = Mock(return_value={"status": "ok"})
        client.bloks_two_step_verification_select_method = Mock(return_value={"status": "ok"})
        client.bloks_two_step_verification_verify_code = Mock(return_value={"layout": {}})
        client.bloks_apply_login_response = Mock(return_value=True)

        result = client.login(verification_code="654321")

        self.assertTrue(result)
        client.bloks_two_step_verification_select_method.assert_called_once_with("context-1", selected_method="sms")
        client.bloks_two_step_verification_verify_code.assert_called_once_with(
            "context-1",
            "654321",
            challenge="sms",
        )
        client.login_flow.assert_called_once_with()

    def test_login_bad_password_without_context_tries_caa_bloks_context_when_code_provided(self):
        client = Client()
        client.username = "example"
        client.password = "password"
        client.authorization_data = {}
        client.last_json = {"message": "The password you entered is incorrect.", "error_type": "bad_password"}
        client.pre_login_flow = Mock(return_value=True)
        client.password_encrypt = Mock(return_value="enc-password")
        client.login_flow = Mock()
        client.private_request = Mock(side_effect=BadPassword("Bad Password", response=Mock(status_code=400)))
        caa_result = {"layout": {"bloks_payload": {"action": "action-with-context"}}}
        client.bloks_caa_login_send_request = Mock(return_value=caa_result)
        client.bloks_extract_two_step_verification_context = Mock(return_value="context-1")
        client.bloks_two_step_verification_entrypoint = Mock(return_value={"status": "ok"})
        client.bloks_two_step_verification_method_picker = Mock(return_value={"status": "ok"})
        client.bloks_two_step_verification_select_method = Mock(return_value={"status": "ok"})
        client.bloks_two_step_verification_verify_code = Mock(return_value={"layout": {}})
        client.bloks_apply_login_response = Mock(return_value=True)

        result = client.login(verification_code="654321")

        self.assertTrue(result)
        client.bloks_caa_login_send_request.assert_called_once_with("password", login_attempt_count=1)
        client.bloks_extract_two_step_verification_context.assert_called_once_with(caa_result)
        client.bloks_two_step_verification_select_method.assert_called_once_with("context-1", selected_method="totp")
        client.bloks_two_step_verification_verify_code.assert_called_once_with(
            "context-1",
            "654321",
            challenge="totp",
        )
        client.login_flow.assert_called_once_with()

    def test_login_bad_password_recovery_response_does_not_try_caa_bloks(self):
        client = Client()
        client.username = "example"
        client.password = "password"
        client.authorization_data = {}
        client.last_json = {
            "message": "You can log in with your linked Facebook account.",
            "error_title": "Forgotten password for example?",
            "error_type": "bad_password",
        }
        client.pre_login_flow = Mock(return_value=True)
        client.password_encrypt = Mock(return_value="enc-password")
        client.private_request = Mock(side_effect=BadPassword("Bad Password", response=Mock(status_code=400)))
        client.bloks_caa_login_send_request = Mock(
            side_effect=AssertionError("recovery bad_password responses are not CAA two-factor challenges")
        )

        with self.assertRaises(BadPassword):
            client.login(verification_code="654321")

        client.bloks_caa_login_send_request.assert_not_called()

    def test_login_with_eight_digit_backup_code_selects_backup_code_bloks_challenge(self):
        client = Client()
        client.username = "example"
        client.password = "password"
        client.authorization_data = {}
        client.last_json = {
            "two_step_verification_context": "context-1",
            "sms_two_factor_on": False,
            "totp_two_factor_on": True,
        }
        client.pre_login_flow = Mock(return_value=True)
        client.password_encrypt = Mock(return_value="enc-password")
        client.login_flow = Mock()
        client.private_request = Mock(side_effect=BadPassword("Bad Password", response=Mock(status_code=400)))
        client.bloks_two_step_verification_entrypoint = Mock(return_value={"status": "ok"})
        client.bloks_two_step_verification_method_picker = Mock(return_value={"status": "ok"})
        client.bloks_two_step_verification_select_method = Mock(return_value={"status": "ok"})
        client.bloks_two_step_verification_enter_backup_code = Mock(return_value={"status": "ok"})
        client.bloks_two_step_verification_verify_code = Mock(return_value={"layout": {}})
        client.bloks_apply_login_response = Mock(return_value=True)

        result = client.login(verification_code="1234 5678")

        self.assertTrue(result)
        client.bloks_two_step_verification_select_method.assert_called_once_with(
            "context-1",
            selected_method="backup_codes",
        )
        client.bloks_two_step_verification_enter_backup_code.assert_called_once_with("context-1")
        client.bloks_two_step_verification_verify_code.assert_called_once_with(
            "context-1",
            "12345678",
            challenge="backup_codes",
        )
        client.login_flow.assert_called_once_with()

    def test_login_bad_password_without_context_raises_clear_error_when_caa_has_no_context(self):
        client = Client()
        client.username = "example"
        client.password = "password"
        client.authorization_data = {}
        client.last_json = {"message": "The password you entered is incorrect.", "error_type": "bad_password"}
        client.pre_login_flow = Mock(return_value=True)
        client.password_encrypt = Mock(return_value="enc-password")
        client.private_request = Mock(side_effect=BadPassword("Bad Password", response=Mock(status_code=400)))
        client.bloks_caa_login_send_request = Mock(return_value={"layout": {"bloks_payload": {"action": ""}}})
        client.bloks_extract_two_step_verification_context = Mock(return_value="")
        client.bloks_two_step_verification_verify_code = Mock()

        with self.assertRaises(TwoFactorRequired) as cm:
            client.login(verification_code="654321")

        self.assertIn("CAA response did not include two_step_verification_context", str(cm.exception))
        client.bloks_caa_login_send_request.assert_called_once_with("password", login_attempt_count=1)
        client.bloks_two_step_verification_verify_code.assert_not_called()

    def test_login_by_sessionid_falls_back_to_private_stream_before_public(self):
        client = Client()
        sessionid = "1234567890123456789012345678901%3Atoken"
        client.user_info_v1 = Mock(side_effect=PrivateError("boom"))
        client.user_stream_by_id_flat = Mock(return_value={"pk": "1234567890123456789", "username": "example"})
        client.user_short_gql = Mock(
            side_effect=AssertionError("sessionid login should use private fallback before public")
        )

        result = client.login_by_sessionid(sessionid)

        self.assertTrue(result)
        client.user_info_v1.assert_called_once_with(1234567890123456789012345678901)
        client.user_stream_by_id_flat.assert_called_once_with("1234567890123456789012345678901")
        client.user_short_gql.assert_not_called()
        self.assertEqual(client.username, "example")
        self.assertEqual(client.authorization_data["sessionid"], sessionid)
        self.assertEqual(client.cookie_dict["ds_user_id"], "1234567890123456789")

    def test_login_by_sessionid_falls_back_to_public_after_private_stream_failure(self):
        client = Client()
        sessionid = "1234567890123456789012345678901%3Atoken"
        client.user_info_v1 = Mock(side_effect=PrivateError("boom"))
        client.user_stream_by_id_flat = Mock(side_effect=PrivateError("stream failed"))
        client.user_short_gql = Mock(return_value=UserShort(pk="1234567890123456789", username="example"))

        result = client.login_by_sessionid(sessionid)

        self.assertTrue(result)
        client.user_info_v1.assert_called_once_with(1234567890123456789012345678901)
        client.user_stream_by_id_flat.assert_called_once_with("1234567890123456789012345678901")
        client.user_short_gql.assert_called_once_with(1234567890123456789012345678901)
        self.assertEqual(client.username, "example")

    def test_login_by_sessionid_uses_user_info_v1_when_available(self):
        client = Client()
        sessionid = "1234567890123456789012345678901%3Atoken"
        user = User(
            pk="1234567890123456789",
            username="example",
            full_name="Example",
            is_private=False,
            profile_pic_url="https://example.com/pic.jpg",
            is_verified=False,
            media_count=0,
            follower_count=0,
            following_count=0,
            is_business=False,
        )
        client.user_info_v1 = Mock(return_value=user)
        client.user_short_gql = Mock()

        result = client.login_by_sessionid(sessionid)

        self.assertTrue(result)
        client.user_info_v1.assert_called_once_with(1234567890123456789012345678901)
        client.user_short_gql.assert_not_called()
        self.assertEqual(client.username, "example")
        self.assertEqual(client.cookie_dict["ds_user_id"], "1234567890123456789")

    def test_login_by_sessionid_primes_authorization_header_for_direct_uploads(self):
        client = Client()
        sessionid = "1234567890123456789012345678901%3Atoken"
        user = User(
            pk="1234567890123456789",
            username="example",
            full_name="Example",
            is_private=False,
            profile_pic_url="https://example.com/pic.jpg",
            is_verified=False,
            media_count=0,
            follower_count=0,
            following_count=0,
            is_business=False,
        )
        client.user_info_v1 = Mock(return_value=user)
        client.user_short_gql = Mock()

        result = client.login_by_sessionid(sessionid)

        self.assertTrue(result)
        self.assertEqual(client.private.headers.get("IG-U-DS-USER-ID"), "1234567890123456789")
        self.assertEqual(client.private.headers.get("IG-INTENDED-USER-ID"), "1234567890123456789")
        self.assertEqual(client.private.headers.get("Authorization"), client.authorization)

    def test_login_by_sessionid_falls_back_to_private_stream_on_validation_error(self):
        client = Client()
        sessionid = "1234567890123456789012345678901%3Atoken"
        client.user_info_v1 = Mock(side_effect=ValidationError.from_exception_data("User", []))
        client.user_stream_by_id_flat = Mock(return_value={"pk_id": "1234567890123456789", "username": "example"})
        client.user_short_gql = Mock(
            side_effect=AssertionError("sessionid login should use private fallback before public")
        )

        result = client.login_by_sessionid(sessionid)

        self.assertTrue(result)
        client.user_info_v1.assert_called_once_with(1234567890123456789012345678901)
        client.user_stream_by_id_flat.assert_called_once_with("1234567890123456789012345678901")
        client.user_short_gql.assert_not_called()
        self.assertEqual(client.username, "example")

    def test_login_by_sessionid_rejects_invalid_sessionid(self):
        client = Client()

        with self.assertRaises(AssertionError):
            client.login_by_sessionid("short")

    def test_login_by_sessionid_rejects_sessionid_without_numeric_prefix(self):
        client = Client()

        with self.assertRaises(AssertionError):
            client.login_by_sessionid("abcdefghijklmnopqrstuvwxyz123456")

    def test_login_resets_relogin_attempt_after_success(self):
        client = Client()
        client.username = "example"
        client.password = "password"
        client.authorization_data = {}
        client.relogin_attempt = 1
        client.last_response = Mock(headers={"ig-set-authorization": "Bearer token"})
        client.parse_authorization = Mock(return_value={"sessionid": "abc"})
        client.pre_login_flow = Mock(return_value=True)
        client.private_request = Mock(return_value=True)
        client.login_flow = Mock()
        client.password_encrypt = Mock(return_value="enc-password")

        result = client.login(relogin=True)

        self.assertTrue(result)
        self.assertEqual(client.relogin_attempt, 0)

    def test_user_stories_authenticated_falls_back_to_private(self):
        client = Client()
        client.authorization_data = {"ds_user_id": "123"}
        expected = [Mock(spec=Story)]

        with mock.patch.object(
            client,
            "user_stories_gql",
            side_effect=ClientGraphqlError("Incorrect Query"),
        ):
            with mock.patch.object(client, "user_stories_v1", return_value=expected) as private_fallback:
                result = client.user_stories("4776134209", amount=5)

        private_fallback.assert_called_once_with("4776134209", 5)
        self.assertEqual(result, expected)

    def test_init_does_not_leave_blank_authorization_header(self):
        client = Client()
        client.set_settings({})
        client.private.headers["Authorization"] = "Bearer stale"

        client.init()

        self.assertNotIn("Authorization", client.private.headers)

    def test_init_clears_stale_private_cookies_when_settings_have_no_cookies(self):
        client = Client()
        client.private.cookies.set("sessionid", "stale-session")
        client.private.cookies.set("ds_user_id", "12345")
        client.set_settings({})

        self.assertEqual(client.private.cookies.get_dict(), {})
        self.assertIsNone(client.sessionid)
        self.assertIsNone(client.user_id)

    def test_init_clears_stale_ig_u_rur_header_when_settings_have_no_value(self):
        client = Client()
        client.private.headers["IG-U-RUR"] = "stale-rur"
        client.set_settings({})

        self.assertNotIn("IG-U-RUR", client.private.headers)

    def test_sessionid_falls_back_to_authorization_data(self):
        client = Client()
        client.private.cookies.clear()
        client.authorization_data = {"sessionid": "auth-session"}

        self.assertEqual(client.sessionid, "auth-session")

    def test_user_id_falls_back_to_authorization_data(self):
        client = Client()
        client.private.cookies.clear()
        client.authorization_data = {"ds_user_id": "12345"}

        self.assertEqual(client.user_id, 12345)

    def test_inject_sessionid_to_public_uses_authorization_fallback(self):
        client = Client()
        client.private.cookies.clear()
        client.authorization_data = {"sessionid": "auth-session"}

        result = client.inject_sessionid_to_public()

        self.assertTrue(result)
        self.assertEqual(client.public.cookies.get("sessionid"), "auth-session")

    def test_inject_sessionid_to_public_returns_false_without_sessionid(self):
        client = Client()

        result = client.inject_sessionid_to_public()

        self.assertFalse(result)
        self.assertIsNone(client.public.cookies.get("sessionid"))

    def test_logout_clears_local_session_state_after_success(self):
        client = Client()
        client.authorization_data = {"sessionid": "auth-session", "ds_user_id": "12345"}
        client.last_login = 123.0
        client.relogin_attempt = 1
        client.private.headers["Authorization"] = "Bearer stale"
        client.private.cookies.set("sessionid", "private-session")
        client.public.cookies.set("sessionid", "public-session")
        client.private_request = Mock(return_value={"status": "ok"})

        result = client.logout()

        self.assertTrue(result)
        self.assertEqual(client.authorization_data, {})
        self.assertIsNone(client.last_login)
        self.assertEqual(client.relogin_attempt, 0)
        self.assertNotIn("Authorization", client.private.headers)
        self.assertEqual(client.private.cookies.get_dict(), {})
        self.assertEqual(client.public.cookies.get_dict(), {})

    def test_parse_authorization_returns_empty_dict_for_missing_header(self):
        client = Client()
        client.logger = Mock()

        result = client.parse_authorization(None)

        self.assertEqual(result, {})
        client.logger.exception.assert_not_called()

    def test_parse_authorization_decodes_valid_bearer_header(self):
        client = Client()
        authorization = "Bearer IGT:2:eyJzZXNzaW9uaWQiOiAiYWJjIiwgImRzX3VzZXJfaWQiOiAiMTIzIn0="

        result = client.parse_authorization(authorization)

        self.assertEqual(result, {"sessionid": "abc", "ds_user_id": "123"})
