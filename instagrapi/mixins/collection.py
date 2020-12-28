from typing import List

from instagrapi.exceptions import CollectionNotFound
from instagrapi.extractors import extract_media_v1, extract_collection
from instagrapi.types import Collection, Media


class CollectionMixin:
    """
    Helpers for collection
    """

    def collections(self) -> List[Collection]:
        """
        Get collections

        Returns
        -------
        List[Collection]
            A list of objects of Collection
        """
        next_max_id = ""
        total_items = []
        while True:
            try:
                result = self.private_request(
                    "/collections/list/",
                    params={
                        "collection_types": '["ALL_MEDIA_AUTO_COLLECTION","PRODUCT_AUTO_COLLECTION","MEDIA"]',
                        "max_id": next_max_id
                    },
                )
            except Exception as e:
                self.logger.exception(e)
                return total_items
            for item in result["items"]:
                total_items.append(extract_collection(item))
            if not result.get("more_available"):
                return total_items
            next_max_id = result.get("next_max_id", "")
        return total_items

    def collection_medias_by_name(self, name: str) -> List[Collection]:
        """
        Get collections by name

        Parameters
        ----------
        name: str
            Name of the media

        Returns
        -------
        List[Collection]
            A list of objects of Collection
        """
        for item in self.collections():
            if item.name.lower() == name.lower():
                return self.collection_medias(item.id)
        raise CollectionNotFound()

    def collection_medias(self, collection_pk: int, amount: int = 21, last_media_pk: int = 0) -> List[Media]:
        """
        Get media in a collection by collection pk

        Parameters
        ----------
        collection_pk: int
            Unique identifier of a Collection
        amount: int, optional
            Maximum number of media to return, default is 21
        last_media_pk: int, optional
            Last PK user has seen, function will return medias after this pk. Default is 0

        Returns
        -------
        List[Media]
            A list of objects of Media
        """
        collection_pk = int(collection_pk)
        last_media_pk = last_media_pk and int(last_media_pk)
        total_items = []
        next_max_id = ""
        while True:
            if len(total_items) >= float(amount):
                return total_items[:amount]
            try:
                result = self.private_request(
                    f"feed/collection/{collection_pk}/",
                    params={"include_igtv_preview": "false", "max_id": next_max_id},
                )
            except Exception as e:
                self.logger.exception(e)
                return total_items
            for item in result["items"]:
                if last_media_pk and last_media_pk == item['media']['pk']:
                    return total_items
                total_items.append(extract_media_v1(item["media"]))
            if not result.get("more_available"):
                return total_items
            next_max_id = result.get("next_max_id", "")
        return total_items
