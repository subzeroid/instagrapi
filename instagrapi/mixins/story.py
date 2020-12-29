import json
from typing import List

from instagrapi import config
from instagrapi.extractors import extract_story_v1
from instagrapi.types import Story


class StoryMixin:

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
        reel = self.private_request(f"feed/user/{user_id}/story/", params=params)['reel']
        stories = []
        for item in reel['items']:
            stories.append(extract_story_v1(item))
        if amount:
            amount = int(amount)
            stories = stories[:amount]
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
        List[Media]
            A list of objects of Media
        """
        # TODO: Add user_stories_gql
        return self.user_stories_v1(user_id, amount)
