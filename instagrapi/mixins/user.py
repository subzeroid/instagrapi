import logging
import time
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
from instagrapi.types import Relationship, User, UserShort, Media
from instagrapi.utils import json_value

from instagrapi.extractors import (
    extract_user_v1,
    extract_user_gql,
    extract_media_gql,
    extract_media_v1,
    extract_user_short,
)



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
                self.logger.exception(e)  # Register unknown error
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
        result = self.private_request(
            "friendships/show_many/",
            data={"user_ids": user_ids}
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

    def user_following_gql(self, user_id: str, amount: int = 0, end_cursor: str = None) -> List[UserShort]:
        """
        Get user's following information by Public Graphql API

        Parameters
        ----------
        user_id: str
            User id of an instagram account
        amount: int, optional
            Maximum number of media to return, default is 0
        end_cursor: str, optional
            The cursor from which it is worth continuing to receive the list of following

        Returns
        -------
        generator<UserShort>
            generator of objects of User type
        """
        user_id = str(user_id)
        nb_users = 0
        variables = {
            "id": user_id,
            "include_reel": True,
            "fetch_mutual": False,
            "first": 24,
        }
        self.inject_sessionid_to_public()
        while True:
            if end_cursor:
                self.last_cursor = end_cursor
                variables["after"] = end_cursor
            data = self.public_graphql_request(
                variables, query_hash="e7e2f4da4b02303f74f0841279e52d76"
            )
            if not data["user"]:
                raise UserNotFound(user_id=user_id, **data)
            page_info = json_value(data, "user", "edge_follow", "page_info", default={})
            edges = json_value(data, "user", "edge_follow", "edges", default=[])
            end_cursor = page_info.get("end_cursor")
            self.last_cursor = end_cursor

            for edge in edges:
                yield extract_user_short(edge["node"])
                nb_users += 1
                if amount and nb_users >= amount:
                    break

            if not page_info.get("has_next_page") or not end_cursor or (amount and nb_users >= amount):
                break
            # time.sleep(sleep)

    def user_following_v1(self, user_id: str, amount: int = 0, max_id: str = None) -> List[UserShort]:
        """
        Get user's following users information by Private Mobile API

        Parameters
        ----------
        user_id: str
            User id of an instagram account
        amount: int, optional
            Maximum number of media to return, default is 0
        max_id: str, optional
            The cursor from which it is worth continuing to receive the list of following

        Returns
        -------
        generator<UserShort>
            generator of objects of User type
        """
        user_id = str(user_id)
        nb_users = 0
        while True:
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
            max_id = result.get("next_max_id")
            self.last_cursor = max_id
            for user in result["users"]:
                yield extract_user_short(user)
                nb_users += 1
                if amount and nb_users >= amount:
                    break

            if not max_id or (amount and nb_users >= amount):
                break

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
        generator[str, UserShort]
            generator of user_id and User object
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
            if user_id not in self._users_following:
                self._users_following[user_id] = {}
            for user in self.user_following_v1(user_id, amount):
                self._users_following[user_id][user.pk] = user
                yield user.pk, user
        else:
            for user_pk in self._users_following[user_id]:
                yield user_pk, self._users_following[user_id][user_pk]

    def user_followers_gql_chunk(self, user_id: str, max_amount: int = 0, end_cursor: str = None) -> List[UserShort]:
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
        generator<UserShort>
            generator of objects of User type with cursor
        """
        user_id = str(user_id)
        nb_users = 0
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
                self.last_cursor = end_cursor
            data = self.public_graphql_request(
                variables, query_hash="5aefa9893005572d237da5068082d8d5"
            )
            if not data["user"]:
                raise UserNotFound(user_id=user_id, **data)
            page_info = json_value(data, "user", "edge_followed_by", "page_info", default={})
            edges = json_value(data, "user", "edge_followed_by", "edges", default=[])
            end_cursor = page_info.get("end_cursor")
            self.last_cursor = end_cursor

            for edge in edges:
                yield extract_user_short(edge["node"])
                nb_users += 1
                if max_amount and nb_users >= max_amount:
                    break
            if not page_info.get("has_next_page") or not end_cursor or (max_amount and nb_users >= max_amount):
                break

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
        generator<UserShort>
            generator of objects of User type
        """
        yield from self.user_followers_gql_chunk(str(user_id), amount)

    def user_followers_v1_chunk(self, user_id: str, max_amount: int = 0, max_id: str = "") -> List[UserShort]:
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
        generator<UserShort>
            generator of usershort
        """
        unique_set = set()
        nb_users = 0
        count = 10000
        while True:
            self.last_cursor = max_id
            try:
                result = self.private_request(f"friendships/{user_id}/followers/", params={
                    "max_id": max_id,
                    "count": int(count),
                    "rank_token": self.rank_token,
                    #                "search_surface": "follow_list_page",
                    #                "query": "",
                    #                "enable_groups": "true"
                })
            except Exception as e:
                if "Please wait a few minutes before you try again" in str(e):
                    logging.info(f"{e}: sleeping 60 min")
                    time.sleep(60*60)
                    continue
                count /= 2
                if count < 1000:
                    logging.info("Count to small, break")
                    break
                continue
            if count < 10000:
                count *= 2
            max_id = result.get("next_max_id")
            self.last_cursor = max_id
            for user in result["users"]:
                user = extract_user_short(user)
                if user.pk in unique_set:
                    continue
                unique_set.add(user.pk)
                yield user
                nb_users += 1
                if max_amount and nb_users >= max_amount:
                    break
            if not max_id or (max_amount and nb_users >= max_amount):
                break

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
        generator<UserShort>
            generator of objects of User type
        """
        yield from self.user_followers_v1_chunk(str(user_id), amount)

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
        generator<str, UserShort>
            generator of user_id and User object
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
            if user_id not in self._users_followers:
                self._users_followers[user_id] = {}
            for user in users:
                self._users_followers[user_id][user.pk] = user
                yield user.pk, user
        else:
            for user_pk in self._users_followers[user_id]:
                yield user_pk, self._users_followers[user_id][user_pk]

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

#    def private_request(self, param, params):
#        pass


    def user_medias_gql_chunk(
            self, user_id: int,
            end_cursor=None
    ) -> Tuple[List[Media], str]:
        """
        Get a chunk of a user's media by Public Graphql API

        Parameters
        ----------
        user_id: int
        end_cursor: str, optional
            Cursor value to start at, obtained from previous call to this method
        Returns
        -------
        Tuple[List[Media], str]
            A tuple containing a list of medias and the next end_cursor value
        """
        user_id = int(user_id)
        variables = {
            "id": user_id,
            "first": 50,
        }
        if end_cursor:
            variables["after"] = end_cursor
        data = self.public_graphql_request(
            variables, query_hash="e7e2f4da4b02303f74f0841279e52d76"
        )
        self.last_public_json = self.last_public_json.get("data", self.last_public_json)


        edges = json_value(
            data, "user", "edge_owner_to_timeline_media", "edges", default=[]
        )
        for edge in edges:
            yield extract_media_gql(edge["node"])

    def user_medias_a1_chunk(
            self, user_name: str,
            end_cursor=None
    ) -> Tuple[List[Media], str]:
        """
        Get a chunk of a user's media by Public Graphql API

        Parameters
        ----------
        user_name: str
        end_cursor: str, optional
            Cursor value to start at, obtained from previous call to this method
        Returns
        -------
        Tuple[List[Media], str]
            A tuple containing a list of medias and the next end_cursor value
        """
        if end_cursor:
            logging.warning("user_medias_a1_chunk not working with max_id, try GQL or V1 method")
        data = self.public_a1_request(
            f"/{user_name}/",
            params={"max_id": end_cursor} if end_cursor else {},
        )["user"]
        self.last_public_json = self.last_public_json.get("graphql", self.last_public_json)
        edges = data["edge_owner_to_timeline_media"]["edges"]
        for edge in edges:
            media = extract_media_gql(edge["node"])
            yield media

    def user_medias_v1_chunk(self, user_id: int, end_cursor: str = "") -> Tuple[List[Media], str]:
        """
        Get a page of user's media by Private Mobile API

        Parameters
        ----------
        user_id: int
        end_cursor: str, optional
            Cursor value to start at, obtained from previous call to this method

        Returns
        -------
        Tuple[List[Media], str]
            A tuple containing a list of medias and the next end_cursor value
        """
        user_id = int(user_id)
        next_max_id = end_cursor
        min_timestamp = None
        items = self.private_request(
                f"feed/user/{user_id}/",
                params={
                    "max_id": next_max_id,
                    "count": 1000,
                    "min_timestamp": min_timestamp,
                    "rank_token": self.rank_token,
                    "ranked_content": "true",
                },
        )["items"]
        for item in items:
            yield extract_media_v1(item)

    def user_medias(
        self, user_id: int, amount: int = 0, sleep: int = 2, end_cursor: str = None, method_api="",
    ) -> List[Media]:
        """
        Get a user's media by Public Graphql API

        Parameters
        ----------
        user_id: int
        amount: int, optional
            Maximum number of media to return, default is 0 (all medias)
        sleep: int, optional
            Timeout between pages iterations, default is 2
        end_cursor: str, optional
            Cursor value to start at, obtained from previous call to this method
        method_api: str
            Method api, default value is ""
        Returns
        -------
        generator<Media>
            A generator of objects of Media
        """
        assert method_api in ("A1", "GQL", "V1"), \
            'You must specify one of the option for "method_api" ("A1", "GQL", "V1")'


        amount = int(amount)
        medias_ids = set()
        nb_media = 0
        user_name = None
        while True:
            self.last_cursor = end_cursor
            if method_api == "A1":
                if not user_name:
                    user_name = self.username_from_user_id(user_id)
                medias = self.user_medias_a1_chunk(user_name, end_cursor=end_cursor)
                if end_cursor:
                    logging.warning("user_medias_a1_chunk not working with max_id, try GQL or V1 method")
                    break
            if method_api == "GQL":
                medias = self.user_medias_gql_chunk(user_id, end_cursor=end_cursor)
            if method_api == "V1":
                medias = self.user_medias_v1_chunk(user_id, end_cursor=end_cursor)
            for media in medias:
                if media.pk not in medias_ids:
                    medias_ids.add(media.pk)
#                    print(media.pk)
                    yield media
                    nb_media += 1
                if amount and nb_media >= amount:
                    break

            if method_api == "V1":
                page_info = self.last_json
                if not page_info.get("more_available"):
                    break
                end_cursor = page_info.get("next_max_id", "")
            else:
                page_info = self.last_public_json["user"]["edge_owner_to_timeline_media"]["page_info"]
                end_cursor = page_info.get("end_cursor")
            if not end_cursor or (amount and nb_media >= amount):
                break
            time.sleep(sleep)
