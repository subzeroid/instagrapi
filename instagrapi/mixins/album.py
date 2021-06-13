import time
from pathlib import Path
from typing import Dict, List
from urllib.parse import urlparse

from instagrapi.exceptions import (
    AlbumConfigureError,
    AlbumNotDownload,
    AlbumUnknownFormat,
)
from instagrapi.extractors import extract_media_v1
from instagrapi.types import Location, Media, Usertag
from instagrapi.utils import dumps


class DownloadAlbumMixin:
    """
    Helper class to download album
    """

    def album_download(self, media_pk: int, folder: Path = "") -> List[Path]:
        """
        Download your album

        Parameters
        ----------
        media_pk: int
            PK for the album you want to download
        folder: Path, optional
            Directory in which you want to download the album, default is "" and will download the files to working directory.

        Returns
        -------
        List[Path]
            List of path for all the files downloaded
        """
        media = self.media_info(media_pk)
        assert media.media_type == 8, "Must been album"
        paths = []
        for resource in media.resources:
            filename = f"{media.user.username}_{resource.pk}"
            if resource.media_type == 1:
                paths.append(
                    self.photo_download_by_url(resource.thumbnail_url, filename, folder)
                )
            elif resource.media_type == 2:
                paths.append(
                    self.video_download_by_url(resource.video_url, filename, folder)
                )
            else:
                raise AlbumNotDownload(
                    'Media type "{resource.media_type}" unknown for album (resource={resource.pk})'
                )
        return paths

    def album_download_by_urls(self, urls: List[str], folder: Path = "") -> List[Path]:
        """
        Download your album using specified URLs

        Parameters
        ----------
        urls: List[str]
            List of URLs to download media from
        folder: Path, optional
            Directory in which you want to download the album, default is "" and will download the files to working directory.

        Returns
        -------
        List[Path]
            List of path for all the files downloaded
        """
        paths = []
        for url in urls:
            file_name = urlparse(url).path.rsplit("/", 1)[1]
            if file_name.lower().endswith((".jpg", ".jpeg")):
                paths.append(self.photo_download_by_url(url, file_name, folder))
            elif file_name.lower().endswith(".mp4"):
                paths.append(self.video_download_by_url(url, file_name, folder))
            else:
                raise AlbumUnknownFormat()
        return paths


class UploadAlbumMixin:
    def album_upload(
        self,
        paths: List[Path],
        caption: str,
        usertags: List[Usertag] = [],
        location: Location = None,
        configure_timeout: int = 3,
        configure_handler=None,
        configure_exception=None,
        to_story=False,
    ) -> Media:
        """
        Upload album to feed

        Parameters
        ----------
        paths: List[Path]
            List of paths for media to upload
        caption: str
            Media caption
        usertags: List[Usertag], optional
            List of users to be tagged on this upload, default is empty list.
        location: Location, optional
            Location tag for this upload, default is none
        configure_timeout: int
            Timeout between attempt to configure media (set caption, etc), default is 3
        configure_handler
            Configure handler method, default is None
        configure_exception
            Configure exception class, default is None
        to_story: bool
            Currently not used, default is False

        Returns
        -------
        Media
            An object of Media class
        """
        children = []
        for path in paths:
            path = Path(path)
            if path.suffix.lower() in (".jpg", ".jpeg"):
                upload_id, width, height = self.photo_rupload(path, to_album=True)
                children.append(
                    {
                        "upload_id": upload_id,
                        "edits": dumps(
                            {
                                "crop_original_size": [width, height],
                                "crop_center": [0.0, -0.0],
                                "crop_zoom": 1.0,
                            }
                        ),
                        "extra": dumps(
                            {"source_width": width, "source_height": height}
                        ),
                        "scene_capture_type": "",
                        "scene_type": None,
                    }
                )
            elif path.suffix.lower() == ".mp4":
                upload_id, width, height, duration, thumbnail = self.video_rupload(
                    path, to_album=True
                )
                children.append(
                    {
                        "upload_id": upload_id,
                        "clips": dumps([{"length": duration, "source_type": "4"}]),
                        "extra": dumps(
                            {"source_width": width, "source_height": height}
                        ),
                        "length": duration,
                        "poster_frame_index": "0",
                        "filter_type": "0",
                        "video_result": "",
                        "date_time_original": time.strftime(
                            "%Y%m%dT%H%M%S.000Z", time.localtime()
                        ),
                        "audio_muted": "false",
                    }
                )
                self.photo_rupload(thumbnail, upload_id)
            else:
                raise AlbumUnknownFormat()

        for attempt in range(20):
            self.logger.debug(f"Attempt #{attempt} to configure Album: {paths}")
            time.sleep(configure_timeout)
            try:
                configured = (configure_handler or self.album_configure)(
                    children, caption, usertags, location
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
        raise (configure_exception or AlbumConfigureError)(
            response=self.last_response, **self.last_json
        )

    def album_configure(
        self,
        childs: List,
        caption: str,
        usertags: List[Usertag] = [],
        location: Location = None,
    ) -> Dict:
        """
        Post Configure Album

        Parameters
        ----------
        childs: List
            List of media/resources of an album
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
        upload_id = str(int(time.time() * 1000))
        if usertags:
            usertags = [
                {"user_id": tag.user.pk, "position": [tag.x, tag.y]} for tag in usertags
            ]
            childs[0]["usertags"] = dumps({"in": usertags})
        data = {
            "timezone_offset": "10800",
            "source_type": "4",
            "creation_logger_session_id": self.client_session_id,
            "location": self.location_build(location),
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
                    **child,
                }
                for child in childs
            ],
        }
        return self.private_request(
            "media/configure_sidecar/", self.with_default_data(data)
        )
