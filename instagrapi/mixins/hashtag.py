import base64
import json
import warnings
from typing import List, Tuple

from instagrapi.exceptions import HashtagNotFound, WrongCursorError
from instagrapi.extractors import (
    extract_hashtag_gql,
    extract_hashtag_v1,
    extract_media_v1,
)
from instagrapi.types import Hashtag, Media
from instagrapi.utils.serialization import dumps


class HashtagMixin:
    """
    Helpers for managing Hashtag
    """

    def _normalize_hashtag_name(self, name: str) -> str:
        normalized = name.strip()
        if normalized.startswith("#"):
            normalized = normalized.lstrip("#").strip()
            if not normalized:
                raise ValueError("Hashtag name cannot be empty")
            warnings.warn(
                f"Hashtag names should not include a leading '#'; normalized to {normalized!r}.",
                UserWarning,
                stacklevel=3,
            )
        if not normalized:
            raise ValueError("Hashtag name cannot be empty")
        return normalized

    def hashtag_info_gql(self, name: str, amount: int = 12, end_cursor: str = None) -> Hashtag:
        """
        Get information about a hashtag by Public Graphql API

        Parameters
        ----------
        name: str
            Name of the hashtag

        amount: int, optional
            Maximum number of media to return, default is 12

        end_cursor: str, optional
            End Cursor, default value is None

        Returns
        -------
        Hashtag
            An object of Hashtag
        """
        name = self._normalize_hashtag_name(name)
        variables = {"tag_name": name, "show_ranked": False, "first": int(amount)}
        if end_cursor:
            variables["after"] = end_cursor
        data = self.public_graphql_request(variables, query_hash="f92f56d47dc7a55b606908374b43a314")
        if not data.get("hashtag"):
            raise HashtagNotFound(name=name, **data)
        return extract_hashtag_gql(data["hashtag"])

    def hashtag_info_v1(self, name: str) -> Hashtag:
        """
        Get information about a hashtag by Private Mobile API

        Parameters
        ----------
        name: str
            Name of the hashtag

        Returns
        -------
        Hashtag
            An object of Hashtag
        """
        name = self._normalize_hashtag_name(name)
        result = self.private_request(f"tags/{name}/info/")
        return extract_hashtag_v1(result)

    def hashtag_info(self, name: str) -> Hashtag:
        """
        Get information about a hashtag

        Parameters
        ----------
        name: str
            Name of the hashtag

        Returns
        -------
        Hashtag
            An object of Hashtag
        """
        name = self._normalize_hashtag_name(name)
        return self.hashtag_info_v1(name)

    def hashtag_medias_v1_chunk(
        self, name: str, max_amount: int = 27, tab_key: str = "", max_id: str = None
    ) -> Tuple[List[Media], str]:
        """
        Get chunk of medias for a hashtag and max_id (cursor) by Private Mobile API

        Parameters
        ----------
        name: str
            Name of the hashtag
        max_amount: int, optional
            Maximum number of media to return, default is 27
        tab_key: str, optional
            Tab Key, default value is ""
        max_id: str
            Max ID, default value is None

        Returns
        -------
        Tuple[List[Media], str]
            List of objects of Media and max_id
        """
        name = self._normalize_hashtag_name(name)
        assert tab_key in (
            "top",
            "recent",
            "clips",
        ), 'You must specify one of the options for "tab_key" ("top", "recent", "clips")'
        media_recency_filter = {
            "top": "default",
            "recent": "top_recent_posts",
        }
        data = {
            "media_recency_filter": media_recency_filter.get(tab_key, tab_key),
            # "page": 1,
            "_uuid": self.uuid,
            "include_persistent": "false",
            "rank_token": self.rank_token,
        }
        if max_id:
            try:
                [page_id, nm_ids] = json.loads(base64.b64decode(max_id))
            except Exception:
                raise WrongCursorError()
            data["max_id"] = page_id
            data["next_media_ids"] = dumps(nm_ids)
        medias = []
        result = self.private_request(
            f"tags/{name}/sections/",
            # params={"max_id": max_id} if max_id else {},
            data=data,
            with_signature=False,
        )
        next_max_id = None
        if result.get("next_max_id"):
            np = result.get("next_max_id")
            ids = result.get("next_media_ids")
            next_max_id = base64.b64encode(json.dumps([np, ids]).encode()).decode()
        for section in result["sections"]:
            layout_content = section.get("layout_content") or {}
            nodes = layout_content.get("medias") or []
            for node in nodes:
                if max_amount and len(medias) >= max_amount:
                    break
                try:
                    media = extract_media_v1(node["media"])
                except (KeyError, AttributeError, TypeError) as exc:
                    self.logger.warning("Skipping malformed hashtag node: %s", exc)
                    continue
                # check contains hashtag in caption
                # if f"#{name}" not in media.caption_text:
                #     continue
                medias.append(media)
        # max_id = result["next_max_id"]
        if not result["more_available"]:
            next_max_id = None  # stop
        return medias, next_max_id

    def hashtag_medias_v1(self, name: str, amount: int = 27, tab_key: str = "") -> List[Media]:
        """
        Get medias for a hashtag by Private Mobile API

        Parameters
        ----------
        name: str
            Name of the hashtag
        amount: int, optional
            Maximum number of media to return, default is 27
        tab_key: str, optional
            Tab Key, default value is ""

        Returns
        -------
        List[Media]
            List of objects of Media
        """
        name = self._normalize_hashtag_name(name)
        medias = []
        max_id = None
        while True:
            items, max_id = self.hashtag_medias_v1_chunk(name, amount, tab_key, max_id)
            medias.extend(items)
            if amount and len(medias) >= amount:
                break
            if not max_id:
                break
        if amount:
            medias = medias[:amount]
        return medias

    def hashtag_medias_top_v1(self, name: str, amount: int = 9) -> List[Media]:
        """
        Get top medias for a hashtag by Private Mobile API

        Parameters
        ----------
        name: str
            Name of the hashtag
        amount: int, optional
            Maximum number of media to return, default is 9

        Returns
        -------
        List[Media]
            List of objects of Media
        """
        name = self._normalize_hashtag_name(name)
        return self.hashtag_medias_v1(name, amount, tab_key="top")

    def hashtag_medias_top(self, name: str, amount: int = 9) -> List[Media]:
        """
        Get top medias for a hashtag

        Parameters
        ----------
        name: str
            Name of the hashtag
        amount: int, optional
            Maximum number of media to return, default is 9

        Returns
        -------
        List[Media]
            List of objects of Media
        """
        name = self._normalize_hashtag_name(name)
        return self.hashtag_medias_top_v1(name, amount)

    def hashtag_medias_recent_v1(self, name: str, amount: int = 27) -> List[Media]:
        """
        Get recent medias for a hashtag by Private Mobile API

        Parameters
        ----------
        name: str
            Name of the hashtag
        amount: int, optional
            Maximum number of media to return, default is 71

        Returns
        -------
        List[Media]
            List of objects of Media
        """
        name = self._normalize_hashtag_name(name)
        return self.hashtag_medias_v1(name, amount, tab_key="recent")

    def hashtag_medias_recent(self, name: str, amount: int = 27) -> List[Media]:
        """
        Get recent medias for a hashtag

        Parameters
        ----------
        name: str
            Name of the hashtag
        amount: int, optional
            Maximum number of media to return, default is 71

        Returns
        -------
        List[Media]
            List of objects of Media
        """
        name = self._normalize_hashtag_name(name)
        return self.hashtag_medias_recent_v1(name, amount)

    def hashtag_medias_reels_v1(self, name: str, amount: int = 27) -> List[Media]:
        """
        Get reels medias for a hashtag by Private Mobile API

        Parameters
        ----------
        name: str
            Name of the hashtag
        amount: int, optional
            Maximum number of media to return, default is 71

        Returns
        -------
        List[Media]
            List of objects of Media
        """
        name = self._normalize_hashtag_name(name)
        return self.hashtag_medias_v1(name, amount, tab_key="clips")

    def hashtag_follow(self, hashtag: str, unfollow: bool = False) -> bool:
        """
        Follow to hashtag
        Parameters
        ----------
        hashtag: str
            Unique identifier of a Hashtag
        unfollow: bool, optional
            Unfollow when True
        Returns
        -------
        bool
            A boolean value
        """
        assert self.user_id, "Login required"
        name = "unfollow" if unfollow else "follow"
        data = self.with_action_data({"user_id": self.user_id})
        result = self.private_request(f"web/tags/{name}/{hashtag}/", domain="www.instagram.com", data=data)
        return result["status"] == "ok"

    def hashtag_following(self, amount: int = 0) -> List[Hashtag]:
        """
        Get hashtags followed by the authenticated account

        Parameters
        ----------
        amount: int, optional
            Maximum number of hashtags to return. Value 0 returns all hashtags
            returned by Instagram.

        Returns
        -------
        List[Hashtag]
            List of objects of Hashtag
        """
        assert self.user_id, "Login required"
        result = self.private_graphql_following_list(
            str(self.user_id),
            self.rank_token,
            priority="u=3, i",
            skip_preview_hashtags=False,
            skip_hashtag_count=False,
        )
        data = result.get("data") or {}
        following = next(
            (
                value
                for key, value in data.items()
                if isinstance(value, dict) and "xdt_api__v1__friendships__following" in key
            ),
            {},
        )
        hashtags = []
        for item in following.get("preview_hashtags") or []:
            if not isinstance(item, dict):
                continue
            node = item.get("hashtag") or item.get("node") or item
            if not isinstance(node, dict) or not node:
                continue
            node = dict(node)
            node["id"] = node.get("id") or node.get("pk")
            node["media_count"] = node.get("media_count") or node.get("post_count") or node.get("postCount")
            node["profile_pic_url"] = node.get("profile_pic_url") or node.get("profilePictureUrl") or None
            if not node.get("id") or not node.get("name"):
                continue
            hashtags.append(Hashtag(**node))
        if amount:
            hashtags = hashtags[:amount]
        return hashtags

    def hashtag_unfollow(self, hashtag: str) -> bool:
        """
        Unfollow to hashtag
        Parameters
        ----------
        hashtag: str
            Unique identifier of a Hashtag
        Returns
        -------
        bool
            A boolean value
        """
        return self.hashtag_follow(hashtag, unfollow=True)
