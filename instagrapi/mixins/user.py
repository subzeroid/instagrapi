from copy import deepcopy
from json.decoder import JSONDecodeError
from typing import Dict, List, Tuple

from instagrapi.exceptions import (
    ClientError,
    ClientJSONDecodeError,
    ClientLoginRequired,
    ClientNotFoundError,
    UserNotFound,
)
from instagrapi.extractors import extract_user_gql, extract_user_short, extract_user_v1
from instagrapi.types import Relationship, User, UserShort
from instagrapi.utils import json_value


class UserMixin:
    """
    Helpers to manage user
    """

    _users_cache = {}  # user_pk -> User
    _userhorts_cache = {}  # user_pk -> UserShort
    _usernames_cache = {}  # username -> user_pk
    _users_following = {}  # user_pk -> dict(user_pk -> "short user object")
    _users_followers = {}  # user_pk -> dict(user_pk -> "short user object")

    def user_id_from_username(self, username: str) -> str:
        """
        Get full media id

        Parameters
        ----------
        username: str
            Username for an Instagram account

        Returns
        -------
        str
            User PK

        Example
        -------
        'adw0rd' -> 1903424587
        """
        username = str(username).lower()
        return str(self.user_info_by_username(username).pk)

    def user_short_gql(self, user_id: str, use_cache: bool = True) -> UserShort:
        """
        Get full media id

        Parameters
        ----------
        user_id: str
            User ID
        use_cache: bool, optional
            Whether or not to use information from cache, default value is True

        Returns
        -------
        UserShort
            An object of UserShort type
        """
        if use_cache:
            cache = self._userhorts_cache.get(user_id)
            if cache:
                return cache
        variables = {
            "user_id": str(user_id),
            "include_reel": True,
        }
        data = self.public_graphql_request(
            variables, query_hash="ad99dd9d3646cc3c0dda65debcd266a7"
        )
        if not data["user"]:
            raise UserNotFound(user_id=user_id, **data)
        user = extract_user_short(data["user"]["reel"]["user"])
        self._userhorts_cache[user_id] = user
        return user

    def username_from_user_id_gql(self, user_id: str) -> str:
        """
        Get username from user id

        Parameters
        ----------
        user_id: str
            User ID

        Returns
        -------
        str
            User name

        Example
        -------
        1903424587 -> 'adw0rd'
        """
        return self.user_short_gql(user_id).username

    def username_from_user_id(self, user_id: str) -> str:
        """
        Get username from user id

        Parameters
        ----------
        user_id: str
            User ID

        Returns
        -------
        str
            User name

        Example
        -------
        1903424587 -> 'adw0rd'
        """
        user_id = str(user_id)
        try:
            username = self.username_from_user_id_gql(user_id)
        except ClientError:
            username = self.user_info_v1(user_id).username
        return username

    def user_info_by_username_gql(self, username: str) -> User:
        """
        Get user object from user name

        Parameters
        ----------
        username: str
            User name of an instagram account

        Returns
        -------
        User
            An object of User type
        """
        username = str(username).lower()
        return extract_user_gql(self.public_a1_request(f"/{username!s}/")["user"])

    def user_info_by_username_v1(self, username: str) -> User:
        """
        Get user object from user name

        Parameters
        ----------
        username: str
            User name of an instagram account

        Returns
        -------
        User
            An object of User type
        """
        username = str(username).lower()
        try:
            result = self.private_request(f"users/{username}/usernameinfo/")
        except ClientNotFoundError as e:
            raise UserNotFound(e, username=username, **self.last_json)
        except ClientError as e:
            if "User not found" in str(e):
                raise UserNotFound(e, username=username, **self.last_json)
            raise e
        return extract_user_v1(result["user"])

    def user_info_by_username(self, username: str, use_cache: bool = True) -> User:
        """
        Get user object from username

        Parameters
        ----------
        username: str
            User name of an instagram account
        use_cache: bool, optional
            Whether or not to use information from cache, default value is True

        Returns
        -------
        User
            An object of User type
        """
        username = str(username).lower()
        if not use_cache or username not in self._usernames_cache:
            try:
                try:
                    user = self.user_info_by_username_gql(username)
                except ClientLoginRequired as e:
                    if not self.inject_sessionid_to_public():
                        raise e
                    user = self.user_info_by_username_gql(username)  # retry
            except Exception as e:
                if not isinstance(e, ClientError):
                    self.logger.exception(e)  # Register unknown error
                user = self.user_info_by_username_v1(username)
            self._users_cache[user.pk] = user
            self._usernames_cache[user.username] = user.pk
        return self.user_info(self._usernames_cache[username])

    def user_info_gql(self, user_id: str) -> User:
        """
        Get user object from user id

        Parameters
        ----------
        user_id: str
            User id of an instagram account

        Returns
        -------
        User
            An object of User type
        """
        user_id = str(user_id)
        try:
            # GraphQL haven't method to receive user by id
            return self.user_info_by_username_gql(
                self.username_from_user_id_gql(user_id)
            )
        except JSONDecodeError as e:
            raise ClientJSONDecodeError(e, user_id=user_id)

    def user_info_v1(self, user_id: str) -> User:
        """
        Get user object from user id

        Parameters
        ----------
        user_id: str
            User id of an instagram account

        Returns
        -------
        User
            An object of User type
        """
        user_id = str(user_id)
        try:
            result = self.private_request(f"users/{user_id}/info/")
        except ClientNotFoundError as e:
            raise UserNotFound(e, user_id=user_id, **self.last_json)
        except ClientError as e:
            if "User not found" in str(e):
                raise UserNotFound(e, user_id=user_id, **self.last_json)
            raise e
        return extract_user_v1(result["user"])

    def user_info(self, user_id: str, use_cache: bool = True) -> User:
        """
        Get user object from user id

        Parameters
        ----------
        user_id: str
            User id of an instagram account
        use_cache: bool, optional
            Whether or not to use information from cache, default value is True

        Returns
        -------
        User
            An object of User type
        """
        user_id = str(user_id)
        if not use_cache or user_id not in self._users_cache:
            try:
                try:
                    user = self.user_info_gql(user_id)
                except ClientLoginRequired as e:
                    if not self.inject_sessionid_to_public():
                        raise e
                    user = self.user_info_gql(user_id)  # retry
            except Exception as e:
                if not isinstance(e, ClientError):
                    self.logger.exception(e)
                user = self.user_info_v1(user_id)
            self._users_cache[user_id] = user
            self._usernames_cache[user.username] = user.pk
        return deepcopy(
            self._users_cache[user_id]
        )  # return copy of cache (dict changes protection)

    def new_feed_exist(self) -> bool:
        """
        Returns bool
        -------
        Check if new feed exist
        -------
        True if new feed exist ,
        After Login or load Settings always return False
        """
        results = self.private_request("feed/new_feed_posts_exist/")
        return results.get("new_feed_posts_exist", False)

    def user_friendships_v1(self, user_ids: List[str]) -> dict:
        """
        Get user friendship status

        Parameters
        ----------
        user_ids: List[str]
            List of user id of an instagram account

        Returns
        -------
        dict
        """
        user_ids_str = ','.join(user_ids)
        result = self.private_request(
            "friendships/show_many/",
            data={"user_ids": user_ids_str, '_uuid': self.uuid},
            with_signature=False
        )
        return result["friendship_statuses"]

    def user_friendship_v1(self, user_id: str) -> Relationship:
        """
        Get user friendship status

        Parameters
        ----------
        user_id: str
            User id of an instagram account

        Returns
        -------
        Relationship
            An object of Relationship type
        """

        try:
            results = self.private_request(f"friendships/show/{user_id}/")
            return Relationship(**results)
        except ClientError as e:
            self.logger.exception(e)
            return None
             
    def search_users_v1(self, query: str, count: int) -> List[UserShort]:
        """
        Search users by a query (Private Mobile API)
        Parameters
        ----------
        query: str
            Query to search
        count: int
            The count of search results
        Returns
        -------
        List[UserShort]
            List of users
        """
        results = self.private_request(
            "users/search/",
            params={
                "query": query,
                "count": count
            }
        )
        users = results.get("users", [])
        return [extract_user_short(user) for user in users]
    
    def search_users(self, query: str, count: int = 50) -> List[UserShort]:
        """
        Search users by a query
        Parameters
        ----------
        query: str
            Query string to search
        count: int
            The count of search results
        Returns
        -------
        List[UserShort]
            List of User short object
        """
        return self.search_users_v1(query, count)

    def search_followers_v1(self, user_id: str, query: str) -> List[UserShort]:

        """
        Search users by followers (Private Mobile API)

        Parameters
        ----------
        user_id: str
            User id of an instagram account
        query: str
            Query to search

        Returns
        -------
        List[UserShort]
            List of users
        """
        results = self.private_request(
            f"friendships/{user_id}/followers/",
            params={
                "search_surface": "follow_list_page",
                "query": query,
                "enable_groups": "true"
            }
        )
        users = results.get("users", [])
        return [extract_user_short(user) for user in users]

    def search_followers(self, user_id: str, query: str) -> List[UserShort]:
        """
        Search by followers

        Parameters
        ----------
        user_id: str
            User id of an instagram account
        query: str
            Query string

        Returns
        -------
        List[UserShort]
            List of User short object
        """
        return self.search_followers_v1(user_id, query)

    def search_following_v1(self, user_id: str, query: str) -> List[UserShort]:
        """
        Search following users (Private Mobile API)

        Parameters
        ----------
        user_id: str
            User id of an instagram account
        query: str
            Query to search

        Returns
        -------
        List[UserShort]
            List of users
        """
        results = self.private_request(
            f"friendships/{user_id}/following/",
            params={
                "includes_hashtags": "false",
                "search_surface": "follow_list_page",
                "query": query,
                "enable_groups": "true"
            }
        )
        users = results.get("users", [])
        return [extract_user_short(user) for user in users]

    def search_following(self, user_id: str, query: str) -> List[UserShort]:
        """
        Search by following

        Parameters
        ----------
        user_id: str
            User id of an instagram account
        query: str
            Query string

        Returns
        -------
        List[UserShort]
            List of User short object
        """
        return self.search_following_v1(user_id, query)

    def user_following_gql(self, user_id: str, amount: int = 0) -> List[UserShort]:
        """
        Get user's following information by Public Graphql API

        Parameters
        ----------
        user_id: str
            User id of an instagram account
        amount: int, optional
            Maximum number of media to return, default is 0

        Returns
        -------
        List[UserShort]
            List of objects of User type
        """
        user_id = str(user_id)
        end_cursor = None
        users = []
        variables = {
            "id": user_id,
            "include_reel": True,
            "fetch_mutual": False,
            "first": 24,
        }
        self.inject_sessionid_to_public()
        while True:
            if end_cursor:
                variables["after"] = end_cursor
            data = self.public_graphql_request(
                variables, query_hash="e7e2f4da4b02303f74f0841279e52d76"
            )
            if not data["user"] and not users:
                raise UserNotFound(user_id=user_id, **data)
            page_info = json_value(data, "user", "edge_follow", "page_info", default={})
            edges = json_value(data, "user", "edge_follow", "edges", default=[])
            for edge in edges:
                users.append(extract_user_short(edge["node"]))
            end_cursor = page_info.get("end_cursor")
            if not page_info.get("has_next_page") or not end_cursor:
                break
            if amount and len(users) >= amount:
                break
            # time.sleep(sleep)
        if amount:
            users = users[:amount]
        return users

    def user_following_v1(self, user_id: str, amount: int = 0) -> List[UserShort]:
        """
        Get user's following users information by Private Mobile API

        Parameters
        ----------
        user_id: str
            User id of an instagram account
        amount: int, optional
            Maximum number of media to return, default is 0

        Returns
        -------
        List[UserShort]
            List of objects of User type
        """
        user_id = str(user_id)
        max_id = ""
        users = []
        while True:
            if amount and len(users) >= amount:
                break
            params = {
                "rank_token": self.rank_token,
                "search_surface": "follow_list_page",
                "includes_hashtags": "true",
                "enable_groups": "true",
                "query": "",
                "count": 10000
            }
            if max_id:
                params["max_id"] = max_id
            result = self.private_request(f"friendships/{user_id}/following/", params=params)
            for user in result["users"]:
                users.append(extract_user_short(user))
            max_id = result.get("next_max_id")
            if not max_id:
                break
        if amount:
            users = users[:amount]
        return users

    def user_following(
            self, user_id: str, use_cache: bool = True, amount: int = 0
    ) -> Dict[str, UserShort]:
        """
        Get user's followers information

        Parameters
        ----------
        user_id: str
            User id of an instagram account
        use_cache: bool, optional
            Whether or not to use information from cache, default value is True
        amount: int, optional
            Maximum number of media to return, default is 0

        Returns
        -------
        Dict[str, UserShort]
            Dict of user_id and User object
        """
        user_id = str(user_id)
        users = self._users_following.get(user_id, {})
        if not use_cache or not users or (amount and len(users) < amount):
            # Temporary: Instagram Required Login for GQL request
            # You can inject sessionid from private to public session
            # try:
            #     users = self.user_following_gql(user_id, amount)
            # except Exception as e:
            #     if not isinstance(e, ClientError):
            #         self.logger.exception(e)
            #     users = self.user_following_v1(user_id, amount)
            users = self.user_following_v1(user_id, amount)
            self._users_following[user_id] = {user.pk: user for user in users}
        following = self._users_following[user_id]
        if amount and len(following) > amount:
            following = dict(list(following.items())[:amount])
        return following

    def user_followers_gql_chunk(self, user_id: str, max_amount: int = 0, end_cursor: str = None) -> Tuple[
        List[UserShort], str]:
        """
        Get user's followers information by Public Graphql API and end_cursor

        Parameters
        ----------
        user_id: str
            User id of an instagram account
        max_amount: int, optional
            Maximum number of media to return, default is 0 - Inf
        end_cursor: str, optional
            The cursor from which it is worth continuing to receive the list of followers

        Returns
        -------
        Tuple[List[UserShort], str]
            List of objects of User type with cursor
        """
        user_id = str(user_id)
        users = []
        variables = {
            "id": user_id,
            "include_reel": True,
            "fetch_mutual": False,
            "first": 12
        }
        self.inject_sessionid_to_public()
        while True:
            if end_cursor:
                variables["after"] = end_cursor
            data = self.public_graphql_request(
                variables, query_hash="5aefa9893005572d237da5068082d8d5"
            )
            if not data["user"] and not users:
                raise UserNotFound(user_id=user_id, **data)
            page_info = json_value(data, "user", "edge_followed_by", "page_info", default={})
            edges = json_value(data, "user", "edge_followed_by", "edges", default=[])
            for edge in edges:
                users.append(extract_user_short(edge["node"]))
            end_cursor = page_info.get("end_cursor")
            if not page_info.get("has_next_page") or not end_cursor:
                break
            if max_amount and len(users) >= max_amount:
                break
        return users, end_cursor

    def user_followers_gql(self, user_id: str, amount: int = 0) -> List[UserShort]:
        """
        Get user's followers information by Public Graphql API

        Parameters
        ----------
        user_id: str
            User id of an instagram account
        amount: int, optional
            Maximum number of media to return, default is 0 - Inf

        Returns
        -------
        List[UserShort]
            List of objects of User type
        """
        users, _ = self.user_followers_gql_chunk(str(user_id), amount)
        if amount:
            users = users[:amount]
        return users

    def user_followers_v1_chunk(self, user_id: str, max_amount: int = 0, max_id: str = "") -> Tuple[
        List[UserShort], str]:
        """
        Get user's followers information by Private Mobile API and max_id (cursor)

        Parameters
        ----------
        user_id: str
            User id of an instagram account
        max_amount: int, optional
            Maximum number of media to return, default is 0 - Inf
        max_id: str, optional
            Max ID, default value is empty String

        Returns
        -------
        Tuple[List[UserShort], str]
            Tuple of List of users and max_id
        """
        unique_set = set()
        users = []
        while True:
            result = self.private_request(f"friendships/{user_id}/followers/", params={
                "max_id": max_id,
                "count": 10000,
                "rank_token": self.rank_token,
                "search_surface": "follow_list_page",
                "query": "",
                "enable_groups": "true"
            })
            for user in result["users"]:
                user = extract_user_short(user)
                if user.pk in unique_set:
                    continue
                unique_set.add(user.pk)
                users.append(user)
            max_id = result.get("next_max_id")
            if not max_id or (max_amount and len(users) >= max_amount):
                break
        return users, max_id

    def user_followers_v1(self, user_id: str, amount: int = 0) -> List[UserShort]:
        """
        Get user's followers information by Private Mobile API

        Parameters
        ----------
        user_id: str
            User id of an instagram account
        amount: int, optional
            Maximum number of media to return, default is 0 - Inf

        Returns
        -------
        List[UserShort]
            List of objects of User type
        """
        users, _ = self.user_followers_v1_chunk(str(user_id), amount)
        if amount:
            users = users[:amount]
        return users

    def user_followers(
            self, user_id: str, use_cache: bool = True, amount: int = 0
    ) -> Dict[str, UserShort]:
        """
        Get user's followers

        Parameters
        ----------
        user_id: str
            User id of an instagram account
        use_cache: bool, optional
            Whether or not to use information from cache, default value is True
        amount: int, optional
            Maximum number of media to return, default is 0 - Inf

        Returns
        -------
        Dict[str, UserShort]
            Dict of user_id and User object
        """
        user_id = str(user_id)
        users = self._users_followers.get(user_id, {})
        if not use_cache or not users or (amount and len(users) < amount):
            try:
                users = self.user_followers_gql(user_id, amount)
            except Exception as e:
                if not isinstance(e, ClientError):
                    self.logger.exception(e)
                users = self.user_followers_v1(user_id, amount)
            self._users_followers[user_id] = {user.pk: user for user in users}
        followers = self._users_followers[user_id]
        if amount and len(followers) > amount:
            followers = dict(list(followers.items())[:amount])
        return followers

    def user_follow(self, user_id: str) -> bool:
        """
        Follow a user

        Parameters
        ----------
        user_id: str

        Returns
        -------
        bool
            A boolean value
        """
        assert self.user_id, "Login required"
        user_id = str(user_id)
        if user_id in self._users_following.get(self.user_id, []):
            self.logger.debug("User %s already followed", user_id)
            return False
        data = self.with_action_data({"user_id": user_id})
        result = self.private_request(f"friendships/create/{user_id}/", data)
        if self.user_id in self._users_following:
            self._users_following.pop(self.user_id)  # reset
        return result["friendship_status"]["following"] is True

    def user_unfollow(self, user_id: str) -> bool:
        """
        Unfollow a user

        Parameters
        ----------
        user_id: str

        Returns
        -------
        bool
            A boolean value
        """
        assert self.user_id, "Login required"
        user_id = str(user_id)
        data = self.with_action_data({"user_id": user_id})
        result = self.private_request(f"friendships/destroy/{user_id}/", data)
        if self.user_id in self._users_following:
            self._users_following[self.user_id].pop(user_id, None)
        return result["friendship_status"]["following"] is False

    def user_remove_follower(self, user_id: str) -> bool:
        """
        Remove a follower

        Parameters
        ----------
        user_id: str

        Returns
        -------
        bool
            A boolean value
        """
        assert self.user_id, "Login required"
        user_id = str(user_id)
        data = self.with_action_data({"user_id": str(user_id)})
        result = self.private_request(f"friendships/remove_follower/{user_id}/", data)
        if self.user_id in self._users_followers:
            self._users_followers[self.user_id].pop(user_id, None)
        return result["friendship_status"]["followed_by"] is False

    def mute_posts_from_follow(self, user_id: str, revert: bool = False) -> bool:
        """
        Mute posts from following user

        Parameters
        ----------
        user_id: str
            Unique identifier of a User
        revert: bool, optional
            Unmute when True

        Returns
        -------
        bool
            A boolean value
        """
        user_id = str(user_id)
        name = "unmute" if revert else "mute"
        result = self.private_request(
            f"friendships/{name}_posts_or_story_from_follow/",
            {
                # "media_id": media_pk,  # when feed_timeline
                "target_posts_author_id": str(user_id),
                "container_module": "media_mute_sheet"  # or "feed_timeline"
            }
        )
        return result["status"] == "ok"

    def unmute_posts_from_follow(self, user_id: str) -> bool:
        """
        Unmute posts from following user

        Parameters
        ----------
        user_id: str
            Unique identifier of a User

        Returns
        -------
        bool
            A boolean value
        """
        return self.mute_posts_from_follow(user_id, True)

    def mute_stories_from_follow(self, user_id: str, revert: bool = False) -> bool:
        """
        Mute stories from following user

        Parameters
        ----------
        user_id: str
            Unique identifier of a User
        revert: bool, optional
            Unmute when True

        Returns
        -------
        bool
            A boolean value
        """
        user_id = str(user_id)
        name = "unmute" if revert else "mute"
        result = self.private_request(
            f"friendships/{name}_posts_or_story_from_follow/",
            {
                # "media_id": media_pk,  # when feed_timeline
                "target_reel_author_id": str(user_id),
                "container_module": "media_mute_sheet"  # or "feed_timeline"
            }
        )
        return result["status"] == "ok"

    def unmute_stories_from_follow(self, user_id: str) -> bool:
        """
        Unmute stories from following user

        Parameters
        ----------
        user_id: str
            Unique identifier of a User

        Returns
        -------
        bool
            A boolean value
        """
        return self.mute_stories_from_follow(user_id, True)

    def enable_posts_notifications(self, user_id: str, disable: bool = False) -> bool:
        """
        Enable post notifications of a user

        Parameters
        ----------
        user_id: str
            Unique identifier of a User
        disable: bool, optional
            Unfavorite when True

        Returns
        -------
        bool
            A boolean value
        """
        assert self.user_id, "Login required"
        user_id = str(user_id)
        data = self.with_action_data({"user_id": user_id, "_uid": self.user_id})
        name = "unfavorite" if disable else "favorite"
        result = self.private_request(f"friendships/{name}/{user_id}/", data)
        return result["status"] == "ok"

    def disable_posts_notifications(self, user_id: str) -> bool:
        """
        Disable post notifications of a user

        Parameters
        ----------
        user_id: str
            Unique identifier of a User
        Returns
        -------
        bool
            A boolean value
        """
        return self.enable_posts_notifications(user_id, True)

    def enable_videos_notifications(self, user_id: str, revert: bool = False) -> bool:
        """
        Enable videos notifications of a user

        Parameters
        ----------
        user_id: str
            Unique identifier of a User
        revert: bool, optional
            Unfavorite when True

        Returns
        -------
        bool
        A boolean value
        """
        assert self.user_id, "Login required"
        user_id = str(user_id)
        data = self.with_action_data({"user_id": user_id, "_uid": self.user_id})
        name = "unfavorite" if revert else "favorite"
        result = self.private_request(f"friendships/{name}_for_igtv/{user_id}/", data)
        return result["status"] == "ok"

    def disable_videos_notifications(self, user_id: str) -> bool:
        """
        Disable videos notifications of a user

        Parameters
        ----------
        user_id: str
            Unique identifier of a User
        Returns
        -------
        bool
            A boolean value
        """
        return self.enable_videos_notifications(user_id, True)

    def enable_reels_notifications(self, user_id: str, revert: bool = False) -> bool:
        """
        Enable reels notifications of a user

        Parameters
        ----------
        user_id: str
            Unique identifier of a User
        revert: bool, optional
            Unfavorite when True

        Returns
        -------
        bool
        A boolean value
        """
        assert self.user_id, "Login required"
        user_id = str(user_id)
        data = self.with_action_data({"user_id": user_id, "_uid": self.user_id})
        name = "unfavorite" if revert else "favorite"
        result = self.private_request(f"friendships/{name}_for_clips/{user_id}/", data)
        return result["status"] == "ok"

    def disable_reels_notifications(self, user_id: str) -> bool:
        """
        Disable reels notifications of a user

        Parameters
        ----------
        user_id: str
            Unique identifier of a User
        Returns
        -------
        bool
            A boolean value
        """
        return self.enable_reels_notifications(user_id, True)

    def enable_stories_notifications(self, user_id: str, revert: bool = False) -> bool:
        """
        Enable stories notifications of a user

        Parameters
        ----------
        user_id: str
            Unique identifier of a User
        revert: bool, optional
            Unfavorite when True

        Returns
        -------
        bool
        A boolean value
        """
        assert self.user_id, "Login required"
        user_id = str(user_id)
        data = self.with_action_data({"user_id": user_id, "_uid": self.user_id})
        name = "unfavorite" if revert else "favorite"
        result = self.private_request(f"friendships/{name}_for_stories/{user_id}/", data)
        return result["status"] == "ok"

    def disable_stories_notifications(self, user_id: str) -> bool:
        """
        Disable stories notifications of a user

        Parameters
        ----------
        user_id: str
            Unique identifier of a User
        Returns
        -------
        bool
            A boolean value
        """
        return self.enable_stories_notifications(user_id, True)
