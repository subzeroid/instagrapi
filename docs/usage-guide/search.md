# Search

Helpers for the Facebook Search (`fbsearch/`) surface — user search, blended top results, hashtag/place lookups, and typeahead suggestions.

## v2 SERP endpoints

The `*_v2` methods hit the same `fbsearch/<tab>_serp/` endpoints the official Instagram app uses to render the Search → Top / Accounts / Reels tabs. They return raw payloads so callers can drive their own pagination.

| Method | Return | Description |
|--------|--------|-------------|
| `fbsearch_accounts_v2(query: str, page_token: str = None)` | `dict` | "Accounts" tab — `fbsearch/account_serp/`. Pagination via `next_page_token`. |
| `fbsearch_reels_v2(query: str, reels_max_id: str = None, rank_token: str = None)` | `dict` | "Reels" tab — `fbsearch/reels_serp/`. |
| `fbsearch_topsearch_v2(query: str, next_max_id: str = None, reels_max_id: str = None, rank_token: str = None)` | `dict` | Default "Top" blended tab — `fbsearch/top_serp/`. |
| `fbsearch_item(item_id: str, search_surface: str, query: str, ...)` | `dict` | Generic `fbsearch/{item_id}/` tab helper with optional pagination cursors. |
| `fbsearch_keyword_typeahead(query: str, timezone_offset: int = 0, count: int = 30)` | `dict` | Raw keyword/typeahead suggestions via `fbsearch/keyword_typeahead/`. |
| `fbsearch_typeahead_stream(query: str, timezone_offset: int = 0, count: int = 30)` | `dict` | Raw streaming typeahead payload via `fbsearch/typeahead_stream/`. |
| `fbsearch_typehead(query: str)` | `List[dict]` | Typeahead user suggestions, flattened from the `stream_rows` envelope returned by `fbsearch/typeahead_stream/`. |
| `media_search(query: str, amount: int = 27)` | `List[Media]` | Typed media search from the private Top blended fbsearch SERP, including media-grid cursor pagination. |
| `media_search_top_gql(query: str, amount: int = 0)` | `List[Media]` | Media from the first page of the mobile Top GraphQL search. `amount=0` returns all media on that page. |
| `media_search_top_gql_chunk(query, cursor=None)` | `Tuple[List[Media], Optional[cursor]]` | One page of mobile Top GraphQL media and a continuation cursor. |

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

# Top media — typed Media objects
medias = cl.media_search("python", amount=3)
top_medias = cl.media_search_top_gql("python", amount=3)
```

Top GraphQL pagination returns media and an opaque cursor. Pass the cursor with the same query and authenticated session. A page can be empty when more pages are available. Stop when the cursor is `None`.

```python
medias, cursor = cl.media_search_top_gql_chunk("python")
while cursor is not None:
    page, cursor = cl.media_search_top_gql_chunk("python", cursor)
    medias.extend(page)
```

`media_search()` raises `PrivateError` when the response omits `media_grid`, returns `null`, or has a malformed grid or sections payload. A valid empty grid still returns `[]`. The exception also propagates on later pages instead of returning partial results. Repeated pagination cursor pairs stop further requests. These checks do not guarantee that Instagram will return search results.

If `media_search()` fails with `Missing media_grid in fbsearch/top_serp response`, use `media_search_top_gql()` for the first page of mobile Top search. To paginate, start a separate search with `media_search_top_gql_chunk(query, cursor=None)`. The original REST response is tracked in [instagrapi #2961](https://github.com/subzeroid/instagrapi/issues/2961).

## Other search helpers

| Method | Return | Description |
|--------|--------|-------------|
| `search_users(query: str)` | `List[UserShort]` | User search via `users/search/`. |
| `search_hashtags(query: str)` | `List[Hashtag]` | Hashtag search via `tags/search/`. |
| `search_music(query: str)` | `List[Track]` | Music/audio search via `music/audio_global_search/`. |
| `fbsearch_topsearch_flat(query: str)` | `List[dict]` | Legacy flat top-search via `fbsearch/topsearch_flat/`. |
| `web_search_users(query: str)` | `List[UserShort]` | Accounts from the web search box through GraphQL with an authenticated session. |
| `web_search_topsearch(query: str)` | `dict` | Raw web top-search payload via `web/search/topsearch/`. |
| `web_search_topsearch_hashtags(query: str)` | `List[Hashtag]` | Extract hashtags from the web top-search payload. |
| `fbsearch_suggested_profiles(user_id: str)` | `List[UserShort]` | Suggested profiles via `fbsearch/accounts_recs/`. |
| `fbsearch_recent()` | `List[Tuple[int, ...]]` | Recently searched items. |

For places, see [Location](location.md).
