import sys
from importlib.metadata import requires
from unittest import mock

from packaging.requirements import Requirement

from instagrapi import Client


def test_default_public_transport_does_not_require_curl_adapter():
    assert Client().public_transport == "requests"


def test_public_user_agent_override_is_preserved():
    client = Client(public_user_agent="custom-public-agent")

    assert client.public.headers["User-Agent"] == "custom-public-agent"


def test_curl_adapter_is_optional_extra():
    requirements = [Requirement(value) for value in requires("instagrapi")]
    adapters = [requirement for requirement in requirements if requirement.name == "curl-adapter"]

    assert len(adapters) == 1
    adapter = adapters[0]
    assert adapter.marker is not None
    assert not adapter.marker.evaluate({"extra": ""})
    assert adapter.marker.evaluate({"extra": "curl"})
    assert "1.2.2" not in adapter.specifier
    assert "1.2.3" in adapter.specifier
    assert "1.2.4" in adapter.specifier


def test_curl_public_transport_uses_optional_adapter():
    adapter = mock.Mock()
    adapter_cls = mock.Mock(return_value=adapter)
    with mock.patch.dict(sys.modules, {"curl_adapter": mock.Mock(CurlCffiAdapter=adapter_cls)}):
        client = Client(public_transport="curl", public_transport_impersonate="chrome136")

    assert client.public_transport == "curl"
    assert client.public_transport_impersonate == "chrome136"
    adapter_cls.assert_any_call(impersonate_browser_type="chrome136")
    assert client.public.adapters["https://"] is adapter
    assert client.public.adapters["http://"] is adapter


def test_curl_public_transport_missing_extra_has_clear_error():
    with mock.patch.dict(sys.modules, {"curl_adapter": None}):
        try:
            Client(public_transport="curl")
        except RuntimeError as exc:
            assert "pip install instagrapi[curl]" in str(exc)
        else:
            raise AssertionError("Expected RuntimeError when curl extra is not installed")


def test_public_transport_settings_roundtrip():
    adapter_cls = mock.Mock(return_value=mock.Mock())
    with mock.patch.dict(sys.modules, {"curl_adapter": mock.Mock(CurlCffiAdapter=adapter_cls)}):
        client = Client(public_transport="curl", public_transport_impersonate="chrome136")
        settings = client.get_settings()

        assert settings["public_transport"] == "curl"
        assert settings["public_transport_impersonate"] == "chrome136"

        restored = Client(settings=settings)

    assert restored.public_transport == "curl"
    assert restored.public_transport_impersonate == "chrome136"
