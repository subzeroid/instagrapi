import socket
from copy import deepcopy
from itertools import count
from types import SimpleNamespace

import pytest
import requests
from requests.adapters import BaseAdapter

from instagrapi import Client
from instagrapi.mixins import private

PIGEON = "X-Pigeon-Session-Id"
RAWTIME = "X-Pigeon-Rawclienttime"
SALT = "X-IG-SALT-IDS"
ACCOUNT_SETTINGS = {"authorization_data": {"ds_user_id": "123", "sessionid": "synthetic-session"}}


class RecordingAdapter(BaseAdapter):
    def __init__(self, records):
        self.records = records

    def send(self, request, **kwargs):
        self.records.append(request)
        response = requests.Response()
        response.status_code = 200
        response._content = b'{"status":"ok"}'
        response.request = request
        response.url = request.url
        return response

    def close(self):
        pass


def record_requests(client, records):
    previous = set(client.private.adapters.values())
    adapter = RecordingAdapter(records)
    client.private.mount("http://", adapter)
    client.private.mount("https://", adapter)
    for retired in previous:
        retired.close()


@pytest.fixture
def recording(monkeypatch):
    def forbid_network(*args, **kwargs):
        raise AssertionError("Network access is forbidden in header lifetime tests")

    monkeypatch.setattr(socket.socket, "connect", forbid_network)
    clock = count(1700000000, 2)
    monkeypatch.setattr(private, "time", SimpleNamespace(time=lambda: next(clock), sleep=lambda _: None))
    clients, records = [], []

    def make_client(settings=None):
        client = Client(settings=settings, private_transport="requests", request_timeout=0)
        record_requests(client, records)
        clients.append(client)
        return client

    yield make_client, records
    for client in clients:
        for session in (client.private, client.public, client.graphql):
            session.close()


def test_successive_get_and_post_reuse_pigeon_id(recording):
    make_client, records = recording
    client = make_client()
    client.private_request("test/")
    client.private_request("test/", data={"synthetic": "value"})

    assert [request.method for request in records] == ["GET", "POST"]
    same_pigeon = records[0].headers[PIGEON] == records[1].headers[PIGEON]
    assert same_pigeon, "A Client must reuse its runtime Pigeon ID"


def test_rawclienttime_is_fresh_for_each_request(recording):
    make_client, records = recording
    client = make_client()
    client.private_request("test/")
    client.private_request("test/", data={"synthetic": "value"})

    newer_timestamp = float(records[1].headers[RAWTIME]) > float(records[0].headers[RAWTIME])
    assert newer_timestamp


def test_new_and_restored_clients_have_distinct_runtime_ids(recording):
    make_client, records = recording
    original = make_client(deepcopy(ACCOUNT_SETTINGS))
    saved = original.get_settings()
    restored = make_client(saved)
    independent = make_client()
    for client in (original, restored, independent):
        client.private_request("test/")

    distinct_ids = len({request.headers[PIGEON] for request in records})
    assert distinct_ids == 3
    assert restored.get_settings()["uuids"] == saved["uuids"]
    assert restored.authorization_data == original.authorization_data
    pigeon_persisted = any("pigeon" in key.lower() for key in saved)
    assert not pigeon_persisted


def test_reapplying_settings_preserves_runtime_id(recording):
    make_client, records = recording
    client = make_client(deepcopy(ACCOUNT_SETTINGS))
    client.private_request("test/")
    client.set_settings(client.get_settings())
    record_requests(client, records)
    client.private_request("test/")

    same_pigeon = records[0].headers[PIGEON] == records[1].headers[PIGEON]
    assert same_pigeon, "Settings reapplication must preserve the runtime Pigeon ID"


def test_authorization_cleanup_preserves_runtime_id(recording):
    make_client, records = recording
    client = make_client(deepcopy(ACCOUNT_SETTINGS))
    client.private_request("test/")
    client._clear_session_state(
        clear_private_cookies=True, clear_authorization_data=True, clear_authorization_header=True
    )
    client.private_request("test/", login=True)

    assert "Authorization" in records[0].headers
    assert "Authorization" not in records[1].headers
    assert records[1].headers["IG-INTENDED-USER-ID"] == "0"
    same_pigeon = records[0].headers[PIGEON] == records[1].headers[PIGEON]
    assert same_pigeon, "Authorization cleanup must preserve the runtime Pigeon ID"


def test_upload_header_helper_uses_the_same_runtime_id(recording):
    make_client, records = recording
    client = make_client(deepcopy(ACCOUNT_SETTINGS))
    client.private_request("test/")
    client.private.post(
        "https://i.instagram.com/rupload_igphoto/synthetic",
        data=b"synthetic",
        headers=client.private_headers({"X-Entity-Type": "image/jpeg"}),
    )
    client.private_request("test/")

    assert records[1].headers["X-Entity-Type"] == "image/jpeg"
    assert "Authorization" in records[1].headers
    same_pigeon = len({request.headers[PIGEON] for request in records}) == 1
    assert same_pigeon, "Uploads and private API requests must share the runtime Pigeon ID"
    newer_timestamp = float(records[1].headers[RAWTIME]) > float(records[0].headers[RAWTIME])
    assert newer_timestamp


def test_default_headers_omit_salt_ids(recording):
    make_client, records = recording
    client = make_client()
    client.private_request("test/")
    client.private_request("test/", data={"synthetic": "value"})

    salt_omitted = all(SALT not in request.headers for request in records)
    assert salt_omitted, "Ordinary requests must not fabricate diagnostic flow IDs"
    assert SALT not in client.private_headers()
    assert SALT not in client.private.headers


def test_explicit_request_overrides_do_not_leak(recording):
    make_client, records = recording
    client = make_client()
    client.private_request("test/")
    client.private_request("test/", data={"synthetic": "value"}, headers={PIGEON: "caller-pigeon", SALT: "11,12"})
    client.private_request("test/")

    assert records[1].headers[PIGEON] == "caller-pigeon"
    assert records[1].headers[SALT] == "11,12"
    same_pigeon = records[0].headers[PIGEON] == records[2].headers[PIGEON]
    assert same_pigeon, "A request override must not replace the runtime Pigeon ID"
    assert SALT not in records[2].headers
    assert SALT not in client.private.headers


def test_persistent_caller_salt_survives_requests_and_temporary_override(recording):
    make_client, records = recording
    client = make_client()
    client.private.headers[SALT] = "11,12"
    client.private_request("test/")
    client.private_request("test/", data={"synthetic": "value"}, headers={SALT: "21"})
    client.private_request("test/")

    caller_salt_preserved = [request.headers.get(SALT) for request in records] == ["11,12", "21", "11,12"]
    assert caller_salt_preserved, "Base headers must preserve caller-supplied persistent SALT"
    assert client.private.headers[SALT] == "11,12"


def test_transport_switches_preserve_runtime_id(recording):
    pytest.importorskip("curl_cffi")
    make_client, records = recording
    client = make_client()
    client.private_request("test/")
    for transport in ("curl", "requests"):
        client.set_retry_config(private_transport=transport)
        record_requests(client, records)
        client.private_request("test/")

    same_pigeon = len({request.headers[PIGEON] for request in records}) == 1
    assert same_pigeon, "Transport selection must preserve the runtime Pigeon ID"
