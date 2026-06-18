import base64
from urllib.parse import urlparse

from instagrapi.types import Share


class ShareMixin:
    def share_info(self, code: str) -> Share:
        """
        Get Share object by code

        Parameters
        ----------
        code: str
            Share code

        Returns
        -------
        Share
            Share object
        """
        if isinstance(code, str):
            code = code.encode()
        # ignore example from instagram: b'highli\xb1\xdb\x1dght:17988089629383770'
        data = (
            base64.b64decode(code)
            .decode(errors="ignore")
            .replace("\x1d", "")
            .split(":")
        )
        return Share(type=data[0], pk=data[1])

    def share_info_by_url(self, url: str) -> Share:
        """
        Get Share object by URL

        Parameters
        ----------
        url: str
            URL of the share object

        Returns
        -------
        Share
            Share object
        """
        return self.share_info(self.share_code_from_url(url))

    def share_code_from_url(self, url: str) -> str:
        """
        Get Share code from URL

        Parameters
        ----------
        url: str
            URL of the share object

        Returns
        -------
        str
            Share code
        """
        path = urlparse(url).path
        parts = [p for p in path.split("/") if p]
        return parts.pop()
