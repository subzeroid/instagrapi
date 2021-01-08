# instagrapi
Fast and effective Instagram Private API wrapper (public+private requests and challenge resolver). Use the most recent version of the API from Instagram, which was obtained using [reverse-engineering with Charles Proxy](https://adw0rd.com/2020/03/26/sniffing-instagram-charles-proxy/en/).

Support **Python >= 3.6**

Instagram API valid for 6 January 2021 (last reverse-engineering check)

[Support Chat in Telegram](https://t.me/instagrapi)
![](https://gist.githubusercontent.com/m8rge/4c2b36369c9f936c02ee883ca8ec89f1/raw/c03fd44ee2b63d7a2a195ff44e9bb071e87b4a40/telegram-single-path-24px.svg) and [GitHub Discussions](https://github.com/adw0rd/instagrapi/discussions)

### Authors

[@adw0rd](http://github.com/adw0rd/) and [@onlinehunter](http://github.com/onlinehunter/)

### Features

1. Performs Public API (web, anonymous) or Private API (mobile app, authorized) requests depending on the situation (to avoid Instagram limits)
2. Challenge Resolver have [Email](/examples/challenge_resolvers.py) (as well as recipes for automating receive a code from email) and [SMS handlers](/examples/challenge_resolvers.py)
3. Support upload a Photo, Video, IGTV, Albums and Stories
4. Support work with User, Media, Insights, Collections, Location (Place), Hashtag and Direct objects
5. Like, Follow, Edit account (Bio) and much more else
6. Insights by account, posts and stories
7. Build stories with custom background, font animation, swipe up link and mention users
8. In the next release, account registration and captcha passing will appear

### Install

    pip install instagrapi

### Requests

* `Public` (anonymous request via web api) methods have a suffix `_gql` (Instagram `GraphQL`) or `_a1` (example `https://www.instagram.com/adw0rd/?__a=1`)
* `Private` (authorized request via mobile api) methods have `_v1` suffix

The first request to fetch media/user is `public` (anonymous), if instagram raise exception, then use `private` (authorized).
Example (pseudo-code):

``` python
def media_info(media_pk):
    try:
        return self.media_info_gql(media_pk)
    except ClientError as e:
        # Restricted Video: This video is not available in your country.
        # Or media from private account
        return self.media_info_v1(media_pk)
```

### Usage

``` python
from instagrapi import Client

cl = Client()
cl.login(ACCOUNT_USERNAME, ACCOUNT_PASSWORD)

user_id = cl.user_id_from_username("adw0rd")
medias = cl.user_medias(user_id, 20)
```

### Types

The current types are in [types.py](/instagrapi/types.py):

| Method         | Description                                                                            |
| -------------- | -------------------------------------------------------------------------------------- |
| Media          | Media (Photo, Video, Album, IGTV or Story)                                             |
| Resource       | Part of Media (for albums)                                                             |
| MediaOembed    | Short version of Media                                                                 |
| Account        | Full private info for your account (e.g. email, phone_number)                          |
| User           | Full public user data                                                                  |
| UserShort      | Short public user data (used in Usertag, Comment, Media, Direct)                       |
| Usertag        | Tag user in Media (coordinates + UserShort)                                            |
| Location       | GEO location (GEO coordinates, name, address)                                          |
| Hashtag        | Hashtag object (id, name, picture)                                                     |
| Collection     | Collection of medias (name, picture and list of medias)                                |
| Comment        | Comments to Media                                                                      |
| Story          | Story                                                                                  |
| StoryLink      | Link (Swipe up)                                                                        |
| StoryLocation  | Tag Location in Story (as stocker)                                                     |
| StoryMention   | Mention users in Story (user, coordinates and dimensions)                              |
| StoryHashtag   | Hashtag for story (as sticker)                                                         |
| StorySticker   | Tag sticker to story (for example from giphy)                                          |
| StoryBuild     | [StoryBuilder](/instagrapi/story.py) return path to photo/video and mention cordinats  |
| DirectThread   | Thread (topic) with messages in Direct                                                 |
| DirectMessage  | Message in Direct                                                                      |

#### Account

This is your authorized account

| Method                                       | Return    | Description                                                                       |
| -------------------------------------------- | --------- | --------------------------------------------------------------------------------- |
| Client(settings: dict = {}, proxy: str = "") | bool      | Init instagrapi client (settings example below)                                   |
| login(username: str, password: str)          | bool      | Login by username and password (get new cookies if it does not exist in settings) |
| relogin()                                    | bool      | Relogin with clean cookies (required cl.username/cl.password)                     |
| login_by_sessionid(sessionid: str)           | bool      | Login by sessionid from Instagram site                                            |
| get_settings()                               | dict      | Return settings dict (more details below)                                         |
| set_proxy(dsn: str)                          | dict      | Support socks and http/https proxy                                                |
| cookie_dict                                  | dict      | Return cookies                                                                    |
| user_id                                      | int       | Return your user_id (after login)                                                 |
| device                                       | dict      | Return device dict which we pass to Instagram                                     |
| set_device(device: dict)                     | bool      | Change device settings                                                            |
| set_user_agent(user_agent: str = "")         | bool      | Change User-Agent header                                                          |
| base_headers                                 | dict      | Base headers for Instagram                                                        |
| account_info()                               | Account   | Get private info for your account (e.g. email, phone_number)                      |
| account_edit(\**data)                        | Account   | Change profile data (e.g. email, phone_number, username, full_name, biography, external_url) |
| account_change_picture(path: Path)           | UserShort | Change Profile picture                                                            |

Example:

``` python
cl.login("instagrapi", "42")
# cl.login_by_sessionid("peiWooShooghahdi2Eip7phohph0eeng")
cl.set_proxy("socks5://127.0.0.1:30235")
# cl.set_proxy("http://username:password@127.0.0.1:8080")

print(cl.get_settings())
print(cl.user_info(cl.user_id))
```

You can pass settings to the Client (and save cookies), it has the following format:

``` python
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

This values send to Instagram API.

#### Media

Viewing and editing publications (medias)

* `media_id` - String ID `"{media_id}_{user_id}"`, example `"2277033926878261772_1903424587"` (Instagram terminology)
* `media_pk` - Integer ID (real media id), example `2277033926878261772` (Instagram terminology)
* `code` - Short code (slug for media), example `BjNLpA1AhXM` from `"https://www.instagram.com/p/BjNLpA1AhXM/"`
* `url` - URL to media publication

| Method                                                          | Return             | Description                                  |
| --------------------------------------------------------------- | ------------------ | -------------------------------------------- |
| media_id(media_pk: int)                                         | str                | Return media_id by media_pk (e.g. 2277033926878261772 -> 2277033926878261772_1903424587)
| media_pk(media_id: str)                                         | int                | Return media_pk by media_id (e.g. 2277033926878261772_1903424587 -> 2277033926878261772)
| media_pk_from_code(code: str)                                   | int                | Return media_pk
| media_pk_from_url(url: str)                                     | int                | Return media_pk
| user_medias(user_id: int, amount: int = 20)                     | List\[Media]       | Get list of medias by user_id
| media_info(media_pk: int)                                       | Media              | Return media info
| media_delete(media_pk: int)                                     | bool               | Delete media
| media_edit(media_pk: int, caption: str, title: str, usertags: List[Usertag], location: Location) | dict | Change caption for media
| media_user(media_pk: int)                                       | User | Get user info for media
| media_oembed(url: str)                                          | MediaOembed        | Return short media info by media URL
| media_like(media_id: str)                                       | bool               | Like media
| media_unlike(media_id: str)                                     | bool               | Unlike media
| media_seen(media_ids: List[str], skipped_media_ids: List[str])  | bool               | Mark a story as seen
| media_likers(media_id: str)                                     | List\[UserShort]   | Return list of users who liked this post

Example:

``` python
>>> cl.media_pk_from_code("B-fKL9qpeab")
2278584739065882267

>>> cl.media_pk_from_code("B8jnuB2HAbyc0q001y3F9CHRSoqEljK_dgkJjo0")
2243811726252050162

>>> cl.media_pk_from_url("https://www.instagram.com/p/BjNLpA1AhXM/")
1787135824035452364

>>> cl.media_info(1787135824035452364).dict()
{'pk': 1787135824035452364,
 'id': '1787135824035452364_1903424587',
 'code': 'BjNLpA1AhXM',
 'taken_at': datetime.datetime(2018, 5, 25, 15, 46, 53, tzinfo=datetime.timezone.utc),
 'media_type': 8,
 'product_type': '',
 'thumbnail_url': None,
 'location': {'pk': 260916528,
  'name': 'Foros, Crimea',
  'address': '',
  'lng': 33.7878,
  'lat': 44.3914,
  'external_id': 181364832764479,
  'external_id_source': 'facebook_places'},
 'user': {'pk': 1903424587,
  'username': 'adw0rd',
  'full_name': 'Mikhail Andreev',
  'profile_pic_url': HttpUrl('https://scontent-hel3-1.cdninstagram.com/v/t51.2885-19/s150x150/123884060_...&oe=5FD7600E')},
 'comment_count': 0,
 'like_count': 48,
 'caption_text': '@mind__flowers в Форосе под дождём, 24 мая 2018 #downhill #skateboarding #downhillskateboarding #crimea #foros',
 'usertags': [],
 'video_url': None,
 'view_count': 0,
 'video_duration': 0.0,
 'title': '',
 'resources': [{'pk': 1787135361353462176,
   'video_url': HttpUrl('https://scontent-hel3-1.cdninstagram.com/v/t50.2886-16/33464086_3755...0e2362', scheme='https', ...),
   'thumbnail_url': HttpUrl('https://scontent-hel3-1.cdninstagram.com/v/t51.2885-15/e35/3220311...AE7332', scheme='https', ...),
   'media_type': 2},
  {'pk': 1787135762219834098,
   'video_url': HttpUrl('https://scontent-hel3-1.cdninstagram.com/v/t50.2886-16/32895...61320_n.mp4', scheme='https', ...),
   'thumbnail_url': HttpUrl('https://scontent-hel3-1.cdninstagram.com/v/t51.2885-15/e35/3373413....8480_n.jpg', scheme='https', ...),
   'media_type': 2},
  {'pk': 1787133803186894424,
   'video_url': None,
   'thumbnail_url': HttpUrl('https://scontent-hel3-1.cdninstagram.com/v/t51.2885-15/e35/324307712_n.jpg...', scheme='https', ...),
   'media_type': 1}]}

>>> cl.media_oembed("https://www.instagram.com/p/B3mr1-OlWMG/").dict()
{'version': '1.0',
 'title': 'В гостях у ДК @delai_krasivo_kaifui',
 'author_name': 'adw0rd',
 'author_url': 'https://www.instagram.com/adw0rd',
 'author_id': 1903424587,
 'media_id': '2154602296692269830_1903424587',
 'provider_name': 'Instagram',
 'provider_url': 'https://www.instagram.com',
 'type': 'rich',
 'width': 658,
 'height': None,
 'html': '<blockquote>...',
 'thumbnail_url': 'https://instagram.frix7-1.fna.fbcdn.net/v...0655800983_n.jpg',
 'thumbnail_width': 640,
 'thumbnail_height': 480,
 'can_view': True}

```

#### Media Type

* Photo: media_type=1
* Video: media_type=2, product_type=feed
* IGTV:  media_type=2, product_type=igtv
* Reel:  media_type=2, product_type=clips
* Album: media_type=8

#### Story

| Method                                                          | Return      | Description
| --------------------------------------------------------------- | ----------- | ---------------------------------- |
| user_stories(user_id: int, amount: int = None)                  | List[Story] | Get list of stories by user_id
| story_info(story_pk: int, use_cache: bool = True)               | Story       | Return story info
| story_delete(story_pk: int)                                     | bool        | Delete story
| story_seen(story_pks: List[int], skipped_story_pks: List[int])  | bool        | Mark a story as seen


#### Comment

| Method                                             | Return             | Description                                                   |
| -------------------------------------------------- | ------------------ | ------------------------------------------------------------- |
| media_comment(media_id: str, message: str)         | bool               | Add new comment to media                                      |
| media_comments(media_id: str)                      | List\[Comment]     | Get all comments for media                                    |
| comment_like(comment_pk: int)                      | bool               | Like comment                                                  |
| comment_unlike(comment_pk: int)                    | bool               | Unlike comment                                                |


#### User

View a list of a user's medias, following and followers

* `user_id` - Integer ID of user, example `1903424587`

| Method                                             | Return              | Description                                                        |
| -------------------------------------------------- | ------------------- | ------------------------------------------------------------------ |
| user_followers(user_id: int, amount: int = 0)      | Dict\[int, User]    | Get dict of followers users (amount=0 - fetch all followers)       |
| user_following(user_id: int, amount: int = 0)      | Dict\[int, User]    | Get dict of following users (amount=0 - fetch all following users) |
| user_info(user_id: int)                            | User                | Get user info                                                      |
| user_info_by_username(username: str)               | User                | Get user info by username                                          |
| user_follow(user_id: int)                          | bool                | Follow user                                                        |
| user_unfollow(user_id: int)                        | bool                | Unfollow user                                                      |
| user_id_from_username(username: str)               | int                 | Get user_id by username                                            |
| username_from_user_id(user_id: int)                | str                 | Get username by user_id                                            |

Example:

``` python
>>> cl.user_followers(cl.user_id).keys()
dict_keys([5563084402, 43848984510, 1498977320, ...])

>>> cl.user_following(cl.user_id)
{
  8530498223: UserShort(
    pk=8530498223,
    username="something",
    full_name="Example description",
    profile_pic_url=HttpUrl(
      'https://instagram.frix7-1.fna.fbcdn.net/v/t5...9217617140_n.jpg',
      scheme='https',
      host='instagram.frix7-1.fna.fbcdn.net',
      ...
    ),
  ),
  49114585: UserShort(
    pk=49114585,
    username='gx1000',
    full_name='GX1000',
    profile_pic_url=HttpUrl(
      'https://scontent-hel3-1.cdninstagram.com/v/t51.2885-19/10388...jpg',
      scheme='https',
      host='scontent-hel3-1.cdninstagram.com',
      ...
    )
  ),
  ...
}

>>> cl.user_info_by_username('adw0rd').dict()
{'pk': 1903424587,
 'username': 'adw0rd',
 'full_name': 'Mikhail Andreev',
 'is_private': False,
 'profile_pic_url': HttpUrl('https://scontent-hel3-1.cdninstagram.com/v/t51.2885-19/s150x150/123884060_803537687159702_2508263208740189974_n.jpg?...', scheme='https', host='scontent-hel3-1.cdninstagram.com', tld='com', host_type='domain', ...'),
 'is_verified': False,
 'media_count': 102,
 'follower_count': 576,
 'following_count': 538,
 'biography': 'Engineer: Python, JavaScript, Erlang',
 'external_url': HttpUrl('https://adw0rd.com/', scheme='https', host='adw0rd.com', tld='com', host_type='domain', path='/'),
 'is_business': False}
 
```

#### Download Media

| Method                                                       | Return  | Description                                                         |
| ------------------------------------------------------------ | ------- | ------------------------------------------------------------------- |
| photo_download(media_pk: int, folder: Path)                  | Path    | Download photo (path to photo with best resoluton)                  |
| photo_download_by_url(url: str, filename: str, folder: Path) | Path    | Download photo by URL (path to photo with best resoluton)           |
| video_download(media_pk: int, folder: Path)                  | Path    | Download video (path to video with best resoluton)                  |
| video_download_by_url(url: str, filename: str, folder: Path) | Path    | Download Video by URL (path to video with best resoluton)           |
| igtv_download(media_pk: int, folder: Path)                   | Path    | Download IGTV (path to video with best resoluton)                   |
| igtv_download_by_url(url: str, filename: str, folder: Path)  | Path    | Download IGTV by URL (path to video with best resoluton)            |
| album_download(media_pk: int, folder: Path)                  | Path    | Download Album (multiple paths to photo/video with best resolutons) |
| album_download_by_urls(urls: List[str], folder: Path)        | Path    | Download Album by URLs (multiple paths to photo/video)              |

#### Upload Media

Upload medias to your feed. Common arguments:

* `path` - Path to source file
* `caption`  - Text for you post
* `usertags` - List[Usertag] of mention users (see `Usertag` in [types.py](/instagrapi/types.py))
* `location` - Location (e.g. `Location(name='Test', lat=42.0, lng=42.0)`)

| Method                                                                                                                    | Return  | Description                        |
| ------------------------------------------------------------------------------------------------------------------------- | ------- | ---------------------------------- |
| photo_upload(path: Path, caption: str, upload_id: str, usertags: List[Usertag], location: Location)                       | Media   | Upload photo (Support JPG files)   |
| video_upload(path: Path, caption: str, thumbnail: Path, usertags: List[Usertag], location: Location)                      | Media   | Upload video (Support MP4 files)   |
| igtv_upload(path: Path, title: str, caption: str, thumbnail: Path, usertags: List[Usertag], location: Location)           | Media   | Upload IGTV (Support MP4 files)    |
| album_upload(paths: List[Path], caption: str, usertags: List[Usertag], location: Location)                                | Media   | Upload Album (Support JPG and MP4) |

#### Upload Stories

Upload medias to your stories. Common arguments:

* `path` - Path to media file
* `caption` - Caption for story (now use to fetch mentions)
* `thumbnail` - Thumbnail instead capture from source file
* `mentions` - Tag profiles in story
* `locations` - Add locations to story
* `links` - "Swipe Up" links (now use first)
* `hashtags` - Add hashtags to story
* `stickers` - Add stickers to story

| Method                                                                                           | Return   | Description   |
| ------------------------------------------------------------------------------------------------ | -------- | ------------- |
| photo_upload_to_story(path: Path, caption: str, upload_id: str, mentions: List[Usertag], locations: List[StoryLocation], links: List[StoryLink], hashtags: List[StoryHashtag], stickers: List[StorySticker])  | Story  | Upload photo (Support JPG files)
| video_upload_to_story(path: Path, caption: str, thumbnail: Path, mentions: List[Usertag], locations: List[StoryLocation], links: List[StoryLink], hashtags: List[StoryHashtag], stickers: List[StorySticker]) | Story  | Upload video (Support MP4 files)

Examples:

``` python
from instagrapi import Client
from instagrapi.types import Location, StoryMention, StoryLocation, StoryLink, StoryHashtag

cl = Client()
cl.login(USERNAME, PASSWORD)

media_path = cl.video_download(
    cl.media_pk_from_url('https://www.instagram.com/p/CGgDsi7JQdS/')
)
adw0rd = cl.user_info_by_username('adw0rd')
loc = cl.location_complete(Location(name='Test', lat=42.0, lng=42.0))
ht = cl.hashtag_info('dhbastards')

cl.video_upload_to_story(
    media_path,
    "Credits @adw0rd",
    mentions=[StoryMention(user=adw0rd, x=0.49892962, y=0.703125, width=0.8333333333333334, height=0.125)],
    locations=[StoryLocation(location=loc, x=0.33, y=0.22, width=0.4, height=0.7)],
    links=[StoryLink(webUri='https://github.com/adw0rd/instagrapi')],
    hashtags=[StoryHashtag(hashtag=ht, x=0.23, y=0.32, width=0.5, height=0.22)],
)
```

#### Build Story to Upload

| Method                                                | Return     | Description                              |
| ----------------------------------------------------- | ---------- | ---------------------------------------- |
| build_clip(clip: moviepy.Clip, max_duration: int = 0) | StoryBuild | Build CompositeVideoClip with background and mentioned users. Return MP4 file and mentions with coordinates |
| video(max_duration: int = 0)  # in seconds            | StoryBuild | Call build_clip(VideoClip, max_duration) |
| photo(max_duration: int = 0)  # in seconds            | StoryBuild | Call build_clip(ImageClip, max_duration) |

Example:

``` python
from instagrapi.story import StoryBuilder

media_path = cl.video_download(
    cl.media_pk_from_url('https://www.instagram.com/p/CGgDsi7JQdS/')
)
adw0rd = cl.user_info_by_username('adw0rd')

buildout = StoryBuilder(
    media_path,
    'Credits @adw0rd',
    [StoryMention(user=adw0rd)],
    Path('/path/to/background_720x1280.jpg')
).video(15)  # seconds

cl.video_upload_to_story(
    buildout.path,
    "Credits @adw0rd",
    mentions=buildout.mentions,
    links=[StoryLink(webUri='https://github.com/adw0rd/instagrapi')]
)
```

Result:

![](https://github.com/adw0rd/instagrapi/blob/master/examples/dhb.gif)

More stories here https://www.instagram.com/surferyone/


#### Collections

| Method                                                                          | Return             | Description                                      |
| ------------------------------------------------------------------------------- | ------------------ | ------------------------------------------------ |
| collections()                                                                   | List\[Collection]  | Get all account collections
| collection_pk_by_name(name: str)                                                | int                | Get collection_pk by name
| collection_medias_by_name(name: str)                                            | List\[Media]       | Get medias in collection by name
| collection_medias(collection_pk: int, amount: int = 21, last_media_pk: int = 0) | List\[Media]       | Get medias in collection by collection_id; Use **amount=0** to return all medias in collection; Use **last_media_pk** to return medias by cursor
| media_save(media_id: str, collection_pk: int = None)                            | bool               | Save media to collection
| media_unsave(media_id: str, collection_pk: int = None)                          | bool               | Unsave media from collection


#### Insights

Get statistics by medias. Common arguments:

* `post_type` - Media type: "ALL", "CAROUSEL_V2", "IMAGE", "SHOPPING", "VIDEO".
* `time_frame` - Time frame for media publishing date: "ONE_WEEK", "ONE_MONTH", "THREE_MONTHS", "SIX_MONTHS", "ONE_YEAR", "TWO_YEARS".
* `data_ordering` - Data ordering in instagram response: "REACH_COUNT", "LIKE_COUNT", "FOLLOW", "SHARE_COUNT", "BIO_LINK_CLICK", "COMMENT_COUNT", "IMPRESSION_COUNT", "PROFILE_VIEW", "VIDEO_VIEW_COUNT", "SAVE_COUNT".

| Method                                                                                             | Return             | Description                                                   |
| -------------------------------------------------------------------------------------------------- | ------------------ | ------------------------------------------------------------- |
| insights_media_feed_all(post_type: str = "ALL", time_frame: str = "TWO_YEARS", data_ordering: str = "REACH_COUNT", count: int = 0, sleep: int = 2) | list | Return medias with insights |
| insights_account()                                                                                 | dict               | Get statistics by your account                                |
| insights_media(media_pk: int)                                                                      | dict               | Get statistics by your media                                  |

#### Direct

| Method                                                                    | Return              | Description                        |
| ------------------------------------------------------------------------- | ------------------- | ---------------------------------- |
| direct_threads(amount: int = 20)                                          | List[DirectThread]  | Get all Threads                    |
| direct_thread(thread_id: int, amount: int = 20)                           | DirectThread        | Get Thread with Messages           |
| direct_messages(thread_id: int, amount: int = 20)                         | List[DirectMessage] | Get only Messages in Thread        |
| direct_answer(thread_id: int, text: str)                                  | DirectMessage       | Add Message to exist Thread        |
| direct_send(text: str, users: List[int] = [], threads: List[int] = [])    | DirectMessage       | Send Message to Users or Threads   |

#### Location

| Method                                                     | Return         | Description                                                             |
| ---------------------------------------------------------- | -------------- | ----------------------------------------------------------------------- |
| location_search(lat: float, lng: float)                    | List[Location] | Search Location by GEO coordinates
| location_complete(location: Location)                      | Location       | Complete blank fields
| location_build(location: Location)                         | String         | Serialized JSON
| location_info(location_pk: int)                            | Location       | Return Location info (pk, name, address, lng, lat, external_id, external_id_source)
| location_medias_top(location_pk: int, amount: int = 9)     | List[Media]    | Return Top posts by Location
| location_medias_recent(location_pk: int, amount: int = 24) | List[Media]    | Return Most recent posts by Location

#### Hashtag

| Method                                                               | Return              | Description                             |
| -------------------------------------------------------------------- | ------------------- | --------------------------------------- |
| hashtag_info(name: str)                                              | Hashtag             | Return Hashtag info (id, name, picture) |
| hashtag_related_hashtags(name: str)                                  | List[Hashtag]       | Return list of related Hashtags         |
| hashtag_medias_top(name: str, amount: int = 9)                       | List[Media]         | Return Top posts by Hashtag             |
| hashtag_medias_recent(name: str, amount: int = 27)                   | List[Media]         | Return Most recent posts by Hashtag     |

#### Challenge

All challenges solved in the module [challenge.py](/instagrapi/challenge.py)

Automatic submission code from SMS/Email in examples [here](/examples/challenge_resolvers.py)

### Common Exceptions

| Exception                 | Base        | Description                          |
| ------------------------- | ----------- |------------------------------------- |
| ClientError               | Exception   | Base Exception for Instagram calls   |
| GenericRequestError       | ClientError | Base Exception for Request           |
| ClientGraphqlError        | ClientError | Exception for GraphQL calls          |
| ClientJSONDecodeError     | ClientError | JSON Exception                       |
| ClientConnectionError     | ClientError | Connection error                     |
| ClientBadRequestError     | ClientError | HTTP 400 Exception                   |
| ClientForbiddenError      | ClientError | HTTP 403 Exception                   |
| ClientNotFoundError       | ClientError | HTTP 404 Exception                   |
| ClientThrottledError      | ClientError | HTTP 429 Exception                   |
| ClientRequestTimeout      | ClientError | Request Timeout Exception            |
| ClientIncompleteReadError | ClientError | Raised when response interrupted     |
| ClientLoginRequired       | ClientError | Raised when Instagram required Login |
| ReloginAttemptExceeded    | ClientError | Raised when all attempts exceeded    |

### Private Exceptions

| Exception                | Base         | Description                                                 |
| ------------------------ | ------------ |------------------------------------------------------------ |
| PrivateError             | ClientError  | Base Exception for Private calls (received from Instagram)  |
| FeedbackRequired         | PrivateError | Raise when get message=feedback_required                    |
| LoginRequired            | PrivateError | Raise when get message=login_required                       |
| SentryBlock              | PrivateError | Raise when get message=sentry_block                         |
| RateLimitError           | PrivateError | Raise when get message=rate_limit_error                     |
| BadPassword              | PrivateError | Raise when get message=bad_password                         |
| UnknownError             | PrivateError | Raise when get unknown message (new message from instagram) |

### Challenge Exceptions

| Exception                      | Base           | Description                                                 |
| ------------------------------ | -------------- |------------------------------------------------------------ |
| ChallengeError                 | PrivateError   | Base Challenge Exception (received from Instagram)          |
| ChallengeRedirection           | ChallengeError | Raise when get type=CHALLENGE_REDIRECTION                   |
| ChallengeRequired              | ChallengeError | Raise when get message=challenge_required                   |
| SelectContactPointRecoveryForm | ChallengeError | Raise when get challengeType=SelectContactPointRecoveryForm |
| RecaptchaChallengeForm         | ChallengeError | Raise when get challengeType=RecaptchaChallengeForm         |
| SubmitPhoneNumberForm          | ChallengeError | Raise when get challengeType=SubmitPhoneNumberForm          |

### Media Exceptions

| Exception                | Base         | Description                                    |
| ------------------------ | ------------ |----------------------------------------------- |
| MediaError               | PrivateError | Base Media Exception (received from Instagram) |
| MediaNotFound            | MediaError   | Raise when user unavailable                    |

### User Exceptions

| Exception                | Base          | Description                                   |
| ------------------------ | ------------- |---------------------------------------------- |
| UserError                | PrivateError  | Base User Exception (received from Instagram) |
| UserNotFound             | UserError     | Raise when user unavailable                   |

### Collection Exceptions

| Exception                | Base            | Description                                         |
| ------------------------ | --------------- |---------------------------------------------------- |
| CollectionError          | PrivateError    | Base Collection Exception (received from Instagram) |
| CollectionNotFound       | CollectionError | Raise when collection unavailable                   |


### Direct Exceptions

| Exception                | Base           | Description                                    |
| ------------------------ | -------------- |----------------------------------------------- |
| DirectError              | PrivateError   | Base Direct Exception                          |
| DirectThreadNotFound     | DirectError    | Raise when thread not found                    |
| DirectMessageNotFound    | DirectError    | Raise when message in thread not found         |


### Photo Exceptions

| Exception                | Base                | Description                                    |
| ------------------------ | ------------------- |----------------------------------------------- |
| PhotoNotDownload         | PrivateError        | Raise when source photo not found              |
| PhotoNotUpload           | PrivateError        | Raise when photo not upload                    |
| PhotoConfigureError      | PhotoNotUpload      | Raise when photo not configured                |
| PhotoConfigureStoryError | PhotoConfigureError | Raise when photo story not configured          |


### Video Exceptions

| Exception                | Base                | Description                                    |
| ------------------------ | ------------------- | ---------------------------------------------- |
| VideoNotDownload         | PrivateError        | Raise when source video not found              |
| VideoNotUpload           | PrivateError        | Raise when video not upload                    |
| VideoConfigureError      | VideoNotUpload      | Raise when video not configured                |
| VideoConfigureStoryError | VideoConfigureError | Raise when video story not configured          |

### IGTV Exceptions

| Exception                | Base          | Description                                    |
| ------------------------ | ------------- |----------------------------------------------- |
| IGTVNotUpload            | PrivateError  | Raise when IGTV not upload                     |
| IGTVConfigureError       | IGTVNotUpload | Raise when IGTV not configured                 |


### Album Exceptions

| Exception                | Base         | Description                                    |
| ------------------------ | ------------ |----------------------------------------------- |
| AlbumNotDownload         | PrivateError | Raise when album not found                     |
| AlbumUnknownFormat       | PrivateError | Raise when format of media not MP4 or JPG      |
| AlbumConfigureError      | PrivateError | Raise when album not configured                |

## Contribute

First, please [install docker](https://docs.docker.com/install/) on your computer.
Docker must be running correctly for these commands to work.

*If you are using windows, please make sure your editor writes files with linefeed (`\n`) line endings.*

Once you have cloned this repo, run the test suite to see if docker is set up correctly:

```bash
docker-compose run --rm test
```

You can also run just the lint using:

```bash
docker-compose run --rm lint
```
