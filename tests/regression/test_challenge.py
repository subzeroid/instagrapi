from instagrapi.mixins.challenge import ChallengeChoice
from tests.helpers import *


class ChallengeRegressionTestCase(unittest.TestCase):
    def test_challenge_required_legacy_challenge_message_explains_handlers(self):
        error = ChallengeRequired(
            message="challenge_required",
            challenge={"api_path": "/challenge/12345/nonce-code/"},
            status="fail",
        )

        self.assertEqual(error.raw_message, "challenge_required")
        self.assertIn("legacy challenge flow", str(error))
        self.assertIn("challenge_code_handler", str(error))
        self.assertIn("saved client settings", str(error))

    def test_challenge_required_auth_platform_message_explains_manual_flow(self):
        error = ChallengeRequired(
            message="challenge_required",
            challenge={"api_path": "/auth_platform/?apc=test-token"},
            status="fail",
        )

        self.assertIn("auth platform flow", str(error))
        self.assertIn("official Instagram app or web", str(error))
        self.assertIn("not supported automatically", str(error))

    def test_challenge_required_bloks_redirect_message_explains_acknowledgement(self):
        error = ChallengeRequired(
            message="challenge_required",
            step_name="STEP_NAME",
            bloks_action="com.bloks.www.ig.challenge.redirect.async",
            challenge_context="opaque-context",
            challenge_type_enum_str="SUSPICIOUS_LOGIN",
            status="ok",
        )

        self.assertIn("Bloks redirect checkpoint", str(error))
        self.assertIn("challenge_bloks_redirect_dismiss()", str(error))
        self.assertIn("trusted device", str(error))

    def test_challenge_required_unknown_step_message_names_step(self):
        error = ChallengeRequired(
            message="challenge_required",
            step_name="verify_email",
            status="ok",
        )

        self.assertIn("challenge step `verify_email`", str(error))
        self.assertIn("challenge_code_handler", str(error))

    def test_challenge_required_preserves_explicit_message(self):
        error = ChallengeRequired(
            "Challenge code required.",
            message="challenge_required",
            status="fail",
        )

        self.assertEqual(str(error), "Challenge code required.")
        self.assertEqual(error.raw_message, "challenge_required")

    def test_auth_platform_challenge_raises_clear_manual_verification_error(self):
        client = Client()
        last_json = {
            "message": "challenge_required",
            "challenge": {"api_path": "/auth_platform/?apc=test-token"},
            "status": "fail",
        }

        with self.assertRaises(ChallengeRequired) as cm:
            client.challenge_resolve(last_json)

        self.assertIn("Manual verification required", str(cm.exception))

    def test_challenge_resolve_simple_fails_fast_when_handler_has_no_code(self):
        client = Client()
        client.username = "example"
        client.last_json = {
            "message": "challenge_required",
            "status": "fail",
            "step_name": "verify_email",
            "step_data": {"email": "e***@example.com"},
        }
        client.challenge_code_handler = lambda *args, **kwargs: False

        with mock.patch("instagrapi.mixins.challenge.time.sleep") as sleep:
            with self.assertRaises(ChallengeRequired) as cm:
                client.challenge_resolve_simple("challenge/test/")

        self.assertIn("Challenge code required", str(cm.exception))
        sleep.assert_not_called()

    def test_change_password_step_does_not_leak_password_to_stdout_or_logs(self):
        """CodeQL py/clear-text-logging-sensitive-data — the previous
        implementation printed the new password to stdout. Verify
        neither print(...) nor logger.info(...) carries the password."""
        client = Client()
        client.last_json = {
            "message": "challenge_required",
            "status": "ok",
            "step_name": "change_password",
            "challenge_context": "{}",
        }
        secret = "Sup3rS3cret-Pass@2026!"
        client.change_password_handler = lambda username: secret

        printed = []
        with mock.patch("builtins.print", side_effect=printed.append):
            with mock.patch.object(client, "bloks_change_password", return_value=True):
                with self.assertLogs(client.logger.name, level="INFO") as log_ctx:
                    result = client.challenge_resolve_simple("/dummy/")

        self.assertTrue(result)
        # Password must not leak to stdout via print(...).
        for line in printed:
            self.assertNotIn(secret, str(line))
        # Or to logs via self.logger.info(...).
        for record in log_ctx.records:
            self.assertNotIn(secret, record.getMessage())

    def test_challenge_resolve_simple_ufac_www_bloks_raises_clear_manual_error(self):
        client = Client()
        client.username = "example"
        client.last_json = {
            "message": "challenge_required",
            "status": "ok",
            "step_name": "ufac_www_bloks",
            "step_data": {"screen_data": '{"screen_output_payload":{}}'},
            "challenge_context": "dummy",
            "challenge_type_enum_str": "UFAC_WWW_BLOKS",
        }

        with self.assertRaises(ChallengeRequired) as cm:
            client.challenge_resolve_simple("challenge/test/")

        self.assertIn("UFAC web bloks checkpoint", str(cm.exception))

    def test_challenge_resolve_simple_delta_acknowledge_approved_posts_ack_choice(self):
        client = Client()
        client.username = "example"
        client.last_json = {
            "step_name": "delta_acknowledge_approved",
            "flow_render_type": 3,
            "bloks_action": "com.instagram.challenge.navigation.take_challenge",
            "challenge_context": ('{"step_name":"delta_acknowledge_approved","challenge_type_enum":"GENERIC_PHISHED"}'),
            "challenge_type_enum_str": "GENERIC_PHISHED",
            "status": "ok",
        }
        client._send_private_request = Mock()

        result = client.challenge_resolve_simple("/challenge/test/")

        self.assertTrue(result)
        client._send_private_request.assert_called_once_with("/challenge/test/", {"choice": "0"})

    def test_challenge_resolve_simple_bloks_redirect_step_acknowledges_context(self):
        client = Client()
        client.username = "example"
        client.last_json = {
            "message": "challenge_required",
            "status": "ok",
            "step_name": "STEP_NAME",
            "flow_render_type": 3,
            "bloks_action": "com.bloks.www.ig.challenge.redirect.async",
            "challenge_context": "opaque-context",
            "challenge_type_enum_str": "SUSPICIOUS_LOGIN",
        }
        client.bloks_challenge_take_challenge = Mock(return_value={"status": "ok", "action": "close"})

        result = client.challenge_resolve_simple("challenge/test/")

        self.assertTrue(result)
        client.bloks_challenge_take_challenge.assert_called_once_with(
            challenge_context="opaque-context",
            choice=0,
        )

    def test_challenge_resolve_simple_bloks_redirect_password_reset_uses_handler(self):
        client = Client()
        client.username = "example"
        client.last_json = {
            "message": "challenge_required",
            "status": "ok",
            "step_name": "STEP_NAME",
            "flow_render_type": 3,
            "bloks_action": "com.bloks.www.ig.challenge.redirect.async",
            "challenge_context": "opaque-context",
            "challenge_type_enum_str": "PASSWORD_RESET",
        }
        client.change_password_handler = Mock(return_value="new-password")

        with mock.patch.object(client, "bloks_change_password", return_value=True) as change_password:
            result = client.challenge_resolve_simple("challenge/test/")

        self.assertTrue(result)
        change_password.assert_called_once_with("new-password", "opaque-context")

    def test_challenge_bloks_redirect_dismiss_posts_pending_context(self):
        client = Client()
        client.username = "example"
        client.last_json = {
            "message": "challenge_required",
            "status": "ok",
            "step_name": "STEP_NAME",
            "flow_render_type": 3,
            "bloks_action": "com.bloks.www.ig.challenge.redirect.async",
            "challenge_context": "opaque-context",
            "challenge_type_enum_str": "SUSPICIOUS_LOGIN",
        }
        client.bloks_challenge_take_challenge = Mock(return_value={"status": "ok", "action": "close"})

        result = client.challenge_bloks_redirect_dismiss()

        self.assertTrue(result)
        client.bloks_challenge_take_challenge.assert_called_once_with(
            challenge_context="opaque-context",
        )

    def test_challenge_bloks_redirect_dismiss_requires_pending_context(self):
        client = Client()
        client.last_json = {}

        with self.assertRaises(ChallengeRequired) as cm:
            client.challenge_bloks_redirect_dismiss()

        self.assertIn("No pending Bloks redirect challenge", str(cm.exception))

    def test_challenge_bloks_redirect_dismiss_raises_when_checkpoint_still_pending(self):
        client = Client()
        client.last_json = {
            "message": "challenge_required",
            "status": "ok",
            "step_name": "STEP_NAME",
            "bloks_action": "com.bloks.www.ig.challenge.redirect.async",
            "challenge_context": "opaque-context",
        }
        client.bloks_challenge_take_challenge = Mock(
            return_value={
                "status": "ok",
                "step_name": "STEP_NAME",
                "bloks_action": "com.bloks.www.ig.challenge.redirect.async",
                "challenge_context": "opaque-context",
            }
        )

        with self.assertRaises(ChallengeRequired) as cm:
            client.challenge_bloks_redirect_dismiss()

        self.assertIn("Bloks redirect checkpoint", str(cm.exception))

    def test_challenge_resolve_uses_default_context_when_missing(self):
        client = Client()
        client.uuid = "uuid-1"
        client.android_device_id = "android-1"
        last_json = {
            "message": "challenge_required",
            "challenge": {"api_path": "/challenge/12345/nonce-code/"},
            "status": "fail",
        }

        with mock.patch.object(client, "_send_private_request") as send_request:
            with mock.patch.object(client, "challenge_resolve_simple", return_value=True) as resolve_simple:
                result = client.challenge_resolve(last_json)

        self.assertTrue(result)
        send_request.assert_called_once()
        self.assertEqual(send_request.call_args.args[0], "challenge/12345/nonce-code/")
        self.assertEqual(
            send_request.call_args.kwargs["params"]["challenge_context"],
            '{"step_name": "", "nonce_code": "nonce-code", "user_id": 12345, "is_stateless": false}',
        )
        resolve_simple.assert_called_once_with("/challenge/12345/nonce-code/")

    def test_challenge_resolve_normalizes_prefixed_api_challenge_path(self):
        client = Client()
        client.uuid = "uuid-1"
        client.android_device_id = "android-1"
        last_json = {
            "message": "challenge_required",
            "challenge": {"api_path": "/api/challenge/12345/nonce-code/"},
            "status": "fail",
        }

        with mock.patch.object(client, "_send_private_request") as send_request:
            with mock.patch.object(client, "challenge_resolve_simple", return_value=True) as resolve_simple:
                result = client.challenge_resolve(last_json)

        self.assertTrue(result)
        self.assertEqual(send_request.call_args.args[0], "challenge/12345/nonce-code/")
        resolve_simple.assert_called_once_with("/challenge/12345/nonce-code/")

    def test_challenge_resolve_normalizes_prefixed_api_v1_challenge_path(self):
        client = Client()
        client.uuid = "uuid-1"
        client.android_device_id = "android-1"
        last_json = {
            "message": "challenge_required",
            "challenge": {"api_path": "/api/v1/challenge/12345/nonce-code/"},
            "status": "fail",
        }

        with mock.patch.object(client, "_send_private_request") as send_request:
            with mock.patch.object(client, "challenge_resolve_simple", return_value=True) as resolve_simple:
                result = client.challenge_resolve(last_json)

        self.assertTrue(result)
        self.assertEqual(send_request.call_args.args[0], "challenge/12345/nonce-code/")
        resolve_simple.assert_called_once_with("/challenge/12345/nonce-code/")

    def test_challenge_resolve_falls_back_to_contact_form(self):
        client = Client()
        client.last_json = {"message": "challenge_required", "status": "fail"}
        last_json = {
            "message": "challenge_required",
            "challenge": {"api_path": "/challenge/test/"},
            "status": "fail",
        }

        with mock.patch.object(client, "_send_private_request", side_effect=ChallengeRequired):
            with mock.patch.object(client, "challenge_resolve_contact_form", return_value=True) as contact_form:
                result = client.challenge_resolve(last_json)

        self.assertTrue(result)
        contact_form.assert_called_once_with("/challenge/test/")

    def test_challenge_resolve_contact_form_posts_numeric_email_choice(self):
        client = Client()
        client.user_agent = "Instagram Test"
        fake_session = Mock()
        fake_session.cookies = requests.cookies.cookiejar_from_dict({"csrftoken": "token"})
        fake_session.get.return_value = Mock()
        fake_session.post.return_value = Mock(json=Mock(return_value={}))

        with mock.patch("instagrapi.mixins.challenge.requests.Session", return_value=fake_session):
            with mock.patch("instagrapi.mixins.challenge.time.sleep"):
                with mock.patch.object(
                    client,
                    "handle_challenge_result",
                    side_effect=ChallengeRedirection(),
                ):
                    result = client.challenge_resolve_contact_form("/challenge/test/")

        self.assertTrue(result)
        self.assertEqual(
            fake_session.post.call_args_list[0].args[1]["choice"],
            1,
        )

    def test_challenge_resolve_contact_form_posts_numeric_sms_choice_on_fallback(self):
        client = Client()
        client.user_agent = "Instagram Test"
        fake_session = Mock()
        fake_session.cookies = requests.cookies.cookiejar_from_dict({"csrftoken": "token"})
        fake_session.get.return_value = Mock()
        fake_session.post.side_effect = [
            Mock(json=Mock(return_value={})),
            Mock(json=Mock(return_value={})),
        ]

        with mock.patch("instagrapi.mixins.challenge.requests.Session", return_value=fake_session):
            with mock.patch("instagrapi.mixins.challenge.time.sleep"):
                with mock.patch.object(
                    client,
                    "handle_challenge_result",
                    side_effect=[
                        SelectContactPointRecoveryForm("Need SMS", challenge={}),
                        ChallengeRedirection(),
                    ],
                ):
                    result = client.challenge_resolve_contact_form("/challenge/test/")

        self.assertTrue(result)
        self.assertEqual(fake_session.post.call_args_list[0].args[1]["choice"], 1)
        self.assertEqual(fake_session.post.call_args_list[1].args[1]["choice"], 0)

    def test_handle_challenge_result_raises_recaptcha_form(self):
        client = Client()
        challenge = {
            "challengeType": "RecaptchaChallengeForm",
            "errors": ["Captcha failed"],
        }

        with self.assertRaises(RecaptchaChallengeForm) as cm:
            client.handle_challenge_result(challenge)

        self.assertIn("Captcha failed", str(cm.exception))

    def test_handle_challenge_result_raises_select_contact_point_recovery_form(self):
        client = Client()
        challenge = {
            "challengeType": "SelectContactPointRecoveryForm",
            "errors": ["Need recovery"],
            "extraData": {"content": [{"title": "Help us confirm you own this account"}]},
        }

        with self.assertRaises(SelectContactPointRecoveryForm) as cm:
            client.handle_challenge_result(challenge)

        self.assertIn("Need recovery", str(cm.exception))

    def test_handle_challenge_result_raises_submit_phone_number_form(self):
        client = Client()
        challenge = {
            "challengeType": "SubmitPhoneNumberForm",
            "fields": {"phone_number": "None"},
        }

        with self.assertRaises(SubmitPhoneNumberForm):
            client.handle_challenge_result(challenge)

    def test_handle_challenge_result_allows_sms_captcha_verification_form(self):
        client = Client()
        challenge = {"challenge": {"challengeType": "VerifySMSCodeFormForSMSCaptcha"}}

        result = client.handle_challenge_result(challenge)

        self.assertEqual(result["challengeType"], "VerifySMSCodeFormForSMSCaptcha")

    def test_handle_challenge_result_rejects_malformed_nested_payload(self):
        client = Client()

        with self.assertRaises(ChallengeError) as cm:
            client.handle_challenge_result({"challenge": "broken"})

        self.assertIn("Malformed nested challenge payload", str(cm.exception))

    def test_handle_challenge_result_unknown_type_includes_context(self):
        client = Client()
        challenge = {
            "challengeType": "SomeNewChallengeForm",
            "errors": ["Need manual action"],
            "extraData": {"content": [{"text": "Open Instagram to continue"}]},
        }

        with self.assertRaises(ChallengeError) as cm:
            client.handle_challenge_result(challenge)

        self.assertIn("Unsupported challenge type: SomeNewChallengeForm", str(cm.exception))
        self.assertIn("Need manual action", str(cm.exception))

    def test_challenge_resolve_simple_select_verify_method_uses_sms_choice_for_code(
        self,
    ):
        client = Client()
        client.last_json = {
            "step_name": "select_verify_method",
            "step_data": {"phone_number": "+1 *** *** 1234"},
            "action": "close",
            "status": "ok",
        }
        client._send_private_request = Mock()
        client.challenge_code_or_raised = Mock(return_value="123456")

        result = client.challenge_resolve_simple("/challenge/test/")

        self.assertTrue(result)
        self.assertEqual(client._send_private_request.call_args_list[0].args[1]["choice"], "0")
        self.assertEqual(client.challenge_code_or_raised.call_args.args[0].name, "SMS")
        self.assertEqual(client.challenge_code_or_raised.call_args.kwargs["wait_seconds"], 5)
        self.assertEqual(client.challenge_code_or_raised.call_args.kwargs["attempts"], 24)

    def test_challenge_resolve_simple_select_contact_point_recovery_uses_sms_choice_for_code(
        self,
    ):
        client = Client()
        client.last_json = {
            "step_name": "select_contact_point_recovery",
            "step_data": {"phone_number": "+1 *** *** 1234"},
            "action": "close",
            "status": "ok",
        }
        client._send_private_request = Mock(
            side_effect=[
                None,
                None,
            ]
        )
        client.challenge_code_or_raised = Mock(return_value="123456")

        result = client.challenge_resolve_simple("/challenge/test/")

        self.assertTrue(result)
        self.assertEqual(client._send_private_request.call_args_list[0].args[1]["choice"], "0")
        self.assertEqual(client.challenge_code_or_raised.call_args.args[0].name, "SMS")

    def test_challenge_resolve_simple_unknown_step_raises_clear_error(self):
        client = Client()
        client.username = "example"
        client.last_json = {
            "step_name": "mystery_step",
            "status": "ok",
        }

        with self.assertRaises(ChallengeUnknownStep) as cm:
            client.challenge_resolve_simple("/challenge/test/")

        self.assertIn('Unknown step_name "mystery_step"', str(cm.exception))

    def test_challenge_resolve_simple_change_password_requires_handler_output(self):
        client = Client()
        client.username = "example"
        client.last_json = {
            "step_name": "change_password",
            "challenge_context": '{"step_name":"change_password"}',
            "status": "ok",
        }
        client.change_password_handler = Mock(return_value="")

        with mock.patch("instagrapi.mixins.challenge.time.sleep"):
            with self.assertRaises(ChallengeRequired) as cm:
                client.challenge_resolve_simple("/challenge/test/")

        self.assertIn("Password change required", str(cm.exception))

    def test_challenge_resolve_simple_recovery_final_step_has_clear_error(self):
        client = Client()
        client.last_json = {
            "step_name": "select_contact_point_recovery",
            "step_data": {"phone_number": "+1 *** *** 1234"},
            "status": "ok",
        }

        def fake_send_private_request(*args, **kwargs):
            if "security_code" in (args[1] if len(args) > 1 else {}):
                client.last_json = {"step_name": "unexpected_step", "status": "ok"}

        client._send_private_request = Mock(side_effect=fake_send_private_request)
        client.challenge_code_or_raised = Mock(return_value="123456")

        with self.assertRaises(ChallengeError) as cm:
            client.challenge_resolve_simple("/challenge/test/")

        self.assertIn("Unexpected final challenge step", str(cm.exception))

    def test_challenge_resolve_simple_submit_phone_posts_number_then_sms_code(self):
        client = Client()
        client.username = "example"
        client.phone_number = "+15551234567"
        client.last_json = {
            "step_name": "submit_phone",
            "step_data": {"phone_number": "+1 *** *** 4567"},
            "challenge_context": "{}",
            "status": "ok",
        }

        def fake_send_private_request(endpoint, data):
            if "phone_number" in data:
                client.last_json = {
                    "step_name": "verify_phone",
                    "step_data": {"phone_number": "+1 *** *** 4567"},
                    "challenge_context": "{}",
                    "status": "ok",
                }
            elif "security_code" in data:
                client.last_json = {"action": "close", "status": "ok"}

        client._send_private_request = Mock(side_effect=fake_send_private_request)
        client.challenge_code_or_raised = Mock(return_value="123456")

        result = client.challenge_resolve_simple("/challenge/test/")

        self.assertTrue(result)
        self.assertEqual(
            client._send_private_request.call_args_list[0].args,
            ("/challenge/test/", {"phone_number": "+15551234567"}),
        )
        client.challenge_code_or_raised.assert_called_once_with(
            ChallengeChoice.SMS,
            wait_seconds=5,
            attempts=24,
        )
        self.assertEqual(
            client._send_private_request.call_args_list[1].args,
            ("/challenge/test/", {"security_code": "123456"}),
        )

    def test_challenge_resolve_simple_submit_phone_requires_configured_phone_number(self):
        client = Client()
        client.username = "example"
        client.phone_number = None
        client.last_json = {
            "step_name": "submit_phone",
            "step_data": {"phone_number": "+1 *** *** 4567"},
            "challenge_context": "{}",
            "status": "ok",
        }

        with self.assertRaises(ChallengeRequired) as cm:
            client.challenge_resolve_simple("/challenge/test/")

        self.assertIn("Phone number required", str(cm.exception))

    def test_challenge_resolve_contact_form_raises_clear_error_for_unexpected_verify_step(
        self,
    ):
        client = Client()
        client.user_agent = "Instagram Test"
        fake_session = Mock()
        fake_session.cookies = requests.cookies.cookiejar_from_dict({"csrftoken": "token"})
        fake_session.get.return_value = Mock()
        fake_session.post.return_value = Mock(json=Mock(return_value={}))

        with mock.patch("instagrapi.mixins.challenge.requests.Session", return_value=fake_session):
            with mock.patch("instagrapi.mixins.challenge.time.sleep"):
                with mock.patch.object(
                    client,
                    "handle_challenge_result",
                    return_value={"challengeType": "UnexpectedForm"},
                ):
                    with self.assertRaises(ChallengeError) as cm:
                        client.challenge_resolve_contact_form("/challenge/test/")

        self.assertIn("Unexpected contact-form challenge step", str(cm.exception))

    def test_challenge_resolve_contact_form_raises_clear_error_for_detail_mismatch(
        self,
    ):
        client = Client()
        client.user_agent = "Instagram Test"
        client.username = "expected-user"
        fake_session = Mock()
        fake_session.cookies = requests.cookies.cookiejar_from_dict({"csrftoken": "token"})
        fake_session.get.return_value = Mock()
        fake_session.post.side_effect = [
            Mock(json=Mock(return_value={})),
            Mock(
                json=Mock(
                    return_value={
                        "challengeType": "ReviewContactPointChangeForm",
                        "extraData": {"content": []},
                        "navigation": {"forward": "/challenge/forward/"},
                    }
                )
            ),
        ]

        with mock.patch("instagrapi.mixins.challenge.requests.Session", return_value=fake_session):
            with mock.patch("instagrapi.mixins.challenge.time.sleep"):
                with mock.patch.object(
                    client,
                    "handle_challenge_result",
                    return_value={"challengeType": "VerifySMSCodeFormForSMSCaptcha"},
                ):
                    with mock.patch.object(client, "challenge_code_handler", return_value="123456"):
                        with self.assertRaises(ChallengeError) as cm:
                            client.challenge_resolve_contact_form("/challenge/test/")

        self.assertIn("Data invalid", str(cm.exception))

    def test_challenge_resolve_contact_form_raises_clear_error_for_bad_final_response(
        self,
    ):
        client = Client()
        client.user_agent = "Instagram Test"
        fake_session = Mock()
        fake_session.cookies = requests.cookies.cookiejar_from_dict({"csrftoken": "token"})
        fake_session.get.return_value = Mock()
        fake_session.post.side_effect = [
            Mock(json=Mock(return_value={})),
            Mock(
                json=Mock(
                    return_value={
                        "challengeType": "ReviewContactPointChangeForm",
                        "extraData": {"content": []},
                        "navigation": {"forward": "/challenge/forward/"},
                    }
                )
            ),
            Mock(json=Mock(return_value={"type": "NOPE", "status": "fail"})),
        ]

        with mock.patch("instagrapi.mixins.challenge.requests.Session", return_value=fake_session):
            with mock.patch("instagrapi.mixins.challenge.time.sleep"):
                with mock.patch.object(
                    client,
                    "handle_challenge_result",
                    return_value={"challengeType": "VerifySMSCodeFormForSMSCaptcha"},
                ):
                    with mock.patch.object(client, "challenge_code_handler", return_value="123456"):
                        with self.assertRaises(ChallengeError) as cm:
                            client.challenge_resolve_contact_form("/challenge/test/")

        self.assertIn("Unexpected final response after contact-form approval", str(cm.exception))
