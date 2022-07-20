import logging
from urllib.parse import urlparse

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from instagrapi.mixins.account import AccountMixin
from instagrapi.mixins.album import DownloadAlbumMixin, UploadAlbumMixin
from instagrapi.mixins.auth import LoginMixin
from instagrapi.mixins.bloks import BloksMixin
from instagrapi.mixins.challenge import ChallengeResolveMixin
from instagrapi.mixins.clip import DownloadClipMixin, UploadClipMixin
from instagrapi.mixins.collection import CollectionMixin
from instagrapi.mixins.comment import CommentMixin
from instagrapi.mixins.direct import DirectMixin
from instagrapi.mixins.fbsearch import FbSearchMixin
from instagrapi.mixins.hashtag import HashtagMixin
from instagrapi.mixins.highlight import HighlightMixin
from instagrapi.mixins.igtv import DownloadIGTVMixin, UploadIGTVMixin
from instagrapi.mixins.insights import InsightsMixin
from instagrapi.mixins.location import LocationMixin
from instagrapi.mixins.media import MediaMixin
from instagrapi.mixins.notification import NotificationMixin
from instagrapi.mixins.password import PasswordMixin
from instagrapi.mixins.photo import DownloadPhotoMixin, UploadPhotoMixin
from instagrapi.mixins.private import PrivateRequestMixin
from instagrapi.mixins.public import (
    ProfilePublicMixin,
    PublicRequestMixin,
    TopSearchesPublicMixin,
)
from instagrapi.mixins.share import ShareMixin
from instagrapi.mixins.story import StoryMixin
from instagrapi.mixins.timeline import ReelsMixin
from instagrapi.mixins.totp import TOTPMixin
from instagrapi.mixins.user import UserMixin
from instagrapi.mixins.video import DownloadVideoMixin, UploadVideoMixin
from instagrapi.mixins.multiple_accounts import MultipleAccountsMixin
from instagrapi.mixins.fundraiser import FundraiserMixin

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class Client(
    PublicRequestMixin,
    ChallengeResolveMixin,
    PrivateRequestMixin,
    TopSearchesPublicMixin,
    ProfilePublicMixin,
    LoginMixin,
    ShareMixin,
    FbSearchMixin,
    HighlightMixin,
    DownloadPhotoMixin,
    UploadPhotoMixin,
    DownloadVideoMixin,
    UploadVideoMixin,
    DownloadAlbumMixin,
    NotificationMixin,
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
    CommentMixin,
    StoryMixin,
    PasswordMixin,
    DownloadClipMixin,
    UploadClipMixin,
    ReelsMixin,
    BloksMixin,
    TOTPMixin,
    MultipleAccountsMixin,
    FundraiserMixin
):
    proxy = None
    logger = logging.getLogger("instagrapi")

    def __init__(self, settings: dict = {}, proxy: str = None, delay_range: list = None, **kwargs):
        super().__init__(**kwargs)
        self.settings = settings
        self.delay_range = delay_range
        self.set_proxy(proxy)
        self.init()

    def set_proxy(self, dsn: str):
        if dsn:
            assert isinstance(
                dsn, str
            ), f'Proxy must been string (URL), but now "{dsn}" ({type(dsn)})'
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
