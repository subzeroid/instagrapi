# instagrapi

[![Package](https://github.com/adw0rd/instagrapi/actions/workflows/python-package.yml/badge.svg?branch=master)](https://github.com/adw0rd/instagrapi/actions/workflows/python-package.yml)
[![PyPI](https://img.shields.io/pypi/v/instagrapi)][pypi]
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/instagrapi)][pypi]

Fast and effective Instagram Private API wrapper (public+private requests and challenge resolver). Use the most recent version of the API from Instagram, which was obtained using [reverse-engineering with Charles Proxy](https://adw0rd.com/2020/03/26/sniffing-instagram-charles-proxy/en/) and [Proxyman](https://proxyman.io/).

Support **Python >= 3.6**

For any other languages (e.g. C++, C#, F#, Golang, Erlang, Haskell, Lisp, Julia, R, Java, Kotlin, Scala, OCaml, JavaScript, Ruby, Rust, Swift, Objective-C, Visual Basic, .NET, Pascal, Perl, Lua, PHP and others), I suggest using [instagrapi-rest](https://github.com/adw0rd/instagrapi-rest)

Instagram API valid for 13 May 2021 (last reverse-engineering check)

[Support Chat in Telegram](https://t.me/instagrapi)
![](https://gist.githubusercontent.com/m8rge/4c2b36369c9f936c02ee883ca8ec89f1/raw/c03fd44ee2b63d7a2a195ff44e9bb071e87b4a40/telegram-single-path-24px.svg) and [GitHub Discussions](https://github.com/adw0rd/instagrapi/discussions)

## Features

1. Performs Public API (web, anonymous) or Private API (mobile app, authorized) requests depending on the situation (to avoid Instagram limits)
1. Login by username and password, including 2fa and by sessionid
1. Challenge Resolver have Email (as well as recipes for automating receive a code from email) and SMS handlers
1. Support upload a Photo, Video, IGTV, Reels, Albums and Stories
1. Support work with User, Media, Insights, Collections, Location (Place), Hashtag and Direct objects
1. Like, Follow, Edit account (Bio) and much more else
1. Insights by account, posts and stories
1. Build stories with custom background, font animation, swipe up link and mention users
1. In the next release, account registration and captcha passing will appear

## Example

### Basic Usage

``` python
from instagrapi import Client

cl = Client()
cl.login(ACCOUNT_USERNAME, ACCOUNT_PASSWORD)

user_id = cl.user_id_from_username("adw0rd")
medias = cl.user_medias(user_id, 20)
```

#### The full example

``` python
from instagrapi import Client
from instagrapi.types import Location, StoryMention, StoryLocation, StoryLink, StoryHashtag

cl = Client()
cl.login(USERNAME, PASSWORD, verification_code='123456')  # with 2FA verification_code

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

## Detailed Documentation

To learn more about the various ways `instagrapi` can be used, read the [Usage Guide][usage-guide] page.

[ci]: https://github.com/adw0rd/instagrapi/actions
[pypi]: https://pypi.org/project/instagrapi/
[getting-started]: getting-started.md
[usage-guide]: usage-guide/fundamentals.md
[exceptions]: exceptions.md
