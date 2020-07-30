import time
from urllib.parse import urlparse

from .extractors import extract_media_v1
from .exceptions import PrivateError
from .utils import dumps


class AlbumNotDownload(PrivateError):
    pass


class AlbumNotUpload(PrivateError):
    pass


class UnknownFormat(AlbumNotUpload):
    pass


class AlbumConfigureError(AlbumNotUpload):
    pass


class AlbumConfigureStoryError(AlbumConfigureError):
    pass


class DownloadAlbum:
    def album_download(self, media_pk: int, folder: str = "/tmp") -> str:
        media = self.media_info(media_pk)
        assert media["media_type"] == 8, "Must been album"
        paths = []
        for resource in media['resources']:
            filename = "{username}_{media_pk}".format(
                username=media["user"]["username"],
                media_pk=resource['pk']
            )
            if resource['media_type'] == 1:
                paths.append(
                    self.photo_download_by_url(resource["thumbnail_url"], filename, folder)
                )
            elif resource['media_type'] == 2:
                paths.append(
                    self.video_download_by_url(resource["video_url"], filename, folder)
                )
            else:
                raise AlbumNotDownload('Media type "%s" unknown for album (resource.media_pk=%s)' % (resource['media_type'], resource['pk']))
        return paths

    def album_download_by_urls(self, urls: str, folder: str = "/tmp") -> str:
        paths = []
        for url in urls:
            fname = urlparse(url).path.rsplit('/', 1)[1]
            if fname.endswith('.jpg'):
                paths.append(self.photo_download_by_url(url, fname, folder))
            elif fname.endswith('.mp4'):
                paths.append(self.video_download_by_url(url, fname, folder))
            else:
                raise UnknownFormat()
        return paths


class UploadAlbum:

    def album_upload(
        self,
        paths: list,
        caption: str,
        usertags: list = [],
        configure_timeout: str = 3,
        configure_handler=None,
        configure_exception=None,
        to_story=False
    ) -> dict:
        """Upload album to feed

        :param paths:               Path to files (List)
        :param caption:             Media description (String)
        :param usertags:            Mentioned users (List)
        :param configure_timeout:   Timeout between attempt to configure media (set caption, etc)
        :param configure_handler:   Configure handler method
        :param configure_exception: Configure exception class

        :return: Extracted media (Dict)
        """
        childs = []
        for filepath in paths:
            if filepath.endswith('.jpg'):
                upload_id, width, height = self.photo_rupload(filepath, to_album=True)
                childs.append({
                    "upload_id": upload_id,
                    "edits": dumps({"crop_original_size": [width, height], "crop_center": [0.0, -0.0], "crop_zoom": 1.0}),
                    "extra": dumps({"source_width": width, "source_height": height}),
                    "scene_capture_type": "",
                    "scene_type": None
                })
            elif filepath.endswith('.mp4'):
                upload_id, width, height, duration, thumbnail = self.video_rupload(filepath, to_album=True)
                childs.append({
                    "upload_id": upload_id,
                    "clips": dumps([{"length": duration, "source_type": "4"}]),
                    "extra": dumps({"source_width": width, "source_height": height}),
                    "length": duration,
                    "poster_frame_index": "0",
                    "filter_type": "0",
                    "video_result": "",
                    "date_time_original": time.strftime("%Y%m%dT%H%M%S.000Z", time.localtime()),
                    "audio_muted": "false"
                })
                self.photo_rupload(thumbnail, upload_id)
            else:
                raise UnknownFormat()

        for attempt in range(20):
            self.logger.debug("Attempt #%d to configure Album: %s", attempt, filepath)
            time.sleep(configure_timeout)
            try:
                configured = (configure_handler or self.album_configure)(childs, caption, usertags)
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
        raise (configure_exception or AlbumConfigureError)(response=self.last_response, **self.last_json)

    def album_configure(
        self,
        childs: list,
        caption: str,
        usertags: list,
    ) -> bool:
        """Post Configure Album

        :param childs:     Childs of album (List)
        :param caption:    Media description (String)
        :param usertags:   Mentioned users (List)

        :return: Media (Dict)
        """
        upload_id = str(int(time.time() * 1000))
        if usertags:
            usertags = [
                {"user_id": tag['user']['pk'], "position": tag['position']}
                for tag in usertags
            ]
            childs[0]["usertags"] = dumps({"in": usertags})
        data = {
            "timezone_offset": "10800",
            "source_type": "4",
            "creation_logger_session_id": self.client_session_id,
            "caption": caption,
            "client_sidecar_id": upload_id,
            "upload_id": upload_id,
            # "location": self.build_location(name, lat, lng, address),
            "suggested_venue_position": -1,
            "device": self.device,
            "is_suggested_venue": False,
            "children_metadata": [
                {
                    "source_type": "4",
                    "timezone_offset": "10800",
                    "device": dumps(self.device),
                    **child
                } for child in childs
            ]
        }
        return self.private_request("media/configure_sidecar/", self.with_default_data(data))
