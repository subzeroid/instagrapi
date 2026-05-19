import json
import random
import time
from copy import deepcopy
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

from instagrapi.exceptions import (
    ClientError,
    ClientForbiddenError,
    ClientGraphqlError,
    ClientLoginRequired,
    ClientNotFoundError,
    ClientUnauthorizedError,
    MediaNotFound,
    PrivateError,
)
from instagrapi.extractors import (
    extract_direct_message,
    extract_location,
    extract_media_gql,
    extract_media_oembed,
    extract_media_v1,
    extract_user_short,
)
from instagrapi.mixins.graphql import GQL_STUFF
from instagrapi.types import Location, Media, Story, UserShort, Usertag
from instagrapi.utils.auth import generate_jazoest
from instagrapi.utils.ids import InstagramIdCodec
from instagrapi.utils.serialization import dumps, json_value

MEDIA_INFO_DOC_ID = "8845758582119845"
IG_PROFILE_TIMELINE_DOC_ID = "56030350814417327502004290437"


class MediaMixin:
    """
    Helpers for media
    """

    _medias_cache = {}  # pk -> object

    @staticmethod
    def _find_profile_timeline_payload(data):
        if not isinstance(data, dict):
            return None
        if "profile_grid_items" in data:
            return data
        for value in data.values():
            found = MediaMixin._find_profile_timeline_payload(value)
            if found:
                return found
        return None

    @staticmethod
    def _normalize_xdt_profile_media(media: Dict) -> Dict:
        media = deepcopy(media)
        user = media.get("user") or {}
        if "pk" not in user and user.get("id"):
            user["pk"] = user["id"]
        media["user"] = user
        media_id = str(media.get("id") or media.get("pk") or "")
        if "pk" not in media and media_id:
            media["pk"] = media_id.split("_", 1)[0]
        if media_id and "_" not in media_id and user.get("pk"):
            media["id"] = f"{media_id}_{user['pk']}"
        if "taken_at" not in media and "1ltaken_at" in media:
            media["taken_at"] = media["1ltaken_at"]
        return media

    def _user_medias_paginated_app_gql(self, user_id: str, amount: int = 0, end_cursor=None) -> Tuple[List[Media], str]:
        count = 50 if not amount or amount > 50 else amount
        variables = {
            "request_media_chunk": True,
            "skip_clips_captions_fields": False,
            "fetch_profile_grid_items": True,
            "exclude_comment": "false",
            "request_hints_chunk": False,
            "include_unseen_media_ids": False,
            "exclude_pinned_posts": False,
            "enable_carousel_media_count_in_deferred": True,
            "include_fb_mentioned_users": False,
            "include_attribution_ui_data": True,
            "include_profile_grid_rendering_option": False,
            "count": count,
            "initial_count_carousel_media": 5,
            "exclude_collaborative_posts": False,
            "include_is_photo_comments_composer_enabled_for_author": False,
            "include_associated_highlights": False,
            "include_attribution_ui_data_v2": True,
            "include_media_notes_fields": True,
            "include_eligible_insights_entrypoints": False,
            "include_accessibility_caption_for_carousel": True,
            "defer_maybe_non_essential_lightweight_fields": False,
            "num_previews_for_associated_highlights": 3,
            "include_videos_for_associated_highlights": False,
            "exclude_user": False,
            "defer_hints_chunk": False,
            "exclude_highlights": True,
            "include_ring_creator_fields": False,
            "include_timeline_ordered_edge": False,
            "user_id": str(user_id),
            "exclude_besties_content": True,
            "force_compute_user_tags": False,
            "enable_profile_fm_integration": False,
            "include_is_unseen_by_viewer": False,
        }
        if end_cursor:
            variables["max_id"] = end_cursor
        data = {
            "method": "post",
            "pretty": "false",
            "format": "json",
            "server_timestamps": "true",
            "locale": self.locale,
            "fb_api_req_friendly_name": "IGProfileTimelineQuery",
            "fb_api_caller_class": "graphservice",
            "client_doc_id": IG_PROFILE_TIMELINE_DOC_ID,
            "variables": json.dumps(variables, separators=(",", ":")),
        }
        response = self.private_graphql_request(
            data,
            headers={"X-FB-Friendly-Name": "IGProfileTimelineQuery"},
        )
        timeline = self._find_profile_timeline_payload(response.get("data", response))
        if not timeline:
            raise ClientGraphqlError("Missing profile timeline payload in IGProfileTimelineQuery response")
        medias = []
        for item in timeline.get("profile_grid_items") or []:
            media = item.get("media") if isinstance(item, dict) else None
            if not media:
                continue
            medias.append(extract_media_v1(self._normalize_xdt_profile_media(media)))
        end_cursor = None
        if timeline.get("more_available"):
            end_cursor = timeline.get("next_max_id") or timeline.get("profile_grid_items_cursor")
        if amount:
            medias = medias[:amount]
        return medias, end_cursor

    def _user_medias_paginated_public_gql(
        self, user_id: str, amount: int = 0, end_cursor=None
    ) -> Tuple[List[Media], str]:
        amount = int(amount)
        user_id = int(user_id)
        medias = []
        variables = {
            "id": user_id,
            "first": 50 if not amount or amount > 50 else amount,
        }
        variables["after"] = end_cursor
        data = self.public_graphql_request(variables, query_hash="e7e2f4da4b02303f74f0841279e52d76")
        page_info = json_value(data, "user", "edge_owner_to_timeline_media", "page_info", default={})
        edges = json_value(data, "user", "edge_owner_to_timeline_media", "edges", default=[])
        for edge in edges:
            medias.append(edge["node"])
        end_cursor = page_info.get("end_cursor")
        if amount:
            medias = medias[:amount]
        return ([extract_media_gql(media) for media in medias], end_cursor)

    def _extract_configured_media(self, configured):
        media = None
        if isinstance(configured, dict):
            media = configured.get("media")
        if media is None:
            media = self.last_json.get("media") if isinstance(self.last_json, dict) else None
        if media is None:
            return None
        return extract_media_v1(media)

    def _extract_configured_media_or_raise(self, configured, exception_cls, context: str):
        media = self._extract_configured_media(configured)
        if media is None:
            raise exception_cls(
                f"{context} configure succeeded without media payload",
                response=self.last_response,
                **(self.last_json if isinstance(self.last_json, dict) else {}),
            )
        return media

    def _current_story_ids(self, amount: int = 20):
        user_id = self.user_id or getattr(self, "_user_id", None)
        if not user_id:
            return None
        try:
            return {str(story.id) for story in self.user_stories(user_id, amount=amount)}
        except Exception as e:
            self.logger.debug("Unable to read current stories before upload: %s", e)
            return None

    def _new_story_after_upload(self, previous_story_ids, attempts: int = 5, delay: int = 3, amount: int = 20):
        user_id = self.user_id or getattr(self, "_user_id", None)
        if previous_story_ids is None or not user_id:
            return None
        for attempt in range(attempts):
            try:
                stories = self.user_stories(user_id, amount=amount)
            except Exception as e:
                self.logger.debug("Unable to read uploaded story on attempt %s: %s", attempt, e)
            else:
                for story in stories:
                    if str(story.id) not in previous_story_ids:
                        return story
            if attempt < attempts - 1:
                time.sleep(delay)
        return None

    def _extract_configured_story_or_recent(
        self,
        configured,
        exception_cls,
        context: str,
        previous_story_ids,
        story_kwargs,
    ):
        media = self._extract_configured_media(configured)
        if media is not None:
            return Story(**story_kwargs, **media.model_dump())
        story = self._new_story_after_upload(previous_story_ids)
        if story is not None:
            return story.model_copy(update=story_kwargs)
        raise exception_cls(
            f"{context} configure succeeded without media payload and uploaded story was not visible",
            response=self.last_response,
            **(self.last_json if isinstance(self.last_json, dict) else {}),
        )

    def _extract_configured_direct_message_or_raise(self, configured, exception_cls, context: str):
        message_metadata = []
        if isinstance(configured, dict):
            message_metadata = configured.get("message_metadata") or []
        if not message_metadata and isinstance(self.last_json, dict):
            message_metadata = self.last_json.get("message_metadata") or []
        if not message_metadata:
            raise exception_cls(
                f"{context} configure succeeded without message_metadata payload",
                response=self.last_response,
                **(self.last_json if isinstance(self.last_json, dict) else {}),
            )
        return extract_direct_message(message_metadata[0])

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
            assert media_id.isdigit(), "media_id must been contain digits, now %s" % media_id
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
        return str(InstagramIdCodec.decode(code[:11]))

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
        if parts[:2] == ["share", "p"] and len(parts) >= 3:
            response = self.public.get(
                url,
                proxies=self.public.proxies,
                timeout=self.request_timeout,
                allow_redirects=False,
            )
            location = response.headers.get("Location") or response.headers.get("location")
            if location:
                return self.media_pk_from_url(location)
        return self.media_pk_from_code(parts.pop())

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
        try:
            data = self.public_graphql_request(variables, query_hash="477b65a610463740ccdb83135b2014db")
        except (
            ClientForbiddenError,
            ClientGraphqlError,
            ClientLoginRequired,
            ClientNotFoundError,
            ClientUnauthorizedError,
        ):
            data = self.public_doc_id_graphql_request(
                MEDIA_INFO_DOC_ID,
                {"shortcode": shortcode},
                referer=f"https://www.instagram.com/p/{shortcode}/",
            )
            media = data.get("xdt_shortcode_media") or data.get("shortcode_media")
            if not media:
                raise MediaNotFound(media_pk=media_pk, **data)
            return extract_media_gql(media)
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

    def media_info_v2(self, media_id: str) -> Media:
        """
        Get media via the discover-style metadata endpoint.

        ``GET /discover/media_metadata/?media_id={pk}`` — alternative
        source for media info that returns a ``media_or_ad`` payload.
        Useful as a fallback when ``media_info_v1`` fails on certain
        ad-tagged or sponsored media. Unlike ``media_info_v1``, this
        endpoint expects only the numeric pk (the ``_userid`` suffix
        is stripped automatically if you pass a full media_id).

        Parameters
        ----------
        media_id: str
            Media pk or full media_id (``pk_userid``).

        Returns
        -------
        Media
            Extracted via :func:`extract_media_v1`.

        Raises
        ------
        MediaNotFound
            ``media_or_ad`` was missing from the response.
        """
        media_id = str(media_id).split("_")[0]
        result = self.private_request("discover/media_metadata/", params={"media_id": media_id})
        media = result.get("media_or_ad")
        if not media:
            raise MediaNotFound(media_id=media_id, **(self.last_json or {}))
        return extract_media_v1(media)

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
        return deepcopy(self._medias_cache[media_pk])  # return copy of cache (dict changes protection)

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
        result = self.private_request(f"media/{media_id}/delete/", self.with_default_data({"media_id": media_id}))
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
        usertags = [{"user_id": tag.user.pk, "position": [tag.x, tag.y]} for tag in usertags]
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
        media_id = str(media_id)
        data = {
            "inventory_source": "media_or_ad",
            "media_id": media_id,
            "_uid": str(self.user_id),
            "radio_type": "wifi-none",
            "delivery_class": "organic",
            "tap_source": "button",
            "is_2m_enabled": "false",
            "is_from_swipe": "false",
            "is_carousel_bumped_post": "false",
            "floating_context_items": "[]",
            "media_pct_watched": "0",
            "container_module": "feed_timeline",
            "feed_position": str(random.randint(0, 6)),
        }
        name = "unlike" if revert else "like"
        result = self.private_request(f"media/{media_id}/{name}/", self.with_action_data(data))
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

    def media_note_create(
        self,
        media_id: str,
        text: str = "",
        audience: int = 7,
        note_style: int = 13,
        extra_data: Optional[Dict] = None,
    ) -> Dict:
        """
        Create a note attached to a media item.

        This is separate from Direct inbox Notes created by
        :meth:`create_note`; it mirrors the Android app's
        ``media/create_note/v2/`` flow for notes attached to posts/Reels.

        Parameters
        ----------
        media_id: str
            Full media id, for example ``"3884795301060104481_52448022913"``.
        text: str, optional
            Note text.
        audience: int, optional
            Raw media-note audience value. The Android app sends ``7``.
        note_style: int, optional
            Raw media-note style value. The Android app sends ``13``.
        extra_data: Dict, optional
            Additional app-surface fields such as ``tracking_token``,
            ``ranking_info_token`` or ``nav_chain`` when the caller has them.

        Returns
        -------
        Dict
            Raw created note response.
        """
        assert self.user_id, "Login required"
        data = {
            "inventory_source": "recommended_clips_chaining_model",
            "media_client_position": "0",
            "media_id": str(media_id),
            "note_style": str(note_style),
            "carousel_index": "-1",
            "text": text,
            "_uuid": self.uuid,
            "audience": str(audience),
            "event_source": "ufi",
            "container_module": "clips_viewer_clips_tab",
        }
        if extra_data:
            data.update(extra_data)
        return self.private_request("media/create_note/v2/", data=data, with_signature=False)

    def media_note_delete(self, note_id: str, extra_data: Optional[Dict] = None) -> bool:
        """
        Delete a note attached to a media item.

        Parameters
        ----------
        note_id: str
            ID of the media note to delete.
        extra_data: Dict, optional
            Additional app-surface fields such as ``tracking_token``,
            ``ranking_info_token`` or ``nav_chain`` when the caller has them.

        Returns
        -------
        bool
            A boolean value.
        """
        assert self.user_id, "Login required"
        data = {
            "inventory_source": "recommended_clips_chaining_model",
            "carousel_index": "-1",
            "_uuid": self.uuid,
            "event_source": "ufi",
            "container_module": "clips_viewer_clips_tab",
            "note_id": str(note_id),
        }
        if extra_data:
            data.update(extra_data)
        result = self.private_request("media/delete_note/", data=data, with_signature=False)
        return result.get("status", "") == "ok"

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
        try:
            return self._user_medias_paginated_app_gql(user_id, amount, end_cursor=end_cursor)
        except ClientError:
            return self._user_medias_paginated_public_gql(user_id, amount, end_cursor=end_cursor)

    def user_medias_chunk_gql(
        self, user_id: str, sleep: int = 2, end_cursor=None, amount: int = 0
    ) -> Tuple[List[Media], str]:
        """
        Compatibility alias for aiograpi's original chunk naming.
        """
        return self.user_medias_paginated_gql(user_id, amount=amount, sleep=sleep, end_cursor=end_cursor)

    def user_medias_gql(self, user_id: str, amount: int = 0, sleep: int = 0) -> List[Media]:
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

            medias_page, end_cursor = self.user_medias_paginated_gql(user_id, amount, sleep, end_cursor=end_cursor)
            medias.extend(medias_page)
            if not end_cursor or len(medias_page) == 0:
                break
            if amount and len(medias) >= amount:
                break
            time.sleep(sleep)
        if amount:
            medias = medias[:amount]
        return medias

    def user_videos_paginated_v1(self, user_id: str, amount: int = 50, end_cursor: str = "") -> Tuple[List[Media], str]:
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
            resp = self.private_request("igtv/channel/", params={"id": f"uservideo_{user_id}", "count": 50})
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

    def user_videos_chunk_v1(self, user_id: str, end_cursor: str = "") -> Tuple[List[Media], str]:
        """
        Compatibility alias for aiograpi's original chunk naming.
        """
        return self.user_videos_paginated_v1(user_id, amount=50, end_cursor=end_cursor)

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
                medias_page, next_max_id = self.user_videos_paginated_v1(user_id, amount, end_cursor=next_max_id)
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

    def user_medias_paginated_v1(self, user_id: str, amount: int = 33, end_cursor: str = "") -> Tuple[List[Media], str]:
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

    def user_medias_chunk_v1(self, user_id: str, end_cursor: str = "") -> Tuple[List[Media], str]:
        """
        Compatibility alias for aiograpi's original chunk naming.
        """
        return self.user_medias_paginated_v1(user_id, amount=33, end_cursor=end_cursor)

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
                medias_page, next_max_id = self.user_medias_paginated_v1(user_id, amount, end_cursor=next_max_id)
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

    def user_medias_paginated(self, user_id: str, amount: int = 0, end_cursor: str = "") -> Tuple[List[Media], str]:
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
                medias, end_cursor = self.user_medias_paginated_gql(user_id, amount, end_cursor=end_cursor)
            except ClientLoginRequired as e:
                if not self.inject_sessionid_to_public():
                    raise e
                medias, end_cursor = self.user_medias_paginated_gql(user_id, amount, end_cursor=end_cursor)
        except PrivateError as e:
            raise e
        except Exception as e:
            if isinstance(e, EndCursorIsV1):
                pass
            elif not isinstance(e, ClientError):
                self.logger.exception(e)
            medias, end_cursor = self.user_medias_paginated_v1(user_id, amount, end_cursor=end_cursor)
        return medias, end_cursor

    def user_medias_chunk(self, user_id: str, end_cursor: str = "") -> Tuple[List[Media], str]:
        """
        Compatibility alias for aiograpi's original chunk naming.
        """
        return self.user_medias_paginated(user_id, amount=0, end_cursor=end_cursor)

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
        self.base_headers["X-IG-Nav-Chain"] = (
            "MainFeedFragment:feed_timeline:12:main_home::,UserDetailFragment:profile:13:button::"
        )
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

    def user_clips_paginated_v1(self, user_id: str, amount: int = 50, end_cursor: str = "") -> Tuple[List[Media], str]:
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

    def user_clips_chunk_v1(self, user_id: str, end_cursor: str = "") -> Tuple[List[Media], str]:
        """
        Compatibility alias for aiograpi's original chunk naming.
        """
        return self.user_clips_paginated_v1(user_id, amount=50, end_cursor=end_cursor)

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
                medias_page, next_max_id = self.user_clips_paginated_v1(user_id, end_cursor=next_max_id)
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
        result = self.private_request("/v2/media/seen/?reel=1&live_vod=0", self.with_default_data(data))
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

    def media_likers_gql_chunk(self, media_pk: str, end_cursor: str = "") -> List[dict]:
        """
        Get media likers through the web GraphQL doc_id endpoint.
        """
        data = {
            "variables": dumps({"id": media_pk}),
            "doc_id": "24452425501069647",
            "fb_dtsg": self.fb_dtsg,
            "jazoest": generate_jazoest(self.phone_id),
            **GQL_STUFF,
        }
        resp = self.graphql_request(data=data)
        return resp.get("data", {}).get("xdt_api__v1__likes__media_id__likers", {}).get("users", [])

    def media_likers_gql(self, media_pk: str, amount: int = 0) -> List[dict]:
        """
        Get media likers through the web GraphQL doc_id endpoint.
        """
        likers = self.media_likers_gql_chunk(self.media_pk(media_pk))
        if amount:
            likers = likers[:amount]
        return likers

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
        result = self.private_request(f"media/{media_id}/{name}/", self.with_action_data({"media_id": media_id}))
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

    def archive_medias_paginated_v1(self, amount: int = 0, end_cursor: str = "") -> Tuple[List[Media], str]:
        """
        Get a page of your archived medias by Private Mobile API

        Parameters
        ----------
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
        params = {"max_id": end_cursor} if end_cursor else {}
        result = self.private_request("feed/only_me_feed/", params=params)
        items = result.get("items", [])
        if amount:
            items = items[:amount]
        medias = [extract_media_v1(item.get("media", item)) for item in items]
        return medias, result.get("max_id") or ""

    def archive_medias_v1(self, amount: int = 0) -> List[Media]:
        """
        Get your archived medias by Private Mobile API

        Parameters
        ----------
        amount: int, optional
            Maximum number of media to return, default is 0 (all medias)

        Returns
        -------
        List[Media]
            A list of objects of Media
        """
        amount = int(amount)
        medias = []
        next_max_id = ""
        while True:
            medias_page, next_max_id = self.archive_medias_paginated_v1(amount=amount, end_cursor=next_max_id)
            medias.extend(medias_page)
            if not next_max_id:
                break
            if amount and len(medias) >= amount:
                break
        if amount:
            medias = medias[:amount]
        return medias

    def archive_medias(self, amount: int = 0) -> List[Media]:
        """
        Get your archived medias

        Parameters
        ----------
        amount: int, optional
            Maximum number of media to return, default is 0 (all medias)

        Returns
        -------
        List[Media]
            A list of objects of Media
        """
        return self.archive_medias_v1(amount)

    def usertag_medias_gql(self, user_id: str, amount: int = 0, sleep: int = 2) -> List[Media]:
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
            data = self.public_graphql_request(variables, query_hash="be13233562af2d229b008d2976b998b5")
            page_info = json_value(data, "user", "edge_user_to_photos_of_you", "page_info", default={})
            edges = json_value(data, "user", "edge_user_to_photos_of_you", "edges", default=[])
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

    def usertag_medias_paginated_gql(
        self, user_id: str, amount: int = 0, sleep: int = 2, end_cursor=None
    ) -> Tuple[List[Media], str]:
        """
        Get a page of medias where a user is tagged (by Public GraphQL API)

        Parameters
        ----------
        user_id: str
        amount: int, optional
            Maximum number of media to return, default is 0 (all medias)
        sleep: int, optional
            Kept for API symmetry with usertag_medias_gql; not used for a single page fetch.
        end_cursor: str, optional
            Cursor value to start at, obtained from previous call to this method

        Returns
        -------
        Tuple[List[Media], str]
            A tuple containing a list of medias and the next end_cursor value
        """
        amount = int(amount)
        user_id = int(user_id)
        variables = {
            "id": user_id,
            "first": 50 if not amount or amount > 50 else amount,
        }
        if end_cursor:
            variables["after"] = end_cursor
        data = self.public_graphql_request(variables, query_hash="be13233562af2d229b008d2976b998b5")
        page_info = json_value(data, "user", "edge_user_to_photos_of_you", "page_info", default={})
        edges = json_value(data, "user", "edge_user_to_photos_of_you", "edges", default=[])
        medias = [edge["node"] for edge in edges]
        if amount:
            medias = medias[:amount]
        return [extract_media_gql(media) for media in medias], page_info.get("end_cursor")

    def usertag_medias_paginated_v1(
        self, user_id: str, amount: int = 0, end_cursor: str = ""
    ) -> Tuple[List[Media], str]:
        """
        Get a page of medias where a user is tagged (by Private Mobile API)

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
        result = self.private_request(f"usertags/{user_id}/feed/", params={"max_id": end_cursor})
        items = result.get("items", [])
        if amount:
            items = items[:amount]
        return [extract_media_v1(media) for media in items], result.get("next_max_id") or ""

    def usertag_medias_v1_chunk(self, user_id: str, max_id: str = "") -> Tuple[List[Media], str]:
        """
        Compatibility alias for aiograpi's original chunk naming.
        """
        return self.usertag_medias_paginated_v1(user_id, amount=0, end_cursor=max_id)

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
                items = self.private_request(f"usertags/{user_id}/feed/", params={"max_id": next_max_id})["items"]
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

    def usertag_medias_paginated(self, user_id: str, amount: int = 0, end_cursor: str = "") -> Tuple[List[Media], str]:
        """
        Get a page of medias where a user is tagged

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
        try:
            medias, end_cursor = self.usertag_medias_paginated_gql(user_id, amount, end_cursor=end_cursor)
        except ClientError:
            medias, end_cursor = self.usertag_medias_paginated_v1(user_id, amount, end_cursor=end_cursor)
        return medias, end_cursor

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

    def media_configure_to_cutout_sticker(
        self,
        upload_id: str,
        source_type: str = "library",
        manual_box: List[float] = None,
        use_ai_detection: bool = False,
        extra_data: Dict[str, str] = None,
    ) -> Media:
        """
        Configure an uploaded photo as a Cutout Sticker.

        Parameters
        ----------
        upload_id: str
            Upload ID from `photo_rupload`
        source_type: str, optional
            Source type (default "library")
        manual_box: List[float], optional
            Bounding box [x, y, w, h] normalized (0.0 to 1.0).
            Pass [0.0, 0.0, 1.0, 1.0] to select the full image (Bypass AI).
        use_ai_detection: bool, optional
            If True, asks Instagram to detect the subject (Server-side AI).
        extra_data: Dict[str, str], optional
            Dict of extra parameters

        Returns
        -------
        Media
            An object of Media type (The created sticker)
        """
        url = "media/configure_to_cutout_sticker/"
        data = {
            "upload_id": upload_id,
            "source_type": source_type,
            "sticker_type": "cutout_sticker",
            "_uuid": self.uuid,
            "_uid": self.user_id,
        }
        if extra_data:
            data.update(extra_data)

        if manual_box:
            data["cutout_sticker_data"] = json.dumps({"manual_mask": {"box": manual_box}})
        elif use_ai_detection:
            data["detect_subject"] = "true"

        result = self.private_request(url, data)
        return self._extract_configured_media_or_raise(
            result,
            PrivateError,
            "Cutout sticker upload",
        )

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

    def media_template_v1(self, media_id: str):
        """
        Fetch a clip template (remix-from-template) for a clip media.
        """
        data = {
            "should_show_friends_media_at_top": "false",
            "template_clips_media_id": media_id,
            "_uuid": self.uuid,
        }
        return self.private_request("clips/template/", data=data)

    def media_create_livestream(self, title="Instagram Live"):
        """
        Create a new live broadcast.

        Parameters
        ----------
        title : str
            The title of the live broadcast.

        Returns
        -------
        dict
            Information about the streaming server and the stream key.
        """
        data = {
            "_uuid": self.uuid,
            "_uid": self.user_id,
            "preview_height": 1920,
            "preview_width": 1080,
            "broadcast_message": title,
            "broadcast_type": "RTMP",
            "internal_only": 0,
            "_csrftoken": self.token,
        }
        try:
            response = self.private_request("live/create/", data=data)
            broadcast_id = response["broadcast_id"]
            upload_url = response["upload_url"].split(str(broadcast_id))
            if len(upload_url) >= 2:
                stream_server = upload_url[0]
                stream_key = f"{broadcast_id}{upload_url[1]}"
                return {
                    "broadcast_id": broadcast_id,
                    "stream_server": stream_server,
                    "stream_key": stream_key,
                }
        except Exception as e:
            self.logger.error(f"Error creating live broadcast: {e}")
            raise

    def media_start_livestream(self, broadcast_id):
        """
        Start a live broadcast.

        Parameters
        ----------
        broadcast_id : str
            The ID of the live broadcast.

        Returns
        -------
        bool
            True if the broadcast started successfully, False otherwise.
        """
        data = {
            "_uuid": self.uuid,
            "_uid": self.user_id,
            "should_send_notifications": 1,
            "_csrftoken": self.token,
        }
        try:
            response = self.private_request(f"live/{broadcast_id}/start/", data=data)
            return response.get("status") == "ok"
        except Exception as e:
            self.logger.error(f"Error starting live broadcast: {e}")
            return False

    def media_end_livestream(self, broadcast_id):
        """
        End a live broadcast.

        Parameters
        ----------
        broadcast_id : str
            The ID of the live broadcast.

        Returns
        -------
        bool
            True if the broadcast ended successfully, False otherwise.
        """
        data = {
            "_uuid": self.uuid,
            "_uid": self.user_id,
            "_csrftoken": self.token,
        }
        try:
            response = self.private_request(f"live/{broadcast_id}/end_broadcast/", data=data)
            return response.get("status") == "ok"
        except Exception as e:
            self.logger.error(f"Error ending live broadcast: {e}")
            return False

    def media_get_livestream_info(self, broadcast_id):
        """
        Retrieve information about the live broadcast.

        Parameters
        ----------
        broadcast_id : str
            The ID of the live broadcast.

        Returns
        -------
        dict
            Information about the live broadcast.
        """
        try:
            response = self.private_request(f"live/{broadcast_id}/info/")
            return response
        except Exception as e:
            self.logger.error(f"Error retrieving live info: {e}")
            raise

    def media_get_livestream_comments(self, broadcast_id):
        """
        Retrieve comments from the live broadcast.

        Parameters
        ----------
        broadcast_id : str
            The ID of the live broadcast.

        Returns
        -------
        list
            A list of comments.
        """
        try:
            response = self.private_request(f"live/{broadcast_id}/get_comment/")
            if "comments" in response:
                return [{"username": c["user"]["username"], "text": c["text"]} for c in response["comments"]]
            return []
        except Exception as e:
            self.logger.error(f"Error retrieving live comments: {e}")
            raise

    def media_get_livestream_viewers(self, broadcast_id):
        """
        Retrieve the list of viewers of the live broadcast.

        Parameters
        ----------
        broadcast_id : str
            The ID of the live broadcast.

        Returns
        -------
        list
            A list of viewers.
        """
        try:
            response = self.private_request(f"live/{broadcast_id}/get_viewer_list/")
            return [{"username": user["username"], "pk": user["pk"]} for user in response.get("users", [])]
        except Exception as e:
            self.logger.error(f"Error retrieving live viewers: {e}")
            raise
