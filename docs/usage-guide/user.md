# User

View a list of a user's medias, following and followers

* `user_id` - Integer ID of user, example `1903424587`

| Method                                        | Return                | Description                                                  |
|-----------------------------------------------|-----------------------|--------------------------------------------------------------|
| user_followers(user_id: str, amount: int = 0, order: str = None) | Dict\[int, UserShort] | Get dict of followers users (amount=0 - fetch all followers). Use `order="date_followed_latest"` or `order="date_followed_earliest"` for mobile follower sorting |
| user_following(user_id: str, amount: int = 0) | Dict\[int, UserShort] | Get dict of following users (amount=0 - fetch all)           |
| iter_user_followers_v1(user_id: str, amount: int = 0, page_size: int = 200, order: str = None) | Iterator[UserShort] | Stream followers from the private/mobile API without building a full dict |
| iter_user_following_v1(user_id: str, amount: int = 0, page_size: int = 200) | Iterator[UserShort] | Stream following users from the private/mobile API without building a full dict |
| search_followers(user_id: str, query: str)    | List[UserShort]       | Search by followers                                          |
| search_following(user_id: str, query: str)    | List[UserShort]       | Search by following                                          |
| user_info(user_id: str)                       | User                  | Get user info                                                |
| user_info_by_username(username: str)          | User                  | Get user info by username                                    |
| user_about_v1(user_id: str)                   | About                 | Get "About this account" info                                |
| user_guides_v1(user_id: int)                  | List[Guide]           | Get user's guides                                            |
| user_follow(user_id: str)                     | bool                  | Follow user, or request to follow a private user             |
| user_unfollow(user_id: str)                   | bool                  | Unfollow user                                                |
| user_follow_requests(amount: int = 0)         | List[UserShort]       | Get pending incoming follow requests                         |
| user_follow_request_approve(user_id: str)     | bool                  | Approve a pending incoming follow request                    |
| user_follow_request_decline(user_id: str)     | bool                  | Decline a pending incoming follow request                    |
| user_follow_requests_approve(user_ids: List[str]) | Dict[str, bool]  | Approve pending incoming follow requests                     |
| user_follow_requests_decline(user_ids: List[str]) | Dict[str, bool]  | Decline pending incoming follow requests                     |
| user_id_from_username(username: str)          | int                   | Get user_id by username                                      |
| username_from_user_id(user_id: str)           | str                   | Get username by user_id                                      |
| user_remove_follower(user_id: str)            | bool                  | Remove your follower                                         |
| mute_posts_from_follow(user_id: str)          | bool                  | Mute posts from following user                               |
| unmute_posts_from_follow(user_id: str)        | bool                  | Unmute posts from following user                             |
| mute_stories_from_follow(user_id: str)        | bool                  | Mute stories from following user                             |
| enable_posts_notifications(user_id: str)      | bool                  | Enable post notifications of user                            |
| disable_posts_notifications(user_id: str)     | bool                  | Disable post notifications of user                           |
| enable_videos_notifications(user_id: str)     | bool                  | Enable videos notifications of user                          |
| disable_videos_notifications(user_id: str)    | bool                  | Disable videos notifications of user                         |
| enable_reels_notifications(user_id: str)      | bool                  | Enable reels notifications of user                           |
| disable_reels_notifications(user_id: str)     | bool                  | Disable reels notifications of user                          |
| enable_stories_notifications(user_id: str)    | bool                  | Enable stories notifications of user                         |
| disable_stories_notifications(user_id: str)   | bool                  | Disable stories notifications of user                        |
| close_friend_add(user_id: str)                | bool                  | Add to Close Friends List                                    |
| close_friend_remove(user_id: str)             | bool                  | Remove from Close Friends List                               |
| user_suggested_profiles(user_id: str, expand_suggestion: bool = False) | dict | Suggested profiles ("Suggested for you") for a profile. Wraps `chaining` and, with `expand_suggestion=True`, returns the raw `fetch_suggestion_details` payload (`items` in current app responses) |
| address_book_link(contacts: List[AddressBookContact \| dict], include: Sequence[str] \| str = ("extra_display_name", "thumbnails")) | dict | Upload/link address book contacts and return Instagram's raw contact-based suggestions response |
| address_book_unlink()                         | dict                  | Disconnect the uploaded address book from the current account |
| chaining(user_id: str)                        | dict                  | Suggested users for a profile (`discover/chaining/`) — same surface as the app's "Suggested for you" carousel |
| fetch_suggestion_details(user_id: str, chained_ids: str) | dict       | Expanded social-context fields for chained suggestion ids (`discover/fetch_suggestion_details/`) |
| discover_recommended_accounts_for_category_v1(user_id: str) | dict | Business-category-similar accounts: extracts `category_id` from the target's stream payload, then calls `discover/recommended_accounts_for_category/` |
| user_related_profiles_gql(user_id: str)       | List[UserShort]       | Related profiles via public GraphQL `edge_chaining` (legacy `query_hash`, gated by IG — prefer `chaining` for reliability) |

Lookup helpers:

| Method                                        | Return                | Description                                                  |
|-----------------------------------------------|-----------------------|--------------------------------------------------------------|
| user_short_gql(user_id: str, use_cache: bool = True) | UserShort      | Short user info with current GraphQL/web-profile fallback chain |
| username_from_user_id_gql(user_id: str)       | str                   | Resolve username from user id using the same fallback chain  |

Streamed profile fetch (raw payloads, app-side surface):

| Method                                        | Return                | Description                                                  |
|-----------------------------------------------|-----------------------|--------------------------------------------------------------|
| user_stream_by_id_v1(user_id: str)            | dict                  | Streamed profile envelope by pk (`users/{user_id}/info_stream/`) |
| user_stream_by_username_v1(username: str)     | dict                  | Streamed profile envelope by username (`users/{username}/usernameinfo_stream/`) |
| user_stream_by_id_flat(user_id: str)          | dict                  | Same as `_v1` but `stream_rows[*].user` partials merged into a single dict |
| user_stream_by_username_flat(username: str)   | dict                  | Same as `_v1` but `stream_rows[*].user` partials merged into a single dict |
| user_web_profile_info_v1(username: str)       | dict                  | `users/web_profile_info/?username=...` via the private host (logged-in session, bypasses public-side rate limiting) |
| feed_user_stream_item(item_id: str, is_pull_to_refresh: bool = False) | dict | Raw streamed feed payload for a user/profile grid item |

Low level methods:

| Method                                                                              | Return                      | Description                                                                |
|-------------------------------------------------------------------------------------|-----------------------------|----------------------------------------------------------------------------|
| user_followers_gql_chunk(user_id: str, max_amount: int = 0, end_cursor: str = None) | Tuple[List[UserShort], str] | Get user's followers information by Public Graphql API and end_cursor      |
| user_followers_gql(user_id: str, amount: int = 0)                                   | List[UserShort]             | Get user's followers information by Public Graphql API                     |
| user_followers_v1_chunk(user_id: str, max_amount: int = 0, max_id: str = "", order: str = None) | Tuple[List[UserShort], str] | Get user's followers information by Private Mobile API and max_id (cursor). Supports `date_followed_latest` and `date_followed_earliest` |
| user_followers_v1(user_id: str, amount: int = 0, order: str = None)                 | List[UserShort]             | Get user's followers information by Private Mobile API. Supports `date_followed_latest` and `date_followed_earliest` |
| iter_user_followers_v1(user_id: str, amount: int = 0, page_size: int = 200, order: str = None) | Iterator[UserShort] | Stream followers page by page through `user_followers_v1_chunk()` |
| user_followers_private_gql_chunk(user_id: str, max_amount: int = 0, max_id: str = None, rank_token: str = None, order: str = None) | Tuple[List[UserShort], str] | Get user's followers through the private mobile GraphQL `FollowersList` surface and max_id cursor |
| user_followers_private_gql(user_id: str, amount: int = 0, rank_token: str = None, order: str = None) | List[UserShort] | Get user's followers through the private mobile GraphQL `FollowersList` surface |
| user_following_v1(user_id: str, amount: int = 0)                                    | List[UserShort]             | Get user's following users information by Private Mobile API               |
| iter_user_following_v1(user_id: str, amount: int = 0, page_size: int = 200)         | Iterator[UserShort]          | Stream following users page by page through `user_following_v1_chunk()` |
| user_follow_requests_chunk(max_amount: int = 0, max_id: str = "")                   | Tuple[List[UserShort], str] | Get pending incoming follow requests by Private Mobile API and max_id      |
| user_following_gql(user_id: str, amount: int = 0)                                   | List[UserShort]             | Get user's following information by Public Graphql API                     |
| search_followers_v1(user_id: str, query: str)                                       | List[UserShort]             | Search by followers by Private Mobile API                                  |
| search_following_v1(user_id: str, query: str)                                       | List[UserShort]             | Search by following by Private Mobile API                                  |
| user_info_v2_gql(user_id: str)                                                      | User                        | Profile lookup through current doc_id GraphQL                              |
| user_info_by_username_v2_gql(username: str)                                         | User                        | Resolve username through doc_id search, then fetch profile                 |
| private_graphql_followers_list(user_id: str, rank_token: str, ..., order: str = None) | dict                      | Raw private mobile GraphQL followers list. Supports `date_followed_latest` and `date_followed_earliest` |
| private_graphql_following_list(user_id: str, rank_token: str, ..., order: str = None) | dict                      | Raw private mobile GraphQL following list. Supports mobile `order` when accepted by Instagram |
| private_graphql_clips_profile(target_user_id: str, ...)                             | dict                        | Raw private mobile GraphQL profile Reels stream                            |
| private_graphql_inbox_tray_for_user(user_id: str, ...)                              | dict                        | Raw private mobile GraphQL inbox tray query                                |

The batch follow request helpers call the single-user approve/decline endpoints for
each `user_id`; they do not implement an auto-approval policy.

`user_follow()` returns `True` only when it sends a new follow action and Instagram reports either an immediate follow or a new outgoing follow request for a private account. It returns `False` when the current account already follows the target or already has a pending outgoing follow request. Use `user_friendship_v1()` when you need to distinguish `following` from `outgoing_request`.

`UserShort` objects returned from private GraphQL follow-list payloads preserve selected v2-only fields when Instagram sends them: `friendship_status`, `profile_pic_id`, `fbid_v2`, `interop_messaging_user_fbid`, `strong_id__`, and raw `account_badges`. The legacy `latest_reel_media` property is also populated from Instagram's current `1llatest_reel_media` key.

Example:

``` python
>>> cl.user_followers(cl.user_id).keys()
dict_keys([5563084402, 43848984510, 1498977320, ...])

>>> cl.user_following(cl.user_id)
{
  8530498223: UserShort(
    pk=8530498223,
    username="something",
    full_name="Example description",
    profile_pic_url=HttpUrl(
      'https://instagram.frix7-1.fna.fbcdn.net/v/t5...9217617140_n.jpg',
      scheme='https',
      host='instagram.frix7-1.fna.fbcdn.net',
      ...
    ),
  ),
  49114585: UserShort(
    pk=49114585,
    username='gx1000',
    full_name='GX1000',
    profile_pic_url=HttpUrl(
      'https://scontent-hel3-1.cdninstagram.com/v/t51.2885-19/10388...jpg',
      scheme='https',
      host='scontent-hel3-1.cdninstagram.com',
      ...
    )
  ),
  ...
}

>>> cl.user_info_by_username('example').dict()
{'pk': 1903424587,
 'username': 'example',
 'full_name': 'Example Example',
 'is_private': False,
 'profile_pic_url': HttpUrl('https://scontent-hel3-1.cdninstagram.com/v/t51.2885-19/s150x150/123884060_803537687159702_2508263208740189974_n.jpg?...', scheme='https', host='scontent-hel3-1.cdninstagram.com', tld='com', host_type='domain', ...'),
 'is_verified': False,
 'media_count': 102,
 'follower_count': 576,
 'following_count': 538,
 'biography': 'Engineer: Python, JavaScript, Erlang',
 'external_url': HttpUrl('https://example.org/', scheme='https', host='example.org', tld='com', host_type='domain', path='/'),
 'is_business': False}

```

Sorted followers:

``` python
latest_followers = cl.user_followers(cl.user_id, amount=50, order="date_followed_latest")
earliest_followers = cl.user_followers_v1(cl.user_id, amount=50, order="date_followed_earliest")
```

Streaming followers/following:

``` python
for follower in cl.iter_user_followers_v1(cl.user_id, amount=1000, page_size=100, order="date_followed_latest"):
    print(follower.pk, follower.username)

for user in cl.iter_user_following_v1(cl.user_id, amount=1000, page_size=100):
    print(user.pk, user.username)
```

Raw private GraphQL helpers expose the same mobile `order` variable for callers that need the `FollowersList`/`FollowingList` payload directly:

``` python
payload = cl.private_graphql_followers_list(cl.user_id, cl.rank_token, order="date_followed_latest")
```

Use `user_followers_private_gql()` when you want the current mobile GraphQL followers list parsed into `UserShort` objects:

``` python
followers = cl.user_followers_private_gql(cl.user_id, amount=50, order="date_followed_latest")
```

Example: We go around the list of our followers and unfollow from them:

``` python
from instagrapi import Client
cl = Client()
cl.login(USERNAME, PASSWORD)

followers = cl.user_followers(cl.user_id)
for user_id in followers.keys():
    cl.user_unfollow(user_id)
```

Example: Suggested profiles ("Suggested for you") for a target user:

``` python
from instagrapi import Client
from instagrapi.exceptions import InvalidTargetUser

cl = Client()
cl.login(USERNAME, PASSWORD)

user_id = cl.user_id_from_username("example")
try:
    suggested = cl.user_suggested_profiles(user_id)
    # Expanded social-context fields (current app responses expose them under "items"):
    detailed = cl.user_suggested_profiles(user_id, expand_suggestion=True)
except InvalidTargetUser:
    # Instagram refuses chaining for locked-down / private targets
    suggested = {"users": []}
```

Tip:

* `user_info()`, `user_info_by_username()`, `user_id_from_username()`, and `username_from_user_id()` use private/mobile lookup first when the client has authorization data or a saved `sessionid`, then fall back to public/web lookup. Without authorization, these high-level helpers keep the public/web-first behavior. Explicit `_gql` methods still call the public/web path directly.
* `user_followers()` and `user_following()` use private/mobile lookup first when the client has authorization data or a saved `sessionid`, then fall back to public/web lookup. Without authorization, these high-level helpers keep the public/web-first behavior. Explicit `_gql` methods still call the public/web path directly.
* Use `iter_user_followers_v1()` and `iter_user_following_v1()` when you need to process large follow lists incrementally instead of keeping the full result in memory.
