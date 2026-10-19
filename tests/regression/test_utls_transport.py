# protects: Prepared requests, native session lifecycle and per-call deadline budgets survive the uTLS bridge.
# fails_when: Native response failures leak pools, queued requests transmit late, or request policy crosses calls.
# why_new: Existing curl/Requests coverage cannot exercise the separate C ABI lifetime and serialization contract.
# seam: none
import base64
import ctypes
import json
import threading
import time
from io import BytesIO
from unittest.mock import Mock

import pytest
import requests

from instagrapi import Client
from instagrapi.utls import create_utls_h2_adapter
from instagrapi.utls_native import load_library


def response(status=200, body=b'{"status":"ok"}', **changes):
    return {
        "id": "fixture-response",
        "status": status,
        "usedProtocol": "HTTP/2.0",
        "headers": {"Content-Type": ["application/json"]},
        "body": "data:application/json;base64," + base64.b64encode(body).decode(),
        **changes,
    }


@pytest.fixture
def native(monkeypatch):
    replies, payloads, buffers = [], [], []

    def request(data):
        payloads.append(json.loads(data))
        buffer = ctypes.create_string_buffer(json.dumps(replies.pop(0)).encode())
        buffers.append(buffer)
        return ctypes.addressof(buffer)

    def destroy(data):
        buffer = ctypes.create_string_buffer(b'{"id":"destroy","success":true}')
        buffers.append(buffer)
        return ctypes.addressof(buffer)

    library = Mock(request=Mock(side_effect=request), destroySession=Mock(side_effect=destroy))
    monkeypatch.setattr("instagrapi.utls.load_library", lambda path: library)
    return library, replies, payloads


@pytest.fixture
def session(native):
    session = requests.Session()
    session.trust_env = False
    session.mount("https://", create_utls_h2_adapter("fixture-native"))
    yield session
    session.close()


def test_client_keeps_one_pool_when_settings_and_retry_policy_are_restored(native):
    client = Client(private_transport="utls", utls_library_path="fixture-native")
    adapter = client.private.get_adapter("https://i.instagram.com/")
    client.private.cookies.set("sessionid", "fixture-cookie")
    settings = client.get_settings()
    client.set_settings(settings)
    client.set_retry_config(private_transport="utls", session_retry_total=0)
    assert client.private.get_adapter("https://i.instagram.com/") is adapter
    assert client.private.cookies.get("sessionid") == "fixture-cookie"
    assert settings["private_transport"] == "utls"
    native[0].destroySession.assert_not_called()
    for session in (client.private, client.public, client.graphql):
        session.close()


def test_headers_cookies_binary_body_and_status_remain_owned_by_requests(session, native):
    library, replies, payloads = native
    replies.extend(
        [
            response(
                headers={
                    "Content-Type": ["application/json"],
                    "Content-Encoding": ["gzip"],
                    "Content-Length": ["100"],
                    "Set-Cookie": ["a=alpha; Path=/; Secure", "b=beta; Path=/; Secure"],
                }
            ),
            response(status=429, body=b"", headers={"Retry-After": ["7"]}),
        ]
    )
    first = session.get("https://i.instagram.com/first", timeout=2)
    assert first.json() == {"status": "ok"}
    assert "Content-Encoding" not in first.headers and "Content-Length" not in first.headers
    assert first.raw.headers.getlist("Set-Cookie") == ["a=alpha; Path=/; Secure", "b=beta; Path=/; Secure"]
    second = session.post("https://i.instagram.com/second?escaped=%2F", data=BytesIO(b"binary\x00body"), timeout=2)
    assert second.status_code == 429 and second.content == b"" and second.headers["Retry-After"] == "7"
    assert len(payloads) == 2
    assert payloads[0]["sessionId"] == payloads[1]["sessionId"]
    assert payloads[1]["requestUrl"].endswith("?escaped=%2F")
    assert base64.b64decode(payloads[1]["requestBody"]) == b"binary\x00body"
    assert set(payloads[1]["headers"]["Cookie"].split("; ")) == {"a=alpha", "b=beta"}
    assert payloads[1]["withoutCookieJar"] is True and payloads[1]["followRedirects"] is False
    library.freeMemory.assert_called()


@pytest.mark.parametrize(
    "changed", [{"timeout": 0.1}, {"verify": False}, {"proxies": {"https": "http://proxy.example:80"}}]
)
def test_per_request_policy_changes_rebuild_native_pool(session, native, changed):
    library, replies, payloads = native
    replies.extend([response(), response()])
    session.get("https://i.instagram.com/", timeout=2)
    session.get("https://i.instagram.com/", **{"timeout": 2, **changed})
    assert payloads[0]["sessionId"] != payloads[1]["sessionId"]
    library.destroySession.assert_called_once()


@pytest.mark.parametrize(
    "detail,error",
    [
        ("failed to do request: x509: certificate signed by unknown authority", requests.exceptions.SSLError),
        ("failed to do request: context deadline exceeded", requests.Timeout),
        ("failed to do request: unexpected EOF secret-fixture", requests.ConnectionError),
        ("failed to build client out of request input: invalid configuration", requests.ConnectionError),
    ],
)
def test_errors_are_classified_without_retry_or_provider_text(session, native, detail, error):
    library, replies, payloads = native
    replies.append({"id": "fixture-response", "status": 0, "body": detail})
    with pytest.raises(error) as caught:
        session.post("https://i.instagram.com/", data="synthetic-password", timeout=2)
    assert "secret-fixture" not in str(caught.value)
    assert len(payloads) == 1
    session.close()
    assert library.destroySession.call_count == int(detail.startswith("failed to do request:"))


def test_http1_response_is_rejected_without_fallback(session, native):
    native[1].append(response(usedProtocol="HTTP/1.1"))
    with pytest.raises(requests.ConnectionError, match="HTTP/2"):
        session.post("https://i.instagram.com/", data="synthetic-password", timeout=2)
    assert len(native[2]) == 1


@pytest.mark.parametrize("detail", ["unexpected EOF", "gzip: invalid header", "context deadline exceeded"])
def test_first_response_body_failure_still_destroys_the_constructed_native_session(session, native, detail):
    library, replies, payloads = native
    replies.append({"id": "fixture-response", "status": 0, "body": detail})
    with pytest.raises((requests.ConnectionError, requests.Timeout)):
        session.post("https://fixture.invalid/", data="synthetic-body", timeout=2)
    session.close()
    assert len(payloads) == 1
    library.destroySession.assert_called_once()


@pytest.mark.parametrize("status", [None, 600])
def test_invalid_native_http_status_still_destroys_the_constructed_session(session, native, status):
    native[1].append(response(status=status))
    with pytest.raises(requests.ConnectionError, match="invalid HTTP status"):
        session.get("https://fixture.invalid/", timeout=2)
    session.close()
    native[0].destroySession.assert_called_once()


def test_expired_session_queue_deadline_does_not_transmit_a_request(session, native):
    library, replies, payloads = native
    adapter = session.get_adapter("https://fixture.invalid/")
    adapter.client.lock.acquire()
    release = threading.Timer(0.25, adapter.client.lock.release)
    release.start()
    replies.append(response())
    started = time.monotonic()
    try:
        with pytest.raises(requests.Timeout):
            session.post("https://fixture.invalid/", data="synthetic-body", timeout=0.05)
        assert time.monotonic() - started < 0.2
        assert payloads == []
        library.request.assert_not_called()
    finally:
        release.join(1)


def test_time_spent_waiting_for_session_is_subtracted_from_native_budget(session, native):
    adapter = session.get_adapter("https://fixture.invalid/")
    adapter.client.lock.acquire()
    release = threading.Timer(0.1, adapter.client.lock.release)
    release.start()
    native[1].append(response())
    try:
        assert session.get("https://fixture.invalid/", timeout=1).status_code == 200
        assert 1 <= native[2][0]["timeoutMilliseconds"] <= 950
    finally:
        release.join(1)


def test_policy_change_after_first_body_failure_destroys_each_native_pool_once(session, native):
    library, replies, payloads = native
    replies.extend([{"id": "fixture-response", "status": 0, "body": "unexpected EOF"}, response()])
    with pytest.raises(requests.ConnectionError):
        session.get("https://fixture.invalid/", timeout=2)
    assert session.get("https://fixture.invalid/", timeout=1).status_code == 200
    assert payloads[0]["sessionId"] != payloads[1]["sessionId"]
    library.destroySession.assert_called_once()
    session.close()
    assert library.destroySession.call_count == 2


@pytest.mark.parametrize(
    "arguments",
    [
        {"verify": "custom-ca.pem"},
        {"cert": "client.pem"},
        {"timeout": (1, 2)},
        {"timeout": 0},
        {"timeout": float("inf")},
    ],
)
def test_unsupported_policy_is_rejected_before_credentials_are_sent(session, native, arguments):
    with pytest.raises(ValueError):
        session.post("https://i.instagram.com/", data="synthetic-password", **arguments)
    assert native[2] == []


def test_missing_or_unverified_library_fails_before_native_load(tmp_path, monkeypatch):
    loader = Mock()
    monkeypatch.setattr("instagrapi.utls_native.ctypes.CDLL", loader)
    with pytest.raises(RuntimeError, match="utls_library_path"):
        load_library(None)
    path = tmp_path / "unverified-library"
    path.write_bytes(b"fixture-not-native-code")
    with pytest.raises(RuntimeError, match="verified"):
        load_library(path)
    loader.assert_not_called()


def test_body_preparation_consumes_deadline_before_native_transmission(session, native):
    class SlowBody:
        def read(self):
            time.sleep(0.08)
            return b"synthetic-body"

    with pytest.raises(requests.Timeout):
        session.post("https://fixture.invalid/", data=SlowBody(), timeout=0.02)
    assert native[2] == []
