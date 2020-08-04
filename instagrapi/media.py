import json
from urllib.parse import urlparse

from .utils import InstagramIdCodec
from .exceptions import (
    ClientError,
    ClientNotFoundError,
    MediaNotFound,
)
from .decorators import check_login
from .extractors import extract_media_v1, extract_media_gql, extract_user_short


class Media:
    _medias_cache = {}  # pk -> object

    def media_id(self, media_pk: str) -> str:
        """Return full media id
        Example: 2277033926878261772 -> 2277033926878261772_1903424587
        """
        media_id = str(media_pk)
        if "_" not in media_id:
            assert media_id.isdigit(), (
                "media_id must been contain digits, now %s" % media_id
            )
            user = self.media_user(media_id)
            media_id = "%s_%s" % (media_id, user["pk"])
        return media_id

    @staticmethod
    def media_pk(media_id: str) -> int:
        """Return short media id
        Example: 2277033926878261772_1903424587 -> 2277033926878261772
        """
        media_pk = str(media_id)
        if "_" in media_pk:
            media_pk, _ = media_id.split("_")
        return int(media_pk)

    def media_pk_from_code(self, code: str) -> int:
        """Return media_pk from code
        Example: B1LbfVPlwIA -> 2110901750722920960
        Example: B-fKL9qpeab -> 2278584739065882267
        Example: CCQQsCXjOaBfS3I2PpqsNkxElV9DXj61vzo5xs0 -> 2346448800803776129 (because: CCQQsCXjOaB -> 2346448800803776129)
        """
        return InstagramIdCodec.decode(code[:11])

    def media_pk_from_url(self, url: str) -> int:
        """Return media_pk from url
        Example: https://instagram.com/p/B1LbfVPlwIA/ -> 2110901750722920960
        Example: https://www.instagram.com/p/B-fKL9qpeab/?igshid=1xm76zkq7o1im -> 2278584739065882267
        """
        path = urlparse(url).path
        parts = [p for p in path.split("/") if p]
        return self.media_pk_from_code(parts.pop())

    def media_info_a1(self, media_pk: int, max_id=None) -> dict:
        media_pk = self.media_pk(media_pk)
        shortcode = InstagramIdCodec.encode(media_pk)
        """Use Client.media_info
        """
        params = {"max_id": max_id} if max_id else None
        data = self.public_a1_request(
            "/p/{shortcode!s}/".format(**{"shortcode": shortcode}), params=params
        )
        if not data.get("shortcode_media"):
            raise MediaNotFound(media_pk=media_pk, **data)
        return extract_media_gql(data["shortcode_media"])

    def media_info_gql(self, media_pk: int) -> dict:
        media_pk = self.media_pk(media_pk)
        shortcode = InstagramIdCodec.encode(media_pk)
        """Use Client.media_info
        """
        variables = {
            "shortcode": shortcode,
            "child_comment_count": 3,
            "fetch_comment_count": 40,
            "parent_comment_count": 24,
            "has_threaded_comments": False,
        }
        data = self.public_graphql_request(
            variables, query_hash="477b65a610463740ccdb83135b2014db"
        )
        if not data.get("shortcode_media"):
            raise MediaNotFound(media_pk=media_pk, **data)
        return extract_media_gql(data["shortcode_media"])

    def media_info_v1(self, media_pk: int) -> dict:
        try:
            result = self.private_request(f"media/{media_pk}/info/")
        except ClientNotFoundError as e:
            raise MediaNotFound(e, media_pk=media_pk, **self.last_json)
        except ClientError as e:
            if "Media not found" in str(e):
                raise MediaNotFound(e, media_pk=media_pk, **self.last_json)
            raise e
        return extract_media_v1(result["items"].pop())

    def media_info(self, media_pk: int, use_cache: bool = True) -> dict:
        """Return dict with media information
        """
        media_pk = self.media_pk(media_pk)
        if not use_cache or media_pk not in self._medias_cache:
            try:
                media = self.media_info_gql(media_pk)
            except Exception as e:
                if not isinstance(e, ClientError):
                    self.logger.exception(e)  # Register unknown error
                # Restricted Video: This video is not available in your country.
                # Or private account
                media = self.media_info_v1(media_pk)
            self._medias_cache[media_pk] = media
        return self._medias_cache[media_pk]

    @check_login
    def media_delete(self, media_id: str, media_type: str = '') -> bool:
        """Delete media
        Examples:
        https://i.instagram.com/api/v1/media/2277033926878261772_1903424587/delete/?media_type=PHOTO
        https://i.instagram.com/api/v1/media/2354534148830717883_1903424587/delete/?media_type=CAROUSEL
        """
        media_id = self.media_id(media_id)
        result = self.private_request(
            f"media/{media_id}/delete/", self.with_default_data({"media_id": media_id})
        )
        self._medias_cache.pop(self.media_pk(media_id), None)
        return result.get("did_delete")

    @check_login
    def media_edit(self, media_id: str, caption: str, title: str = "", usertags: list = []) -> bool:
        """Edit caption for media
        Example: https://i.instagram.com/api/v1/media/2154602296692269830_1903424587/edit_media/

        Video:
        {
            "caption_text": "Repost",
            "_csrftoken": "H8Rk6Ry2ffWcUSwWIBblVK4hHHII2RMk",
            "usertags": "{\"in\":[]}",
            "_uid": "8530598273",
            "device_id": "android-7d8ad96cc1b71922",
            "_uuid": "c642fece-8663-40d8-8ab7-112df0179e65",
            "is_carousel_bumped_post": "false",
            "container_module": "edit_media_info",
            "feed_position": "0",
            "location": "{}"
        }

        IGTV:
        {
            'igtv_ads_toggled_on': '0',
            'caption_text': 'TEXT',
            '_csrftoken': 'Bavik4rD52i0CvNqV1vDPNHBu4NcHQWB',
            '_uid': '1903424587',
            '_uuid': 'c642fece-8663-40d8-8ab7-112df0179e65',
            'title': 'zr+trip,+crimea,+feb+2017.+Edit+by+@milashensky'
        }
        """
        media_id = self.media_id(media_id)
        media = self.media_info(media_id)  # from cache
        usertags = [
            {"user_id": tag['user']['pk'], "position": tag['position']}
            for tag in usertags
        ]
        data = {
            "caption_text": caption,
            "container_module": "edit_media_info",
            "feed_position": "0",
            "location": "{}",
            "usertags": json.dumps({"in": usertags}),
            "is_carousel_bumped_post": "false",
        }
        if media["product_type"] == "igtv":
            if not title:
                try:
                    title, caption = caption.split("\n", 1)
                except ValueError:
                    title = caption[:75]
            data = {
                "caption_text": caption,
                "title": title,
                "igtv_ads_toggled_on": "0",
            }
        self._medias_cache.pop(self.media_pk(media_id), None)  # clean cache
        result = self.private_request(
            f"media/{media_id}/edit_media/", self.with_default_data(data),
        )
        return result

    def media_user(self, media_pk: int) -> dict:
        """Get user object
        """
        # return extract_user_short(
        #     self._media_info_a1(InstagramIdCodec.encode(media_pk))["owner"]
        # )
        return self.media_info(media_pk)["user"]

    def media_oembed(self, url: str) -> dict:
        """Return info about media and user by post URL
        Example: https://i.instagram.com/api/v1/oembed/?
            url=https://instagram.com/p/B1LbfVPlwIA?
            ig_mid=D68F44BF-2EDC-43AF-BB7F-D693BA0ABF05&
            utm_source=instagramweb
        Result: {
            "version": "1.0",
            "title": "",
            "author_name": "mind__flowers",
            "author_url": "https://www.instagram.com/mind__flowers",
            "author_id": 8572539084,
            "media_id": "2110901750722920960_8572539084",
            "provider_name": "Instagram",
            "provider_url": "https://www.instagram.com",
            "type": "rich",
            "width": 658,
            "height": null,
            "html": '...",
            "thumbnail_width": 640,
            "thumbnail_height": 799,
            "can_view": true,
        }
        """
        return self.private_request(f"oembed?url={url}")

    def media_comments(self, media_id: str) -> list:
        """Get list of comments for media
        Example: https://i.instagram.com/api/v1/media/2277659671519488169_8530598273/comments/?
        inventory_source=media_or_ad&
        analytics_module=comments_v2_feed_timeline&
        can_support_threading=true&
        is_carousel_bumped_post=false&
        feed_position=0
        """
        # TODO: to public or private
        media_id = self.media_id(media_id)
        max_id = None
        comments = []
        while True:
            try:
                result = self.private_request(
                    f"media/{media_id}/comments/", params={"max_id": max_id}
                )
                for comment in result["comments"]:
                    comment["user"] = extract_user_short(comment["user"])
                    comments.append(comment)
                if not result["has_more_comments"]:
                    break
                max_id = result["next_max_id"]
            except ClientNotFoundError as e:
                raise MediaNotFound(e, media_id=media_id, **self.last_json)
            except ClientError as e:
                if "Media not found" in str(e):
                    raise MediaNotFound(e, media_id=media_id, **self.last_json)
                raise e
        return comments

    @check_login
    def media_comment(self, media_id: str, text: str) -> int:
        """Comment media
        Example: {
            "user_breadcrumb": "u3QwgWYbhXMTf7nKhvpBYMyWxI9IScUmtUJ69TeTVwY=\nNCAxNDg5IDAgMTU4NjE5Mjg3MzI4NA==\n",
            "delivery_class": "organic",
            "idempotence_token": "9d68650c-bb63-4c09-a367-53d0bc177de4",
            "_csrftoken": "H8Rk6Ry2ffWcUSwWIBblVK4hHHII2RMk",
            "radio_type": "wifi-none",
            "_uid": "8530598273",
            "_uuid": "c642fece-8663-40d8-8ab7-112df0179e65",
            "comment_text": "Test",
            "is_carousel_bumped_post": "false",
            "container_module": "self_comments_v2_feed_contextual_self_profile",
            "feed_position": "0"
        }
        """
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
        comment = result["comment"]
        comment["user"] = extract_user_short(comment["user"])
        return comment
