# Examples

Runnable examples live in the repository:

* [examples/README.md](https://github.com/subzeroid/instagrapi/blob/master/examples/README.md)
* [examples directory](https://github.com/subzeroid/instagrapi/tree/master/examples)

The examples read credentials and runtime options from environment variables instead of hard-coding secrets:

```bash
export IG_USERNAME="your_username"
export IG_PASSWORD="your_password"
export IG_SESSION_FILE="./ig_settings.json"
```

Common scripts:

| Script | Purpose |
| --- | --- |
| [`public_lookup.py`](https://github.com/subzeroid/instagrapi/blob/master/examples/public_lookup.py) | Public profile lookup with optional `public_transport="curl"`. |
| [`download_user_media.py`](https://github.com/subzeroid/instagrapi/blob/master/examples/download_user_media.py) | Login, list recent media for a username, and download photos/videos/albums. |
| [`upload_media.py`](https://github.com/subzeroid/instagrapi/blob/master/examples/upload_media.py) | Upload a feed photo, feed video, Reel, or Trial Reel. |
| [`upload_story.py`](https://github.com/subzeroid/instagrapi/blob/master/examples/upload_story.py) | Upload a photo or video story, optionally with a link sticker. |
| [`direct_message.py`](https://github.com/subzeroid/instagrapi/blob/master/examples/direct_message.py) | Send a Direct text message to user IDs or thread IDs. |
| [`handle_exception.py`](https://github.com/subzeroid/instagrapi/blob/master/examples/handle_exception.py) | Centralized exception handling for challenges, relogin, and rate limits. |

Examples:

```bash
python examples/public_lookup.py instagram
IG_PUBLIC_TRANSPORT=curl python examples/public_lookup.py instagram
python examples/download_user_media.py instagram --amount 5 --folder ./downloads
python examples/upload_media.py reel ./reel.mp4 --thumbnail ./thumb.jpg --caption "Reel"
python examples/upload_story.py photo ./story.jpg --caption "Story"
python examples/direct_message.py --user-ids 123456789 --text "Hello"
```

Video uploads in Android environments should pass `--thumbnail` or install the optional video extra and configure executable `ffmpeg`. See [Pydroid and ffmpeg](pydroid.md) and [Termux](termux.md).
