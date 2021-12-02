# Comment

Post comment, viewing, like and unlike comments

| Method                                                                                  | Return             | Description
| --------------------------------------------------------------------------------------- | ------------------ | --------------------------
| media_comment(media_id: str, message: str, replied_to_comment_id: Optional[int] = None) | Comment            | Add new comment to media
| media_comments(media_id: str, amount: int = 0)                                          | List\[Comment]     | Get a list comments for media (amount=0 - all comments)
| comment_like(comment_pk: int)                                                           | bool               | Like a comment
| comment_unlike(comment_pk: int)                                                         | bool               | Unlike a comment
| comment_bulk_delete(media_id: str, comment_pks: List[int])                              | bool               | Delete a comment


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
  'username': 'adw0rd',
  'full_name': 'Mikhail Andreev',
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
  'username': 'adw0rd',
  'full_name': 'Mikhail Andreev',
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
  'username': 'adw0rd',
  'full_name': 'Mikhail Andreev',
  'profile_pic_url': HttpUrl('https://scontent-hel3-1.cdninstagram.com/v/t51.2885-19/s150x150/156689363_269505058076642_6448820957073669709_n.jpg?tp=1&_nc_ht=scontent-hel3-1.cdninstagram.com&_nc_ohc=EtzrL0pAdg8AX9pE_wN&edm=AId3EpQBAAAA&ccb=7-4&oh=e3fbafcdb63cec3535004e85eb3397ae&oe=60C65AD1&_nc_sid=705020', scheme='https', host='scontent-hel3-1.cdninstagram.com', tld='com', host_type='domain', path='/v/t51.2885-19/s150x150/156689363_269505058076642_6448820957073669709_n.jpg', query='tp=1&_nc_ht=scontent-hel3-1.cdninstagram.com&_nc_ohc=EtzrL0pAdg8AX9pE_wN&edm=AId3EpQBAAAA&ccb=7-4&oh=e3fbafcdb63cec3535004e85eb3397ae&oe=60C65AD1&_nc_sid=705020'),
  'stories': []},
 'created_at_utc': datetime.datetime(2021, 5, 15, 14, 50, 3, tzinfo=datetime.timezone.utc),
 'content_type': 'comment',
 'status': 'Active',
 'has_liked': False,
 'like_count': 0}

>>> cl.comment_like(17926777897585108)
True

>>> cl.comment_unlike(17926777897585108)
True

>>> cl.comment_bulk_delete(media_id, [17926777897585108])
True
```
