"""Exercise Direct serialization over real loopback TLS/HTTP2 with the default curl transport."""

import base64
import json
from urllib.parse import parse_qs

import pytest

pytest.importorskip("curl_cffi")
pytest.importorskip("h2")
pytest.importorskip("cryptography")

from instagrapi import Client, config
from tests.http2_server import Handler, LoopbackServer

CHAIN = "DirectInboxFragment:direct_inbox:1:main_direct:20:::20,DirectThreadFragment:direct_thread:2:inbox:21:::21"
PAYLOAD = {"status": "ok", "payload": {"item_id": "1", "timestamp": 1761953663000000, "user_id": "123"}}


@pytest.fixture
def lab(tmp_path, monkeypatch):
    for name in ("http_proxy", "https_proxy", "all_proxy", "no_proxy", "requests_ca_bundle", "curl_ca_bundle"):
        monkeypatch.delenv(name, raising=False)
        monkeypatch.delenv(name.upper(), raising=False)
    monkeypatch.setattr(
        Handler,
        "response",
        staticmethod(lambda path: (200, [("content-type", "application/json")], json.dumps(PAYLOAD).encode())),
    )
    server = LoopbackServer(tmp_path).start()
    monkeypatch.setattr(config, "API_DOMAIN", f"localhost:{server.port}")
    try:
        yield server
    finally:
        server.close()


def assert_wire(records, text, chain, original):
    assert len(records) == 2
    headers = dict(records[0]["headers"])
    data = parse_qs(base64.b64decode(records[0]["body_base64"]).decode(), keep_blank_values=True)
    assert records[0]["negotiated"] == records[1]["negotiated"] == "h2"
    assert headers["x-ig-nav-chain"] == data["nav_chain"][0]
    if chain is not None:
        assert headers["x-ig-nav-chain"] == chain
    assert data["send_attribution"] == ["inbox"]
    assert json.loads(data["recipient_users"][0]) == [[456]]
    endpoint = "link" if "http" in text else "text"
    assert headers[":path"] == "/api/v1/direct_v2/threads/broadcast/" + endpoint + "/"
    assert dict(records[1]["headers"])["x-ig-nav-chain"] == original


@pytest.mark.parametrize("chain", [None, CHAIN])
@pytest.mark.parametrize("text", ["hello", "https://example.com/link"])
def test_default_curl_sends_matching_chain_without_leaking(lab, text, chain):
    client = Client(
        settings={"authorization_data": {"ds_user_id": "123", "sessionid": "synthetic-session"}},
        tls_verify=str(lab.ca_path),
        request_timeout=0,
    )
    try:
        assert client.private_transport == "curl"
        original = client.base_headers["X-IG-Nav-Chain"]
        result = client.direct_send(text, user_ids=[456], send_attribute="inbox", nav_chain=chain)
        assert result.id == "1"
        client.private_request("test/")
        assert client.private.headers["X-IG-Nav-Chain"] == original
        assert_wire(lab.records, text, chain, original)
    finally:
        for session in (client.private, client.public, client.graphql):
            session.close()
