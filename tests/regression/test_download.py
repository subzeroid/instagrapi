import io

from instagrapi.exceptions import ClientIncompleteReadError
from tests.helpers import *


class _RawBytes(io.BytesIO):
    decode_content = False


class _DownloadResponse:
    def __init__(self, content: bytes, content_length: int | str | None = None):
        self.content = content
        self.raw = _RawBytes(content)
        self.headers = {}
        if content_length is not None:
            self.headers["Content-Length"] = str(content_length)
        self.status_code = 200
        self.url = "https://example.com/media.bin"

    def raise_for_status(self):
        return None


class DownloadRegressionTestCase(unittest.TestCase):
    def test_photo_download_by_url_skips_existing_file_when_overwrite_disabled(self):
        client = Client()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "photo.jpg"
            path.write_bytes(b"existing-photo")

            with mock.patch("instagrapi.mixins.photo.requests.get") as get:
                result = client.photo_download_by_url(
                    "https://example.com/photo.jpg",
                    folder=tmpdir,
                    overwrite=False,
                )

            get.assert_not_called()
            self.assertEqual(result, path.resolve())
            self.assertEqual(path.read_bytes(), b"existing-photo")

    def test_video_download_by_url_skips_existing_file_when_overwrite_disabled(self):
        client = Client()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "video.mp4"
            path.write_bytes(b"existing-video")

            with mock.patch("instagrapi.mixins.video.requests.get") as get:
                result = client.video_download_by_url(
                    "https://example.com/video.mp4",
                    folder=tmpdir,
                    overwrite=False,
                )

            get.assert_not_called()
            self.assertEqual(result, path.resolve())
            self.assertEqual(path.read_bytes(), b"existing-video")

    def test_album_download_by_urls_propagates_overwrite_flag(self):
        client = Client()
        with mock.patch.object(client, "photo_download_by_url") as photo_download:
            with mock.patch.object(client, "video_download_by_url") as video_download:
                client.album_download_by_urls(
                    [
                        "https://example.com/picture.jpg",
                        "https://example.com/movie.mp4",
                    ],
                    folder="/tmp",
                    overwrite=False,
                )

        photo_download.assert_called_once_with(
            "https://example.com/picture.jpg",
            "picture.jpg",
            "/tmp",
            overwrite=False,
        )
        video_download.assert_called_once_with(
            "https://example.com/movie.mp4",
            "movie.mp4",
            "/tmp",
            overwrite=False,
        )

    def test_photo_download_by_url_rejects_incomplete_content_length(self):
        client = Client()
        response = _DownloadResponse(b"short", content_length=10)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "photo.jpg"

            with mock.patch("instagrapi.mixins.photo.requests.get", return_value=response):
                with self.assertRaises(ClientIncompleteReadError) as ctx:
                    client.photo_download_by_url("https://example.com/photo.jpg", folder=tmpdir)

            self.assertFalse(path.exists())
            self.assertIn('Broken file "{}"'.format(path), str(ctx.exception))
            self.assertIn("Content-length=10, but file length=5", str(ctx.exception))

    def test_photo_download_by_url_origin_rejects_incomplete_content_length(self):
        client = Client()
        response = _DownloadResponse(b"short", content_length=10)

        with mock.patch("instagrapi.mixins.photo.requests.get", return_value=response):
            with self.assertRaises(ClientIncompleteReadError) as ctx:
                client.photo_download_by_url_origin("https://example.com/photo.jpg")

        self.assertIn('Broken file from url "https://example.com/photo.jpg"', str(ctx.exception))
        self.assertIn("Content-length=10, but file length=5", str(ctx.exception))

    def test_story_download_by_url_rejects_incomplete_content_length(self):
        client = Client()
        response = _DownloadResponse(b"short", content_length=10)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "story.mp4"

            with mock.patch.object(client, "_send_public_request", return_value=response):
                with self.assertRaises(ClientIncompleteReadError) as ctx:
                    client.story_download_by_url("https://example.com/story.mp4", folder=tmpdir)

            self.assertFalse(path.exists())
            self.assertIn('Broken file "{}"'.format(path), str(ctx.exception))
