"""Exercise the optional public adapter with real loopback response bodies."""

import gzip
import json
import threading
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from instagrapi import Client

BODY = '{"status":"ok","title":"café"}'.encode()
PAYLOAD = {"status": "ok", "title": "café"}


@pytest.fixture(scope="module")
def public_server():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/browser-headers":
                body = json.dumps({"browser_headers": "Sec-Fetch-Mode" in self.headers}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            body = BODY
            encoding = self.path.removeprefix("/")
            if encoding == "gzip":
                body = gzip.compress(body)
            elif encoding == "deflate":
                body = zlib.compress(body)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            if encoding != "plain":
                self.send_header("Content-Encoding", encoding)
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{server.server_port}"
        finally:
            server.shutdown()
            thread.join(timeout=5)


@pytest.fixture
def curl_adapter():
    # Default installations must remain usable without the optional extra.
    return pytest.importorskip("curl_adapter")


@pytest.fixture
def curl_client(curl_adapter):
    client = Client(public_transport="curl")
    client.public.trust_env = False
    try:
        assert isinstance(client.public.get_adapter("http://"), curl_adapter.CurlCffiAdapter)
        yield client
    finally:
        client.public.close()
        client.private.close()


@pytest.mark.parametrize("encoding", ["plain", "gzip", "deflate"])
@pytest.mark.parametrize("stream", [False, True], ids=["buffered", "streamed"])
def test_public_curl_reads_response_body(curl_client, public_server, encoding, stream):
    with curl_client.public.get(f"{public_server}/{encoding}", stream=stream, timeout=5) as response:
        assert response.status_code == 200
        if stream:
            assert not response._content_consumed
            assert b"".join(response.iter_content(chunk_size=7)) == BODY
        else:
            assert response.content == BODY
            assert response.json() == PAYLOAD


@pytest.mark.parametrize("encoding", ["plain", "gzip", "deflate"])
def test_public_curl_request_decodes_json(curl_client, public_server, encoding):
    assert curl_client.public_request(f"{public_server}/{encoding}", return_json=True, retries_count=1) == PAYLOAD


def test_public_curl_sends_browser_headers(curl_client, public_server):
    assert curl_client.public_request(f"{public_server}/browser-headers", return_json=True, retries_count=1) == {
        "browser_headers": True
    }


def test_public_curl_browser_alias_sends_browser_headers(curl_adapter, public_server):
    client = Client(public_transport="curl", public_transport_impersonate="chrome")
    client.public.trust_env = False
    try:
        assert client.public_request(f"{public_server}/browser-headers", return_json=True, retries_count=1) == {
            "browser_headers": True
        }
    finally:
        client.public.close()
        client.private.close()
