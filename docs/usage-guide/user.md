# User

View a list of a user's medias, following and followers

* `user_id` - Integer ID of user, example `1903424587`

| Method                                        | Return                | Description
| --------------------------------------------- | --------------------- | ---------------------------------------------------------
| user_followers(user_id: int, amount: int = 0) | Dict\[int, UserShort] | Get dict of followers users (amount=0 - fetch all followers)
| user_following(user_id: int, amount: int = 0) | Dict\[int, UserShort] | Get dict of following users (amount=0 - fetch all)
| search_followers(user_id: int, query: str)    | List[UserShort]       | Search by followers
| search_following(user_id: int, query: str)    | List[UserShort]       | Search by following
| user_info(user_id: int)                       | User                  | Get user info
| user_info_by_username(username: str)          | User                  | Get user info by username
| user_follow(user_id: int)                     | bool                  | Follow user
| user_unfollow(user_id: int)                   | bool                  | Unfollow user
| user_id_from_username(username: str)          | int                   | Get user_id by username
| username_from_user_id(user_id: int)           | str                   | Get username by user_id
| user_remove_follower(user_id: int)            | bool                  | Remove your follower
| mute_posts_from_follow(user_id: int)          | bool                  | Mute posts from following user
| unmute_posts_from_follow(user_id: int)        | bool                  | Unmute posts from following user
| mute_stories_from_follow(user_id: int)        | bool                  | Mute stories from following user
| unmute_stories_from_follow(user_id: int)      | bool                  | Unmute stories from following user

Low level methods:

| Method                                            | Return          | Description
| ------------------------------------------------- | --------------- | ---------------------------------------------------------
| user_followers_gql_chunk(user_id: int, max_amount: int = 0, end_cursor: str = None) | Tuple[List[UserShort], str] | Get user's followers information by Public Graphql API and end_cursor
| user_followers_gql(user_id: int, amount: int = 0) | List[UserShort] | Get user's followers information by Public Graphql API
| user_followers_v1_chunk(user_id: int, max_amount: int = 0, max_id: str = "") | Tuple[List[UserShort], str] | Get user's followers information by Private Mobile API and max_id (cursor)
| user_followers_v1(user_id: int, amount: int = 0)  | List[UserShort] | Get user's followers information by Private Mobile API
| user_following_v1(user_id: int, amount: int = 0)  | List[UserShort] | Get user's following users information by Private Mobile API
| user_following_gql(user_id: int, amount: int = 0) | List[UserShort] | Get user's following information by Public Graphql API
| search_followers_v1(user_id: int, query: str)     | List[UserShort] | Search by followers by Private Mobile API
| search_following_v1(user_id: int, query: str)     | List[UserShort] | Search by following by Private Mobile API

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

>>> cl.user_info_by_username('adw0rd').dict()
{'pk': 1903424587,
 'username': 'adw0rd',
 'full_name': 'Mikhail Andreev',
 'is_private': False,
 'profile_pic_url': HttpUrl('https://scontent-hel3-1.cdninstagram.com/v/t51.2885-19/s150x150/123884060_803537687159702_2508263208740189974_n.jpg?...', scheme='https', host='scontent-hel3-1.cdninstagram.com', tld='com', host_type='domain', ...'),
 'is_verified': False,
 'media_count': 102,
 'follower_count': 576,
 'following_count': 538,
 'biography': 'Engineer: Python, JavaScript, Erlang',
 'external_url': HttpUrl('https://adw0rd.com/', scheme='https', host='adw0rd.com', tld='com', host_type='domain', path='/'),
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
