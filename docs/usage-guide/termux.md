# Termux

Termux can run many `instagrapi` flows, but Android does not use the same binary wheel ecosystem as desktop Linux. Keep the default install small and add media tooling only when the script really needs it.

## Install

```bash
pkg update
pkg install python python-pillow
python -m pip install -U pip setuptools wheel
python -m pip install instagrapi
```

`python-pillow` is recommended because photo uploads use Pillow through `instagrapi.image_util`. Installing it with `pkg` avoids a slow or fragile Pillow source build in pip.

## Video Uploads

For standard MP4 uploads, pass your own thumbnail and `instagrapi` can read width, height, and duration with its built-in MP4 parser:

```python
from pathlib import Path

media = cl.clip_upload(
    Path("reel.mp4"),
    "Uploaded from Termux",
    thumbnail=Path("reel-thumb.jpg"),
)
```

This path does not need MoviePy, NumPy, or ffmpeg.

## Optional Video Helpers

Install the optional video extra only if you need automatic thumbnail generation, `StoryBuilder`, `prepare_video()`, or audio/video composition helpers:

```bash
pkg install ffmpeg
python -m pip install "instagrapi[video]"
```

If MoviePy cannot find ffmpeg, point ImageIO at the Termux binary before running the script:

```bash
export IMAGEIO_FFMPEG_EXE="$(command -v ffmpeg)"
```

If `pip install "instagrapi[video]"` tries to build NumPy and fails, avoid the optional video helpers on-device: prepare the MP4 and thumbnail elsewhere, then use upload methods with `thumbnail=...`.
