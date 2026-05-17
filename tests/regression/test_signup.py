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
