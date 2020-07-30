import json
import time
import random
from uuid import uuid4
from PIL import Image
import moviepy.editor as mp

from . import config
from .extractors import extract_media_v1
from .exceptions import ClientError, PrivateError


class IGTVNotUpload(PrivateError):
    pass


class IGTVConfigureError(IGTVNotUpload):
    pass


class DownloadIGTV:
    def igtv_download(self, media_pk: int, folder: str = "/tmp") -> str:
        return self.video_download(media_pk, folder)

    def igtv_download_by_url(self, url: str, filename: str = "", folder: str = "/tmp") -> str:
        return self.video_download_by_url(url, filename, folder)


class UploadIGTV:
    def igtv_upload(
        self,
        filepath: str,
        title: str,
        caption: str,
        thumbnail: str = None,
        usertags: list = [],
        configure_timeout: str = 10,
    ) -> dict:
        """Upload IGTV to Instagram

        :param filepath:          Path to IGTV file (String)
        :param title:             Media title (String)
        :param caption:           Media description (String)
        :param thumbnail:         Path to thumbnail for IGTV (String). When None, then
                                  thumbnail is generate automatically
        :param configure_timeout: Timeout between attempt to configure media (set caption and title)

        :return: Object with state of uploading to Instagram (or False)
        """
        assert isinstance(filepath, str), "Filepath must been string, now %s" % filepath
        upload_id = str(int(time.time() * 1000))
        thumbnail, width, height, duration = analyze_video(filepath, thumbnail)
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
        igtv_data = open(filepath, "rb").read()
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
            self.logger.debug("Attempt #%d to configure IGTV: %s", attempt, filepath)
            time.sleep(configure_timeout)
            try:
                configured = self.igtv_configure(
                    upload_id, thumbnail, width, height, duration, title, caption, usertags
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
        thumbnail: str,
        width: int,
        height: int,
        duration: int,
        title: str,
        caption: str,
        usertags: list
    ) -> bool:
        """Post Configure IGTV (send caption, thumbnail and more to Instagram)

        :param upload_id:  Unique upload_id (String)
        :param thumbnail:  Path to thumbnail for igtv (String)
        :param width:      Width in px (Integer)
        :param height:     Height in px (Integer)
        :param duration:   Duration in seconds (Integer)
        :param caption:    Media description (String)
        """
        self.photo_rupload(thumbnail, upload_id)
        usertags = [
            {"user_id": tag['user']['pk'], "position": tag['position']}
            for tag in usertags
        ]
        data = {
            "igtv_ads_toggled_on": "0",
            "filter_type": "0",
            "timezone_offset": "10800",
            "media_folder": "ScreenRecorder",
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


def analyze_video(filepath: str, thumbnail: str = None) -> tuple:
    """Analyze and crop thumbnail if need
    """
    print(f'Analizing IGTV file "{filepath}"')
    video = mp.VideoFileClip(filepath)
    width, height = video.size
    if not thumbnail:
        thumbnail = f"{filepath}.jpg"
        print(f'Generating thumbnail "{thumbnail}"...')
        video.save_frame(thumbnail, t=(video.duration / 2))
        crop_thumbnail(thumbnail)
    return thumbnail, width, height, video.duration


def crop_thumbnail(filepath):
    """Crop IGTV thumbnail with save height
    """
    im = Image.open(filepath)
    width, height = im.size
    offset = (height / 1.78) / 2
    center = width / 2
    # Crop the center of the image
    im = im.crop((center - offset, 0, center + offset, height))
    im.save(open(filepath, "w"))
    im.close()
    return True
