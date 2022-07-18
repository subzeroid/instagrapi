import json
import shutil
from copy import deepcopy
from pathlib import Path
from typing import List
from urllib.parse import urlparse

import requests

from instagrapi import config
from instagrapi.exceptions import ClientNotFoundError, UserNotFound
from instagrapi.extractors import (
    extract_story_gql,
    extract_story_v1,
    extract_user_short,
)
from instagrapi.types import Story, UserShort


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

    # def story_info_gql(self, story_pk: str):
    #     # GQL havent video_url :-(
    #     return self.media_info_gql(self, str(story_pk))

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
        # result = self.private_request(f"media/{story_pk}/info/")
        # story = extract_story_v1(result["items"][0])
        stories = self.user_stories_v1(user_id)
        for story in stories:
            self._stories_cache[story.pk] = story
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
        self.inject_sessionid_to_public()

        def _userid_chunks():
            assert user_ids is not None
            user_ids_per_query = 50
            for i in range(0, len(user_ids), user_ids_per_query):
                yield user_ids[i:i + user_ids_per_query]

        stories_un = {}
        for userid_chunk in _userid_chunks():
            res = self.public_graphql_request(
                query_hash="303a4ae99711322310f25250d988f3b7",
                variables={"reel_ids": userid_chunk, "precomposed_overlay": False}
            )
            stories_un.update(res)
        users = []
        for media in stories_un['reels_media']:
            user = extract_user_short(media['owner'])
            items = media['items']
            if amount:
                items = items[:amount]
            user.stories = [extract_story_gql(m) for m in items]
            users.append(user)
        return users

    def user_stories_gql(self, user_id: int, amount: int = None) -> List[UserShort]:
        """
        Get a user's stories (Public API)

        Parameters
        ----------
        user_id: int
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

    def user_stories_v1(self, user_id: int, amount: int = None) -> List[Story]:
        """
        Get a user's stories (Private API)

        Parameters
        ----------
        user_id: int
        amount: int, optional
            Maximum number of story to return, default is all

        Returns
        -------
        List[Story]
            A list of objects of Story
        """
        params = {
            "supported_capabilities_new": json.dumps(config.SUPPORTED_CAPABILITIES)
        }
        user_id = int(user_id)
        reel = self.private_request(f"feed/user/{user_id}/story/", params=params).get("reel") or {}
        stories = []
        for item in reel.get("items", []):
            stories.append(extract_story_v1(item))
        if amount:
            stories = stories[:int(amount)]
        return stories

    def user_stories(self, user_id: int, amount: int = None) -> List[Story]:
        """
        Get a user's stories

        Parameters
        ----------
        user_id: int
        amount: int, optional
            Maximum number of story to return, default is all

        Returns
        -------
        List[Story]
            A list of objects of STory
        """
        try:
            return self.user_stories_gql(user_id, amount)
        except ClientNotFoundError as e:
            raise UserNotFound(e, user_id=user_id, **self.last_json)
        except IndexError:
            return []
        except Exception:
            return self.user_stories_v1(user_id, amount)

    def story_seen(self, story_pks: List[int], skipped_story_pks: List[int] = []):
        """
        Mark a story as seen

        Parameters
        ----------
        story_pk: int

        Returns
        -------
        bool
            A boolean value
        """
        return self.media_seen(
            [self.media_id(mid) for mid in story_pks],
            [self.media_id(mid) for mid in skipped_story_pks]
        )

    def story_download(self, story_pk: int, filename: str = "", folder: Path = "") -> Path:
        """
        Download story media by media_type

        Parameters
        ----------
        story_pk: int

        Returns
        -------
        Path
            Path for the file downloaded
        """
        story_pk = int(story_pk)
        story = self.story_info(story_pk)
        url = story.thumbnail_url if story.media_type == 1 else story.video_url
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
        fname = urlparse(url).path.rsplit("/", 1)[1].strip()
        assert fname, """The URL must contain the path to the file (mp4 or jpg).\n"""\
            """Read the documentation https://adw0rd.github.io/instagrapi/usage-guide/story.html"""
        filename = "%s.%s" % (filename, fname.rsplit(".", 1)[1]) if filename else fname
        path = Path(folder) / filename
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(path, "wb") as f:
            response.raw.decode_content = True
            shutil.copyfileobj(response.raw, f)
        return path.resolve()

    def story_viewers(self, story_pk: int, amount: int = 0) -> List[UserShort]:
        """
        List of story viewers (Private API)

        Parameters
        ----------
        story_pk: int
        amount: int, optional
            Maximum number of story viewers

        Returns
        -------
        List[UserShort]
            A list of objects of UserShort
        """
        users = []
        next_max_id = None
        story_pk = self.media_pk(story_pk)
        params = {"supported_capabilities_new": json.dumps(config.SUPPORTED_CAPABILITIES)}
        while True:
            try:
                if next_max_id:
                    params["max_id"] = next_max_id
                result = self.private_request(f"media/{story_pk}/list_reel_media_viewer/", params=params)
                for item in result['users']:
                    users.append(extract_user_short(item))
                if amount and len(users) >= amount:
                    break
                next_max_id = result.get('next_max_id')
                if not next_max_id:
                    break
            except Exception as e:
                self.logger.exception(e)
                break
        if amount:
            users = users[:int(amount)]
        return users

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
            "container_module": "reel_feed_timeline"
        }
        name = "unsend" if revert else "send"
        result = self.private_request(
            f"story_interactions/{name}_story_like", self.with_action_data(data)
        )
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
