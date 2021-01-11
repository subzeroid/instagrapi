import json
from copy import deepcopy
from typing import List

from instagrapi import config
from instagrapi.exceptions import StoryNotFound
from instagrapi.extractors import extract_story_gql, extract_story_v1
from instagrapi.types import Story


class StoryMixin:
    _stories_cache = {}  # pk -> object

    # def story_info_gql(self, story_pk: int):
    #     # GQL havent video_url :-(
    #     return self.media_info_gql(self, int(story_pk))

    def story_info_v1(self, story_pk: int) -> Story:
        """
        Get Story by pk or id

        Parameters
        ----------
        story_pk: int
            Unique identifier of the story

        Returns
        -------
        Story
            An object of Story type
        """
        story_id = self.media_id(story_pk)
        story_pk, user_id = story_id.split("_")
        stories = self.user_stories_v1(user_id)
        story_pk = int(story_pk)
        for story in stories:
            self._stories_cache[story.pk] = story
        if story_pk in self._stories_cache:
            return deepcopy(self._stories_cache[story_pk])
        raise StoryNotFound(story_pk=story_pk, user_id=user_id)

    def story_info(self, story_pk: int, use_cache: bool = True) -> Story:
        """
        Get Story by pk or id

        Parameters
        ----------
        story_pk: int
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

    def story_delete(self, story_pk: int) -> bool:
        """
        Delete story

        Parameters
        ----------
        story_pk: int
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
        List[Media]
            A list of objects of Media
        """
        params = {
            "supported_capabilities_new": json.dumps(config.SUPPORTED_CAPABILITIES)
        }
        user_id = int(user_id)
        reel = self.private_request(f"feed/user/{user_id}/story/", params=params)[
            "reel"
        ]
        stories = []
        for item in reel["items"]:
            stories.append(extract_story_v1(item))
        if amount:
            amount = int(amount)
            stories = stories[:amount]
        return stories

    def user_stories_gql(self, user_ids: List[int] = None):
        self.public.cookies.update(self.private.cookies)

        def _userid_chunks():
            assert user_ids is not None
            user_ids_per_query = 50
            for i in range(0, len(user_ids), user_ids_per_query):
                yield user_ids[i:i + user_ids_per_query]

        stories_un = {}
        for userid_chunk in _userid_chunks():
            res = self.public_graphql_request(query_hash="303a4ae99711322310f25250d988f3b7",
                                              variables={"reel_ids": userid_chunk, "precomposed_overlay": False})
            stories_un.update(res)

        st = []
        for media in stories_un['reels_media']:
            for story in media["items"]:
                st.append(extract_story_gql(story))
                st.append(story)
        return st

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
        List[Media]
            A list of objects of Media
        """
        # TODO: Add user_stories_gql
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
