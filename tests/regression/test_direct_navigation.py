import json
import socket
from copy import deepcopy
from types import SimpleNamespace
from typing import get_args
from urllib.parse import parse_qs

import pytest

from instagrapi import Client
from instagrapi.exceptions import ClientError
from instagrapi.mixins.direct import SEND_ATTRIBUTE

SETTINGS = {"authorization_data": {"ds_user_id": "123", "sessionid": "synthetic-session"}}
LEGACY_CHAIN = (
    "1qT:feed_timeline:1,1qT:feed_timeline:2,1qT:feed_timeline:3,"
    "7Az:direct_inbox:4,7Az:direct_inbox:5,5rG:direct_thread:7"
)
PROFILE_CHAIN = (
    "UserDetailFragment:profile:1:search_result:10:::10,DirectThreadFragment:direct_thread:2:message_button:11:::11"
)
INBOX_CHAIN = (
    "DirectInboxFragment:direct_inbox:1:main_direct:20:::20,DirectThreadFragment:direct_thread:2:inbox:21:::21"
)
PAYLOAD = {"status": "ok", "payload": {"item_id": "1", "timestamp": 1761953663000000, "user_id": "123"}}


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Network prohibited in Direct serialization tests")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket, "getaddrinfo", blocked)
    import curl_cffi
    import curl_cffi.aio

    monkeypatch.setattr(curl_cffi.Curl, "perform", blocked)
    monkeypatch.setattr(curl_cffi.aio.AsyncCurl, "add_handle", blocked)


def form(request):
    body = request.body
    return parse_qs(body.decode() if isinstance(body, bytes) else body, keep_blank_values=True)


from contextlib import contextmanager

import requests
from requests.adapters import BaseAdapter


class Recorder(BaseAdapter):
    def __init__(self):
        self.records = []
        self.fail_next = False

    def send(self, request, **kwargs):
        self.records.append(request)
        response = requests.Response()
        response.status_code = 400 if self.fail_next else 200
        response._content = json.dumps(
            {"status": "fail", "message": "synthetic failure"} if self.fail_next else PAYLOAD
        ).encode()
        response.request = request
        response.url = request.url
        self.fail_next = False
        return response

    def close(self):
        pass


@contextmanager
def recording():
    client = Client(settings=deepcopy(SETTINGS), private_transport="requests", request_timeout=0)
    recorder = Recorder()
    previous = set(client.private.adapters.values())
    client.private.mount("http://", recorder)
    client.private.mount("https://", recorder)
    for adapter in previous:
        adapter.close()
    try:
        yield client, recorder
    finally:
        for session in (client.private, client.public, client.graphql):
            session.close()


@pytest.mark.parametrize("text, endpoint", [("hello", "text"), ("see https://example.com/a", "link")])
@pytest.mark.parametrize("attribution", ["message_button", "inbox_search", "inbox"])
def test_default_chain_matches_actual_header_and_preserves_payload(text, endpoint, attribution):
    with recording() as (client, recorder):
        result = client.direct_send(text, user_ids=[456], send_attribute=attribution)
        assert result.id == "1"
        request = recorder.records[0]
        data = form(request)
        assert str(request.url).endswith("/broadcast/" + endpoint + "/")
        assert request.headers["X-IG-Nav-Chain"] == data["nav_chain"][0] == LEGACY_CHAIN
        assert data["send_attribution"] == [attribution]
        assert json.loads(data["recipient_users"][0]) == [[456]]
        assert data["client_context"] == data["mutation_token"] == data["offline_threading_id"]
        assert "signed_body" not in data
        assert attribution in get_args(SEND_ATTRIBUTE)
        if endpoint == "link":
            assert data["link_text"] == [text]
            assert json.loads(data["link_urls"][0]) == ["https://example.com/a"]
        else:
            assert data["text"] == [text]


def test_custom_chains_are_request_local_and_do_not_leak():
    with recording() as (client, recorder):
        original = client.base_headers["X-IG-Nav-Chain"]
        for chain, attribution in [(PROFILE_CHAIN, "message_button"), (INBOX_CHAIN, "inbox")]:
            client.direct_send("hello", thread_ids=[456], send_attribute=attribution, nav_chain=chain)
        client.private_request("test/")
        assert [form(req)["nav_chain"][0] for req in recorder.records[:2]] == [PROFILE_CHAIN, INBOX_CHAIN]
        assert [req.headers["X-IG-Nav-Chain"] for req in recorder.records] == [PROFILE_CHAIN, INBOX_CHAIN, original]
        assert client.base_headers["X-IG-Nav-Chain"] == client.private.headers["X-IG-Nav-Chain"] == original


def test_positional_reply_and_link_keep_fields_with_custom_chain():
    with recording() as (client, recorder):
        reply = SimpleNamespace(id="88", client_context="reply-context")
        client.direct_send("https://example.com/reply", [], [456], "message_button", reply, nav_chain=PROFILE_CHAIN)
        request = recorder.records[0]
        data = form(request)
        assert str(request.url).endswith("/broadcast/link/")
        assert data["nav_chain"] == [PROFILE_CHAIN]
        assert request.headers["X-IG-Nav-Chain"] == PROFILE_CHAIN
        assert data["replied_to_item_id"] == ["88"]
        assert data["replied_to_client_context"] == ["reply-context"]
        assert data["replied_to_action_source"] == ["swipe"]
        assert json.loads(data["thread_ids"][0]) == [456]
        assert "recipient_users" not in data


@pytest.mark.parametrize(
    "chain", ["", " ", " leading", "x\rInjected: yes", "x\nInjected: yes", "x\x00", "x\t", "x\x7f", 123, False, []]
)
def test_invalid_chain_is_rejected_before_dispatch(chain):
    with recording() as (client, recorder):
        with pytest.raises(ValueError, match="nav_chain"):
            client.direct_send("hello", thread_ids=[456], nav_chain=chain)
        assert recorder.records == []


def test_failed_send_does_not_leak_chain_to_next_request():
    with recording() as (client, recorder):
        original = client.base_headers["X-IG-Nav-Chain"]
        recorder.fail_next = True
        with pytest.raises(ClientError):
            client.direct_send("hello", thread_ids=[456], nav_chain=PROFILE_CHAIN)
        client.private_request("test/")
        assert len(recorder.records) == 2
        assert recorder.records[0].headers["X-IG-Nav-Chain"] == PROFILE_CHAIN
        assert recorder.records[1].headers["X-IG-Nav-Chain"] == original
        assert client.private.headers["X-IG-Nav-Chain"] == original
