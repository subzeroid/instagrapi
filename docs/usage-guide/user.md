# User

View a list of a user's medias, following and followers

* `user_id` - Integer ID of user, example `1903424587`

| Method                                        | Return                | Description                                                  |
|-----------------------------------------------|-----------------------|--------------------------------------------------------------|
| user_followers(user_id: str, amount: int = 0) | Dict\[int, UserShort] | Get dict of followers users (amount=0 - fetch all followers) |
| user_following(user_id: str, amount: int = 0) | Dict\[int, UserShort] | Get dict of following users (amount=0 - fetch all)           |
| search_followers(user_id: str, query: str)    | List[UserShort]       | Search by followers                                          |
| search_following(user_id: str, query: str)    | List[UserShort]       | Search by following                                          |
| user_info(user_id: str)                       | User                  | Get user info                                                |
| user_info_by_username(username: str)          | User                  | Get user info by username                                    |
| user_about_v1(user_id: str)                   | About                 | Get "About this account" info                                |
| user_guides_v1(user_id: int)                  | List[Guide]           | Get user's guides                                            |
| user_follow(user_id: str)                     | bool                  | Follow user                                                  |
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
| user_followers_v1_chunk(user_id: str, max_amount: int = 0, max_id: str = "")        | Tuple[List[UserShort], str] | Get user's followers information by Private Mobile API and max_id (cursor) |
| user_followers_v1(user_id: str, amount: int = 0)                                    | List[UserShort]             | Get user's followers information by Private Mobile API                     |
| user_following_v1(user_id: str, amount: int = 0)                                    | List[UserShort]             | Get user's following users information by Private Mobile API               |
| user_follow_requests_chunk(max_amount: int = 0, max_id: str = "")                   | Tuple[List[UserShort], str] | Get pending incoming follow requests by Private Mobile API and max_id      |
| user_following_gql(user_id: str, amount: int = 0)                                   | List[UserShort]             | Get user's following information by Public Graphql API                     |
| search_followers_v1(user_id: str, query: str)                                       | List[UserShort]             | Search by followers by Private Mobile API                                  |
| search_following_v1(user_id: str, query: str)                                       | List[UserShort]             | Search by following by Private Mobile API                                  |
| user_info_by_username_a1(username: str)                                             | dict                        | Raw public A1 username payload                                             |
| user_info_v2_gql(user_id: str)                                                      | User                        | Profile lookup through current doc_id GraphQL                              |
| user_info_by_username_v2_gql(username: str)                                         | User                        | Resolve username through doc_id search, then fetch profile                 |
| private_graphql_followers_list(user_id: str, rank_token: str, ...)                  | dict                        | Raw private mobile GraphQL followers list                                  |
| private_graphql_following_list(user_id: str, rank_token: str, ...)                  | dict                        | Raw private mobile GraphQL following list                                  |
| private_graphql_clips_profile(target_user_id: str, ...)                             | dict                        | Raw private mobile GraphQL profile Reels stream                            |
| private_graphql_inbox_tray_for_user(user_id: str, ...)                              | dict                        | Raw private mobile GraphQL inbox tray query                                |

The batch follow request helpers call the single-user approve/decline endpoints for
each `user_id`; they do not implement an auto-approval policy.

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

Example: We go around the list of our followers and unfollow from them:

``` python
from instagrapi import Client
cl = Client()
cl.login(USERNAME, PASSWORD)

followers = cl.user_followers(cl.user_id)
for user_id in followers.keys():
    cl.user_unfollow(user_id)
```

Tip:

* `user_info_by_username()` and other high-level user helpers may internally fall back between web/public and private paths depending on what Instagram currently accepts for the session.
