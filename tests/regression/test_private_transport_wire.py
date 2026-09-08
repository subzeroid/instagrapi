"""Exercise the optional transport against a real loopback TLS/HTTP2 server."""

import base64
import shutil
import subprocess
from io import BytesIO

import pytest
import requests
from urllib3.util import Timeout

curl_cffi = pytest.importorskip("curl_cffi", reason="install instagrapi[curl] for transport wire tests")
pytest.importorskip("h2")
pytest.importorskip("cryptography")

from curl_cffi import CurlHttpVersion, CurlOpt

from instagrapi import Client
from instagrapi.exceptions import ClientConnectionError, ClientThrottledError
from tests.http2_server import LAB_HOST, LAB_JSON, LoopbackServer


@pytest.fixture
def lab(tmp_path, monkeypatch):
    # Curl must never inherit a developer's real proxy during a loopback test.
    for name in ("http_proxy", "https_proxy", "all_proxy", "no_proxy"):
        monkeypatch.delenv(name, raising=False)
        monkeypatch.delenv(name.upper(), raising=False)
    server = LoopbackServer(tmp_path).start()
    try:
        yield server
    finally:
        server.close()


@pytest.fixture
def client(lab):
    client = Client(private_transport="curl", tls_verify=str(lab.ca_path), request_timeout=0)
    client.private.trust_env = False
    adapter = client.private.get_adapter("https://localhost/")
    adapter.client.curl_options[CurlOpt.RESOLVE] = [f"{LAB_HOST}:{lab.port}:127.0.0.1"]
    try:
        yield client
    finally:
        for session in (client.private, client.public, client.graphql):
            session.close()


def url(lab, path="/lab/ok"):
    return f"https://{LAB_HOST}:{lab.port}{path}"


def test_actual_clienthello_h2_only_and_connection_reuse(client, lab):
    first = client.private.get(url(lab), timeout=2)
    second = client.private.get(url(lab), timeout=2)

    assert first.json() == second.json() == {"status": "lab-ok"}
    assert [r["alpn_offers"] for r in lab.records] == [["h2"], ["h2"]]
    assert [r["negotiated"] for r in lab.records] == ["h2", "h2"]
    assert [r["connection_id"] for r in lab.records] == [1, 1]
    assert [r["stream_id"] for r in lab.records] == [1, 3]


def test_mixed_alpn_control_still_negotiates_h2_but_has_different_clienthello(client, lab):
    adapter = client.private.get_adapter(url(lab))
    adapter.client.http_version = CurlHttpVersion.V2_0
    response = client.private.get(url(lab), timeout=2)

    assert response.status_code == 200
    assert lab.records[0]["negotiated"] == "h2"
    assert lab.records[0]["alpn_offers"] == ["h2", "http/1.1"]


@pytest.mark.parametrize(
    "body", ["signed_body=SIGNATURE.%7B%22x%22%3A1%7D", b"binary\x00body", BytesIO(b"file\x00body")]
)
def test_exact_prepared_body_and_mobile_headers(client, lab, body):
    expected = body.getvalue() if isinstance(body, BytesIO) else body.encode() if isinstance(body, str) else body
    request = requests.Request(
        "POST",
        url(lab, "/lab/form?encoded=%2F%2B"),
        data=body,
        headers={"X-IG-App-ID": "test-app", "Content-Type": "application/octet-stream", "X-Empty": ""},
    )
    prepared = client.private.prepare_request(request)
    original_headers = dict(prepared.headers)
    response = client.private.send(prepared, verify=str(lab.ca_path), timeout=2)

    assert response.status_code == 200
    assert dict(prepared.headers) == original_headers
    observed = lab.records[0]
    headers = dict(observed["headers"])
    assert base64.b64decode(observed["body_base64"]) == expected
    assert headers[":path"] == "/lab/form?encoded=%2F%2B"
    assert headers["x-ig-app-id"] == "test-app"
    assert headers["x-empty"] == ""
    assert headers["content-type"] == "application/octet-stream"
    assert headers["user-agent"] == client.user_agent


def test_gzip_is_decoded_once_and_raw_stream_stays_compressed(client, lab):
    with client.private.get(url(lab), timeout=2, stream=True) as response:
        assert response.raw.read(2) == b"\x1f\x8b"
    with client.private.get(url(lab), timeout=2, stream=True) as response:
        assert b"".join(response.iter_content(3)) == LAB_JSON
    assert client.private.get(url(lab), timeout=2).json() == {"status": "lab-ok"}


@pytest.mark.parametrize("stream", [False, True])
def test_head_preserves_content_length_without_expecting_a_body(client, lab, stream):
    with client.private.head(url(lab), timeout=2, stream=stream) as response:
        assert response.status_code == 200
        assert int(response.headers["Content-Length"]) > 0
        assert b"".join(response.iter_content(3)) == b""
    assert client.private.get(url(lab), timeout=2).json() == {"status": "lab-ok"}
    assert [dict(record["headers"])[":method"] for record in lab.records] == ["HEAD", "GET"]
    assert [record["connection_id"] for record in lab.records] == [1, 1]


def test_duplicate_cookies_are_replayed_and_cleared_only_by_requests(client, lab):
    first = client.private.get(url(lab), timeout=2)
    assert first.raw.headers.getlist("set-cookie") == [
        "first_cookie=one; Path=/; Secure",
        "second_cookie=two; Path=/; Secure",
    ]
    assert first.cookies.get_dict() == {"first_cookie": "one", "second_cookie": "two"}
    client.private.get(url(lab), timeout=2)
    cookies = dict(lab.records[-1]["headers"])["cookie"]
    assert set(cookies.split("; ")) == {"first_cookie=one", "second_cookie=two"}
    client.private.cookies.clear()
    client.private.get(url(lab), timeout=2)
    assert "cookie" not in dict(lab.records[-1]["headers"])


def test_429_preserves_response_without_automatic_post_retry(client, lab):
    response = client.private.post(url(lab, "/lab/rate-limit"), data="synthetic_password=test", timeout=2)
    assert response.status_code == 429
    assert response.content == b""
    assert response.headers["Retry-After"] == "7"
    assert len(lab.records) == 1


def test_private_request_maps_429_without_retrying_password(client, lab):
    with pytest.raises(ClientThrottledError):
        client.private_request("lab/rate-limit", data={"synthetic_password": "test"}, domain=f"{LAB_HOST}:{lab.port}")
    assert len(lab.records) == 1


def test_connection_drop_maps_error_without_resubmitting_body(client, lab):
    with pytest.raises(requests.ConnectionError):
        client.private.post(url(lab, "/lab/drop"), data="synthetic_password=test", timeout=2)
    assert len(lab.records) == 1


def test_truncated_http2_stream_maps_to_requests_connection_error(client, lab):
    with pytest.raises(requests.ConnectionError):
        client.private.get(url(lab, "/lab/partial"), timeout=2)
    assert len(lab.records) == 1


def test_private_request_preserves_http2_stream_failure(client, lab):
    with pytest.raises(ClientConnectionError):
        client.private_request("lab/partial", domain=f"{LAB_HOST}:{lab.port}")
    assert len(lab.records) == 1


def test_curl_partial_file_does_not_resubmit_password(client, monkeypatch):
    from curl_cffi.requests.exceptions import IncompleteRead

    submissions = []

    def partial_file(*args, **kwargs):
        submissions.append(kwargs["data"])
        raise IncompleteRead("Synthetic partial transfer", code=18)

    adapter = client.private.get_adapter("https://i.instagram.com/")
    monkeypatch.setattr(adapter.client, "request", partial_file)
    with pytest.raises(ClientConnectionError):
        client.private_request("synthetic/partial", data={"synthetic_password": "test"})
    assert len(submissions) == 1


def test_per_request_tls_verification_and_ca_path(client, lab):
    with pytest.raises(requests.exceptions.SSLError):
        client.private.get(url(lab), verify=True, timeout=2)
    assert lab.records == []
    assert client.private.get(url(lab), verify=str(lab.ca_path), timeout=2).status_code == 200


def test_insecure_request_does_not_disable_verification_for_later_requests(client, lab):
    assert client.private.get(url(lab), verify=False, timeout=2).status_code == 200
    with pytest.raises(requests.exceptions.SSLError):
        client.private.get(url(lab), verify=True, timeout=2)
    assert len(lab.records) == 1


def test_per_request_timeout_is_honored(client, lab):
    with pytest.raises(requests.Timeout):
        client.private.get(url(lab, "/lab/slow"), timeout=0.05)
    assert len(lab.records) == 1


@pytest.mark.parametrize("timeout", [(None, 0.05), Timeout(connect=0.05, read=0.05)])
def test_unsupported_timeouts_are_rejected_before_network(client, lab, timeout):
    with pytest.raises(ValueError, match="numeric"):
        client.private.get(url(lab, "/lab/slow"), timeout=timeout)
    assert lab.records == []


def test_trust_env_false_does_not_use_curl_environment_proxy(client, lab, monkeypatch):
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:1")
    monkeypatch.setenv("ALL_PROXY", "http://127.0.0.1:1")
    assert client.private.get(url(lab), timeout=2).status_code == 200


def test_explicit_proxy_overrides_environment_no_proxy(client, lab, monkeypatch):
    monkeypatch.setenv("NO_PROXY", "*")
    with pytest.raises(requests.ConnectionError):
        client.private.get(url(lab), proxies={"https": "http://127.0.0.1:1"}, timeout=0.2)
    assert lab.records == []


def test_session_proxy_change_is_honored(client, lab):
    assert client.private.get(url(lab), timeout=2).status_code == 200
    client.set_proxy("http://127.0.0.1:1")
    with pytest.raises(requests.ConnectionError):
        client.private.get(url(lab), timeout=0.2)
    assert len(lab.records) == 1


def test_old_libcurl_rejected_before_any_request(monkeypatch):
    monkeypatch.setattr(curl_cffi, "__curl_version__", "libcurl/8.9.1 OpenSSL")
    with pytest.raises(RuntimeError, match=r"libcurl.*8\.10"):
        Client(private_transport="curl")


@pytest.mark.parametrize("variable", ["REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE"])
def test_requests_controls_whether_to_trust_environment_ca(lab, monkeypatch, variable):
    monkeypatch.delenv("REQUESTS_CA_BUNDLE", raising=False)
    monkeypatch.delenv("CURL_CA_BUNDLE", raising=False)
    monkeypatch.setenv(variable, str(lab.ca_path))
    client = Client(private_transport="curl")
    try:
        client.private.trust_env = False
        with pytest.raises(requests.exceptions.SSLError):
            client.private.get(url(lab), timeout=2)
        assert lab.records == []
        client.private.trust_env = True
        assert client.private.get(url(lab), timeout=2).status_code == 200
    finally:
        for session in (client.private, client.public, client.graphql):
            session.close()


def test_ca_directory_is_honored_and_does_not_leak_to_later_requests(client, lab, tmp_path):
    openssl = shutil.which("openssl")
    if not openssl:
        pytest.skip("openssl rehash is needed for the CA directory fixture")
    ca_directory = tmp_path / "ca-directory"
    ca_directory.mkdir()
    shutil.copyfile(lab.ca_path, ca_directory / "root.pem")
    subprocess.run([openssl, "rehash", str(ca_directory)], check=True, capture_output=True)
    assert client.private.get(url(lab), verify=str(ca_directory), timeout=2).status_code == 200
    with pytest.raises(requests.exceptions.SSLError):
        client.private.get(url(lab), verify=True, timeout=2)
    assert client.private.get(url(lab), verify=str(lab.ca_path), timeout=2).status_code == 200
