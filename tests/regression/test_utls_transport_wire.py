"""Exercise the pinned native transport on loopback, without Instagram traffic."""

import base64
import os
import socket
import ssl
from contextlib import ExitStack
from io import BytesIO

import pytest
import requests

pytest.importorskip("h2")
pytest.importorskip("cryptography")

from h2.events import RemoteSettingsChanged, WindowUpdated

from instagrapi import Client
from instagrapi.exceptions import ClientConnectionError, ClientThrottledError
from tests import http2_server
from tests.http2_server import LAB_HOST, LAB_JSON, LoopbackProxy, LoopbackServer
from tests.socks5_proxy import LoopbackSocksProxy


@pytest.fixture
def library_path():
    path = os.environ.get("INSTAGRAPI_UTLS_TEST_LIBRARY")
    if not path:
        pytest.skip("Install the native library and set INSTAGRAPI_UTLS_TEST_LIBRARY to run wire tests")
    return path


@pytest.fixture
def lab(tmp_path):
    server = LoopbackServer(tmp_path).start()
    server.server.tls.minimum_version = ssl.TLSVersion.TLSv1_3
    server.server.tls.maximum_version = ssl.TLSVersion.TLSv1_3
    try:
        yield server
    finally:
        server.close()


@pytest.fixture
def client(lab, library_path):
    # Only the local generated certificate bypasses verification. Other tests
    # explicitly prove that verify=True still rejects that certificate.
    client = Client(private_transport="utls", utls_library_path=library_path, tls_verify=False, request_timeout=0)
    client.private.trust_env = False
    try:
        yield client
    finally:
        for session in (client.private, client.public, client.graphql):
            session.close()


def url(lab, path="/lab/ok"):
    return f"https://{LAB_HOST}:{lab.port}{path}"


def test_actual_clienthello_and_http2_profile(client, lab, monkeypatch):
    hellos, settings, windows = [], [], []
    original_hello = http2_server.peek_client_hello
    original_receive = http2_server.H2Connection.receive_data

    def capture_hello(sock):
        header = sock.recv(5, socket.MSG_PEEK | socket.MSG_WAITALL)
        record = sock.recv(5 + int.from_bytes(header[3:5], "big"), socket.MSG_PEEK | socket.MSG_WAITALL)
        hello = record[9:]
        offset = 35 + hello[34]
        size = int.from_bytes(hello[offset : offset + 2], "big")
        ciphers = hello[offset + 2 : offset + 2 + size]
        offset += 2 + size
        offset += 1 + hello[offset]
        offset += 2
        extensions = {}
        while offset < len(hello):
            kind = int.from_bytes(hello[offset : offset + 2], "big")
            size = int.from_bytes(hello[offset + 2 : offset + 4], "big")
            extensions[kind] = hello[offset + 4 : offset + 4 + size]
            offset += 4 + size

        def pairs(value):
            return [int.from_bytes(value[i : i + 2], "big") for i in range(0, len(value), 2)]

        hellos.append((pairs(hello[:2]), pairs(ciphers), extensions))
        return original_hello(sock)

    def capture_settings(connection, data):
        events = original_receive(connection, data)
        for event in events:
            if isinstance(event, RemoteSettingsChanged):
                settings.append([(int(key), value.new_value) for key, value in event.changed_settings.items()])
            if isinstance(event, WindowUpdated) and event.stream_id == 0:
                windows.append(event.delta)
        return events

    monkeypatch.setattr(http2_server, "peek_client_hello", capture_hello)
    monkeypatch.setattr(http2_server.H2Connection, "receive_data", capture_settings)
    assert client.private.get(url(lab), timeout=2).content == LAB_JSON
    assert client.private.get(url(lab), timeout=2).content == LAB_JSON
    assert len(hellos) == 1
    version, ciphers, extensions = hellos[0]
    assert version == [771] and ciphers == [4865]
    assert list(extensions) == [0, 43, 10, 51, 13, 16, 45]
    assert extensions[43] == b"\x02\x03\x04"  # TLS 1.3 only
    assert extensions[10] == b"\x00\x04\x00\x1d\x00\x17"  # X25519, P-256
    assert extensions[13] == b"\x00\x06\x04\x03\x05\x03\x08\x04"
    assert extensions[51][:6] == b"\x00\x24\x00\x1d\x00\x20"  # One X25519 key share
    assert settings[0] == [(1, 65536), (2, 0), (3, 1000), (4, 6291456), (6, 262144)]
    assert windows == [15663105]
    assert [record["connection_id"] for record in lab.records] == [1, 1]
    for record in lab.records:
        assert record["alpn_offers"] == ["h2"] and record["negotiated"] == "h2"
        assert [name for name, _ in record["headers"] if name.startswith(":")] == [
            ":method",
            ":authority",
            ":scheme",
            ":path",
        ]


@pytest.mark.parametrize(
    "body", ["signed_body=SIGNATURE.%7B%22x%22%3A1%7D", b"binary\x00body", BytesIO(b"file\x00body")]
)
def test_exact_prepared_body_query_and_headers(client, lab, body):
    expected = body.getvalue() if isinstance(body, BytesIO) else body.encode() if isinstance(body, str) else body
    response = client.private.post(
        url(lab, "/lab/form?encoded=%2F%2B"), data=body, headers={"X-IG-App-ID": "fixture", "X-Empty": ""}, timeout=2
    )
    assert response.content == LAB_JSON
    observed = lab.records[0]
    assert base64.b64decode(observed["body_base64"]) == expected
    headers = dict(observed["headers"])
    assert headers[":path"] == "/lab/form?encoded=%2F%2B"
    assert headers["x-ig-app-id"] == "fixture" and headers["x-empty"] == ""
    assert headers["user-agent"] == client.user_agent


def test_native_decodes_gzip_once_and_requests_owns_duplicate_cookies(client, lab):
    with client.private.get(url(lab), timeout=2, stream=True) as response:
        assert response.raw.read() == LAB_JSON
        assert response.raw.headers.getlist("set-cookie") == [
            "first_cookie=one; Path=/; Secure",
            "second_cookie=two; Path=/; Secure",
        ]
    assert b"".join(client.private.get(url(lab), timeout=2).iter_content(3)) == LAB_JSON
    assert set(dict(lab.records[-1]["headers"])["cookie"].split("; ")) == {"first_cookie=one", "second_cookie=two"}
    client.private.cookies.clear()
    client.private.get(url(lab), timeout=2)
    assert "cookie" not in dict(lab.records[-1]["headers"])


def test_head_returns_metadata_without_reading_a_gzip_body(client, lab):
    response = client.private.head(url(lab), timeout=2)
    assert response.status_code == 200 and response.content == b""
    assert int(response.headers["Content-Length"]) > 0
    assert client.private.get(url(lab), timeout=2).content == LAB_JSON


def test_private_request_classifies_429_and_stream_failure_without_repeating_post(client, lab):
    with pytest.raises(ClientThrottledError):
        client.private_request("lab/rate-limit", data={"synthetic_password": "test"}, domain=f"{LAB_HOST}:{lab.port}")
    with pytest.raises(ClientConnectionError):
        client.private_request("lab/partial", data={"synthetic_password": "test"}, domain=f"{LAB_HOST}:{lab.port}")
    assert len(lab.records) == 2


def test_transport_returns_429_and_does_not_repeat_dropped_post(client, lab):
    response = client.private.post(url(lab, "/lab/rate-limit"), data="synthetic-password", timeout=2)
    assert response.status_code == 429 and response.content == b"" and response.headers["Retry-After"] == "7"
    with pytest.raises(requests.ConnectionError):
        client.private.post(url(lab, "/lab/drop"), data="synthetic-password", timeout=2)
    assert len(lab.records) == 2


def test_per_request_deadline_and_verification_do_not_leak_through_pool(client, lab):
    assert client.private.get(url(lab), timeout=2).status_code == 200
    with pytest.raises(requests.Timeout):
        client.private.get(url(lab, "/lab/slow"), timeout=0.05)
    with pytest.raises(requests.exceptions.SSLError):
        client.private.get(url(lab), verify=True, timeout=2)
    assert len(lab.records) == 2
    assert client.private.get(url(lab), verify=False, timeout=2).status_code == 200


@pytest.mark.parametrize("scheme", ["http", "socks5h"])
def test_proxy_routes_change_without_losing_cookies_or_resending_body(client, lab, scheme, monkeypatch):
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:1")
    monkeypatch.setenv("ALL_PROXY", "http://127.0.0.1:1")
    assert client.private.get(url(lab), timeout=2).status_code == 200
    with ExitStack() as stack:
        proxy = stack.enter_context((LoopbackProxy if scheme == "http" else LoopbackSocksProxy)(lab))
        client.set_proxy(f"{scheme}://synthetic:password@127.0.0.1:{proxy.port}")
        assert client.private.post(url(lab), data=b"synthetic-body", timeout=2).content == LAB_JSON
        assert client.private.get(url(lab), timeout=2).content == LAB_JSON
        assert len(proxy.records) == 1
        assert [record["connection_id"] for record in lab.records] == [1, 2, 2]
        assert base64.b64decode(lab.records[1]["body_base64"]) == b"synthetic-body"
        assert "first_cookie=one" in dict(lab.records[1]["headers"])["cookie"]
        assert "proxy-authorization" not in dict(lab.records[1]["headers"])
        if scheme == "socks5h":
            assert proxy.records[0] == {"hostname": "localhost", "port": lab.port, "authenticated": True}
