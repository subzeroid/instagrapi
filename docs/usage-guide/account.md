# Account

Viewing and managing your profile

| Method                             | Return    | Description
| ---------------------------------- | --------- | ----------------------------------------------------------
| account_info()                     | Account | Get private info for your account (e.g. email, phone_number)
| account_edit(email: str, phone_number: str, username: str, full_name: str, biography: str, external_url: str) | Account | Change profile data
| account_change_picture(path: Path) | UserShort | Change Profile picture
