import base64
import json
import warnings
from typing import Iterator, List, Tuple

from instagrapi.exceptions import ClientError, ClientLoginRequired, HashtagNotFound, PrivateError, WrongCursorError
from instagrapi.extractors import (
    extract_hashtag_gql,
    extract_hashtag_v1,
    extract_media_gql,
    extract_media_v1,
)
from instagrapi.types import Hashtag, Media
from instagrapi.utils.iterators import iter_paginated
from instagrapi.utils.serialization import dumps


class HashtagMixin:
    """
    Helpers for managing Hashtag
    """

    def _hashtag_section_media_nodes(self, section):
        layout_content = section.get("layout_content") or {}
        one_by_two_item = layout_content.get("one_by_two_item") or {}
        if isinstance(one_by_two_item, dict):
            clips = one_by_two_item.get("clips") or {}
            if isinstance(clips, dict):
                for node in clips.get("items") or []:
                    yield node
        for key in ("fill_items", "medias"):
            for node in layout_content.get(key) or []:
                yield node

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
            "tab": tab_key,
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
            for node in self._hashtag_section_media_nodes(section):
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

    def _is_hashtag_v1_cursor(self, cursor: str) -> bool:
        if not cursor:
            return False
        try:
            value = json.loads(base64.b64decode(cursor))
        except Exception:
            return False
        return isinstance(value, list) and len(value) == 2

    def hashtag_medias_paginated_gql(
        self, name: str, amount: int = 27, end_cursor: str = None
    ) -> Tuple[List[Media], str]:
        """
        Get a page of medias for a hashtag by Public GraphQL API

        Parameters
        ----------
        name: str
            Name of the hashtag
        amount: int, optional
            Maximum number of media to return, default is 27
        end_cursor: str, optional
            Cursor value to start at, obtained from previous call to this method

        Returns
        -------
        Tuple[List[Media], str]
            A tuple containing a list of medias and the next end_cursor value
        """
        name = self._normalize_hashtag_name(name)
        amount = int(amount)
        variables = {"tag_name": name, "show_ranked": False, "first": amount}
        if end_cursor:
            variables["after"] = end_cursor
        data = self.public_graphql_request(variables, query_hash="f92f56d47dc7a55b606908374b43a314")
        if not data.get("hashtag"):
            raise HashtagNotFound(name=name, **data)
        media_edge = data["hashtag"].get("edge_hashtag_to_media") or {}
        page_info = media_edge.get("page_info") or {}
        next_cursor = page_info.get("end_cursor") if page_info.get("has_next_page") else None
        medias = []
        for edge in media_edge.get("edges") or []:
            try:
                medias.append(extract_media_gql(edge["node"]))
            except (KeyError, AttributeError, TypeError) as exc:
                self.logger.warning("Skipping malformed hashtag GraphQL node: %s", exc)
        if amount:
            medias = medias[:amount]
        return medias, next_cursor

    def hashtag_medias_paginated_v1(
        self, name: str, amount: int = 27, tab_key: str = "recent", end_cursor: str = None
    ) -> Tuple[List[Media], str]:
        """
        Get a page of medias for a hashtag by Private Mobile API

        Parameters
        ----------
        name: str
            Name of the hashtag
        amount: int, optional
            Maximum number of media to return, default is 27
        tab_key: str, optional
            Tab key: "top", "recent" or "clips", default is "recent"
        end_cursor: str, optional
            Cursor value to start at, obtained from previous call to this method

        Returns
        -------
        Tuple[List[Media], str]
            A tuple containing a list of medias and the next end_cursor value
        """
        name = self._normalize_hashtag_name(name)
        amount = int(amount)
        return self.hashtag_medias_v1_chunk(name, max_amount=amount, tab_key=tab_key, max_id=end_cursor)

    def hashtag_medias_paginated(
        self, name: str, amount: int = 27, tab_key: str = "recent", end_cursor: str = None
    ) -> Tuple[List[Media], str]:
        """
        Get a page of medias for a hashtag

        Parameters
        ----------
        name: str
            Name of the hashtag
        amount: int, optional
            Maximum number of media to return, default is 27
        tab_key: str, optional
            Tab key: "top", "recent" or "clips", default is "recent". Public GraphQL only supports "recent".
        end_cursor: str, optional
            Cursor value to start at, obtained from previous call to this method

        Returns
        -------
        Tuple[List[Media], str]
            A tuple containing a list of medias and the next end_cursor value
        """
        name = self._normalize_hashtag_name(name)
        amount = int(amount)
        end_cursor_is_v1 = self._is_hashtag_v1_cursor(end_cursor)
        private_required = tab_key != "recent" or end_cursor_is_v1

        def public_lookup():
            try:
                return self.hashtag_medias_paginated_gql(name, amount=amount, end_cursor=end_cursor)
            except ClientLoginRequired as e:
                if not self.inject_sessionid_to_public():
                    raise e
                return self.hashtag_medias_paginated_gql(name, amount=amount, end_cursor=end_cursor)

        def private_lookup():
            return self.hashtag_medias_paginated_v1(name, amount=amount, tab_key=tab_key, end_cursor=end_cursor)

        if self._has_private_auth() or private_required:
            try:
                return private_lookup()
            except PrivateError:
                raise
            except Exception as e:
                if private_required:
                    raise e
                if not isinstance(e, ClientError):
                    self.logger.exception(e)
                return public_lookup()
        try:
            return public_lookup()
        except PrivateError:
            raise
        except Exception as e:
            if not isinstance(e, ClientError):
                self.logger.exception(e)
            return private_lookup()

    def iter_hashtag_medias(
        self,
        name: str,
        amount: int = 0,
        page_size: int = 27,
        tab_key: str = "recent",
    ) -> Iterator[Media]:
        """
        Iterate over medias for a hashtag.

        Parameters
        ----------
        name: str
            Name of the hashtag
        amount: int, optional
            Maximum number of media to yield, default is 0 (all medias)
        page_size: int, optional
            Maximum number of media to fetch per page, default is 27
        tab_key: str, optional
            Tab key: "top", "recent" or "clips", default is "recent". Public GraphQL only supports "recent".

        Returns
        -------
        Iterator[Media]
            Iterator of Media objects
        """
        name = self._normalize_hashtag_name(name)

        def fetch_page(end_cursor: str, page_amount: int) -> Tuple[List[Media], str]:
            return self.hashtag_medias_paginated(name, amount=page_amount, tab_key=tab_key, end_cursor=end_cursor)

        return iter_paginated(fetch_page, amount=amount, page_size=page_size, initial_cursor=None)

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
