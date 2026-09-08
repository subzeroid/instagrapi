import sys
from unittest import mock

import pytest
from requests.adapters import HTTPAdapter

from instagrapi import Client


def test_default_private_transport_does_not_import_optional_dependencies(monkeypatch):
    monkeypatch.setitem(sys.modules, "curl_adapter", None)
    monkeypatch.setitem(sys.modules, "curl_cffi", None)
    client = Client()

    assert client.private_transport == "requests"
    assert type(client.private.get_adapter("https://i.instagram.com/")) is HTTPAdapter


def test_unknown_private_transport_is_rejected():
    with pytest.raises(ValueError, match="private_transport"):
        Client(private_transport="unknown")


def test_missing_curl_extra_has_actionable_error(monkeypatch):
    # Keep newly imported application modules cached for later mock targets.
    monkeypatch.setitem(sys.modules, "curl_adapter", None)
    monkeypatch.setitem(sys.modules, "curl_cffi", None)
    with pytest.raises(RuntimeError, match=r"pip install instagrapi\[curl\]"):
        Client(private_transport="curl")


@pytest.fixture
def curl_adapter_factory():
    with mock.patch("instagrapi.transports.create_curl_h2_adapter") as factory:
        factory.return_value = mock.Mock(spec=HTTPAdapter)
        yield factory


def test_private_curl_keeps_sessions_headers_proxy_and_tls_settings(curl_adapter_factory):
    client = Client(private_transport="curl", proxy="http://proxy.example:8080", tls_verify="custom-ca.pem")

    assert client.private_transport == "curl"
    assert client.public_transport == "requests"
    assert client.private.get_adapter("https://i.instagram.com/") is curl_adapter_factory.return_value
    curl_adapter_factory.assert_called_once_with()
    assert type(client.public.get_adapter("https://i.instagram.com/")) is HTTPAdapter
    assert type(client.graphql.get_adapter("https://i.instagram.com/")) is HTTPAdapter
    assert client.private.verify == "custom-ca.pem"
    assert client.private.proxies["https"] == "http://proxy.example:8080"
    assert client.private.headers["User-Agent"] == client.user_agent


def test_private_transport_roundtrip_and_switch_preserve_session(curl_adapter_factory):
    client = Client(private_transport="curl")
    adapter = client.private.get_adapter("https://i.instagram.com/")
    session = client.private
    session.cookies.set("sessionid", "test-session", domain="i.instagram.com", path="/")
    session.headers["Authorization"] = "Bearer test-token"
    settings = client.get_settings()

    assert settings["private_transport"] == "curl"
    restored = Client(settings=settings)
    assert restored.private_transport == "curl"
    assert restored.private.cookies.get("sessionid") == "test-session"

    client.set_retry_config(session_retry_total=0)
    assert client.private.get_adapter("https://i.instagram.com/") is adapter
    adapter.close.assert_not_called()

    client.set_retry_config(private_transport="requests")
    assert client.private is session
    assert type(session.get_adapter("https://i.instagram.com/")) is HTTPAdapter
    assert session.cookies.get("sessionid") == "test-session"
    assert session.headers["Authorization"] == "Bearer test-token"
    assert client.get_settings()["private_transport"] == "requests"
    adapter.close.assert_called_once()


def test_loading_legacy_settings_keeps_explicit_private_transport(curl_adapter_factory):
    client = Client(private_transport="curl", settings={"locale": "en_US"})
    assert client.private_transport == "curl"


def test_invalid_transport_update_does_not_replace_adapter(curl_adapter_factory):
    client = Client(private_transport="curl")
    adapter = client.private.get_adapter("https://i.instagram.com/")
    with pytest.raises(ValueError, match="private_transport"):
        client.set_retry_config(private_transport="unknown")
    assert client.private.get_adapter("https://i.instagram.com/") is adapter
    adapter.close.assert_not_called()


def test_unavailable_transport_update_keeps_working_configuration():
    client = Client()
    adapter = client.private.get_adapter("https://i.instagram.com/")
    with mock.patch("instagrapi.transports.create_curl_h2_adapter", side_effect=RuntimeError("Unavailable")):
        with pytest.raises(RuntimeError, match="Unavailable"):
            client.set_retry_config(private_transport="curl")
    assert client.private_transport == "requests"
    assert client.get_settings()["private_transport"] == "requests"
    assert client.private.get_adapter("https://i.instagram.com/") is adapter
