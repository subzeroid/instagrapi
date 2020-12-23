from typing import List

from instagrapi.extractors import (
    extract_hashtag_gql,
    extract_hashtag_v1,
    extract_media_gql,
    extract_media_v1
)
from instagrapi.exceptions import ClientError, ClientLoginRequired
from instagrapi.types import Hashtag, Media
from instagrapi.utils import dumps


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

    def hashtag_related_hashtags(self, name: str) -> List[Hashtag]:
        """Get related hashtags
        """
        data = self.public_a1_request(f"/explore/tags/{name}/")
        return [
            extract_hashtag_gql(item["node"])
            for item in data['hashtag']['edge_hashtag_to_related_tags']["edges"]
        ]

    def hashtag_medias_a1(self, name: str, amount: int = 27, tab_key: str = '') -> List[Media]:
        """Receive medias by hashtag name
        """
        uniqs = set()
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
                # check uniq
                media_pk = edge['node']['id']
                if media_pk in uniqs:
                    continue
                uniqs.add(media_pk)
                # check contains hashtag in caption
                media = extract_media_gql(edge['node'])
                if f'#{name}' not in media.caption_text:
                    continue
                # fetch full media with User, Usertags, video_url
                medias.append(self.media_info_gql(media_pk))
            if not page_info["has_next_page"] or not end_cursor:
                break
            if amount and len(medias) >= amount:
                break
        if amount:
            medias = medias[:amount]
        return medias

    def hashtag_medias_v1(self, name: str, amount: int = 27, tab_key: str = '') -> List[Media]:
        """Receive medias by hashtag name
        """
        data = {
            'supported_tabs': dumps([tab_key]),
            # 'lat': 59.8626416,
            # 'lng': 30.5126682,
            'include_persistent': 'true',
            'rank_token': self.rank_token,
        }
        max_id = None
        medias = []
        while True:
            result = self.private_request(
                f'tags/{name}/sections/',
                params={"max_id": max_id} if max_id else {},
                data=self.with_default_data(data)
            )
            for section in result['sections']:
                layout_content = section.get('layout_content') or {}
                nodes = layout_content.get('medias') or []
                for node in nodes:
                    if amount and len(medias) >= amount:
                        break
                    media = extract_media_v1(node['media'])
                    # check contains hashtag in caption
                    if f'#{name}' not in media.caption_text:
                        continue
                    medias.append(media)
            if not result["more_available"]:
                break
            if amount and len(medias) >= amount:
                break
            max_id = result["next_max_id"]
        if amount:
            medias = medias[:amount]
        return medias

    def hashtag_medias_top_a1(self, name: str, amount: int = 9) -> List[Media]:
        """Top medias by public API
        """
        return self.hashtag_medias_a1(
            name, amount,
            tab_key='edge_hashtag_to_top_posts'
        )

    def hashtag_medias_top_v1(self, name: str, amount: int = 9) -> List[Media]:
        """Top medias by private API
        """
        return self.hashtag_medias_v1(name, amount, tab_key='top')

    def hashtag_medias_top(self, name: str, amount: int = 9) -> List[Media]:
        """Top medias
        """
        try:
            try:
                medias = self.hashtag_medias_top_a1(name, amount)
            except ClientLoginRequired as e:
                if not self.inject_sessionid_to_public():
                    raise e
                medias = self.hashtag_medias_top_a1(name, amount)  # retry
        except Exception as e:
            if not isinstance(e, ClientError):
                self.logger.exception(e)
            medias = self.hashtag_medias_top_v1(name, amount)
        return medias

    def hashtag_medias_recent_a1(self, name: str, amount: int = 71) -> List[Media]:
        """Recent medias by public API
        """
        return self.hashtag_medias_a1(
            name, amount,
            tab_key='edge_hashtag_to_media'
        )

    def hashtag_medias_recent_v1(self, name: str, amount: int = 27) -> List[Media]:
        """Recent medias by private API
        """
        return self.hashtag_medias_v1(name, amount, tab_key='recent')

    def hashtag_medias_recent(self, name: str, amount: int = 27) -> List[Media]:
        """Recent medias
        """
        try:
            try:
                medias = self.hashtag_medias_recent_a1(name, amount)
            except ClientLoginRequired as e:
                if not self.inject_sessionid_to_public():
                    raise e
                medias = self.hashtag_medias_recent_a1(name, amount)  # retry
        except Exception as e:
            if not isinstance(e, ClientError):
                self.logger.exception(e)
            medias = self.hashtag_medias_recent_v1(name, amount)
        return medias
