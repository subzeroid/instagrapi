import random
from typing import List

from instagrapi.exceptions import ClientError, ClientNotFoundError, MediaNotFound
from instagrapi.extractors import extract_comment
from instagrapi.types import Comment


class CommentMixin:
    """
    Helpers for managing comments on a Media
    """

    def media_comments(self, media_id: str) -> List[Comment]:
        """
        Get comments on a media

        Parameters
        ----------
        media_id: str
            Unique identifier of a Media

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
        result = self.private_request(
            f"media/{media_id}/comments/", params
        )
        get_comments()
        while ((result.get("has_more_comments") and result.get("next_max_id"))
               or (result.get("has_more_headload_comments") and result.get("next_min_id"))):
            try:
                if result.get("has_more_comments"):
                    params = {"max_id": result.get("next_max_id")}
                else:
                    params = {"min_id": result.get("next_min_id")}
                if not (result.get("next_max_id") or result.get("next_min_id")
                        or result.get("comments")):
                    break
                result = self.private_request(
                    f"media/{media_id}/comments/", params
                )
                get_comments()
            except ClientNotFoundError as e:
                raise MediaNotFound(e, media_id=media_id, **self.last_json)
            except ClientError as e:
                if "Media not found" in str(e):
                    raise MediaNotFound(e, media_id=media_id, **self.last_json)
                raise e
        return comments

    def media_comment(self, media_id: str, text: str) -> Comment:
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
        result = self.private_request(
            f"media/{media_id}/comment/",
            self.with_action_data(
                {
                    "delivery_class": "organic",
                    "feed_position": "0",
                    "container_module": "self_comments_v2_feed_contextual_self_profile",  # "comments_v2",
                    "user_breadcrumb": self.gen_user_breadcrumb(len(text)),
                    "idempotence_token": self.generate_uuid(),
                    "comment_text": text,
                }
            ),
        )
        return extract_comment(result["comment"])

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
        result = self.private_request(
            f"media/{comment_pk}/comment_{name}/", self.with_action_data(data)
        )
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
            "comment_ids_to_delete": ','.join([str(pk) for pk in comment_pks]),
            "container_module": "self_comments_v2_newsfeed_you"
        }
        result = self.private_request(
            f"media/{media_id}/comment/bulk_delete/",
            self.with_action_data(data)
        )
        return result["status"] == "ok"
