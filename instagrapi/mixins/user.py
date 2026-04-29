import json
import logging
from copy import deepcopy
from json.decoder import JSONDecodeError
from typing import Dict, List, Tuple

from requests.exceptions import RequestException

from instagrapi.exceptions import (
    ClientError,
    ClientGraphqlError,
    ClientJSONDecodeError,
    ClientLoginRequired,
    ClientNotFoundError,
    InvalidTargetUser,
    RelatedProfileRequired,
    UnknownError,
    UserNotFound,
)
from instagrapi.extractors import extract_user_gql, extract_user_short, extract_user_v1
from instagrapi.types import Relationship, RelationshipShort, User, UserShort
from instagrapi.utils import dumps, generate_jazoest, json_value

MAX_USER_COUNT = 200
INFO_FROM_MODULES = ("self_profile", "feed_timeline", "reel_feed_timeline")
GRAPHQL_WEB_API_URL = "https://www.instagram.com/api/graphql"
GQL_STUFF = {
    "av": "17841464591314721",
    "__d": "www",
    "__user": "0",
    "__a": "1",
    "__req": "q",
    "__hs": "19768.HYP:instagram_web_pkg.2.1..0.1",
    "dpr": "2",
    "__ccg": "UNKNOWN",
    "__rev": "1011444902",
    "__s": "x82a1q:agr3gd:4nh4nl",
    "__hsi": "7335888108907652597",
    "__dyn": (
        "7xeUjG1mxu1syUbFp40NonwgU7SbzEdF8aUco2qwJxS0k24o0B-"
        "q1ew65xO0FE2awt81s8hwGwQwoEcE7O2l0Fwqo31w9O7U2cxe0E"
        "UjwGzEaE7622362W2K0zK5o4q3y1Sx-0iS2Sq2-azqwt8dUaob8"
        "2cwMwrUdUbGwmk0KU6O1FwlE6PhA6bxy4VUKUnAwHw"
    ),
    "__csr": (
        "g9cj5kxfs8lifTitQDqhdhalmDEAJaKBRJFdkAGHBkPy9HgCA-A"
        "rtucm5bCBBGpyAoz-mLJpXJufKWGQ9hHhAhnKECuFUZ3Q8Jkmmp"
        "eWyGAzkEj_CjyoZUgK-E8bwYzaxy00ktMGx20XU3gw4KAo3MChU"
        "jw3N80poolwiA1d7G2yu2ucxi1nwEw16OE1JsS043Etw63wkSEgg1Mu00yiU"
    ),
    "__comet_req": "7",
    "lsd": "6b2800R9u4biJOYjcdXFEI",
    "__spin_r": "1011444902",
    "__spin_b": "trunk",
    "__spin_t": "1708019550",
    "fb_api_caller_class": "RelayModern",
    "fb_api_req_friendly_name": "PolarisProfilePageContentQuery",
    "server_timestamps": "true",
}

logger = logging.getLogger(__name__)

try:
    from typing import Literal

    INFO_FROM_MODULE = Literal[INFO_FROM_MODULES]
except Exception:
    INFO_FROM_MODULE = str


class UserMixin:
    """
    Helpers to manage user
    """

    _users_cache = {}  # user_pk -> User
    _userhorts_cache = {}  # user_pk -> UserShort
    _usernames_cache = {}  # username -> user_pk
    _users_following = {}  # user_pk -> dict(user_pk -> "short user object")
    _users_followers = {}  # user_pk -> dict(user_pk -> "short user object")
    _fb_dtsg = None

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
        'example' -> 1903424587
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
        try:
            data = self.public_graphql_request(
                variables, query_hash="ad99dd9d3646cc3c0dda65debcd266a7"
            )
            if not data["user"]:
                raise UserNotFound(user_id=user_id, **data)
            user = extract_user_short(data["user"]["reel"]["user"])
        except ClientGraphqlError:
            user = extract_user_short(self.user_web_profile_info_gql(user_id))
        self._userhorts_cache[user_id] = user
        return user

    def fetch_fb_dtsg(self):
        self.inject_sessionid_to_public()
        response = self.public.get(
            self.PUBLIC_API_URL,
            proxies=self.public.proxies,
            timeout=self.request_timeout,
        )
        html = response.text
        if html:
            start = html.find("__eqmc")
            if start >= 0:
                chunk = html[start:]
                chunk = chunk[:5000]
                chunk_start = chunk.find("{")
                chunk_end = chunk.find("</script>")
                if chunk_start >= 0 and chunk_end > chunk_start:
                    return json.loads(chunk[chunk_start:chunk_end]).get("f")
        return None

    @property
    def fb_dtsg(self):
        if not self._fb_dtsg:
            self._fb_dtsg = self.fetch_fb_dtsg()
        return self._fb_dtsg

    def user_web_profile_info_gql(self, user_id: str) -> dict:
        user_id = str(user_id)
        if not self.inject_sessionid_to_public():
            raise ClientLoginRequired("Session is required for web profile GraphQL")
        doc_id = "26762473490008061"
        variables = {
            "enable_integrity_filters": True,
            "id": user_id,
            "render_surface": "PROFILE",
            "__relay_internal__pv__PolarisCannesGuardianExperienceEnabledrelayprovider": True,
            "__relay_internal__pv__PolarisCASB976ProfileEnabledrelayprovider": False,
            "__relay_internal__pv__PolarisRepostsConsumptionEnabledrelayprovider": False,
        }
        headers = {
            "Origin": "https://www.instagram.com",
            "Authority": "www.instagram.com",
            "Sec-Fetch-Site": "same-origin",
            "X-FB-Friendly-Name": "PolarisProfilePageContentQuery",
        }
        body = self.public_request(
            GRAPHQL_WEB_API_URL,
            data={
                "variables": dumps(variables),
                "doc_id": doc_id,
                "fb_dtsg": self.fb_dtsg,
                "jazoest": generate_jazoest(self.phone_id),
                **GQL_STUFF,
            },
            headers=headers,
            update_headers=False,
            return_json=True,
        )
        if errs := body.get("errors"):
            if "data" not in body:
                summary = errs[0].get("summary")
                description = errs[0].get("description")
                raise ClientGraphqlError(
                    "GraphQL user profile fallback failed. Summary: '{}'. Description: '{}'".format(
                        summary, description
                    )
                )
        data = body.get("data")
        if not data or not data.get("user"):
            raise UserNotFound(user_id=user_id, **body)
        return data["user"]

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
        1903424587 -> 'example'
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
        1903424587 -> 'example'
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
        temporary_public_headers = {
            "Host": "www.instagram.com",
            "X-Requested-With": "XMLHttpRequest",
            "Sec-Ch-Prefers-Color-Scheme": "dark",
            "Sec-Ch-Ua-Platform": '"Linux"',
            "X-Ig-App-Id": "936619743392459",
            "Sec-Ch-Ua-Model": '""',
            "Sec-Ch-Ua-Mobile": "?0",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.6261.112 Safari/537.36"
            ),
            "Accept": "*/*",
            "X-Asbd-Id": "129477",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Referer": "https://www.instagram.com/",
            "Accept-Language": "en-US,en;q=0.9",
            "Priority": "u=1, i",
        }
        data = extract_user_gql(
            json.loads(
                self.public_request(
                    f"https://www.instagram.com/api/v1/users/web_profile_info/?username={username}",
                    headers=temporary_public_headers,
                )
            )["data"]["user"]
        )
        return data

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
                if isinstance(e, RequestException):
                    self.logger.warning(
                        "Public user lookup failed, falling back to private API: %s",
                        e,
                    )
                elif not isinstance(e, ClientError):
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

    def user_info_v1(
        self,
        user_id: str,
        from_module: INFO_FROM_MODULE = "self_profile",
        is_app_start: bool = False,
    ) -> User:
        """
        Get user object from user id

        Parameters
        ----------
        user_id: str
            User id of an instagram account
        from_module: str
            Which module triggered request: self_profile, feed_timeline, reel_feed_timeline. Default: self_profile
        is_app_start: bool
            Boolean value specifying if profile is being retrieved on app launch

        Returns
        -------
        User
            An object of User type
        """
        user_id = str(user_id)
        try:
            params = {
                "is_prefetch": "false",
                "entry_point": "self_profile",
                "from_module": from_module,
                "is_app_start": is_app_start,
            }
            assert (
                from_module in INFO_FROM_MODULES
            ), f'Unsupported send_attribute="{from_module}" {INFO_FROM_MODULES}'
            if from_module != "self_profile":
                params["entry_point"] = "profile"

            result = self.private_request(f"users/{user_id}/info/", params=params)
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

    def user_friendships_v1(self, user_ids: List[str]) -> List[RelationshipShort]:
        """
        Get user friendship status

        Parameters
        ----------
        user_ids: List[str]
            List of user ID of an instagram account

        Returns
        -------
        List[RelationshipShort]
           List of RelationshipShorts with requested user_ids
        """
        user_ids_str = ",".join(user_ids)
        result = self.private_request(
            "friendships/show_many/",
            data={"user_ids": user_ids_str, "_uuid": self.uuid},
            with_signature=False,
        )
        assert result.get("status", "") == "ok"

        relationships = []
        for user_id, status in result.get("friendship_statuses", {}).items():
            relationships.append(RelationshipShort(user_id=user_id, **status))

        return relationships

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
            params = {
                "is_external_deeplink_profile_view": "false",
            }
            result = self.private_request(f"friendships/show/{user_id}/", params=params)
            assert result.get("status", "") == "ok"

            return Relationship(user_id=user_id, **result)
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
            "users/search/", params={"query": query, "count": count}
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
                "enable_groups": "true",
            },
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
                "enable_groups": "true",
            },
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

    def user_following_gql_chunk(
        self, user_id: str, max_amount: int = 0, end_cursor: str = None
    ) -> tuple[list[UserShort], str]:
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
                variables, query_hash="58712303d941c6855d4e888c5f0cd22f"
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
            if max_amount and len(users) >= max_amount:
                break
            # time.sleep(sleep)
        return users, end_cursor

    def user_following_gql(self, user_id: str, amount: int = 0) -> List[UserShort]:
        """
        Get user's following users information by Public Graphql API

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
        users, _ = self.user_following_gql_chunk(str(user_id), amount)
        if amount:
            users = users[:amount]
        return users

    def user_following_v1_chunk(
        self, user_id: str, max_amount: int = 0, max_id: str = ""
    ) -> Tuple[List[UserShort], str]:
        """
        Get user's following users information by Private Mobile API and max_id (cursor)

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
            params = {
                "count": max_amount or MAX_USER_COUNT,
                "rank_token": self.rank_token,
                "search_surface": "follow_list_page",
                "query": "",
                "enable_groups": "true",
            }
            if max_id:
                params["max_id"] = max_id
            result = self.private_request(
                f"friendships/{user_id}/following/",
                params=params,
            )
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

    def user_following_v1(self, user_id: str, amount: int = 0) -> List[UserShort]:
        """
        Get user's following users formation by Private Mobile API

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
        users, _ = self.user_following_v1_chunk(str(user_id), amount)
        if amount:
            users = users[:amount]
        return users

    def user_following(
        self, user_id: str, use_cache: bool = True, amount: int = 0
    ) -> Dict[str, UserShort]:
        """
        Get user's following information

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

    def user_followers_gql_chunk(
        self, user_id: str, max_amount: int = 0, end_cursor: str = None
    ) -> Tuple[List[UserShort], str]:
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
            "first": 12,
        }
        self.inject_sessionid_to_public()
        while True:
            if end_cursor:
                variables["after"] = end_cursor
            data = self.public_graphql_request(
                variables, query_hash="37479f2b8209594dde7facb0d904896a"
            )
            if not data["user"] and not users:
                raise UserNotFound(user_id=user_id, **data)
            page_info = json_value(
                data, "user", "edge_followed_by", "page_info", default={}
            )
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

    def user_followers_v1_chunk(
        self, user_id: str, max_amount: int = 0, max_id: str = ""
    ) -> Tuple[List[UserShort], str]:
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
            params = {
                "count": max_amount or MAX_USER_COUNT,
                "rank_token": self.rank_token,
                "search_surface": "follow_list_page",
                "query": "",
                "enable_groups": "true",
            }
            if max_id:
                params["max_id"] = max_id
            result = self.private_request(
                f"friendships/{user_id}/followers/",
                params=params,
            )
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

    def user_block(self, user_id: str, surface: str = "profile") -> bool:
        """
        Block a User

        Parameters
        ----------
        user_id: str
            User ID of an Instagram account
        surface: str, (optional)
            Surface of block (deafult "profile", also can be "direct_thread_info")

        Returns
        -------
        bool
            A boolean value
        """
        data = {
            "surface": surface,
            "is_auto_block_enabled": "false",
            "user_id": user_id,
            "_uid": self.user_id,
            "_uuid": self.uuid,
        }
        if surface == "direct_thread_info":
            data["client_request_id"] = self.request_id

        result = self.private_request(f"friendships/block/{user_id}/", data)
        assert result.get("status", "") == "ok"

        return result.get("friendship_status", {}).get("blocking") is True

    def user_unblock(self, user_id: str, surface: str = "profile") -> bool:
        """
        Unlock a User

        Parameters
        ----------
        user_id: str
            User ID of an Instagram account
        surface: str, (optional)
            Surface of block (deafult "profile", also can be "direct_thread_info")

        Returns
        -------
        bool
            A boolean value
        """
        data = {
            "container_module": surface,
            "user_id": user_id,
            "_uid": self.user_id,
            "_uuid": self.uuid,
        }
        if surface == "direct_thread_info":
            data["client_request_id"] = self.request_id

        result = self.private_request(f"friendships/unblock/{user_id}/", data)
        assert result.get("status", "") == "ok"

        return result.get("friendship_status", {}).get("blocking") is False

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
                "container_module": "media_mute_sheet",  # or "feed_timeline"
            },
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
                "container_module": "media_mute_sheet",  # or "feed_timeline"
            },
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
        result = self.private_request(
            f"friendships/{name}_for_stories/{user_id}/", data
        )
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

    def close_friend_add(self, user_id: str):
        """
        Add to Close Friends List

        Parameters
        ----------
        user_id: str
            Unique identifier of a User
        Returns
        -------
        bool
            A boolean value
        """
        assert self.user_id, "Login required"
        user_id = str(user_id)
        data = {
            "block_on_empty_thread_creation": "false",
            "module": "CLOSE_FRIENDS_V2_SEARCH",
            "source": "audience_manager",
            "_uid": self.user_id,
            "_uuid": self.uuid,
            "remove": [],
            "add": [user_id],
        }
        result = self.private_request("friendships/set_besties/", data)
        return json_value(result, "friendship_statuses", user_id, "is_bestie")

    def close_friend_remove(self, user_id: str):
        """
        Remove from Close Friends List

        Parameters
        ----------
        user_id: str
            Unique identifier of a User
        Returns
        -------
        bool
            A boolean value
        """
        assert self.user_id, "Login required"
        user_id = str(user_id)
        data = {
            "block_on_empty_thread_creation": "false",
            "module": "CLOSE_FRIENDS_V2_SEARCH",
            "source": "audience_manager",
            "_uid": self.user_id,
            "_uuid": self.uuid,
            "remove": [user_id],
            "add": [],
        }
        result = self.private_request("friendships/set_besties/", data)
        return json_value(result, "friendship_statuses", user_id, "is_bestie") is False

    def creator_info(
        self, user_id: str, entry_point: str = "direct_thread"
    ) -> Tuple[UserShort, Dict]:
        """
        Retrieves Creator's information

        Parameters
        ----------
        user_id: str
            Unique identifier of a User
        entry_point: str, optional
            Entry point for retrieving, default - direct_thread
            When passing self_profile, own user_id must be provided

        Returns
        -------
        Tuple[UserShort, Dict]
            Retrieved User and his Creator's Info
        """
        assert self.user_id, "Login required"
        params = {
            "entry_point": entry_point,
            "surface_type": "android",
            "user_id": user_id,
        }

        result = self.private_request("creator/creator_info/", params=params)
        assert result.get("status", "") == "ok"

        creator_info = result.get("user", {}).pop("creator_info", {})
        user = extract_user_short(result.get("user", {}))
        return (user, creator_info)

    def chaining(self, user_id: str) -> dict:
        """
        Get suggested users for a target user_id.

        Hits Instagram's private ``discover/chaining/`` endpoint — the
        same surface the official app uses to render the "Suggested
        for you" carousel under a profile. Returns the raw payload so
        the caller can decide what shape it wants (typically passed
        straight into :meth:`fetch_suggestion_details` for the
        expanded form).

        Parameters
        ----------
        user_id: str
            Target user pk.

        Returns
        -------
        dict
            Raw ``discover/chaining/`` response.

        Raises
        ------
        InvalidTargetUser
            Instagram refused chaining for this target ("Not eligible
            for chaining."). Common on locked-down / private accounts
            and recently-flagged users.
        """
        params = {
            "module": "profile",
            "target_id": str(user_id),
            "profile_chaining_check": "false",
            "eligible_for_threads_cta": "false",
        }
        try:
            return self.private_request("discover/chaining/", params=params)
        except UnknownError as e:
            if str(e) == "Not eligible for chaining.":
                raise InvalidTargetUser("Not eligible for chaining.") from e
            raise

    def fetch_suggestion_details(self, user_id: str, chained_ids: str) -> dict:
        """
        Fetch expanded details for chained suggestion ids.

        Companion to :meth:`chaining`. Pass a comma-separated list of
        user pks (typically the ``pk`` field of every entry in
        ``chaining()['users']``) and Instagram returns the same users
        with social-context fields filled in (mutual followers,
        verification, friendship state, etc.).

        Parameters
        ----------
        user_id: str
            Target user pk that produced the chained ids.
        chained_ids: str
            Comma-separated list of suggested user pks.

        Returns
        -------
        dict
            Raw ``discover/fetch_suggestion_details/`` response.
        """
        params = {
            "target_id": str(user_id),
            "chained_ids": chained_ids,
            "include_social_context": "1",
        }
        return self.private_request(
            "discover/fetch_suggestion_details/",
            params=params,
        )

    def user_stream_by_username_v1(self, username: str) -> dict:
        """
        Get the streamed profile envelope by username.

        ``POST /users/{username}/usernameinfo_stream/`` — IG's app-side
        surface for a profile fetch keyed by username. Returns the
        streamed envelope (typically with ``stream_rows``).

        Parameters
        ----------
        username: str
            Target IG username.

        Returns
        -------
        dict
            Parsed JSON response.

        Raises
        ------
        UserNotFound
            On 404 / unknown ClientError.
        """
        username = str(username).lower()
        data = {
            "is_prefetch": False,
            "entry_point": "profile",
            "from_module": "feed_timeline",
        }
        try:
            return self.private_request(
                f"users/{username}/usernameinfo_stream/", data=data
            )
        except ClientNotFoundError as e:
            raise UserNotFound(e, username=username, **self.last_json)
        except ClientError as e:
            raise UserNotFound(e, username=username, **self.last_json)

    def user_stream_by_id_v1(self, user_id: str) -> dict:
        """
        Get the streamed profile envelope by pk (mirror of
        :meth:`user_stream_by_username_v1`).

        ``POST /users/{user_id}/info_stream/`` — IG's app-side surface
        for a profile fetch initiated from within the feed-timeline
        flow. Returns the same streamed envelope as the username
        variant.

        Parameters
        ----------
        user_id: str
            Target user pk.

        Returns
        -------
        dict
            Parsed JSON response (typically with ``stream_rows``).

        Raises
        ------
        UserNotFound
            On 404 / unknown ClientError.
        """
        data = {
            "is_prefetch": False,
            "entry_point": "profile",
            "from_module": "feed_timeline",
        }
        try:
            return self.private_request(f"users/{user_id}/info_stream/", data=data)
        except (ClientNotFoundError, ClientError) as e:
            logger.exception(
                "Client error user_stream_by_id_v1, exception: %r, user_id %r",
                e,
                user_id,
            )
            raise UserNotFound("User not found")

    def _user_stream_collector(self, resp, id=None, username=None):
        """
        Collapse a ``stream_rows`` envelope into a single flat user dict.

        Each row in ``stream_rows`` carries a partial ``user`` payload;
        this merges them in order so later rows override earlier ones.
        Falls back to one extra fetch if the first response was empty
        (defensive behaviour matching observed IG quirks).
        """
        data = {}
        for urow in resp.get("stream_rows", []):
            data.update(urow.get("user", {}))
        if data:
            data["pk"] = data.get("pk", data.get("pk_id"))
            return data
        logger.error("user_stream_collector: empty stream_rows, falling back: %r", resp)
        if username:
            self.user_stream_by_username_v1(username)
        elif id:
            self.user_stream_by_id_v1(id)
        else:
            raise UserNotFound(code_error=1257)
        return self.last_json

    def user_stream_by_id_flat(self, user_id: str) -> dict:
        """
        Flatten the streamed profile envelope for a target user pk
        into a single user dict.

        Convenience wrapper: calls :meth:`user_stream_by_id_v1` and
        merges all ``stream_rows[*].user`` partial payloads in order.

        Parameters
        ----------
        user_id: str
            Target user pk.

        Returns
        -------
        dict
            Merged user dict (with ``pk`` resolved from ``pk`` or
            ``pk_id`` whichever IG provided).
        """
        resp = self.user_stream_by_id_v1(user_id)
        return self._user_stream_collector(resp, id=user_id)

    def user_stream_by_username_flat(self, username: str) -> dict:
        """
        Flatten the streamed profile envelope for a target username
        into a single user dict.

        Convenience wrapper: calls :meth:`user_stream_by_username_v1`
        and merges all ``stream_rows[*].user`` partial payloads in
        order.

        Parameters
        ----------
        username: str
            Target IG username.

        Returns
        -------
        dict
            Merged user dict.
        """
        resp = self.user_stream_by_username_v1(username)
        return self._user_stream_collector(resp, username=username)

    def user_web_profile_info_v1(self, username: str) -> dict:
        """
        Web-scraper-style profile fetch via the private API.

        ``GET /users/web_profile_info/?username={username}`` — the same
        payload shape as the public ``api/v1/users/web_profile_info/``
        endpoint, but routed through the private host so it can carry
        a logged-in session and bypass some of the public-side rate
        limiting. Returns the inner ``data`` block (already unwrapped).

        Parameters
        ----------
        username: str
            Target IG username.

        Returns
        -------
        dict
            The user payload (from ``response['data']``).

        Raises
        ------
        UserNotFound
            ``data`` is missing from the response or the request 404'd.
        """
        try:
            result = self.private_request(
                "users/web_profile_info/",
                params={"username": username},
            )
        except (ClientNotFoundError, ClientError) as e:
            raise UserNotFound(e, username=username, **self.last_json)
        if data := result.get("data", {}):
            return data
        raise UserNotFound("Username not found", username=username, **self.last_json)

    def discover_recommended_accounts_for_category_v1(self, user_id: str) -> dict:
        """
        Get business-category-similar accounts for a target user.

        Two-step call:

        1. Fetch the target's profile via :meth:`user_stream_by_id_v1`
           to extract ``category_id`` from the streamed payload.
        2. Hit ``GET /discover/recommended_accounts_for_category/``
           with that ``category_id`` to get IG's "similar businesses"
           recommendations for that category.

        Parameters
        ----------
        user_id: str
            Target user pk.

        Returns
        -------
        dict
            Raw recommended-accounts payload. ``category_id`` will be
            ``None`` if the target has no business category — IG
            still returns a payload (typically with empty ``users``)
            in that case.
        """
        user_info = self.user_stream_by_id_v1(user_id)
        category_id = next(
            (
                cid
                for row in user_info.get("stream_rows", [])
                if (cid := row.get("user", {}).get("category_id")) is not None
            ),
            None,
        )
        return self.private_request(
            "discover/recommended_accounts_for_category/",
            params={"target_id": user_id, "category_id": category_id},
        )

    def user_related_profiles_gql(self, user_id: str) -> List[UserShort]:
        """
        Get related profiles for a target user via the public GraphQL
        ``edge_chaining`` field.

        Hits the legacy ``query_hash="ad99dd9d3646cc3c0dda65debcd266a7"``
        — IG has been gating this query_hash more aggressively over
        time; it may raise ``ClientGraphqlError`` on logged-out or
        rate-limited callers. For a more reliable mobile-app-style
        suggestion list, use :meth:`chaining` (private API).

        Parameters
        ----------
        user_id: str
            Target user pk.

        Returns
        -------
        List[UserShort]
            Related profiles. Empty list if IG returned no edges.

        Raises
        ------
        UserNotFound
            GraphQL response had no ``user`` block.
        RelatedProfileRequired
            Empty result and the caller had ``self.num_retry`` set
            below 4 (opt-in retry signal — set ``client.num_retry``
            yourself to enable).
        """
        variables = {
            "user_id": str(user_id),
            "include_chaining": True,
        }
        data = self.public_graphql_request(
            variables, query_hash="ad99dd9d3646cc3c0dda65debcd266a7"
        )
        if not data.get("user"):
            raise UserNotFound("User not found")
        edges = json_value(data, "user", "edge_chaining", "edges", default=[])
        res = [extract_user_short(e["node"]) for e in edges if "node" in e]
        if (
            not res
            and getattr(self, "num_retry", None) is not None
            and self.num_retry < 4
        ):
            raise RelatedProfileRequired
        return res
