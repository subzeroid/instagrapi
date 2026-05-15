from __future__ import annotations

import argparse
from pathlib import Path

from _common import env, make_client


def upload_media(kind: str, path: Path, caption: str, thumbnail: Path | None = None):
    cl = make_client()

    if kind == "photo":
        return cl.photo_upload(path, caption)
    if kind == "video":
        return cl.video_upload(path, caption, thumbnail=thumbnail)
    if kind == "reel":
        return cl.clip_upload(path, caption, thumbnail=thumbnail)
    if kind == "trial-reel":
        if not cl.clip_trial_eligible():
            raise SystemExit("This account does not currently report Trial Reels eligibility.")
        return cl.clip_upload(path, caption, thumbnail=thumbnail, trial=True)

    raise ValueError(f"Unsupported media kind: {kind}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload a feed photo, feed video, Reel, or Trial Reel.")
    parser.add_argument("kind", choices=["photo", "video", "reel", "trial-reel"])
    parser.add_argument("path", type=Path)
    parser.add_argument("--caption", default=env("IG_CAPTION", "Uploaded with instagrapi"))
    parser.add_argument("--thumbnail", type=Path, default=None)
    args = parser.parse_args()

    media = upload_media(args.kind, args.path, args.caption, args.thumbnail)
    print(f"Uploaded {media.pk} https://www.instagram.com/p/{media.code}/")


if __name__ == "__main__":
    main()
