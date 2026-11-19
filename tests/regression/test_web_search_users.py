from unittest.mock import Mock

import pytest

from instagrapi import Client
from instagrapi.exceptions import ClientGraphqlError
from instagrapi.types import UserShort


def _connection(users):
    return {"xdt_api__v1__fbsearch__topsearch_connection": {"users": users}}


def test_web_search_users_uses_browser_contract_and_preserves_order():
    entries = [
        {"position": 2, "user": {"pk": "123", "id": "relay-id", "username": "first", "is_verified": True}},
        {"position": 4, "user": {"id": "456", "username": "second"}},
    ]
    client = Client()
    client.generate_uuid = Mock(return_value="search-uuid")
    client.public_doc_id_graphql_request = Mock(return_value=_connection(entries))

    result = client.web_search_users("dd")

    assert all(isinstance(user, UserShort) for user in result)
    assert [(user.pk, user.username) for user in result] == [("123", "first"), ("456", "second")]
    assert result[0].is_verified is True
    assert entries[0]["user"]["id"] == "relay-id"
    client.public_doc_id_graphql_request.assert_called_once_with(
        "27706427925724183",
        {
            "data": {
                "context": "blended",
                "include_reel": "true",
                "query": "dd",
                "rank_token": "",
                "search_session_id": "search-uuid",
                "search_surface": "web_top_search",
            },
            "hasQuery": True,
        },
        referer="https://www.instagram.com/explore/",
        headers={"X-FB-Friendly-Name": "PolarisSearchBoxRefetchableQuery"},
        url="https://www.instagram.com/api/graphql",
        include_lsd=True,
        include_fb_dtsg=True,
    )


def test_web_search_users_allows_empty_results():
    client = Client()
    client.public_doc_id_graphql_request = Mock(return_value=_connection([]))

    assert client.web_search_users("missing") == []


@pytest.mark.parametrize(
    "body",
    [None, {}, _connection(None), _connection([{}]), _connection([{"user": {"id": "relay-only"}}])],
)
def test_web_search_users_raises_on_malformed_response(body):
    client = Client()
    client.public_doc_id_graphql_request = Mock(return_value=body)

    with pytest.raises(ClientGraphqlError, match="Malformed web account search response"):
        client.web_search_users("dd")


def test_web_search_users_rejects_blank_query_without_network():
    client = Client()
    client.public_doc_id_graphql_request = Mock()

    with pytest.raises(ValueError, match="query"):
        client.web_search_users("  ")

    client.public_doc_id_graphql_request.assert_not_called()
