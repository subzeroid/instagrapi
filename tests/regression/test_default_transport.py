import pytest

from instagrapi import Client
from instagrapi.transports import _CurlH2Adapter


@pytest.mark.parametrize(
    "kwargs, expected",
    [
        ({}, "curl"),
        ({"settings": {"locale": "en_US"}}, "curl"),
        ({"private_transport": "requests"}, "requests"),
        ({"settings": {"locale": "en_US"}, "private_transport": "requests"}, "requests"),
        ({"settings": {"private_transport": "requests"}, "private_transport": "curl"}, "requests"),
        ({"settings": {"private_transport": "curl"}, "private_transport": "requests"}, "curl"),
    ],
)
def test_private_transport_default_and_saved_precedence(kwargs, expected):
    client = Client(**kwargs)
    try:
        assert client.private_transport == expected
        assert (isinstance(client.private.get_adapter("https://i.instagram.com/"), _CurlH2Adapter)) is (
            expected == "curl"
        )
        assert client.get_settings()["private_transport"] == expected
        assert client.public_transport == "requests"
    finally:
        for session in (client.private, client.public, client.graphql):
            session.close()
