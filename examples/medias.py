import random
from typing import List

from instagrapi import Client
from instagrapi.types import Media
from datetime import datetime, timedelta

HASHTAGS = ['instacool']
USERNAMES = ['2296733608']
IG_USERNAME = ''
IG_PASSWORD = ''
IG_CREDENTIAL_PATH = 'credential.json'


def get_logger(name, **kwargs):
    import logging
    logging.basicConfig(**kwargs)
    logger = logging.getLogger(name)
    logger.debug(f"start logging '{name}'")
    return logger


def filter_medias(
        medias,
        like_count_min=None,
        like_count_max=None,
        comment_count_min=None,
        comment_count_max=None,
        days_ago_max=None
):
    days_back = datetime.now() - timedelta(days=days_ago_max)
    media_ids = set()
    nb_media = 0

    for media in medias:
        if (like_count_min is None or media.like_count >= like_count_min) and \
           (like_count_max is None or media.like_count <= like_count_max) and \
            (comment_count_min is None or media.comment_count >= comment_count_min) and \
            (comment_count_max is None or media.command_count <= comment_count_max) and \
            (days_ago_max is None or media.taken_at > days_back.astimezone(media.taken_at.tzinfo)):
            nb_media += 1
            if media.pk not in media_ids:
                media_ids.add(media.pk)
                yield media
    print(nb_media)

def get_medias(keywords,
               ht_type='top',
               amount=27,
               crawl_type='hashtag',
               ):
    for keyword in keywords:
        if crawl_type == 'hashtag':
            if ht_type == 'top':
                print("TOP")
                yield from cl.hashtag_medias_top(
                        name=keyword,
                        amount=amount if amount <= 9 else 9
                    )
            elif ht_type == 'recent':
                print("RECENT")
                yield from cl.hashtag_medias_recent(
                        name=keyword,
                        amount=amount
                    )
            else:
                print("STREAM")
                yield from cl.hashtag_medias_v1_logged_out(
                    name=keyword,
                    max_amount=amount
                )
        elif crawl_type == "username":
            yield from cl.user_medias(keyword)

def next_proxy():
    return None

if __name__ == '__main__':
    import os
    log = get_logger("example_media", **{
        "level": "DEBUG",
        "format": "%(asctime)s %(levelname)s %(name)s: %(message)s"
    })
#    cl = Client(proxy=next_proxy())
    cl = Client()
    if os.path.exists(IG_CREDENTIAL_PATH):
        cl.load_settings(IG_CREDENTIAL_PATH)
        cl.login(IG_USERNAME, IG_PASSWORD)
    elif IG_PASSWORD and IG_USERNAME:
        cl.login(IG_USERNAME, IG_PASSWORD)
        cl.dump_settings(IG_CREDENTIAL_PATH)
    else:
        log.info("Run without credential")

    m = get_medias(HASHTAGS, amount=500, ht_type="stream", crawl_type="hashtag")

#    m = get_medias(HASHTAGS, amount=500, ht_type="recent", crawl_type="hashtag")
#    m = get_medias(HASHTAGS, amount=999999, ht_type="top", crawl_type="hashtag")
#    m = get_medias(USERNAMES, amount=999999, crawl_type="username")
    m = filter_medias(m, days_ago_max=365*15)
    log.info(len(list(m)))
