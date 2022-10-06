import os
from time import sleep
from typing import Dict, List

from instagrapi import Client
from instagrapi.types import UserShort

IG_USERNAME = ''
IG_PASSWORD = ''
IG_CREDENTIAL_PATH = './ig_settings.json'
SLEEP_TIME = '600' # in seconds

class Bot:
    _cl = None

    def __init__(self):
        self._cl = Client()
        if os.path.exists(IG_CREDENTIAL_PATH):
            self._cl.load_settings(IG_CREDENTIAL_PATH)
            self._cl.login(IG_USERNAME, IG_PASSWORD)
        else:
            self._cl.login(IG_USERNAME, IG_PASSWORD)
            self._cl.dump_settings(IG_CREDENTIAL_PATH)
    
    def follow_by_username(self, username) -> bool:
        """
        Follow a user

        Parameters
        ----------
        username: str
            Username for an Instagram account

        Returns
        -------
        bool
            A boolean value
        """
        userid = self._cl.user_id_from_username(username)
        return self._cl.user_follow(userid)

    def unfollow_by_username(self, username) -> bool:
        """
        Unfollow a user

        Parameters
        ----------
        username: str
            Username for an Instagram account

        Returns
        -------
        bool
            A boolean value
        """
        userid = self._cl.user_id_from_username(username)
        return self._cl.user_unfollow(userid)
    
    def get_followers(self, amount: int = 0) -> Dict[int, UserShort]:
        """
        Get bot's followers

        Parameters
        ----------
        amount: int, optional
            Maximum number of media to return, default is 0 - Inf

        Returns
        -------
        Dict[int, UserShort]
            Dict of user_id and User object
        """
        return self._cl.user_followers(self._cl.user_id, amount=amount)
    
    def get_followers_usernames(self, amount: int = 0) -> List[str]:
        """
        Get bot's followers usernames

        Parameters
        ----------
        amount: int, optional
            Maximum number of media to return, default is 0 - Inf

        Returns
        -------
        List[str]
            List of usernames
        """
        followers = self._cl.user_followers(self._cl.user_id, amount=amount)
        return [user.username for user in followers.values()]

    def get_following(self, amount: int = 0) -> Dict[int, UserShort]:
        """
        Get bot's followed users

        Parameters
        ----------
        amount: int, optional
            Maximum number of media to return, default is 0 - Inf

        Returns
        -------
        Dict[int, UserShort]
            Dict of user_id and User object
        """
        return self._cl.user_following(self._cl.user_id, amount=amount)
    
    def get_following_usernames(self, amount: int = 0) -> List[str]:
        """
        Get bot's followed usernames

        Parameters
        ----------
        amount: int, optional
            Maximum number of media to return, default is 0 - Inf

        Returns
        -------
        List[str]
            List of usernames
        """
        following = self._cl.user_following(self._cl.user_id, amount=amount)
        return [user.username for user in following.values()]
    
    def update(self):
        """
        Do something
        """
        pass

if __name__ == '__main__':
    bot = Bot()

    bot.follow_by_username('futbot__')

    while True:
        """
        Infnit loop
        """
        bot.update()
        sleep(SLEEP_TIME)