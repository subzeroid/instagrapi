from tests.helpers import *


class AccountRegressionTestCase(unittest.TestCase):
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
