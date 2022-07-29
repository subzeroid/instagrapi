import json
import random
import time
from pathlib import Path
from typing import Dict, List
from uuid import uuid4

from instagrapi import config
from instagrapi.exceptions import ClientError, ClipConfigureError, ClipNotUpload
from instagrapi.extractors import extract_media_v1
from instagrapi.types import Location, Media, Usertag
from instagrapi.utils import date_time_original

try:
    from PIL import Image
except ImportError:
    raise Exception("You don't have PIL installed. Please install PIL or Pillow>=8.1.1")


class DownloadClipMixin:
    """
    Helpers to download CLIP videos
    """

    def clip_download(self, media_pk: int, folder: Path = "") -> str:
        """
        Download CLIP video

        Parameters
        ----------
        media_pk: int
            PK for the album you want to download
        folder: Path, optional
            Directory in which you want to download the album, default is "" and will download the files to working
                directory.

        Returns
        -------
        str
        """
        return self.video_download(media_pk, folder)

    def clip_download_by_url(
        self, url: str, filename: str = "", folder: Path = ""
    ) -> str:
        """
        Download CLIP video using URL

        Parameters
        ----------
        url: str
            URL to download media from
        folder: Path, optional
            Directory in which you want to download the album, default is "" and will download the files to working
                directory.

        Returns
        -------
        str
        """
        return self.video_download_by_url(url, filename, folder)


class UploadClipMixin:
    """
    Helpers to upload CLIP videos
    """

    def clip_upload(
        self,
        path: Path,
        caption: str,
        thumbnail: Path = None,
        usertags: List[Usertag] = [],
        location: Location = None,
        configure_timeout: int = 10,
        feed_show : str  = '1',
        extra_data: Dict[str, str] = {},
    ) -> Media:
        """
        Upload CLIP to Instagram

        Parameters
        ----------
        path: Path
            Path to CLIP file
        caption: str
            Media caption
        thumbnail: Path, optional
            Path to thumbnail for CLIP. Default value is None, and it generates a thumbnail
        usertags: List[Usertag], optional
            List of users to be tagged on this upload, default is empty list.
        location: Location, optional
            Location tag for this upload, default is none
        configure_timeout: int
            Timeout between attempt to configure media (set caption, etc), default is 10
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
        upload_id = str(int(time.time() * 1000))
        thumbnail, width, height, duration = analyze_video(path, thumbnail)
        waterfall_id = str(uuid4())
        # upload_name example: '1576102477530_0_7823256191'
        upload_name = "{upload_id}_0_{rand}".format(
            upload_id=upload_id, rand=random.randint(1000000000, 9999999999)
        )
        # by segments bb2c1d0c127384453a2122e79e4c9a85-0-6498763
        # upload_name = "{hash}-0-{rand}".format(
        #     hash="bb2c1d0c127384453a2122e79e4c9a85", rand=random.randint(1111111, 9999999)
        # )
        rupload_params = {
            "is_clips_video": "1",
            "retry_context": '{"num_reupload":0,"num_step_auto_retry":0,"num_step_manual_retry":0}',
            "media_type": "2",
            "xsharing_user_ids": json.dumps([self.user_id]),
            "upload_id": upload_id,
            "upload_media_duration_ms": str(int(duration * 1000)),
            "upload_media_width": str(width),
            "upload_media_height": str(height),
        }
        headers = {
            "Accept-Encoding": "gzip",
            "X-Instagram-Rupload-Params": json.dumps(rupload_params),
            "X_FB_VIDEO_WATERFALL_ID": waterfall_id,
            "X-Entity-Type": "video/mp4",
        }
        response = self.private.get(
            "https://{domain}/rupload_igvideo/{name}".format(
                domain=config.API_DOMAIN, name=upload_name
            ),
            headers=headers,
        )
        self.request_log(response)
        if response.status_code != 200:
            raise ClipNotUpload(response=self.last_response, **self.last_json)
        with open(path, "rb") as fp:
            clip_data = fp.read()
            clip_len = str(len(clip_data))
        headers = {
            "Offset": "0",
            "X-Entity-Name": upload_name,
            "X-Entity-Length": clip_len,
            "Content-Type": "application/octet-stream",
            "Content-Length": clip_len,
            **headers,
        }
        response = self.private.post(
            "https://{domain}/rupload_igvideo/{name}".format(
                domain=config.API_DOMAIN, name=upload_name
            ),
            data=clip_data,
            headers=headers,
        )
        self.request_log(response)
        if response.status_code != 200:
            raise ClipNotUpload(response=self.last_response, **self.last_json)
        # CONFIGURE
        # self.igtv_composer_session_id = self.generate_uuid()  #issue
        for attempt in range(50):
            self.logger.debug(f"Attempt #{attempt} to configure CLIP: {path}")
            time.sleep(configure_timeout)
            try:
                configured = self.clip_configure(
                    upload_id,
                    thumbnail,
                    width,
                    height,
                    duration,
                    caption,
                    usertags,
                    location,
                    feed_show,
                    extra_data=extra_data
                )
            except ClientError as e:
                if "Transcode not finished yet" in str(e):
                    """
                    Response 202 status:
                    {"message": "Transcode not finished yet.", "status": "fail"}
                    """
                    time.sleep(configure_timeout)
                    continue
                raise e
            else:
                if configured:
                    media = self.last_json.get("media")
                    self.expose()
                    return extract_media_v1(media)
        raise ClipConfigureError(response=self.last_response, **self.last_json)

    def clip_configure(
        self,
        upload_id: str,
        thumbnail: Path,
        width: int,
        height: int,
        duration: int,
        caption: str,
        usertags: List[Usertag] = [],
        location: Location = None,
        feed_show : str = '1',
        extra_data: Dict[str, str] = {},
    ) -> Dict:
        """
        Post Configure CLIP (send caption, thumbnail and more to Instagram)

        Parameters
        ----------
        upload_id: str
            Unique identifier for a IGTV video
        thumbnail: Path
            Path to thumbnail for IGTV
        width: int
            Width of the video in pixels
        height: int
            Height of the video in pixels
        duration: int
            Duration of the video in seconds
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
            # "igtv_ads_toggled_on": "0",
            "filter_type": "0",
            "timezone_offset": str(self.timezone_offset),
            "media_folder": "ScreenRecorder",
            "location": self.location_build(location),
            "source_type": "4",
            # "title": title,
            "caption": caption,
            "usertags": json.dumps({"in": usertags}),
            "date_time_original": date_time_original(time.localtime()),
            "clips_share_preview_to_feed": feed_show,
            "upload_id": upload_id,
            # "igtv_composer_session_id": self.igtv_composer_session_id,
            "device": self.device,
            "length": duration,
            "clips": [{"length": duration, "source_type": "4"}],
            "extra": {"source_width": width, "source_height": height},
            "audio_muted": False,
            "poster_frame_index": 70,
            **extra_data
        }
        return self.private_request(
            "media/configure_to_clips/?video=1",
            self.with_default_data(data),
            with_signature=True,
        )


def analyze_video(path: Path, thumbnail: Path = None) -> tuple:
    """
    Analyze and crop thumbnail if need

    Parameters
    ----------
    path: Path
        Path to the video
    thumbnail: Path
        Path to thumbnail for CLIP

    Returns
    -------
    Tuple
        A tuple with (thumbail path, width, height, duration)
    """
    try:
        import moviepy.editor as mp
    except ImportError:
        raise Exception("Please install moviepy>=1.0.3 and retry")

    print(f'Analyzing CLIP file "{path}"')
    video = mp.VideoFileClip(str(path))
    width, height = video.size
    if not thumbnail:
        thumbnail = f"{path}.jpg"
        print(f'Generating thumbnail "{thumbnail}"...')
        video.save_frame(thumbnail, t=(video.duration / 2))
        crop_thumbnail(thumbnail)
    return thumbnail, width, height, video.duration


def crop_thumbnail(path: Path) -> bool:
    """
    Analyze and crop thumbnail if need

    Parameters
    ----------
    path: Path
        Path to the video

    Returns
    -------
    bool
        A boolean value
    """
    im = Image.open(str(path))
    width, height = im.size
    offset = (height / 1.78) / 2
    center = width / 2
    # Crop the center of the image
    im = im.crop((center - offset, 0, center + offset, height))
    with open(path, "w") as fp:
        im.save(fp)
        im.close()
    return True
