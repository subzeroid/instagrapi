from __future__ import annotations

import argparse
from pathlib import Path

from _common import env_int, make_client


def download_media(username: str, amount: int, folder: Path) -> list[Path]:
    cl = make_client()
    folder.mkdir(parents=True, exist_ok=True)

    user_id = cl.user_id_from_username(username)
    downloaded: list[Path] = []
    for media in cl.user_medias(user_id, amount=amount):
        if media.media_type == 1:
            downloaded.append(cl.photo_download(media.pk, folder=folder))
        elif media.media_type == 2:
            downloaded.append(cl.video_download(media.pk, folder=folder))
        elif media.media_type == 8:
            downloaded.extend(cl.album_download(media.pk, folder=folder))
    return downloaded


def main() -> None:
    parser = argparse.ArgumentParser(description="Download recent media for an Instagram username.")
    parser.add_argument("username")
    parser.add_argument("--amount", type=int, default=env_int("IG_AMOUNT", 10))
    parser.add_argument("--folder", type=Path, default=Path("downloads"))
    args = parser.parse_args()

    for path in download_media(args.username, args.amount, args.folder):
        print(path)


if __name__ == "__main__":
    main()
