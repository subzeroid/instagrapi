from typing import Dict, List, Optional, Tuple, Union

from instagrapi.extractors import (
    extract_hashtag_v1,
    extract_location,
    extract_track,
    extract_user_short,
)
from instagrapi.types import Hashtag, Location, Track, UserShort


class FbSearchMixin:
    def fbsearch_places(
        self, query: str, lat: float = 40.74, lng: float = -73.94
    ) -> List[Location]:
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
        return [extract_track(item["track"]) for item in result["items"]]

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
        return result["users"]

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
                data.append(
                    (item.get("client_time", None), extract_user_short(item["user"]))
                )
            if "hashtag" in item.keys():
                hashtag = item.get("hashtag")
                hashtag["media_count"] = hashtag.pop("formatted_media_count")
                data.append((item.get("client_time", None), Hashtag(**hashtag)))
            if "keyword" in item.keys():
                data.append((item.get("client_time", None), item["keyword"]))
        return data

    def fbsearch_accounts_v2(
        self, query: str, page_token: Optional[str] = None
    ) -> dict:
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
