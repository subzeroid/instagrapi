from __future__ import annotations

import argparse
from pathlib import Path

from _common import env, make_client

from instagrapi.types import StoryLink


def upload_story(kind: str, path: Path, caption: str, thumbnail: Path | None = None, link: str | None = None):
    cl = make_client()
    links = [StoryLink(webUri=link)] if link else []

    if kind == "photo":
        return cl.photo_upload_to_story(path, caption=caption, links=links)
    if kind == "video":
        return cl.video_upload_to_story(path, caption=caption, thumbnail=thumbnail, links=links)

    raise ValueError(f"Unsupported story kind: {kind}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload a photo or video story.")
    parser.add_argument("kind", choices=["photo", "video"])
    parser.add_argument("path", type=Path)
    parser.add_argument("--caption", default=env("IG_CAPTION", ""))
    parser.add_argument("--thumbnail", type=Path, default=None)
    parser.add_argument("--link", default=env("IG_STORY_LINK"))
    args = parser.parse_args()

    story = upload_story(args.kind, args.path, args.caption, args.thumbnail, args.link)
    print(f"Uploaded story {story.pk}")


if __name__ == "__main__":
    main()
