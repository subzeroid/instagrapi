from unittest import mock

from instagrapi import Client


class _FakeResponse:
    status_code = 200
    text = ""

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class _FakeSession:
    def __init__(self):
        self.verify = None
        self.proxies = {}
        self.get_calls = []
        self.post_calls = []

    def get(self, *args, **kwargs):
        self.get_calls.append((args, kwargs))
        return _FakeResponse({"offset": 0})

    def post(self, *args, **kwargs):
        self.post_calls.append((args, kwargs))
        return _FakeResponse({"media_id": 123})


def _assert_client_tls_verify(client, expected):
    assert client.tls_verify == expected
    assert client.public.verify == expected
    assert client.private.verify == expected
    assert client.graphql.verify == expected


def test_default_client_tls_verify_is_enabled():
    _assert_client_tls_verify(Client(), True)


def test_client_tls_verify_can_be_disabled_for_debugging_proxy():
    _assert_client_tls_verify(Client(tls_verify=False), False)


def test_client_tls_verify_accepts_ca_bundle_path_and_roundtrips_settings():
    ca_bundle = "/tmp/instagram-proxy-ca.pem"
    client = Client(tls_verify=ca_bundle)

    settings = client.get_settings()
    assert settings["tls_verify"] == ca_bundle

    restored = Client(settings=settings)
    _assert_client_tls_verify(restored, ca_bundle)


def test_set_tls_verify_updates_existing_sessions():
    client = Client()

    assert client.set_tls_verify(False) is True
    _assert_client_tls_verify(client, False)


def test_direct_rupload_fresh_sessions_use_client_tls_verify():
    client = Client(tls_verify="/tmp/direct-ca.pem")
    fake_session = _FakeSession()

    with mock.patch("requests.Session", return_value=fake_session):
        media_id = client._video_rupload(b"video-bytes", "entity-name", "waterfall-id")

    assert media_id == 123
    assert fake_session.verify == "/tmp/direct-ca.pem"
