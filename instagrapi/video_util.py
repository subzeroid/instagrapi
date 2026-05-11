import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

THUMBNAIL_FFMPEG_MESSAGE = (
    "Could not generate video thumbnail. Pass thumbnail=... or install ffmpeg / set IMAGEIO_FFMPEG_EXE."
)
METADATA_FFMPEG_MESSAGE = (
    "Could not read video metadata with the MP4 parser and MoviePy/ffmpeg is unavailable. "
    "Use a standard MP4 file, or install ffmpeg / set IMAGEIO_FFMPEG_EXE."
)


@dataclass(frozen=True)
class VideoMetadata:
    width: int
    height: int
    duration: float


@dataclass
class _TrackMetadata:
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[float] = None
    handler_type: Optional[str] = None


def _iter_boxes(data: bytes):
    pos = 0
    end = len(data)
    while pos + 8 <= end:
        size, box_type = struct.unpack_from(">I4s", data, pos)
        header_size = 8
        if size == 1:
            if pos + 16 > end:
                raise ValueError("Invalid MP4 box with incomplete extended size")
            size = struct.unpack_from(">Q", data, pos + 8)[0]
            header_size = 16
        elif size == 0:
            size = end - pos
        if size < header_size or pos + size > end:
            raise ValueError("Invalid MP4 box size")
        box_end = pos + size
        yield box_type.decode("ascii", errors="replace"), data[pos + header_size : box_end]
        pos = box_end


def _read_moov(path: Path) -> bytes:
    file_size = path.stat().st_size
    with path.open("rb") as fp:
        while fp.tell() + 8 <= file_size:
            box_start = fp.tell()
            header = fp.read(8)
            if len(header) < 8:
                break
            size, box_type = struct.unpack(">I4s", header)
            header_size = 8
            if size == 1:
                extended_size = fp.read(8)
                if len(extended_size) < 8:
                    raise ValueError("Invalid MP4 box with incomplete extended size")
                size = struct.unpack(">Q", extended_size)[0]
                header_size = 16
            elif size == 0:
                size = file_size - box_start
            if size < header_size or box_start + size > file_size:
                raise ValueError("Invalid MP4 box size")
            payload_size = size - header_size
            if box_type == b"moov":
                return fp.read(payload_size)
            fp.seek(payload_size, 1)
    raise ValueError("MP4 metadata box 'moov' was not found")


def _parse_mvhd(data: bytes) -> Optional[float]:
    if not data:
        return None
    version = data[0]
    if version == 0:
        if len(data) < 20:
            return None
        timescale, duration = struct.unpack_from(">II", data, 12)
    elif version == 1:
        if len(data) < 32:
            return None
        timescale = struct.unpack_from(">I", data, 20)[0]
        duration = struct.unpack_from(">Q", data, 24)[0]
    else:
        return None
    if not timescale:
        return None
    return duration / timescale


def _parse_tkhd(data: bytes) -> tuple[Optional[int], Optional[int]]:
    if not data:
        return None, None
    version = data[0]
    offset = 76 if version == 0 else 88 if version == 1 else None
    if offset is None or len(data) < offset + 8:
        return None, None
    width_fixed, height_fixed = struct.unpack_from(">II", data, offset)
    width = round(width_fixed / 65536)
    height = round(height_fixed / 65536)
    if width <= 0 or height <= 0:
        return None, None
    return width, height


def _parse_hdlr(data: bytes) -> Optional[str]:
    if len(data) < 12:
        return None
    return data[8:12].decode("ascii", errors="replace")


def _parse_mdia(data: bytes, track: _TrackMetadata) -> None:
    for box_type, payload in _iter_boxes(data):
        if box_type == "mdhd":
            track.duration = _parse_mvhd(payload)
        elif box_type == "hdlr":
            track.handler_type = _parse_hdlr(payload)


def _parse_trak(data: bytes) -> _TrackMetadata:
    track = _TrackMetadata()
    for box_type, payload in _iter_boxes(data):
        if box_type == "tkhd":
            track.width, track.height = _parse_tkhd(payload)
        elif box_type == "mdia":
            _parse_mdia(payload, track)
    return track


def read_video_metadata(path: Path) -> VideoMetadata:
    """
    Read MP4 width, height, and duration without invoking MoviePy or ffmpeg.
    """
    moov = _read_moov(Path(path))
    movie_duration = None
    tracks = []
    for box_type, payload in _iter_boxes(moov):
        if box_type == "mvhd":
            movie_duration = _parse_mvhd(payload)
        elif box_type == "trak":
            tracks.append(_parse_trak(payload))

    video_track = next(
        (
            track
            for track in tracks
            if track.handler_type == "vide" and track.width is not None and track.height is not None
        ),
        None,
    )
    if video_track is None:
        video_track = next(
            (track for track in tracks if track.width is not None and track.height is not None),
            None,
        )
    if video_track is None:
        raise ValueError("MP4 video track dimensions were not found")

    duration = movie_duration if movie_duration is not None else video_track.duration
    if duration is None:
        raise ValueError("MP4 video duration was not found")
    return VideoMetadata(video_track.width, video_track.height, float(duration))


def _ffmpeg_unavailable(exc: Exception) -> bool:
    message = str(exc).lower()
    return (
        isinstance(exc, ImportError)
        or "ffmpeg" in message
        or "imageio_ffmpeg_exe" in message
        or "no ffmpeg exe" in message
    )


def _import_moviepy(error_message: str):
    try:
        import moviepy.editor as mp
    except ImportError:
        try:
            import moviepy as mp
        except ImportError as exc:
            raise RuntimeError(error_message) from exc
        except Exception as exc:
            if _ffmpeg_unavailable(exc):
                raise RuntimeError(error_message) from exc
            raise
    except Exception as exc:
        if _ffmpeg_unavailable(exc):
            raise RuntimeError(error_message) from exc
        raise
    return mp


def read_video_metadata_with_moviepy(path: Path) -> VideoMetadata:
    mp = _import_moviepy(METADATA_FFMPEG_MESSAGE)
    video = None
    try:
        video = mp.VideoFileClip(str(path))
        width, height = video.size
        return VideoMetadata(width, height, float(video.duration))
    except Exception as exc:
        if _ffmpeg_unavailable(exc):
            raise RuntimeError(METADATA_FFMPEG_MESSAGE) from exc
        raise
    finally:
        if video:
            video.close()


def read_video_metadata_with_fallback(path: Path) -> VideoMetadata:
    try:
        return read_video_metadata(path)
    except Exception:
        return read_video_metadata_with_moviepy(path)


def generate_video_thumbnail(
    path: Path,
    thumbnail: Path,
    duration: Optional[float] = None,
    crop_thumbnail: Optional[Callable[[Path], bool]] = None,
) -> None:
    mp = _import_moviepy(THUMBNAIL_FFMPEG_MESSAGE)
    video = None
    try:
        video = mp.VideoFileClip(str(path))
        frame_time = duration if duration is not None else float(video.duration)
        video.save_frame(str(thumbnail), t=(frame_time / 2))
    except Exception as exc:
        if _ffmpeg_unavailable(exc):
            raise RuntimeError(THUMBNAIL_FFMPEG_MESSAGE) from exc
        raise
    finally:
        if video:
            video.close()
    if crop_thumbnail:
        crop_thumbnail(thumbnail)


def analyze_video_for_upload(
    path: Path,
    thumbnail: Path = None,
    label: str = "video",
    crop_thumbnail: Optional[Callable[[Path], bool]] = None,
) -> tuple[Path, int, int, float]:
    path = Path(path)
    if thumbnail is not None:
        thumbnail = Path(thumbnail)
    print(f'Analyzing {label} file "{path}"')
    metadata = read_video_metadata_with_fallback(path)
    if thumbnail is None:
        thumbnail = Path(f"{path}.jpg")
        print(f'Generating thumbnail "{thumbnail}"...')
        generate_video_thumbnail(path, thumbnail, duration=metadata.duration, crop_thumbnail=crop_thumbnail)
    return thumbnail, metadata.width, metadata.height, metadata.duration
