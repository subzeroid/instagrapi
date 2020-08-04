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
    Direct
):
    proxy = None
    logger = logging.getLogger("Client")

    def __init__(self, settings={}, proxy=None, **kwargs):
        super().__init__(**kwargs)
        self.settings = settings
        self.set_proxy(proxy)

    def set_proxy(self, proxy):
        if proxy:
            assert isinstance(
                proxy, str
            ), 'Proxy must been string (URL), but now "%s" (%s)' % (proxy, type(proxy))
            self.proxy = proxy
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
