from typing import List

from instagrapi.exceptions import CollectionNotFound
from instagrapi.extractors import extract_collection, extract_media_v1
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
                    "collections/list/",
                    params={
                        "collection_types": '["ALL_MEDIA_AUTO_COLLECTION","PRODUCT_AUTO_COLLECTION","MEDIA"]',
                        "max_id": next_max_id,
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

    def collection_pk_by_name(self, name: str) -> int:
        """
        Get collection_pk by name

        Parameters
        ----------
        name: str
            Name of the collection

        Returns
        -------
        List[Collection]
            A list of objects of Collection
        """
        for item in self.collections():
            if item.name == name:
                return item.id
        raise CollectionNotFound(name=name)

    def collection_medias_by_name(self, name: str) -> List[Collection]:
        """
        Get medias by collection name

        Parameters
        ----------
        name: str
            Name of the collection

        Returns
        -------
        List[Collection]
            A list of collections
        """

        return self.collection_medias(self.collection_pk_by_name(name))

    def collection_medias(
        self, collection_pk: str, amount: int = 21, last_media_pk: int = 0
    ) -> List[Media]:
        """
        Get media in a collection by collection_pk

        Parameters
        ----------
        collection_pk: str
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
        if collection_pk.isdigit():
            private_request_endpoint = f"feed/collection/{collection_pk}/"
        else:
            private_request_endpoint = "feed/saved/posts/"

        last_media_pk = last_media_pk and int(last_media_pk)
        total_items = []
        next_max_id = ""
        while True:
            if len(total_items) >= float(amount):
                return total_items[:amount]
            try:
                result = self.private_request(
                    private_request_endpoint,
                    params={"include_igtv_preview": "false", "max_id": next_max_id},
                )
            except Exception as e:
                self.logger.exception(e)
                return total_items
            for item in result["items"]:
                if last_media_pk and last_media_pk == item["media"]["pk"]:
                    return total_items
                total_items.append(extract_media_v1(item["media"]))
            if not result.get("more_available"):
                return total_items
            next_max_id = result.get("next_max_id", "")
        return total_items

    def media_save(self, media_id: str, collection_pk: int = None, revert: bool = False) -> bool:
        """
        Save a media to collection

        Parameters
        ----------
        media_id: str
            Unique identifier of a Media
        collection_pk: int
            Unique identifier of a Collection
        revert: bool, optional
            If True then save to collection, otherwise unsave

        Returns
        -------
        bool
            A boolean value
        """
        assert self.user_id, "Login required"
        media_id = self.media_id(media_id)
        data = {
            "module_name": "feed_timeline",
            "radio_type": "wifi-none",
        }
        if collection_pk:
            data["added_collection_ids"] = f"[{int(collection_pk)}]"
        name = "unsave" if revert else "save"
        result = self.private_request(
            f"media/{media_id}/{name}/", self.with_action_data(data)
        )
        return result["status"] == "ok"

    def media_unsave(self, media_id: str, collection_pk: int = None) -> bool:
        """
        Unsave a media

        Parameters
        ----------
        media_id: str
            Unique identifier of a Media
        collection_pk: int
            Unique identifier of a Collection

        Returns
        -------
        bool
            A boolean value
        """
        return self.media_save(media_id, collection_pk, revert=True)
