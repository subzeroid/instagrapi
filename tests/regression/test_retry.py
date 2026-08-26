import json
import socket
import threading
import unittest
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

import requests
from requests.exceptions import RetryError

from instagrapi import Client
from instagrapi.exceptions import (
    ClientConnectionError,
    ClientError,
    ClientThrottledError,
    PleaseWaitFewMinutes,
)
from instagrapi.mixins import private as private_mixin
from instagrapi.mixins import public as public_mixin
from tests.helpers import is_retryable_http_status_error


@contextmanager
def status_server(status_code, payload=None):
    body = json.dumps(payload or {"message": "rate limited", "status": "fail"}).encode()

    class Handler(BaseHTTPRequestHandler):
        hits = 0

        def do_GET(self):
            type(self).hits += 1
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Retry-After", "0")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/retry", Handler
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def response_with_json(status_code, payload, url):
    response = requests.Response()
    response.status_code = status_code
    response.url = url
    response.headers["Content-Type"] = "application/json"
    response._content = json.dumps(payload).encode()
    response.request = requests.Request("GET", url).prepare()
    return response


def retry_client(total=2):
    client = Client(
        request_timeout=0,
        public_request_retries_timeout=0,
        session_retry_total=total,
        session_retry_backoff_factor=0,
    )
    client.delay_range = None
    client.last_response_ts = 0
    client.public.trust_env = False
    client.private.trust_env = False
    return client


class RetryRegressionTestCase(unittest.TestCase):
    def test_retry_strategies_return_final_status_response(self):
        client = retry_client(total=2)
        client.session_retry_backoff_factor = 0.25
        client.session_retry_statuses = [429, 503]

        for strategy in (
            client._build_private_session_retry_strategy(),
            client._build_public_session_retry_strategy(),
        ):
            with self.subTest(strategy=strategy):
                self.assertFalse(strategy.raise_on_status)
                self.assertEqual(strategy.total, 2)
                self.assertEqual(strategy.backoff_factor, 0.25)
                self.assertEqual(strategy.status_forcelist, [429, 503])
                self.assertEqual(strategy.allowed_methods, ["GET", "POST"])

    def test_legacy_retry_fallback_returns_final_status_response(self):
        client = retry_client(total=2)

        for module, builder_name in (
            (private_mixin, "_build_private_session_retry_strategy"),
            (public_mixin, "_build_public_session_retry_strategy"),
        ):
            calls = []

            def legacy_retry(**kwargs):
                calls.append(kwargs)
                if "allowed_methods" in kwargs:
                    raise TypeError("legacy urllib3")
                return kwargs

            with self.subTest(module=module.__name__):
                with mock.patch.object(module, "Retry", side_effect=legacy_retry):
                    strategy = getattr(client, builder_name)()

                self.assertFalse(strategy.get("raise_on_status", True))
                self.assertEqual(strategy["method_whitelist"], ["GET", "POST"])
                self.assertEqual(len(calls), 2)

    def test_private_session_returns_final_429_after_configured_attempts(self):
        client = retry_client(total=2)

        with status_server(429) as (url, handler):
            response = client.private.get(url, timeout=1)

        self.assertEqual(response.status_code, 429)
        self.assertEqual(handler.hits, 3)

    def test_public_request_maps_final_429_after_configured_attempts(self):
        client = retry_client(total=2)

        with status_server(429) as (url, handler):
            with self.assertRaises(ClientThrottledError) as raised:
                client._send_public_request(url, return_json=True, timeout=1)

        self.assertEqual(raised.exception.response.status_code, 429)
        self.assertEqual(handler.hits, 3)

    def test_public_request_does_not_repeat_adapter_exhausted_429(self):
        client = retry_client(total=2)

        with status_server(429) as (url, handler):
            with self.assertRaises(ClientThrottledError):
                client.public_request(url, retries_count=2, retries_timeout=0)

        self.assertEqual(handler.hits, 3)

    def test_public_request_retains_outer_retries_when_transport_retries_are_disabled(self):
        for total in (0, -1):
            with self.subTest(total=total):
                client = retry_client(total=total)

                with status_server(429) as (url, handler):
                    with self.assertRaises(ClientThrottledError):
                        client.public_request(url, retries_count=2, retries_timeout=0)

                self.assertEqual(handler.hits, 2)

    def test_public_request_retains_outer_retries_for_curl_transport(self):
        client = retry_client(total=2)
        client.public_transport = "curl"
        response = response_with_json(
            429,
            {"message": "rate limited", "status": "fail"},
            "https://www.instagram.com/test/",
        )
        error = ClientThrottledError(response=response)

        with mock.patch.object(client, "_send_public_request", side_effect=error) as send:
            with self.assertRaises(ClientThrottledError):
                client.public_request("https://www.instagram.com/test/", retries_count=2, retries_timeout=0)

        self.assertEqual(send.call_count, 2)

    def test_public_request_does_not_repeat_adapter_exhausted_503(self):
        client = retry_client(total=2)

        with status_server(503) as (url, handler):
            with self.assertRaises(ClientError) as raised:
                client.public_request(url, retries_count=2, retries_timeout=0)

        self.assertEqual(raised.exception.response.status_code, 503)
        self.assertEqual(handler.hits, 3)

    def test_public_request_retries_status_not_handled_by_adapter(self):
        client = retry_client(total=2)

        with status_server(418) as (url, handler):
            with self.assertRaises(ClientError) as raised:
                client.public_request(url, retries_count=2, retries_timeout=0)

        self.assertEqual(raised.exception.response.status_code, 418)
        self.assertEqual(handler.hits, 2)

    def test_public_request_retries_response_less_connection_error(self):
        client = retry_client(total=2)
        error = ClientConnectionError("connection exhausted")

        with mock.patch.object(client, "_send_public_request", side_effect=error) as send:
            with self.assertRaises(ClientConnectionError):
                client.public_request("https://www.instagram.com/test/", retries_count=2, retries_timeout=0)

        self.assertEqual(send.call_count, 2)

    def test_public_stream_maps_final_429_before_returning(self):
        client = retry_client(total=2)

        with status_server(429) as (url, handler):
            with self.assertRaises(ClientThrottledError) as raised:
                client._send_public_request(url, stream=True, timeout=1)

        self.assertTrue(raised.exception.response.raw.closed)
        self.assertEqual(handler.hits, 3)

    def test_public_stream_returns_open_success_response(self):
        client = retry_client(total=0)

        with status_server(200, {"status": "ok"}) as (url, _handler):
            response = client._send_public_request(url, stream=True, timeout=1)
            try:
                self.assertEqual(response.status_code, 200)
                self.assertFalse(response._content)
            finally:
                response.close()

    def test_private_final_429_maps_to_client_throttled_error(self):
        client = retry_client(total=0)
        response = response_with_json(
            429,
            {"message": "rate limited", "status": "fail"},
            "https://i.instagram.com/api/v1/test/",
        )

        with mock.patch.object(client.private, "get", return_value=response):
            with self.assertRaises(ClientThrottledError) as raised:
                client._send_private_request("test/")

        self.assertIs(raised.exception.response, response)

    def test_private_final_429_with_wait_message_maps_to_please_wait(self):
        client = retry_client(total=0)
        response = response_with_json(
            429,
            {"message": "Please wait a few minutes before you try again.", "status": "fail"},
            "https://i.instagram.com/api/v1/test/",
        )

        with mock.patch.object(client.private, "get", return_value=response):
            with self.assertRaises(PleaseWaitFewMinutes) as raised:
                client._send_private_request("test/")

        self.assertIs(raised.exception.response, response)

    def test_public_connection_exhaustion_remains_client_connection_error(self):
        client = retry_client(total=0)
        probe = socket.socket()
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
        probe.close()

        with self.assertRaises(ClientConnectionError):
            client._send_public_request(f"http://127.0.0.1:{port}/", timeout=0.2)

    def test_retryable_http_status_error_accepts_typed_status_and_legacy_retry_error(self):
        response = response_with_json(
            500,
            {"status": "fail"},
            "https://i.instagram.com/api/v1/media/configure_to_igtv/",
        )
        typed_error = ClientError(response=response)
        legacy_error = RetryError("configure_to_igtv: too many 500 error responses")

        self.assertTrue(is_retryable_http_status_error(typed_error, {500}, "configure_to_igtv"))
        self.assertTrue(is_retryable_http_status_error(legacy_error, {500}, "configure_to_igtv"))

    def test_retryable_http_status_error_rejects_wrong_status_or_endpoint(self):
        cases = (
            (400, "https://i.instagram.com/api/v1/media/configure_to_igtv/"),
            (500, "https://i.instagram.com/api/v1/media/configure/"),
        )

        for status_code, url in cases:
            with self.subTest(status_code=status_code, url=url):
                response = response_with_json(status_code, {"status": "fail"}, url)
                error = ClientError(response=response)

                self.assertFalse(is_retryable_http_status_error(error, {500}, "configure_to_igtv"))
