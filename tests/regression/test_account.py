from tests.helpers import *


class AccountRegressionTestCase(unittest.TestCase):
    def test_send_password_reset_posts_recovery_payload(self):
        client = Client()

        with mock.patch.object(client, "public_request", return_value={"status": "ok"}) as public_request:
            result = client.send_password_reset("user@example.com")

        self.assertEqual(result, {"status": "ok"})
        public_request.assert_called_once()
        args, kwargs = public_request.call_args
        self.assertEqual(args, ("https://www.instagram.com/accounts/account_recovery_send_ajax/",))
        self.assertEqual(
            kwargs["data"],
            {
                "email_or_username": "user@example.com",
                "recaptcha_challenge_field": "",
            },
        )
        self.assertEqual(kwargs["headers"]["x-requested-with"], "XMLHttpRequest")
        self.assertIn("x-csrftoken", kwargs["headers"])
        self.assertTrue(kwargs["return_json"])
        self.assertFalse(kwargs["update_headers"])

    def test_send_password_reset_accepts_recaptcha_challenge_field(self):
        client = Client()

        with mock.patch.object(client, "public_request", return_value={"status": "ok"}) as public_request:
            client.send_password_reset("user@example.com", recaptcha_challenge_field="challenge")

        self.assertEqual(public_request.call_args.kwargs["data"]["recaptcha_challenge_field"], "challenge")

    def test_reset_password_delegates_to_send_password_reset(self):
        client = Client()

        with mock.patch.object(client, "send_password_reset", return_value={"status": "ok"}) as send_password_reset:
            result = client.reset_password("username")

        self.assertEqual(result, {"status": "ok"})
        send_password_reset.assert_called_once_with("username")

    def test_confirm_email_posts_verify_email_code_payload(self):
        client = Client()
        client.phone_id = "phone-id"
        client.authorization_data = {"ds_user_id": "123"}
        client.uuid = "uuid"
        client.android_device_id = "android-id"

        with mock.patch.object(client, "private_request", return_value={"status": "ok"}) as private_request:
            result = client.confirm_email("addr@example.com", "123456")

        self.assertEqual(result, {"status": "ok"})
        private_request.assert_called_once_with(
            "accounts/verify_email_code/",
            {
                "_uuid": "uuid",
                "device_id": "android-id",
                "phone_id": "phone-id",
                "_uid": "123",
                "guid": "uuid",
                "email": "addr@example.com",
                "code": "123456",
            },
        )
