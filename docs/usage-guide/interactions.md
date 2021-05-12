# Interactions

`instagrapi` provides various types of `Interactions` that can be used to control how the program will interact with the `Instagram`:

* [`Media`](media.md) - Media (Photo, Video, Album, IGTV, Reels or Story)
* `Resource` - Part of Media (for albums)
* `MediaOembed` - Short version of Media
* `Account` - Full private info for your account (e.g. email, phone_number)
* [`User`](user.md) - Full public user data
* `UserShort` - Short public user data (used in Usertag, Comment, Media, Direct)
* `Usertag` - Tag user in Media (coordinates + UserShort)
* [`Location`](location.md) - GEO location (GEO coordinates, name, address)
* [`Hashtag`](hashtag.md) - Hashtag object (id, name, picture)
* [`Collection`](collection.md) - Collection of medias (name, picture and list of medias)
* [`Comment`](comment.md) - Comments to Media
* [`Story`](story.md) - Story
* [`StoryLink`](story.md) - Link (Swipe up)
* [`StoryLocation`](story.md) - Tag Location in Story (as sticker)
* [`StoryMention`](story.md) - Mention users in Story (user, coordinates and dimensions)
* [`StoryHashtag`](story.md) - Hashtag for story (as sticker)
* [`StorySticker`](story.md) - Tag sticker to story (for example from giphy)
* [`StoryBuild`](story.md) - [StoryBuilder](/instagrapi/story.py) return path to photo/video and mention co-ordinates
* [`DirectThread`](direct.md) - Thread (topic) with messages in Direct
* [`DirectMessage`](direct.md) - Message in Direct
* [`Insight`](insight.md) - Insights for a post

## Interacting with Instagram Account

`instagrapi` provides the following `Interactions` that can be used to control and get the information about your `Instagram` account:

* Client(settings: dict = {}, proxy: str = ""): bool - Init `instagrapi` client
  
``` python
cl.login("instagrapi", "42")
# cl.login("instagrapi", "42", verification_code="123456")  # with 2FA verification_code
# cl.login_by_sessionid("peiWooShooghahdi2Eip7phohph0eeng")
cl.set_proxy("socks5://127.0.0.1:30235")
# cl.set_proxy("http://username:password@127.0.0.1:8080")
# cl.set_proxy("socks5://username:password@127.0.0.1:30235")

print(cl.get_settings())
print(cl.user_info(cl.user_id))
```

* login(username: str, password: str): bool - Login by username and password (get new cookies if it does not exist in settings)
* login(username, password, verification_code='<2FA CODE>') - Login by username and password with 2FA verification code
* relogin(): bool - Re-login with clean cookies (required cl.username/cl.password)
* login_by_sessionid(sessionid: str): bool - Login by sessionid from Instagram site
* get_settings(): dict - Return settings dict

You can pass settings to the Client (and save cookies), it has the following format:

```python
settings = {
   "uuids": {
      "phone_id": "57d64c41-a916-3fa5-bd7a-3796c1dab122",
      "uuid": "8aa373c6-f316-44d7-b49e-d74563f4a8f3",
      "client_session_id": "6c296d0a-3534-4dce-b5aa-a6a6ab017443",
      "advertising_id": "8dc88b76-dfbc-44dc-abbc-31a6f1d54b04",
      "device_id": "android-e021b636049dc0e9"
   },
   "cookies":  {},  # set here your saved cookies
   "last_login": 1596069420.0000145,
   "device_settings": {
      "cpu": "h1",
      "dpi": "640dpi",
      "model": "h1",
      "device": "RS988",
      "resolution": "1440x2392",
      "app_version": "117.0.0.28.123",
      "manufacturer": "LGE/lge",
      "version_code": "168361634",
      "android_release": "6.0.1",
      "android_version": 23
   },
   "user_agent": "Instagram 117.0.0.28.123 Android (23/6.0.1; ...US; 168361634)"
}

cl = Client(settings)
```

* set_settings(settings: Dict): bool - Set session settings
* load_settings(path: Path): dict - Load session settings from file
* dump_settings(path: Path): bool - Serialize and save session settings to file
* set_proxy(dsn: str): dict - Support socks and http/https proxy "scheme://username:password@host:port"
* cookie_dict: dict - Return cookies
* user_id: int - Return your user_id (after login)
* device: dict - Return device dict which we pass to Instagram
* set_device(device: dict): bool - Change device settings (https://www.myfakeinfo.com/mobile/get-android-device-information.php)
* set_user_agent(user_agent: str = ""): bool - Change User-Agent header (https://user-agents.net/applications/instagram-app)
* base_headers: dict - Base headers for Instagram
* account_info(): Account - Get private info for your account (e.g. email, phone_number)
* account_edit(\*\*data): Account - Change profile data (e.g. email, phone_number, username, full_name, biography, external_url)
* account_change_picture(path: Path): UserShort - Change Profile picture

## Challenge

All challenges solved in the module challenge.py

Automatic submission code from SMS/Email in examples here