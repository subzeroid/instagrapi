# Media

Viewing, downloading, uploading and editing publications

In terms of Instagram, this is called Media, usually users call it publications or posts

### Basic terms:

* `media_id` - String ID `"{media_id}_{user_id}"`, e.g. `"2277033926878261772_1903424587"`
* `media_pk` - Integer ID (real media id), e.g. `2277033926878261772`
* `code` - Short code (slug for media), e.g. `BjNLpA1AhXM` from `"https://www.instagram.com/p/BjNLpA1AhXM/"`
* `url` - URL to media publication, e.g. `"https://www.instagram.com/p/BjNLpA1AhXM/"`

### Media types:

* `Photo` - When media_type=1
* `Video` - When media_type=2 and product_type=feed
* `IGTV`  - When media_type=2 and product_type=igtv
* `Reel`  - When media_type=2 and product_type=clips
* `Album` - When media_type=8

## Viewing and editing publication

| Method                                                          | Return             | Description
| --------------------------------------------------------------- | ------------------ | --------------------------------------------
| media_id(media_pk: int)                                         | str                | Return media_id by media_pk (e.g. 2277033926878261772 -> 2277033926878261772_1903424587)
| media_pk(media_id: str)                                         | int                | Return media_pk by media_id (e.g. 2277033926878261772_1903424587 -> 2277033926878261772)
| media_pk_from_code(code: str)                                   | int                | Return media_pk
| media_pk_from_url(url: str)                                     | int                | Return media_pk
| user_medias(user_id: int, amount: int = 20)                     | List\[Media]       | Get list of medias by user_id
| user_medias_paginated(user_id: int, amount: int = 0, end_cursor: str = "")           | Tuple\[List\[Media], str] | Get one page of medias by user_id 
| usertag_medias(user_id: int, amount: int = 20)                  | List\[Media]       | Get medias where a user is tagged
| media_info(media_pk: int)                                       | Media              | Return media info
| media_delete(media_pk: int)                                     | bool               | Delete media
| media_edit(media_pk: int, caption: str, title: str, usertags: List[Usertag], location: Location) | dict | Change caption for media
| media_user(media_pk: int)                                       | User | Get user info for media
| media_oembed(url: str)                                          | MediaOembed        | Return short media info by media URL
| media_like(media_id: str)                                       | bool               | Like media
| media_unlike(media_id: str)                                     | bool               | Unlike media
| media_seen(media_ids: List[str], skipped_media_ids: List[str])  | bool               | Mark a media as seen
| media_likers(media_id: str)                                     | List\[UserShort]   | Return list of users who liked this post
| media_archive(media_id: str)                                    | bool               | Archive a media
| media_unarchive(media_id: str)                                  | bool               | Unarchive a media

Low level methods:

| Method                                                          | Return       | Description
| --------------------------------------------------------------- | ------------ | --------------------------------------------
| media_info_a1(media_pk: int, max_id: str = None)                | Media        | Get Media from PK by Public Web API
| media_info_gql(media_pk: int)                                   | Media        | Get Media from PK by Public Graphql API
| media_info_v1(media_pk: int)                                    | Media        | Get Media from PK by Private Mobile API
| user_medias_gql(user_id: int, amount: int = 50, sleep: int = 2) | List\[Media] | Get a user's media by Public Graphql API
| user_medias_paginated_gql(user_id: int, amount: int = 50, sleep: int = 2, end_cursor=None) | Tuple\[List\[Media], str] | Get a page of user's media by Public Graphql API
| user_medias_v1(user_id: int, amount: int = 18)                  | List\[Media] | Get a user's media by Private Mobile API
| user_medias_paginated_v1(self, user_id: int, amount: int = 0, end_cursor="") | Tuple\[List\[Media], str] | Get a page of user's media by Private Mobile API
| usertag_medias_gql(user_id: int, amount: int = 20)              | List\[Media] | Get medias where a user is tagged by Public Graphql API
| usertag_medias_v1(user_id: int, amount: int = 20)               | List\[Media] | Get medias where a user is tagged by Private Mobile API

### Example:

``` python
>>> from instagrapi import Client
>>> cl = Client()
>>> cl.login(USERNAME, PASSWORD)

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


>>> cl.media_archive('2155832952940083788_1903424587')
True

>>> cl.media_unarchive('2155832952940083788_1903424587')
True

>>> cl.user_medias_gql(1903424587, amount=1)[0].dict()
{'pk': 2592252466151482347,
 'id': '2592252466151482347_1903424587',
 'code': 'CP5h-I1FuPr',
 'taken_at': datetime.datetime(2021, 6, 9, 12, 9, 56, tzinfo=datetime.timezone.utc),
 'media_type': 8,
 'product_type': '',
 'thumbnail_url': None,
 'location': None,
 'user': {'pk': 1903424587,
  'username': 'adw0rd',
  'full_name': '',
  'profile_pic_url': None,
  'profile_pic_url_hd': None,
  'stories': []},
 'comment_count': 5,
 'like_count': 63,
 'has_liked': None,
 'caption_text': 'Любимые подвески ♥️ @daewon1song @tensortrucks',
 'usertags': [{'user': {'pk': 53860445,
    'username': 'tensortrucks',
    'full_name': '',
    'profile_pic_url': None,
    'profile_pic_url_hd': None,
    'stories': []},
   'x': 0.3146666667,
   'y': 0.368159204}],
 'video_url': None,
 'view_count': 0,
 'video_duration': 0.0,
 'title': '',
 'resources': [{'pk': 2592252463089480898,
   'video_url': None,
   'thumbnail_url': HttpUrl('https://instagram.fhel5-1.fna.fbcdn.net/v/t51.2885-15/e35/s1080x1080/198404255_317668533141074_749682826672118306_n.jpg?_nc_ht=instagram.fhel5-1.fna.fbcdn.net&_nc_cat=102&_nc_ohc=f8FR-bZNbp8AX-A6YQ4&edm=APU89FABAAAA&ccb=7-4&oh=864bb145a4fa7e523f5cc22f9ac5d015&oe=61145E4F&_nc_sid=86f79a', scheme='https', host='instagram.fhel5-1.fna.fbcdn.net', tld='net', host_type='domain', path='/v/t51.2885-15/e35/s1080x1080/198404255_317668533141074_749682826672118306_n.jpg', query='_nc_ht=instagram.fhel5-1.fna.fbcdn.net&_nc_cat=102&_nc_ohc=f8FR-bZNbp8AX-A6YQ4&edm=APU89FABAAAA&ccb=7-4&oh=864bb145a4fa7e523f5cc22f9ac5d015&oe=61145E4F&_nc_sid=86f79a'),
   'media_type': 1},
  {'pk': 2592252463081081550,
   'video_url': None,
   'thumbnail_url': HttpUrl('https://instagram.fhel5-1.fna.fbcdn.net/v/t51.2885-15/e35/s1080x1080/198228498_303261361473979_3031095263106513772_n.jpg?_nc_ht=instagram.fhel5-1.fna.fbcdn.net&_nc_cat=107&_nc_ohc=C9SeKrAO6poAX-nXhCG&edm=APU89FABAAAA&ccb=7-4&oh=6aab825e12fef746449be22c322762a1&oe=61132FB0&_nc_sid=86f79a', scheme='https', host='instagram.fhel5-1.fna.fbcdn.net', tld='net', host_type='domain', path='/v/t51.2885-15/e35/s1080x1080/198228498_303261361473979_3031095263106513772_n.jpg', query='_nc_ht=instagram.fhel5-1.fna.fbcdn.net&_nc_cat=107&_nc_ohc=C9SeKrAO6poAX-nXhCG&edm=APU89FABAAAA&ccb=7-4&oh=6aab825e12fef746449be22c322762a1&oe=61132FB0&_nc_sid=86f79a'),
   'media_type': 1},
  {'pk': 2592252463056089912,
   'video_url': None,
   'thumbnail_url': HttpUrl('https://instagram.fhel5-1.fna.fbcdn.net/v/t51.2885-15/e35/s1080x1080/199142152_323583732599636_4553823395468898634_n.jpg?_nc_ht=instagram.fhel5-1.fna.fbcdn.net&_nc_cat=108&_nc_ohc=_feIkorChpsAX_wzTff&edm=APU89FABAAAA&ccb=7-4&oh=a22a2f5b30772fbbb02db92b9394e981&oe=61147D59&_nc_sid=86f79a', scheme='https', host='instagram.fhel5-1.fna.fbcdn.net', tld='net', host_type='domain', path='/v/t51.2885-15/e35/s1080x1080/199142152_323583732599636_4553823395468898634_n.jpg', query='_nc_ht=instagram.fhel5-1.fna.fbcdn.net&_nc_cat=108&_nc_ohc=_feIkorChpsAX_wzTff&edm=APU89FABAAAA&ccb=7-4&oh=a22a2f5b30772fbbb02db92b9394e981&oe=61147D59&_nc_sid=86f79a'),
   'media_type': 1}]}

# Use paginated interface to resume fetch from stored cursor

>>> end_cursor = None
... for page in range(3):
...     medias, end_cursor = client.user_medias_paginated(1903424587, 5, end_cursor=end_cursor)
...     print([ m.taken_at.date().isoformat() for m in medias ])
...

['2021-06-09', '2019-10-16', '2019-10-14', '2019-06-13', '2019-06-06']
['2019-06-05', '2019-03-23', '2019-03-23', '2018-11-15', '2018-10-16']
['2018-10-16', '2018-10-11', '2018-10-09', '2018-10-09', '2018-08-02']

```

## Download media

| Method                                                       | Return  | Description                                                         |
| ------------------------------------------------------------ | ------- | ------------------------------------------------------------------- |
| photo_download(media_pk: int, folder: Path)                  | Path    | Download photo (path to photo with best resoluton)                  |
| photo_download_by_url(url: str, filename: str, folder: Path) | Path    | Download photo by URL (path to photo with best resoluton)           |
| video_download(media_pk: int, folder: Path)                  | Path    | Download video (path to video with best resoluton)                  |
| video_download_by_url(url: str, filename: str, folder: Path) | Path    | Download Video by URL (path to video with best resoluton)           |
| album_download(media_pk: int, folder: Path)                  | Path    | Download Album (multiple paths to photo/video with best resolutons) |
| album_download_by_urls(urls: List[str], folder: Path)        | Path    | Download Album by URLs (multiple paths to photo/video)              |
| igtv_download(media_pk: int, folder: Path)                   | Path    | Download IGTV (path to video with best resoluton)                   |
| igtv_download_by_url(url: str, filename: str, folder: Path)  | Path    | Download IGTV by URL (path to video with best resoluton)            |
| clip_download(media_pk: int, folder: Path)                   | Path    | Download Reels Clip (path to video with best resoluton)             |
| clip_download_by_url(url: str, filename: str, folder: Path)  | Path    | Download Reels Clip by URL (path to video with best resoluton)      |

### Example:

``` python

>>> from instagrapi import Client
>>> cl = Client()
>>> cl.login(USERNAME, PASSWORD)

>>> cl.media_pk_from_url("https://www.instagram.com/p/BqNQJleFoSJ/")
1913256444155036809

>>> video_url = cl.media_info(1913256444155036809).video_url
>>> cl.video_download_by_url(video_url, folder='/tmp')
PosixPath('/tmp/45588546_367538213983456_6830188946193737023_n.mp4')

```

``` python

>>> cl.media_pk_from_url("http://www.instagram.com/p/BjNLpA1AhXM/")
1787135824035452364

>>> cl.album_download(1787135824035452364)
[PosixPath('/app/adw0rd_1787135361353462176.mp4'),
 PosixPath('/app/adw0rd_1787135762219834098.mp4'),
 PosixPath('/app/adw0rd_1787133803186894424.jpg')]

```

## Upload media

Upload medias to your feed. Common arguments:

* `path` - Path to source file
* `caption`  - Text for you post
* `usertags` - List[Usertag] of mention users (see `Usertag` in [types.py](https://github.com/adw0rd/instagrapi/blob/master/instagrapi/types.py))
* `location` - Location (e.g. `Location(name='Test', lat=42.0, lng=42.0)`)

| Method                                                                                                                                 | Return  | Description
| -------------------------------------------------------------------------------------------------------------------------------------- | ------- | ------------------
| photo_upload(path: Path, caption: str, upload_id: str, usertags: List[Usertag], location: Location, extra_data: Dict = {})             | Media   | Upload photo (Support JPG files)
| video_upload(path: Path, caption: str, thumbnail: Path, usertags: List[Usertag], location: Location, extra_data: Dict = {})            | Media   | Upload video (Support MP4 files)
| album_upload(paths: List[Path], caption: str, usertags: List[Usertag], location: Location, extra_data: Dict = {})                      | Media   | Upload Album (Support JPG/MP4 files)
| igtv_upload(path: Path, title: str, caption: str, thumbnail: Path, usertags: List[Usertag], location: Location, extra_data: Dict = {}) | Media   | Upload IGTV (Support MP4 files)
| clip_upload(path: Path, caption: str, thumbnail: Path, usertags: List[Usertag], location: Location, extra_data: Dict = {})             | Media   | Upload Reels Clip (Support MP4 files)

In `extra_data`, you can pass additional media settings, for example:

| Method                        | Type   | Description
| ----------------------------- | ------ | ------------------
| custom_accessibility_caption  | String | [Set alternative text](https://github.com/adw0rd/instagrapi/issues/351) `{"custom_accessibility_caption": "ALT TEXT HERE"}`
| like_and_view_counts_disabled | Int    | [Disable like and view counts](https://github.com/adw0rd/instagrapi/issues/382) `{"like_and_view_counts_disabled": 1}`
| disable_comments              | Int    | Disable comments `{"disable_comments": 1}`

### Example:

``` python
>>> from instagrapi import Client

>>> cl = Client()
>>> cl.login(USERNAME, PASSWORD)

>>> media = cl.photo_upload(
    "/app/image.jpg",
    "Test caption for photo with #hashtags and mention users such @adw0rd",
    extra_data={
        "custom_accessibility_caption": "alt text example",
        "like_and_view_counts_disabled": 1,
        "disable_comments": 1,
    }
)

>>> media.dict()
{'pk': 2573347427873726764,
 'id': '2573347427873726764_1903424587',
 'code': 'CO2Xdn6FCEs',
 'taken_at': datetime.datetime(2021, 5, 14, 10, 9, tzinfo=datetime.timezone.utc),
 'media_type': 1,
 'product_type': 'feed',
 'thumbnail_url': HttpUrl('https://instagram.fhel5-1.fna.fbcdn.net/v/t51.2885-15/e35/185486538_463522984736407_6315244509641560230_n.jpg?se=8&tp=1&_nc_ht=instagram.fhel5-1.fna.fbcdn.net&_nc_cat=107&_nc_ohc=6tBMsh9HlmMAX9zI_jc&edm=ACqnv0EBAAAA&ccb=7-4&oh=2b46f1e9fbd2416eb7d08b398e0f639e&oe=60C30437&_nc_sid=9ec724&ig_cache_key=MjU3MzM0NzQyNzg3MzcyNjc2NA%3D%3D.2-ccb7-4', scheme='https', host='instagram.fhel5-1.fna.fbcdn.net', tld='net', host_type='domain', path='/v/t51.2885-15/e35/185486538_463522984736407_6315244509641560230_n.jpg', query='se=8&tp=1&_nc_ht=instagram.fhel5-1.fna.fbcdn.net&_nc_cat=107&_nc_ohc=6tBMsh9HlmMAX9zI_jc&edm=ACqnv0EBAAAA&ccb=7-4&oh=2b46f1e9fbd2416eb7d08b398e0f639e&oe=60C30437&_nc_sid=9ec724&ig_cache_key=MjU3MzM0NzQyNzg3MzcyNjc2NA%3D%3D.2-ccb7-4'),
 'location': None,
 'user': {'pk': 1903424587,
  'username': 'adw0rd',
  'full_name': 'Mikhail Andreev',
  'profile_pic_url': HttpUrl('https://instagram.fhel5-1.fna.fbcdn.net/v/t51.2885-19/s150x150/156689363_269505058076642_6448820957073669709_n.jpg?tp=1&_nc_ht=instagram.fhel5-1.fna.fbcdn.net&_nc_ohc=EtzrL0pAdg8AX-Xq8yS&edm=ACqnv0EBAAAA&ccb=7-4&oh=e2fd6a9d362f8587ea8123f23b248f1b&oe=60C2CB91&_nc_sid=9ec724', scheme='https', host='instagram.fhel5-1.fna.fbcdn.net', tld='net', host_type='domain', path='/v/t51.2885-19/s150x150/156689363_269505058076642_6448820957073669709_n.jpg', query='tp=1&_nc_ht=instagram.fhel5-1.fna.fbcdn.net&_nc_ohc=EtzrL0pAdg8AX-Xq8yS&edm=ACqnv0EBAAAA&ccb=7-4&oh=e2fd6a9d362f8587ea8123f23b248f1b&oe=60C2CB91&_nc_sid=9ec724'),
  'stories': []},
 'comment_count': 0,
 'like_count': 0,
 'has_liked': None,
 'caption_text': 'Test caption for photo with #hashtags and mention users such @adw0rd',
 'usertags': [],
 'video_url': None,
 'view_count': 0,
 'video_duration': 0.0,
 'title': '',
 'resources': []}
```

Now let's mention users (Usertag) and location:

``` python
>>> from instagrapi import Client
>>> from instagrapi.types import Usertag, Location

>>> cl = Client()
>>> cl.login(USERNAME, PASSWORD)

>>> adw0rd = cl.user_info_by_username('adw0rd')
>>> media = cl.photo_upload(
    "/app/image.jpg",
    "Test caption for photo with #hashtags and mention users such @adw0rd",
    usertags=[Usertag(user=adw0rd, x=0.5, y=0.5)],
    location=Location(name='Russia, Saint-Petersburg', lat=59.96, lng=30.29)
)

>>> media.dict()
{'pk': 2573355619819242434,
 'id': '2573355619819242434_1903424587',
 'code': 'CO2ZU1QFMPC',
 'taken_at': datetime.datetime(2021, 5, 14, 10, 25, 16, tzinfo=datetime.timezone.utc),
 'media_type': 1,
 'product_type': 'feed',
 'thumbnail_url': HttpUrl('https://instagram.fhel5-1.fna.fbcdn.net/v/t51.2885-15/e35/185426950_474602463640866_4228057388625412955_n.jpg?se=8&tp=1&_nc_ht=instagram.fhel5-1.fna.fbcdn.net&_nc_cat=106&_nc_ohc=7NrVvAEG7f4AX_XPaOK&edm=ACqnv0EBAAAA&ccb=7-4&oh=bd2c90c2dcb693184e07c2777e09bb0b&oe=60C4E326&_nc_sid=9ec724&ig_cache_key=MjU3MzM1NTYxOTgxOTI0MjQzNA%3D%3D.2-ccb7-4', scheme='https', host='instagram.fhel5-1.fna.fbcdn.net', tld='net', host_type='domain', path='/v/t51.2885-15/e35/185426950_474602463640866_4228057388625412955_n.jpg', query='se=8&tp=1&_nc_ht=instagram.fhel5-1.fna.fbcdn.net&_nc_cat=106&_nc_ohc=7NrVvAEG7f4AX_XPaOK&edm=ACqnv0EBAAAA&ccb=7-4&oh=bd2c90c2dcb693184e07c2777e09bb0b&oe=60C4E326&_nc_sid=9ec724&ig_cache_key=MjU3MzM1NTYxOTgxOTI0MjQzNA%3D%3D.2-ccb7-4'),
 'location': {'pk': 107617247320879,
  'name': 'Russia, Saint-Petersburg',
  'address': 'Russia, Saint-Petersburg',
  'lng': 30.30605,
  'lat': 59.93318,
  'external_id': 107617247320879,
  'external_id_source': 'facebook_places'},
 'user': {'pk': 1903424587,
  'username': 'adw0rd',
  'full_name': 'Mikhail Andreev',
  'profile_pic_url': HttpUrl('https://instagram.fhel5-1.fna.fbcdn.net/v/t51.2885-19/s150x150/156689363_269505058076642_6448820957073669709_n.jpg?tp=1&_nc_ht=instagram.fhel5-1.fna.fbcdn.net&_nc_ohc=EtzrL0pAdg8AX-Xq8yS&edm=ACqnv0EBAAAA&ccb=7-4&oh=e2fd6a9d362f8587ea8123f23b248f1b&oe=60C2CB91&_nc_sid=9ec724', scheme='https', host='instagram.fhel5-1.fna.fbcdn.net', tld='net', host_type='domain', path='/v/t51.2885-19/s150x150/156689363_269505058076642_6448820957073669709_n.jpg', query='tp=1&_nc_ht=instagram.fhel5-1.fna.fbcdn.net&_nc_ohc=EtzrL0pAdg8AX-Xq8yS&edm=ACqnv0EBAAAA&ccb=7-4&oh=e2fd6a9d362f8587ea8123f23b248f1b&oe=60C2CB91&_nc_sid=9ec724'),
  'stories': []},
 'comment_count': 0,
 'like_count': 0,
 'has_liked': None,
 'caption_text': 'Test caption for photo with #hashtags and mention users such @adw0rd',
 'usertags': [{'user': {'pk': 1903424587,
    'username': 'adw0rd',
    'full_name': 'Mikhail Andreev',
    'profile_pic_url': HttpUrl('https://instagram.fhel5-1.fna.fbcdn.net/v/t51.2885-19/s150x150/156689363_269505058076642_6448820957073669709_n.jpg?tp=1&_nc_ht=instagram.fhel5-1.fna.fbcdn.net&_nc_ohc=EtzrL0pAdg8AX-Xq8yS&edm=ACqnv0EBAAAA&ccb=7-4&oh=e2fd6a9d362f8587ea8123f23b248f1b&oe=60C2CB91&_nc_sid=9ec724', scheme='https', host='instagram.fhel5-1.fna.fbcdn.net', tld='net', host_type='domain', path='/v/t51.2885-19/s150x150/156689363_269505058076642_6448820957073669709_n.jpg', query='tp=1&_nc_ht=instagram.fhel5-1.fna.fbcdn.net&_nc_ohc=EtzrL0pAdg8AX-Xq8yS&edm=ACqnv0EBAAAA&ccb=7-4&oh=e2fd6a9d362f8587ea8123f23b248f1b&oe=60C2CB91&_nc_sid=9ec724'),
    'stories': []},
   'x': 0.5,
   'y': 0.5}],
 'video_url': None,
 'view_count': 0,
 'video_duration': 0.0,
 'title': '',
 'resources': []}
```
