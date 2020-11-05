import logging
from urllib.parse import urlparse

from .auth import Login
from .public import (
    PublicRequest,
    HashtagPublic,
    TopSearchesPublic,
    ProfilePublic,
)
from .private import PrivateRequest
from .challenge import ChallengeResolve
from .photo import DownloadPhoto, UploadPhoto
from .video import DownloadVideo, UploadVideo
from .album import DownloadAlbum, UploadAlbum
from .igtv import DownloadIGTV, UploadIGTV
from .media import Media
from .user import User
from .insights import Insights
from .collection import Collection
from .account import Account
from .direct import Direct
from .location import LocationMixin


class Client(
    PublicRequest,
    ChallengeResolve,
    PrivateRequest,
    HashtagPublic,
    TopSearchesPublic,
    ProfilePublic,
    Login,
    DownloadPhoto,
    UploadPhoto,
    DownloadVideo,
    UploadVideo,
    DownloadAlbum,
    UploadAlbum,
    DownloadIGTV,
    UploadIGTV,
    Media,
    User,
    Insights,
    Collection,
    Account,
    Direct,
    LocationMixin
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
