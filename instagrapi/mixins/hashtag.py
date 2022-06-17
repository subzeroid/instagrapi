from typing import List, Tuple

from instagrapi.exceptions import ClientError, HashtagNotFound
from instagrapi.extractors import (
    extract_hashtag_gql,
    extract_hashtag_v1,
    extract_media_gql,
    extract_media_v1,
)
from instagrapi.types import Hashtag, Media
from instagrapi.utils import dumps


class HashtagMixin:
    """
    Helpers for managing Hashtag
    """

    def hashtag_info_gql(
        self, name: str, amount: int = 12, end_cursor: str = None
    ) -> Hashtag:
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
        data = self.public_graphql_request(
            variables, query_hash="f92f56d47dc7a55b606908374b43a314"
        )
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
            self.hashtag_medias_v1_logged_out(name)
            hashtag = extract_hashtag_gql(self.last_json["data"]["hashtag"])
        except Exception:
            # Users do not understand the output of such information and create bug reports
            # such this - https://github.com/adw0rd/instagrapi/issues/364
            # if not isinstance(e, ClientError):
            #     self.logger.exception(e)
            hashtag = self.hashtag_info_v1(name)
        return hashtag

    def hashtag_medias_v1_logged_out(
                self, name: str, max_amount: int = 27, tab_key: str = ""
        ) -> List[Media]:
            """
            Get chunk of medias for a hashtag and max_id (cursor) by Private Web API

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
            result = self.private_request(
                f"tags/logged_out_web_info/?tag_name={name}",
            )
            for node in result["data"]["hashtag"][tab_key]["edges"]:
                media = extract_media_gql(node["node"])
                yield media
                nb_media += 1
                if max_amount and nb_media >= max_amount:
                    break

    def hashtag_medias_gql(
        self, name: str, amount: int = 12, tab_key: str = "", end_cursor: str = None
    ) -> Hashtag:
        """
        Get chunk of medias for a hashtag and max_id (cursor) by Public Graphql API

        Parameters
        ----------
        name: str
            Name of the hashtag

        amount: int, optional
            Maximum number of media to return, default is 12

        tab_key: str, optional
            Tab Key, default value is ""

        end_cursor: str, optional
            End Cursor, default value is None

        Returns
        -------
        Hashtag
            An object of Hashtag
        """
        assert tab_key in ("edge_hashtag_to_top_posts", "edge_hashtag_to_media"), \
                       'You must specify one of the options for "tab_key" ("edge_hashtag_to_top_posts" or "edge_hashtag_to_media")'

        unique_set = set()
        nb_media = 0
        variables = {"tag_name": name, "show_ranked": False, "first": 100}
        while True:
            if end_cursor:
                variables["after"] = end_cursor
                self.last_cursor = end_cursor

            data = self.public_graphql_request(
                variables, query_hash="f92f56d47dc7a55b606908374b43a314"
            )["hashtag"]
            page_info = data[tab_key]["page_info"]
            edges = data[tab_key]["edges"]
            for edge in edges:
                media_pk = edge["node"]["id"]
                if media_pk in unique_set:
                    continue
                unique_set.add(media_pk)
                media = extract_media_gql(edge["node"])
                yield media
                nb_media += 1
                if amount and nb_media >= amount:
                    break

            if not page_info.get("has_next_page") or not page_info.get("end_cursor") or (
                    amount and nb_media >= amount):
                print(page_info)
                break
            end_cursor = page_info["end_cursor"]


    def hashtag_medias_v1(
        self, name: str, max_amount: int = 27, tab_key: str = "", max_id: str = None
    ) -> List[Media]:
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
        generator<Media>
            generator of objects of Media
        """
        assert tab_key in ("top", "recent"), \
            'You must specify one of the options for "tab_key" ("top" or "recent")'
        data = {
            "supported_tabs": dumps([tab_key]),
            # 'lat': 59.8626416,
            # 'lng': 30.5126682,
            "include_persistent": "true",
            "rank_token": self.rank_token,
            "count": 10000,
        }
        nb_media = 0
        while True:
            self.last_cursor = max_id
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
                    nb_media += 1
                    if max_amount and nb_media >= max_amount:
                        break
            if not result["more_available"] or (max_amount and nb_media >= max_amount):
                break
            max_id = result["next_max_id"]


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
            self.logger.info("Use GQL method")
            yield from self.hashtag_medias_gql(name, amount, tab_key="edge_hashtag_to_top_posts", end_cursor=end_cursor)
        except ClientError:
            self.logger.info("Use V1 method")
            yield from self.hashtag_medias_v1(name, amount, tab_key="top", max_id=end_cursor)


    def hashtag_medias_recent(self, name: str, amount: int = 27, end_cursor: str = None) -> List[Media]:
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
            self.logger.info("Use GQL method")
            yield from self.hashtag_medias_gql(name, amount, tab_key="edge_hashtag_to_media", end_cursor=end_cursor)
        except ClientError:
            self.logger.info("Use V1 method")
            yield from self.hashtag_medias_v1(name, amount, tab_key="recent", max_id=end_cursor)
