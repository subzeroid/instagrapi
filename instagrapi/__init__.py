import logging
import random
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
    settings = None
    proxy = None
    logger = logging.getLogger("instagrapi")

    def __init__(
        self,
        settings: Optional[Dict[str, Any]] = None,
        proxy: Optional[Dict[str, Any]] = None,
        job_id: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)

        if settings:
            self.settings = settings
        if proxy:
            self.set_proxy(proxy, job_id=job_id)

        self.init()

    def get_session_id(self, job_id: Optional[str] = None):
        total = random.randint(1_000, 10_000_000)
        if job_id:
            total += sum([ord(c) * i * i for i, c in enumerate(job_id)])
        return total

    def set_proxy(self, proxy: Dict[str, Any], job_id: Optional[str] = None):
        proxy_uri = random.choice(proxy["proxies"])
        proxy_username = proxy.get("username", "")
        proxy_password = proxy.get("password", "")
        proxy_api = proxy.get("api", "")
        proxy_country = proxy.get("country")

        session_id = self.get_session_id(job_id)

        if "lum-superproxy" in proxy_uri:
            if "unblocker" in proxy_username:
                session_type = "unblocker-session"
            else:
                session_type = "session"

            proxy_uri = f"http://{proxy_username}-{session_type}-{session_id}:{proxy_password}@{proxy_uri}"
            proxy_dict = {
                "http": proxy_uri,
                "https": proxy_uri,
                "type": "luminati",
            }
        elif "scraperapi" in proxy_uri:
            proxy_uri = f"{proxy_api}?api_key={proxy_password}&url=%s&keep_headers=true&session_number={session_id}"

            if proxy_country:
                country = random.choice(proxy_country.split(","))
                proxy_uri += f"&country_code={country}"

            proxy_dict = {"overwrite_url": proxy_uri, "type": "scraperapi"}
        elif "oxylabs" in proxy_uri:
            if "unblock" in proxy_uri:
                self.private.headers["X-Oxylabs-Session-Id"] = str(session_id)
                self.public.headers["X-Oxylabs-Session-Id"] = str(session_id)
            else:
                proxy_username = f"customer-{proxy_username}-sessid-{session_id}"
                if proxy_country:
                    country = random.choice(proxy_country.split(","))
                    proxy_username += "-cc-{country}"

            proxy_uri = f"http://{proxy_username}:{proxy_password}@{proxy_uri}"
            proxy_dict = {
                "http": proxy_uri,
                "https": proxy_uri,
                "proxy_type": "oxylabs",
            }
        else:
            proxy_uri = f"http://{proxy_username}:{proxy_password}@{proxy_uri}"
            proxy_dict = {
                "http": proxy_uri,
                "https": proxy_uri,
                "type": "other",
            }

        self.public.proxies = self.private.proxies = proxy_dict

        proxy_scheme = "" if urlparse(proxy_uri).scheme else "http://"
        proxy_href = f"{proxy_scheme}{proxy_uri}"

        self.proxy = proxy_href

    def handle_exception(self, exception):
        return True
