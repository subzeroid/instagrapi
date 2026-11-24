import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union

from pydantic import TypeAdapter, ValidationError

from instagrapi.exceptions import ClientGraphqlError, PrivateError
from instagrapi.extractors import (
    extract_hashtag_v1,
    extract_location,
    extract_media_v1,
    extract_track,
    extract_user_short,
)
from instagrapi.types import Hashtag, Location, Media, Track, UserShort

_TOP_SERP_USERTAG_POSITION = TypeAdapter(tuple[float, float])


@dataclass(frozen=True, repr=False)
class _TopSerpCursor:
    query: str
    search_ids: Tuple[str, str, str]
    after: str
    seen_media: frozenset[str]
    seen_cursors: frozenset[str]


class FbSearchMixin:
    def _validate_fbsearch_media_grid(self, result: object) -> dict:
        response = getattr(self, "last_response", None)
        if not isinstance(result, dict):
            raise PrivateError("Malformed fbsearch/top_serp response", response=response)
        media_grid = result.get("media_grid")
        if media_grid is None:
            raise PrivateError("Missing media_grid in fbsearch/top_serp response", response=response)
        if not isinstance(media_grid, dict):
            raise PrivateError("Malformed media_grid in fbsearch/top_serp response", response=response)
        sections = media_grid.get("sections")
        if sections is not None and not isinstance(sections, list):
            raise PrivateError("Malformed media_grid sections in fbsearch/top_serp response", response=response)
        return media_grid

    def _fbsearch_media_grid_nodes(self, media_grid: dict):
        def _yield_media_items(items):
            if not isinstance(items, list):
                return
            for item in items:
                media = item.get("media") if isinstance(item, dict) else None
                if isinstance(media, dict):
                    yield media

        for section in media_grid.get("sections") or []:
            if not isinstance(section, dict):
                continue
            layout_content = section.get("layout_content") or {}
            if not isinstance(layout_content, dict):
                continue
            one_by_two_item = layout_content.get("one_by_two_item") or {}
            if isinstance(one_by_two_item, dict):
                media = one_by_two_item.get("media")
                if isinstance(media, dict):
                    yield media
                clips = one_by_two_item.get("clips") or {}
                if isinstance(clips, dict):
                    yield from _yield_media_items(clips.get("items"))
            for key in ("fill_items", "medias"):
                yield from _yield_media_items(layout_content.get(key))

    def fbsearch_places(self, query: str, lat: float = 40.74, lng: float = -73.94) -> List[Location]:
        params = {
            "search_surface": "places_search_page",
            "timezone_offset": self.timezone_offset,
            "lat": lat,
            "lng": lng,
            "count": 30,
            "query": query,
        }
        result = self.private_request("fbsearch/places/", params=params)
        locations = []
        for item in result["items"]:
            locations.append(extract_location(item["location"]))
        return locations

    def web_search_users(self, query: str) -> List[UserShort]:
        """Return account results from Instagram's web search on a saved session.

        The query must contain at least one non-whitespace character.
        """
        if not query.strip():
            raise ValueError("query must not be blank")
        data = self.public_doc_id_graphql_request(
            "27706427925724183",
            {
                "data": {
                    "context": "blended",
                    "include_reel": "true",
                    "query": query,
                    "rank_token": "",  # nosec B105 - This initial search ranking field is empty.
                    "search_session_id": self.generate_uuid(),
                    "search_surface": "web_top_search",
                },
                "hasQuery": True,
            },
            referer="https://www.instagram.com/explore/",
            headers={"X-FB-Friendly-Name": "PolarisSearchBoxRefetchableQuery"},
            url=self.GRAPHQL_PUBLIC_WEB_API_URL,
            include_lsd=True,
            include_fb_dtsg=True,
        )
        connection = data.get("xdt_api__v1__fbsearch__topsearch_connection") if isinstance(data, dict) else None
        entries = connection.get("users") if isinstance(connection, dict) else None
        error = "Malformed web account search response"
        if not isinstance(entries, list):
            raise ClientGraphqlError(error)
        users: List[UserShort] = []
        for entry in entries:
            user = entry.get("user") if isinstance(entry, dict) else None
            if not isinstance(user, dict):
                raise ClientGraphqlError(error)
            pk = str(user.get("pk") or user.get("id") or "")
            if not pk.isdecimal():
                raise ClientGraphqlError(error)
            try:
                users.append(extract_user_short(deepcopy(dict(user, id=pk))))
            except (TypeError, ValueError) as exc:
                raise ClientGraphqlError(error) from exc
        return users

    def web_search_topsearch(self, query: str) -> dict:
        params = {
            "search_surface": "web_top_search",
            "context": "blended",
            "include_reel": "true",
            "query": query,
        }
        return self.private_request("web/search/topsearch/", params=params)

    def fbsearch_topsearch_flat(self, query: str) -> List[dict]:
        params = {
            "search_surface": "top_search_page",
            "context": "blended",
            "timezone_offset": self.timezone_offset,
            "count": 30,
            "query": query,
        }
        result = self.private_request("fbsearch/topsearch_flat/", params=params)
        return result["list"]

    def search_users(self, query: str) -> List[UserShort]:
        params = {
            "search_surface": "user_search_page",
            "timezone_offset": self.timezone_offset,
            "count": 30,
            "q": query,
        }
        result = self.private_request("users/search/", params=params)
        return [extract_user_short(item) for item in result["users"]]

    def search_music(self, query: str) -> List[Track]:
        params = {
            "query": query,
            "browse_session_id": self.generate_uuid(),
        }
        result = self.private_request("music/audio_global_search/", params=params)
        return [extract_track(item["track"]) for item in result["items"] if item.get("track")]

    def search_hashtags(self, query: str) -> List[Hashtag]:
        params = {
            "search_surface": "hashtag_search_page",
            "timezone_offset": self.timezone_offset,
            "count": 30,
            "q": query,
        }
        result = self.private_request("tags/search/", params=params)
        return [extract_hashtag_v1(ht) for ht in result["results"]]

    def fbsearch_suggested_profiles(self, user_id: str) -> List[UserShort]:
        params = {
            "target_user_id": user_id,
            "include_friendship_status": "true",
        }
        result = self.private_request("fbsearch/accounts_recs/", params=params)
        return [extract_user_short(item) for item in result["users"]]

    def web_search_topsearch_hashtags(self, query: str) -> List[Hashtag]:
        result = self.web_search_topsearch(query)
        return [extract_hashtag_v1(item["hashtag"]) for item in result.get("hashtags", [])]

    def fbsearch_item(
        self,
        item_id: str,
        search_surface: str,
        query: str,
        timezone_offset: int = 0,
        count: int = 30,
        reels_page_index: int = None,
        has_more_reels: str = None,
        reels_max_id: str = None,
        next_max_id: str = None,
        rank_token: str = None,
        page_index: int = None,
        page_token: str = None,
        paging_token: str = None,
    ) -> dict:
        params = {
            "search_surface": search_surface,
            "query": query,
        }
        if timezone_offset:
            params["timezone_offset"] = timezone_offset
        if count:
            params["count"] = count
        if reels_page_index is not None:
            params["reels_page_index"] = reels_page_index
        if has_more_reels:
            params["has_more_reels"] = has_more_reels
        if reels_max_id:
            params["reels_max_id"] = reels_max_id
        if next_max_id:
            params["next_max_id"] = next_max_id
        if rank_token:
            params["rank_token"] = rank_token
        if page_index is not None:
            params["page_index"] = page_index
        if page_token:
            params["page_token"] = page_token
        if paging_token:
            params["paging_token"] = paging_token
        return self.private_request(f"fbsearch/{item_id}/", params=params)

    def fbsearch_keyword_typeahead(
        self,
        query: str,
        timezone_offset: int = 0,
        count: int = 30,
    ) -> dict:
        params = {
            "search_surface": "typeahead_search_page",
            "query": query,
            "context": "blended",
        }
        if timezone_offset:
            params["timezone_offset"] = timezone_offset
        if count:
            params["count"] = count
        return self.private_request("fbsearch/keyword_typeahead/", params=params)

    def fbsearch_typeahead_stream(
        self,
        query: str,
        timezone_offset: int = 0,
        count: int = 30,
    ) -> dict:
        params = {
            "search_surface": "typeahead_search_page",
            "query": query,
            "context": "blended",
        }
        if timezone_offset:
            params["timezone_offset"] = timezone_offset
        if count:
            params["count"] = count
        return self.private_request("fbsearch/typeahead_stream/", params=params)

    def fbsearch_recent(self) -> List[Tuple[int, Union[UserShort, Hashtag, Dict]]]:
        """
        Retrieves recently searched results

        Returns
        -------
        List[Tuple[int, Union[UserShort, Hashtag, Dict]]]
            Returns list of Tuples where first value is timestamp of searh, second is retrived result
        """
        result = self.private_request("fbsearch/recent_searches/")
        assert result.get("status", "") == "ok", "Failed to retrieve recent searches"

        data = []
        for item in result.get("recent", []):
            if "user" in item.keys():
                data.append((item.get("client_time", None), extract_user_short(item["user"])))
            if "hashtag" in item.keys():
                hashtag = item.get("hashtag")
                hashtag["media_count"] = hashtag.pop("formatted_media_count")
                data.append((item.get("client_time", None), Hashtag(**hashtag)))
            if "keyword" in item.keys():
                data.append((item.get("client_time", None), item["keyword"]))
        return data

    def fbsearch_accounts_v2(self, query: str, page_token: Optional[str] = None) -> dict:
        """
        Search accounts via the v2 SERP endpoint.

        ``GET /fbsearch/account_serp/`` — the surface IG's app uses for
        the "Accounts" tab inside search. Returns the raw payload with
        the full ``users`` list plus pagination cursor.

        Parameters
        ----------
        query: str
            Search query.
        page_token: Optional[str], default None
            Pagination cursor from a previous response.

        Returns
        -------
        dict
            Raw account-serp payload (``users``, ``has_more``,
            ``next_page_token``, etc.).
        """
        params = {
            "search_surface": "account_serp",
            "timezone_offset": self.timezone_offset,
            "query": query,
        }
        if page_token:
            params["page_token"] = page_token
        return self.private_request("fbsearch/account_serp/", params=params)

    def fbsearch_reels_v2(
        self,
        query: str,
        reels_max_id: Optional[str] = None,
        rank_token: Optional[str] = None,
    ) -> dict:
        """
        Search reels via the v2 SERP endpoint.

        ``GET /fbsearch/reels_serp/`` — the surface IG's app uses for
        the "Reels" tab inside search.

        Parameters
        ----------
        query: str
            Search query.
        reels_max_id: Optional[str], default None
            Pagination cursor for the next page of reels.
        rank_token: Optional[str], default None
            Optional client-side ranking token (forwarded to IG to
            keep ordering stable across paginated calls).

        Returns
        -------
        dict
            Raw reels-serp payload.
        """
        params = {
            "search_surface": "clips_search_page",
            "timezone_offset": self.timezone_offset,
            "query": query,
        }
        if reels_max_id:
            params["reels_max_id"] = reels_max_id
        if rank_token:
            params["rank_token"] = rank_token
        return self.private_request("fbsearch/reels_serp/", params=params)

    def fbsearch_topsearch_v2(
        self,
        query: str,
        next_max_id: Optional[str] = None,
        reels_max_id: Optional[str] = None,
        rank_token: Optional[str] = None,
    ) -> dict:
        """
        Blended search (accounts + hashtags + media + reels) via the
        v2 SERP endpoint.

        ``GET /fbsearch/top_serp/`` — the surface IG's app uses for the
        default "Top" tab inside search.

        Parameters
        ----------
        query: str
            Search query.
        next_max_id: Optional[str], default None
            Pagination cursor for the next page of results.
        reels_max_id: Optional[str], default None
            Pagination cursor for the embedded reels carousel.
        rank_token: Optional[str], default None
            Optional client-side ranking token. When provided overrides
            the default ``self.rank_token``.

        Returns
        -------
        dict
            Raw top-serp payload.
        """
        params = {
            "search_surface": "top_serp",
            "timezone_offset": self.timezone_offset,
            "query": query,
            "rank_token": self.rank_token,
        }
        if next_max_id:
            params["next_max_id"] = next_max_id
        if rank_token:
            params["rank_token"] = rank_token
        if reels_max_id:
            params["reels_max_id"] = reels_max_id
        return self.private_request("fbsearch/top_serp/", params=params)

    @staticmethod
    def _top_serp_media_pk(item: dict) -> str:
        pk = str(item.get("pk") or item.get("id") or "").partition("_")[0]
        return pk if pk.isdecimal() else ""

    def media_search_top_gql(self, query: str, amount: int = 0) -> List[Media]:
        """Return media from the first page of mobile Top search.

        With ``amount=0``, return every media item on that page.
        """
        if amount < 0:
            raise ValueError("amount must be non-negative")
        connection = self._top_serp_connection(query, self._top_serp_search_ids())
        return self._extract_top_serp_media(connection, set(), amount)

    def media_search_top_gql_chunk(
        self, query: str, cursor: Optional[_TopSerpCursor] = None
    ) -> Tuple[List[Media], Optional[_TopSerpCursor]]:
        """Return one page of mobile Top search media and the cursor for the next page.

        Pass the returned cursor with the same query and authenticated session until
        the cursor is ``None``. A page can be empty even when more pages are available.
        """
        if cursor is None:
            search_ids = self._top_serp_search_ids()
            after = None
            seen_media: set[str] = set()
            seen_cursors: frozenset[str] = frozenset()
        else:
            if not isinstance(cursor, _TopSerpCursor):
                raise TypeError("cursor must come from media_search_top_gql_chunk")
            if cursor.query != query:
                raise ValueError("cursor belongs to a different search query")
            search_ids = cursor.search_ids
            after = cursor.after
            seen_media = set(cursor.seen_media)
            seen_cursors = cursor.seen_cursors

        connection = self._top_serp_connection(query, search_ids, after)
        medias = self._extract_top_serp_media(connection, seen_media)
        page_info = connection.get("page_info")
        if not isinstance(page_info, dict) or page_info.get("has_next_page") is not True:
            return medias, None
        next_after = page_info.get("end_cursor")
        if not isinstance(next_after, str) or not next_after or next_after in seen_cursors:
            return medias, None
        return medias, _TopSerpCursor(query, search_ids, next_after, frozenset(seen_media), seen_cursors | {next_after})

    def _top_serp_search_ids(self) -> Tuple[str, str, str]:
        return self.generate_uuid(), self.generate_uuid(), self.generate_uuid()

    def _top_serp_connection(self, query: str, search_ids: Tuple[str, str, str], after: Optional[str] = None) -> dict:
        search_session_id, serp_session_id, journey_session_id = search_ids
        variables = {
            "query": query,
            "search_session_id": search_session_id,
            "serp_session_id": serp_session_id,
            "journey_session_id": journey_session_id,
            "turn_id": 0,
            "skip_over_fetched_user_fields": False,
            "should_include_media_overlay_info_in_lightweight": True,
            "in_serp_interacted_media_ids": [],
            "is_pagination_request": after is not None,
            "should_fetch_timeline_in_skw": False,
            "serp_origination_context": {
                "serp_origination": "keyboard",
                "session_state": "typeahead",
                "keyword_context": "null",
                "cdd_ranking_token": None,  # nosec B105 - This protocol field is null.
            },
            "is_incremental_delivery_enabled": False,
            "enable_clips_metadata_in_light_media": False,
            "include_profile_update_info": True,
            "search_type": "SEARCH",
            "remove_view_count_from_lightweight": True,
            "remove_unused_video_subtitles_status": True,
            "include_journey_header": False,
            "is_page_info_fetched_in_separate_chunk": True,
            "remove_unused_deprecated_owner_counts": True,
            "exclude_main_user_field": False,
            "enable_pando_connection": False,
            "num_media_to_fetch": 10,
            "remove_unused_video_subtitles_confidence": True,
            "lightweight_carousel_type": "DELAYED_METADATA",
            "delay_clips_viewer_fragment": True,
            "search_surface": "TOP_SERP",
            "enable_tentpole_story_previews": True,
            "exclude_pinned_posts": True,
            "is_discovery_grid_enabled": True,
            "exclude_caption_user_field": False,
            "hcm_entrypoint": "IG_SEARCH_TYPEAHEAD_KEYBOARD_SEND",
            "lightweight_carousel_count": 1,
            "include_clips_viewer_fragment": True,
            "remove_unused_carousel_pending_post_count": True,
            "remove_paid_partnership_and_subtitles_from_lightweight": True,
            "enable_thumbnails_in_light_media": False,
            "include_search_engine_attributes": False,
            "remove_unused_views_on_grid_status": False,
            "include_search_social_context": False,
            "enable_serp_clips_viewer_deduplication": True,
        }
        if after is not None:
            variables["after"] = after
        result = self.private_graphql_request(
            {
                "method": "post",
                "format": "json",
                "locale": "user",
                "server_timestamps": "true",
                "fb_api_req_friendly_name": "TopSerpQuery",
                "client_doc_id": "418531681916451609839969517761",
                "variables": json.dumps(variables, separators=(",", ":")),
            },
            headers={"X-Root-Field-Name": "xdt_fbsearch__top_serp_graphql"},
        )
        data = result.get("data")
        connection = None
        if isinstance(data, dict):
            connection = data.get("manual_pagination_query", data.get("xdt_fbsearch__top_serp_graphql"))
        if not isinstance(connection, dict) or not isinstance(connection.get("edges"), list):
            raise PrivateError("Missing TopSerpQuery edges", response=self.last_response)
        return connection

    @staticmethod
    def _without_invalid_top_serp_usertag_positions(media: dict) -> dict:
        usertags = media.get("usertags")
        if not isinstance(usertags, dict):
            return media
        tags = usertags.get("in")
        if not isinstance(tags, list):
            return media

        positioned_tags = []
        changed = False
        for tag in tags:
            if isinstance(tag, dict):
                fields = (tag.get("x"), tag.get("y"))
                position = tag.get("position", fields)
                try:
                    _TOP_SERP_USERTAG_POSITION.validate_python(position)
                except ValidationError:
                    changed = True
                    if "position" not in tag:
                        continue
                    try:
                        _TOP_SERP_USERTAG_POSITION.validate_python(fields)
                    except ValidationError:
                        continue
                    tag = dict(tag)
                    tag.pop("position")
            positioned_tags.append(tag)
        if not changed:
            return media
        return dict(media, usertags={**usertags, "in": positioned_tags})

    def _extract_top_serp_media(self, connection: dict, seen: set[str], amount: int = 0) -> List[Media]:
        medias: List[Media] = []
        for edge in connection["edges"]:
            if not isinstance(edge, dict):
                continue
            node = edge.get("node")
            if not isinstance(node, dict) or node.get("__typename") != "XDTTopSerpMediaGridUnit":
                continue
            items = node.get("items")
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict) or item.get("__typename") != "XDTMediaDict":
                    continue
                media_pk = self._top_serp_media_pk(item)
                user = item.get("user")
                if not media_pk or media_pk in seen or not isinstance(user, dict):
                    continue
                user_pk = user.get("id") or user.get("pk")
                if not user_pk:
                    continue
                normalized = dict(item, pk=media_pk, id=f"{media_pk}_{user_pk}", user=dict(user, id=user_pk))
                normalized = self._without_invalid_top_serp_usertag_positions(normalized)
                children = item.get("carousel_media")
                if isinstance(children, list):
                    normalized["carousel_media"] = [
                        self._without_invalid_top_serp_usertag_positions(dict(child, pk=child_pk))
                        for child in children
                        if isinstance(child, dict) and (child_pk := self._top_serp_media_pk(child))
                    ]
                try:
                    medias.append(extract_media_v1(normalized))
                except (AssertionError, AttributeError, IndexError, KeyError, TypeError, ValueError):
                    self.logger.warning("Skipping malformed TopSerpQuery media item")
                    continue
                seen.add(media_pk)
                if amount and len(medias) >= amount:
                    return medias
        return medias

    def media_search(self, query: str, amount: int = 27) -> List[Media]:
        """
        Search top media by keyword via the private fbsearch SERP.

        Parameters
        ----------
        query: str
            Search query.
        amount: int, optional
            Maximum number of media to return, default is 27.

        Returns
        -------
        List[Media]
            List of media results.

        Raises
        ------
        PrivateError
            If the response omits ``media_grid`` or returns a malformed grid payload.
        """
        medias: List[Media] = []
        next_max_id = None
        reels_max_id = None
        rank_token = None
        seen_cursors = set()
        while True:
            kwargs: Dict[str, str] = {}
            if next_max_id:
                kwargs["next_max_id"] = next_max_id
            if reels_max_id:
                kwargs["reels_max_id"] = reels_max_id
            if rank_token:
                kwargs["rank_token"] = rank_token
            result = self.fbsearch_topsearch_v2(query, **kwargs)
            media_grid = self._validate_fbsearch_media_grid(result)
            for node in self._fbsearch_media_grid_nodes(media_grid):
                if amount and len(medias) >= amount:
                    break
                try:
                    medias.append(extract_media_v1(node))
                except (KeyError, AttributeError, TypeError) as exc:
                    self.logger.warning("Skipping malformed fbsearch media node: %s", exc)
                    continue
            if amount and len(medias) >= amount:
                break
            next_max_id = media_grid.get("next_max_id") or result.get("next_max_id")
            if not media_grid.get("has_more") or not next_max_id:
                break
            reels_max_id = media_grid.get("reels_max_id") or result.get("reels_max_id")
            rank_token = media_grid.get("rank_token") or result.get("rank_token")
            cursor_key = (
                str(next_max_id),
                str(reels_max_id) if reels_max_id is not None else None,
            )
            if cursor_key in seen_cursors:
                break
            seen_cursors.add(cursor_key)
        if amount:
            medias = medias[:amount]
        return medias

    def fbsearch_typehead(self, query: str) -> List[dict]:
        """
        Typeahead user suggestions via the streaming endpoint.

        ``GET /fbsearch/typeahead_stream/`` — convenience wrapper that
        flattens the ``stream_rows`` envelope into a flat list of user
        dicts (each row contains a list of users; rows are
        concatenated).

        Parameters
        ----------
        query: str
            Partial query string.

        Returns
        -------
        List[dict]
            Flat list of suggested user dicts.
        """
        params = {
            "search_surface": "typeahead_search_page",
            "timezone_offset": self.timezone_offset,
            "query": query,
            "context": "blended",
        }
        res = self.private_request("fbsearch/typeahead_stream/", params=params)
        rows = res.get("stream_rows", []) or []
        return [user for row in rows for user in row.get("users", [])]
