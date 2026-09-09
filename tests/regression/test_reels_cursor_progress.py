"""Bounded regression tests for Reels pagination."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from instagrapi import Client


@pytest.fixture
def client(monkeypatch):
    client = Client()
    client.logger = Mock()
    monkeypatch.setattr(
        "instagrapi.mixins.timeline.extract_media_v1", lambda value: SimpleNamespace(pk=str(value["pk"]))
    )
    return client


def page(*pks, more=False, cursor=""):
    return {"items": [{"media": {"pk": pk}} for pk in pks], "paging_info": {"more_available": more, "max_id": cursor}}


def run(client, **kwargs):
    return client.reels_timeline_media(**kwargs)


def request_mock(**kwargs):
    return Mock(**kwargs)


@pytest.mark.parametrize(
    "paging",
    [{"more_available": True}, {"more_available": True, "max_id": ""}, {"more_available": True, "max_id": None}],
)
def test_missing_cursor_stops_before_another_request(client, paging):
    response = page(1)
    response["paging_info"] = paging
    client.private_request = request_mock(side_effect=[response, AssertionError("unexpected extra request")])
    assert [m.pk for m in run(client, collection_pk="reels", amount=10)] == ["1"]
    assert client.private_request.call_count == 1


@pytest.mark.parametrize("pks", [(), (2,)])
def test_unchanged_cursor_stops_on_empty_or_nonempty_page(client, pks):
    client.private_request = request_mock(
        side_effect=[
            page(1, more=True, cursor="A"),
            page(*pks, more=True, cursor="A"),
            AssertionError("unexpected repeated cursor"),
        ]
    )
    assert [m.pk for m in run(client, collection_pk="reels", amount=10)] == ["1", *map(str, pks)]
    assert client.private_request.call_count == 2


def test_cursor_cycle_is_not_requested_again(client):
    client.private_request = request_mock(
        side_effect=[
            page(1, more=True, cursor="A"),
            page(2, more=True, cursor="B"),
            page(3, more=True, cursor="A"),
            AssertionError("unexpected cycle"),
        ]
    )
    assert [m.pk for m in run(client, collection_pk="reels", amount=10)] == ["1", "2", "3"]
    assert client.private_request.call_count == 3
    assert [call.kwargs["params"]["max_id"] for call in client.private_request.call_args_list] == ["", "A", "B"]


def test_empty_page_with_new_cursor_still_advances(client):
    client.private_request = request_mock(
        side_effect=[page(more=True, cursor="A"), page(1, more=True, cursor="B"), page(2)]
    )
    assert [m.pk for m in run(client, collection_pk="reels", amount=10)] == ["1", "2"]
    assert [call.kwargs["params"]["max_id"] for call in client.private_request.call_args_list] == ["", "A", "B"]


def test_terminal_page_does_not_follow_cursor(client):
    client.private_request = request_mock(return_value=page(1, cursor="unused"))
    assert [m.pk for m in run(client, collection_pk="reels", amount=10)] == ["1"]
    assert client.private_request.call_count == 1
