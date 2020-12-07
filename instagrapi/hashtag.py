import time
from typing import List

from .extractors import (
    extract_hashtag_gql,
    extract_hashtag_v1,
    extract_media_v1
)
from .exceptions import ClientError
from .types import Hashtag, Media
from .utils import dumps


class HashtagMixin:

    def hashtag_info_a1(self, name: str, max_id: str = None) -> Hashtag:
        """Get info (id, name, profile_pic_url)
        """
        params = {"max_id": max_id} if max_id else None
        data = self.public_a1_request(
            f"/explore/tags/{name}/", params=params
        )
        return extract_hashtag_gql(data["hashtag"])

    def hashtag_info_gql(self, name: str, amount: int = 12, end_cursor: str = None) -> Hashtag:
        """Get info (id, name, profile_pic_url)
        """
        variables = {
            "tag_name": name,
            "show_ranked": False,
            "first": int(amount)
        }
        if end_cursor:
            variables["after"] = end_cursor
        data = self.public_graphql_request(
            variables, query_hash="f92f56d47dc7a55b606908374b43a314"
        )
        return extract_hashtag_gql(data["hashtag"])

    def hashtag_info_v1(self, name: str) -> Hashtag:
        """Get info (id, name, profile_pic_url)
        """
        result = self.private_request(f'tags/{name}/info/')
        return extract_hashtag_v1(result)

    def hashtag_info(self, name: str) -> Hashtag:
        """Get info (id, name, profile_pic_url)
        """
        try:
            hashtag = self.hashtag_info_a1(name)
        except Exception as e:
            if not isinstance(e, ClientError):
                self.logger.exception(e)
            hashtag = self.hashtag_info_v1(name)
        return hashtag

    def hashtag_related_hashtags(self, name):
        """Get related hashtags
        """
        data = self.public_a1_request(f"/explore/tags/{name}/")
        return [
            extract_hashtag_gql(item["node"])
            for item in data['hashtag']['edge_hashtag_to_related_tags']["edges"]
        ]

    def hashtag_medias_a1(self, name: str, amount: int = 27, sleep: float = 0.5, tab_key: str = '') -> List[Media]:
        """Receive medias by hastag name
        """
        medias = []
        end_cursor = None
        while True:
            data = self.public_a1_request(
                f'/explore/tags/{name}/',
                params={"max_id": end_cursor} if end_cursor else {}
            )['hashtag']
            page_info = data["edge_hashtag_to_media"]["page_info"]
            end_cursor = page_info["end_cursor"]
            edges = data[tab_key]["edges"]
            for edge in edges:
                if amount and len(medias) >= amount:
                    break
                node = edge['node']
                # node haven't video_url and
                #   User fields (username, pic_url, full_name)
                # if 'username' not in node['owner']:
                #     node['owner'] = self.user_short_gql(
                #         node['owner']['id']
                #     ).dict()
                #     time.sleep(sleep)
                # medias.append(extract_media_gql(node))
                medias.append(
                    self.media_info_gql(node['id'])
                )
                time.sleep(sleep)
            if not page_info["has_next_page"] or not end_cursor:
                break
            if amount and len(medias) >= amount:
                break
            time.sleep(sleep)
        # Post unique filtration
        # (if calculate immediately, then the cycle can be infinite)
        uniq_pks = set()
        medias = [
            m for m in medias
            if not (m.pk in uniq_pks or uniq_pks.add(m.pk))
        ]
        if amount:
            medias = medias[:amount]
        return medias

    def hashtag_medias_v1(self, name: str, amount: int = 27, tab_key: str = '') -> List[Media]:
        """Receive medias by hastag name
        """
        data = {
            'supported_tabs': dumps([tab_key]),
            # 'lat': 59.8626416,
            # 'lng': 30.5126682,
            'include_persistent': 'true',
            'rank_token': self.rank_token,
        }
        result = self.private_request(
            f'tags/{name}/sections/', self.with_default_data(data)
        )
        medias = []
        for section in result['sections']:
            for node in section['layout_content']['medias']:
                medias.append(
                    extract_media_v1(node['media'])
                )
        if amount:
            medias = medias[:amount]
        return medias

    def hashtag_medias_top_a1(self, name: str, amount: int = 9, sleep: float = 0.5) -> List[Media]:
        """Top medias
        """
        return self.hashtag_medias_a1(
            name, amount, sleep=sleep,
            tab_key='edge_hashtag_to_top_posts'
        )

    def hashtag_medias_top_v1(self, name: str, amount: int = 9) -> List[Media]:
        """Top medias
        """
        return self.hashtag_medias_v1(name, amount, tab_key='top')

    def hashtag_medias_top(self, name: str, amount: int = 9) -> List[Media]:
        """Top medias
        """
        try:
            medias = self.hashtag_medias_top_a1(name, amount)
        except Exception as e:
            if not isinstance(e, ClientError):
                self.logger.exception(e)
            medias = self.hashtag_medias_top_v1(name, amount)
        return medias

    def hashtag_medias_recent_a1(self, name: str, amount: int = 27, sleep: float = 0.5) -> List[Media]:
        """Recent medias
        """
        return self.hashtag_medias_a1(
            name, amount, sleep=sleep,
            tab_key='edge_hashtag_to_media'
        )

    def hashtag_medias_recent_v1(self, name: str, amount: int = 27) -> List[Media]:
        """All medias
        """
        return self.hashtag_medias_v1(name, amount, tab_key='recent')

    def hashtag_medias_recent(self, name: str, amount: int = 27) -> List[Media]:
        """All medias
        """
        try:
            medias = self.hashtag_medias_recent_a1(name, amount)
        except Exception as e:
            if not isinstance(e, ClientError):
                self.logger.exception(e)
            medias = self.hashtag_medias_recent_v1(name, amount)
        return medias
