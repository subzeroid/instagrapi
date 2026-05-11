from instagrapi.exceptions import ClientJSONDecodeError
from instagrapi.mixins.private import JSONDecodeError as PrivateJSONDecodeError
from instagrapi.mixins.public import JSONDecodeError as PublicJSONDecodeError
from tests.helpers import *


def _html_response(body: str, json_error):
    response = Mock()
    response.headers = {"Content-Length": "0"}
    response.raw.tell.return_value = 0
    response.status_code = 200
    response.url = "https://www.instagram.com/api/test/"
    response.text = body
    response.raise_for_status.return_value = None
    response.json.side_effect = json_error
    return response


class RequestLoggingRegressionTestCase(unittest.TestCase):
    def test_public_json_decode_error_log_truncates_response_body(self):
        client = Client()
        client.request_timeout = 0
        client.last_response_ts = 0
        client.public_request_logger = Mock()
        long_body = "<html>" + ("A" * 5000) + "</html>"
        response = _html_response(long_body, PublicJSONDecodeError("bad", "x", 0))

        with mock.patch.object(client.public, "get", return_value=response):
            with self.assertRaises(ClientJSONDecodeError):
                client._send_public_request("https://www.instagram.com/api/test/", return_json=True)

        logged_body = client.public_request_logger.error.call_args.args[3]
        self.assertLessEqual(len(logged_body), 600)
        self.assertTrue(logged_body.startswith("<html>"))
        self.assertIn("truncated", logged_body)
        self.assertNotEqual(logged_body, long_body)

    def test_private_json_decode_error_log_truncates_response_body(self):
        client = Client()
        client.request_timeout = 0
        client.last_response_ts = 0
        client.authorization_data = {"ds_user_id": "1"}
        client.logger = Mock()
        client.request_log = Mock()
        long_body = "<html>" + ("A" * 5000) + "</html>"
        response = _html_response(long_body, PrivateJSONDecodeError("bad", "x", 0))

        with mock.patch.object(client.private, "get", return_value=response):
            with self.assertRaises(ClientJSONDecodeError):
                client._send_private_request("test/")

        logged_body = client.logger.error.call_args.args[4]
        self.assertLessEqual(len(logged_body), 600)
        self.assertTrue(logged_body.startswith("<html>"))
        self.assertIn("truncated", logged_body)
        self.assertNotEqual(logged_body, long_body)
