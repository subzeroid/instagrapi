# Interactions

`instagrapi` provides various types of `Interactions` that can be used to control how the program will interact with the `Instagram`:

* [`Media`](media.md) - Media (Photo, Video, Album, IGTV, Reels or Story)
* [`Resource`](media.md) - Part of Media (for albums)
* [`MediaOembed`](media.md) - Short version of Media
* [`Account`](account.md) - Full private info for your account (e.g. email, phone_number)
* [`TOTP`](totp.md) - 2FA TOTP helpers (generate seed, enable/disable TOTP, generate code as Google Authenticator)
* [`User`](user.md) - Full public user data
* [`UserShort`](user.md) - Short public user data (used in Usertag, Comment, Media, Direct)
* [`Usertag`](user.md) - Tag user in Media (coordinates + UserShort)
* [`Location`](location.md) - GEO location (GEO coordinates, name, address)
* [`Hashtag`](hashtag.md) - Hashtag object (id, name, picture)
* [`Collection`](collection.md) - Collection of medias (name, picture and list of medias)
* [`Comment`](comment.md) - Comments to Media
* [`Highlight`](highlight.md) - Highlights
* [`Story`](story.md) - Story
* [`StoryLink`](story.md) - Link (Swipe up)
* [`StoryLocation`](story.md) - Tag Location in Story (as sticker)
* [`StoryMention`](story.md) - Mention users in Story (user, coordinates and dimensions)
* [`StoryHashtag`](story.md) - Hashtag for story (as sticker)
* [`StorySticker`](story.md) - Tag sticker to story (for example from giphy)
* [`StoryBuild`](story.md) - [StoryBuilder](https://github.com/adw0rd/instagrapi/blob/master/instagrapi/story.py) return path to photo/video and mention co-ordinates
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

### Request

| Property            | Description
| ------------------- | --------------------------------------------------------------
| request\_logger     | Logger in which various actions from Instagram are registered
| request\_timeout    | Timeout in seconds between requests (1 second by default)


### Login

| Method                               | Return  | Description
| ------------------------------------ | ------- | -------------------------------------------------
| login(username: str, password: str)  | bool    | Login by username and password (get new cookies if it does not exist in settings)
| login(username: str, password: str, verification\_code: str) | bool | Login by username and password with 2FA verification code (use Google Authenticator or something similar to generate TOTP code, not work with SMS)
| relogin()                            | bool    | Re-login with clean cookies (required cl.username and cl.password)
| login\_by\_sessionid(sessionid: str) | bool    | Login by sessionid from Instagram site
| inject\_sessionid\_to\_public()      | bool    | Inject sessionid from Private Session to Public Session
| logout()                             | bool    | Logout

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

### Settings

Store and manage uuids, device configuration, user agent, authorization data (aka cookies) and other session settings

| Method                         | Return  | Description
| ------------------------------ | ------- | ------------------------------------------------------------------
| get\_settings()                | dict    | Return settings dict
| set\_settings(settings: dict)  | bool    | Set session settings
| load\_settings(path: Path)     | dict    | Load session settings from file
| dump\_settings(path: Path)     | bool    | Serialize and save session settings to file

In order for Instagram [to trust you more](https://github.com/adw0rd/instagrapi/discussions/220), you must always login from one device and one IP (or from a subnet):

```python
cl = Client()
cl.login(USERNAME, PASSWORD)
cl.dump_settings('/tmp/dump.json')
```

Next time:

```python
cl = Client()
cl.load_settings('/tmp/dump.json')
cl.login(USERNAME, PASSWORD)
cl.get_timeline_feed()  # check session
```

### Manage device, proxy and other account settings

| Method                                   | Return | Description
|------------------------------------------|------|----------------------------------------------------------------------------
| set_proxy(dsn: str)                      | dict | Support socks and http/https proxy "scheme://username:password@host:port"
| private.proxies                          | dict | Stores used proxy servers for private (mobile, v1) requests
| public.proxies                           | dict | Stores used proxy servers for public (web, graphql) requests
| set_device(device: dict)                 | bool | Change device settings ([Android Device Information Generator Online](https://www.myfakeinfo.com/mobile/get-android-device-information.php))
| device                                   | dict | Return device dict which we pass to Instagram
| set_user_agent(user_agent: str = "")     | bool | Change User-Agent header ([User Agents](https://user-agents.net/applications/instagram-app))
| cookie_dict                              | dict | Return cookies
| user_id                                  | int  | Return your user_id (after login)
| base_headers                             | dict | Base headers for Instagram
| set_country(country: str = "US")         | bool | Set country (advice: use the country of your proxy)
| set_country_code(country_code: int = 1)  | bool | Set country calling code. Default: +1 (USA)
| set_locale(locale: str = "en_US")        | bool | Set locale (advice: use the locale of your proxy)
| set_timezone_offset(seconds: int)        | bool | Set timezone offset in seconds

``` python
cl = Client()

# Los Angles user:
cl.set_proxy('http://los:angeles@proxy.address:8080')
cl.set_locale('en_US')
cl.set_timezone_offset(-7 * 60 * 60)  # Los Angeles UTC (GMT) -7 hours == -25200 seconds
cl.get_settings()
{
    ...
    'user_agent': 'Instagram 194.0.0.36.172 Android (26/8.0.0; 480dpi; 1080x1920; Xiaomi; MI 5s; capricorn; qcom; en_US; 301484483)',
    'country': 'US',
    'country_code': 1,
    'locale': 'en_US',
    'timezone_offset': -25200
}

# Moscow user:
cl.set_proxy('socks5://moscow:proxy@address:8080')
cl.set_locale('ru_RU')
cl.set_country_code(7)  # +7
cl.set_timezone_offset(3 * 3600)  # Moscow UTC+3
cl.get_settings()
{
    ...
    'user_agent': 'Instagram 194.0.0.36.172 Android (26/8.0.0; 480dpi; 1080x1920; Xiaomi; MI 5s; capricorn; qcom; ru_RU; 301484483)',
    'country': 'RU',
    'country_code': 7,
    'locale': 'ru_RU',
    'timezone_offset': 10800
}
```

## What's Next?

* [Getting Started](../getting-started.md)
* [Usage Guide](fundamentals.md)
* [Handle Exceptions](handle_exception.md)
* [Challenge Resolver](challenge_resolver.md)
* [Exceptions](../exceptions.md)
