import time

from .exceptions import (
    ClientError,
    ClientNotFoundError,
    UserNotFound,
)
from .decorators import check_login
from .extractors import (
    extract_user_gql,
    extract_user_v1,
    extract_user_short,
    extract_media_gql,
    extract_media_v1,
)
from .utils import json_value
from . import config


class User:
    _users_cache = {}  # user_pk -> "full user object"
    _usernames_cache = {}  # username -> user_pk
    _users_following = {}  # user_pk -> dict(user_pk -> "short user object")
    _users_followers = {}  # user_pk -> dict(user_pk -> "short user object")

    def user_id_from_username(self, username: str) -> int:
        """Get user_id by username
        Result: 'adw0rd' -> 1903424587
        """
        return int(self.user_info_by_username(username)["pk"])

    def username_from_user_id(self, user_id: int) -> str:
        """Get username by user_id
        Result: 1903424587 -> 'adw0rd'
        """
        user_id = int(user_id)
        return self.user_info(user_id)["username"]

    def user_info_by_username_gql(self, username: str) -> dict:
        """Return user object via GraphQL API
        """
        return extract_user_gql(self.public_a1_request(f"/{username!s}/")["user"])

    def user_info_by_username_v1(self, username: str) -> dict:
        """Return user object via Private API
        """
        try:
            result = self.private_request(f"users/{username}/usernameinfo/")
        except ClientNotFoundError as e:
            raise UserNotFound(e, username=username, **self.last_json)
        except ClientError as e:
            if "User not found" in str(e):
                raise UserNotFound(e, username=username, **self.last_json)
            raise e
        return extract_user_v1(result["user"])

    def user_info_by_username(self, username: str, use_cache: bool = True) -> dict:
        """Get user info by username
        Result as in self.user_info()
        """
        if not use_cache or username not in self._usernames_cache:
            try:
                user = self.user_info_by_username_gql(username)
            except Exception as e:
                if not isinstance(e, ClientError):
                    self.logger.exception(e)  # Register unknown error
                user = self.user_info_by_username_v1(username)
            self._users_cache[user["pk"]] = user
            self._usernames_cache[user["username"]] = user["pk"]
        return self.user_info(self._usernames_cache[username])

    def user_info_gql(self, user_id: int) -> dict:
        """Return user object via GraphQL API
        """
        user_id = int(user_id)
        variables = {
            "user_id": user_id,
            "include_reel": True,
        }
        data = self.public_graphql_request(
            variables, query_hash="ad99dd9d3646cc3c0dda65debcd266a7"
        )
        if not data["user"]:
            raise UserNotFound(user_id=user_id, **data)
        return self.user_info_by_username_gql(data["user"]["reel"]["user"]["username"])

    def user_info_v1(self, user_id: int) -> dict:
        """Return user object via Private API
        """
        user_id = int(user_id)
        try:
            result = self.private_request(f"users/{user_id}/info/")
        except ClientNotFoundError as e:
            raise UserNotFound(e, user_id=user_id, **self.last_json)
        except ClientError as e:
            if "User not found" in str(e):
                raise UserNotFound(e, user_id=user_id, **self.last_json)
            raise e
        return extract_user_v1(result["user"])

    def user_info(self, user_id: int, use_cache: bool = True) -> list:
        """Get user info by user_id
        """
        user_id = int(user_id)
        if not use_cache or user_id not in self._users_cache:
            try:
                user = self.user_info_gql(user_id)
            except Exception as e:
                if not isinstance(e, ClientError):
                    self.logger.exception(e)
                user = self.user_info_v1(user_id)
            self._users_cache[user_id] = user
            self._usernames_cache[user["username"]] = user["pk"]
        return self._users_cache[user_id]

    def user_following_gql(self, user_id: int, amount: int = 0) -> list:
        """Return list of following users (without authorization)
        """
        user_id = int(user_id)
        end_cursor = None
        users = []
        variables = {
            "id": user_id,
            "include_reel": True,
            "fetch_mutual": False,
            "first": 24
        }
        while True:
            if end_cursor:
                variables["after"] = end_cursor
            data = self.public_graphql_request(
                variables, query_hash="e7e2f4da4b02303f74f0841279e52d76"
            )
            if not data["user"] and not users:
                raise UserNotFound(user_id=user_id, **data)
            page_info = json_value(
                data, "user", "edge_follow", "page_info", default={}
            )
            edges = json_value(
                data, "user", "edge_follow", "edges", default=[]
            )
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

    def user_following_v1(self, user_id: int, amount: int = 0) -> list:
        """Return list of following users (with authorization)
        """
        user_id = int(user_id)
        max_id = ""
        users = []
        while True:
            result = self.private_request(
                f"friendships/{user_id}/following/",
                params={
                    "max_id": max_id,
                    "rank_token": self.rank_token,
                    "ig_sig_key_version": config.SIG_KEY_VERSION,
                },
            )
            for user in result["users"]:
                users.append(extract_user_short(user))
            max_id = result.get("next_max_id")
            if not max_id or (amount and len(users) >= amount):
                break
        if amount:
            users = users[:amount]
        return users

    def user_following(self, user_id: int, use_cache: bool = True, amount: int = 0) -> dict:
        """Return dict {user_id: user} of following users
        """
        user_id = int(user_id)
        if not use_cache or user_id not in self._users_following:
            # Temporary: Instagram Required Login for GQL request
            # try:
            #     users = self.user_following_gql(user_id, amount)
            # except Exception as e:
            #     if not isinstance(e, ClientError):
            #         self.logger.exception(e)
            #     users = self.user_following_v1(user_id, amount)
            users = self.user_following_v1(user_id, amount)
            self._users_following[user_id] = {
                user["pk"]: user for user in users
            }
        return self._users_following[user_id]

    def user_followers(self, user_id: int, use_cache: bool = True) -> list:
        """Get list of user_id of Followers
        """
        user_id = int(user_id)
        if not use_cache or user_id not in self._users_followers:
            # TODO: to public
            max_id = ""
            users = []
            while True:
                result = self.private_request(
                    f"friendships/{user_id}/followers/",
                    params={"rank_token": self.rank_token, "max_id": max_id},
                )
                users += result["users"]
                max_id = result.get("next_max_id")
                if not max_id:
                    break
            self._users_followers[user_id] = {
                user["pk"]: extract_user_short(user) for user in users
            }
        return self._users_followers[user_id]

    @check_login
    def user_follow(self, user_id: int) -> bool:
        """Follow user by user_id
        """
        user_id = int(user_id)
        if user_id in self._users_following.get(self.user_id, []):
            self.logger.debug("User %s already followed", user_id)
            return False
        data = self.with_action_data({"user_id": user_id})
        result = self.private_request(f"friendships/create/{user_id}/", data)
        if self.user_id in self._users_following:
            self._users_following.pop(self.user_id)  # reset
        return result["friendship_status"]["following"] is True

    @check_login
    def user_unfollow(self, user_id: int) -> bool:
        """Unfollow user by user_id
        """
        user_id = int(user_id)
        data = self.with_action_data({"user_id": user_id})
        result = self.private_request(f"friendships/destroy/{user_id}/", data)
        if self.user_id in self._users_following:
            self._users_following[self.user_id].pop(user_id, None)
        return result["friendship_status"]["following"] is False

    def user_medias_gql(self, user_id: int, amount: int = 50, sleep: int = 2) -> list:
        """
        !Use Client.user_medias instead!
        Return list with media of instagram profile by user id using graphql
        :rtype: list
        :param user_id: Profile user id in instagram
        :param amount: Count of medias for fetching (by default instagram return 50)
        :param sleep: Timeout between requests
        :return: List of medias for profile
        """
        amount = int(amount)
        user_id = int(user_id)
        medias = []
        end_cursor = None
        variables = {
            "id": user_id,
            "first": 50,  # default amount
        }
        while True:
            if end_cursor:
                variables["after"] = end_cursor
            data = self.public_graphql_request(
                variables, query_hash="e7e2f4da4b02303f74f0841279e52d76"
            )
            page_info = json_value(
                data, "user", "edge_owner_to_timeline_media", "page_info", default={}
            )
            edges = json_value(
                data, "user", "edge_owner_to_timeline_media", "edges", default=[]
            )
            for edge in edges:
                medias.append(edge["node"])
            end_cursor = page_info.get("end_cursor")
            if not page_info.get("has_next_page") or not end_cursor:
                break
            if len(medias) >= amount:
                break
            time.sleep(sleep)
        return [extract_media_gql(media) for media in medias[:amount]]

    def user_medias_v1(self, user_id: int, amount: int = 18) -> list:
        """Get all medias by user_id via Private API
        :user_id: User ID
        :amount: By default instagram return 18 items by each request
        """
        amount = int(amount)
        user_id = int(user_id)
        medias = []
        next_max_id = ""
        min_timestamp = None
        while True:
            try:
                items = self.private_request(
                    f"feed/user/{user_id}/",
                    params={
                        "max_id": next_max_id,
                        "min_timestamp": min_timestamp,
                        "rank_token": self.rank_token,
                        "ranked_content": "true",
                    },
                )["items"]
            except Exception as e:
                self.logger.exception(e)
                break
            medias.extend(items)
            if not self.last_json.get("more_available"):
                break
            if len(medias) >= amount:
                break
            next_max_id = self.last_json.get("next_max_id", "")
        return [extract_media_v1(media) for media in medias[:amount]]

    def user_medias(self, user_id: int, amount: int = 50) -> list:
        """Get all medias by user_id
        First, through the Public API, then through the Private API
        """
        amount = int(amount)
        user_id = int(user_id)
        try:
            medias = self.user_medias_gql(user_id, amount)  # get first 50 medias
        except Exception as e:
            if not isinstance(e, ClientError):
                self.logger.exception(e)
            # User may been private, attempt via Private API
            # (You can check is_private, but there may be other reasons,
            #  it is better to try through a Private API)
            medias = self.user_medias_v1(user_id, amount)
        return medias
