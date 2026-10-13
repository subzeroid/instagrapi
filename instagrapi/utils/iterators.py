from collections.abc import Callable, Hashable, Iterator, Sequence
from typing import TypeVar

T = TypeVar("T")
Cursor = str | None
PageFetcher = Callable[[Cursor, int], tuple[Sequence[T], Cursor]]


def iter_paginated(
    fetch_page: PageFetcher[T],
    amount: int = 0,
    page_size: int = 0,
    initial_cursor: Cursor = None,
    *,
    item_key: Callable[[T], Hashable] | None = None,
) -> Iterator[T]:
    amount = int(amount)
    page_size = int(page_size)
    cursor = initial_cursor
    yielded = 0
    seen: set[Hashable] = set()

    while True:
        page_amount = page_size
        if amount:
            remaining = amount - yielded
            if remaining <= 0:
                return
            page_amount = min(page_size, remaining) if page_size else remaining

        items, next_cursor = fetch_page(cursor, page_amount)
        if not items:
            return

        for item in items:
            if amount and yielded >= amount:
                return
            if item_key is not None:
                key = item_key(item)
                if key in seen:
                    continue
                seen.add(key)
            yield item
            yielded += 1

        if not next_cursor or next_cursor == cursor:
            return
        cursor = next_cursor
