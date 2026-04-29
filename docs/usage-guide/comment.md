# Comment

Post comment, viewing, like and unlike comments

| Method | Return | Description |
| --- | --- | --- |
| media_comment(media_id: str, text: str, replied_to_comment_id: Optional[int] = None) | Comment | Add a new comment to media or reply to an existing comment |
| media_comments(media_id: str, amount: int = 20) | List\[Comment] | Get comments for media; pass `amount=0` to keep paginating until exhaustion |
| media_comments_chunk(media_id: str, max_amount: int, min_id: str = None) | Tuple[List\[Comment], str] | Get a paginated chunk of comments and the next `min_id` cursor |
| media_check_offensive_comment(media_id: str, text: str) | bool | Ask Instagram whether a comment text is considered offensive |
| media_check_offensive_comment_v2(media_id: str, comment: str) | dict | Lighter variant of `media_check_offensive_comment` — same endpoint without `with_action_data` wrapping; returns the raw payload so callers can inspect category / confidence flags beyond `is_offensive` |
| comment_like(comment_pk: int, revert: bool = False) | bool | Like a comment |
| comment_unlike(comment_pk: int) | bool | Unlike a comment |
| comment_pin(media_id: str, comment_pk: int, revert: bool = False) | bool | Pin a comment on your media |
| comment_unpin(media_id: str, comment_pk: int) | bool | Unpin a previously pinned comment |
| comment_bulk_delete(media_id: str, comment_pks: List[int]) | bool | Delete one or more comments from your media |


Example:

``` python
>>> from instagrapi import Client

>>> cl = Client()
>>> cl.login(USERNAME, PASSWORD)

>>> media_id = cl.media_id(cl.media_pk_from_url('https://www.instagram.com/p/ByU3LAslgWY/'))

>>> comment = cl.media_comment(media_id, "Test comment")
>>> comment.dict()
{'pk': 17926777897585108,
 'text': 'Test comment',
 'user': {'pk': 1903424587,
  'username': 'example',
  'full_name': 'Example Example',
  'profile_pic_url': HttpUrl('https://scontent-hel3-1.cdninstagram.com/v/t51.2885-19/s150x150/156689363_269505058076642_6448820957073669709_n.jpg?tp=1&_nc_ht=scontent-hel3-1.cdninstagram.com&_nc_ohc=EtzrL0pAdg8AX9pE_wN&edm=ABQSlwABAAAA&ccb=7-4&oh=e04d45b7651140e7fef61b1f67f1f408&oe=60C65AD1&_nc_sid=b2b2bd', scheme='https', host='scontent-hel3-1.cdninstagram.com', tld='com', host_type='domain', path='/v/t51.2885-19/s150x150/156689363_269505058076642_6448820957073669709_n.jpg', query='tp=1&_nc_ht=scontent-hel3-1.cdninstagram.com&_nc_ohc=EtzrL0pAdg8AX9pE_wN&edm=ABQSlwABAAAA&ccb=7-4&oh=e04d45b7651140e7fef61b1f67f1f408&oe=60C65AD1&_nc_sid=b2b2bd'),
  'stories': []},
 'created_at_utc': datetime.datetime(2021, 5, 15, 14, 50, 3, tzinfo=datetime.timezone.utc),
 'content_type': 'comment',
 'status': 'Active',
 'has_liked': None,
 'like_count': None}

>>> comment = cl.media_comment(media_id, "Test comment 2", replied_to_comment_id=comment.pk)
>>> comment.dict()
{'pk': 17926777897585109,
 'text': 'Test comment 2',
 'user': {'pk': 1903424587,
  'username': 'example',
  'full_name': 'Example Example',
  'profile_pic_url': HttpUrl('https://scontent-hel3-1.cdninstagram.com/v/t51.2885-19/s150x150/156689363_269505058076642_6448820957073669709_n.jpg?tp=1&_nc_ht=scontent-hel3-1.cdninstagram.com&_nc_ohc=EtzrL0pAdg8AX9pE_wN&edm=ABQSlwABAAAA&ccb=7-4&oh=e04d45b7651140e7fef61b1f67f1f408&oe=60C65AD1&_nc_sid=b2b2bd', scheme='https', host='scontent-hel3-1.cdninstagram.com', tld='com', host_type='domain', path='/v/t51.2885-19/s150x150/156689363_269505058076642_6448820957073669709_n.jpg', query='tp=1&_nc_ht=scontent-hel3-1.cdninstagram.com&_nc_ohc=EtzrL0pAdg8AX9pE_wN&edm=ABQSlwABAAAA&ccb=7-4&oh=e04d45b7651140e7fef61b1f67f1f408&oe=60C65AD1&_nc_sid=b2b2bd'),
  'stories': []},
 'created_at_utc': datetime.datetime(2021, 5, 15, 14, 50, 3, tzinfo=datetime.timezone.utc),
 'content_type': 'comment',
 'status': 'Active',
 'has_liked': None,
 'like_count': None}

>>> comments = cl.media_comments(media_id)
>>> comments[0].dict()
 {'pk': 17926777897585108,
 'text': 'Test comment',
 'user': {'pk': 1903424587,
  'username': 'example',
  'full_name': 'Example Example',
  'profile_pic_url': HttpUrl('https://scontent-hel3-1.cdninstagram.com/v/t51.2885-19/s150x150/156689363_269505058076642_6448820957073669709_n.jpg?tp=1&_nc_ht=scontent-hel3-1.cdninstagram.com&_nc_ohc=EtzrL0pAdg8AX9pE_wN&edm=AId3EpQBAAAA&ccb=7-4&oh=e3fbafcdb63cec3535004e85eb3397ae&oe=60C65AD1&_nc_sid=705020', scheme='https', host='scontent-hel3-1.cdninstagram.com', tld='com', host_type='domain', path='/v/t51.2885-19/s150x150/156689363_269505058076642_6448820957073669709_n.jpg', query='tp=1&_nc_ht=scontent-hel3-1.cdninstagram.com&_nc_ohc=EtzrL0pAdg8AX9pE_wN&edm=AId3EpQBAAAA&ccb=7-4&oh=e3fbafcdb63cec3535004e85eb3397ae&oe=60C65AD1&_nc_sid=705020'),
  'stories': []},
 'created_at_utc': datetime.datetime(2021, 5, 15, 14, 50, 3, tzinfo=datetime.timezone.utc),
 'content_type': 'comment',
 'status': 'Active',
 'has_liked': False,
 'like_count': 0}

>>> (comments_part1, next_min_id) = cl.media_comments_chunk(media_id, 100)
>>> next_min_id
QVFBQmZCa1dxaFB5eFpBY2luVFMwLWdmN2ZCcUV6OF9hQWlIQk12ZWZqUlctZ2pOa1J5YjJ6bFY5Q1doSGNuUmpxSS1DdXRvZ0NLemJrR1hXd2p0dS1JMg==
>>> (comments_part2, next_min_id) = cl.media_comments_chunk(media_id, 100, next_min_id)
>>> next_min_id
QVFEbHpIWmpFc3BNUkgzUFVuOGZOQlhDQ1hHeWlVWHlJSnBhb2FHbFB3YlJtNThnOUlrd01JUWdKRmRwZTRpWWU0bnZmX3VMNHlwcDBkWTJpZjQ2NE9SeQ==

>>> cl.media_check_offensive_comment(media_id, "Some draft text")
False

>>> cl.comment_like(17926777897585108)
True

>>> cl.comment_unlike(17926777897585108)
True

>>> cl.comment_bulk_delete(media_id, [17926777897585108])
True
```

Notes:

* `media_comments()` fetches both regular and headload comment pages until `amount` is reached.
* `media_comments_chunk()` is the better choice when you want to store and resume the server cursor manually.
* `comment_pin()` / `comment_unpin()` only work on media owned by the authenticated account.
* Reply creation is supported through `replied_to_comment_id`, but there is no dedicated helper yet for fetching a standalone reply thread for a comment.
