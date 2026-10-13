import io
import json
import unittest
from unittest.mock import Mock, patch
from urllib.parse import parse_qs

import requests
from requests.adapters import BaseAdapter

from instagrapi import Client
from instagrapi.exceptions import ChallengeRequired

CHALLENGE = {
    "status": "fail",
    "message": "challenge_required",
    "challenge": {"api_path": "/challenge/12345/nonce/", "challenge_context": "synthetic-context"},
}
CODE_STEP = {"status": "ok", "step_name": "verify_email", "challenge_context": "synthetic-code-context"}
# Server step metadata only; no replacement password is present.
RESET_STEP = {"status": "ok", "step_name": "change_password", "challenge_context": "synthetic-password-context"}
CLOSED = {"status": "ok", "action": "close"}
OK = {"status": "ok", "result": "original-request"}


def submitted_code(request):
    body = request.content if hasattr(request, "content") else request.body
    if isinstance(body, bytes):
        body = body.decode()
    form = parse_qs(body)
    return json.loads(form["signed_body"][0].split(".", 1)[1])["security_code"]


class ChallengeTransport(BaseAdapter):
    def __init__(self, replies):
        self.replies = iter(replies)
        self.requests = []

    def send(self, request, **kwargs):
        self.requests.append(request)
        status_code, payload = next(self.replies)
        response = requests.Response()
        response.status_code = status_code
        response._content = json.dumps(payload).encode()
        response.url = request.url
        response.request = request
        return response

    def close(self):
        pass


class ChallengePolicyRegressionTestCase(unittest.TestCase):
    def make_client(self, replies, **kwargs):
        client = Client(private_transport="requests", request_timeout=0, **kwargs)
        client.request_log = Mock()
        transport = ChallengeTransport(replies)
        client.private.mount("https://", transport)
        self.addCleanup(client.private.close)
        self.addCleanup(client.public.close)
        return client, transport.requests

    def test_default_policy_is_compatible(self):
        client, _ = self.make_client([])
        self.assertIs(client.with_challenge_flow, True)

    def test_disabled_policy_stops_before_resolver_input_or_replay(self):
        shapes = [
            CHALLENGE,
            {**CHALLENGE, "challenge": {"api_path": "/challenge/opaque/nonce/", "native_flow": True}},
            {**CHALLENGE, "challenge": {"api_path": "/auth_platform/?apc=synthetic"}},
        ]
        for payload in shapes:
            for data in (None, {"action": "synthetic"}):
                with self.subTest(challenge=payload["challenge"], post=bool(data)):
                    client, sent = self.make_client([(400, payload)], with_challenge_flow=False)
                    with patch("builtins.input") as read, self.assertRaises(ChallengeRequired) as cm:
                        client.private_request("feed/timeline/", data=data, login=True)
                    read.assert_not_called()
                    self.assertEqual(len(sent), 1)
                    self.assertEqual(sent[0].method, "POST" if data else "GET")
                    self.assertEqual(client.last_json, payload)
                    self.assertEqual(cm.exception.challenge, payload["challenge"])
                    self.assertEqual(client.last_response.status_code, 400)

    def test_runtime_policy_toggle_preserves_original_exception(self):
        client, sent = self.make_client([])
        client.with_challenge_flow = False
        original = ChallengeRequired(message="challenge_required", challenge=CHALLENGE["challenge"])
        client._send_private_request = Mock(side_effect=original)
        with self.assertRaises(ChallengeRequired) as cm:
            client.private_request("feed/timeline/", login=True)
        self.assertIs(cm.exception, original)
        client._send_private_request.assert_called_once()
        self.assertEqual(sent, [])

    def test_automatic_resolution_keeps_manual_code_and_successful_replay(self):
        client, sent = self.make_client([(400, CHALLENGE), (200, CODE_STEP), (200, CLOSED), (200, OK)])
        with patch("builtins.input", side_effect=["invalid", " 012345 "]) as read:
            result = client.private_request("feed/timeline/", login=True)
        self.assertEqual(result, OK)
        self.assertEqual(read.call_count, 2)
        self.assertEqual([r.method for r in sent], ["GET", "GET", "POST", "GET"])
        self.assertEqual(submitted_code(sent[2]), "012345")
        self.assertEqual(sent[0].url, sent[-1].url)

    def test_code_eof_is_actionable_challenge_without_submission_or_replay(self):
        client, sent = self.make_client([(400, CHALLENGE), (200, CODE_STEP)])
        with patch("builtins.input", side_effect=EOFError("synthetic EOF")), self.assertRaises(ChallengeRequired) as cm:
            client.private_request("feed/timeline/", login=True)
        self.assertIn("challenge_code_handler", str(cm.exception))
        self.assertIsInstance(cm.exception.__cause__, EOFError)
        self.assertEqual(cm.exception.step_name, "verify_email")
        self.assertEqual(cm.exception.challenge_context, CODE_STEP["challenge_context"])
        self.assertEqual(client.last_json, CODE_STEP)
        self.assertEqual([r.method for r in sent], ["GET", "GET"])

    def test_password_eof_is_actionable_challenge_without_submission_or_replay(self):
        client, sent = self.make_client([(400, CHALLENGE), (200, RESET_STEP)])
        with patch("builtins.input", side_effect=EOFError("synthetic EOF")), self.assertRaises(ChallengeRequired) as cm:
            client.private_request("feed/timeline/", login=True)
        self.assertIn("change_password_handler", str(cm.exception))
        self.assertIsInstance(cm.exception.__cause__, EOFError)
        self.assertEqual(cm.exception.step_name, "change_password")
        self.assertEqual(cm.exception.challenge_context, RESET_STEP["challenge_context"])
        self.assertEqual(client.last_json, RESET_STEP)
        self.assertEqual([r.method for r in sent], ["GET", "GET"])

    def test_code_handler_accepts_non_tty_input(self):
        client, _ = self.make_client([])
        stream = io.StringIO("invalid\n 012345 \n")
        self.assertFalse(stream.isatty())
        with patch("sys.stdin", stream), patch("sys.stdout", io.StringIO()):
            code = client.challenge_code_handler("synthetic")
        self.assertEqual(code, "012345")

    def test_password_handler_accepts_non_tty_input(self):
        client, _ = self.make_client([])
        with patch("sys.stdin", io.StringIO("\n synthetic-password \n")), patch("sys.stdout", io.StringIO()):
            password = client.change_password_handler("synthetic")
        self.assertEqual(password, "synthetic-password")

    def test_eof_error_preserves_payload_without_overwriting_hint(self):
        client, _ = self.make_client([])
        client.last_json = CHALLENGE.copy()
        with patch("builtins.input", side_effect=EOFError), self.assertRaises(ChallengeRequired) as cm:
            client.challenge_code_handler("synthetic")
        self.assertIn("challenge_code_handler", str(cm.exception))
        self.assertEqual(cm.exception.challenge, CHALLENGE["challenge"])
        self.assertEqual(client.last_json, CHALLENGE)

    def test_custom_code_handler_keeps_its_contract(self):
        client, sent = self.make_client([(400, CHALLENGE), (200, CODE_STEP), (200, CLOSED), (200, OK)])
        handler = Mock(return_value="012345")
        client.challenge_code_handler = handler
        with patch("builtins.input") as read:
            result = client.private_request("feed/timeline/", login=True)
        self.assertEqual(result, OK)
        read.assert_not_called()
        self.assertEqual(handler.call_count, 1)
        self.assertEqual(submitted_code(sent[2]), "012345")

    def test_custom_password_handler_keeps_its_contract(self):
        client, _ = self.make_client([])
        client.last_json = RESET_STEP.copy()
        client.change_password_handler = Mock(return_value="synthetic-password")
        client.bloks_change_password = Mock(return_value=True)
        with patch("builtins.input") as read:
            result = client.challenge_resolve_simple("/challenge/12345/nonce/")
        self.assertTrue(result)
        read.assert_not_called()
        client.change_password_handler.assert_called_once_with(client.username)
        client.bloks_change_password.assert_called_once_with("synthetic-password", RESET_STEP["challenge_context"])

    def test_custom_handler_errors_are_not_rewritten(self):
        for step, name in ((CODE_STEP, "challenge_code_handler"), (RESET_STEP, "change_password_handler")):
            with self.subTest(handler=name):
                client, sent = self.make_client([(400, CHALLENGE), (200, step)])
                original = EOFError("custom handler error")
                setattr(client, name, Mock(side_effect=original))
                with self.assertRaises(EOFError) as cm:
                    client.private_request("feed/timeline/", login=True)
                self.assertIs(cm.exception, original)
                self.assertEqual(len(sent), 2)

    def test_raising_generic_hook_has_priority_over_automatic_resolution(self):
        for policy in (False, True):
            with self.subTest(policy=policy):
                client, sent = self.make_client([(400, CHALLENGE)], with_challenge_flow=policy)
                errors = []

                def stop(c, error):
                    self.assertIs(c, client)
                    errors.append(error)
                    raise error

                client.handle_exception = stop
                with self.assertRaises(ChallengeRequired) as cm:
                    client.private_request("feed/timeline/", login=True)
                self.assertIs(cm.exception, errors[0])
                self.assertEqual(len(sent), 1)

    def test_returning_generic_hook_preserves_existing_replay_contract(self):
        client, sent = self.make_client([(400, CHALLENGE), (200, OK)], with_challenge_flow=False)
        client.handle_exception = Mock(return_value=None)
        result = client.private_request("feed/timeline/", login=True)
        self.assertEqual(result, OK)
        client.handle_exception.assert_called_once()
        self.assertEqual(len(sent), 2)
        self.assertEqual(sent[0].url, sent[1].url)
