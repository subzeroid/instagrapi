import logging
from urllib.parse import urlparse

from instagrapi.mixins.auth import LoginMixin
from instagrapi.mixins.public import (
    PublicRequestMixin,
    TopSearchesPublicMixin,
    ProfilePublicMixin
)
from instagrapi.mixins.private import PrivateRequestMixin
from instagrapi.mixins.challenge import ChallengeResolveMixin
from instagrapi.mixins.photo import DownloadPhotoMixin, UploadPhotoMixin
from instagrapi.mixins.video import DownloadVideoMixin, UploadVideoMixin
from instagrapi.mixins.album import DownloadAlbumMixin, UploadAlbumMixin
from instagrapi.mixins.igtv import DownloadIGTVMixin, UploadIGTVMixin
from instagrapi.mixins.media import MediaMixin
from instagrapi.mixins.user import UserMixin
from instagrapi.mixins.insights import InsightsMixin
from instagrapi.mixins.collection import CollectionMixin
from instagrapi.mixins.account import AccountMixin
from instagrapi.mixins.direct import DirectMixin
from instagrapi.mixins.location import LocationMixin
from instagrapi.mixins.hashtag import HashtagMixin
from instagrapi.mixins.comment import CommentMixin


class Client(
    PublicRequestMixin,
    ChallengeResolveMixin,
    PrivateRequestMixin,
    TopSearchesPublicMixin,
    ProfilePublicMixin,
    LoginMixin,
    DownloadPhotoMixin,
    UploadPhotoMixin,
    DownloadVideoMixin,
    UploadVideoMixin,
    DownloadAlbumMixin,
    UploadAlbumMixin,
    DownloadIGTVMixin,
    UploadIGTVMixin,
    MediaMixin,
    UserMixin,
    InsightsMixin,
    CollectionMixin,
    AccountMixin,
    DirectMixin,
    LocationMixin,
    HashtagMixin,
    CommentMixin
):
    proxy = None
    logger = logging.getLogger("instagrapi")

    def __init__(self, settings: dict = {}, proxy: str = None, **kwargs):
        super().__init__(**kwargs)
        self.settings = settings
        self.set_proxy(proxy)
        self.init()

    def set_proxy(self, dsn: str):
        if dsn:
            assert isinstance(dsn, str),\
                f'Proxy must been string (URL), but now "{dsn}" ({type(dsn)})'
            self.proxy = dsn
            proxy_href = "{scheme}{href}".format(
                scheme="http://" if not urlparse(self.proxy).scheme else "",
                href=self.proxy,
            )
            self.public.proxies = self.private.proxies = {
                "http": proxy_href,
                "https": proxy_href,
            }
            return True
        self.public.proxies = self.private.proxies = {}
        return False
