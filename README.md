# instagrapi

Fast and effective Instagram Private API wrapper (public+private requests and challenge resolver)

### Features

1. Performs public (`_gql` or `_a1` methods) or private (`_v1` methods) requests depending on the situation (in order to avoid Instagram limits)
2. Challenge Resolver have Email (As well as recipes for automating sending a code from Email) and SMS handlers
3. Support upload Photo, Video, IGTV, Albums and Stories
4. Support User, Media, Insights, Collections and Direct
5. Insights
6. Build Stories with custom background and font animation

### Install

    pip install instagrapi

### Tests

    python -m unittest tests
    python -m unittest tests.ClientPublicTestCase


### Requests

Public (anonymous) methods had suffix `_gql` (GraphQL) or `_a1` (`?__a=1`)
Private (authorized request) methods have `_v1` suffix
The first request to fetch media or user is anonymous then authorized ("private" request)

### Usage

```
from instagrapi import Client

cl = Client()
cl.login(ACCOUNT_USERNAME, ACCOUNT_PASSWORD)

user_id = cl.user_id_from_username("adw0rd")
medias = cl.user_medias(user_id, 20)
```

#### Account

This is your authorized account

| Method                   | Description   |
| ------------------------ |:-------------:|
| login_by_sessionid(sessionid: str) | Login by sessionid from instagram |
| login(username: str, password: str, settings: dict = {}) | Login by username and password |
| get_settings() | Return settings dict (more details below) |
| set_proxy("socks5://127.0.0.1:30235") | socks proxy |
| set_proxy("http://127.0.0.1:8080") | http/https proxy |

You can pass settings to the Client, it has the following format:

```
settings = {
   "uuids": {
      "phone_id":"57d64c41-a916-3fa5-bd7a-3796c1dab122",
      "uuid":"8aa373c6-f316-44d7-b49e-d74563f4a8f3",
      "client_session_id":"6c296d0a-3534-4dce-b5aa-a6a6ab017443",
      "advertising_id":"8dc88b76-dfbc-44dc-abbc-31a6f1d54b04",
      "device_id":"android-e021b636049dc0e9"
   },
   "cookies":{},  # set here you saved cookies
   "last_login":1596069420.0000145,
   "device_settings":{
      "cpu":"h1",
      "dpi":"640dpi",
      "model":"h1",
      "device":"RS988",
      "resolution":"1440x2392",
      "app_version":"117.0.0.28.123",
      "manufacturer":"LGE/lge",
      "version_code":"168361634",
      "android_release":"6.0.1",
      "android_version":23
   },
   "user_agent":"Instagram 117.0.0.28.123 Android (23/6.0.1; 640dpi; 1440x2392; LGE/lge; RS988; h1; h1; en_US; 168361634)"
}

cl = Client(username, password, settings)
```

This values send to Instagram API.

#### Media

This is Instagram terminology (media_id and media_pk):

* `media_id` - String ID `"{media_id}_{user_id}"`, example `"2277033926878261772_1903424587"`
* `media_pk` - Integer ID (real media id), example `2277033926878261772`
* `code` - Short code (slug for media), example `BjNLpA1AhXM` from `"https://www.instagram.com/p/BjNLpA1AhXM/"`
* `url` - URL to media

| Method                   | Description   | Example       |
| ------------------------ |:-------------:|:-------------:|
| media_id(media_pk) | Return media_id by media_pk |
| media_pk(media_id) | Return media_pk by media_id |
| media_pk_from_code(short_code) | Return media_pk | media_pk_from_code("B-fKL9qpeab") -> 2278584739065882267 |
| media_pk_from_code(full_code) | Return media_pk (by IGTV code) | media_pk_from_code("B8jnuB2HAbyc0q001y3F9CHRSoqEljK_dgkJjo0") -> 2243811726252050162 |
| media_pk_from_url(url) | Return media_pk | media_pk_from_url("https://www.instagram.com/p/BjNLpA1AhXM/") -> 1787135824035452364 |
| media_info(media_pk) | media_info_gql or media_info_v1 |
| media_delete(media_pk) | Delete media |
| media_edit(media_pk, caption) | Change caption for media |
| media_user(media_pk) | Get user info for media |
| media_oembed(url) | Return short media info by media URL | media_oembed("https://www.instagram.com/p/B3mr1-OlWMG/") |
| media_comments(media_id) | Get all comments  |
| media_comment(media_id, message) | Write message to media | 

#### User

user_id - Integer ID of user, example `1903424587`

| Method                   | Description   |
| ------------------------ |:-------------:|
| user_medias(user_id, 20) | Get list of medias by user_id |
| user_followers(user_id) | Get list of user_id of followers users |
| user_following | Get list of user_id of following users |
| user_info(user_id) | Get user info dict. First call public request user_info_gql(user_id) and next private api request user_info_v1(user_id) |
| user_info_by_username(username) | Get user info dict by username |
| user_follow(user_id) | Follow user |
| user_unfollow(user_id) | Unfollow user |
| user_id_from_username(username) | Get user_id by username |
| username_from_user_id(user_id) | Get username by user_id |

#### Upload

| Method                   | Description   |
| ------------------------ |:-------------:|
| photo_upload(path, caption)| Upload photo |
| photo_download(media_pk) | Download photo |
| video_upload(path, caption) | Upload video |
| video_download(media_pk) | Download video |
| igtv_upload(path, title, caption) | Upload IGTV |
| igtv_download(media_pk) | Download IGTV |
| album_upload(paths, caption) | Upload Album |
| album_download(media_pk) | Download Album |

#### Stories

In the process of describing

#### Collections

| Method                   | Description   |
| ------------------------ |:-------------:|
| collections() | Get all account collections |
| collection_medias_by_name(name) | Get medias in collection by name |
| collection_medias(collection_id, amount=21, last_media_pk=0) | Get medias in collection by collection_id |

#### Insights

In the process of describing

#### Direct

In the process of describing

#### Challenge

In the process of describing
