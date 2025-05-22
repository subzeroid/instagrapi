from typing import List

from instagrapi.extractors import extract_media_v1
from instagrapi.instagrapi_types import Media


class ReelsMixin:
    """
    Helpers for Reels
    """

    def feed(self, amount: int = None, next_max_id: str = None):
        nb_posts = 0
        data = {
            '_uuid': self.uuid,
            '_csrftoken': self.token,
            'is_prefetch': '0',
            'is_pull_to_refresh': '0',
            'phone_id': self.phone_id,
            'timezone_offset': self.timezone_offset,
        }

        while True:
            if amount and nb_posts >= amount:
                break
            if next_max_id:
                data["max_id"] = next_max_id
            result = self.private_request("feed/timeline/", data=data, with_signature=False)

            for item in result["feed_items"]:
                media = item.get("media_or_ad")
                if media:
                    yield extract_media_v1(media)
                    nb_posts += 1
                    if amount and nb_posts >= amount:
                        break

            if not result.get("more_available"):
                break
            next_max_id = result.get('next_max_id')
            self.last_cursor = next_max_id

    def reels(self, amount: int = 10, last_media_pk: int = 0) -> List[Media]:
        """
        Get connected reels media

        Parameters
        ----------
        amount: int, optional
            Maximum number of media to return, default is 10
        last_media_pk: int, optional
            Last PK user has seen, function will return medias after this pk. Default is 0
        Returns
        -------
        List[Media]
            A list of objects of Media
        """
        return self.reels_timeline_media("reels", amount, last_media_pk)

    def explore_reels(self, amount: int = 10, last_media_pk: int = 0) -> List[Media]:
        """
        Get discover reels media

        Parameters
        ----------
        amount: int, optional
            Maximum number of media to return, default is 10
        last_media_pk: int, optional
            Last PK user has seen, function will return medias after this pk. Default is 0
        Returns
        -------
        List[Media]
            A list of objects of Media
        """
        return self.reels_timeline_media("explore_reels", amount, last_media_pk)

    def reels_timeline_media(self,
                             collection_pk: str,
                             amount: int = 10,
                             last_media_pk: int = 0) -> List[Media]:
        """
        Get reels timeline media in a collection

        Parameters
        ----------
        collection_pk: str
            Unique identifier of a timeline
        amount: int, optional
            Maximum number of media to return, default is 10
        last_media_pk: int, optional
            Last PK user has seen, function will return medias after this pk. Default is 0

        Returns
        -------
        List[Media]
            A list of objects of Media
        """

        if collection_pk == "reels":
            private_request_endpoint = "clips/connected/"
        elif collection_pk == 'explore_reels':
            private_request_endpoint = "clips/discover/"

        last_media_pk = last_media_pk and int(last_media_pk)
        total_items = []
        next_max_id = ""
        while True:
            if len(total_items) >= float(amount):
                return total_items[:amount]
            try:
                result = self.private_request(
                    private_request_endpoint,
                    data=' ',
                    params={"max_id": next_max_id},
                )
            except Exception as e:
                return total_items

            for item in result["items"]:
                if last_media_pk and last_media_pk == item["media"]["pk"]:
                    return total_items
                total_items.append(extract_media_v1(item.get("media")))

            if not result.get('paging_info', {}).get("more_available"):
                return total_items

            next_max_id = result.get('paging_info', {}).get("more_available")
