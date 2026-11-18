import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from instagrapi import Client
from instagrapi.exceptions import PrivateError


def test_top_serp_graphql_merges_batched_edges_and_deferred_items():
    root = "manual_pagination_query"
    grid = [root, "edges", 1, "node"]
    frames = [
        {"data": {root: {"edges": [{"node": {"__typename": "XDTTopSerpHeaderUnit"}}]}}},
        [
            {
                "path": [root, "edges", 1],
                "data": {"node": {"__typename": "XDTTopSerpMediaGridUnit", "items": [{}, {}]}},
            },
            {"path": [root, "edges", 2], "data": {"node": {"__typename": "XDTTopSerpAccountsHCMUnit"}}},
        ],
        {"path": grid + ["items", 1], "data": {"__typename": "XDTMediaDict", "pk": "12"}},
        {"path": grid + ["items", 0], "data": {"__typename": "XDTMediaDict", "pk": "11"}},
        {"path": [root], "data": {"page_info": {"has_next_page": False}}},
    ]
    text = "\n".join(json.dumps(frame) for frame in frames)
    response = SimpleNamespace(text=text, json=lambda: json.loads(text))

    body = Client()._json_from_graphql_response(response)

    connection = body["data"][root]
    assert len(connection["edges"]) == 3
    assert [item["pk"] for item in connection["edges"][1]["node"]["items"]] == ["11", "12"]
    assert connection["page_info"] == {"has_next_page": False}


def test_media_search_top_gql_uses_first_page_of_typed_grid_items():
    grid_media = {
        "__typename": "XDTMediaDict",
        "id": "123",
        "pk": None,
        "code": "example",
        "taken_at": 1_700_000_000,
        "media_type": 1,
        "user": {"id": "456", "username": "example"},
    }
    connection = {
        "edges": [
            {"node": {"__typename": "XDTTopSerpAccountsHCMUnit", "items": [grid_media]}},
            {"node": {"__typename": "XDTTopSerpMediaGridUnit", "items": [grid_media]}},
        ]
    }
    client = Client()
    client.private_graphql_request = Mock(return_value={"data": {"manual_pagination_query": connection}})

    result = client.media_search_top_gql("Istanbul", amount=1)

    assert [(media.pk, media.id, media.user.pk) for media in result] == [("123", "123_456", "456")]
    client.private_graphql_request.assert_called_once()
    form = client.private_graphql_request.call_args.args[0]
    assert form["fb_api_req_friendly_name"] == "TopSerpQuery"
    assert form["client_doc_id"] == "418531681916451609839969517761"
    variables = json.loads(form["variables"])
    assert variables["query"] == "Istanbul"
    assert variables["search_surface"] == "TOP_SERP"
    assert variables["is_pagination_request"] is False
    assert variables["is_incremental_delivery_enabled"] is False
    assert variables["is_page_info_fetched_in_separate_chunk"] is True
    assert (
        client.private_graphql_request.call_args.kwargs["headers"]["X-Root-Field-Name"]
        == "xdt_fbsearch__top_serp_graphql"
    )
    assert grid_media["pk"] is None


def test_media_search_top_gql_preserves_distinct_media_and_carousel_resources():
    first = {
        "__typename": "XDTMediaDict",
        "id": "123",
        "code": "example",
        "taken_at": 1_700_000_000,
        "media_type": 1,
        "user": {"id": None, "pk": "456", "username": "example"},
    }
    bad = dict(first, id="124", image_versions2={"candidates": []})
    second = dict(first, id="125", media_type=8, carousel_media=[{"id": "126", "media_type": 1}])
    edges = [
        {"node": {"__typename": "XDTTopSerpMediaGridUnit", "items": [item]}} for item in [bad, first, first, second]
    ]
    client = Client()
    client.private_graphql_request = Mock(return_value={"data": {"manual_pagination_query": {"edges": edges}}})

    result = client.media_search_top_gql("Istanbul", amount=2)

    assert [media.pk for media in result] == ["123", "125"]
    assert result[1].resources[0].pk == "126"
    assert first["user"]["id"] is None
    assert "pk" not in second["carousel_media"][0]


@pytest.mark.parametrize("data", [["unexpected"], {"manual_pagination_query": ["unexpected"]}])
def test_media_search_top_gql_rejects_malformed_response_containers(data):
    client = Client()
    client.private_graphql_request = Mock(return_value={"data": data})

    with pytest.raises(PrivateError, match="Missing TopSerpQuery edges"):
        client.media_search_top_gql("Istanbul")
