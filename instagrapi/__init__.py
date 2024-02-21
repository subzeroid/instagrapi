import logging
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from instagrapi.exceptions import (
    BadPassword, ReloginAttemptExceeded, ChallengeRequired, SelectContactPointRecoveryForm,
    RecaptchaChallengeForm, FeedbackRequired, PleaseWaitFewMinutes, LoginRequired,
    ClientBadRequestError, ClientError
)
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
):
    proxy = None
    logger = logging.getLogger("instagrapi")

    def __init__(self, settings: Optional[Dict[str, Any]] = None, proxy: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(**kwargs)

        if not settings:
            settings = {}
        if not proxy:
            proxy = {}

        self.settings = settings
        self.set_proxy(proxy)
        self.init()

    def set_proxy(self, proxy: Dict[str, Any]):
        http_proxy = proxy.get("http")
        if http_proxy:
            proxy_scheme = "" if urlparse(http_proxy).scheme else "http://"
            proxy_href = f"{proxy_scheme}{self.proxy}"
            self.proxy = http_proxy

            if "unblock.oxylabs" in proxy_href and "sessid-" in proxy_href:
                session_id = proxy_href.split("sessid-")[1].split(":")[0].split("-")[0]
                self.private.headers["X-Oxylabs-Session-Id"] = session_id
                self.public.headers["X-Oxylabs-Session-Id"] = session_id
                # self.private.headers["X-Oxylabs-Render"] = "html"
                # self.public.headers["X-Oxylabs-Render"] = "html"
                proxy_href = proxy_href.replace(f"-sessid-{session_id}", "")

            proxies = {
                "http": proxy_href,
                "https": proxy_href,
            }
        else:
            proxies = {}

        self.public.proxies = self.private.proxies = proxies

    def handle_exception(self, exception):
        return True

    def next_proxy(self, job_id, proxy_function):
        if proxy_function:
            return proxy_function(job_id)
