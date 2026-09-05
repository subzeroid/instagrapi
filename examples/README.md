# instagrapi Examples

These scripts are small runnable starting points for common `instagrapi` tasks.
They keep credentials out of source code and use environment variables so they can be copied into applications without
hard-coded secrets.

## Setup

Install the package and export credentials:

```bash
python -m pip install -U instagrapi

export IG_USERNAME="your_username"
export IG_PASSWORD="your_password"
export IG_SESSION_FILE="./ig_settings.json"
```

Optional settings:

```bash
export IG_PROXY="http://user:pass@host:port"
export IG_PUBLIC_TRANSPORT="curl"
export IG_PUBLIC_TRANSPORT_IMPERSONATE="chrome136"
```

`IG_SESSION_FILE` is reused between runs. Keep that file private; it contains session data.

## Scripts

| Script | Purpose |
| --- | --- |
| [`_common.py`](_common.py) | Shared login, proxy, session, and environment helpers used by the examples. |
| [`session_login.py`](session_login.py) | Minimal session persistence and `sessionid` login sample. |
| [`diagnose_login.py`](diagnose_login.py) | Capture sanitized HTTP diagnostics for password login, CAA fallback, and challenges. |
| [`public_lookup.py`](public_lookup.py) | Public profile lookup with optional `public_transport="curl"`. |
| [`download_user_media.py`](download_user_media.py) | Login, list recent media for a username, and download photos/videos/albums. |
| [`monitor_user_content.py`](monitor_user_content.py) | Poll a small set of users for new posts and stories using a saved session. |
| [`upload_media.py`](upload_media.py) | Upload a feed photo, feed video, Reel, or Trial Reel. |
| [`upload_story.py`](upload_story.py) | Upload a photo or video story, optionally with a link sticker. |
| [`direct_message.py`](direct_message.py) | Send a Direct text message to user IDs or thread IDs. |
| [`handle_exception.py`](handle_exception.py) | Centralized exception handling pattern for challenges, relogin, and rate limits. |
| [`challenge_resolvers.py`](challenge_resolvers.py) | Email/SMS challenge resolver hooks. |
| [`next_proxy.py`](next_proxy.py) | Example proxy rotation scaffold. |
| [`download_all_medias.py`](download_all_medias.py) | Larger download script for account media. |

## Login diagnostics

Run [`diagnose_login.py`](diagnose_login.py) in the same Python environment and with the same
`instagrapi` version as the failing script. It is standalone: downloading that one file is enough;
keep your installed library version unchanged while collecting evidence.

```bash
python examples/diagnose_login.py --settings session.json --report login-diagnostic.json --relogin
```

If you downloaded the file outside the repository, use `python diagnose_login.py` with the same options.
Point `--settings` at the settings file your script already uses. An existing file is loaded before login;
otherwise a new client identity is created. Settings are saved even when login fails. `--relogin` tests
password login even with an authorized saved session, preserving its device identifiers. Without it,
the library can validate and reuse the saved session instead.

The script prompts for username/password unless `IG_USERNAME`/`IG_PASSWORD` are set. Add `--proxy`
to enter your usual proxy privately, or keep your existing `IG_PROXY`. Add `--two-factor` to enter a
current 2FA code. It stops at the original challenge response without automatically resolving
email/SMS challenges or changing passwords.

It calls `login()` once, disables transport retries, and applies 10-second connect / 30-second
read timeouts. The normal library login flow can make several requests, including a CAA fallback.
Each response is summarized immediately, before another request can overwrite `last_json`.

Share **only `login-diagnostic.json`**, after reviewing it. It contains fixed endpoint labels, HTTP
statuses, content types, response sizes, and allowlisted error categories. Unknown messages and values
become `other`; response bodies, full URLs, cookies, credentials, IDs, and challenge tokens are omitted.
The separate **settings file is private** and contains session credentials. Both files are written with
owner-only permissions on systems that support them. Exit code `1` is expected when login fails; the
report is still written. Use the next observed failure rather than repeatedly retrying to collect logs.

## Public lookup

```bash
python examples/public_lookup.py instagram
IG_PUBLIC_TRANSPORT=curl python examples/public_lookup.py instagram
```

## Download media

```bash
python examples/download_user_media.py instagram --amount 5 --folder ./downloads
python examples/monitor_user_content.py instagram --stories --interval 900
```

## Upload media

```bash
python examples/upload_media.py photo ./photo.jpg --caption "Hello from instagrapi"
python examples/upload_media.py video ./video.mp4 --thumbnail ./thumb.jpg --caption "Feed video"
python examples/upload_media.py reel ./reel.mp4 --thumbnail ./thumb.jpg --caption "Reel"
python examples/upload_media.py trial-reel ./reel.mp4 --thumbnail ./thumb.jpg --caption "Trial Reel"
```

For Android environments, pass `--thumbnail` for videos and Reels or install `instagrapi[video]`, install MoviePy with `pip install --no-deps "moviepy==2.2.1"`, and configure executable `ffmpeg`.

## Upload story

```bash
python examples/upload_story.py photo ./story.jpg --caption "Story"
python examples/upload_story.py video ./story.mp4 --thumbnail ./thumb.jpg --link https://github.com/subzeroid/instagrapi
```

Story assets should usually be 9:16, for example 720x1280.

## Direct message

```bash
python examples/direct_message.py --user-ids 123456789 --text "Hello"
python examples/direct_message.py --thread-ids 340282366841710301949128122292511813703 --text "Hello thread"
```

Use exactly one target type: `--user-ids` or `--thread-ids`.
