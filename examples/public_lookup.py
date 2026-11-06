from __future__ import annotations

import argparse
from json import dumps

from _common import make_client


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch public Instagram profile information.")
    parser.add_argument("username", nargs="?", default="instagram")
    parser.add_argument("--session-file", help="Load an existing saved session; no fresh login is performed.")
    args = parser.parse_args()

    cl = make_client(login=False)
    if args.session_file:
        cl.load_settings(args.session_file)
    user = cl.user_info_by_username_v2_gql(args.username)
    print(
        dumps(
            {
                "pk": user.pk,
                "username": user.username,
                "full_name": user.full_name,
                "media_count": user.media_count,
                "follower_count": user.follower_count,
                "following_count": user.following_count,
                "is_private": user.is_private,
                "is_verified": user.is_verified,
            },
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    main()
