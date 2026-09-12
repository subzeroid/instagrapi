"""Reels feeds can carry media in items_with_ads instead of legacy items."""

from unittest.mock import Mock

import pytest

from instagrapi import Client


def media(pk):
    pk = str(pk)
    code = f"code{pk}"
    return {
        "media": {
            "pk": pk,
            "id": f"{pk}_1",
            "code": code,
            "taken_at": 1710000000,
            "media_type": 2,
            "caption": {"text": "caption"},
            "user": {"pk": "1", "username": "example", "profile_pic_url": "https://example.com/profile.jpg"},
            "like_count": 0,
            "video_versions": [{"url": "https://example.com/video.mp4", "width": 720, "height": 1280}],
            "image_versions2": {
                "candidates": [{"url": "https://example.com/thumbnail.jpg", "width": 720, "height": 1280}]
            },
        }
    }


@pytest.mark.parametrize("collection", ["reels", "explore_reels", "friends_reels"])
@pytest.mark.parametrize("legacy", [{}, {"items": []}])
def test_modern_reels_returns_first_media_without_requesting_another_page(collection, legacy):
    client = Client()
    client.logger = Mock()
    client.private_request = Mock(
        side_effect=[
            {
                **legacy,
                "items_with_ads": [media(1), media(2)],
                "paging_info": {"more_available": True, "max_id": "next-page"},
            }
        ]
    )

    result = client.reels_timeline_media(collection, amount=1)

    assert [item.pk for item in result] == ["1"]
    assert client.private_request.call_count == 1


def test_nonempty_legacy_items_keep_priority_when_both_lists_are_present():
    client = Client()
    client.private_request = Mock(
        return_value={
            "items": [media(1)],
            "items_with_ads": [media(2)],
            "paging_info": {"more_available": False},
        }
    )

    assert [item.pk for item in client.explore_reels(amount=10)] == ["1"]
    assert client.private_request.call_count == 1


def test_modern_reels_skips_non_media_wrappers_and_preserves_order():
    client = Client()
    client.private_request = Mock(
        return_value={
            "items": [],
            "items_with_ads": [media(1), {"ad": {"id": "synthetic"}}, {"media": None}, media(2)],
            "paging_info": {"more_available": False},
        }
    )

    assert [item.pk for item in client.explore_reels(amount=10)] == ["1", "2"]


def test_modern_reels_preserves_server_cursor_between_pages():
    client = Client()
    client.private_request = Mock(
        side_effect=[
            {"items": [], "items_with_ads": [media(1)], "paging_info": {"more_available": True, "max_id": "next-page"}},
            {"items_with_ads": [media(2)], "paging_info": {"more_available": False}},
        ]
    )

    assert [item.pk for item in client.explore_reels(amount=10)] == ["1", "2"]
    assert [call.kwargs["params"]["max_id"] for call in client.private_request.call_args_list] == ["", "next-page"]


def test_empty_modern_and_legacy_lists_return_no_media():
    client = Client()
    client.private_request = Mock(
        return_value={"items": [], "items_with_ads": [], "paging_info": {"more_available": False}}
    )

    assert client.explore_reels(amount=10) == []
    assert client.private_request.call_count == 1


def test_modern_reels_preserves_existing_integer_stop_marker():
    client = Client()
    stop_item = media(2)
    stop_item["media"]["pk"] = 2
    client.private_request = Mock(
        return_value={
            "items": [],
            "items_with_ads": [media(1), stop_item, media(3)],
            "paging_info": {"more_available": False},
        }
    )

    assert [item.pk for item in client.explore_reels(amount=10, last_media_pk=2)] == ["1"]
    assert client.private_request.call_count == 1
