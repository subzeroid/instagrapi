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

    def test_account_convert_to_professional_posts_conversion_payload(self):
        client = Client()
        account = object()

        with mock.patch.object(client, "with_default_data", side_effect=lambda data: {"default": "yes", **data}):
            with mock.patch.object(client, "private_request", return_value={"status": "ok"}) as private_request:
                with mock.patch.object(client, "account_info", return_value=account) as account_info:
                    result = client.account_convert_to_professional(
                        to_account_type=3,
                        category_id=2347428775505624,
                        should_show_category=True,
                        should_show_public_contacts=False,
                        entry_point="setting",
                        extra_data={"custom": "value"},
                    )

        self.assertIs(result, account)
        private_request.assert_called_once_with(
            "business/account/convert_account/",
            data={
                "default": "yes",
                "entry_point": "setting",
                "creator_destination_migration": "false",
                "to_account_type": "3",
                "category_id": "2347428775505624",
                "should_show_category": "1",
                "should_show_public_contacts": "0",
                "custom": "value",
            },
        )
        account_info.assert_called_once_with()

    def test_account_convert_to_business_uses_business_account_type(self):
        client = Client()

        with mock.patch.object(client, "account_convert_to_professional", return_value="account") as convert:
            result = client.account_convert_to_business(category_id="123", should_show_public_contacts=True)

        self.assertEqual(result, "account")
        convert.assert_called_once_with(
            to_account_type=2,
            category_id="123",
            should_show_category=True,
            should_show_public_contacts=True,
        )

    def test_account_convert_to_creator_uses_creator_account_type(self):
        client = Client()

        with mock.patch.object(client, "account_convert_to_professional", return_value="account") as convert:
            result = client.account_convert_to_creator(category_id="456", should_show_category=False)

        self.assertEqual(result, "account")
        convert.assert_called_once_with(
            to_account_type=3,
            category_id="456",
            should_show_category=False,
            should_show_public_contacts=False,
        )

    def test_account_convert_to_professional_rejects_personal_account_type(self):
        client = Client()

        with self.assertRaises(ValueError):
            client.account_convert_to_professional(to_account_type=1)

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
