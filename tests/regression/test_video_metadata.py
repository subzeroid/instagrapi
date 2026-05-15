import builtins
import contextlib
import importlib
import importlib.metadata
import os
import shutil
import struct
import subprocess
import sys

from tests.helpers import *


def _box(name: str, payload: bytes) -> bytes:
    return struct.pack(">I4s", len(payload) + 8, name.encode("ascii")) + payload


def _sample_mp4(width: int = 720, height: int = 1280, duration: float = 3.5) -> bytes:
    timescale = 1000
    duration_units = int(duration * timescale)
    ftyp = _box("ftyp", b"isom\x00\x00\x00\x01isommp42")

    mvhd = _box(
        "mvhd",
        b"\x00\x00\x00\x00" + b"\x00" * 8 + struct.pack(">II", timescale, duration_units),
    )
    tkhd_payload = bytearray(84)
    tkhd_payload[0] = 0
    tkhd_payload[3] = 3
    struct.pack_into(">I", tkhd_payload, 76, width << 16)
    struct.pack_into(">I", tkhd_payload, 80, height << 16)
    tkhd = _box("tkhd", bytes(tkhd_payload))
    mdhd = _box(
        "mdhd",
        b"\x00\x00\x00\x00" + b"\x00" * 8 + struct.pack(">II", timescale, duration_units),
    )
    hdlr = _box("hdlr", b"\x00\x00\x00\x00" + b"\x00" * 4 + b"vide")
    mdia = _box("mdia", mdhd + hdlr)
    trak = _box("trak", tkhd + mdia)
    moov = _box("moov", mvhd + trak)
    return ftyp + moov + _box("mdat", b"\x00" * 4)


def _ffmpeg_exe() -> str:
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg:
            return ffmpeg
    raise unittest.SkipTest("ffmpeg is required for MoviePy video generation coverage")


def _write_real_mp4(folder: Path, name: str = "source.mp4", duration: float = 4.0) -> Path:
    path = folder / name
    subprocess.run(
        [
            _ffmpeg_exe(),
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=black:s=640x360:d={duration}",
            "-pix_fmt",
            "yuv420p",
            str(path),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )
    return path


class VideoMetadataRegressionTestCase(unittest.TestCase):
    def write_sample_mp4(self, folder: Path, name: str = "sample.mp4") -> Path:
        path = folder / name
        path.write_bytes(_sample_mp4())
        return path

    def block_moviepy_imports(self, exc):
        real_import = builtins.__import__

        def blocked_import(name, *args, **kwargs):
            if name.startswith("moviepy"):
                raise exc
            return real_import(name, *args, **kwargs)

        return mock.patch("builtins.__import__", side_effect=blocked_import)

    def test_mp4_metadata_parser_reads_dimensions_and_duration(self):
        from instagrapi.utils.video import read_video_metadata

        with tempfile.TemporaryDirectory() as tmpdir:
            path = self.write_sample_mp4(Path(tmpdir))
            metadata = read_video_metadata(path)

        self.assertEqual(metadata.width, 720)
        self.assertEqual(metadata.height, 1280)
        self.assertAlmostEqual(metadata.duration, 3.5)

    def test_analyze_video_with_thumbnail_does_not_import_moviepy(self):
        import instagrapi.mixins.clip as clip_mixin
        import instagrapi.mixins.igtv as igtv_mixin
        import instagrapi.mixins.video as video_mixin

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            path = self.write_sample_mp4(tmpdir)
            thumbnail = tmpdir / "thumb.jpg"
            thumbnail.write_bytes(b"thumbnail")
            with self.block_moviepy_imports(AssertionError("moviepy should not be imported")):
                video_result = video_mixin.analyze_video(path, thumbnail=thumbnail)
                clip_result = clip_mixin.analyze_video(path, thumbnail=thumbnail)
                igtv_result = igtv_mixin.analyze_video(path, thumbnail=thumbnail)

        self.assertEqual(video_result[0:2], (720, 1280))
        self.assertAlmostEqual(video_result[2], 3.5)
        self.assertEqual(video_result[3], thumbnail)
        self.assertEqual(clip_result[0], thumbnail)
        self.assertEqual(clip_result[1:3], (720, 1280))
        self.assertAlmostEqual(clip_result[3], 3.5)
        self.assertEqual(igtv_result[0], thumbnail)
        self.assertEqual(igtv_result[1:3], (720, 1280))
        self.assertAlmostEqual(igtv_result[3], 3.5)

    def test_missing_thumbnail_reports_ffmpeg_fix(self):
        import instagrapi.mixins.video as video_mixin

        with tempfile.TemporaryDirectory() as tmpdir:
            path = self.write_sample_mp4(Path(tmpdir))
            with self.block_moviepy_imports(ImportError("no moviepy")):
                with self.assertRaises(RuntimeError) as ctx:
                    video_mixin.analyze_video(path)

        message = str(ctx.exception)
        self.assertIn("thumbnail=", message)
        self.assertIn("ffmpeg", message.lower())
        self.assertIn("IMAGEIO_FFMPEG_EXE", message)

    def test_missing_thumbnail_wraps_imageio_ffmpeg_error(self):
        import instagrapi.mixins.video as video_mixin

        imageio_error = RuntimeError(
            "No ffmpeg exe could be found. Install ffmpeg on your system, "
            "or set the IMAGEIO_FFMPEG_EXE environment variable."
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self.write_sample_mp4(Path(tmpdir))
            with self.block_moviepy_imports(imageio_error):
                with self.assertRaises(RuntimeError) as ctx:
                    video_mixin.analyze_video(path)

        message = str(ctx.exception)
        self.assertIn("Pass thumbnail=...", message)
        self.assertIn("IMAGEIO_FFMPEG_EXE", message)

    def test_core_install_does_not_require_moviepy(self):
        pyproject = Path("pyproject.toml").read_text()
        required_dependencies = pyproject.split("[project.optional-dependencies]", 1)[0]
        optional_dependencies = pyproject.split("[project.optional-dependencies]", 1)[1]

        self.assertNotIn("moviepy", required_dependencies)
        self.assertIn("video = [", optional_dependencies)
        self.assertIn('"imageio-ffmpeg>=0.2.0"', optional_dependencies)
        self.assertNotIn('"moviepy==1.0.3"', optional_dependencies)

    def test_story_builder_import_does_not_require_moviepy(self):
        sys.modules.pop("instagrapi.story", None)
        with self.block_moviepy_imports(ImportError("no moviepy")):
            try:
                story = importlib.import_module("instagrapi.story")
            except Exception as exc:
                self.fail(f"StoryBuilder import should not require MoviePy: {exc}")

        self.assertEqual(story.StoryBuilder(Path("photo.jpg")).path, Path("photo.jpg"))

    def test_story_builder_render_reports_video_extra_without_moviepy(self):
        sys.modules.pop("instagrapi.story", None)
        with self.block_moviepy_imports(ImportError("no moviepy")):
            story = importlib.import_module("instagrapi.story")
            with self.assertRaises(RuntimeError) as ctx:
                story.StoryBuilder(Path("video.mp4")).video()

        message = str(ctx.exception)
        self.assertIn("instagrapi[video]", message)
        self.assertIn("moviepy==2.2.1", message)
        self.assertIn("--no-deps", message)

    def test_prepare_video_reports_video_extra_without_moviepy(self):
        from instagrapi.image_util import prepare_video

        with self.block_moviepy_imports(ImportError("no moviepy")):
            with self.assertRaises(RuntimeError) as ctx:
                prepare_video("video.mp4")

        message = str(ctx.exception)
        self.assertIn("instagrapi[video]", message)
        self.assertIn("moviepy==2.2.1", message)
        self.assertIn("--no-deps", message)

    def test_story_builder_photo_generates_video_with_moviepy_2(self):
        from PIL import Image

        from instagrapi.story import StoryBuilder
        from instagrapi.utils.video import read_video_metadata

        self.assertEqual(importlib.metadata.version("moviepy"), "2.2.1")
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            image = tmpdir / "photo.jpg"
            Image.new("RGB", (720, 1280), "white").save(image)

            build = StoryBuilder(image, caption="MoviePy 2").photo(max_duration=1, link="https://example.com")
            try:
                output = Path(build.path)
                self.assertTrue(output.exists())
                self.assertGreater(output.stat().st_size, 0)
                metadata = read_video_metadata(output)
                self.assertEqual((metadata.width, metadata.height), (720, 1280))
                self.assertAlmostEqual(metadata.duration, 1.0, delta=0.25)
            finally:
                with contextlib.suppress(FileNotFoundError):
                    os.unlink(build.path)

    def test_prepare_video_generates_thumbnail_with_moviepy_2(self):
        from instagrapi.image_util import prepare_video

        self.assertEqual(importlib.metadata.version("moviepy"), "2.2.1")
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _write_real_mp4(Path(tmpdir))
            video_data, size, duration, thumbnail_data = prepare_video(
                str(path),
                max_size=None,
                aspect_ratios=None,
                skip_reencoding=True,
            )

        self.assertGreater(len(video_data), 0)
        self.assertEqual(size, [640, 360])
        self.assertAlmostEqual(duration, 4.0, delta=0.25)
        self.assertGreater(len(thumbnail_data), 0)
