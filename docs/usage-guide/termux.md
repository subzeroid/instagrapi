# Termux

Termux can run many `instagrapi` flows, but Android does not use the same binary wheel ecosystem as desktop Linux. Keep the default install small and add media tooling only when the script really needs it.

instagrapi 3.2.0+ requires Python 3.11+ and Pillow 13+. Check the versions provided by your Android environment before upgrading; see [Getting Started](../getting-started.md) for the migration requirements.

## Install

```bash
pkg update
pkg install python python-pillow
python -m pip install -U pip setuptools wheel
python -m pip install --extra-index-url https://termux-user-repository.github.io/pypi/ instagrapi
```

`python-pillow` is recommended because photo uploads use Pillow through `instagrapi.image_util`. Installing it with `pkg` avoids a slow or fragile Pillow source build in pip.

The Termux User Repository PyPI index provides Android wheels for native packages that PyPI may only publish as desktop Linux wheels. When the interpreter reports `sys.platform == "android"`, `instagrapi` uses `pydantic==2.12.5`, which depends on `pydantic-core==2.41.5`; that core version has Android wheels for Python 3.13 and 3.14 in the Termux index. Newer core versions may lack wheels for a particular Python version and require a Rust build on-device. Wheel availability does not establish runtime compatibility.

Check the interpreter used to install and run the library:

```bash
python -c "import sys; print(sys.version); print(sys.platform)"
```

The dependency marker follows the interpreter value, rather than the device operating system. An interpreter reporting `linux`, including some custom or proot environments, selects the non-Android dependency range. Include the Python version and `sys.platform` value when reporting installation problems.

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
python -m pip install --no-deps "moviepy==2.2.1"
```

MoviePy `2.2.1` currently declares `Pillow<12`, but instagrapi requires `Pillow>=13.0.0,<14` for upstream security fixes; install MoviePy with `--no-deps` to retain that dependency range. MoviePy `1.x` is no longer supported by instagrapi's optional video helpers.

If MoviePy cannot find ffmpeg, point ImageIO at the Termux binary before running the script:

```bash
export IMAGEIO_FFMPEG_EXE="$(command -v ffmpeg)"
```

If `pip install "instagrapi[video]"` tries to build NumPy and fails, avoid the optional video helpers on-device: prepare the MP4 and thumbnail elsewhere, then use upload methods with `thumbnail=...`.
