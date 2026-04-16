# instagrapi

[![PyPI](https://img.shields.io/pypi/v/instagrapi)](https://pypi.org/project/instagrapi/)
[![Python](https://img.shields.io/pypi/pyversions/instagrapi)](https://pypi.org/project/instagrapi/)
[![License](https://img.shields.io/pypi/l/instagrapi)](LICENSE)
[![Docs](https://img.shields.io/badge/docs-gh--pages-blue)](https://subzeroid.github.io/instagrapi/)

Fast and effective unofficial Instagram API wrapper for Python.

`instagrapi` combines public web and private mobile API flows, supports session persistence and challenge handling, and covers the main automation primitives for users, media, stories, direct messages, notes, locations, comments, insights, and uploads.

Support **Python >= 3.9**

## Installation

```
pip install instagrapi
```

## Quick Start

``` python
from instagrapi import Client

cl = Client()
cl.login(ACCOUNT_USERNAME, ACCOUNT_PASSWORD)

user_id = cl.user_id_from_username(ACCOUNT_USERNAME)
medias = cl.user_medias(user_id, 20)
```

## Session Persistence

``` python
from instagrapi import Client

cl = Client()
cl.login(USERNAME, PASSWORD)
cl.dump_settings("session.json")

# reload later without entering credentials again
cl = Client()
cl.load_settings("session.json")
cl.login(USERNAME, PASSWORD)
```

If you want more explicit control over the loaded session object:

```python
from instagrapi import Client

cl = Client()
cl.set_settings(cl.load_settings("session.json"))
cl.login(USERNAME, PASSWORD)
```

### Login using a sessionid

``` python
from instagrapi import Client

cl = Client()
cl.login_by_sessionid("<your_sessionid>")
```

`login_by_sessionid()` is best treated as a lightweight compatibility path. For long-lived automation, prefer the normal
`login() -> dump_settings() -> load_settings()/set_settings()` session flow.

## Typical Tasks

### List and download another user's posts

``` python
from instagrapi import Client

cl = Client()
cl.login(USERNAME, PASSWORD)

target_id = cl.user_id_from_username("target_user")
posts = cl.user_medias(target_id, amount=10)
for media in posts:
    # download photos to the current folder
    cl.photo_download(media.pk)
```
See [examples/session_login.py](examples/session_login.py) for a standalone script demonstrating these login methods.

### Search locations by name or exact pk

```python
from instagrapi import Client

cl = Client()
cl.login(USERNAME, PASSWORD)

places = cl.location_search_name("Times Square")
place = places[0]
same_place = cl.location_search_pk(place.pk)

print(same_place.name, same_place.pk)
```

### Work with Notes

```python
from instagrapi import Client

cl = Client()
cl.login(USERNAME, PASSWORD)

notes = cl.get_notes()
print(cl.get_note_text_by_user(notes, "instagram"))

note = cl.create_note("Hello from instagrapi", audience=0)
cl.delete_note(note.id)
```

## Features

* Uses [Web API](https://subzeroid.github.io/instagrapi/usage-guide/fundamentals.html) or [Mobile API](https://subzeroid.github.io/instagrapi/usage-guide/fundamentals.html) depending on the situation
* Supports login by password, 2FA, and `sessionid`
* Includes email/SMS-based [challenge resolver](https://subzeroid.github.io/instagrapi/usage-guide/challenge_resolver.html) hooks
* Uploads and downloads photos, videos, albums, IGTV, reels, and stories
* Works with users, media, comments, locations, hashtags, collections, notes, direct messages, and insights
* Supports story building with mentions, hashtags, link stickers, and media stickers
* Includes helpers for current location search and notes flows

## Documentation And Support

* [Documentation index](https://subzeroid.github.io/instagrapi/)
* [Getting Started](https://subzeroid.github.io/instagrapi/getting-started.html)
* [Usage Guide](https://subzeroid.github.io/instagrapi/usage-guide/fundamentals.html)
* [GitHub Discussions](https://github.com/subzeroid/instagrapi/discussions)
* [Support chat in Telegram](https://t.me/instagrapi)

For other languages, consider [instagrapi-rest](https://github.com/subzeroid/instagrapi-rest). For async Python, see [aiograpi](https://github.com/subzeroid/aiograpi).


<details>
    <summary>Additional example</summary>

```python
from instagrapi import Client
from instagrapi.types import StoryMention, StoryMedia, StoryLink, StoryHashtag

cl = Client()
cl.login(USERNAME, PASSWORD, verification_code="<2FA CODE HERE>")

media_pk = cl.media_pk_from_url('https://www.instagram.com/p/CGgDsi7JQdS/')
media_path = cl.video_download(media_pk)
subzeroid = cl.user_info_by_username('subzeroid')
hashtag = cl.hashtag_info('dhbastards')

cl.video_upload_to_story(
    media_path,
    "Credits @subzeroid",
    mentions=[StoryMention(user=subzeroid, x=0.49892962, y=0.703125, width=0.8333333333333334, height=0.125)],
    links=[StoryLink(webUri='https://github.com/subzeroid/instagrapi')],
    hashtags=[StoryHashtag(hashtag=hashtag, x=0.23, y=0.32, width=0.5, height=0.22)],
    medias=[StoryMedia(media_pk=media_pk, x=0.5, y=0.5, width=0.6, height=0.8)]
)
```
</details>

## Documentation

* [Index](https://subzeroid.github.io/instagrapi/)
* [Getting Started](https://subzeroid.github.io/instagrapi/getting-started.html)
* [Usage Guide](https://subzeroid.github.io/instagrapi/usage-guide/fundamentals.html)
* [Interactions](https://subzeroid.github.io/instagrapi/usage-guide/interactions.html)
  * [`Media`](https://subzeroid.github.io/instagrapi/usage-guide/media.html) - Publication (also called post): Photo, Video, Album, IGTV and Reels
  * [`Resource`](https://subzeroid.github.io/instagrapi/usage-guide/media.html) - Part of Media (for albums)
  * [`MediaOembed`](https://subzeroid.github.io/instagrapi/usage-guide/media.html) - Short version of Media
  * [`Account`](https://subzeroid.github.io/instagrapi/usage-guide/account.html) - Full private info for your account (e.g. email, phone_number)
  * [`TOTP`](https://subzeroid.github.io/instagrapi/usage-guide/totp.html) - 2FA TOTP helpers (generate seed, enable/disable TOTP, generate code as Google Authenticator)
  * [`User`](https://subzeroid.github.io/instagrapi/usage-guide/user.html) - Full public user data
  * [`UserShort`](https://subzeroid.github.io/instagrapi/usage-guide/user.html) - Short public user data (used in Usertag, Comment, Media, Direct Message)
  * [`Usertag`](https://subzeroid.github.io/instagrapi/usage-guide/user.html) - Tag user in Media (coordinates + UserShort)
  * [`Location`](https://subzeroid.github.io/instagrapi/usage-guide/location.html) - GEO location (GEO coordinates, name, address)
  * [`Hashtag`](https://subzeroid.github.io/instagrapi/usage-guide/hashtag.html) - Hashtag object (id, name, picture)
  * [`Collection`](https://subzeroid.github.io/instagrapi/usage-guide/collection.html) - Collection of medias (name, picture and list of medias)
  * [`Comment`](https://subzeroid.github.io/instagrapi/usage-guide/comment.html) - Comments to Media
  * [`Highlight`](https://subzeroid.github.io/instagrapi/usage-guide/highlight.html) - Highlights
  * [`Notes`](https://subzeroid.github.io/instagrapi/usage-guide/notes.html) - Notes
  * [`Story`](https://subzeroid.github.io/instagrapi/usage-guide/story.html) - Story
  * [`StoryLink`](https://subzeroid.github.io/instagrapi/usage-guide/story.html) - Story link sticker
  * [`StoryLocation`](https://subzeroid.github.io/instagrapi/usage-guide/story.html) - Tag Location in Story (as sticker)
  * [`StoryMention`](https://subzeroid.github.io/instagrapi/usage-guide/story.html) - Mention users in Story (user, coordinates and dimensions)
  * [`StoryHashtag`](https://subzeroid.github.io/instagrapi/usage-guide/story.html) - Hashtag for story (as sticker)
  * [`StorySticker`](https://subzeroid.github.io/instagrapi/usage-guide/story.html) - Tag sticker to story (for example from giphy)
  * [`StoryBuild`](https://subzeroid.github.io/instagrapi/usage-guide/story.html) - [StoryBuilder](/instagrapi/story.py) return path to photo/video and mention co-ordinates
  * [`DirectThread`](https://subzeroid.github.io/instagrapi/usage-guide/direct.html) - Thread (topic) with messages in Direct Message
  * [`DirectMessage`](https://subzeroid.github.io/instagrapi/usage-guide/direct.html) - Message in Direct Message
  * [`Insight`](https://subzeroid.github.io/instagrapi/usage-guide/insight.html) - Insights for a post
  * [`Track`](https://subzeroid.github.io/instagrapi/usage-guide/track.html) - Music track (for Reels/Clips)
* [Best Practices](https://subzeroid.github.io/instagrapi/usage-guide/best-practices.html)
* [Development Guide](https://subzeroid.github.io/instagrapi/development-guide.html)
* [Handle Exceptions](https://subzeroid.github.io/instagrapi/usage-guide/handle_exception.html)
* [Challenge Resolver](https://subzeroid.github.io/instagrapi/usage-guide/challenge_resolver.html)
* [Exceptions](https://subzeroid.github.io/instagrapi/exceptions.html)

## Ecosystem And Hosted Options

If you need async Python, use [aiograpi](https://github.com/subzeroid/aiograpi).

If you need hosted infrastructure instead of maintaining accounts, proxies, and challenge handling yourself, consider:

* [HikerAPI](https://hikerapi.com/p/bkXQlaVe) for hosted Instagram API
* [Cloqly](https://cloqly.com/register?ref=58dbf70f) for rotating proxies
* [DataLikers](https://datalikers.com/p/S9Lv5vBy) for Instagram datasets, MCP, and CacheAPI
* [LamaTok](https://lamatok.com/p/B9ScEYIQ) for TikTok API
* [InstaSurfBot](https://t.me/InstaSurfBot) for downloading Instagram media in Telegram
* [OSINTagramBot](https://t.me/OSINTagramBot) for Instagram OSINT in Telegram

### [HikerAPI Affiliate Program](https://hikerapi.com/help/affiliate)

Refer users to HikerAPI and earn a percentage of their API spending:

| Plan | Commission |
|------|------------|
| Start trial plan ($0.02/req) | **50%** |
| Standard ($0.001/req) | **25%** |
| Business ($0.00069/req) | **15%** |
| Ultra ($0.0006/req) | **10%** |

**Extras:** 2-level referral system, no caps, lifetime attribution

**Payouts:** USDT / USDC (TRC-20 or ERC-20), minimum 20 USDT, request anytime from the dashboard

## Contributing

[![List of contributors](https://opencollective.com/instagrapi/contributors.svg?width=890&button=0)](https://github.com/subzeroid/instagrapi/graphs/contributors)

To release, you need to call the following commands:

    python -m build
    twine upload dist/*
