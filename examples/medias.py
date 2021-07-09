from typing import List

from instagrapi import Client
from instagrapi.types import Media

HASHTAGS = ['instacool']
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
        medias: List[Media],
        like_count_min=None,
        like_count_max=None,
        comment_count_min=None,
        comment_count_max=None,
        days_ago_max=None
):
    from datetime import datetime, timedelta

    medias = list(
        filter(lambda x: True if like_count_min is None else x.like_count >= like_count_min, medias))
    medias = list(
        filter(lambda x: True if like_count_max is None else x.like_count <= like_count_max, medias))
    medias = list(filter(lambda x: True if comment_count_min is None else x.comment_count >= comment_count_min,
                         medias))
    medias = list(filter(lambda x: True if comment_count_max is None else x.comment_count <= comment_count_max,
                         medias))
    if days_ago_max is not None:
        days_back = datetime.now() - timedelta(days=days_ago_max)
        medias = list(filter(
            lambda x: days_ago_max is None or x.taken_at is None or x.taken_at > days_back.astimezone(
                x.taken_at.tzinfo),
            medias))

    return list(medias)


def get_medias(hashtags,
               ht_type='top',
               amount=27,
               ):
    ht_medias = []
    for hashtag in hashtags:
        if ht_type == 'top':
            ht_medias.extend(
                cl.hashtag_medias_top(
                    name=hashtag,
                    amount=amount if amount <= 9 else 9
                )
            )
        elif ht_type == 'recent':
            ht_medias.extend(
                cl.hashtag_medias_recent(
                    name=hashtag,
                    amount=amount
                )
            )
    return list(dict([(media.pk, media) for media in ht_medias]).values())


if __name__ == '__main__':
    import os

    log = get_logger("example_media", **{
        "level": "DEBUG",
        "format": "%(asctime)s %(levelname)s %(name)s: %(message)s"
    })
    cl = Client()
    if os.path.exists(IG_CREDENTIAL_PATH):
        cl.load_settings(IG_CREDENTIAL_PATH)
        cl.login(IG_USERNAME, IG_PASSWORD)
    else:
        cl.login(IG_USERNAME, IG_PASSWORD)
        cl.dump_settings(IG_CREDENTIAL_PATH)

    m = get_medias(HASHTAGS, amount=4)
    m = filter_medias(m, like_count_min=1, days_ago_max=365)
    log.info(len(m))
