# Search

Helpers for the Facebook Search (`fbsearch/`) surface — user search, blended top results, hashtag/place lookups, and typeahead suggestions.

## v2 SERP endpoints

The `*_v2` methods hit the same `fbsearch/<tab>_serp/` endpoints the official Instagram app uses to render the Search → Top / Accounts / Reels tabs. They return raw payloads so callers can drive their own pagination.

| Method | Return | Description |
|--------|--------|-------------|
| `fbsearch_accounts_v2(query: str, page_token: str = None)` | `dict` | "Accounts" tab — `fbsearch/account_serp/`. Pagination via `next_page_token`. |
| `fbsearch_reels_v2(query: str, reels_max_id: str = None, rank_token: str = None)` | `dict` | "Reels" tab — `fbsearch/reels_serp/`. |
| `fbsearch_topsearch_v2(query: str, next_max_id: str = None, reels_max_id: str = None, rank_token: str = None)` | `dict` | Default "Top" blended tab — `fbsearch/top_serp/`. |
| `fbsearch_typehead(query: str)` | `List[dict]` | Typeahead user suggestions, flattened from the `stream_rows` envelope returned by `fbsearch/typeahead_stream/`. |

Example:

```python
# Top tab — first page
top = cl.fbsearch_topsearch_v2("python")

# Accounts — paginate
page1 = cl.fbsearch_accounts_v2("python")
page2 = cl.fbsearch_accounts_v2("python", page_token=page1["next_page_token"])

# Reels — paginate
page1 = cl.fbsearch_reels_v2("python")
page2 = cl.fbsearch_reels_v2("python", reels_max_id=page1["reels_max_id"])

# Typeahead — flat list of user dicts
users = cl.fbsearch_typehead("py")
```

## Other search helpers

| Method | Return | Description |
|--------|--------|-------------|
| `search_users(query: str)` | `List[UserShort]` | User search via `users/search/`. |
| `search_hashtags(query: str)` | `List[Hashtag]` | Hashtag search via `tags/search/`. |
| `search_music(query: str)` | `List[Track]` | Music/audio search via `music/audio_global_search/`. |
| `fbsearch_topsearch_flat(query: str)` | `List[dict]` | Legacy flat top-search via `fbsearch/topsearch_flat/`. |
| `fbsearch_suggested_profiles(user_id: str)` | `List[UserShort]` | Suggested profiles via `fbsearch/accounts_recs/`. |
| `fbsearch_recent()` | `List[Tuple[int, ...]]` | Recently searched items. |

For places, see [Location](location.md).
