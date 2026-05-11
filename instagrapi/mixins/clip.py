import contextlib
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

from instagrapi import config
from instagrapi.exceptions import ClientError, ClipConfigureError, ClipNotUpload
from instagrapi.types import Location, Media, Track, Usertag
from instagrapi.utils.timing import date_time_original
from instagrapi.utils.video import analyze_video_for_upload

try:
    from PIL import Image
except ImportError:
    raise Exception("You don't have PIL installed. Please install PIL or Pillow>=8.1.1")


def _make_tmp_path(suffix: str) -> str:
    """Create a uniquely-named tempfile path safely.

    ``tempfile.mktemp`` is deprecated and prone to TOCTOU races. We
    use ``mkstemp`` to atomically create the file under a unique
    name, then close the file descriptor — the path is reserved and
    safe for the caller to reopen.
    """
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    return path


class ClipMixin:
    """
    Helpers for CLIP/Reel actions
    """

    def clip_pin(self, media_pk: str, revert: bool = False) -> bool:
        """
        Pin Reel to the Reels tab/profile Reels grid

        Parameters
        ----------
        media_pk: str
        revert: bool, optional
            Unpin when True

        Returns
        -------
        bool
        A boolean value
        """
        name = "unpin" if revert else "pin"
        result = self.private_request(
            f"users/{name}_timeline_media/",
            data={"post_id": str(media_pk), "profile_grid": "clips"},
        )
        return result["status"] == "ok"

    def clip_unpin(self, media_pk: str) -> bool:
        """
        Unpin Reel from the Reels tab/profile Reels grid

        Parameters
        ----------
        media_pk: str

        Returns
        -------
        bool
        A boolean value
        """
        return self.clip_pin(media_pk, True)


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
            Directory in which you want to download the album,
            default is "" and will download the files to working
            directory.

        Returns
        -------
        str
        """
        return self.video_download(media_pk, folder)

    def clip_download_by_url(self, url: str, filename: str = "", folder: Path = "") -> str:
        """
        Download CLIP video using URL

        Parameters
        ----------
        url: str
            URL to download media from
        folder: Path, optional
            Directory in which you want to download the album,
            default is "" and will download the files to working
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

    def clip_info_for_creation(self) -> Dict:
        """
        Get Reel creation preflight configuration for the current user.

        Returns
        -------
        Dict
            A dictionary of response from the call
        """
        return self.private_request("clips/clips_info_for_creation/")

    def clip_trial_eligible(self) -> bool:
        """
        Check whether the current user can create Trial Reels.

        Returns
        -------
        bool
            A boolean value
        """
        result = self.clip_info_for_creation()
        trial_config = result.get("trial_config") or {}
        return bool(trial_config.get("is_enabled"))

    def clip_share_to_fb_config(self, device_status: Optional[Dict[str, object]] = None) -> Dict:
        """
        Get Reel Facebook sharing configuration for the current user.

        Parameters
        ----------
        device_status: Dict[str, object], optional
            Device video capability status sent by the Instagram Android app.

        Returns
        -------
        Dict
            A dictionary of response from the call
        """
        device_status = device_status or {
            "hw_av1_dec": False,
            "hw_vp9_dec": False,
            "hw_avc_dec": False,
            "10bit_hw_av1_dec": False,
            "10bit_hw_vp9_dec": False,
            "is_hlg_supported": False,
            "chip_vendor": "others",
            "chip_name": "unknown",
            "core_count": 0,
            "max_ghz_sum": 0,
            "min_ghz_sum": 0,
        }
        return self.private_request(
            "clips/user/share_to_fb_config/",
            params={"device_status": json.dumps(device_status)},
        )

    def clip_upload(
        self,
        path: Path,
        caption: str,
        thumbnail: Path = None,
        usertags: List[Usertag] = [],
        location: Location = None,
        configure_timeout: int = 10,
        feed_show: str = "1",
        extra_data: Dict[str, object] = {},
        trial: bool = False,
        trial_graduation_strategy: str = "manual",
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
            Path to thumbnail for CLIP.
            Default value is None, and it generates a thumbnail
        usertags: List[Usertag], optional
            List of users to be tagged on this upload, default is empty list.
        location: Location, optional
            Location tag for this upload, default is none
        configure_timeout: int
            Timeout between attempt to configure media (set caption, etc), default is 10
        feed_show: str
            Show Reel preview in feed/profile grid, default is "1".
            Forced to "0" for Trial Reels.
        extra_data: Dict[str, object], optional
            Dict of extra data, if you need to add your params,
            like {"share_to_facebook": 1}.
        trial: bool, optional
            Upload as a Trial Reel for eligible accounts, default is False.
        trial_graduation_strategy: str, optional
            Trial Reel graduation strategy, default is "manual".

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
        with open(path, "rb") as fp:
            clip_data = fp.read()
            clip_len = str(len(clip_data))
        configure_extra_data = dict(extra_data or {})
        if trial:
            feed_show = "0"
            configure_extra_data.setdefault(
                "trial_params",
                {"graduation_strategy": trial_graduation_strategy},
            )
        duration_ms = str(int(duration * 1000))
        composer_session_id = str(uuid4())
        asset_id = uuid4().hex[:12].upper()
        target_id = self.user_id or getattr(self, "_user_id", None)
        upload_context = {
            "source_attribution": None,
            "enable_video_dimension_upscale": False,
            "source_type": "clips",
            "quality": "",
        }
        if target_id:
            upload_context["target_id"] = int(target_id)
        upload_timestamp_ms = upload_id
        upload_name = "{upload_uuid}-0-{length}-{timestamp}-{timestamp}".format(
            upload_uuid=uuid4().hex,
            length=clip_len,
            timestamp=upload_timestamp_ms,
        )
        upload_settings = {
            "composer_session_id": composer_session_id,
            "upload_setting_properties": {
                "upload_settings_version": "v0.1",
                "codec": {},
                "context": upload_context,
                "video": {
                    "video_height": height,
                    "video_gop_size_sec": 0,
                    "video_rotation_angle": 0,
                    "video_width": width,
                    "source_video_codec": None,
                    "video_partial_frame_size_bytes": 0,
                    "asset_id": asset_id,
                    "video_key_frame_size_bytes": 0,
                    "target_duration": int(duration),
                    "video_original_file_size": int(clip_len),
                    "video_duration_milliseconds": int(duration_ms),
                    "audio_bit_rate_bps": -1,
                    "video_bit_rate_bps": 0,
                    "audio_codec_type": None,
                    "video_fps": 30,
                },
                "creative_tools": {
                    "transmuxing_eligible": False,
                    "transcoding_required": True,
                },
                "network": {
                    "download_latency_connection_quality": "ig_dummy",
                    "network_connection_name": "ig_dummy",
                    "download_bandwidth_connection_quality": "ig_dummy",
                },
            },
            "preview_spec": {
                "spec_version": 1,
                "video_dur_ms": int(duration_ms),
                "audio_dur_ms": int(duration_ms),
            },
        }
        upload_settings_data = json.dumps(upload_settings)
        upload_settings_len = str(len(upload_settings_data.encode("utf-8")))
        headers = {
            "Accept-Encoding": "gzip",
            "Content-Type": "application/json",
            "Content-Length": upload_settings_len,
            "Offset": "0",
            "X-Entity-Length": upload_settings_len,
            "X-Entity-Name": "upload_settings",
            "X-Entity-Type": "application/json",
            "X_FB_VIDEO_WATERFALL_ID": f"{composer_session_id}_settings",
        }
        response = self.private.post(
            "https://{domain}/upload_settings/{session_id}".format(
                domain=config.API_DOMAIN,
                session_id=composer_session_id,
            ),
            data=upload_settings_data,
            headers=headers,
        )
        self.request_log(response)
        if response.status_code != 200:
            raise ClipNotUpload(response=self.last_response, **self.last_json)
        rupload_params = {
            "provenance_metadata": json.dumps({"origin": ["EXTERNAL"]}),
            "upload_media_height": str(height),
            "share_type": "reels",
            "debug_segment_id": "0",
            "extract_cover_frame": "1",
            "upload_engine_config_enum": "0",
            "xsharing_user_ids": "[]",
            "upload_media_width": str(width),
            "stella_data": "{}",
            "is_clips_video": "1",
            "is_optimistic_upload": "true",
            "upload_media_duration_ms": duration_ms,
            "content_tags": "use_default_cover",
            "upload_id": upload_id,
            "retry_context": '{"num_reupload":0,"num_step_manual_retry":0,"num_step_auto_retry":0}',
            "session_id": upload_id,
            "media_type": "2",
        }
        headers = {
            "Accept-Encoding": "gzip",
            "X-Instagram-Rupload-Params": json.dumps(rupload_params),
            "X_FB_VIDEO_WATERFALL_ID": f"{composer_session_id}_{asset_id}_Mixed_0",
            "X-Entity-Type": "video/mp4",
            "Segment-Start-Offset": "0",
            "Segment-Type": "3",
        }
        response = self.private.get(
            "https://{domain}/rupload_igvideo/{name}".format(domain=config.API_DOMAIN, name=upload_name),
            headers=headers,
        )
        self.request_log(response)
        if response.status_code != 200:
            raise ClipNotUpload(response=self.last_response, **self.last_json)
        headers = {
            "Offset": "0",
            "X-Entity-Name": upload_name,
            "X-Entity-Length": clip_len,
            "Content-Type": "application/octet-stream",
            "Content-Length": clip_len,
            **headers,
        }
        response = self.private.post(
            "https://{domain}/rupload_igvideo/{name}".format(domain=config.API_DOMAIN, name=upload_name),
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
                    extra_data=configure_extra_data,
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
                    self.expose()
                    return self._extract_configured_media_or_raise(
                        configured,
                        ClipConfigureError,
                        "Clip upload",
                    )
        raise ClipConfigureError(response=self.last_response, **self.last_json)

    def clip_upload_as_reel_with_music(
        self,
        path: Path,
        caption: str,
        track: Track,
        extra_data: Dict[str, object] = {},
    ) -> Media:
        """
        Upload CLIP as reel with music metadata.
        It also add the music under the video, therefore a mute video is required.

        If you just want to add music metadata to your reel,
        just copy the extra data you find here and add it
        to the extra_data parameter of the clip_upload function.

        Parameters
        ----------
        path: Path
            Path to CLIP file
        caption: str
            Media caption
        track: Track
            The music track to be added to the video reel
            use cl.search_music(title)[0].dict()

        extra_data: Dict[str, object], optional
            Dict of extra data, if you need to add your params, like {"share_to_facebook": 1}.

        Returns
        -------
        Media
            A Media response from the call
        """
        tmpaudio = Path(_make_tmp_path(".m4a"))
        tmpaudio = self.track_download_by_url(track.uri, "track", tmpaudio.parent)
        tmpvideo = None
        try:
            highlight_start_time = track.highlight_start_times_in_ms[0]
        except IndexError:
            highlight_start_time = 0
        try:
            import moviepy.editor as mp
        except ImportError:
            try:
                import moviepy as mp
            except ImportError:
                raise Exception("Please install moviepy>=1.0.3 and retry")
        video = None
        audio_clip = None
        try:
            # get all media to create the reel
            video = mp.VideoFileClip(str(path))
            audio_clip = mp.AudioFileClip(str(tmpaudio))
            # set the start time of the audio and create the actual media
            start = highlight_start_time / 1000
            end = highlight_start_time / 1000 + video.duration
            audio_clip = audio_clip.subclip(start, end)
            video = video.set_audio(audio_clip)
            video_duration = video.duration
            # save the media in tmp folder
            tmpvideo = Path(_make_tmp_path(".mp4"))
            video.write_videofile(str(tmpvideo))
            # create the extra data to upload with it
            data = dict(extra_data or {})
            data["clips_audio_metadata"] = {
                "original": {"volume_level": 0.0},
                "song": {
                    "volume_level": 1.0,
                    "is_saved": "0",
                    "artist_name": track.display_artist,
                    "audio_asset_id": track.id,
                    "audio_cluster_id": track.audio_cluster_id,
                    "track_name": track.title,
                    "is_picked_precapture": "1",
                },
            }
            data["music_params"] = {
                "audio_asset_id": track.id,
                "audio_cluster_id": track.audio_cluster_id,
                "audio_asset_start_time_in_ms": highlight_start_time,
                "derived_content_start_time_in_ms": 0,
                "overlap_duration_in_ms": int(video_duration * 1000),
                "product": "story_camera_clips_v2",
                "song_name": track.title,
                "artist_name": track.display_artist,
                "alacorn_session_id": "null",
            }
            if getattr(track, "music_canonical_id", None):
                data["clips_audio_metadata"]["song"]["music_canonical_id"] = track.music_canonical_id
                data["music_params"]["music_canonical_id"] = track.music_canonical_id
            return self.clip_upload(tmpvideo, caption, extra_data=data)
        finally:
            for clip in (video, audio_clip):
                with contextlib.suppress(AttributeError):
                    if clip:
                        clip.close()
            for tmp_path in (tmpvideo, tmpaudio):
                with contextlib.suppress(FileNotFoundError):
                    if tmp_path:
                        tmp_path.unlink()

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
        feed_show: str = "1",
        extra_data: Dict[str, object] = {},
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
        extra_data: Dict[str, object], optional
            Dict of extra data, if you need to add your params, like {"share_to_facebook": 1}.

        Returns
        -------
        Dict
            A dictionary of response from the call
        """
        self.photo_rupload(Path(thumbnail), upload_id, for_story=True)
        usertags = [{"user_id": tag.user.pk, "position": [tag.x, tag.y]} for tag in usertags]
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
            **extra_data,
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
    return analyze_video_for_upload(path, thumbnail, label="CLIP", crop_thumbnail=crop_thumbnail)


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
