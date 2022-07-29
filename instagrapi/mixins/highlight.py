import json
import random
import time
from pathlib import Path
from typing import Dict, List
from urllib.parse import urlparse

from instagrapi import config
from instagrapi.exceptions import HighlightNotFound
from instagrapi.extractors import extract_highlight_v1
from instagrapi.types import Highlight
from instagrapi.utils import dumps


class HighlightMixin:

    def highlight_pk_from_url(self, url: str) -> str:
        """
        Get Highlight PK from URL

        Parameters
        ----------
        url: str
            URL of highlight

        Returns
        -------
        str
            Highlight PK

        Examples
        --------
        https://www.instagram.com/stories/highlights/17895485201104054/ -> 17895485201104054
        """
        assert '/highlights/' in url, 'URL must contain "/highlights/"'
        path = urlparse(url).path
        parts = [p for p in path.split("/") if p and p.isdigit()]
        return str(parts[0])

    def user_highlights_v1(self, user_id: int, amount: int = 0) -> List[Highlight]:
        """
        Get a user's highlight

        Parameters
        ----------
        user_id: int
        amount: int, optional
            Maximum number of highlight to return, default is 0 (all highlights)

        Returns
        -------
        List[Highlight]
            A list of objects of Highlight
        """
        amount = int(amount)
        user_id = int(user_id)
        params = {
            "supported_capabilities_new": json.dumps(config.SUPPORTED_CAPABILITIES),
            "phone_id": self.phone_id,
            "battery_level": random.randint(25, 100),
            "panavision_mode": "",
            "is_charging": random.randint(0, 1),
            "is_dark_mode": random.randint(0, 1),
            "will_sound_on": random.randint(0, 1),
        }
        result = self.private_request(f"highlights/{user_id}/highlights_tray/", params=params)
        return [
            extract_highlight_v1(highlight)
            for highlight in result.get("tray", [])
        ]

    def user_highlights(self, user_id: int, amount: int = 0) -> List[Highlight]:
        """
        Get a user's highlights

        Parameters
        ----------
        user_id: int
        amount: int, optional
            Maximum number of highlight to return, default is 0 (all highlights)

        Returns
        -------
        List[Highlight]
            A list of objects of Highlight
        """
        return self.user_highlights_v1(user_id, amount)

    def highlight_info_v1(self, highlight_pk: str) -> Highlight:
        """
        Get Highlight by pk or id (by Private Mobile API)

        Parameters
        ----------
        highlight_pk: str
            Unique identifier of Highlight

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

    def highlight_info(self, highlight_pk: str) -> Highlight:
        """
        Get Highlight by pk or id

        Parameters
        ----------
        highlight_pk: str
            Unique identifier of Highlight

        Returns
        -------
        Highlight
            An object of Highlight type
        """
        return self.highlight_info_v1(highlight_pk)

    def highlight_create(self, title: str, story_ids: List[str], cover_story_id: str = "", crop_rect: List[float] = [0.0, 0.21830457, 1.0, 0.78094524]) -> Highlight:
        """
        Create highlight

        Parameters
        ----------
        title: str
            Title
        story_ids: List[str]
            List of story ids
        cover_story_id: str
            User story as cover, default is first of story_ids

        Returns
        -------
        Highlight
            An object of Highlight type
        """
        if not cover_story_id:
            cover_story_id = story_ids[0]
        data = {
            "supported_capabilities_new": json.dumps(config.SUPPORTED_CAPABILITIES),
            "source": "self_profile",
            "creation_id": str(int(time.time())),
            "_uid": str(self.user_id),
            "_uuid": self.uuid,
            "cover": dumps({
                "media_id": self.media_id(cover_story_id),
                "crop_rect": dumps(crop_rect)
            }),
            "title": title,
            "media_ids": dumps([self.media_id(sid) for sid in story_ids])
        }
        result = self.private_request("highlights/create_reel/", data=data)
        return extract_highlight_v1(result['reel'])

    def highlight_edit(self, highlight_pk: str, title: str = "", cover: Dict = {}, added_media_ids: List[str] = [], removed_media_ids: List[str] = []):
        data = {
            "supported_capabilities_new": json.dumps(config.SUPPORTED_CAPABILITIES),
            "source": "self_profile",
            "_uid": str(self.user_id),
            "_uuid": self.uuid,
            "added_media_ids": dumps(added_media_ids),
            "removed_media_ids": dumps(removed_media_ids)
        }
        if title:
            data["title"] = title
        if cover:
            data["cover"] = dumps(cover)
        result = self.private_request(f"highlights/highlight:{highlight_pk}/edit_reel/", data=data)
        return extract_highlight_v1(result['reel'])

    def highlight_change_title(self, highlight_pk: str, title: str) -> Highlight:
        """
        Change title for highlight

        Parameters
        ----------
        highlight_pk: str
            Unique identifier of Highlight
        title: str
            Title of Highlight

        Returns
        -------
        Highlight
        """
        return self.highlight_edit(highlight_pk, title=title)

    def highlight_change_cover(self, highlight_pk: str, cover_path: Path) -> Highlight:
        """
        Change cover for highlight

        Parameters
        ----------
        highlight_pk: str
            Unique identifier of Highlight
        cover_path: Path
            Path to photo

        Returns
        -------
        Highlight
        """
        upload_id, width, height = self.photo_rupload(Path(cover_path))
        cover = {"upload_id": str(upload_id), "crop_rect": "[0.0,0.0,1.0,1.0]"}
        return self.highlight_edit(highlight_pk, cover=cover)

    def highlight_add_stories(self, highlight_pk: str, added_media_ids: List[str]) -> Highlight:
        """
        Add stories to highlight

        Parameters
        ----------
        highlight_pk: str
            Unique identifier of Highlight
        removed_media_ids: List[str]
            Remove stories from highlight

        Returns
        -------
        Highlight
        """
        return self.highlight_edit(highlight_pk, added_media_ids=added_media_ids)

    def highlight_remove_stories(self, highlight_pk: str, removed_media_ids: List[str]) -> Highlight:
        """
        Remove stories from highlight

        Parameters
        ----------
        highlight_pk: str
            Unique identifier of Highlight
        removed_media_ids: List[str]
            Remove stories from highlight

        Returns
        -------
        Highlight
        """
        return self.highlight_edit(highlight_pk, removed_media_ids=removed_media_ids)

    def highlight_delete(self, highlight_pk: str) -> bool:
        """
        Delete highlight

        Parameters
        ----------
        highlight_pk: str
            Unique identifier of Highlight

        Returns
        -------
        bool
        """
        data = {"_uid": str(self.user_id), "_uuid": self.uuid}
        result = self.private_request(f"highlights/highlight:{highlight_pk}/delete_reel/", data=data)
        return result.get("status") == "ok"
