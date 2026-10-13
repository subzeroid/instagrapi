from unittest.mock import Mock

import pytest

from instagrapi import Client
from instagrapi.utils.iterators import iter_paginated


def build_client(pages):
    client = Client(private_transport="requests")
    client.private_request = Mock(
        side_effect=[
            {
                "users": [{"pk": pk, "username": f"user_{pk}"} for pk in ids],
                "next_max_id": cursor,
            }
            for ids, cursor in pages
        ]
    )
    return client


def collect(iterator):
    return list(iterator)


@pytest.mark.parametrize("relation", ["followers", "following"])
@pytest.mark.parametrize(
    "pages,amount,expected",
    [
        ([([1, 2], "page-2"), ([2, 3], "")], 0, ["1", "2", "3"]),
        ([([1, 2], "page-2"), ([2, 3], "page-3"), ([4], "")], 4, ["1", "2", "3", "4"]),
        ([([1, 2], "page-2"), ([2, 1], "page-3"), ([3, 4], "")], 0, ["1", "2", "3", "4"]),
        ([([1, 2], "page-2"), ([2, 3], "")], 4, ["1", "2", "3"]),
        ([([1, 2], "page-2"), ([2, 3], "page-2")], 0, ["1", "2", "3"]),
        ([([1, 2], "page-2"), ([], "")], 0, ["1", "2"]),
    ],
    ids=["overlap", "unique-amount", "duplicate-only-page", "exhausted", "repeated-cursor", "empty-page"],
)
def test_user_iterators_yield_unique_users(relation, pages, amount, expected):
    client = build_client(pages)
    kwargs = {"amount": amount, "page_size": 2}
    if relation == "followers":
        kwargs["order"] = "date_followed_latest"

    users = collect(getattr(client, f"iter_user_{relation}_v1")("999", **kwargs))

    assert [user.pk for user in users] == expected
    assert client.private_request.call_count == len(pages)
    previous_cursor = ""
    for index, call in enumerate(client.private_request.call_args_list):
        assert call.args == (f"friendships/999/{relation}/",)
        assert call.kwargs["params"].get("max_id", "") == previous_cursor
        if relation == "followers":
            assert call.kwargs["params"]["order"] == "date_followed_latest"
        previous_cursor = pages[index][1]
    if amount == 4 and len(pages) == 3:
        assert [call.kwargs["params"]["count"] for call in client.private_request.call_args_list] == [2, 2, 1]


@pytest.mark.parametrize("relation", ["followers", "following"])
def test_user_iterators_keep_first_seen_user(relation):
    client = build_client([])
    client.private_request.side_effect = [
        {"users": [{"pk": 1, "username": "first"}], "next_max_id": "page-2"},
        {"users": [{"pk": "1", "username": "changed"}, {"pk": 2, "username": "second"}], "next_max_id": ""},
    ]

    users = collect(getattr(client, f"iter_user_{relation}_v1")("999", page_size=1))

    assert [(user.pk, user.username) for user in users] == [("1", "first"), ("2", "second")]


@pytest.mark.parametrize("relation", ["followers", "following"])
def test_user_iterator_deduplication_is_per_invocation(relation):
    pages = [([1, 2], "page-2"), ([2, 3], "")]
    client = build_client(pages * 2)
    method = getattr(client, f"iter_user_{relation}_v1")

    assert [user.pk for user in collect(method("999", page_size=2))] == ["1", "2", "3"]
    assert [user.pk for user in collect(method("999", page_size=2))] == ["1", "2", "3"]


@pytest.mark.parametrize("relation", ["followers", "following"])
def test_user_iterators_remain_lazy(relation):
    client = build_client([([1, 2], "page-2"), ([2, 3], "")])
    iterator = getattr(client, f"iter_user_{relation}_v1")("999", page_size=2)
    client.private_request.assert_not_called()

    assert next(iterator).pk == "1"
    assert next(iterator).pk == "2"
    client.private_request.assert_called_once()
    iterator.close()


def test_default_paginator_preserves_repeated_unhashable_items():
    items = [{"pk": "1"}, {"pk": "1"}]
    fetch = Mock(return_value=(items, ""))

    result = collect(iter_paginated(fetch, page_size=2, initial_cursor=""))

    assert result == items
    fetch.assert_called_once_with("", 2)
