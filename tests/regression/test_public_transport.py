import sys
from pathlib import Path
from unittest import mock

from instagrapi import Client


def test_default_public_transport_does_not_require_curl_adapter():
    assert Client().public_transport == "requests"


def test_public_user_agent_override_is_preserved():
    client = Client(public_user_agent="custom-public-agent")

    assert client.public.headers["User-Agent"] == "custom-public-agent"


def test_curl_adapter_is_optional_extra():
    pyproject = Path("pyproject.toml").read_text()
    required_dependencies = pyproject.split("[project.optional-dependencies]", 1)[0]
    optional_dependencies = pyproject.split("[project.optional-dependencies]", 1)[1]

    assert "curl-adapter" not in required_dependencies
    assert "curl = [" in optional_dependencies
    assert '"curl-adapter>=1.2.1"' in optional_dependencies


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
