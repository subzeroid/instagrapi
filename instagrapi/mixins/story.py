import json
from copy import deepcopy
from pathlib import Path
from typing import List, Tuple
from urllib.parse import urlparse

from instagrapi import config
from instagrapi.exceptions import (
    ClientError,
    ClientGraphqlError,
    ClientNotFoundError,
    StoryNotFound,
    UserNotFound,
)
from instagrapi.extractors import (
    extract_story_archive_day,
    extract_story_gql,
    extract_story_v1,
    extract_user_short,
    extract_viewer,
)
from instagrapi.types import Story, StoryArchiveDay, UserShort, Viewer


class StoryMixin:
    _stories_cache = {}  # pk -> object

    def story_pk_from_url(self, url: str) -> str:
        """
        Get Story (media) PK from URL

        Parameters
        ----------
        url: str
            URL of the story

        Returns
        -------
        str
            Media PK

        Examples
        --------
        https://www.instagram.com/stories/dhbastards/2581281926631793076/ -> 2581281926631793076
        """
        path = urlparse(url).path
        parts = [p for p in path.split("/") if p and p.isdigit()]
        return str(parts[0])

    def story_info_v1(self, story_pk: str) -> Story:
        """
        Get Story by pk or id

        Parameters
        ----------
        story_pk: str
            Unique identifier of the story

        Returns
        -------
        Story
            An object of Story type
        """
        story_id = self.media_id(story_pk)
        story_pk, user_id = story_id.split("_")

        stories = self.user_stories_v1(user_id)
        for story in stories:
            self._stories_cache[story.pk] = story
        if story_pk not in self._stories_cache:
            raise StoryNotFound(story_pk=story_pk, **self.last_json)
        story = self._stories_cache[story_pk]
        return deepcopy(story)

    def story_info(self, story_pk: str, use_cache: bool = True) -> Story:
        """
        Get Story by pk or id

        Parameters
        ----------
        story_pk: str
            Unique identifier of the story
        use_cache: bool, optional
            Whether or not to use information from cache, default value is True

        Returns
        -------
        Story
            An object of Story type
        """
        if not use_cache or story_pk not in self._stories_cache:
            story = self.story_info_v1(story_pk)
            self._stories_cache[story_pk] = story
        return deepcopy(self._stories_cache[story_pk])

    def story_delete(self, story_pk: str) -> bool:
        """
        Delete story

        Parameters
        ----------
        story_pk: str
            Unique identifier of the story

        Returns
        -------
        bool
            A boolean value
        """
        assert self.user_id, "Login required"
        media_id = self.media_id(story_pk)
        self._stories_cache.pop(self.media_pk(media_id), None)
        return self.media_delete(media_id)

    def users_stories_gql(self, user_ids: List[int], amount: int = 0) -> List[UserShort]:
        """
        Get a user's stories (Public API)

        Parameters
        ----------
        user_ids: List[int]
            List of users
        amount: int
            Max amount of stories

        Returns
        -------
        List[UserShort]
            A list of objects of UserShort for each user_id
        """
        assert isinstance(user_ids, list), "user_ids should be a list of user_id"
        self.inject_sessionid_to_public()

        def _userid_chunks():
            assert user_ids is not None
            user_ids_per_query = 50
            for i in range(0, len(user_ids), user_ids_per_query):
                end = i + user_ids_per_query
                yield user_ids[i:end]

        stories_un = {}
        for userid_chunk in _userid_chunks():
            res = self.public_graphql_request(
                query_hash="303a4ae99711322310f25250d988f3b7",
                variables={"reel_ids": userid_chunk, "precomposed_overlay": False},
            )
            stories_un.update(res)
        users = []
        for media in stories_un["reels_media"]:
            user = extract_user_short(media["owner"])
            items = media["items"]
            if amount:
                items = items[:amount]
            user.stories = [extract_story_gql(m) for m in items]
            users.append(user)
        return users

    def user_stories_gql(self, user_id: str, amount: int = None) -> List[Story]:
        """
        Get a user's stories (Public API)

        Parameters
        ----------
        user_id: str
        amount: int, optional
            Maximum number of story to return, default is all

        Returns
        -------
        List[UserShort]
            A list of objects of UserShort for each user_id
        """
        user = self.users_stories_gql([user_id], amount=amount)[0]
        stories = deepcopy(user.stories)
        if amount:
            stories = stories[:amount]
        return stories

    def _user_stories_public(self, user_id: str, amount: int = None) -> List[Story]:
        try:
            return self.user_stories_gql(user_id, amount)
        except ClientNotFoundError as e:
            raise UserNotFound(e, user_id=user_id, **self.last_json)
        except IndexError:
            return []

    def user_stories_v1(self, user_id: str, amount: int = None) -> List[Story]:
        """
        Get a user's stories (Private API)

        Parameters
        ----------
        user_id: str
        amount: int, optional
            Maximum number of story to return, default is all

        Returns
        -------
        List[Story]
            A list of objects of Story
        """
        params = {"supported_capabilities_new": json.dumps(config.SUPPORTED_CAPABILITIES)}
        user_id = int(user_id)
        reel = self.private_request(f"feed/user/{user_id}/story/", params=params).get("reel") or {}
        stories = []
        for item in reel.get("items", []):
            stories.append(extract_story_v1(item))
        if amount:
            stories = stories[: int(amount)]
        return stories

    def user_stories(self, user_id: str, amount: int = None) -> List[Story]:
        """
        Get a user's stories

        Parameters
        ----------
        user_id: str
        amount: int, optional
            Maximum number of story to return, default is all

        Returns
        -------
        List[Story]
            A list of objects of STory
        """
        if self._has_private_auth():
            try:
                return self.user_stories_v1(user_id, amount)
            except Exception as e:
                if not isinstance(e, ClientError):
                    self.logger.exception(e)
                return self._user_stories_public(user_id, amount)
        try:
            return self._user_stories_public(user_id, amount)
        except UserNotFound:
            raise
        except Exception as e:
            if not self.user_id:
                if isinstance(e, ClientGraphqlError):
                    raise
                raise ClientGraphqlError(
                    "Anonymous story fetch failed via public API and private fallback requires login"
                ) from e
            return self.user_stories_v1(user_id, amount)

    def archive_story_days_paginated_v1(
        self,
        amount: int = 0,
        end_cursor: str = "",
        include_memories: bool = True,
        reel_id: str = "",
    ) -> Tuple[List[StoryArchiveDay], str]:
        """
        Get a page of your story archive days by Private Mobile API

        Parameters
        ----------
        amount: int, optional
            Maximum number of archive days to return, default is 0 (all days)
        end_cursor: str, optional
            Cursor value to start at, obtained from previous call to this method
        include_memories: bool, optional
            Whether to include memories metadata, default value is True
        reel_id: str, optional
            Archive reel identifier to filter by

        Returns
        -------
        Tuple[List[StoryArchiveDay], str]
            A tuple containing a list of archive days and the next end_cursor value
        """
        amount = int(amount)
        params = {
            "timezone_offset": self.timezone_offset,
            "include_memories": "1" if include_memories else "0",
        }
        if end_cursor:
            params["max_id"] = end_cursor
        if reel_id:
            params["reel_id"] = reel_id
        result = self.private_request("archive/reel/day_shells_paginated/", params=params)
        items = result.get("items", [])
        if amount:
            items = items[:amount]
        return ([extract_story_archive_day(item) for item in items], result.get("max_id") or "")

    def archive_story_days_v1(self, amount: int = 0, include_memories: bool = True) -> List[StoryArchiveDay]:
        """
        Get your story archive days by Private Mobile API

        Parameters
        ----------
        amount: int, optional
            Maximum number of archive days to return, default is 0 (all days)
        include_memories: bool, optional
            Whether to include memories metadata, default value is True

        Returns
        -------
        List[StoryArchiveDay]
            A list of objects of StoryArchiveDay
        """
        amount = int(amount)
        days = []
        next_max_id = ""
        while True:
            days_page, next_max_id = self.archive_story_days_paginated_v1(
                amount=amount,
                end_cursor=next_max_id,
                include_memories=include_memories,
            )
            days.extend(days_page)
            if not next_max_id:
                break
            if amount and len(days) >= amount:
                break
        if amount:
            days = days[:amount]
        return days

    def archive_story_days(self, amount: int = 0, include_memories: bool = True) -> List[StoryArchiveDay]:
        """
        Get your story archive days

        Parameters
        ----------
        amount: int, optional
            Maximum number of archive days to return, default is 0 (all days)
        include_memories: bool, optional
            Whether to include memories metadata, default value is True

        Returns
        -------
        List[StoryArchiveDay]
            A list of objects of StoryArchiveDay
        """
        return self.archive_story_days_v1(amount, include_memories)

    @staticmethod
    def _archive_story_reels(response) -> List[dict]:
        reels = response.get("reels") or response.get("reels_media") or []
        if isinstance(reels, dict):
            return list(reels.values())
        if reels:
            return reels
        return [value for key, value in response.items() if str(key).startswith("archiveDay:")]

    def archive_stories_v1(self, amount: int = 0) -> List[Story]:
        """
        Get your archived stories by Private Mobile API

        Parameters
        ----------
        amount: int, optional
            Maximum number of stories to return, default is 0 (all stories)

        Returns
        -------
        List[Story]
            A list of objects of Story
        """
        amount = int(amount)
        days = self.archive_story_days_v1(amount=0)
        stories = []
        for start in range(0, len(days), 50):
            day_ids = [day.id for day in days[start : start + 50]]
            if not day_ids:
                continue
            data = self.with_default_data(
                {
                    "reel_ids": day_ids,
                    "reason": "on_tap",
                    "source": "archive",
                    "batch_size": len(day_ids),
                }
            )
            result = self.private_request("feed/reels_media_stream/", data=data)
            for reel in self._archive_story_reels(result):
                for item in reel.get("items", []):
                    story = extract_story_v1(item)
                    self._stories_cache[story.pk] = story
                    stories.append(story)
                    if amount and len(stories) >= amount:
                        return stories
        return stories

    def archive_stories(self, amount: int = 0) -> List[Story]:
        """
        Get your archived stories

        Parameters
        ----------
        amount: int, optional
            Maximum number of stories to return, default is 0 (all stories)

        Returns
        -------
        List[Story]
            A list of objects of Story
        """
        return self.archive_stories_v1(amount)

    def story_seen(self, story_pks: List[int], skipped_story_pks: List[int] = []):
        """
        Mark stories as seen

        Parameters
        ----------
        story_pks: List[int]

        Returns
        -------
        bool
            A boolean value
        """
        assert isinstance(story_pks, list), "story_pks should be a list of story.pk"
        return self.media_seen(
            [self.media_id(mid) for mid in story_pks],
            [self.media_id(mid) for mid in skipped_story_pks],
        )

    def story_download(self, story_pk: str, filename: str = "", folder: Path = "") -> Path:
        """
        Download story media by media_type

        Parameters
        ----------
        story_pk: str

        Returns
        -------
        Path
            Path for the file downloaded
        """
        story = self.story_info(story_pk)
        url = str(story.thumbnail_url if story.media_type == 1 else story.video_url)
        return self.story_download_by_url(url, filename, folder)

    def story_download_by_url(self, url: str, filename: str = "", folder: Path = "") -> Path:
        """
        Download story media using URL

        Parameters
        ----------
        url: str
            URL for a media
        filename: str, optional
            Filename for the media
        folder: Path, optional
            Directory in which you want to download the album, default is "" and will download the files to working
                directory

        Returns
        -------
        Path
            Path for the file downloaded
        """
        url = str(url)
        fname = urlparse(url).path.rsplit("/", 1)[1].strip()
        assert fname, (
            """The URL must contain the path to the file (mp4 or jpg).\n"""
            """Read the documentation https://subzeroid.github.io/instagrapi/usage-guide/story.html"""
        )
        filename = "%s.%s" % (filename, fname.rsplit(".", 1)[1]) if filename else fname
        path = Path(folder) / filename

        response = self._send_public_request(url, stream=True, timeout=self.request_timeout)
        response.raise_for_status()
        return self._download_response_to_path(response, path)

    def story_viewers_chunk(self, story_pk: int, max_amount: int = 0, max_id: str = "") -> tuple[list[Viewer], str]:
        unique_set: set[str] = set()
        viewers: list[Viewer] = []
        story_pk = self.media_pk(story_pk)
        params = {"supported_capabilities_new": json.dumps(config.SUPPORTED_CAPABILITIES)}

        while True:
            if max_id:
                params["max_id"] = max_id
            result = self.private_request(f"media/{story_pk}/list_reel_media_viewer/", params=params)
            for item in result["viewers"]:
                viewer = extract_viewer(item)
                if viewer.pk in unique_set:
                    continue
                unique_set.add(viewer.pk)
                viewers.append(viewer)

            max_id = result.get("next_max_id")
            if not max_id or (max_amount and len(viewers) >= max_amount):
                break
        return viewers, max_id

    def story_viewers(self, story_pk: int, amount: int = 0) -> List[Viewer]:
        """
        List of story viewers (Private API)

        Parameters
        ----------
        story_pk: int
        amount: int, optional
            Maximum number of story viewers

        Returns
        -------
        List[Viewer]
            A list of objects of Viewer
        """
        viewers, _ = self.story_viewers_chunk(story_pk, amount)
        if amount:
            viewers = viewers[:amount]
        return viewers

    def story_likers_chunk(self, story_pk: int, max_amount: int = 0, max_id: str = "") -> tuple[list[UserShort], str]:
        unique_set: set[str] = set()
        likers: list[UserShort] = []
        story_pk = self.media_pk(story_pk)
        params = {"supported_capabilities_new": json.dumps(config.SUPPORTED_CAPABILITIES)}

        while True:
            if max_id:
                params["max_id"] = max_id
            result = self.private_request(f"media/{story_pk}/list_reel_media_viewer/", params=params)
            for item in result.get("viewers") or []:
                if not item.get("has_liked"):
                    continue
                liker = extract_user_short(item["user"])
                if liker.pk in unique_set:
                    continue
                unique_set.add(liker.pk)
                likers.append(liker)

            max_id = result.get("next_max_id")
            if not max_id or (max_amount and len(likers) >= max_amount):
                break
        return likers, max_id

    def story_likers(self, story_pk: int, amount: int = 0) -> List[UserShort]:
        """
        List of story likers (Private API)

        Parameters
        ----------
        story_pk: int
        amount: int, optional
            Maximum number of story likers

        Returns
        -------
        List[UserShort]
            A list of objects of UserShort
        """
        likers, _ = self.story_likers_chunk(story_pk, amount)
        if amount:
            likers = likers[:amount]
        return likers

    def story_like(self, story_id: str, revert: bool = False) -> bool:
        """
        Like a story

        Parameters
        ----------
        story_id: str
            Unique identifier of a Story
        revert: bool, optional
            If liked, whether or not to unlike. Default is False

        Returns
        -------
        bool
            A boolean value
        """
        assert self.user_id, "Login required"
        media_id = self.media_id(story_id)
        data = {
            "media_id": media_id,
            "_uid": str(self.user_id),
            "source_of_like": "button",
            "tray_session_id": self.tray_session_id,
            "viewer_session_id": self.client_session_id,
            "container_module": "reel_feed_timeline",
        }
        name = "unsend" if revert else "send"
        result = self.private_request(f"story_interactions/{name}_story_like", self.with_action_data(data))
        return result["status"] == "ok"

    def story_unlike(self, story_id: str) -> bool:
        """
        Unlike a story

        Parameters
        ----------
        story_id: str
            Unique identifier of a Story

        Returns
        -------
        bool
            A boolean value
        """
        return self.story_like(story_id, revert=True)

    def story_poll_vote(self, story_id: str, poll_id: str, vote: int) -> bool:
        """
        Vote in a story poll

        Parameters
        ----------
        story_id: str
            Unique identifier of a Story
        poll_id: str
            Unique identifier of a story poll sticker
        vote: int
            Poll option index, starting from 0

        Returns
        -------
        bool
            A boolean value
        """
        assert self.user_id, "Login required"
        if not isinstance(vote, int) or vote < 0:
            raise ValueError("vote must be a non-negative option index")
        media_id = self.media_id(story_id)
        data = {
            "_uid": str(self.user_id),
            "_csrftoken": self.token,
            "vote": str(vote),
        }
        result = self.private_request(
            f"media/{media_id}/{poll_id}/story_poll_vote/",
            self.with_action_data(data),
        )
        return result["status"] == "ok"

    def sticker_tray(self) -> dict:
        """
        Getting a sticker tray from Instagram

        Returns
        -------
        dict
            Sticker Tray
        """
        data = {"_uid": self.user_id, "type": "static_stickers", "_uuid": self.uuid}
        result = self.private_request(
            "creatives/sticker_tray/",
            data=data,
            with_signature=True,
        )
        assert result["status"] == "ok"
        return result
