import json
import random
import shutil
import time
from pathlib import Path
from typing import Dict, List
from urllib.parse import urlparse
from uuid import uuid4

import requests

from instagrapi import config
from instagrapi.exceptions import (
    PhotoConfigureError,
    PhotoConfigureStoryError,
    PhotoNotUpload,
)
from instagrapi.extractors import extract_media_v1
from instagrapi.types import (
    Location,
    Media,
    Story,
    StoryHashtag,
    StoryLink,
    StoryLocation,
    StoryMention,
    StorySticker,
    Usertag,
)
from instagrapi.utils import dumps

try:
    from PIL import Image
except ImportError:
    raise Exception("You don't have PIL installed. Please install PIL or Pillow>=8.1.1")


class DownloadPhotoMixin:
    """
    Helpers for downloading photo
    """

    def photo_download(self, media_pk: int, folder: Path = "") -> Path:
        """
        Download photo using media pk

        Parameters
        ----------
        media_pk: int
            Unique Media ID
        folder: Path, optional
            Directory in which you want to download the album, default is "" and will download the files to working
                directory

        Returns
        -------
        Path
            Path for the file downloaded
        """
        media = self.media_info(media_pk)
        assert media.media_type == 1, "Must been photo"
        filename = "{username}_{media_pk}".format(
            username=media.user.username, media_pk=media_pk
        )
        return self.photo_download_by_url(media.thumbnail_url, filename, folder)

    def photo_download_by_url(
        self, url: str, filename: str = "", folder: Path = ""
    ) -> Path:
        """
        Download photo using URL

        Parameters
        ----------
        url: str
            URL for a media
        filename: str, optional
            Filename for the media
        folder: Path, optional
            Directory in which you want to download the album, default is "" and will download the files to working
                directory

        Returns
        -------
        Path
            Path for the file downloaded
        """
        fname = urlparse(url).path.rsplit("/", 1)[1]
        filename = "%s.%s" % (filename, fname.rsplit(".", 1)[1]) if filename else fname
        path = Path(folder) / filename
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(path, "wb") as f:
            response.raw.decode_content = True
            shutil.copyfileobj(response.raw, f)
        return path.resolve()


class UploadPhotoMixin:
    """
    Helpers for downloading photo
    """

    def photo_rupload(
        self, path: Path, upload_id: str = "", to_album: bool = False
    ) -> tuple:
        """
        Upload photo to Instagram

        Parameters
        ----------
        path: Path
            Path to the media
        upload_id: str, optional
            Unique upload_id (String). When None, then generate automatically. Example from video.video_configure
        to_album: bool, optional

        Returns
        -------
        tuple
            (Upload ID for the media, width, height)
        """
        assert isinstance(path, Path), f"Path must been Path, now {path} ({type(path)})"
        upload_id = upload_id or str(int(time.time() * 1000))
        assert path, "Not specified path to photo"
        waterfall_id = str(uuid4())
        # upload_name example: '1576102477530_0_7823256191'
        upload_name = "{upload_id}_0_{rand}".format(
            upload_id=upload_id, rand=random.randint(1000000000, 9999999999)
        )
        # media_type: "2" when from video/igtv/album thumbnail, "1" - upload photo only
        rupload_params = {
            "retry_context": '{"num_step_auto_retry":0,"num_reupload":0,"num_step_manual_retry":0}',
            "media_type": "1",  # "2" if upload_id else "1",
            "xsharing_user_ids": "[]",
            "upload_id": upload_id,
            "image_compression": json.dumps(
                {"lib_name": "moz", "lib_version": "3.1.m", "quality": "80"}
            ),
        }
        if to_album:
            rupload_params["is_sidecar"] = "1"
        with open(path, "rb") as fp:
            photo_data = fp.read()
            photo_len = str(len(photo_data))
        headers = {
            "Accept-Encoding": "gzip",
            "X-Instagram-Rupload-Params": json.dumps(rupload_params),
            "X_FB_PHOTO_WATERFALL_ID": waterfall_id,
            "X-Entity-Type": "image/jpeg",
            "Offset": "0",
            "X-Entity-Name": upload_name,
            "X-Entity-Length": photo_len,
            "Content-Type": "application/octet-stream",
            "Content-Length": photo_len,
        }
        response = self.private.post(
            "https://{domain}/rupload_igphoto/{name}".format(
                domain=config.API_DOMAIN, name=upload_name
            ),
            data=photo_data,
            headers=headers,
        )
        self.request_log(response)
        if response.status_code != 200:
            self.logger.error(
                "Photo Upload failed with the following response: %s", response
            )
            last_json = self.last_json  # local variable for read in sentry
            raise PhotoNotUpload(response.text, response=response, **last_json)
        with Image.open(path) as im:
            width, height = im.size
        return upload_id, width, height

    def photo_upload(
        self,
        path: Path,
        caption: str,
        upload_id: str = "",
        usertags: List[Usertag] = [],
        location: Location = None,
    ) -> Media:
        """
        Upload photo and configure to feed

        Parameters
        ----------
        path: Path
            Path to the media
        caption: str
            Media caption
        upload_id: str, optional
            Unique upload_id (String). When None, then generate automatically. Example from video.video_configure
        usertags: List[Usertag], optional
            List of users to be tagged on this upload, default is empty list.
        location: Location, optional
            Location tag for this upload, default is None

        Returns
        -------
        Media
            An object of Media class
        """
        path = Path(path)
        upload_id, width, height = self.photo_rupload(path, upload_id)
        for attempt in range(10):
            self.logger.debug(f"Attempt #{attempt} to configure Photo: {path}")
            time.sleep(3)
            if self.photo_configure(
                upload_id, width, height, caption, usertags, location,
            ):
                media = self.last_json.get("media")
                self.expose()
                return extract_media_v1(media)
        raise PhotoConfigureError(
            response=self.last_response, **self.last_json
        )

    def photo_configure(
        self,
        upload_id: str,
        width: int,
        height: int,
        caption: str,
        usertags: List[Usertag] = [],
        location: Location = None,
    ) -> Dict:
        """
        Post Configure Photo (send caption to Instagram)

        Parameters
        ----------
        upload_id: str
            Unique upload_id
        width: int
            Width of the video in pixels
        height: int
            Height of the video in pixels
        caption: str
            Media caption
        usertags: List[Usertag], optional
            List of users to be tagged on this upload, default is empty list.
        location: Location, optional
            Location tag for this upload, default is None

        Returns
        -------
        Dict
            A dictionary of response from the call
        """
        usertags = [
            {"user_id": tag.user.pk, "position": [tag.x, tag.y]} for tag in usertags
        ]
        data = {
            "timezone_offset": "10800",
            "creation_logger_session_id": self.client_session_id,
            "multi_sharing": "1",
            "location": self.location_build(location),
            "media_folder": "Camera",
            "source_type": "4",
            "caption": caption,
            "upload_id": upload_id,
            "device": self.device,
            "usertags": json.dumps({"in": usertags}),
            "edits": {
                "crop_original_size": [width * 1.0, height * 1.0],
                "crop_center": [0.0, 0.0],
                "crop_zoom": 1.0,
            },
            "extra": {"source_width": width, "source_height": height},
        }
        return self.private_request("media/configure/", self.with_default_data(data))

    def photo_upload_to_story(
        self,
        path: Path,
        caption: str,
        upload_id: str = "",
        mentions: List[StoryMention] = [],
        locations: List[StoryLocation] = [],
        links: List[StoryLink] = [],
        hashtags: List[StoryHashtag] = [],
        stickers: List[StorySticker] = [],
    ) -> Story:
        """
        Upload photo as a story and configure it

        Parameters
        ----------
        path: Path
            Path to the media
        caption: str
            Media caption
        upload_id: str, optional
            Unique upload_id (String). When None, then generate automatically. Example from video.video_configure
        mentions: List[StoryMention], optional
            List of mentions to be tagged on this upload, default is empty list.
        locations: List[StoryLocation], optional
            List of locations to be tagged on this upload, default is empty list.
        links: List[StoryLink]
            URLs for Swipe Up
        hashtags: List[StoryHashtag], optional
            List of hashtags to be tagged on this upload, default is empty list.
        stickers: List[StorySticker], optional
            List of stickers to be tagged on this upload, default is empty list.

        Returns
        -------
        Story
            An object of Media class
        """
        path = Path(path)
        upload_id, width, height = self.photo_rupload(path, upload_id)
        for attempt in range(10):
            self.logger.debug(f"Attempt #{attempt} to configure Photo: {path}")
            time.sleep(3)
            if self.photo_configure_to_story(
                upload_id,
                width,
                height,
                caption,
                mentions,
                locations,
                links,
                hashtags,
                stickers,
            ):
                media = self.last_json.get("media")
                self.expose()
                return Story(
                    links=links,
                    mentions=mentions,
                    hashtags=hashtags,
                    locations=locations,
                    stickers=stickers,
                    **extract_media_v1(media).dict()
                )
        raise PhotoConfigureStoryError(
            response=self.last_response, **self.last_json
        )

    def photo_configure_to_story(
        self,
        upload_id: str,
        width: int,
        height: int,
        caption: str,
        mentions: List[StoryMention] = [],
        locations: List[StoryLocation] = [],
        links: List[StoryLink] = [],
        hashtags: List[StoryHashtag] = [],
        stickers: List[StorySticker] = [],
        extra_data: Dict[str, str] = {},
    ) -> Dict:
        """
        Post configure photo

        Parameters
        ----------
        upload_id: str
            Unique upload_id
        width: int
            Width of the video in pixels
        height: int
            Height of the video in pixels
        caption: str
            Media caption
        mentions: List[StoryMention], optional
            List of mentions to be tagged on this upload, default is empty list.
        locations: List[StoryLocation], optional
            List of locations to be tagged on this upload, default is empty list.
        links: List[StoryLink]
            URLs for Swipe Up
        hashtags: List[StoryHashtag], optional
            List of hashtags to be tagged on this upload, default is empty list.
        stickers: List[StorySticker], optional
            List of stickers to be tagged on this upload, default is empty list.
        extra_data: List[str, str], optional
            Dict of extra data, if you need to add your params, like {"share_to_facebook": 1}.

        Returns
        -------
        Dict
            A dictionary of response from the call
        """
        timestamp = int(time.time())
        story_sticker_ids = []
        data = {
            "text_metadata": '[{"font_size":40.0,"scale":1.0,"width":611.0,"height":169.0,"x":0.51414347,"y":0.8487708,"rotation":0.0}]',
            "supported_capabilities_new": json.dumps(config.SUPPORTED_CAPABILITIES),
            "has_original_sound": "1",
            "camera_session_id": self.client_session_id,
            "scene_capture_type": "",
            "timezone_offset": "10800",
            "client_shared_at": str(timestamp - 5),  # 5 seconds ago
            "story_sticker_ids": "",
            "media_folder": "Camera",
            "configure_mode": "1",
            "source_type": "4",
            "creation_surface": "camera",
            "imported_taken_at": (timestamp - 3 * 24 * 3600),  # 3 days ago
            "caption": caption,
            "capture_type": "normal",
            "rich_text_format_types": '["default"]',
            "upload_id": upload_id,
            "client_timestamp": str(timestamp),
            "device": self.device,
            "edits": {
                "crop_original_size": [width * 1.0, height * 1.0],
                "crop_center": [0.0, 0.0],
                "crop_zoom": 1.0,
            },
            "extra": {"source_width": width, "source_height": height},
        }
        data.update(extra_data)
        if links:
            links = [link.dict() for link in links]
            data["story_cta"] = dumps([{"links": links}])
        tap_models = []
        static_models = []
        if mentions:
            reel_mentions = [
                {
                    "x": 0.5002546,
                    "y": 0.8583542,
                    "z": 0,
                    "width": 0.4712963,
                    "height": 0.0703125,
                    "rotation": 0.0,
                    "type": "mention",
                    "user_id": str(mention.user.pk),
                    "is_sticker": False,
                    "display_type": "mention_username",
                }
                for mention in mentions
            ]
            data["reel_mentions"] = json.dumps(reel_mentions)
            tap_models.extend(reel_mentions)
        if hashtags:
            story_sticker_ids.append("hashtag_sticker")
            for mention in hashtags:
                item = {
                    "x": mention.x,
                    "y": mention.y,
                    "z": 0,
                    "width": mention.width,
                    "height": mention.height,
                    "rotation": 0.0,
                    "type": "hashtag",
                    "tag_name": mention.hashtag.name,
                    "is_sticker": True,
                    "tap_state": 0,
                    "tap_state_str_id": "hashtag_sticker_gradient"
                }
                tap_models.append(item)
        if locations:
            story_sticker_ids.append("location_sticker")
            for mention in locations:
                mention.location = self.location_complete(mention.location)
                item = {
                    "x": mention.x,
                    "y": mention.y,
                    "z": 0,
                    "width": mention.width,
                    "height": mention.height,
                    "rotation": 0.0,
                    "type": "location",
                    "location_id": str(mention.location.pk),
                    "is_sticker": True,
                    "tap_state": 0,
                    "tap_state_str_id": "location_sticker_vibrant"
                }
                tap_models.append(item)
        if stickers:
            for sticker in stickers:
                str_id = sticker.id  # "gif_Igjf05J559JWuef4N5"
                static_models.append({
                    "x": sticker.x,
                    "y": sticker.y,
                    "z": sticker.z,
                    "width": sticker.width,
                    "height": sticker.height,
                    "rotation": sticker.rotation,
                    "str_id": str_id,
                    "sticker_type": sticker.type,
                })
                story_sticker_ids.append(str_id)
                if sticker.type == "gif":
                    data["has_animated_sticker"] = "1"
        data["tap_models"] = dumps(tap_models)
        data["static_models"] = dumps(static_models)
        data["story_sticker_ids"] = dumps(story_sticker_ids)
        return self.private_request(
            "media/configure_to_story/", self.with_default_data(data)
        )
