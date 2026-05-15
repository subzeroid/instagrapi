# Pydroid and ffmpeg

Android/Pydroid can run many `instagrapi` flows, but video helpers need special care because Android apps often cannot execute arbitrary binaries from shared storage.

## What needs ffmpeg

`instagrapi` does not need ffmpeg for login, reads, photo uploads, downloads, or normal API requests.

For standard MP4 files, `instagrapi` can read video width, height, and duration with its built-in MP4 parser. If you also pass a thumbnail file, these upload helpers do not need MoviePy/ffmpeg just to analyze the upload:

```python
from pathlib import Path

cl.video_upload(Path("video.mp4"), "caption", thumbnail=Path("thumb.jpg"))
cl.clip_upload(Path("reel.mp4"), "caption", thumbnail=Path("thumb.jpg"))
cl.igtv_upload(Path("video.mp4"), "title", "caption", thumbnail=Path("thumb.jpg"))
cl.video_upload_to_story(Path("story.mp4"), thumbnail=Path("thumb.jpg"))
```

MoviePy/ffmpeg is still required when `instagrapi` has to render or extract media. Install the optional video extra for these flows:

```bash
pip install "instagrapi[video]"
pip install --no-deps "moviepy==2.2.1"
```

The extra is intentionally not part of the default install, because it pulls in NumPy and ffmpeg-related packages that can be hard to build on Android. MoviePy `2.2.1` currently declares `Pillow<12`, but instagrapi keeps `Pillow>=12.2.0` for security fixes; the `--no-deps` install keeps the safe Pillow version. MoviePy `1.x` is no longer supported by instagrapi's video helpers.

* automatic thumbnail generation when `thumbnail` is not provided
* `StoryBuilder`
* `prepare_video()`
* `clip_upload_as_reel_with_music()` and other audio/video composition helpers
* video album uploads, because album video items currently generate thumbnails internally
* non-standard MP4 files that the built-in parser cannot read

## Error

If ffmpeg is missing or cannot be executed, video thumbnail generation can fail with:

```text
RuntimeError: No ffmpeg exe could be found. Install ffmpeg on your system, or set the IMAGEIO_FFMPEG_EXE environment variable.
```

Current `instagrapi` upload helpers raise a clearer error for this thumbnail path:

```text
Could not generate video thumbnail. Pass thumbnail=... or install MoviePy 2.2.1. Install video dependencies with pip install "instagrapi[video]" and then install MoviePy with pip install --no-deps "moviepy==2.2.1". Make sure ffmpeg is executable or set IMAGEIO_FFMPEG_EXE.
```

## Fix

The most reliable Pydroid setup is to pre-process the video outside Pydroid and pass both files:

* `video.mp4` - MP4 file accepted by Instagram, usually H.264 video with AAC audio
* `thumb.jpg` - JPEG thumbnail for the upload

Then call the upload method with `thumbnail=Path("thumb.jpg")`.

If you need automatic thumbnail generation or StoryBuilder inside Pydroid, install the optional video dependencies and MoviePy, install an ffmpeg binary that the Pydroid app can execute, and set `IMAGEIO_FFMPEG_EXE` before running the upload:

```python
import os

os.environ["IMAGEIO_FFMPEG_EXE"] = "/absolute/path/to/ffmpeg"
```

Verify the same Python process can execute it:

```python
import os
import subprocess

subprocess.run([os.environ["IMAGEIO_FFMPEG_EXE"], "-version"], check=True)
```

If this raises `PermissionError`, the file exists but Android is not allowing Pydroid to execute it. A binary placed under shared storage such as `/storage/emulated/0/...` can hit that limitation. Move ffmpeg to a location executable by the app or use a Pydroid package/plugin that provides an executable binary.

## Minimal upload example

```python
from pathlib import Path

from instagrapi import Client

cl = Client()
cl.login(USERNAME, PASSWORD)

media = cl.clip_upload(
    Path("reel.mp4"),
    "Uploaded from Pydroid",
    thumbnail=Path("reel-thumb.jpg"),
)
print(media.pk)
```

If you omit `thumbnail=...`, Pydroid must have a working ffmpeg executable so `instagrapi` can capture a frame from the video.
