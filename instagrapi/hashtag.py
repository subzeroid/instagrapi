import time

from .extractors import extract_hashtag_gql, extract_hashtag_v1
from .exceptions import ClientError


class HashtagMixin:

    def hashtag_info_a1(self, name, max_id=None):
        params = {"max_id": max_id} if max_id else None
        data = self.public_a1_request(
            f"/explore/tags/{name}/", params=params
        )
        return extract_hashtag_gql(data["hashtag"])

    def hashtag_info_gql(self, name, count=12, end_cursor=None):
        variables = {
            "tag_name": name,
            "show_ranked": False,
            "first": int(count),
        }
        if end_cursor:
            variables["after"] = end_cursor
        data = self.public_graphql_request(
            variables, query_hash="f92f56d47dc7a55b606908374b43a314"
        )
        return extract_hashtag_gql(data["hashtag"])

    def hashtag_info_v1(self, name):
        result = self.private_request(f'tags/{name}/info/')
        return extract_hashtag_v1(result)

    def hashtag_info(self, name, count=12):
        try:
            hashtag = self.hashtag_info_a1(name)
        except Exception as e:
            if not isinstance(e, ClientError):
                self.logger.exception(e)
            hashtag = self.hashtag_info_v1(name)
        return hashtag

    def hashtag_top_feed(self, hashtag):
        data = self.hashtag_info_a1(hashtag)
        return data["edge_hashtag_to_top_posts"]["edges"]

    def hashtag_related_hashtags(self, hashtag):
        data = self.hashtag_info_a1(hashtag)
        return [
            item["node"]["name"]
            for item in data["edge_hashtag_to_related_tags"]["edges"]
        ]

    def hashtag_feed(self, hashtag, count=70, sleep=2):
        medias = []
        end_cursor = None
        while True:
            data = self.hashtag_info(hashtag, end_cursor)
            end_cursor = data["edge_hashtag_to_media"]["page_info"]["end_cursor"]
            edges = data["edge_hashtag_to_media"]["edges"]
            medias.extend(edges)
            if (
                not data["edge_hashtag_to_media"]["page_info"]["has_next_page"]
                or len(medias) >= count
            ):
                break
            time.sleep(sleep)
        return medias[:count]
