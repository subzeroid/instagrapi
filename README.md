[![Package](https://github.com/adw0rd/instagrapi/actions/workflows/python-package.yml/badge.svg?branch=master)](https://github.com/adw0rd/instagrapi/actions/workflows/python-package.yml)
![PyPI](https://img.shields.io/pypi/v/instagrapi)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/instagrapi)
![Checked with mypy](https://img.shields.io/badge/mypy-checked-blue)

[![Donate](https://www.buymeacoffee.com/assets/img/custom_images/yellow_img.png)](https://www.buymeacoffee.com/adw0rd)

# instagrapi

Fast and effective Instagram Private API wrapper (public+private requests and challenge resolver). Use the most recent version of the API from Instagram, which was obtained using [reverse-engineering with Charles Proxy](https://adw0rd.com/2020/03/26/sniffing-instagram-charles-proxy/en/) and [Proxyman](https://proxyman.io/).

*Instagram API valid for **16 May 2021** (last reverse-engineering check)*

Support **Python >= 3.6**

For any other languages (e.g. C++, C#, F#, Golang, Erlang, Haskell, Lisp, Julia, R, Java, Kotlin, Scala, OCaml, JavaScript, Ruby, Rust, Swift, Objective-C, Visual Basic, .NET, Pascal, Perl, Lua, PHP and others), I suggest using [instagrapi-rest](https://github.com/adw0rd/instagrapi-rest)

[Support Chat in Telegram](https://t.me/instagrapi)
![](https://gist.githubusercontent.com/m8rge/4c2b36369c9f936c02ee883ca8ec89f1/raw/c03fd44ee2b63d7a2a195ff44e9bb071e87b4a40/telegram-single-path-24px.svg) and [GitHub Discussions](https://github.com/adw0rd/instagrapi/discussions)


## Features

1. Performs [Public API](https://adw0rd.github.io/instagrapi/usage-guide/fundamentals.html) (web, anonymous) or [Private API](https://adw0rd.github.io/instagrapi/usage-guide/fundamentals.html) (mobile app, authorized) requests depending on the situation (to avoid Instagram limits)
2. [Login](https://adw0rd.github.io/instagrapi/usage-guide/interactions.html) by username and password, including 2FA and by sessionid
3. [Challenge Resolver](https://adw0rd.github.io/instagrapi/usage-guide/interactions.html) have [Email](/examples/challenge_resolvers.py) (as well as recipes for automating receive a code from email) and [SMS handlers](/examples/challenge_resolvers.py)
4. Support [upload](https://adw0rd.github.io/instagrapi/usage-guide/media.html) a Photo, Video, IGTV, Reels, Albums and Stories
5. Support work with [User](https://adw0rd.github.io/instagrapi/usage-guide/user.html), [Media](https://adw0rd.github.io/instagrapi/usage-guide/media.html), [Comment](https://adw0rd.github.io/instagrapi/usage-guide/comment.html), [Insights](https://adw0rd.github.io/instagrapi/usage-guide/insight.html), [Collections](https://adw0rd.github.io/instagrapi/usage-guide/collection.html), [Location](https://adw0rd.github.io/instagrapi/usage-guide/location.html) (Place), [Hashtag](https://adw0rd.github.io/instagrapi/usage-guide/hashtag.html) and [Direct Message](https://adw0rd.github.io/instagrapi/usage-guide/direct.html) objects
6. [Like](https://adw0rd.github.io/instagrapi/usage-guide/media.html), [Follow](https://adw0rd.github.io/instagrapi/usage-guide/user.html), [Edit account](https://adw0rd.github.io/instagrapi/usage-guide/interactions.html) (Bio) and much more else
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

<details>
    <summary>The full example</summary>

```python
from instagrapi import Client
from instagrapi.types import Location, StoryMention, StoryLocation, StoryLink, StoryHashtag

cl = Client()
cl.login(USERNAME, PASSWORD, verification_code="<2FA CODE HERE>")

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
</details>

## Documentation

* [Index](https://adw0rd.github.io/instagrapi/)
* [Getting Started](https://adw0rd.github.io/instagrapi/getting-started.html)
* [Usage Guide](https://adw0rd.github.io/instagrapi/usage-guide/fundamentals.html)
* [Interactions](https://adw0rd.github.io/instagrapi/usage-guide/interactions.html)
  * [`Media`](https://adw0rd.github.io/instagrapi/usage-guide/media.html) - Publication (also called post): Photo, Video, Album, IGTV and Reels
  * [`Resource`](https://adw0rd.github.io/instagrapi/usage-guide/media.html) - Part of Media (for albums)
  * [`MediaOembed`](https://adw0rd.github.io/instagrapi/usage-guide/media.html) - Short version of Media
  * [`Account`](https://adw0rd.github.io/instagrapi/usage-guide/account.html) - Full private info for your account (e.g. email, phone_number)
  * [`User`](https://adw0rd.github.io/instagrapi/usage-guide/user.html) - Full public user data
  * [`UserShort`](https://adw0rd.github.io/instagrapi/usage-guide/user.html) - Short public user data (used in Usertag, Comment, Media, Direct Message)
  * [`Usertag`](https://adw0rd.github.io/instagrapi/usage-guide/user.html) - Tag user in Media (coordinates + UserShort)
  * [`Location`](https://adw0rd.github.io/instagrapi/usage-guide/location.html) - GEO location (GEO coordinates, name, address)
  * [`Hashtag`](https://adw0rd.github.io/instagrapi/usage-guide/hashtag.html) - Hashtag object (id, name, picture)
  * [`Collection`](https://adw0rd.github.io/instagrapi/usage-guide/collection.html) - Collection of medias (name, picture and list of medias)
  * [`Comment`](https://adw0rd.github.io/instagrapi/usage-guide/comment.html) - Comments to Media
  * [`Story`](https://adw0rd.github.io/instagrapi/usage-guide/story.html) - Story
  * [`StoryLink`](https://adw0rd.github.io/instagrapi/usage-guide/story.html) - Link (Swipe up)
  * [`StoryLocation`](https://adw0rd.github.io/instagrapi/usage-guide/story.html) - Tag Location in Story (as sticker)
  * [`StoryMention`](https://adw0rd.github.io/instagrapi/usage-guide/story.html) - Mention users in Story (user, coordinates and dimensions)
  * [`StoryHashtag`](https://adw0rd.github.io/instagrapi/usage-guide/story.html) - Hashtag for story (as sticker)
  * [`StorySticker`](https://adw0rd.github.io/instagrapi/usage-guide/story.html) - Tag sticker to story (for example from giphy)
  * [`StoryBuild`](https://adw0rd.github.io/instagrapi/usage-guide/story.html) - [StoryBuilder](/instagrapi/story.py) return path to photo/video and mention co-ordinates
  * [`DirectThread`](https://adw0rd.github.io/instagrapi/usage-guide/direct.html) - Thread (topic) with messages in Direct Message
  * [`DirectMessage`](https://adw0rd.github.io/instagrapi/usage-guide/direct.html) - Message in Direct Message
  * [`Insight`](https://adw0rd.github.io/instagrapi/usage-guide/insight.html) - Insights for a post
* [Development Guide](https://adw0rd.github.io/instagrapi/development-guide.html)
* [Exceptions](https://adw0rd.github.io/instagrapi/exceptions.html)
