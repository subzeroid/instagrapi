"""Examples for session persistence and sessionid login."""

import os
from instagrapi import Client

IG_USERNAME = os.environ.get("IG_USERNAME")
IG_PASSWORD = os.environ.get("IG_PASSWORD")
SESSION_FILE = "session.json"


def login_with_persistence() -> Client:
    """Return Client logged in using saved session settings."""
    cl = Client()
    if os.path.exists(SESSION_FILE):
        cl.load_settings(SESSION_FILE)
    cl.login(IG_USERNAME, IG_PASSWORD)
    cl.dump_settings(SESSION_FILE)
    return cl


def login_with_sessionid(sessionid: str) -> Client:
    """Return Client logged in only with a sessionid."""
    cl = Client()
    cl.login_by_sessionid(sessionid)
    return cl


def list_and_download(username: str, amount: int = 10):
    """Download recent posts from the specified account."""
    cl = login_with_persistence()
    user_id = cl.user_id_from_username(username)
    for media in cl.user_medias(user_id, amount=amount):
        if media.media_type == 1:
            cl.photo_download(media.pk)
        elif media.media_type == 2:
            cl.video_download(media.pk)
        elif media.media_type == 8:
            cl.album_download(media.pk)


if __name__ == "__main__":
    target = input("Target username: ")
    list_and_download(target)
