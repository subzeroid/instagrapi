# instagrapi

> ⚠️ **Telegram support group moved to [aiograpi_support](https://t.me/aiograpi_support)** — the previous `@instagrapi` group has been restricted by Meta and is no longer maintained.

[![PyPI](https://img.shields.io/pypi/v/instagrapi)](https://pypi.org/project/instagrapi/)
[![Python](https://img.shields.io/pypi/pyversions/instagrapi)](https://pypi.org/project/instagrapi/)
[![License](https://img.shields.io/pypi/l/instagrapi)](LICENSE)
[![Package](https://github.com/subzeroid/instagrapi/actions/workflows/python-package.yml/badge.svg)](https://github.com/subzeroid/instagrapi/actions/workflows/python-package.yml)
[![Docs](https://img.shields.io/badge/docs-gh--pages-blue)](https://subzeroid.github.io/instagrapi/)

Fast and effective unofficial Instagram API wrapper for Python.

`instagrapi` combines public web and private mobile API flows, supports session persistence and challenge handling, and covers the main automation primitives for users, media, stories, direct messages, notes, locations, comments, insights, and uploads.

Private API automation is fragile in production because account trust, proxies, device state, challenges, and rate limits can change independently of the library.
For account-owned business workflows, prefer official Instagram APIs where they cover your use case.
For production private API infrastructure, a hosted provider such as [HikerAPI](https://hikerapi.com/) may be a better fit than maintaining accounts, proxies, and challenge handling yourself.

The instagrapi project is best suited for testing, research, and controlled internal automation.

✨ [aiograpi - Asynchronous Python library for Instagram Private API](https://github.com/subzeroid/aiograpi) ✨

Support **Python 3.10+**

`Python 3.9` support was dropped in `2.5.0`. Upstream security patches for Pillow `12.x` and pytest `9.x` are not backported to `Python 3.9`, leaving conditional pins permanently exposed to known CVEs. Users who need `Python 3.9` should pin to `instagrapi==2.4.5`.

## Installation

```bash
pip install instagrapi
```

Optional public web TLS impersonation support is available as an extra:

```bash
pip install "instagrapi[curl]"
```

Use it only for public web endpoints that are sensitive to browser TLS fingerprints:

```python
cl = Client(public_transport="curl", public_transport_impersonate="chrome136")
```

See the [public transport guide](docs/usage-guide/public-transport.md) for live comparison results and caveats.

TLS certificate verification is enabled by default. For a trusted debugging MITM proxy, prefer `Client(tls_verify="/path/to/proxy-ca.pem")`; use `Client(tls_verify=False)` only for temporary local debugging because it allows session interception.

If your project uses [uv](https://docs.astral.sh/uv/), you can add the package with:

```bash
uv add instagrapi
```

Or install it into the active virtual environment:

```bash
uv pip install instagrapi
```

Video uploads can use a built-in MP4 metadata parser when you provide `thumbnail=...`. Automatic thumbnail generation, `StoryBuilder`, and video/audio composition still need the optional video dependencies, MoviePy `2.2.1`, and executable `ffmpeg`:

```bash
pip install "instagrapi[video]"
pip install --no-deps "moviepy==2.2.1"
```

MoviePy `2.2.1` currently declares `Pillow<12`, but instagrapi keeps `Pillow>=12.2.0` for security fixes; the `--no-deps` install keeps the safe Pillow version. If your project imports MoviePy directly, migrate any MoviePy `1.x` code from `moviepy.editor`, `set_*`, `resize`, and `subclip` APIs to the MoviePy `2.x` API before upgrading.

Android users should see [Pydroid and ffmpeg](docs/usage-guide/pydroid.md) and [Termux](docs/usage-guide/termux.md).

## Quick Start

``` python
from instagrapi import Client

cl = Client()
cl.login(ACCOUNT_USERNAME, ACCOUNT_PASSWORD)

user_id = cl.user_id_from_username(ACCOUNT_USERNAME)
medias = cl.user_medias(user_id, 20)
```

## Runnable Examples

Practical scripts live in [examples/README.md](examples/README.md). They cover session login, public lookups, media
downloads, feed uploads, Reels and Trial Reels, story uploads, Direct messages, proxies, challenge handling, and optional
curl-backed public transport.

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

`login_by_sessionid()` is best treated as a lightweight compatibility path. For long-lived automation, prefer the normal `login() -> dump_settings() -> load_settings()/set_settings()` session flow.

If a browser/web `sessionid` returns `login_required` or logs the browser out, Instagram rejected that session for the private mobile API. Use a stable password login once, save settings with `dump_settings()`, and reuse those settings instead of repeatedly importing browser cookies.

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
* Supports login by password, 2FA, `sessionid`, and [Bloks 2FA](https://subzeroid.github.io/instagrapi/usage-guide/totp.html#bloks-two-factor-flow) fallback/helpers for newer verification flows
* Includes email/SMS-based [challenge resolver](https://subzeroid.github.io/instagrapi/usage-guide/challenge_resolver.html) hooks
* Uploads and downloads photos, videos, albums, IGTV, reels, and stories
* Works with users, media, comments, locations, hashtags, collections, notes, direct messages, and insights
* Supports story building with mentions, hashtags, link stickers, and media stickers
* Includes helpers for current location search and notes flows
* Supports mobile follower sorting with `date_followed_latest` and `date_followed_earliest`
* App-side discovery surfaces: `chaining`, `fetch_suggestion_details`, `discover_recommended_accounts_for_category_v1`, `user_stream_*`, `user_web_profile_info_v1`
* v2 search SERPs: `fbsearch_accounts_v2`, `fbsearch_reels_v2`, `fbsearch_topsearch_v2`, `fbsearch_typehead`
* Alternative media-info path (`media_info_v2`) for ad-tagged / sponsored media that the canonical endpoint refuses

Anonymous/public web paths are best treated as opportunistic rather than guaranteed. Instagram can change or restrict them independently of the library, so production-grade workflows should prefer authenticated sessions.

## Documentation And Support

API reference and full usage guide live at [subzeroid.github.io/instagrapi](https://subzeroid.github.io/instagrapi/):

* [Documentation index](https://subzeroid.github.io/instagrapi/)
* [Getting Started](https://subzeroid.github.io/instagrapi/getting-started.html)
* [Usage Guide](https://subzeroid.github.io/instagrapi/usage-guide/fundamentals.html)
* [Interactions reference](https://subzeroid.github.io/instagrapi/usage-guide/interactions.html)
* [Best Practices](https://subzeroid.github.io/instagrapi/usage-guide/best-practices.html) for sessions, proxies, and anti-abuse handling
* [Handle Exceptions](https://subzeroid.github.io/instagrapi/usage-guide/handle_exception.html) for centralizing `429`, challenge, and relogin logic
* [GitHub Discussions](https://github.com/subzeroid/instagrapi/discussions)
* Support chat in Telegram: [aiograpi_support](https://t.me/aiograpi_support) — the previous `@instagrapi` group was restricted by Meta and is no longer maintained

For other languages, consider [instagrapi-rest](https://github.com/subzeroid/instagrapi-rest). For async Python, see [aiograpi](https://github.com/subzeroid/aiograpi).

## Tutorials

Hands-on guides for real instagrapi work — login flows, sessions, proxies, scraping, posting, error handling — live at [instagrapi.com/guides](https://instagrapi.com/guides/):

* [Instagram Private API in Python](https://instagrapi.com/guides/instagram-private-api-python/) — pillar walkthrough: login, sessions, fetching, posting
* [2FA and `challenge_required`](https://instagrapi.com/guides/instagrapi-2fa-challenge/)
* [Session persistence: file, Redis, and Postgres patterns](https://instagrapi.com/guides/instagrapi-session-persistence/)
* [Configuring proxies (HTTP, SOCKS5, residential)](https://instagrapi.com/guides/instagrapi-proxy-setup/)
* [Instagram scraper in Python: a working setup](https://instagrapi.com/guides/instagram-scraper-python/)
* [Upload a photo from Python](https://instagrapi.com/guides/instagrapi-upload-photo-python/)
* [Download Instagram stories](https://instagrapi.com/guides/instagrapi-download-stories-python/)
* [Common errors reference](https://instagrapi.com/guides/errors/) — `bad_password`, `challenge_required`, `login_required`, `please_wait_a_few_minutes`, `feedback_required`, `proxy_address_is_blocked`
* [`BadPassword`: correct password rejected by Instagram](https://instagrapi.com/guides/errors/bad-password/) — proxy/IP/device/session trust troubleshooting
* [Framework integrations](https://instagrapi.com/guides/integrations/) — Django, FastAPI, Celery, Docker, AWS Lambda

Comparing instagrapi to other tools:

* [instagrapi vs Instaloader](https://instagrapi.com/compare/instaloader/) — download-only vs authenticated automation
* [instagrapi vs aiograpi](https://instagrapi.com/guides/instagrapi-vs-aiograpi/) — sync or async
* [Instagram API libraries by language](https://instagrapi.com/guides/instagram-api-libraries-by-language/) — what's actually maintained in 2026


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

## Related Projects

If you need async Python, use [aiograpi](https://github.com/subzeroid/aiograpi).

For other languages, see [instagrapi-rest](https://github.com/subzeroid/instagrapi-rest).
For hosted production Instagram API infrastructure, see [HikerAPI](https://hikerapi.com/).

Related services:

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

For local setup, tests, linting, and pull request expectations, see [CONTRIBUTING.md](CONTRIBUTING.md) and the [development guide](https://subzeroid.github.io/instagrapi/development-guide.html).

Maintainer release commands:

```bash
git tag -a X.Y.Z -m "Release X.Y.Z"
git push origin X.Y.Z
git push codeberg X.Y.Z
```

The tag-based `publish.yml` workflow publishes to PyPI via trusted publishing and creates the GitHub release.

## License

`instagrapi` is distributed under the [MIT License](LICENSE).
