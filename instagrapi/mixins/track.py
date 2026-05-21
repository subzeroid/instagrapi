from pathlib import Path
from typing import Any, Dict, Optional, Union
from urllib.parse import urlparse

import requests

from instagrapi.exceptions import ClientError, TrackNotFound
from instagrapi.extractors import extract_track
from instagrapi.types import Track
from instagrapi.utils.serialization import json_value


class TrackMixin:
    @staticmethod
    def _track_value(track: Union[Track, Dict], key: str):
        if isinstance(track, dict):
            return track.get(key)
        return getattr(track, key, None)

    @classmethod
    def _track_highlight_start(cls, track: Union[Track, Dict]) -> int:
        highlight_times = cls._track_value(track, "highlight_start_times_in_ms") or []
        return int(highlight_times[0]) if highlight_times else 0

    def track_download_by_url(self, url: str, filename: str = "", folder: Path = "") -> Path:
        """
        Download track by URL

        Parameters
        ----------
        url: str
            URL for a track
        filename: str, optional
            Filename for the track
        folder: Path, optional
            Directory in which you want to download the track,
            default is "" and will download the files to working directory

        Returns
        -------
        Path
            Path for the file downloaded
        """
        url = str(url)
        fname = urlparse(url).path.rsplit("/", 1)[1].strip()
        assert fname, """The URL must contain the path to the file (m4a or mp3)."""
        filename = "%s.%s" % (filename, fname.rsplit(".", 1)[1]) if filename else fname
        path = Path(folder) / filename
        response = requests.get(url, stream=True, timeout=self.request_timeout)
        response.raise_for_status()
        return self._download_response_to_path(response, path)

    def _track_request(self, data: Dict[str, Any], path: str = "clips/music/") -> Dict:
        try:
            result = self.private_request(path, data)
        except ClientError as e:
            if not self.last_json:
                kw = {k: v for k, v in data.items() if k in {"music_canonical_id", "original_sound_audio_asset_id"}}
                raise TrackNotFound(**kw)
            raise e
        return result

    def music_in_feed_audio_browser(self, browse_session_id: Optional[str] = None) -> Dict:
        """
        Retrieve music candidates for feed photo and carousel posts.

        Parameters
        ----------
        browse_session_id: str, optional
            Browser session id. Generated when omitted.

        Returns
        -------
        Dict
            Raw response from ``music/music_in_feed_audio_browser/``.
        """
        if browse_session_id is None:
            browse_session_id = self.generate_uuid()
        return self.private_request(
            "music/music_in_feed_audio_browser/",
            data={
                "product": "music_in_feed",
                "_uuid": self.uuid,
                "browse_session_id": browse_session_id,
            },
            with_signature=False,
        )

    def music_trending(self, product: str = "feed_post") -> Dict:
        """
        Retrieve trending music candidates.

        Parameters
        ----------
        product: str, optional
            Music product surface. The Android app uses ``feed_post`` for the
            successful current feed-post path.

        Returns
        -------
        Dict
            Raw response from ``music/trending/``.
        """
        return self.private_request(
            "music/trending/",
            data={"product": product, "_uuid": self.uuid},
            with_signature=False,
        )

    def music_top_trends(self, product: str = "music_in_feed", page_size: int = 15) -> Dict:
        """
        Retrieve top trending music candidates.

        Parameters
        ----------
        product: str, optional
            Music product surface.
        page_size: int, optional
            Number of trend rows requested.

        Returns
        -------
        Dict
            Raw response from ``music/top_trends/``.
        """
        return self.private_request(
            "music/top_trends/",
            data={
                "product": product,
                "_uuid": self.uuid,
                "page_size": str(page_size),
            },
            with_signature=False,
        )

    def music_search_v2(
        self,
        query: str,
        product: str = "music_in_feed",
        from_typeahead: bool = False,
        search_session_id: Optional[str] = None,
        browse_session_id: Optional[str] = None,
    ) -> Dict:
        """
        Search music through the current ``music/search_v2/`` app endpoint.

        Parameters
        ----------
        query: str
            Search query.
        product: str, optional
            Music product surface.
        from_typeahead: bool, optional
            Whether the query came from a typeahead suggestion.
        search_session_id: str, optional
            Search session id. Generated when omitted.
        browse_session_id: str, optional
            Browse session id. Generated when omitted.

        Returns
        -------
        Dict
            Raw search response.
        """
        if search_session_id is None:
            search_session_id = self.generate_uuid()
        if browse_session_id is None:
            browse_session_id = self.generate_uuid()
        return self.private_request(
            "music/search_v2/",
            data={
                "from_typeahead": self._bool_to_ig_string(from_typeahead),
                "search_session_id": search_session_id,
                "product": product,
                "q": str(query),
                "_uuid": self.uuid,
                "browse_session_id": browse_session_id,
            },
            with_signature=False,
        )

    def music_keyword_search(
        self,
        query: str,
        product: str = "music_in_feed",
        num_keywords: int = 3,
        search_session_id: str = "",
        browse_session_id: Optional[str] = None,
    ) -> Dict:
        """
        Search music keywords for typeahead.

        Parameters
        ----------
        query: str
            Search query.
        product: str, optional
            Music product surface.
        num_keywords: int, optional
            Number of keyword suggestions requested.
        search_session_id: str, optional
            Search session id.
        browse_session_id: str, optional
            Browse session id. Generated when omitted.

        Returns
        -------
        Dict
            Raw keyword response.
        """
        if browse_session_id is None:
            browse_session_id = self.generate_uuid()
        return self.private_request(
            "music/keyword_search/",
            params={
                "num_keywords": str(num_keywords),
                "search_session_id": search_session_id,
                "product": product,
                "q": str(query),
                "browse_session_id": browse_session_id,
            },
        )

    def music_bookmark(
        self,
        original_audio_id: str,
        surface_requested_from: str = "audio_aggregation_page",
    ) -> bool:
        """
        Bookmark an original audio track.

        Parameters
        ----------
        original_audio_id: str
            Original audio id to bookmark.
        surface_requested_from: str, optional
            App surface requesting the bookmark.

        Returns
        -------
        bool
            A boolean value.
        """
        result = self.private_request(
            "music/bookmark_music/",
            data={
                "original_audio_id": str(original_audio_id),
                "_uuid": self.uuid,
                "surface_requested_from": surface_requested_from,
            },
            with_signature=False,
        )
        return bool(result.get("success")) or result.get("status") == "ok"

    def music_clips_audio_browser(
        self,
        product: str = "story_camera_clips_v2",
        browse_session_id: Optional[str] = None,
    ) -> Dict:
        """
        Retrieve music candidates for the Reels/Clips camera surface.

        Parameters
        ----------
        product: str, optional
            Music product surface.
        browse_session_id: str, optional
            Browse session id. Generated when omitted.

        Returns
        -------
        Dict
            Raw response from ``music/clips_audio_browser/``.
        """
        if browse_session_id is None:
            browse_session_id = self.generate_uuid()
        return self.private_request(
            "music/clips_audio_browser/",
            data={
                "product": product,
                "_uuid": self.uuid,
                "browse_session_id": browse_session_id,
            },
            with_signature=False,
        )

    def music_verify_original_audio_title(self, original_audio_name: str) -> bool:
        """
        Validate an original audio title for Reels publishing.

        Parameters
        ----------
        original_audio_name: str
            Proposed original audio title.

        Returns
        -------
        bool
            ``True`` when Instagram accepts the title.
        """
        result = self.private_request(
            "music/verify_original_audio_title/",
            data={"original_audio_name": original_audio_name, "_uuid": self.uuid},
            with_signature=False,
        )
        return bool(result.get("is_valid"))

    def _feed_music_params(
        self,
        track: Union[Track, Dict],
        audio_asset_start_time: Optional[int] = None,
        overlap_duration: int = 30000,
        browse_session_id: Optional[str] = None,
        alacorn_session_id: Optional[str] = None,
    ) -> Dict:
        audio_asset_id = self._track_value(track, "audio_asset_id") or self._track_value(track, "id")
        audio_cluster_id = self._track_value(track, "audio_cluster_id")
        assert audio_asset_id, "track.audio_asset_id or track.id is required"
        assert audio_cluster_id, "track.audio_cluster_id is required"
        if audio_asset_start_time is None:
            audio_asset_start_time = self._track_highlight_start(track)
        if alacorn_session_id is None:
            alacorn_session_id = self._track_value(track, "alacorn_session_id")
        if alacorn_session_id is None:
            alacorn_session_id = self.music_in_feed_audio_browser().get("alacorn_session_id")
        assert alacorn_session_id, "alacorn_session_id is required"

        data = {
            "audio_asset_id": audio_asset_id,
            "audio_cluster_id": audio_cluster_id,
            "audio_asset_start_time_in_ms": int(audio_asset_start_time),
            "derived_content_start_time_in_ms": 0,
            "overlap_duration_in_ms": int(overlap_duration),
            "browse_session_id": browse_session_id,
            "product": "music_in_feed",
            "song_name": self._track_value(track, "title") or "",
            "artist_name": self._track_value(track, "display_artist") or "",
            "alacorn_session_id": alacorn_session_id,
            "audio_apply_source": 0,
        }
        music_canonical_id = self._track_value(track, "music_canonical_id")
        if music_canonical_id:
            data["music_canonical_id"] = music_canonical_id
        return data

    def track_info_by_canonical_id(self, music_canonical_id: str) -> Track:
        """
        Get Track by music_canonical_id

        Parameters
        ----------
        music_canonical_id: str
            Unique identifier of the track

        Returns
        -------
        Track
            An object of Track type
        """
        data = {
            "tab_type": "clips",
            "referrer_media_id": "",
            "_uuid": self.uuid,
            "music_canonical_id": str(music_canonical_id),
        }
        result = self.private_request("clips/music/", data)
        track = json_value(result, "metadata", "music_info", "music_asset_info")
        return extract_track(track)

    def track_info_by_id(self, track_id: str, max_id: str = "") -> Dict:
        """
        Get Track by id

        Parameters
        ----------
        track_id: str
            Unique identifier of the track

        Returns
        -------
        Dict
            Raw insta response json
        """
        data = {
            "audio_cluster_id": track_id,
            "original_sound_audio_asset_id": track_id,
        }
        if max_id:
            data["max_id"] = max_id
        return self._track_request(data)

    def track_stream_info_by_id(self, track_id: str, max_id: str = "") -> Dict:
        """
        Fetch the streamed clips-pivot page for a given track id.

        ``POST /clips/stream_clips_pivot_page/`` — the surface IG's app
        uses to render the "Audio" page (clips that use this audio +
        the audio-asset metadata). Returns the raw payload so the
        caller can extract whatever they need (clip list, audio
        cluster info, etc.).

        Parameters
        ----------
        track_id: str
            Track identifier (used as both ``audio_asset_id`` and
            ``audio_cluster_id`` per IG's app behavior).
        max_id: str, default ""
            Pagination cursor for the next page of clips.

        Returns
        -------
        Dict
            Raw response.
        """
        data = {
            "pivot_page_type": "audio",
            "music_page": {
                "tab_type": "clips",
                "audio_asset_id": track_id,
                "audio_cluster_id": track_id,
            },
            "_uuid": self.uuid,
        }
        if max_id:
            data["music_page"]["max_id"] = max_id
        return self._track_request(data, path="clips/stream_clips_pivot_page/")
