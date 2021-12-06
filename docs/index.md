# instagrapi

[![Package](https://github.com/adw0rd/instagrapi/actions/workflows/python-package.yml/badge.svg?branch=master)](https://github.com/adw0rd/instagrapi/actions/workflows/python-package.yml)
[![PyPI](https://img.shields.io/pypi/v/instagrapi)][pypi]
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/instagrapi)][pypi]

Fast and effective Instagram Private API wrapper (public+private requests and challenge resolver). Use the most recent version of the API from Instagram, which was obtained using [reverse-engineering with Charles Proxy](https://adw0rd.com/2020/03/26/sniffing-instagram-charles-proxy/en/) and [Proxyman](https://proxyman.io/).

*Instagram API valid for **5 December 2021** (last reverse-engineering check)*

Support **Python >= 3.6**, recommend 3.8+

For any other languages (e.g. C++, C#, F#, D, [Golang](https://github.com/adw0rd/instagrapi-rest/tree/main/golang), Erlang, Elixir, Nim, Haskell, Lisp, Closure, Julia, R, Java, Kotlin, Scala, OCaml, JavaScript, Crystal, Ruby, Rust, [Swift](https://github.com/adw0rd/instagrapi-rest/tree/main/swift), Objective-C, Visual Basic, .NET, Pascal, Perl, Lua, PHP and others), I suggest using [instagrapi-rest](https://github.com/adw0rd/instagrapi-rest)

[Support Chat in Telegram](https://t.me/instagrapi)
![](https://gist.githubusercontent.com/m8rge/4c2b36369c9f936c02ee883ca8ec89f1/raw/c03fd44ee2b63d7a2a195ff44e9bb071e87b4a40/telegram-single-path-24px.svg) and [GitHub Discussions](https://github.com/adw0rd/instagrapi/discussions)

## Features

1. Performs [Public API](https://adw0rd.github.io/instagrapi/usage-guide/fundamentals.html) (web, anonymous) or [Private API](https://adw0rd.github.io/instagrapi/usage-guide/fundamentals.html) (mobile app, authorized) requests depending on the situation (to avoid Instagram limits)
2. [Login](https://adw0rd.github.io/instagrapi/usage-guide/interactions.html) by username and password, including 2FA and by sessionid
3. [Challenge Resolver](https://adw0rd.github.io/instagrapi/usage-guide/challenge_resolver.html) have Email and SMS handlers
4. Support [upload](https://adw0rd.github.io/instagrapi/usage-guide/media.html) a Photo, Video, IGTV, Reels, Albums and Stories
5. Support work with [User](https://adw0rd.github.io/instagrapi/usage-guide/user.html), [Media](https://adw0rd.github.io/instagrapi/usage-guide/media.html), [Comment](https://adw0rd.github.io/instagrapi/usage-guide/comment.html), [Insights](https://adw0rd.github.io/instagrapi/usage-guide/insight.html), [Collections](https://adw0rd.github.io/instagrapi/usage-guide/collection.html), [Location](https://adw0rd.github.io/instagrapi/usage-guide/location.html) (Place), [Hashtag](https://adw0rd.github.io/instagrapi/usage-guide/hashtag.html) and [Direct Message](https://adw0rd.github.io/instagrapi/usage-guide/direct.html) objects
6. [Like](https://adw0rd.github.io/instagrapi/usage-guide/media.html), [Follow](https://adw0rd.github.io/instagrapi/usage-guide/user.html), [Edit account](https://adw0rd.github.io/instagrapi/usage-guide/account.html) (Bio) and much more else
7. [Insights](https://adw0rd.github.io/instagrapi/usage-guide/insight.html) by account, posts and stories
8. [Build stories](https://adw0rd.github.io/instagrapi/usage-guide/story.html) with custom background, font animation, swipe up link and mention users
9. In the next release, account registration and captcha passing will appear

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
from instagrapi.types import StoryMention, StoryMedia, StoryLink, StoryHashtag

cl = Client()
cl.login(USERNAME, PASSWORD, verification_code="<2FA CODE HERE>")

media_pk = cl.media_pk_from_url('https://www.instagram.com/p/CGgDsi7JQdS/')
media_path = cl.video_download(media_pk)
adw0rd = cl.user_info_by_username('adw0rd')
hashtag = cl.hashtag_info('dhbastards')

cl.video_upload_to_story(
    media_path,
    "Credits @adw0rd",
    mentions=[StoryMention(user=adw0rd, x=0.49892962, y=0.703125, width=0.8333333333333334, height=0.125)],
    links=[StoryLink(webUri='https://github.com/adw0rd/instagrapi')],
    hashtags=[StoryHashtag(hashtag=hashtag, x=0.23, y=0.32, width=0.5, height=0.22)],
    medias=[StoryMedia(media_pk=media_pk, x=0.5, y=0.5, width=0.6, height=0.8)]
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

To learn more about the various ways `instagrapi` can be used, read the [Usage Guide](usage-guide/fundamentals.md) page.

* [Getting Started](getting-started.md)
* [Usage Guide](usage-guide/fundamentals.md)
* [Interactions](usage-guide/interactions.md)
  * [`Media`](usage-guide/media.md) - Publication (also called post): Photo, Video, Album, IGTV and Reels
  * [`Resource`](usage-guide/media.md) - Part of Media (for albums)
  * [`MediaOembed`](usage-guide/media.md) - Short version of Media
  * [`Account`](usage-guide/account.md) - Full private info for your account (e.g. email, phone_number)
  * [`TOTP`](usage-guide/totp.md) - 2FA TOTP helpers (generate seed, enable/disable TOTP, generate code as Google Authenticator)
  * [`User`](usage-guide/user.md) - Full public user data
  * [`UserShort`](usage-guide/user.md) - Short public user data (used in Usertag, Comment, Media, Direct Message)
  * [`Usertag`](usage-guide/user.md) - Tag user in Media (coordinates + UserShort)
  * [`Location`](usage-guide/location.md) - GEO location (GEO coordinates, name, address)
  * [`Hashtag`](usage-guide/hashtag.md) - Hashtag object (id, name, picture)
  * [`Collection`](usage-guide/collection.md) - Collection of medias (name, picture and list of medias)
  * [`Comment`](usage-guide/comment.md) - Comments to Media
  * [`Highlight`](usage-guide/highlight.md) - Highlights
  * [`Story`](usage-guide/story.md) - Story
  * [`StoryLink`](usage-guide/story.md) - Link (Swipe up)
  * [`StoryLocation`](usage-guide/story.md) - Tag Location in Story (as sticker)
  * [`StoryMention`](usage-guide/story.md) - Mention users in Story (user, coordinates and dimensions)
  * [`StoryHashtag`](usage-guide/story.md) - Hashtag for story (as sticker)
  * [`StorySticker`](usage-guide/story.md) - Tag sticker to story (for example from giphy)
  * [`StoryBuild`](usage-guide/story.md) - [StoryBuilder](https://github.com/adw0rd/instagrapi/blob/master/instagrapi/story.py) return path to photo/video and mention co-ordinates
  * [`DirectThread`](usage-guide/direct.md) - Thread (topic) with messages in Direct Message
  * [`DirectMessage`](usage-guide/direct.md) - Message in Direct Message
  * [`Insight`](usage-guide/insight.md) - Insights for a post
* [Development Guide](development-guide.md)
* [Handle Exceptions](usage-guide/handle_exception.md)
* [Challenge Resolver](usage-guide/challenge_resolver.md)
* [Exceptions](exceptions.md)

[ci]: https://github.com/adw0rd/instagrapi/actions
[pypi]: https://pypi.org/project/instagrapi/
