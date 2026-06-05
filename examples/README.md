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
