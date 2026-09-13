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


@pytest.mark.parametrize("collection", ["reels", "explore_reels", "friends_reels"])
def test_terminal_page_respects_amount(client, collection):
    client.private_request = request_mock(return_value=page(1, 2, 3))
    assert [m.pk for m in run(client, collection_pk=collection, amount=1)] == ["1"]
    assert client.private_request.call_count == 1


def test_amount_is_enforced_when_next_page_is_terminal(client):
    client.private_request = request_mock(side_effect=[page(1, more=True, cursor="A"), page(2, 3, 4)])
    assert [m.pk for m in run(client, collection_pk="reels", amount=2)] == ["1", "2"]
    assert client.private_request.call_count == 2


def test_amount_is_enforced_before_stop_marker(client):
    client.private_request = request_mock(return_value=page(1, 2, 3, 4))
    assert [m.pk for m in run(client, collection_pk="reels", amount=1, last_media_pk=4)] == ["1"]


def test_media_beyond_amount_is_not_extracted(client, monkeypatch):
    def extract(value):
        assert value["pk"] == 1, "media beyond requested amount must not be parsed"
        return SimpleNamespace(pk="1")

    monkeypatch.setattr("instagrapi.mixins.timeline.extract_media_v1", extract)
    client.private_request = request_mock(return_value=page(1, 2, more=True, cursor="A"))
    assert [m.pk for m in run(client, collection_pk="reels", amount=1)] == ["1"]
    assert client.private_request.call_count == 1


@pytest.mark.parametrize("amount", [0, -1])
def test_nonpositive_amount_does_not_request_a_page(client, amount):
    client.private_request = request_mock()
    assert run(client, collection_pk="reels", amount=amount) == []
    client.private_request.assert_not_called()


def test_partial_results_survive_request_failure(client):
    client.private_request = request_mock(
        side_effect=[page(1, more=True, cursor="A"), RuntimeError("synthetic failure")]
    )
    assert [m.pk for m in run(client, collection_pk="reels", amount=3)] == ["1"]
    assert client.private_request.call_count == 2
