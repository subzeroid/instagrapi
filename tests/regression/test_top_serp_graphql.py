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


def _top_serp_page(*ids, after=None, has_next_page=True):
    items = [
        {
            "__typename": "XDTMediaDict",
            "pk": pk,
            "code": "example",
            "taken_at": 1_700_000_000,
            "media_type": 1,
            "user": {"id": "456", "username": "example"},
        }
        for pk in ids
    ]
    connection = {
        "edges": [{"node": {"__typename": "XDTTopSerpMediaGridUnit", "items": items}}],
        "page_info": {"has_next_page": has_next_page, "end_cursor": after},
    }
    return {"data": {"manual_pagination_query": connection}}


@pytest.mark.parametrize("paginated", [False, True], ids=["first-page", "chunk"])
@pytest.mark.parametrize("on_child", [False, True], ids=["parent-tag", "child-tag"])
@pytest.mark.parametrize(
    "invalid_coordinates",
    [
        {"x": None, "y": None},
        {"position": [0.5, None]},
        {},
        {"position": None},
        {"position": [0.5, "invalid"]},
    ],
    ids=["null-fields", "partial-position", "missing-fields", "null-position", "nonnumeric-position"],
)
def test_top_serp_keeps_carousel_with_invalid_usertag_coordinates(paginated, on_child, invalid_coordinates):
    response = _top_serp_page("123", after="next")
    carousel = response["data"]["manual_pagination_query"]["edges"][0]["node"]["items"][0]
    child = {"id": "124", "media_type": 1}
    carousel.update(media_type=8, carousel_media=[child])
    tagged_item = child if on_child else carousel
    tagged_item["usertags"] = {
        "in": [
            {"user": {"pk": "701", "username": "invalid"}, **invalid_coordinates},
            {"user": {"pk": "702", "username": "valid_position"}, "position": [0.25, 0.75]},
            {"user": {"pk": "703", "username": "valid_fields"}, "x": "0.5", "y": 0.5},
            {"user": {"pk": "704", "username": "fallback_fields"}, "position": None, "x": "0.75", "y": 0},
        ]
    }
    client = Client()
    client.private_graphql_request = Mock(return_value=response)

    if paginated:
        result, cursor = client.media_search_top_gql_chunk("example")
        assert cursor is not None
    else:
        result = client.media_search_top_gql("example")

    assert [media.pk for media in result] == ["123"]
    assert [resource.pk for resource in result[0].resources] == ["124"]
    parsed_item = result[0].resources[0] if on_child else result[0]
    assert [(tag.user.pk, tag.x, tag.y) for tag in parsed_item.usertags] == [
        ("702", 0.25, 0.75),
        ("703", 0.5, 0.5),
        ("704", 0.75, 0.0),
    ]
    assert len(tagged_item["usertags"]["in"]) == 4
    assert tagged_item["usertags"]["in"][-1]["position"] is None


def test_media_search_top_gql_chunk_preserves_search_session_and_filters_duplicates():
    client = Client()
    client.private_graphql_request = Mock(
        side_effect=[
            _top_serp_page("123", "123", after="next"),
            _top_serp_page("123", "124", after="ignored", has_next_page=False),
        ]
    )

    first, cursor = client.media_search_top_gql_chunk("Istanbul")
    assert cursor is not None
    second, next_cursor = client.media_search_top_gql_chunk("Istanbul", cursor)

    assert [media.pk for media in first] == ["123"]
    assert [media.pk for media in second] == ["124"]
    assert next_cursor is None
    first_request, second_request = client.private_graphql_request.call_args_list
    first_variables = json.loads(first_request.args[0]["variables"])
    second_variables = json.loads(second_request.args[0]["variables"])
    assert "after" not in first_variables
    assert first_variables["is_pagination_request"] is False
    assert second_variables == dict(first_variables, after="next", is_pagination_request=True)


@pytest.mark.parametrize("cursors", [("a", "a"), ("a", "b", "a")])
def test_media_search_top_gql_chunk_stops_on_repeated_cursor(cursors):
    client = Client()
    client.private_graphql_request = Mock(side_effect=[_top_serp_page("123", after=after) for after in cursors])

    first, cursor = client.media_search_top_gql_chunk("Istanbul")
    assert first and cursor is not None
    for _ in cursors[1:]:
        media, cursor = client.media_search_top_gql_chunk("Istanbul", cursor)
        assert media == []
    assert cursor is None
    assert client.private_graphql_request.call_count == len(cursors)


def test_media_search_top_gql_chunk_rejects_a_cursor_from_another_query_before_request():
    client = Client()
    client.private_graphql_request = Mock(return_value=_top_serp_page("123", after="next"))
    _, cursor = client.media_search_top_gql_chunk("Istanbul")
    assert cursor is not None

    with pytest.raises(ValueError, match="query"):
        client.media_search_top_gql_chunk("Rome", cursor)
    with pytest.raises(TypeError, match="cursor"):
        client.media_search_top_gql_chunk("Istanbul", "next")
    assert client.private_graphql_request.call_count == 1


@pytest.mark.parametrize("page_info", [None, {}, {"has_next_page": True}, {"has_next_page": True, "end_cursor": 17}])
def test_media_search_top_gql_chunk_requires_usable_page_info(page_info):
    client = Client()
    response = _top_serp_page("123")
    response["data"]["manual_pagination_query"]["page_info"] = page_info
    client.private_graphql_request = Mock(return_value=response)

    page, cursor = client.media_search_top_gql_chunk("Istanbul")

    assert [media.pk for media in page] == ["123"]
    assert cursor is None
