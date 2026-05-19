from instagrapi.mixins.challenge import ChallengeChoice
from tests.helpers import *


class PasswordEncryptionRegressionTestCase(unittest.TestCase):
    def test_password_enrypt(self):
        cl = Client()
        enc_password = cl.password_encrypt("test")
        parts = enc_password.split(":")
        self.assertEqual(parts[0], "#PWD_INSTAGRAM")
        self.assertEqual(parts[1], "4")
        self.assertTrue(int(parts[2]) > 1607612345)
        self.assertTrue(len(parts[3]) == 392)


class SignupHelperRegressionTestCase(unittest.TestCase):
    def test_check_username_posts_uuid_payload(self):
        client = Client()
        client.uuid = "uuid"
        with mock.patch.object(client, "private_request", return_value={"available": True}) as private_request:
            result = client.check_username("example")

        self.assertEqual(result, {"available": True})
        private_request.assert_called_once_with(
            "users/check_username/",
            data={"username": "example", "_uuid": "uuid"},
        )

    def test_check_phone_number_posts_signup_payload(self):
        client = Client()
        client.phone_id = "phone-id"
        client.uuid = "uuid"
        client.android_device_id = "android-id"
        with mock.patch.object(client, "private_request", return_value={"valid": True}) as private_request:
            result = client.check_phone_number("+15551234567")

        self.assertEqual(result, {"valid": True})
        private_request.assert_called_once_with(
            "accounts/check_phone_number/",
            data={
                "phone_id": "phone-id",
                "login_nonce_map": "{}",
                "phone_number": "+15551234567",
                "guid": "uuid",
                "device_id": "android-id",
                "prefill_shown": "False",
            },
        )

    def test_challenge_api_rejects_external_api_path(self):
        client = Client()
        client.uuid = "uuid"
        client.android_device_id = "android-id"
        client.private.get = mock.Mock()

        for api_path in ("@attacker.example/steal", "//attacker.example/steal"):
            with self.subTest(api_path=api_path):
                with self.assertRaises(ClientError):
                    client.challenge_api(
                        {
                            "api_path": api_path,
                            "challenge_context": "{}",
                        }
                    )

        client.private.get.assert_not_called()

    def test_challenge_captcha_rejects_external_api_path_before_solver(self):
        client = Client()
        client.captcha_resolve = mock.Mock(side_effect=AssertionError("solver should not be called"))
        client.private.post = mock.Mock()

        with self.assertRaises(ClientError):
            client.challenge_captcha(
                {
                    "api_path": "@attacker.example/steal",
                    "fields": {"sitekey": "site-key"},
                    "challengeType": "RecaptchaChallengeForm",
                }
            )

        client.captcha_resolve.assert_not_called()
        client.private.post.assert_not_called()

    def test_challenge_submit_phone_number_rejects_external_forward_path(self):
        client = Client()
        client.private.post = mock.Mock(json=mock.Mock(return_value={"status": "ok"}))

        with self.assertRaises(ClientError):
            client.challenge_submit_phone_number(
                {
                    "navigation": {"forward": "@attacker.example/steal"},
                    "challenge_context": "{}",
                },
                "+15551234567",
            )

        client.private.post.assert_not_called()

    def test_challenge_verify_sms_captcha_rejects_external_forward_path(self):
        client = Client()
        client.private.post = mock.Mock(json=mock.Mock(return_value={"status": "ok"}))

        with self.assertRaises(ClientError):
            client.challenge_verify_sms_captcha(
                {
                    "navigation": {"forward": "@attacker.example/steal"},
                    "challenge_context": "{}",
                },
                "123456",
            )

        client.private.post.assert_not_called()

    def test_challenge_flow_submits_phone_number_then_sms_code(self):
        client = Client()
        start = {"api_path": "/challenge/start", "challenge_context": "{}"}
        submit_phone_step = {
            "challengeType": "SubmitPhoneNumberForm",
            "navigation": {"forward": "/challenge/phone"},
            "challenge_context": "{}",
        }
        verify_sms_step = {
            "challengeType": "VerifySMSCodeFormForSMSCaptcha",
            "navigation": {"forward": "/challenge/sms"},
            "challenge_context": "{}",
        }

        with mock.patch.object(client, "challenge_api", return_value=submit_phone_step):
            with mock.patch.object(
                client,
                "challenge_submit_phone_number",
                return_value=verify_sms_step,
            ) as submit_phone:
                with mock.patch.object(
                    client,
                    "challenge_verify_sms_captcha",
                    return_value={"status": "ok"},
                ) as verify_sms:
                    with mock.patch.object(client, "challenge_code_handler", return_value="123456") as code_handler:
                        result = client.challenge_flow(
                            start,
                            phone_number="+15551234567",
                            username="example",
                            wait_seconds=0,
                        )

        self.assertTrue(result)
        submit_phone.assert_called_once_with(submit_phone_step, "+15551234567")
        code_handler.assert_called_once()
        self.assertEqual(code_handler.call_args.args[0], "example")
        self.assertEqual(code_handler.call_args.args[1], ChallengeChoice.SMS)
        verify_sms.assert_called_once_with(verify_sms_step, "123456")

    def test_challenge_flow_requires_phone_number_for_sms_challenge(self):
        client = Client()
        start = {"api_path": "/challenge/start", "challenge_context": "{}"}
        submit_phone_step = {
            "challengeType": "SubmitPhoneNumberForm",
            "navigation": {"forward": "/challenge/phone"},
            "challenge_context": "{}",
        }

        with mock.patch.object(client, "challenge_api", return_value=submit_phone_step):
            with self.assertRaises(ClientError) as ctx:
                client.challenge_flow(start, username="example", wait_seconds=0)

        self.assertIn("phone_number is required", str(ctx.exception))

    def test_challenge_flow_requires_sms_code(self):
        client = Client()
        start = {"api_path": "/challenge/start", "challenge_context": "{}"}
        verify_sms_step = {
            "challengeType": "VerifySMSCodeFormForSMSCaptcha",
            "navigation": {"forward": "/challenge/sms"},
            "challenge_context": "{}",
        }

        with mock.patch.object(client, "challenge_api", return_value=verify_sms_step):
            with mock.patch.object(client, "challenge_code_handler", return_value=False):
                with self.assertRaises(ChallengeRequired) as ctx:
                    client.challenge_flow(
                        start,
                        phone_number="+15551234567",
                        username="example",
                        wait_seconds=0,
                        attempts=1,
                    )

        self.assertIn("SMS code required", str(ctx.exception))

    def test_signup_passes_phone_number_to_challenge_flow(self):
        client = Client()
        client.wait_seconds = 0
        challenge = {"api_path": "/challenge/start", "challenge_context": "{}"}

        with mock.patch.object(client, "get_signup_config", return_value={}):
            with mock.patch.object(client, "check_email", return_value={"valid": True, "available": True}):
                with mock.patch.object(client, "send_verify_email", return_value={"email_sent": True}):
                    with mock.patch.object(client, "challenge_code_handler", return_value="654321"):
                        with mock.patch.object(
                            client,
                            "check_confirmation_code",
                            return_value={"signup_code": "signup-code"},
                        ):
                            with mock.patch.object(
                                client,
                                "accounts_create",
                                side_effect=[
                                    {"message": "challenge_required", "challenge": challenge},
                                    {"created_user": {"pk": "1", "username": "example"}},
                                ],
                            ):
                                with mock.patch.object(client, "challenge_flow", return_value=True) as challenge_flow:
                                    with mock.patch(
                                        "instagrapi.mixins.signup.extract_user_short",
                                        return_value="created-user",
                                    ):
                                        result = client.signup(
                                            "example",
                                            "password",
                                            "example@example.com",
                                            "+15551234567",
                                        )

        self.assertEqual(result, "created-user")
        challenge_flow.assert_called_once_with(
            challenge,
            phone_number="+15551234567",
            username="example",
        )
