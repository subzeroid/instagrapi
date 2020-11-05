import json
import time
import random
from pathlib import Path
from typing import List
from uuid import uuid4
from PIL import Image
import moviepy.editor as mp

from . import config
from .extractors import extract_media_v1
from .exceptions import ClientError, IGTVNotUpload, IGTVConfigureError
from .types import Usertag, Location, Media


class DownloadIGTV:
    def igtv_download(self, media_pk: int, folder: Path = "") -> str:
        return self.video_download(media_pk, folder)

    def igtv_download_by_url(self, url: str, filename: str = "", folder: Path = "") -> str:
        return self.video_download_by_url(url, filename, folder)


class UploadIGTV:
    def igtv_upload(
        self,
        path: Path,
        title: str,
        caption: str,
        thumbnail: Path = None,
        usertags: List[Usertag] = [],
        location: Location = None,
        configure_timeout: int = 10,
    ) -> Media:
        """Upload IGTV to Instagram

        :param path:              Path to IGTV file
        :param title:             Media title (String)
        :param caption:           Media description (String)
        :param thumbnail:         Path to thumbnail for IGTV. When None, then
                                  thumbnail is generate automatically
        :param usertags:          Mentioned users (List)
        :param location:          Location
        :param configure_timeout: Timeout between attempt to configure media (set caption and title)

        :return: Media
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
            "is_igtv_video": "1",
            "retry_context": '{"num_step_auto_retry":0,"num_reupload":0,"num_step_manual_retry":0}',
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
            ), headers=headers
        )
        self.request_log(response)
        if response.status_code != 200:
            raise IGTVNotUpload(response=self.last_response, **self.last_json)
        igtv_data = open(path, "rb").read()
        igtv_len = str(len(igtv_data))
        headers = {
            "Offset": "0",
            "X-Entity-Name": upload_name,
            "X-Entity-Length": igtv_len,
            "Content-Type": "application/octet-stream",
            "Content-Length": igtv_len,
            **headers
        }
        response = self.private.post(
            "https://{domain}/rupload_igvideo/{name}".format(
                domain=config.API_DOMAIN, name=upload_name
            ),
            data=igtv_data, headers=headers
        )
        self.request_log(response)
        if response.status_code != 200:
            raise IGTVNotUpload(response=self.last_response, **self.last_json)
        # CONFIGURE
        self.igtv_composer_session_id = self.generate_uuid()
        for attempt in range(20):
            self.logger.debug(f"Attempt #{attempt} to configure IGTV: {path}")
            time.sleep(configure_timeout)
            try:
                configured = self.igtv_configure(
                    upload_id, thumbnail, width, height, duration, title, caption, usertags, location
                )
            except ClientError as e:
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
                    media = self.last_json.get("media")
                    self.expose()
                    return extract_media_v1(media)
        raise IGTVConfigureError(response=self.last_response, **self.last_json)

    def igtv_configure(
        self,
        upload_id: str,
        thumbnail: Path,
        width: int,
        height: int,
        duration: int,
        title: str,
        caption: str,
        usertags: List[Usertag] = [],
        location: Location = None
    ) -> dict:
        """Post Configure IGTV (send caption, thumbnail and more to Instagram)

        :param upload_id:  Unique upload_id (String)
        :param thumbnail:  Path to thumbnail for IGTV
        :param width:      Width in px (Integer)
        :param height:     Height in px (Integer)
        :param duration:   Duration in seconds (Integer)
        :param caption:    Media description (String)
        :param usertags:   Mentioned users (List)
        :param location:   Location
        """
        self.photo_rupload(Path(thumbnail), upload_id)
        usertags = [
            {"user_id": tag.user.pk, "position": [tag.x, tag.y]}
            for tag in usertags
        ]
        data = {
            "igtv_ads_toggled_on": "0",
            "filter_type": "0",
            "timezone_offset": "10800",
            "media_folder": "ScreenRecorder",
            "location": self.location_build(location),
            "source_type": "4",
            "title": title,
            "caption": caption,
            "usertags": json.dumps({"in": usertags}),
            "date_time_original": time.strftime("%Y%m%dT%H%M%S.000Z", time.localtime()),
            "igtv_share_preview_to_feed": "1",
            "upload_id": upload_id,
            "igtv_composer_session_id": self.igtv_composer_session_id,
            "device": self.device,
            "length": duration,
            "clips": [{"length": duration, "source_type": "4"}],
            "extra": {"source_width": width, "source_height": height},
            "audio_muted": False,
            "poster_frame_index": 70,
        }
        return self.private_request(
            "media/configure_to_igtv/?video=1",
            self.with_default_data(data),
            with_signature=True,
        )


def analyze_video(path: Path, thumbnail: Path = None) -> tuple:
    """Analyze and crop thumbnail if need
    """
    print(f'Analizing IGTV file "{path}"')
    video = mp.VideoFileClip(str(path))
    width, height = video.size
    if not thumbnail:
        thumbnail = f"{path}.jpg"
        print(f'Generating thumbnail "{thumbnail}"...')
        video.save_frame(thumbnail, t=(video.duration / 2))
        crop_thumbnail(thumbnail)
    return thumbnail, width, height, video.duration


def crop_thumbnail(path: Path) -> bool:
    """Crop IGTV thumbnail with save height
    """
    im = Image.open(str(path))
    width, height = im.size
    offset = (height / 1.78) / 2
    center = width / 2
    # Crop the center of the image
    im = im.crop((center - offset, 0, center + offset, height))
    im.save(open(path, "w"))
    im.close()
    return True
