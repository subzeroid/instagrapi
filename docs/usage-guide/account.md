# Account

Viewing and managing your profile

| Method                             | Return    | Description
| ---------------------------------- | --------- | ----------------------------------------------------------
| account_info()                     | Account | Get private info for your account (e.g. email, phone_number)
| account_edit(email: str, phone_number: str, username: str, full_name: str, biography: str, external_url: str) | Account | Change profile data
| account_change_picture(path: Path) | UserShort | Change Profile picture

Low level methods:

| Method                                         | Return    | Description
| ---------------------------------------------- | --------- | ----------------------------------------------------------
| news_inbox_v1(mark_as_seen: bool = False)      | dict      | Get "Active recently" as is (old and new stories)
