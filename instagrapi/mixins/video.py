import random
import time
from pathlib import Path
from typing import Dict, List
from urllib.parse import urlparse
from uuid import uuid4

import requests

from instagrapi import config
from instagrapi.exceptions import (
    VideoConfigureError,
    VideoConfigureStoryError,
    VideoNotDownload,
    VideoNotUpload,
)
from instagrapi.extractors import extract_direct_message, extract_media_v1
from instagrapi.types import (
    DirectMessage,
    Location,
    Media,
    Story,
    StoryHashtag,
    StoryLink,
    StoryLocation,
    StoryMedia,
    StoryMention,
    StorySticker,
    Usertag,
)
from instagrapi.utils import date_time_original, dumps


class DownloadVideoMixin:
    """
    Helpers for downloading video
    """

    def video_download(self, media_pk: int, folder: Path = "") -> Path:
        """
        Download video using media pk

        Parameters
        ----------
        media_pk: int
            Unique Media ID
        folder: Path, optional
            Directory in which you want to download the video, default is "" and will download the files to working dir.

        Returns
        -------
        Path
            Path for the file downloaded
        """
        media = self.media_info(media_pk)
        assert media.media_type == 2, "Must been video"
        filename = "{username}_{media_pk}".format(
            username=media.user.username, media_pk=media_pk
        )
        return self.video_download_by_url(media.video_url, filename, folder)

    def video_download_by_url(
        self, url: str, filename: str = "", folder: Path = ""
    ) -> Path:
        """
        Download video using URL

        Parameters
        ----------
        url: str
            URL for a media
        filename: str, optional
            Filename for the media
        folder: Path, optional
            Directory in which you want to download the video, default is "" and will download the files to working
                directory

        Returns
        -------
        Path
            Path for the file downloaded
        """
        url = str(url)
        fname = urlparse(url).path.rsplit("/", 1)[1]
        filename = "%s.%s" % (filename, fname.rsplit(".", 1)[1]) if filename else fname
        path = Path(folder) / filename
        response = requests.get(url, stream=True, timeout=self.request_timeout)
        response.raise_for_status()
        try:
            content_length = int(response.headers.get("Content-Length"))
        except TypeError:
            print(
                """
                The program detected an mis-formatted link, and hence can't download it.
                This problem occurs when the URL is passed into
                    'video_download_by_url()' or the 'clip_download_by_url()'.
                The raw URL needs to be re-formatted into one that is recognizable by the methods.
                Use this code: url=self.cl.media_info(self.cl.media_pk_from_url('insert the url here')).video_url
                You can remove the 'self' from the code above if needed.
                """
            )
            raise Exception("The program detected an mis-formatted link.")
        file_length = len(response.content)
        if content_length != file_length:
            raise VideoNotDownload(
                f'Broken file "{path}" (Content-length={content_length}, but file length={file_length})'
            )
        with open(path, "wb") as f:
            f.write(response.content)
            f.close()
        return path.resolve()

    def video_download_by_url_origin(self, url: str) -> bytes:
        """
        Download video using URL

        Parameters
        ----------
        url: str
            URL for a media

        Returns
        -------
        bytes
            Bytes for the file downloaded
        """
        response = requests.get(url, stream=True, timeout=self.request_timeout)
        response.raise_for_status()
        content_length = int(response.headers.get("Content-Length"))
        file_length = len(response.content)
        if content_length != file_length:
            raise VideoNotDownload(
                f'Broken file from url "{url}" (Content-length={content_length}, but file length={file_length})'
            )
        return response.content


class UploadVideoMixin:
    """
    Helpers for downloading video
    """

    def video_rupload(
        self,
        path: Path,
        thumbnail: Path = None,
        to_album: bool = False,
        to_story: bool = False,
        to_direct: bool = False,
    ) -> tuple:
        """
        Upload video to Instagram

        Parameters
        ----------
        path: Path
            Path to the media
        thumbnail: str
            Path to thumbnail for video. When None, then thumbnail is generate automatically
        to_album: bool, optional
        to_story: bool, optional
        to_direct: bool, optional

        Returns
        -------
        tuple
            (Upload ID for the media, width, height)
        """
        assert isinstance(path, Path), f"Path must been Path, now {path} ({type(path)})"
        upload_id = str(int(time.time() * 1000))
        width, height, duration, thumbnail = analyze_video(path, thumbnail)
        waterfall_id = str(uuid4())
        # upload_name example: '1576102477530_0_7823256191'
        upload_name = "{upload_id}_0_{rand}".format(
            upload_id=upload_id, rand=random.randint(1000000000, 9999999999)
        )
        rupload_params = {
            "retry_context": '{"num_step_auto_retry":0,"num_reupload":0,"num_step_manual_retry":0}',
            "media_type": "2",
            "xsharing_user_ids": dumps([self.user_id]),
            "upload_id": upload_id,
            "upload_media_duration_ms": str(int(duration * 1000)),
            "upload_media_width": str(width),
            "upload_media_height": str(height),  # "1138" for Mi5s
        }
        if to_direct:
            rupload_params["direct_v2"] = "1"
            # "hflip": "false",
            # "rotate":"3",
        if to_album:
            rupload_params["is_sidecar"] = "1"
        if to_story:
            rupload_params = {
                "extract_cover_frame": "1",
                "content_tags": "has-overlay",
                "for_album": "1",
                **rupload_params,
            }
        headers = {
            "Accept-Encoding": "gzip, deflate",
            "X-Instagram-Rupload-Params": dumps(rupload_params),
            "X_FB_VIDEO_WATERFALL_ID": waterfall_id,
            # "X_FB_VIDEO_WATERFALL_ID": "88732215909430_55CF262450C9_Mixed_0",  # ALBUM
            # "X_FB_VIDEO_WATERFALL_ID": "1594919079102",  # VIDEO
        }
        if to_album:
            headers = {"Segment-Start-Offset": "0", "Segment-Type": "3", **headers}
        response = self.private.get(
            "https://{domain}/rupload_igvideo/{name}".format(
                domain=config.API_DOMAIN, name=upload_name
            ),
            headers=headers,
        )
        self.request_log(response)
        if response.status_code != 200:
            raise VideoNotUpload(response.text, response=response, **self.last_json)
        with open(path, "rb") as fp:
            video_data = fp.read()
            video_len = str(len(video_data))
        headers = {
            "Offset": "0",
            "X-Entity-Name": upload_name,
            "X-Entity-Length": video_len,
            "Content-Type": "application/octet-stream",
            "Content-Length": video_len,
            "X-Entity-Type": "video/mp4",
            **headers,
        }
        response = self.private.post(
            "https://{domain}/rupload_igvideo/{name}".format(
                domain=config.API_DOMAIN, name=upload_name
            ),
            data=video_data,
            headers=headers,
        )
        self.request_log(response)
        if response.status_code != 200:
            raise VideoNotUpload(response.text, response=response, **self.last_json)
        return upload_id, width, height, duration, Path(thumbnail)

    def video_upload(
        self,
        path: Path,
        caption: str,
        thumbnail: Path = None,
        usertags: List[Usertag] = [],
        location: Location = None,
        extra_data: Dict[str, str] = {},
    ) -> Media:
        """
        Upload video and configure to feed

        Parameters
        ----------
        path: Path
            Path to the media
        caption: str
            Media caption
        thumbnail: str
            Path to thumbnail for video. When None, then thumbnail is generate automatically
        usertags: List[Usertag], optional
            List of users to be tagged on this upload, default is empty list.
        location: Location, optional
            Location tag for this upload, default is None
        extra_data: Dict[str, str], optional
            Dict of extra data, if you need to add your params, like {"share_to_facebook": 1}.

        Returns
        -------
        Media
            An object of Media class
        """
        path = Path(path)
        if thumbnail is not None:
            thumbnail = Path(thumbnail)
        upload_id, width, height, duration, thumbnail = self.video_rupload(
            path, thumbnail, to_story=False
        )
        for attempt in range(50):
            self.logger.debug(f"Attempt #{attempt} to configure Video: {path}")
            time.sleep(3)
            try:
                configured = self.video_configure(
                    upload_id,
                    width,
                    height,
                    duration,
                    thumbnail,
                    caption,
                    usertags,
                    location,
                    extra_data=extra_data,
                )
            except Exception as e:
                if "Transcode not finished yet" in str(e):
                    """
                    Response 202 status:
                    {"message": "Transcode not finished yet.", "status": "fail"}
                    """
                    time.sleep(10)
                    continue
                raise e
            else:
                if configured:
                    media = configured.get("media")
                    self.expose()
                    return extract_media_v1(media)
        raise VideoConfigureError(response=self.last_response, **self.last_json)

    def video_configure(
        self,
        upload_id: str,
        width: int,
        height: int,
        duration: int,
        thumbnail: Path,
        caption: str,
        usertags: List[Usertag] = [],
        location: Location = None,
        extra_data: Dict[str, str] = {},
    ) -> Dict:
        """
        Post Configure Video (send caption, thumbnail and more to Instagram)

        Parameters
        ----------
        upload_id: str
            Unique upload_id
        width: int
            Width of the video in pixels
        height: int
            Height of the video in pixels
        duration: int
            Duration of the video in seconds
        thumbnail: str
            Path to thumbnail for video. When None, then thumbnail is generate automatically
        caption: str
            Media caption
        usertags: List[Usertag], optional
            List of users to be tagged on this upload, default is empty list.
        location: Location, optional
            Location tag for this upload, default is None
        extra_data: Dict[str, str], optional
            Dict of extra data, if you need to add your params, like {"share_to_facebook": 1}.

        Returns
        -------
        Dict
            A dictionary of response from the call
        """
        self.photo_rupload(Path(thumbnail), upload_id)
        usertags = [
            {"user_id": tag.user.pk, "position": [tag.x, tag.y]} for tag in usertags
        ]
        data = {
            "multi_sharing": "1",
            "creation_logger_session_id": self.client_session_id,
            "upload_id": upload_id,
            "source_type": "4",
            "location": self.location_build(location),
            "poster_frame_index": 0,
            "length": duration,
            "audio_muted": False,
            "usertags": dumps({"in": usertags}),
            "filter_type": "0",
            "date_time_original": date_time_original(time.localtime()),
            "timezone_offset": str(self.timezone_offset),
            "clips": [{"length": duration, "source_type": "4"}],
            "extra": {"source_width": width, "source_height": height},
            "device": self.device,
            "caption": caption,
            **extra_data,
        }
        return self.private_request(
            "media/configure/?video=1", self.with_default_data(data)
        )

    def video_upload_to_story(
        self,
        path: Path,
        caption: str = "",
        thumbnail: Path = None,
        mentions: List[StoryMention] = [],
        locations: List[StoryLocation] = [],
        links: List[StoryLink] = [],
        hashtags: List[StoryHashtag] = [],
        stickers: List[StorySticker] = [],
        medias: List[StoryMedia] = [],
        extra_data: Dict[str, str] = {},
    ) -> Story:
        """
        Upload video as a story and configure it

        Parameters
        ----------
        path: Path
            Path to the media
        caption: str
            Story caption
        thumbnail: str
            Path to thumbnail for video. When None, then thumbnail is generate automatically
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
        medias: List[StoryMedia], optional
            List of medias to be tagged on this upload, default is empty list.
        extra_data: Dict[str, str], optional
            Dict of extra data, if you need to add your params, like {"share_to_facebook": 1}.

        Returns
        -------
        Story
            An object of Media class
        """
        path = Path(path)
        if thumbnail is not None:
            thumbnail = Path(thumbnail)
        upload_id, width, height, duration, thumbnail = self.video_rupload(
            path, thumbnail, to_story=True
        )
        for attempt in range(50):
            self.logger.debug(f"Attempt #{attempt} to configure Video: {path}")
            time.sleep(3)
            try:
                configured = self.video_configure_to_story(
                    upload_id,
                    width,
                    height,
                    duration,
                    thumbnail,
                    caption,
                    mentions,
                    locations,
                    links,
                    hashtags,
                    stickers,
                    medias,
                    extra_data=extra_data,
                )
            except Exception as e:
                if "Transcode not finished yet" in str(e):
                    """
                    Response 202 status:
                    {"message": "Transcode not finished yet.", "status": "fail"}
                    """
                    time.sleep(10)
                    continue
                raise e
            if configured:
                media = configured.get("media")
                self.expose()
                return Story(
                    links=links,
                    mentions=mentions,
                    hashtags=hashtags,
                    locations=locations,
                    stickers=stickers,
                    medias=medias,
                    **extract_media_v1(media).dict(),
                )
        raise VideoConfigureStoryError(response=self.last_response, **self.last_json)

    def video_configure_to_story(
        self,
        upload_id: str,
        width: int,
        height: int,
        duration: int,
        thumbnail: Path,
        caption: str,
        mentions: List[StoryMention] = [],
        locations: List[StoryLocation] = [],
        links: List[StoryLink] = [],
        hashtags: List[StoryHashtag] = [],
        stickers: List[StorySticker] = [],
        medias: List[StoryMedia] = [],
        thread_ids: List[int] = [],
        extra_data: Dict[str, str] = {},
    ) -> Dict:
        """
        Story Configure for Photo

        Parameters
        ----------
        upload_id: str
            Unique upload_id
        width: int
            Width of the video in pixels
        height: int
            Height of the video in pixels
        duration: int
            Duration of the video in seconds
        thumbnail: str
            Path to thumbnail for video. When None, then thumbnail is generate automatically
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
        medias: List[StoryMedia], optional
            List of medias to be tagged on this upload, default is empty list.
        thread_ids: List[int], optional
            List of Direct Message Thread ID (to send a story to a thread)
        extra_data: Dict[str, str], optional
            Dict of extra data, if you need to add your params, like {"share_to_facebook": 1}.

        Returns
        -------
        Dict
            A dictionary of response from the call
        """
        timestamp = int(time.time())
        mentions = mentions.copy()
        locations = locations.copy()
        links = links.copy()
        hashtags = hashtags.copy()
        stickers = stickers.copy()
        medias = medias.copy()
        thread_ids = thread_ids.copy()
        story_sticker_ids = []
        data = {
            # USE extra_data TO EXTEND THE SETTINGS OF THE LOADED STORY,
            #   USE FOR EXAMPLE THE PROPERTIES SPECIFIED IN THE COMMENT:
            # ---------------------------------
            # When send to DIRECT:
            # "allow_multi_configures": "1",
            # "client_context":"6823316152962778207",
            #      ^----- token = random.randint(6800011111111111111, 6800099999999999999) from direct.py
            # "is_shh_mode":"0",
            # "mutation_token":"6824688191453546273",
            # "nav_chain":"1qT:feed_timeline:1,1qT:feed_timeline:7,ReelViewerFragment:reel_feed_timeline:21,5HT:attribution_quick_camera_fragment:22,4ji:reel_composer_preview:23,8wg:direct_story_audience_picker:24,4ij:reel_composer_camera:25,ReelViewerFragment:reel_feed_timeline:26",
            # "recipient_users":"[]",
            # "send_attribution":"direct_story_audience_picker",
            # "thread_ids":"[\"340282366841710300949128149448121770626\"]",  <-- send story to direct
            # "view_mode": "replayable",
            # ---------------------------------
            # Optional (markup for caption field) when tagging:
            # "story_captions":"[{\"text\":\"@user1+\\n\\n@user2+\",\"position_data\":{\"x\":0.5,\"y\":0.5,\"height\":272.0,\"width\":670.0,\"rotation\":0.0},\"scale\":1.0,\"font_size\":24.0,\"format_type\":\"classic_v2\",\"effects\":[\"disabled\"],\"colors\":[\"#ffffff\"],\"alignment\":\"center\",\"animation\":\"\"}]",
            # ---------------------------------
            # SEGMENT MODE (when file is too big):
            # "allow_multi_configures": "1",
            # "segmented_video_group_id": str(uuid4()),
            # "multi_upload_session_id": str(uuid4()),
            # "segmented_video_count": "4",  # "4"  # SEGMENT MODE
            # "segmented_video_index": "0",  # 0,1,2,3  # SEGMENT MODE
            # "is_multi_upload": "1",  # SEGMENT MODE
            # "is_segmented_video": "1",  # SEGMENT MODE
            # ---------------------------------
            # COMMON properties:
            "_uid": str(self.user_id),
            "supported_capabilities_new": dumps(config.SUPPORTED_CAPABILITIES),
            "has_original_sound": "1",
            "filter_type": "0",
            "camera_session_id": self.client_session_id,
            "camera_entry_point": str(random.randint(35, 164)),
            "composition_id": self.generate_uuid(),
            # "camera_make": self.device_settings.get("manufacturer", "Xiaomi"),
            # "camera_model": self.device_settings.get("model", "MI+5s"),
            "timezone_offset": str(self.timezone_offset),
            "client_timestamp": str(timestamp),
            "client_shared_at": str(timestamp - 7),  # 7 seconds ago
            # "imported_taken_at": str(timestamp - 5 * 24 * 3600),  # 5 days ago
            "date_time_original": date_time_original(time.localtime()),
            # "date_time_digitalized": date_time_original(time.localtime()),
            # "story_sticker_ids": "",
            # "media_folder": "Camera",
            "configure_mode": "1",
            # "configure_mode": "2", <- when direct
            "source_type": "3",  # "3"
            "video_result": "",
            "creation_surface": "camera",
            # "software": config.SOFTWARE.format(**self.device_settings),
            # "caption": caption,
            "capture_type": "normal",
            # "rich_text_format_types": '["classic_v2"]',  # default, typewriter
            "upload_id": upload_id,
            # "scene_capture_type": "standard",
            # "scene_type": "",
            "original_media_type": "video",
            "camera_position": "back",
            # Facebook Sharing Part:
            # "xpost_surface": "auto_xpost",
            # "share_to_fb_destination_type": "USER",
            # "share_to_fb_destination_id":"832928543",
            # "share_to_facebook":"1",
            # "fb_access_token":"EAABwzLixnjYBACVgqBfLyDuPWs6RN2sTZC........cnNkjHCH2",
            # "attempt_id": str(uuid4()),
            "device": self.device,
            "length": duration,
            "clips": [
                {"length": duration, "source_type": "3", "camera_position": "back"}
            ],
            # "edits": {
            #     "filter_type": 0,
            #     "filter_strength": 1.0,
            #     "crop_original_size": [width, height],
            #     # "crop_center": [0, 0],
            #     # "crop_zoom": 1
            # },
            "media_transformation_info": dumps(
                {
                    "width": str(width),
                    "height": str(height),
                    "x_transform": "0",
                    "y_transform": "0",
                    "zoom": "1.0",
                    "rotation": "0.0",
                    "background_coverage": "0.0",
                }
            ),
            "extra": {"source_width": width, "source_height": height},
            "audio_muted": False,
            "poster_frame_index": 0,
            # "app_attribution_android_namespace": "",
        }
        data.update(extra_data)
        tap_models = []
        static_models = []
        if mentions:
            reel_mentions = []
            text_metadata = []
            for mention in mentions:
                reel_mentions.append(
                    {
                        "x": mention.x,
                        "y": mention.y,
                        "z": 0,
                        "width": mention.width,
                        "height": mention.height,
                        "rotation": 0.0,
                        "type": "mention",
                        "user_id": str(mention.user.pk),
                        "is_sticker": False,
                        "display_type": "mention_username",
                        "tap_state": 0,
                        "tap_state_str_id": "mention_text",
                    }
                )
                text_metadata.append(
                    {
                        "font_size": 24.0,
                        "scale": 1.0,
                        "width": 366.0,
                        "height": 102.0,
                        "x": mention.x,
                        "y": mention.y,
                        "rotation": 0.0,
                    }
                )
            data["text_metadata"] = dumps(text_metadata)
            # data["reel_mentions"] = dumps(reel_mentions)
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
                    "tap_state_str_id": "hashtag_sticker_gradient",
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
                    "tap_state_str_id": "location_sticker_vibrant",
                }
                tap_models.append(item)
        if links:
            # instagram allow one link now
            link = links[0]
            self.private_request(
                "media/validate_reel_url/",
                {
                    "url": str(link.webUri),
                    "_uid": str(self.user_id),
                    "_uuid": str(self.uuid),
                },
            )
            stickers.append(
                StorySticker(
                    type="story_link",
                    x=link.x,
                    y=link.y,
                    z=link.z,
                    width=link.width,
                    height=link.height,
                    rotation=link.rotation,
                    extra=dict(
                        link_type="web",
                        url=str(link.webUri),
                        tap_state_str_id="link_sticker_default",
                    ),
                )
            )
            story_sticker_ids.append("link_sticker_default")
        if stickers:
            for sticker in stickers:
                sticker_extra = sticker.extra or {}
                if sticker.id:
                    sticker_extra["str_id"] = sticker.id
                    story_sticker_ids.append(sticker.id)
                tap_models.append(
                    {
                        "x": round(sticker.x, 7),
                        "y": round(sticker.y, 7),
                        "z": sticker.z,
                        "width": round(sticker.width, 7),
                        "height": round(sticker.height, 7),
                        "rotation": sticker.rotation,
                        "type": sticker.type,
                        "is_sticker": True,
                        "selected_index": 0,
                        "tap_state": 0,
                        **sticker_extra,
                    }
                )
                if sticker.type == "gif":
                    data["has_animated_sticker"] = "1"
        if medias:
            for feed_media in medias:
                assert feed_media.media_pk, "Required StoryMedia.media_pk"
                # if not feed_media.user_id:
                #     user = self.media_user(feed_media.media_pk)
                #     feed_media.user_id = user.pk
                item = {
                    "x": feed_media.x,
                    "y": feed_media.y,
                    "z": feed_media.z,
                    "width": feed_media.width,
                    "height": feed_media.height,
                    "rotation": feed_media.rotation,
                    "type": "feed_media",
                    "media_id": str(feed_media.media_pk),
                    "media_owner_id": str(feed_media.user_id or ""),
                    "product_type": "feed",
                    "is_sticker": True,
                    "tap_state": 0,
                    "tap_state_str_id": "feed_post_sticker_square",
                }
                tap_models.append(item)
            data["reshared_media_id"] = str(feed_media.media_pk)
        if thread_ids:
            # Send to direct thread
            token = self.generate_mutation_token()
            data.update(
                {
                    "configure_mode": "2",
                    "allow_multi_configures": "1",
                    "client_context": token,
                    "is_shh_mode": "0",
                    "mutation_token": token,
                    "nav_chain": (
                        "1qT:feed_timeline:1,1qT:feed_timeline:7,ReelViewerFragment:reel_feed_timeline:21,"
                        "5HT:attribution_quick_camera_fragment:22,4ji:reel_composer_preview:23,"
                        "8wg:direct_story_audience_picker:24,4ij:reel_composer_camera:25,"
                        "ReelViewerFragment:reel_feed_timeline:26"
                    ),
                    "recipient_users": "[]",
                    "send_attribution": "direct_story_audience_picker",
                    "thread_ids": dumps([str(tid) for tid in thread_ids]),
                    "view_mode": "replayable",
                }
            )
        if tap_models:
            data["tap_models"] = dumps(tap_models)
        if static_models:
            data["static_models"] = dumps(static_models)
        if story_sticker_ids:
            data["story_sticker_ids"] = story_sticker_ids[0]
        return self.private_request(
            "media/configure_to_story/?video=1", self.with_default_data(data)
        )

    def video_upload_to_direct(
        self,
        path: Path,
        caption: str = "",
        thumbnail: Path = None,
        mentions: List[StoryMention] = [],
        medias: List[StoryMedia] = [],
        thread_ids: List[int] = [],
        extra_data: Dict[str, str] = {},
    ) -> DirectMessage:
        """
        Upload video to direct thread as a story and configure it

        Parameters
        ----------
        path: Path
            Path to the media
        caption: str
            Story caption
        thumbnail: str
            Path to thumbnail for video. When None, then thumbnail is generate automatically
        mentions: List[StoryMention], optional
            List of mentions to be tagged on this upload, default is empty list.
        thread_ids: List[int], optional
            List of Direct Message Thread ID (to send a story to a thread)
        extra_data: List[str, str], optional
            Dict of extra data, if you need to add your params, like {"share_to_facebook": 1}.

        Returns
        -------
        DirectMessage
            An object of DirectMessage class
        """
        path = Path(path)
        if thumbnail is not None:
            thumbnail = Path(thumbnail)
        upload_id, width, height, duration, thumbnail = self.video_rupload(
            path, thumbnail, to_story=True
        )
        for attempt in range(50):
            self.logger.debug(f"Attempt #{attempt} to configure Video: {path}")
            time.sleep(3)
            try:
                configured = self.video_configure_to_story(
                    upload_id,
                    width,
                    height,
                    duration,
                    thumbnail,
                    caption,
                    mentions=mentions,
                    medias=medias,
                    thread_ids=thread_ids,
                    extra_data=extra_data,
                )
            except Exception as e:
                if "Transcode not finished yet" in str(e):
                    """
                    Response 202 status:
                    {"message": "Transcode not finished yet.", "status": "fail"}
                    """
                    time.sleep(10)
                    continue
                raise e
            if configured and thread_ids:
                return extract_direct_message(configured.get("message_metadata", [])[0])
        raise VideoConfigureStoryError(response=self.last_response, **self.last_json)


def analyze_video(path: Path, thumbnail: Path = None) -> tuple:
    """
    Story Configure for Photo

    Parameters
    ----------
    path: Path
        Path to the media
    thumbnail: str
        Path to thumbnail for video. When None, then thumbnail is generate automatically

    Returns
    -------
    Tuple
        (width, height, duration, thumbnail)
    """

    try:
        import moviepy.editor as mp
    except ImportError:
        raise Exception("Please install moviepy>=1.0.3 and retry")

    print(f'Analyzing video file "{path}"')
    video = mp.VideoFileClip(str(path))
    width, height = video.size
    if not thumbnail:
        thumbnail = f"{path}.jpg"
        print(f'Generating thumbnail "{thumbnail}"...')
        video.save_frame(thumbnail, t=(video.duration / 2))
    # duration = round(video.duration + 0.001, 3)
    try:
        video.close()
    except AttributeError:
        pass
    return width, height, video.duration, thumbnail
