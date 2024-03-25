import json
import random
import time
from copy import deepcopy
from datetime import datetime
from typing import Dict, List, Tuple
from urllib.parse import urlparse

from instagrapi.exceptions import (
    ClientError,
    ClientLoginRequired,
    ClientNotFoundError,
    MediaNotFound,
    PrivateError,
)
from instagrapi.extractors import (
    extract_location,
    extract_media_gql,
    extract_media_oembed,
    extract_media_v1,
    extract_user_short,
)
from instagrapi.types import Location, Media, UserShort, Usertag
from instagrapi.utils import InstagramIdCodec, json_value


class MediaMixin:
    """
    Helpers for media
    """

    _medias_cache = {}  # pk -> object

    def media_id(self, media_pk: str) -> str:
        """
        Get full media id

        Parameters
        ----------
        media_pk: str
            Unique Media ID

        Returns
        -------
        str
            Full media id

        Example
        -------
        2277033926878261772 -> 2277033926878261772_1903424587
        """
        media_id = str(media_pk)
        if "_" not in media_id:
            assert media_id.isdigit(), (
                "media_id must been contain digits, now %s" % media_id
            )
            user = self.media_user(media_id)
            media_id = "%s_%s" % (media_id, user.pk)
        return media_id

    @staticmethod
    def media_pk(media_id: str) -> str:
        """
        Get short media id

        Parameters
        ----------
        media_id: str
            Unique Media ID

        Returns
        -------
        str
            media id

        Example
        -------
        2277033926878261772_1903424587 -> 2277033926878261772
        """
        media_pk = str(media_id)
        if "_" in media_pk:
            media_pk, _ = media_id.split("_")
        return str(media_pk)

    def media_code_from_pk(self, media_pk: str) -> str:
        """
        Get Code from Media PK

        Parameters
        ----------
        media_pk: str
            Media PK

        Returns
        -------
        str
            Code (aka shortcode)

        Examples
        --------
        2110901750722920960 -> B1LbfVPlwIA
        2278584739065882267 -> B-fKL9qpeab
        """
        return InstagramIdCodec.encode(media_pk)

    def media_pk_from_code(self, code: str) -> str:
        """
        Get Media PK from Code

        Parameters
        ----------
        code: str
            Code

        Returns
        -------
        int
            Full media id

        Examples
        --------
        B1LbfVPlwIA -> 2110901750722920960
        B-fKL9qpeab -> 2278584739065882267
        CCQQsCXjOaBfS3I2PpqsNkxElV9DXj61vzo5xs0 -> 2346448800803776129
        """
        return InstagramIdCodec.decode(code)

    def media_pk_from_url(self, url: str) -> str:
        """
        Get Media PK from URL

        Parameters
        ----------
        url: str
            URL of the media

        Returns
        -------
        int
            Media PK

        Examples
        --------
        https://instagram.com/p/B1LbfVPlwIA/ -> 2110901750722920960
        https://www.instagram.com/p/B-fKL9qpeab/?igshid=1xm76zkq7o1im -> 2278584739065882267
        """
        path = urlparse(url).path
        parts = [p for p in path.split("/") if p]
        return self.media_pk_from_code(parts.pop())

    def media_info_a1(self, media_pk: str, max_id: str = None) -> Media:
        """
        Get Media from PK by Public Web API

        Parameters
        ----------
        media_pk: str
            Unique identifier of the media
        max_id: str, optional
            Max ID, default value is None

        Returns
        -------
        Media
            An object of Media type
        """
        media_pk = self.media_pk(media_pk)
        shortcode = self.media_code_from_pk(media_pk)
        """Use Client.media_info
        """
        params = {"max_id": max_id} if max_id else None
        data = self.public_a1_request(
            "/p/{shortcode!s}/".format(**{"shortcode": shortcode}), params=params
        )
        if not data.get("shortcode_media"):
            raise MediaNotFound(media_pk=media_pk, **data)
        return extract_media_gql(data["shortcode_media"])

    def media_info_gql(self, media_pk: str) -> Media:
        """
        Get Media from PK by Public Graphql API

        Parameters
        ----------
        media_pk: str
            Unique identifier of the media

        Returns
        -------
        Media
            An object of Media type
        """
        media_pk = self.media_pk(media_pk)
        shortcode = self.media_code_from_pk(media_pk)
        """Use Client.media_info
        """
        variables = {
            "shortcode": shortcode,
            "child_comment_count": 3,
            "fetch_comment_count": 40,
            "parent_comment_count": 24,
            "has_threaded_comments": False,
        }
        data = self.public_graphql_request(
            variables, query_hash="477b65a610463740ccdb83135b2014db"
        )
        if not data.get("shortcode_media"):
            raise MediaNotFound(media_pk=media_pk, **data)
        if data["shortcode_media"]["location"] and self.authorization:
            data["shortcode_media"]["location"] = self.location_complete(
                extract_location(data["shortcode_media"]["location"])
            ).dict()
        return extract_media_gql(data["shortcode_media"])

    def media_info_v1(self, media_pk: str) -> Media:
        """
        Get Media from PK by Private Mobile API

        Parameters
        ----------
        media_pk: str
            Unique identifier of the media

        Returns
        -------
        Media
            An object of Media type
        """
        try:
            result = self.private_request(f"media/{media_pk}/info/")
        except ClientNotFoundError as e:
            raise MediaNotFound(e, media_pk=media_pk, **self.last_json)
        except ClientError as e:
            if "Media not found" in str(e):
                raise MediaNotFound(e, media_pk=media_pk, **self.last_json)
            raise e
        return extract_media_v1(result["items"].pop())

    def media_info(self, media_pk: str, use_cache: bool = True) -> Media:
        """
        Get Media Information from PK

        Parameters
        ----------
        media_pk: str
            Unique identifier of the media
        use_cache: bool, optional
            Whether or not to use information from cache, default value is True

        Returns
        -------
        Media
            An object of Media type
        """
        media_pk = self.media_pk(media_pk)
        if not use_cache or media_pk not in self._medias_cache:
            try:
                try:
                    media = self.media_info_gql(media_pk)
                except ClientLoginRequired as e:
                    if not self.inject_sessionid_to_public():
                        raise e
                    media = self.media_info_gql(media_pk)  # retry
            except Exception as e:
                if not isinstance(e, ClientError):
                    self.logger.exception(e)  # Register unknown error
                # Restricted Video: This video is not available in your country.
                # Or private account
                media = self.media_info_v1(media_pk)
            self._medias_cache[media_pk] = media
        return deepcopy(
            self._medias_cache[media_pk]
        )  # return copy of cache (dict changes protection)

    def media_delete(self, media_id: str) -> bool:
        """
        Delete media by Media ID

        Parameters
        ----------
        media_id: str
            Unique identifier of the media

        Returns
        -------
        bool
            A boolean value
        """
        assert self.user_id, "Login required"
        media_id = self.media_id(media_id)
        result = self.private_request(
            f"media/{media_id}/delete/", self.with_default_data({"media_id": media_id})
        )
        self._medias_cache.pop(self.media_pk(media_id), None)
        return result.get("did_delete")

    def media_edit(
        self,
        media_id: str,
        caption: str,
        title: str = "",
        usertags: List[Usertag] = [],
        location: Location = None,
    ) -> Dict:
        """
        Edit caption for media

        Parameters
        ----------
        media_id: str
            Unique identifier of the media
        caption: str
            Media caption
        title: str
            Title of the media
        usertags: List[Usertag], optional
            List of users to be tagged on this upload, default is empty list.
        location: Location, optional
            Location tag for this upload, default is None

        Returns
        -------
        Dict
            A dictionary of response from the call
        """
        assert self.user_id, "Login required"
        media_id = self.media_id(media_id)
        media = self.media_info(media_id)  # from cache
        usertags = [
            {"user_id": tag.user.pk, "position": [tag.x, tag.y]} for tag in usertags
        ]
        data = {
            "caption_text": caption,
            "container_module": "edit_media_info",
            "feed_position": "0",
            "location": self.location_build(location),
            "usertags": json.dumps({"in": usertags}),
            "is_carousel_bumped_post": "false",
        }
        if media.product_type == "igtv":
            if not title:
                try:
                    title, caption = caption.split("\n", 1)
                except ValueError:
                    title = caption[:75]
            data = {
                "caption_text": caption,
                "title": title,
                "igtv_ads_toggled_on": "0",
            }
        self._medias_cache.pop(self.media_pk(media_id), None)  # clean cache
        result = self.private_request(
            f"media/{media_id}/edit_media/",
            self.with_default_data(data),
        )
        return result

    def media_user(self, media_pk: str) -> UserShort:
        """
        Get author of the media

        Parameters
        ----------
        media_pk: str
            Unique identifier of the media

        Returns
        -------
        UserShort
            An object of UserShort
        """
        return self.media_info_v1(media_pk).user

    def media_oembed(self, url: str) -> Dict:
        """
        Return info about media and user from post URL

        Parameters
        ----------
        url: str
            URL for a media

        Returns
        -------
        Dict
            A dictionary of response from the call
        """
        return extract_media_oembed(self.private_request(f"oembed?url={url}"))

    def media_like(self, media_id: str, revert: bool = False) -> bool:
        """
        Like a media

        Parameters
        ----------
        media_id: str
            Unique identifier of a Media
        revert: bool, optional
            If liked, whether or not to unlike. Default is False

        Returns
        -------
        bool
            A boolean value
        """
        assert self.user_id, "Login required"
        media_id = self.media_pk(media_id)
        data = {
            "inventory_source": "media_or_ad",
            "media_id": media_id,
            "radio_type": "wifi-none",
            "is_carousel_bumped_post": "false",
            "container_module": "feed_timeline",
            "feed_position": str(random.randint(0, 6)),
        }
        name = "unlike" if revert else "like"
        result = self.private_request(
            f"media/{media_id}/{name}/", self.with_action_data(data)
        )
        return result["status"] == "ok"

    def media_unlike(self, media_id: str) -> bool:
        """
        Unlike a media

        Parameters
        ----------
        media_id: str
            Unique identifier of a Media

        Returns
        -------
        bool
            A boolean value
        """
        return self.media_like(media_id, revert=True)

    def user_medias_paginated_gql(
        self, user_id: str, amount: int = 0, sleep: int = 2, end_cursor=None
    ) -> Tuple[List[Media], str]:
        """
        Get a page of a user's media by Public Graphql API

        Parameters
        ----------
        user_id: str
        amount: int, optional
            Maximum number of media to return, default is 0 (all medias)
        sleep: int, optional
            Timeout between pages iterations, default is 2
        end_cursor: str, optional
            Cursor value to start at, obtained from previous call to this method
        Returns
        -------
        Tuple[List[Media], str]
            A tuple containing a list of medias and the next end_cursor value
        """
        amount = int(amount)
        user_id = int(user_id)
        medias = []
        variables = {
            "id": user_id,
            "first": 50 if not amount or amount > 50 else amount,
            # These are Instagram restrictions, you can only specify <= 50
        }
        variables["after"] = end_cursor
        data = self.public_graphql_request(
            variables, query_hash="e7e2f4da4b02303f74f0841279e52d76"
        )
        page_info = json_value(
            data, "user", "edge_owner_to_timeline_media", "page_info", default={}
        )
        edges = json_value(
            data, "user", "edge_owner_to_timeline_media", "edges", default=[]
        )
        for edge in edges:
            medias.append(edge["node"])
        end_cursor = page_info.get("end_cursor")
        if amount:
            medias = medias[:amount]
        return ([extract_media_gql(media) for media in medias], end_cursor)

    def user_medias_gql(
        self, user_id: str, amount: int = 0, sleep: int = 0
    ) -> List[Media]:
        """
        Get a user's media by Public Graphql API

        Parameters
        ----------
        user_id: str
        amount: int, optional
            Maximum number of media to return, default is 0 (all medias)
        sleep: int, optional
            Timeout between pages iterations, default is a random number between 1 and 3.

        Returns
        -------
        List[Media]
            A list of objects of Media
        """
        amount = int(amount)
        user_id = int(user_id)
        sleep = int(sleep)
        medias = []
        end_cursor = None
        variables = {
            "id": user_id,
            "first": 50 if not amount or amount > 50 else amount,
            # These are Instagram restrictions, you can only specify <= 50
        }
        while True:
            self.logger.info(f"user_medias_gql: {amount}, {end_cursor}")
            if end_cursor:
                variables["after"] = end_cursor

            if not sleep:
                sleep = random.randint(1, 3)

            medias_page, end_cursor = self.user_medias_paginated_gql(
                user_id, amount, sleep, end_cursor=end_cursor
            )
            medias.extend(medias_page)
            if not end_cursor or len(medias_page) == 0:
                break
            if amount and len(medias) >= amount:
                break
            time.sleep(sleep)
        if amount:
            medias = medias[:amount]
        return medias

    def user_videos_paginated_v1(
        self, user_id: str, amount: int = 50, end_cursor: str = ""
    ) -> Tuple[List[Media], str]:
        """
        Get a page of user's video by Private Mobile API

        Parameters
        ----------
        user_id: str
        amount: int, optional
            Maximum number of media to return, default is 0 (all medias)
        end_cursor: str, optional
            Cursor value to start at, obtained from previous call to this method

        Returns
        -------
        Tuple[List[Media], str]
            A tuple containing a list of medias and the next end_cursor value
        """
        items = []
        amount = int(amount)
        user_id = int(user_id)
        medias = []
        next_max_id = end_cursor
        try:
            resp = self.private_request(
                "igtv/channel/", params={"id": f"uservideo_{user_id}", "count": 50}
            )
            items = resp["items"]
        except PrivateError as e:
            raise e
        except Exception as e:
            self.logger.exception(e)
            return [], None
        medias.extend(items)
        next_max_id = self.last_json.get("next_max_id", "")
        if amount:
            medias = medias[:amount]
        return ([extract_media_v1(media) for media in medias], next_max_id)

    def user_videos_v1(self, user_id: str, amount: int = 0) -> List[Media]:
        """
        Get a user's video by Private Mobile API

        Parameters
        ----------
        user_id: str
        amount: int, optional
            Maximum number of media to return, default is 0 (all medias)

        Returns
        -------
        List[Media]
            A list of objects of Media
        """
        amount = int(amount)
        user_id = int(user_id)
        medias = []
        next_max_id = ""
        while True:
            try:
                medias_page, next_max_id = self.user_videos_paginated_v1(
                    user_id, amount, end_cursor=next_max_id
                )
            except PrivateError as e:
                raise e
            except Exception as e:
                self.logger.exception(e)
                break
            medias.extend(medias_page)
            if not next_max_id:
                break
            if amount and len(medias) >= amount:
                break
        if amount:
            medias = medias[:amount]
        return medias

    def user_medias_paginated_v1(
        self, user_id: str, amount: int = 33, end_cursor: str = ""
    ) -> Tuple[List[Media], str]:
        """
        Get a page of user's media by Private Mobile API

        Parameters
        ----------
        user_id: str
        amount: int, optional
            Maximum number of media to return, default is 0 (all medias)
        end_cursor: str, optional
            Cursor value to start at, obtained from previous call to this method

        Returns
        -------
        Tuple[List[Media], str]
            A tuple containing a list of medias and the next end_cursor value
        """
        amount = int(amount)
        user_id = int(user_id)
        medias = []
        next_max_id = end_cursor
        min_timestamp = None
        try:
            items = self.private_request(
                f"feed/user/{user_id}/",
                params={
                    "max_id": next_max_id,
                    "count": amount,
                    "min_timestamp": min_timestamp,
                    "rank_token": self.rank_token,
                    "ranked_content": "true",
                },
            )["items"]
        except PrivateError as e:
            raise e
        except Exception as e:
            self.logger.exception(e)
            return [], None
        medias.extend(items)
        next_max_id = self.last_json.get("next_max_id", "")
        if amount:
            medias = medias[:amount]
        return ([extract_media_v1(media) for media in medias], next_max_id)

    def user_medias_v1(self, user_id: str, amount: int = 0) -> List[Media]:
        """
        Get a user's media by Private Mobile API

        Parameters
        ----------
        user_id: str
        amount: int, optional
            Maximum number of media to return, default is 0 (all medias)

        Returns
        -------
        List[Media]
            A list of objects of Media
        """
        amount = int(amount)
        user_id = int(user_id)
        medias = []
        next_max_id = ""
        while True:
            try:
                medias_page, next_max_id = self.user_medias_paginated_v1(
                    user_id, amount, end_cursor=next_max_id
                )
            except PrivateError as e:
                raise e
            except Exception as e:
                self.logger.exception(e)
                break
            medias.extend(medias_page)
            if not next_max_id:
                break
            if amount and len(medias) >= amount:
                break
        if amount:
            medias = medias[:amount]
        return medias

    def user_medias_paginated(
        self, user_id: str, amount: int = 0, end_cursor: str = ""
    ) -> Tuple[List[Media], str]:
        """
        Get a page of user's media

        Parameters
        ----------
        user_id: str
        amount: int, optional
            Maximum number of media to return, default is 0 (all medias)
        end_cursor: str, optional
            Cursor value to start at, obtained from previous call to this method

        Returns
        -------
        Tuple[List[Media], str]
            A tuple containing a list of medias and the next end_cursor value
        """

        class EndCursorIsV1(Exception):
            pass

        try:
            if end_cursor and "_" in end_cursor:
                # end_cursor is a v1 next_max_id, so we need to use v1 API
                raise EndCursorIsV1
            try:
                medias, end_cursor = self.user_medias_paginated_gql(
                    user_id, amount, end_cursor=end_cursor
                )
            except ClientLoginRequired as e:
                if not self.inject_sessionid_to_public():
                    raise e
                medias, end_cursor = self.user_medias_paginated_gql(
                    user_id, amount, end_cursor=end_cursor
                )
        except PrivateError as e:
            raise e
        except Exception as e:
            if isinstance(e, EndCursorIsV1):
                pass
            elif not isinstance(e, ClientError):
                self.logger.exception(e)
            medias, end_cursor = self.user_medias_paginated_v1(
                user_id, amount, end_cursor=end_cursor
            )
        return medias, end_cursor

    def user_pinned_medias(self, user_id) -> List[Media]:
        """
        Get a pinned medias

        Parameters
        ----------
        user_id: str

        Returns
        -------
        List[Media]
            A list of objects of Media
        """
        default_nav = self.base_headers["X-IG-Nav-Chain"]
        self.base_headers[
            "X-IG-Nav-Chain"
        ] = "MainFeedFragment:feed_timeline:12:main_home::,UserDetailFragment:profile:13:button::"
        medias = self.private_request(
            f"feed/user/{user_id}/",
            params={
                "exclude_comment": "true",
                "only_fetch_first_carousel_media": "false",
            },
        )
        pinned_medias = []
        for media in medias["items"]:
            if media.get("timeline_pinned_user_ids") is not None:
                pinned_medias.append(extract_media_v1(media))
        self.base_headers["X-IG-Nav-Chain"] = default_nav
        return pinned_medias

    def user_medias(self, user_id: str, amount: int = 0, sleep: int = 0) -> List[Media]:
        """
        Get a user's media

        Parameters
        ----------
        user_id: str
        amount: int, optional
            Maximum number of media to return, default is 0 (all medias)
        sleep: int, optional
            Timeout between page iterations

        Returns
        -------
        List[Media]
            A list of objects of Media
        """
        amount = int(amount)
        user_id = int(user_id)
        sleep = int(sleep)
        try:
            try:
                medias = self.user_medias_gql(user_id, amount, sleep)
            except ClientLoginRequired as e:
                if not self.inject_sessionid_to_public():
                    raise e
                medias = self.user_medias_gql(user_id, amount, sleep)  # retry
        except PrivateError as e:
            raise e
        except Exception as e:
            if not isinstance(e, ClientError):
                self.logger.exception(e)
            # User may been private, attempt via Private API
            # (You can check is_private, but there may be other reasons,
            #  it is better to try through a Private API)
            medias = self.user_medias_v1(user_id, amount)
        return medias

    def user_clips_paginated_v1(
        self, user_id: str, amount: int = 50, end_cursor: str = ""
    ) -> Tuple[List[Media], str]:
        """
        Get a page of user's clip (reels) by Private Mobile API

        Parameters
        ----------
        user_id: str
        amount: int, optional
            Maximum number of media to return, default is 0 (all medias)
        end_cursor: str, optional
            Cursor value to start at, obtained from previous call to this method

        Returns
        -------
        Tuple[List[Media], str]
            A tuple containing a list of medias and the next end_cursor value
        """
        amount = int(amount)
        user_id = int(user_id)
        medias = []
        next_max_id = end_cursor
        try:
            items = self.private_request(
                "clips/user/",
                data={
                    "target_user_id": user_id,
                    "max_id": next_max_id,
                    "page_size": amount,  # default from app: 12
                    "include_feed_video": "true",
                },
            )["items"]
        except PrivateError as e:
            raise e
        except Exception as e:
            self.logger.exception(e)
            return [], None
        medias.extend(items)
        next_max_id = json_value(self.last_json, "paging_info", "max_id", default="")
        if amount:
            medias = medias[:amount]
        return ([extract_media_v1(media["media"]) for media in medias], next_max_id)

    def user_clips_v1(self, user_id: str, amount: int = 0) -> List[Media]:
        """
        Get a user's clip (reels) by Private Mobile API

        Parameters
        ----------
        user_id: str
        amount: int, optional
            Maximum number of media to return, default is 0 (all medias)

        Returns
        -------
        List[Media]
            A list of objects of Media
        """
        amount = int(amount)
        user_id = int(user_id)
        medias = []
        next_max_id = ""
        while True:
            try:
                medias_page, next_max_id = self.user_clips_paginated_v1(
                    user_id, end_cursor=next_max_id
                )
            except PrivateError as e:
                raise e
            except Exception as e:
                self.logger.exception(e)
                break
            medias.extend(medias_page)
            if not next_max_id:
                break
            if amount and len(medias) >= amount:
                break
        if amount:
            medias = medias[:amount]
        return medias

    def user_clips(self, user_id: str, amount: int = 0) -> List[Media]:
        """
        Get a user's clip (reels)

        Parameters
        ----------
        user_id: str
        amount: int, optional
            Maximum number of media to return, default is 0 (all medias)

        Returns
        -------
        List[Media]
            A list of objects of Media
        """
        amount = int(amount)
        user_id = int(user_id)
        return self.user_clips_v1(user_id, amount)

    def media_seen(self, media_ids: List[str], skipped_media_ids: List[str] = []):
        """
        Mark a media as seen

        Parameters
        ----------
        media_id: str

        Returns
        -------
        bool
            A boolean value
        """

        def gen(media_ids):
            result = {}
            for media_id in media_ids:
                media_pk, user_id = self.media_id(media_id).split("_")
                end = int(datetime.now().timestamp())
                begin = end - random.randint(100, 3000)
                result[f"{media_pk}_{user_id}_{user_id}"] = [f"{begin}_{end}"]
            return result

        data = {
            "container_module": "feed_timeline",
            "live_vods_skipped": {},
            "nuxes_skipped": {},
            "nuxes": {},
            "reels": gen(media_ids),
            "live_vods": {},
            "reel_media_skipped": gen(skipped_media_ids),
        }
        result = self.private_request(
            "/v2/media/seen/?reel=1&live_vod=0", self.with_default_data(data)
        )
        return result["status"] == "ok"

    def media_likers(self, media_id: str) -> List[UserShort]:
        """
        Get user's likers

        Parameters
        ----------
        media_pk: str

        Returns
        -------
        List[UserShort]
            List of objects of User type
        """
        media_id = self.media_id(media_id)
        result = self.private_request(f"media/{media_id}/likers/")
        return [extract_user_short(u) for u in result["users"]]

    def media_archive(self, media_id: str, revert: bool = False) -> bool:
        """
        Archive a media

        Parameters
        ----------
        media_id: str
            Unique identifier of a Media
        revert: bool, optional
            Flag for archive or unarchive. Default is False

        Returns
        -------
        bool
            A boolean value
        """
        media_id = self.media_id(media_id)
        name = "undo_only_me" if revert else "only_me"
        result = self.private_request(
            f"media/{media_id}/{name}/", self.with_action_data({"media_id": media_id})
        )
        return result["status"] == "ok"

    def media_unarchive(self, media_id: str) -> bool:
        """
        Unarchive a media

        Parameters
        ----------
        media_id: str
            Unique identifier of a Media

        Returns
        -------
        bool
            A boolean value
        """
        return self.media_archive(media_id, revert=True)

    def usertag_medias_gql(
        self, user_id: str, amount: int = 0, sleep: int = 2
    ) -> List[Media]:
        """
        Get medias where a user is tagged (by Public GraphQL API)

        Parameters
        ----------
        user_id: str
        amount: int, optional
            Maximum number of media to return, default is 0 (all medias)
        sleep: int, optional
            Timeout between pages iterations, default is 2

        Returns
        -------
        List[Media]
            A list of objects of Media
        """
        amount = int(amount)
        user_id = int(user_id)
        medias = []
        end_cursor = None
        variables = {
            "id": user_id,
            "first": 50 if not amount or amount > 50 else amount,
            # These are Instagram restrictions, you can only specify <= 50
        }
        while True:
            if end_cursor:
                variables["after"] = end_cursor
            data = self.public_graphql_request(
                variables, query_hash="be13233562af2d229b008d2976b998b5"
            )
            page_info = json_value(
                data, "user", "edge_user_to_photos_of_you", "page_info", default={}
            )
            edges = json_value(
                data, "user", "edge_user_to_photos_of_you", "edges", default=[]
            )
            for edge in edges:
                medias.append(edge["node"])
            end_cursor = page_info.get("end_cursor")
            if not page_info.get("has_next_page") or not end_cursor or len(edges) == 0:
                break
            if amount and len(medias) >= amount:
                break
            time.sleep(sleep)
        if amount:
            medias = medias[:amount]
        return [extract_media_gql(media) for media in medias]

    def usertag_medias_v1(self, user_id: str, amount: int = 0) -> List[Media]:
        """
        Get medias where a user is tagged (by Private Mobile API)

        Parameters
        ----------
        user_id: str
        amount: int, optional
            Maximum number of media to return, default is 0 (all medias)

        Returns
        -------
        List[Media]
            A list of objects of Media
        """
        amount = int(amount)
        user_id = int(user_id)
        medias = []
        next_max_id = ""
        while True:
            try:
                items = self.private_request(
                    f"usertags/{user_id}/feed/", params={"max_id": next_max_id}
                )["items"]
            except PrivateError as e:
                raise e
            except Exception as e:
                self.logger.exception(e)
                break
            medias.extend(items)
            if not self.last_json.get("more_available"):
                break
            if amount and len(medias) >= amount:
                break
            next_max_id = self.last_json.get("next_max_id", "")
        if amount:
            medias = medias[:amount]
        return [extract_media_v1(media) for media in medias]

    def usertag_medias(self, user_id: str, amount: int = 0) -> List[Media]:
        """
        Get medias where a user is tagged

        Parameters
        ----------
        user_id: str
        amount: int, optional
            Maximum number of media to return, default is 0 (all medias)

        Returns
        -------
        List[Media]
            A list of objects of Media
        """
        amount = int(amount)
        user_id = int(user_id)
        try:
            medias = self.usertag_medias_gql(user_id, amount)
        except ClientError:
            medias = self.usertag_medias_v1(user_id, amount)
        return medias

    def media_pin(self, media_pk: str, revert: bool = False):
        """
        Pin post to user profile

        Parameters
        ----------
        media_pk: str
        revert: bool, optional
            Unpin when True

        Returns
        -------
        bool
        A boolean value
        """
        data = self.with_action_data({"post_id": media_pk, "_uuid": self.uuid})
        name = "unpin" if revert else "pin"

        result = self.private_request(f"users/{name}_timeline_media/", data)
        return result["status"] == "ok"

    def media_unpin(self, media_pk):
        """
        Pin post to user profile

        Parameters
        ----------
        media_pk: str

        Returns
        -------
        bool
        A boolean value
        """
        return self.media_pin(media_pk, True)
