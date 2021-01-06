import os

from instagrapi import Client

ACCOUNT_USERNAME = os.environ.get("IG_USERNAME")
ACCOUNT_PASSWORD = os.environ.get("IG_PASSWORD")


def main(username: str, amount: int = 5) -> dict:
    """
    Download all medias from instagram profile
    """
    amount = int(amount)
    cl = Client()
    cl.login(ACCOUNT_USERNAME, ACCOUNT_PASSWORD)
    user_id = cl.user_id_from_username(username)
    medias = cl.user_medias(user_id)
    result = {}
    i = 0
    for m in medias:
        if i >= amount:
            break
        paths = []
        if m.media_type == 1:
            # Photo
            paths.append(cl.photo_download(m.pk))
        elif m.media_type == 2 and m.product_type == 'feed':
            # Video
            paths.append(cl.video_download(m.pk))
        elif m.media_type == 2 and m.product_type == 'igtv':
            # IGTV
            paths.append(cl.video_download(m.pk))
        elif m.media_type == 2 and m.product_type == 'clips':
            # Reels
            paths.append(cl.video_download(m.pk))
        elif m.media_type == 8:
            # Album
            for path in cl.album_download(m.pk):
                paths.append(path)
        result[m.pk] = paths
        print(f'http://instagram.com/p/{m.code}/', paths)
        i += 1
    return result


if __name__ == '__main__':
    username = input('Enter username: ')
    while True:
        amount = input('How many posts to process (default: 5)? ').strip()
        if amount == '':
            amount = '5'
        if amount.isdigit():
            break
    main(username, amount)
