import random
from typing import List, Optional, Tuple

from instagrapi.exceptions import ClientError, ClientNotFoundError, CommentNotFound, MediaNotFound
from instagrapi.extractors import extract_comment
from instagrapi.mixins.graphql import GQL_STUFF
from instagrapi.types import Comment
from instagrapi.utils.auth import generate_jazoest
from instagrapi.utils.serialization import dumps


class CommentMixin:
    """
    Helpers for managing comments on a Media
    """

    def media_comments_threaded_gql_chunk(
        self, media_pk: str, comment_pk: str, end_cursor: str = ""
    ) -> Tuple[List[dict], str]:
        """
        Get threaded comments on a media

        Parameters
        ----------
        comment_pk: str
            Unique identifier of a Comment
        end_cursor: str
            Cursor

        Returns
        -------
        Tuple[List[dict], str]
            A list of objects of Comment
        """
        doc_id = "7171917939589632"
        comments = []
        media_pk = str(self.media_pk(media_pk))
        variables = {
            "after": end_cursor or None,
            "before": None,
            "first": 50,
            "last": None,
            "media_id": media_pk,
            "parent_comment_id": str(comment_pk),
            "is_chronological": None,
        }
        data = {
            "variables": dumps(variables),
            "doc_id": doc_id,
            "fb_dtsg": self.fb_dtsg,
            "jazoest": generate_jazoest(self.phone_id),
            **GQL_STUFF,
        }
        resp = self.graphql_request(data=data)
        if data := resp["data"]:
            key = None
            for key in data.keys():
                if "comments" in key:
                    break
            item = data[key]
            edges = item.get("edges", [])
            if not edges:
                raise CommentNotFound(**data)
            for edge in edges:
                comments.append(edge["node"])
            page_info = item.get("page_info", {})
            end_cursor = page_info.get("end_cursor") if page_info.get("has_next_page") else None
            return comments, end_cursor
        return [], ""

    def media_comments_threaded_gql(self, media_pk: str, comment_pk: str, amount: int = 0) -> List[dict]:
        """
        Get threaded comments on a media
        """
        end_cursor = ""
        comments = []
        while True:
            items, end_cursor = self.media_comments_threaded_gql_chunk(media_pk, comment_pk, end_cursor=end_cursor)
            comments.extend(items)
            if not end_cursor or len(items) == 0:
                break
            if amount and len(comments) >= amount:
                break
        if amount:
            comments = comments[:amount]
        return comments

    def media_comments_gql_chunk(self, media_pk: str, end_cursor: str = "") -> Tuple[List[dict], str]:
        """
        Get comments on a media

        Parameters
        ----------
        media_pk: str
            Unique identifier of a Media
        end_cursor: str
            Cursor

        Returns
        -------
        Tuple[List[dict], str]
            A list of objects of Comment
        """
        media_pk = str(self.media_pk(media_pk))
        comments = []
        doc_id = "6974885689225067"
        variables = {
            "after": end_cursor or None,
            "before": None,
            "first": 50,
            "last": None,
            "media_id": media_pk,
            "sort_order": "popular",
        }
        data = {
            "variables": dumps(variables),
            "doc_id": doc_id,
            "fb_dtsg": self.fb_dtsg,
            "jazoest": generate_jazoest(self.phone_id),
            **GQL_STUFF,
        }
        resp = self.graphql_request(data=data)
        if data := resp["data"]:
            key = None
            for key in data.keys():
                if "comments" in key:
                    break
            item = data[key]
            for edge in item.get("edges", []):
                comments.append(edge["node"])
            page_info = item.get("page_info", {})
            end_cursor = page_info.get("end_cursor") if page_info.get("has_next_page") else None
            return comments, end_cursor
        return [], ""

    def media_comments_gql(self, media_pk: str, amount: int = 50, max_requests: int = 0) -> List[dict]:
        """
        Get comments on a media
        """
        media_pk = self.media_pk(media_pk)
        end_cursor = ""
        comments = []
        i = 0
        while True:
            i += 1
            if max_requests and i > max_requests:
                break
            items, end_cursor = self.media_comments_gql_chunk(media_pk, end_cursor=end_cursor)
            comments.extend(items)
            if not end_cursor or len(items) == 0:
                break
            if amount and len(comments) >= amount:
                break
        if amount:
            comments = comments[:amount]
        return comments

    def media_stream_comments_v1_chunk(
        self, media_id: str, min_id: str = "", max_id: str = ""
    ) -> Tuple[List[Comment], str, str]:
        """
        Get stream comments on a media
        """
        params = {
            "can_support_threading": "true",
            "inventory_source": "explore_story",
            "analytics_module": "comments_v2_feed_timeline",
            "is_carousel_bumped_post": "false",
            "feed_position": "1",
        }
        if min_id:
            params["min_id"] = min_id
        if max_id:
            params["max_id"] = max_id
        result = self.private_request(
            f"media/{media_id}/stream_comments/",
            params=params,
        )
        comments = []
        rows = result.get("stream_rows") or [result]
        for row in rows:
            for comment in row["comments"]:
                comments.append(extract_comment(comment))
        min_id = result.get("next_min_id") or result.get("min_id", "")
        max_id = result.get("next_max_id") or result.get("max_id", "")
        return comments, min_id, max_id

    def media_comment_infos(self, media_ids: List[str]) -> dict:
        """
        Bulk-fetch comment summaries for one or more media items.
        """
        if isinstance(media_ids, (list, tuple)):
            joined = ",".join(str(m) for m in media_ids)
        else:
            joined = str(media_ids)
        params = {
            "can_support_carousel_mentions": "false",
            "media_ids": joined,
        }
        return self.private_request("media/comment_infos/", params=params)

    def media_comments_v1_chunk(
        self, media_id: str, min_id: str = "", max_id: str = ""
    ) -> Tuple[List[Comment], str, str]:
        """
        Get comments on a media by Private Mobile API.
        """
        params = {"can_support_threading": "true", "permalink_enabled": "false"}
        if min_id:
            params["min_id"] = min_id
        if max_id:
            params["max_id"] = max_id
        result = self.private_request(f"media/{media_id}/comments/", params=params)
        comments = [extract_comment(comment) for comment in result.get("comments", [])]
        min_id = result.get("next_min_id") or result.get("min_id", "")
        max_id = result.get("next_max_id") or result.get("max_id", "")
        return comments, min_id, max_id

    def media_comments_v1(self, media_id: str, amount: int = 20) -> List[Comment]:
        """
        Get comments on a media by Private Mobile API.
        """
        comments = []
        min_id, max_id = None, None
        try:
            while True:
                items, min_id, max_id = self.media_comments_v1_chunk(media_id, min_id, max_id)
                comments.extend(items)
                if len(items) == 0:
                    break
                if amount and len(comments) > amount:
                    break
        except ClientNotFoundError as e:
            raise MediaNotFound(e, media_id=media_id, **self.last_json)
        except ClientError as e:
            if "Media not found" in str(e):
                raise MediaNotFound(e, media_id=media_id, **self.last_json)
            raise e
        if amount:
            comments = comments[:amount]
        return comments

    def media_comments(self, media_id: str, amount: int = 20) -> List[Comment]:
        """
        Get comments on a media

        Parameters
        ----------
        media_id: str
            Unique identifier of a Media
        amount: int, optional
            Maximum number of comments to return, default is 0 - Inf

        Returns
        -------
        List[Comment]
            A list of objects of Comment
        """

        # TODO: to public or private
        def get_comments():
            if result.get("comments"):
                for comment in result.get("comments"):
                    comments.append(extract_comment(comment))

        media_id = self.media_id(media_id)
        params = None
        comments = []
        result = self.private_request(f"media/{media_id}/comments/", params)
        get_comments()
        while (result.get("has_more_comments") and result.get("next_max_id")) or (
            result.get("has_more_headload_comments") and result.get("next_min_id")
        ):
            try:
                if result.get("has_more_comments"):
                    params = {"max_id": result.get("next_max_id")}
                else:
                    params = {"min_id": result.get("next_min_id")}
                if not (result.get("next_max_id") or result.get("next_min_id") or result.get("comments")):
                    break
                result = self.private_request(f"media/{media_id}/comments/", params)
                get_comments()
            except ClientNotFoundError as e:
                raise MediaNotFound(e, media_id=media_id, **self.last_json)
            except ClientError as e:
                if "Media not found" in str(e):
                    raise MediaNotFound(e, media_id=media_id, **self.last_json)
                raise e
            if amount and len(comments) >= amount:
                break
        if amount:
            comments = comments[:amount]
        return comments

    def media_comments_chunk(self, media_id: str, max_amount: int, min_id: str = None) -> Tuple[List[Comment], str]:
        """
        Get chunk of comments on a media and end_cursor

        Parameters
        ----------
        media_id: str
            Unique identifier of a Media
        max_amount: int
            Limit number of comments to fetch, default is 100
        min_id: str, optional
            End Cursor of previous chunk that had more comments, default value is None

        Returns
        -------
        Tuple[List[Comment], str]
            A list of objects of Comment and an end_cursor
        """

        # TODO: to public or private
        def get_comments():
            if result.get("comments"):
                for comment in result.get("comments"):
                    comments.append(extract_comment(comment))

        media_id = self.media_id(media_id)
        params = {"min_id": min_id} if min_id else None
        comments = []
        result = self.private_request(f"media/{media_id}/comments/", params)
        get_comments()
        while result.get("has_more_headload_comments") and result.get("next_min_id"):
            try:
                params = {"min_id": result.get("next_min_id")}
                if not (result.get("next_min_id") or result.get("comments")):
                    break
                result = self.private_request(f"media/{media_id}/comments/", params)
                get_comments()
            except ClientNotFoundError as e:
                raise MediaNotFound(e, media_id=media_id, **self.last_json)
            except ClientError as e:
                if "Media not found" in str(e):
                    raise MediaNotFound(e, media_id=media_id, **self.last_json)
                raise e
            if len(comments) >= max_amount:
                break
        return (comments, result.get("next_min_id"))

    def media_comment_replies(self, media_id: str, comment_id: str, amount: int = 0) -> List[Comment]:
        """
        Get replies for a media comment.

        Parameters
        ----------
        media_id: str
            Unique identifier of a Media
        comment_id: str
            Unique identifier of a parent Comment
        amount: int, optional
            Maximum number of replies to return, default is 0 - Inf

        Returns
        -------
        List[Comment]
            A list of objects of Comment
        """
        media_id = self.media_id(media_id)
        comment_id = str(comment_id)
        params = None
        replies = []
        while True:
            try:
                result = self.private_request(
                    f"media/{media_id}/comments/{comment_id}/inline_child_comments/",
                    params,
                )
            except ClientNotFoundError as e:
                raise MediaNotFound(e, media_id=media_id, **self.last_json)
            except ClientError as e:
                if "Media not found" in str(e):
                    raise MediaNotFound(e, media_id=media_id, **self.last_json)
                raise e

            replies.extend(extract_comment(comment) for comment in result.get("child_comments", []))
            if amount and len(replies) >= amount:
                break
            if not (result.get("has_more_head_child_comments") and result.get("next_min_child_cursor")):
                break
            params = {"min_id": result.get("next_min_child_cursor")}
        if amount:
            replies = replies[:amount]
        return replies

    def media_comment_replies_chunk(
        self, media_id: str, comment_id: str, max_amount: int, min_id: str = None
    ) -> Tuple[List[Comment], str]:
        """
        Get one chunk of replies for a media comment and end_cursor.

        Parameters
        ----------
        media_id: str
            Unique identifier of a Media
        comment_id: str
            Unique identifier of a parent Comment
        max_amount: int
            Limit number of replies to fetch
        min_id: str, optional
            End Cursor of previous reply chunk that had more replies,
            default value is None

        Returns
        -------
        Tuple[List[Comment], str]
            A list of objects of Comment and an end_cursor
        """
        media_id = self.media_id(media_id)
        comment_id = str(comment_id)
        params = {"min_id": min_id} if min_id else None
        try:
            result = self.private_request(
                f"media/{media_id}/comments/{comment_id}/inline_child_comments/",
                params,
            )
        except ClientNotFoundError as e:
            raise MediaNotFound(e, media_id=media_id, **self.last_json)
        except ClientError as e:
            if "Media not found" in str(e):
                raise MediaNotFound(e, media_id=media_id, **self.last_json)
            raise e
        replies = [extract_comment(comment) for comment in result.get("child_comments", [])][:max_amount]
        return (replies, result.get("next_min_child_cursor"))

    def media_comment(self, media_id: str, text: str, replied_to_comment_id: Optional[int] = None) -> Comment:
        """
        Post a comment on a media

        Parameters
        ----------
        media_id: str
            Unique identifier of a Media
        text: str
            String to be posted on the media

        Returns
        -------
        Comment
            An object of Comment type
        """
        assert self.user_id, "Login required"
        media_id = self.media_id(media_id)
        data = {
            "delivery_class": "organic",
            "feed_position": "0",
            "container_module": "self_comments_v2_feed_contextual_self_profile",  # "comments_v2",
            "user_breadcrumb": self.gen_user_breadcrumb(len(text)),
            "idempotence_token": self.generate_uuid(),
            "comment_text": text,
        }
        if replied_to_comment_id:
            data["replied_to_comment_id"] = int(replied_to_comment_id)
        result = self.private_request(
            f"media/{media_id}/comment/",
            self.with_action_data(data),
        )
        return extract_comment(result["comment"])

    def media_check_offensive_comment(self, media_id: str, text: str) -> bool:
        """
        Checks if a comment text is offensive

        Parameters
        ----------
        media_id: str
            Unique identifier of a Media
        text: str
            String to be posted on the media

        Returns
        -------
        bool
            If comment is offensive
        """
        assert self.user_id, "Login required"
        media_id = self.media_id(media_id)
        data = {
            # _uid, comment_session_id are not in this body?
            "media_id": media_id,
            "comment_text": text,
        }
        result = self.private_request(
            "media/comment/check_offensive_comment/",
            self.with_action_data(data),
        )
        return result["is_offensive"]

    def media_check_offensive_comment_v2(self, media_id: str, comment: str) -> dict:
        """
        Lighter-weight variant of :meth:`media_check_offensive_comment`
        — returns the full IG payload instead of just the boolean.

        Same endpoint (``POST /media/comment/check_offensive_comment/``)
        but skips the ``with_action_data`` wrapping (no ``_csrftoken`` /
        ``_uid`` / breadcrumb) and just sends
        ``{comment_text, media_id, _uuid}`` directly. Closer to what
        the IG app posts in practice. Returns the raw response so
        callers can inspect any flags IG ships beyond ``is_offensive``
        (e.g. category / confidence in newer payloads).

        Parameters
        ----------
        media_id: str
            Unique identifier of a Media.
        comment: str
            String to check.

        Returns
        -------
        dict
            Raw response payload.
        """
        assert self.user_id, "Login required"
        data = {
            "comment_text": comment,
            "media_id": media_id,
            "_uuid": self.uuid,
        }
        return self.private_request("media/comment/check_offensive_comment/", data=data)

    def comment_like(self, comment_pk: int, revert: bool = False) -> bool:
        """
        Like a comment on a media

        Parameters
        ----------
        comment_pk: int
            Unique identifier of a Comment
        revert: bool, optional
            If liked, whether or not to unlike. Default is False

        Returns
        -------
        bool
            A boolean value
        """
        assert self.user_id, "Login required"
        comment_pk = int(comment_pk)
        data = {
            "is_carousel_bumped_post": "false",
            "container_module": "feed_contextual_self_profile",
            "feed_position": str(random.randint(0, 6)),
        }
        name = "unlike" if revert else "like"
        result = self.private_request(f"media/{comment_pk}/comment_{name}/", self.with_action_data(data))
        return result["status"] == "ok"

    def comment_unlike(self, comment_pk: int) -> bool:
        """
        Unlike a comment on a media

        Parameters
        ----------
        comment_pk: int
            Unique identifier of a Comment

        Returns
        -------
        bool
            A boolean value
        """
        return self.comment_like(comment_pk, revert=True)

    def comment_pin(self, media_id: str, comment_pk: int, revert: bool = False):
        """
        Pin a comment on a media

        Parameters
        ----------
        media_id: str
            Unique identifier of a Media
        comment_pk: int
           Unique identifier of a Comment
        revert: bool, optional
            Unpin when True
        Returns
        -------
        bool
           A boolean value
        """
        data = self.with_action_data({"_uid": self.user_id, "_uuid": self.uuid})
        name = "unpin" if revert else "pin"

        result = self.private_request(f"media/{media_id}/{name}_comment/{comment_pk}", data)
        return result["status"] == "ok"

    def comment_unpin(self, media_id: str, comment_pk: int):
        """
        Unpin a comment on a media

        Parameters
        ----------
        media_id: str
            Unique identifier of a Media
        comment_pk: int
           Unique identifier of a Comment

        Returns
        -------
        bool
           A boolean value
        """
        return self.comment_pin(media_id, comment_pk, True)

    def comment_bulk_delete(self, media_id: str, comment_pks: List[int]) -> bool:
        """
        Delete a comment on a media

        Parameters
        ----------
        media_id: str
            Unique identifier of a Media
        comment_pks: List[int]
            List of unique identifier of a Comment

        Returns
        -------
        bool
            A boolean value
        """
        media_id = self.media_id(media_id)
        data = {
            "comment_ids_to_delete": ",".join([str(pk) for pk in comment_pks]),
            "container_module": "self_comments_v2_newsfeed_you",
        }
        result = self.private_request(f"media/{media_id}/comment/bulk_delete/", self.with_action_data(data))
        return result["status"] == "ok"

    def comment_likers_gql_chunk(self, comment_pk: str, end_cursor: str = "") -> Tuple[List[dict], str]:
        """
        Get likers of comment
        """
        comment_pk = str(comment_pk)
        self.inject_sessionid_to_public()
        likers = []
        variables = {
            "comment_id": str(comment_pk),
            "first": 50,
        }
        query_hash = "5f0b1f6281e72053cbc07909c8d154ae"
        if end_cursor:
            variables["after"] = end_cursor
        data = self.public_graphql_request(variables, query_hash=query_hash)
        comment = data.get("comment") or {}
        edge_liked_by = comment.get("edge_liked_by") or {}
        for edge in edge_liked_by.get("edges") or []:
            likers.append(edge["node"])
        end_cursor = ""
        if "page_info" in edge_liked_by:
            page_info = edge_liked_by["page_info"]
            end_cursor = page_info["end_cursor"] if page_info["has_next_page"] else None
        return likers, end_cursor

    def comment_likers_gql(self, comment_pk: str, amount: int = 0) -> List[dict]:
        """
        Get likers of comment
        """
        comment_pk = str(comment_pk)
        end_cursor = ""
        likers = []
        while True:
            items, end_cursor = self.comment_likers_gql_chunk(comment_pk, end_cursor=end_cursor)
            likers.extend(items)
            if not end_cursor or len(items) == 0:
                break
            if amount and len(likers) >= amount:
                break
        if amount:
            likers = likers[:amount]
        return likers
