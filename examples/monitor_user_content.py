from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from _common import env_int, make_client

from instagrapi.exceptions import ClientError


def load_state(path: Path) -> dict:
    if not path.exists():
        return {"users": {}}
    return json.loads(path.read_text())


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True))


def post_url(code: str | None) -> str | None:
    if not code:
        return None
    return f"https://www.instagram.com/p/{code}/"


def story_url(username: str, story_pk: str | int | None) -> str | None:
    if not story_pk:
        return None
    return f"https://www.instagram.com/stories/{username}/{story_pk}/"


def monitor_user(cl, username: str, amount: int, state: dict, include_stories: bool) -> None:
    user_state = state.setdefault("users", {}).setdefault(username, {})
    known_media_ids = set(user_state.get("media_ids", []))
    known_story_pks = set(user_state.get("story_pks", []))

    user_id = cl.user_id_from_username(username)
    medias = cl.user_medias(user_id, amount=amount)
    media_ids = [str(media.id) for media in medias if media.id]

    for media in reversed(medias):
        media_id = str(media.id)
        if known_media_ids and media_id not in known_media_ids:
            print(f"new post @{username}: {post_url(media.code) or media_id}")

    user_state["media_ids"] = media_ids

    if include_stories:
        stories = cl.user_stories(user_id)
        story_pks = [str(story.pk) for story in stories if story.pk]
        for story in reversed(stories):
            story_pk = str(story.pk)
            if known_story_pks and story_pk not in known_story_pks:
                print(f"new story @{username}: {story_url(username, story.pk) or story_pk}")
        user_state["story_pks"] = story_pks


def main() -> None:
    parser = argparse.ArgumentParser(description="Poll a small set of users for new posts and stories.")
    parser.add_argument("usernames", nargs="+")
    parser.add_argument("--amount", type=int, default=env_int("IG_AMOUNT", 12))
    parser.add_argument("--state", type=Path, default=Path("monitor_state.json"))
    parser.add_argument("--interval", type=int, default=env_int("IG_MONITOR_INTERVAL", 0))
    parser.add_argument("--stories", action="store_true", help="Also check active stories.")
    args = parser.parse_args()

    cl = make_client()
    state = load_state(args.state)

    while True:
        for username in args.usernames:
            try:
                monitor_user(cl, username, args.amount, state, args.stories)
            except ClientError as exc:
                print(f"skip @{username}: {exc}")
            time.sleep(2)

        save_state(args.state, state)
        if args.interval <= 0:
            break
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
