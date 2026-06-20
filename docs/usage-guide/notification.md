# Notification

Manage notification settings for the authenticated account.

| Method | Return | Description |
| --- | --- | --- |
| notification_settings(content_type: NotificationContentType, setting_value: NotificationSettingValue) | bool | Low-level notification setting helper |
| notification_disable() | bool | Disable all supported account notifications |
| notification_mute_all(setting_value: MUTE_ALL = "8_hour") | bool | Mute all notifications for a fixed period |
| notification_likes(setting_value: SETTING_VALUE = "off") | bool | Manage likes notifications |
| notification_comments(setting_value: SETTING_VALUE = "off") | bool | Manage comment notifications |
| notification_direct_share_activity(setting_value: SETTING_VALUE = "off") | bool | Manage Direct share activity notifications |
| notification_login(setting_value: SETTING_VALUE = "off") | bool | Manage login notifications |

`NotificationContentType` is a `Literal` covering the known helper-backed
notification categories:

```python
from instagrapi.mixins.notification import NotificationContentType
```

Available values are:

```python
"mute_all"
"likes"
"like_and_comment_on_photo_user_tagged"
"user_tagged"
"comments"
"comment_likes"
"first_post"
"new_follower"
"follow_request_accepted"
"connection_notification"
"tagged_in_bio"
"pending_direct_share"
"direct_share_activity"
"direct_group_requests"
"video_call"
"rooms"
"live_broadcast"
"felix_upload_result"
"view_count"
"fundraiser_creator"
"fundraiser_supporter"
"notification_reminders"
"announcements"
"report_updated"
"login_notification"
```

Option values are exposed as public aliases:

```python
SETTING_VALUE = Literal["off", "following_only", "everyone"]
MUTE_ALL = Literal["cancel", "15_minutes", "1_hour", "2_hour", "4_hour", "8_hour"]
NotificationSettingValue = Union[SETTING_VALUE, MUTE_ALL]
```

`SETTING_VALUE` is used by the per-category helpers. `MUTE_ALL` is used by
`notification_mute_all()`. `NotificationSettingValue` is used by the low-level
`notification_settings(...)` helper because it can send either a regular
notification value or a mute-all duration depending on `content_type`.

Example:

```python
from instagrapi import Client

cl = Client()
cl.login(USERNAME, PASSWORD)

cl.notification_comments("following_only")
cl.notification_settings("likes", "off")
cl.notification_mute_all("1_hour")
```
