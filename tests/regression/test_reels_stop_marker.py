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


@pytest.mark.parametrize("marker", [2, "2"])
@pytest.mark.parametrize("raw_pk", [2, "2"])
def test_stop_marker_matches_string_and_integer_pks(client, marker, raw_pk):
    client.private_request = request_mock(return_value=page("1", raw_pk, "3"))
    assert [m.pk for m in run(client, collection_pk="reels", amount=10, last_media_pk=marker)] == ["1"]
    assert client.private_request.call_count == 1


def test_marker_at_start_returns_no_media(client):
    client.private_request = request_mock(return_value=page("2", "3", more=True, cursor="A"))
    assert run(client, collection_pk="reels", amount=10, last_media_pk=2) == []
    assert client.private_request.call_count == 1


def test_stop_marker_on_later_page_preserves_earlier_results(client):
    client.private_request = request_mock(
        side_effect=[page("1", more=True, cursor="A"), page("2", "3", "4", more=True, cursor="B")]
    )
    assert [m.pk for m in run(client, collection_pk="reels", amount=10, last_media_pk=3)] == ["1", "2"]
    assert client.private_request.call_count == 2


@pytest.mark.parametrize("marker", [0, "0", 99])
def test_disabled_or_absent_marker_returns_all_media(client, marker):
    client.private_request = request_mock(return_value=page("1", "2"))
    assert [m.pk for m in run(client, collection_pk="reels", amount=10, last_media_pk=marker)] == ["1", "2"]


def test_invalid_marker_fails_before_network_request(client):
    client.private_request = request_mock()
    with pytest.raises(ValueError):
        run(client, collection_pk="reels", amount=10, last_media_pk="invalid")
    client.private_request.assert_not_called()
