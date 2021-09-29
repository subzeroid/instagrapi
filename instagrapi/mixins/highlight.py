import json
from urllib.parse import urlparse

from instagrapi import config
from instagrapi.exceptions import HighlightNotFound
from instagrapi.extractors import extract_highlight_v1
from instagrapi.types import Highlight


class HighlightMixin:

    def highlight_pk_from_url(self, url: str) -> int:
        """
        Get Highlight PK from URL

        Parameters
        ----------
        url: str
            URL of the highlight

        Returns
        -------
        int
            Highlight PK

        Examples
        --------
        https://www.instagram.com/stories/highlights/17895485201104054/ -> 17895485201104054
        """
        assert '/highlights/' in url, 'URL must contain the "/highlights/"'
        path = urlparse(url).path
        parts = [p for p in path.split("/") if p and p.isdigit()]
        return int(parts[0])

    def highlight_info_v1(self, highlight_pk: int) -> Highlight:
        """
        Get Highlight by pk or id (by Private Mobile API)

        Parameters
        ----------
        highlight_pk: int
            Unique identifier of the Highlight

        Returns
        -------
        Highlight
            An object of Highlight type
        """
        highlight_id = f"highlight:{highlight_pk}"
        data = {
            "exclude_media_ids": "[]",
            "supported_capabilities_new": json.dumps(config.SUPPORTED_CAPABILITIES),
            "source": "profile",
            "_uid": str(self.user_id),
            "_uuid": self.uuid,
            "user_ids": [highlight_id]
        }
        result = self.private_request('feed/reels_media/', data)
        data = result['reels']
        if highlight_id not in data:
            raise HighlightNotFound(highlight_pk=highlight_pk, **data)
        return extract_highlight_v1(data[highlight_id])

    def highlight_info(self, highlight_pk: int) -> Highlight:
        """
        Get Highlight by pk or id

        Parameters
        ----------
        highlight_pk: int
            Unique identifier of the Highlight

        Returns
        -------
        Highlight
            An object of Highlight type
        """
        return self.highlight_info_v1(highlight_pk)
