import contextlib
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional, Union
from uuid import uuid4

from instagrapi import config
from instagrapi.exceptions import ClientError, ClipConfigureError, ClipNotUpload
from instagrapi.types import Location, Media, Track, Usertag
from instagrapi.utils.timing import date_time_original
from instagrapi.utils.video import MOVIEPY_2_INSTALL_MESSAGE, analyze_video_for_upload

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


CLIP_FB_CROSSPOSTING_UNIFIED_CONFIG_CLIENT_DOC_ID = "216179630714134719310007237117"
CLIP_FB_CROSSPOSTING_UNIFIED_CONFIG_FRIENDLY_NAME = "CrosspostingUnifiedConfigsQuery"
CLIP_FB_CROSSPOSTING_UNIFIED_CONFIG_ROOT_FIELD = "xcxp_unified_crossposting_configs_root"
CLIP_FB_CROSSPOSTING_SURFACES = [
    {
        "source_surface": "STORY",
        "destination_app": "FB",
        "destination_surface": "STORY",
    },
    {
        "source_surface": "FEED",
        "destination_app": "FB",
        "destination_surface": "FEED",
    },
    {
        "source_surface": "REELS",
        "destination_app": "FB",
        "destination_surface": "REELS",
    },
]


class ClipMixin:
    """
    Helpers for CLIP/Reel actions
    """

    def _raise_clip_upload_error(self, response, stage: str) -> None:
        self.last_response = response
        status_code = getattr(response, "status_code", None)
        response_text = getattr(response, "text", "") or ""
        error_response = {}
        try:
            parsed = response.json()
        except Exception:
            parsed = None
        if isinstance(parsed, dict):
            error_response = parsed
            self.last_json = parsed
        else:
            self.last_json = {}
        details = response_text or error_response
        raise ClipNotUpload(
            f"Clip upload failed during {stage}: HTTP {status_code}: {details}",
            response=response,
            stage=stage,
            status_code=status_code,
            error_response=error_response,
            response_text=response_text,
        )

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

    def clip_change_cover(self, media_pk: str, cover_path: Path) -> bool:
        """
        Change cover image for a published Reel

        Parameters
        ----------
        media_pk: str
            PK for the Reel
        cover_path: Path
            Path to the new cover image

        Returns
        -------
        bool
        A boolean value
        """
        upload_id, _, _ = self.photo_rupload(Path(cover_path))
        result = self.private_request(
            "media/configure_to_clips_cover_image/",
            data={"upload_id": str(upload_id), "clips_media_id": str(media_pk)},
        )
        return bool(result.get("success")) or result.get("status") == "ok"


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

    @staticmethod
    def _default_video_device_status() -> Dict[str, object]:
        return {
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

    def clip_info_for_creation(self, device_status: Optional[Dict[str, object]] = None) -> Dict:
        """
        Get Reel creation preflight configuration for the current user.

        Parameters
        ----------
        device_status: Dict[str, object], optional
            Device video capability status sent by the Instagram Android app.

        Returns
        -------
        Dict
            A dictionary of response from the call
        """
        device_status = device_status or self._default_video_device_status()
        return self.private_request(
            "clips/clips_info_for_creation/",
            params={"device_status": json.dumps(device_status)},
        )

    def clip_trial_eligible(self) -> bool:
        """
        Check whether Reel creation preflight reports Trial Reels enabled.

        Instagram can still reject Trial Reel publishing later during
        configure, so keep upload-side error handling for backend
        eligibility decisions.

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
        device_status = device_status or self._default_video_device_status()
        return self.private_request(
            "clips/user/share_to_fb_config/",
            params={"device_status": json.dumps(device_status)},
        )

    def clip_share_to_fb_unified_config(
        self,
        crosspost_app_surface_list: Optional[List[Dict[str, str]]] = None,
    ) -> Dict:
        """
        Get the Android cross-posting unified config used by the Reel composer.

        Returns
        -------
        Dict
            A dictionary of response from the private GraphQL call
        """
        variables = {
            "configs_request": {
                "source_app": "IG",
                "crosspost_app_surface_list": crosspost_app_surface_list or CLIP_FB_CROSSPOSTING_SURFACES,
            }
        }
        return self.private_graphql_query_request(
            friendly_name=CLIP_FB_CROSSPOSTING_UNIFIED_CONFIG_FRIENDLY_NAME,
            root_field_name=CLIP_FB_CROSSPOSTING_UNIFIED_CONFIG_ROOT_FIELD,
            variables=variables,
            client_doc_id=CLIP_FB_CROSSPOSTING_UNIFIED_CONFIG_CLIENT_DOC_ID,
            priority="u=3, i",
            extra_headers={"X-FB-RMD": "state=URL_ELIGIBLE"},
        )

    def _clip_share_to_fb_unified_root(self, config: Dict[str, object]) -> object:
        data = (config or {}).get("data")
        if isinstance(data, dict):
            root = data.get(CLIP_FB_CROSSPOSTING_UNIFIED_CONFIG_ROOT_FIELD)
            if root is not None:
                return root
            for key, value in data.items():
                if CLIP_FB_CROSSPOSTING_UNIFIED_CONFIG_ROOT_FIELD in str(key):
                    return value
        return config or {}

    def _clip_share_to_fb_iter_dicts(self, value):
        if isinstance(value, dict):
            yield value
            for child in value.values():
                yield from self._clip_share_to_fb_iter_dicts(child)
        elif isinstance(value, list):
            for child in value:
                yield from self._clip_share_to_fb_iter_dicts(child)

    def _clip_share_to_fb_candidate_value(self, config: Dict[str, object], keys) -> object:
        for key in keys:
            value = config.get(key)
            if value not in (None, ""):
                return value
        return None

    def _clip_share_to_fb_reels_fb_candidate(self, config: Dict[str, object]) -> bool:
        source_surface = str(config.get("source_surface") or "").upper()
        destination_surface = str(config.get("destination_surface") or "").upper()
        destination_app = str(config.get("destination_app") or "").upper()
        if source_surface and source_surface not in {"REELS", "CLIPS"}:
            return False
        if destination_surface and destination_surface not in {"REELS", "CLIPS"}:
            return False
        if destination_app and destination_app not in {"FB", "FACEBOOK"}:
            return False
        return bool(source_surface or destination_surface or destination_app)

    def _clip_share_to_fb_unified_destination_candidates(self, config: Dict[str, object]):
        for candidate in self._clip_share_to_fb_iter_dicts(self._clip_share_to_fb_unified_root(config)):
            if not self._clip_share_to_fb_reels_fb_candidate(candidate):
                continue
            merged = dict(candidate)
            for key in (
                "destination",
                "fb_destination",
                "reels_destination",
                "crosspost_destination",
                "crossposting_destination",
                "xpost_destination",
            ):
                nested = candidate.get(key)
                if isinstance(nested, dict):
                    merged.update(nested)
            yield merged

    def clip_share_to_fb_unified_destination(self, config: Optional[Dict[str, object]] = None) -> Dict[str, object]:
        """
        Resolve a confirmed Reel Facebook destination from unified config.

        Parameters
        ----------
        config: Dict[str, object], optional
            Response from :meth:`clip_share_to_fb_unified_config`.

        Returns
        -------
        Dict[str, object]
            Normalized destination fields.
        """
        unified_config = config if config is not None else self.clip_share_to_fb_unified_config()
        for candidate in self._clip_share_to_fb_unified_destination_candidates(unified_config or {}):
            try:
                return self.clip_share_to_fb_destination(config=candidate, use_unified_config=False)
            except ClientError:
                continue
        raise ClientError("Facebook Reel sharing unified config has no confirmed Reel Facebook destination")

    def clip_share_to_fb_destination(
        self,
        config: Optional[Dict[str, object]] = None,
        destination_id: Optional[str] = None,
        destination_type: Optional[str] = None,
        destination_audience_type: Optional[str] = None,
        validation_check_bypass: Optional[bool] = None,
        use_unified_config: bool = True,
    ) -> Dict[str, object]:
        """
        Resolve the Facebook Reel sharing destination from confirmed fields.

        This helper reads only destination-shaped fields that are known to map
        to Reel configure payload fields. It intentionally does not treat
        generic Account Center/linking identifiers such as ``account_id`` as
        ``share_to_fb_destination_id``.

        Parameters
        ----------
        config: Dict[str, object], optional
            Facebook cross-posting config. When omitted, this calls
            :meth:`clip_share_to_fb_config`.
        destination_id: str, optional
            Explicit Facebook destination id. Overrides config values.
        destination_type: str, optional
            Explicit Facebook destination type, ``USER`` or ``PAGE``.
            Overrides config values.
        destination_audience_type: str, optional
            Explicit Facebook Reels audience type, e.g. ``PUBLIC``.
        validation_check_bypass: bool, optional
            Explicit validation bypass flag. Overrides config values.
        use_unified_config: bool, optional
            When config is omitted, fall back to the Android cross-posting
            unified config if the lightweight Reel preflight has no destination.

        Returns
        -------
        Dict[str, object]
            Normalized destination fields.
        """
        fb_config = (config if config is not None else self.clip_share_to_fb_config()) or {}
        if fb_config.get("enabled") is False or fb_config.get("is_account_linked") is False:
            raise ClientError("Facebook Reel sharing is not enabled or no Facebook account is linked")

        explicit_destination = bool(destination_id or destination_type)
        destination_id = destination_id or self._clip_share_to_fb_candidate_value(
            fb_config,
            (
                "share_to_fb_destination_id",
                "reels_destination_id",
                "crosspost_destination_id",
                "crossposting_destination_id",
                "xpost_destination_id",
                "destination_id",
            ),
        )
        destination_type = destination_type or self._clip_share_to_fb_candidate_value(
            fb_config,
            (
                "share_to_fb_destination_type",
                "crosspost_destination_type",
                "crossposting_destination_type",
                "xpost_destination_type",
                "destination_type",
                "posting_type",
            ),
        )
        destination_audience_type = destination_audience_type or self._clip_share_to_fb_candidate_value(
            fb_config,
            (
                "share_to_fb_destination_audience_type",
                "reels_destination_audience_type",
                "destination_audience_type",
                "audience_type",
            ),
        )
        if validation_check_bypass is None:
            validation_check_bypass = fb_config.get(
                "reels_cross_app_share_fb_validation_check_bypass",
                fb_config.get("cross_app_share_fb_validation_check_bypass"),
            )

        has_destination = bool(destination_id and destination_type)
        if not has_destination and use_unified_config and config is None and not explicit_destination:
            try:
                return self.clip_share_to_fb_unified_destination()
            except ClientError:
                pass
        if fb_config.get("share_to_fb_unavailable") and not has_destination:
            raise ClientError(
                "Facebook Reel sharing is unavailable from the Reel preflight response. "
                "If the Instagram app can still cross-post manually, pass destination_id "
                "and destination_type explicitly."
            )
        if not destination_id:
            raise ClientError(
                "Facebook Reel sharing configuration has no destination. "
                "Link a Facebook account/page in the Instagram app or pass destination_id."
            )
        if not destination_type:
            raise ClientError(
                "Facebook Reel sharing configuration has no destination type. Pass destination_type as USER or PAGE."
            )
        destination_type = str(destination_type).upper()
        if destination_type not in {"USER", "PAGE"}:
            raise ClientError(
                "Facebook Reel sharing destination type must be USER or PAGE. "
                "Do not pass reels_cross_app_share_type here."
            )

        destination = {
            "destination_id": str(destination_id),
            "destination_type": destination_type,
        }
        if destination_audience_type:
            destination["destination_audience_type"] = str(destination_audience_type)
        if validation_check_bypass is not None:
            destination["validation_check_bypass"] = bool(validation_check_bypass)
        return destination

    def clip_share_to_fb_extra_data(
        self,
        config: Optional[Dict[str, object]] = None,
        destination_id: Optional[str] = None,
        destination_type: Optional[str] = None,
        destination_audience_type: Optional[str] = None,
        xpost_surface: str = "IG_REELS_COMPOSER",
        validation_check_bypass: Optional[bool] = None,
        attempt_id: Optional[str] = None,
    ) -> Dict[str, object]:
        """
        Build configure fields for sharing a Reel to Facebook.

        Instagram Android 428 stores Reel Facebook cross-posting in
        ``XPlatformParams`` fields. The old ``share_to_facebook`` flag alone is
        not enough for accounts that require an explicit Facebook destination.

        Parameters
        ----------
        config: Dict[str, object], optional
            Facebook cross-posting config. The lightweight
            ``clip_share_to_fb_config()`` response contains availability flags;
            app/draft configs can also contain destination fields.
        destination_id: str, optional
            Facebook destination id. Overrides config values.
        destination_type: str, optional
            Facebook destination type/posting type, ``USER`` or ``PAGE``.
            Overrides config values.
        destination_audience_type: str, optional
            Facebook Reels audience type, e.g. ``PUBLIC``.
        xpost_surface: str, optional
            Cross-posting surface reported by the Instagram app.
        validation_check_bypass: bool, optional
            Whether to bypass app-side FB validation. Overrides config values.
        attempt_id: str, optional
            Cross-post configure attempt id. Generated when omitted.

        Returns
        -------
        Dict
            Extra configure data for ``clip_upload(..., extra_data=...)``.
        """
        destination = self.clip_share_to_fb_destination(
            config=config,
            destination_id=destination_id,
            destination_type=destination_type,
            destination_audience_type=destination_audience_type,
            validation_check_bypass=validation_check_bypass,
        )
        attempt_id = attempt_id or str(uuid4())

        data = {
            "share_to_facebook": "1",
            "is_reel_shared_to_fb": True,
            "share_to_facebook_reels": True,
            "share_to_fb_destination_id": destination["destination_id"],
            "share_to_fb_destination_type": destination["destination_type"],
            "xpost_surface": xpost_surface,
            "no_token_crosspost": "1",  # nosec B105
            "attempt_id": attempt_id,
        }
        if destination.get("destination_audience_type"):
            data["share_to_fb_destination_audience_type"] = destination["destination_audience_type"]
        if destination.get("validation_check_bypass") is not None:
            data["cross_app_share_fb_validation_check_bypass"] = bool(destination["validation_check_bypass"])
        return data

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
        share_to_facebook: bool = False,
        fb_destination_id: Optional[str] = None,
        fb_destination_type: Optional[str] = None,
        fb_destination_audience_type: Optional[str] = None,
        fb_xpost_surface: str = "IG_REELS_COMPOSER",
        fb_validation_check_bypass: Optional[bool] = None,
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
            like {"disable_comments": 1}.
        trial: bool, optional
            Upload as a Trial Reel for eligible accounts, default is False.
        trial_graduation_strategy: str, optional
            Trial Reel graduation strategy, default is "manual".
        share_to_facebook: bool, optional
            Share this Reel to a linked Facebook account/page, default is False.
        fb_destination_id: str, optional
            Facebook destination id used when share_to_facebook is True.
        fb_destination_type: str, optional
            Facebook destination type used when share_to_facebook is True,
            ``USER`` or ``PAGE``.
        fb_destination_audience_type: str, optional
            Facebook Reels audience type, e.g. ``PUBLIC``.
        fb_xpost_surface: str, optional
            Cross-posting surface reported by the Instagram app.
        fb_validation_check_bypass: bool, optional
            Override the validation bypass value from share_to_fb_config.

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
        if share_to_facebook:
            fb_extra_data = self.clip_share_to_fb_extra_data(
                destination_id=fb_destination_id,
                destination_type=fb_destination_type,
                destination_audience_type=fb_destination_audience_type,
                xpost_surface=fb_xpost_surface,
                validation_check_bypass=fb_validation_check_bypass,
            )
            configure_extra_data = {**fb_extra_data, **configure_extra_data}
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
            self._raise_clip_upload_error(response, "upload_settings")
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
            self._raise_clip_upload_error(response, "rupload_init")
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
            self._raise_clip_upload_error(response, "rupload_upload")
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
            Dict of extra data, if you need to add your params, like {"disable_comments": 1}.

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
            from moviepy import AudioFileClip, VideoFileClip
        except ImportError as exc:
            raise RuntimeError(
                f"clip_upload_as_reel_with_music() requires MoviePy 2.2.1. {MOVIEPY_2_INSTALL_MESSAGE}"
            ) from exc
        video = None
        audio_clip = None
        try:
            # get all media to create the reel
            video = VideoFileClip(str(path))
            audio_clip = AudioFileClip(str(tmpaudio))
            # set the start time of the audio and create the actual media
            start = highlight_start_time / 1000
            end = highlight_start_time / 1000 + video.duration
            audio_clip = audio_clip.subclipped(start, end)
            video = video.with_audio(audio_clip)
            video_duration = video.duration
            # save the media in tmp folder
            tmpvideo = Path(_make_tmp_path(".mp4"))
            video.write_videofile(str(tmpvideo))
            # create the extra data to upload with it
            data = self.clip_music_extra_data(
                track,
                extra_data=extra_data,
                audio_asset_start_time=highlight_start_time,
                overlap_duration=int(video_duration * 1000),
                original_volume=0.0,
            )
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

    def clip_music_extra_data(
        self,
        track: Union[Track, Dict],
        extra_data: Dict[str, object] = {},
        audio_asset_start_time: Optional[int] = None,
        overlap_duration: int = 30000,
        original_volume: float = 1.0,
        music_volume: float = 1.0,
        product: str = "story_camera_clips_v2",
        alacorn_session_id: str = "null",
    ) -> Dict[str, object]:
        """
        Build Reel music metadata for ``clip_upload(..., extra_data=...)``.

        This helper only adds the metadata fields used by the app configure
        request. It does not download or mux audio into the local video file.
        """
        audio_asset_id = self._track_value(track, "audio_asset_id") or self._track_value(track, "id")
        audio_cluster_id = self._track_value(track, "audio_cluster_id")
        assert audio_asset_id, "track.audio_asset_id or track.id is required"
        assert audio_cluster_id, "track.audio_cluster_id is required"
        if audio_asset_start_time is None:
            audio_asset_start_time = self._track_highlight_start(track)

        artist_name = self._track_value(track, "display_artist") or ""
        track_name = self._track_value(track, "title") or ""
        data = dict(extra_data or {})
        data["clips_audio_metadata"] = {
            "original": {"volume_level": original_volume},
            "song": {
                "volume_level": music_volume,
                "is_saved": "0",
                "artist_name": artist_name,
                "audio_asset_id": audio_asset_id,
                "audio_cluster_id": audio_cluster_id,
                "track_name": track_name,
                "is_picked_precapture": "1",
            },
        }
        data["music_params"] = {
            "audio_asset_id": audio_asset_id,
            "audio_cluster_id": audio_cluster_id,
            "audio_asset_start_time_in_ms": int(audio_asset_start_time),
            "derived_content_start_time_in_ms": 0,
            "overlap_duration_in_ms": int(overlap_duration),
            "product": product,
            "song_name": track_name,
            "artist_name": artist_name,
            "alacorn_session_id": alacorn_session_id,
        }
        music_canonical_id = self._track_value(track, "music_canonical_id")
        if music_canonical_id:
            data["clips_audio_metadata"]["song"]["music_canonical_id"] = music_canonical_id
            data["music_params"]["music_canonical_id"] = music_canonical_id
        return data

    def clip_upload_with_music(
        self,
        path: Path,
        caption: str,
        track: Union[Track, Dict],
        thumbnail: Path = None,
        usertags: List[Usertag] = [],
        location: Location = None,
        extra_data: Dict[str, object] = {},
        audio_asset_start_time: Optional[int] = None,
        overlap_duration: int = 30000,
        original_volume: float = 1.0,
        music_volume: float = 1.0,
        product: str = "story_camera_clips_v2",
        alacorn_session_id: str = "null",
        **kwargs,
    ) -> Media:
        """
        Upload a Reel with music metadata without local audio muxing.

        Pass ``thumbnail=...`` to avoid automatic thumbnail generation in
        environments where ffmpeg is not available.
        """
        data = self.clip_music_extra_data(
            track,
            extra_data=extra_data,
            audio_asset_start_time=audio_asset_start_time,
            overlap_duration=overlap_duration,
            original_volume=original_volume,
            music_volume=music_volume,
            product=product,
            alacorn_session_id=alacorn_session_id,
        )
        return self.clip_upload(
            path,
            caption,
            thumbnail=thumbnail,
            usertags=usertags,
            location=location,
            extra_data=data,
            **kwargs,
        )

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
            Dict of extra data, if you need to add your params, like {"disable_comments": 1}.

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
