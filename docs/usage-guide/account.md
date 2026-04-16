# Account

Viewing and managing your profile

| Method | Return | Description |
| --- | --- | --- |
| account_info() | Account | Get private info for the current account (email, phone number, birthday, biography, etc.) |
| account_edit(**data) | Account | Update profile fields such as `username`, `full_name`, `biography`, `external_url`, `phone_number`, and `email` |
| account_set_biography(biography: str) | bool | Update biography text, including entity-aware markup handling |
| account_change_picture(path: Path) | UserShort | Change profile picture |
| account_set_private() | bool | Switch account to private mode |
| account_set_public() | bool | Switch account to public mode |
| account_security_info() | dict | Return account security settings, backup codes, trusted devices, and 2FA state |
| set_external_url(external_url: str) | dict | Replace bio links with a single external URL |
| remove_bio_links(link_ids: List[int]) | dict | Remove one or more bio links by link ID |
| reset_password(username: str) | dict | Trigger Instagram account recovery flow |
| change_password(old_password: str, new_password: str) | bool | Change account password |

Example:

```python
>>> from instagrapi import Client
>>> cl = Client()
>>> cl.login(USERNAME, PASSWORD)
>>> cl.account_info().dict()
{'pk': 1903424587,
 'username': 'example',
 'full_name': 'Example Example',
 'is_private': False,
 'profile_pic_url': HttpUrl('https://instagram.frix7-1.fna.fbcdn.net/v/t51.2885-19/s150x150/200092102_504535360754500_904902738723095864_n.jpg?tp=1&_nc_ht=instagram.frix7-1.fna.fbcdn.net&_nc_ohc=T2ZT6yA6XzoAX9MvAQA&edm=AJlpnE4BAAAA&ccb=7-4&oh=3865b51bb33b365c9de8bcf9775e519c&oe=60E982F2&_nc_sid=312772'),
 'is_verified': False,
 'biography': 'Engineer: Python, JavaScript, Erlang, Go, Swift\n@dhbastards \n@bestskatetrick \n@asphalt_kings_lb \n@best_drift_daily \n@wrclive \n@surferyone \n@bmxtravel',
 'external_url': 'https://example.org/',
 'is_business': False,
 'birthday': '1984-01-01',
 'phone_number': '+79991234567',
 'gender': 1,
 'email': '...@gmail.com'}

>>> cl.account_edit(external_url='https://github.com/subzeroid/instagrapi')
Account(pk=1903424587, username='example', ..., external_url='https://github.com/subzeroid/instagrapi')

>>> cl.account_set_biography("Python, APIs, and automation")
True

>>> media_pk = cl.media_pk_from_url('https://www.instagram.com/p/BWnh360Fitr/')
1560364774164147051

>>> profile_pic_path = cl.photo_download(media_pk, folder='/tmp')
PosixPath('/tmp/example_1560364774164147051.jpg')

>>> cl.account_change_picture(profile_pic_path)
UserShort(pk=1903424587, username='example', ...)

>>> cl.send_confirm_email("addr@example.com")
{
    'is_email_legit': False,
    'title': 'Email Already in Use',
    'body': 'The email address you entered is already used on your account. Enter a different one to update your contact info.',
    'error_type': 'email_unchanged',
    'status': 'ok'
}

>>> cl.send_confirm_phone_number("+5599999999")
{
    'action': 'sms_sent',
    'phone_verification_settings': {'max_sms_count': 2,
    'resend_sms_delay_sec': 60,
    'robocall_count_down_time_sec': 30,
    'robocall_after_max_sms': True},
    'status': 'ok'
}
```

Notes:

* `account_edit(**data)` only applies supported fields and preserves missing required profile fields from `account_info()`.
* Use `account_set_biography()` when you want Instagram to re-process biography entities/markup explicitly.
* `account_security_info()` and `insights_*` style methods require an authenticated session and may depend on the account type or enabled security features.

Low level methods:

| Method | Return | Description |
| --- | --- | --- |
| news_inbox_v1(mark_as_seen: bool = False) | dict | Get raw "Active recently" / inbox activity payload |

Example:

```python
>>> cl.news_inbox_v1()
{'story_mentions': {'mentions_count_string': '0 stories mention you.',
  'reels': [],
  'product_stories_count': '0 stories mention your product.',
  'product_stories_reels': []},
 'counts': {'likes': 0,
  'activity_feed_dot_badge': 0,
  'relationships': 0,
  'new_posts': 0,
  'comments': 0,
  'comment_likes': 0,
  'shopping_notification': 0,
  'fundraiser': 0,
  'usertags': 0,
  'campaign_notification': 0,
  'photos_of_you': 0,
  'story_mentions': 0,
  'requests': 0},
 'last_checked': 1625468461.1633658,
 'friend_request_stories': [],
 'new_stories': [{'story_type': 159,
   'type': 13,
   'args': {'rich_text': 'An unrecognized XiaoMi MI 5s just logged in near Moscow, Russia, RU',
    'destination': 'login_activity',
    'icon_url': 'https://i.instagram.com/static/images/activity/info-1.5.png/3385260677b8.png',
    'should_icon_apply_filter': True,
    'icon_should_apply_filter': True,
    'extra': {'lat': 55.7522, 'long': 37.6156},
    'actions': ['hide'],
    'timestamp': 1625475888.805998,
    'tuuid': '0ceff44c-dd70-11eb-8080-808080808080',
    'clicked': False},
   'counts': {},
   'pk': 'xjQlWRMfNO+f739i2qZ1zf8HJTo='}],
 'old_stories': [{'type': 3,
   'story_type': 101,
   'args': {'links': [{'start': 24,
      'end': 33,
  ...
}
```
