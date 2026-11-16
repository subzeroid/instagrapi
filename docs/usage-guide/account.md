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
| account_convert_to_business(category_id: str \| int = "2347428775505624", should_show_category: bool = True, should_show_public_contacts: bool = False) | Account | Convert the current account to a business professional account |
| account_convert_to_creator(category_id: str \| int = "2347428775505624", should_show_category: bool = True, should_show_public_contacts: bool = False) | Account | Convert the current account to a creator professional account |
| account_convert_to_professional(to_account_type: Literal[2, 3] = 3, category_id: str \| int = "2347428775505624", should_show_category: bool = True, should_show_public_contacts: bool = False) | Account | Generic professional account conversion helper; `2` is business and `3` is creator |
| account_security_info() | dict | Return account security settings, backup codes, trusted devices, and 2FA state |
| set_external_url(external_url: str) | dict | Replace bio links with a single external URL |
| remove_bio_links(link_ids: List[int]) | dict | Remove one or more bio links by link ID |
| send_password_reset(identifier: str, recaptcha_challenge_field: str = "") | dict | Send an Instagram password reset link or code to the account email or phone |
| reset_password(username: str) | dict | Backward-compatible alias for `send_password_reset()` |
| change_password(old_password: str, new_password: str) | bool | Change account password |
| send_confirm_email(email: str) | dict | Send a confirmation code to a new email address |
| confirm_email(email: str, code: str) | dict | Confirm a new email address with the received code |
| send_confirm_phone_number(phone_number: str) | dict | Send a confirmation code to a new phone number |
| confirm_phone_number(phone_number: str, code: str, has_sms_consent: bool = False) | dict | Confirm a new phone number with the received SMS code |

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

>>> cl.account_convert_to_creator(category_id="2347428775505624")
Account(pk=1903424587, username='example', ..., account_type=3)

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

>>> cl.confirm_email("addr@example.com", "123456")
{'status': 'ok'}

>>> cl.send_confirm_phone_number("+5599999999")
{
    'action': 'sms_sent',
    'phone_verification_settings': {'max_sms_count': 2,
    'resend_sms_delay_sec': 60,
    'robocall_count_down_time_sec': 30,
    'robocall_after_max_sms': True},
    'status': 'ok'
}

>>> cl.confirm_phone_number("+5599999999", "123456")
{'status': 'ok'}
```

Notes:

* `account_edit(**data)` only applies supported fields and preserves missing required profile fields from `account_info()`.
* Use `account_set_biography()` when you want Instagram to re-process biography entities/markup explicitly.
* Professional conversion uses Instagram's mobile conversion flow and may still be blocked by account-specific eligibility, category, contact, or Account Center requirements.
* `account_convert_to_business()` sends `to_account_type=2`; `account_convert_to_creator()` sends `to_account_type=3`. The generic helper exposes this as `ProfessionalAccountType = Literal[2, 3]`.
* `send_password_reset()` starts Instagram's recovery flow by requesting a reset link or code. It does not set a new password by itself; continue with the link/code flow that Instagram sends to the account email or phone.
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


## Create an additional profile

**Validation status (3.2.15):** the related async flow was validated in aiograpi,
but synchronous live attempts returned a different username and the resulting
sessions required a challenge. Successful synchronous creation and session
handoff have not been established. The method rejects mismatched results; do
not automatically retry creation after such an error.

`client.create_secondary_account(username, *, link_to_main_account=True)`
uses an authenticated main account to create an additional Instagram profile in
its Accounts Center, without a separate email address, phone number or password.
Calling this method accepts Instagram's terms for the new account. Instagram can
require verification or reject creation; unsupported screens stop the flow.
Only the linked Accounts Center flow is supported. Passing
`link_to_main_account=False` raises `ValueError` before sending a request.

```python
from instagrapi import Client
from instagrapi.exceptions import SecondaryAccountError

main = Client()
main.login(MAIN_USERNAME, MAIN_PASSWORD)
try:
    result = main.create_secondary_account("new_additional_profile")
except SecondaryAccountError as exc:
    print(exc.stage, exc.creation_may_have_succeeded)
    # Never retry automatically: a timeout after submission can still create
    # an account. Check the main account's Accounts Center first.
    raise

additional = Client(settings=result.settings, proxy=main.proxy)
print(result.user.pk, result.user.username)
# main still uses its original identity and cookies.
```

The returned `SecondaryAccount` contains `user: UserShort` and `settings: dict`.
Settings contain credentials for the new session: keep them private and persist
with the same care as `Client.get_settings()`. They are omitted from the result's
representation, but included when explicitly serializing the result. Proxy
credentials are not included; pass the intended proxy to the new client.
Temporary connections used by creation are closed before returning.
The main client's `read_timeout` must be a finite positive number; invalid values
are rejected before a temporary client or network request is created.

Creation does not retry automatically or follow HTTP redirects. If the final
submission fails or its response cannot be validated,
`SecondaryAccountError.creation_may_have_succeeded` is true. Interruption after
submission can also leave an uncertain result. Do not call the method again as
a recovery step without checking the account first. No automatic onboarding,
contact upload, follows, or legacy account-family mutation is performed.

Accounts Center linkage and the legacy `get_account_family_v1()` lists are
separate observations: `child_accounts` and `main_accounts` can remain empty
after successful creation. Validate the returned identity/session; an empty
legacy list alone does not mean that creation failed. An "additional profile"
here is not a child-age or parental-supervision account.
