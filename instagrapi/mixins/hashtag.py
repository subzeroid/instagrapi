from typing import List

from instagrapi.exceptions import ClientError, HashtagNotFound
from instagrapi.extractors import (
    extract_hashtag_gql, extract_hashtag_v1, extract_media_gql, extract_media_v1
)
from instagrapi.instagrapi_types import Hashtag, Media
from instagrapi.utils import dumps


class HashtagMixin:
    """
    Helpers for managing Hashtag
    """

    def hashtag_info_a1(self, name: str, max_id: str = None) -> Hashtag:
        """
        Get information about a hashtag by Public Web API
        Parameters
        ----------
        name: str
            Name of the hashtag
        max_id: str
            Max ID, default value is None
        Returns
        -------
        Hashtag
            An object of Hashtag
        """
        params = {"max_id": max_id} if max_id else None
        data = self.public_a1_request(f"/explore/tags/{name}/", params=params)
        if not data.get("hashtag"):
            raise HashtagNotFound(name=name, **data)
        return extract_hashtag_gql(data["hashtag"])

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
        try:
            self.hashtag_medias_v1_logged_out_chunk(name)
            hashtag = extract_hashtag_gql(self.last_json["data"]["hashtag"])
        except Exception:
            try:
                hashtag = self.hashtag_info_a1(name)
            except Exception:
                hashtag = self.hashtag_info_v1(name)
        return hashtag

    def hashtag_medias_v1_logged_out_chunk(
        self, name: str, max_amount: int = 27, tab_key: str = ""
    ) -> List[Media]:
        """
            Get chunk of medias for a hashtag by Private Web API

            Parameters
            ----------
            name: str
                Name of the hashtag
            max_amount: int, optional
                Maximum number of media to return, default is 27

            Returns
            -------
            generator<Media>
                generator of objects of Media
            """
        assert tab_key in ("edge_hashtag_to_top_posts", "edge_hashtag_to_media"), \
            'You must specify one of the options for "tab_key" ("edge_hashtag_to_top_posts" or "edge_hashtag_to_media")'

        nb_media = 0
        result = self.private_request(f"tags/logged_out_web_info/?tag_name={name}",)
        for node in result["data"]["hashtag"][tab_key]["edges"]:
            media = extract_media_gql(node["node"])
            yield media
            nb_media += 1
            if max_amount and nb_media >= max_amount:
                break

    def hashtag_medias_a1_chunk(self,
                                name: str,
                                tab_key: str = "",
                                end_cursor: str = None) -> List[Media]:
        """
        Get one chunk of medias and end_cursor by Public Web API
        Parameters
        ----------
        name: str
            Name of the hashtag
        tab_key: str, optional
            Tab Key, default value is ""
        end_cursor: str, optional
            End Cursor, default value is None
        Returns
        -------
        generator<Media>
            generator of objects of Media
        """
        data = self.public_a1_request(
            f"/explore/tags/{name}/",
            params={"max_id": end_cursor} if end_cursor else {},
        )["hashtag"]
        self.last_public_json = self.last_public_json.get("graphql", self.last_public_json)

        edges = data[tab_key]["edges"]
        for edge in edges:
            media = extract_media_gql(edge["node"])
            yield media

    def hashtag_medias_gql_chunk(self,
                                 name: str,
                                 tab_key: str = "",
                                 end_cursor: str = None) -> List[Media]:
        """
        Get one chunk of medias for a hashtag by Public Graphql API

        Parameters
        ----------
        name: str
            Name of the hashtag
        tab_key: str, optional
            Tab Key, default value is ""
        end_cursor: str, optional
            End Cursor, default value is None
        Returns
        -------
        generator<Media>
            generator of objects of Media
        """
        assert tab_key in ("edge_hashtag_to_top_posts", "edge_hashtag_to_media"), \
                       'You must specify one of the options for "tab_key" ("edge_hashtag_to_top_posts" or "edge_hashtag_to_media")'

        variables = {"tag_name": name, "show_ranked": False, "first": 100}
        if end_cursor:
            variables["after"] = end_cursor
            self.last_cursor = end_cursor

        data = self.public_graphql_request(
            variables, query_hash="f92f56d47dc7a55b606908374b43a314"
        )["hashtag"]
        self.last_public_json = self.last_public_json.get("data", self.last_public_json)

        edges = data[tab_key]["edges"]
        for edge in edges:
            media = extract_media_gql(edge["node"])
            yield media

    def hashtag_medias_v1_chunk(self,
                                name: str,
                                tab_key: str = "",
                                max_id: str = None) -> List[Media]:
        """
        Get chunk of medias for a hashtag by Private Mobile API

        Parameters
        ----------
        name: str
            Name of the hashtag
        tab_key: str, optional
            Tab Key, default value is ""
        max_id: str
            Max ID, default value is None

        Returns
        -------
        generator<Media>
            generator of objects of Media
        """
        assert tab_key in ("top", "recent"), \
            'You must specify one of the options for "tab_key" ("top" or "recent")'
        data = {
            "supported_tabs": dumps([tab_key]),
            "include_persistent": "true",
            "rank_token": self.rank_token,
            "count": 10000,
        }
        result = self.private_request(
            f"tags/{name}/sections/",
            params={"max_id": max_id} if max_id else {},
            data=self.with_default_data(data),
        )
        for section in result["sections"]:
            layout_content = section.get("layout_content") or {}
            nodes = layout_content.get("medias") or []
            for node in nodes:
                media = extract_media_v1(node["media"])
                yield media

    def hashtag_medias(
        self,
        name: str,
        max_amount: int = 27,
        tab_key: str = "",
        end_cursor: str = None,
        method_api: str = "",
        first_page=False
    ) -> List[Media]:
        """
        Get medias by Public Web API (A1) or Public Graphql API
        Parameters
        ----------
        name: str
            Name of the hashtag
        tab_key: str
            Tab Key, default value is ""
        max_amount: int, optional
            Maximum number of media to return, default is 27
        end_cursor: str, optional
            End Cursor, default value is None
        method_api: str
            Method api, default value is ""
        Returns
        -------
        generator<Media>
            generator of objects of Media
        """
        assert tab_key in ("edge_hashtag_to_top_posts", "edge_hashtag_to_media", "recent", "top"), \
            'You must specify one of the options for "tab_key" ("edge_hashtag_to_top_posts" or "edge_hashtag_to_media" or "top", or "recent")'

        assert method_api in ("A1", "GQL", "V1"), \
            'You must specify one of the option for "method_api" ("A1", "GQL", "V1")'

        media_ids = set()
        nb_media = 0
        while True:
            self.last_cursor = end_cursor
            if method_api == "A1":
                medias = self.hashtag_medias_a1_chunk(name, tab_key, end_cursor)
            if method_api == "GQL":
                medias = self.hashtag_medias_gql_chunk(name, tab_key, end_cursor)
            if method_api == "V1":
                medias = self.hashtag_medias_v1_chunk(name, tab_key, end_cursor)

            for media in medias:
                if media.pk not in media_ids:
                    yield media
                    media_ids.add(media.pk)
                    nb_media += 1
                if max_amount and nb_media >= max_amount:
                    break
            if max_amount and nb_media >= max_amount or first_page is True:
                break

            if method_api == "V1":
                page_info = self.last_json
                if not page_info.get("more_available") or not page_info.get("next_max_id"):
                    break
                end_cursor = page_info["next_max_id"]
            else:
                page_info = self.last_public_json["hashtag"][tab_key]["page_info"]
                if not page_info.get("has_next_page") or not page_info.get("end_cursor"):
                    break
                end_cursor = page_info["end_cursor"]

    def hashtag_medias_top(self, name: str, amount: int = 9, end_cursor: str = None) -> List[Media]:
        """
        Get top medias for a hashtag

        Parameters
        ----------
        name: str
            Name of the hashtag
        amount: int, optional
            Maximum number of media to return, default is 9
        end_cursor: str, optional
            End Cursor, default value is None

        Returns
        -------
        generator<Media>
            generator of objects of Media
        """

        try:
            yield from self.hashtag_medias(
                name,
                amount,
                tab_key="edge_hashtag_to_top_posts",
                end_cursor=end_cursor,
                method_api="GQL"
            )
        except ClientError:
            yield from self.hashtag_medias(
                name, amount, tab_key="top", end_cursor=end_cursor, method_api="V1"
            )

    def hashtag_medias_recent(self,
                              name: str,
                              amount: int = 27,
                              end_cursor: str = None) -> List[Media]:
        """
        Get recent medias for a hashtag

        Parameters
        ----------
        name: str
            Name of the hashtag
        amount: int, optional
            Maximum number of media to return, default is 71
        end_cursor: str, optional
            End Cursor, default value is None

        Returns
        -------
        generator<Media>
            generator of objects of Media
        """
        try:
            yield from self.hashtag_medias(
                name,
                amount,
                tab_key="edge_hashtag_to_media",
                end_cursor=end_cursor,
                method_api="GQL"
            )
        except ClientError:
            yield from self.hashtag_medias(
                name, amount, tab_key="recent", end_cursor=end_cursor, method_api="V1"
            )
