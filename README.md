# instagrapi

[![PyPI](https://img.shields.io/pypi/v/instagrapi)](https://pypi.org/project/instagrapi/)
[![Python](https://img.shields.io/pypi/pyversions/instagrapi)](https://pypi.org/project/instagrapi/)
[![License](https://img.shields.io/pypi/l/instagrapi)](LICENSE)
[![Package](https://github.com/subzeroid/instagrapi/actions/workflows/python-package.yml/badge.svg)](https://github.com/subzeroid/instagrapi/actions/workflows/python-package.yml)
[![Docs](https://img.shields.io/badge/docs-gh--pages-blue)](https://subzeroid.github.io/instagrapi/)

Fast and effective unofficial Instagram API wrapper for Python.

`instagrapi` combines public web and private mobile API flows, supports session persistence and challenge handling, and covers the main automation primitives for users, media, stories, direct messages, notes, locations, comments, insights, and uploads.

If you want to work with Instagrapi for business interests, prefer [HikerAPI SaaS](https://hikerapi.com/p/bkXQlaVe).
You will not need to spend weeks or even months setting it up.
The service handles millions of daily requests, provides round-the-clock support, and offers partners a special rate.
In many cases, clients first try to save money with self-hosted private API automation, then return to [HikerAPI SaaS](https://hikerapi.com/p/bkXQlaVe) after spending more time and money on accounts, proxies, and challenge handling.
It is difficult to find good accounts, good proxies, resolve challenges reliably, and keep Instagram from banning accounts.

The instagrapi project is better suited for testing and research than for running a production business.

✨ [aiograpi - Asynchronous Python library for Instagram Private API](https://github.com/subzeroid/aiograpi) ✨

Support **Python 3.10+**

`Python 3.9` remains in maintenance support through **December 31, 2026**.
This transition keeps current users stable while aligning the main supported range with modern dependency security and tooling compatibility. In particular, newer `requests` releases now target `Python 3.10+`, which is one of the reasons `Python 3.9` is now maintenance-only.

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

* Uses [Web API](https://subzeroid.github.io/instagrapi/usage-guide/fundamentals.html) and [Mobile API](https://subzeroid.github.io/instagrapi/usage-guide/fundamentals.html) flows where available
* Supports login by password, 2FA, and `sessionid`
* Includes email/SMS-based [challenge resolver](https://subzeroid.github.io/instagrapi/usage-guide/challenge_resolver.html) hooks
* Uploads and downloads photos, videos, albums, IGTV, reels, and stories
* Works with users, media, comments, locations, hashtags, collections, notes, direct messages, and insights
* Supports story building with mentions, hashtags, link stickers, and media stickers
* Includes helpers for current location search and notes flows

Anonymous/public web paths are best treated as opportunistic rather than guaranteed. Instagram can change or restrict them independently of the library, so production-grade workflows should prefer authenticated sessions.

## Documentation And Support

* [Documentation index](https://subzeroid.github.io/instagrapi/)
* [Getting Started](https://subzeroid.github.io/instagrapi/getting-started.html)
* [Usage Guide](https://subzeroid.github.io/instagrapi/usage-guide/fundamentals.html)
* [Interactions reference](https://subzeroid.github.io/instagrapi/usage-guide/interactions.html)
* [Best Practices](https://subzeroid.github.io/instagrapi/usage-guide/best-practices.html) for sessions, proxies, and anti-abuse handling
* [Handle Exceptions](https://subzeroid.github.io/instagrapi/usage-guide/handle_exception.html) for centralizing `429`, challenge, and relogin logic
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

## Ecosystem And Hosted Options

If you need async Python, use [aiograpi](https://github.com/subzeroid/aiograpi).

If you need hosted infrastructure instead of maintaining accounts, proxies, and challenge handling yourself, consider:

* [HikerAPI](https://hikerapi.com/p/bkXQlaVe) for production-grade hosted Instagram API infrastructure
* [Cloqly](https://cloqly.com/register?ref=58dbf70f) for premium rotating proxies and stable automation traffic
* [DataLikers](https://datalikers.com/p/S9Lv5vBy) for Instagram MCP, Cache API, and datasets
* [LamaTok](https://lamatok.com/p/B9ScEYIQ) for TikTok API access, automation, and data workflows
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
