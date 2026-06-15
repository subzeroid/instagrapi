import io

from instagrapi.exceptions import ClientForbiddenError, ClientIncompleteReadError
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
    def _photo_media(self, media_pk="2936202982639873318", thumbnail_url="https://example.com/photo.jpg"):
        return Media(
            pk=media_pk,
            id=f"{media_pk}_50838397751",
            code="Ci_fQ5YsS0m",
            taken_at=datetime(2026, 1, 1),
            media_type=1,
            user=UserShort(
                pk="50838397751",
                username="example",
                profile_pic_url="https://example.com/profile.jpg",
            ),
            like_count=0,
            caption_text="",
            usertags=[],
            sponsor_tags=[],
            thumbnail_url=thumbnail_url,
        )

    def _video_media(self, media_pk="3903542582802212941"):
        return Media(
            pk=media_pk,
            id=f"{media_pk}_50838397751",
            code="DYsK0wViWhN",
            taken_at=datetime(2026, 1, 1),
            media_type=2,
            user=UserShort(
                pk="50838397751",
                username="example",
                profile_pic_url="https://example.com/profile.jpg",
            ),
            like_count=0,
            caption_text="",
            usertags=[],
            sponsor_tags=[],
            video_url="https://example.com/video.mp4",
        )

    def test_video_download_uses_private_media_info_lookup(self):
        client = Client()
        media = self._video_media()
        expected = Path("/tmp/example.mp4")

        with mock.patch.object(
            client, "media_info", side_effect=AssertionError("public-first media_info")
        ) as media_info:
            with mock.patch.object(client, "media_info_v1", return_value=media) as media_info_v1:
                with mock.patch.object(client, "video_download_by_url", return_value=expected) as download_by_url:
                    result = client.video_download(media.pk, folder="/tmp", overwrite=False)

        media_info.assert_not_called()
        media_info_v1.assert_called_once_with(media.pk)
        download_by_url.assert_called_once_with(
            media.video_url,
            f"example_{media.pk}",
            "/tmp",
            overwrite=False,
        )
        self.assertEqual(result, expected)

    def test_photo_download_prefers_public_gql_media_info_lookup(self):
        client = Client()
        media_pk = "2936202982639873318"
        public_media = self._photo_media(media_pk, "https://example.com/public-1440.jpg")
        private_media = self._photo_media(media_pk, "https://example.com/private-1080.jpg")
        expected = Path("/tmp/example.jpg")

        with mock.patch.object(client, "media_info_gql", return_value=public_media) as media_info_gql:
            with mock.patch.object(client, "media_info", return_value=private_media) as media_info:
                with mock.patch.object(client, "photo_download_by_url", return_value=expected) as download_by_url:
                    result = client.photo_download(media_pk, folder="/tmp", overwrite=False)

        media_info_gql.assert_called_once_with(media_pk)
        media_info.assert_not_called()
        download_by_url.assert_called_once_with(
            str(public_media.thumbnail_url),
            f"example_{media_pk}",
            "/tmp",
            overwrite=False,
        )
        self.assertEqual(result, expected)

    def test_photo_download_falls_back_to_media_info_when_public_gql_is_gated(self):
        client = Client()
        media_pk = "2936202982639873318"
        private_media = self._photo_media(media_pk, "https://example.com/private-1080.jpg")
        expected = Path("/tmp/example.jpg")

        with mock.patch.object(client, "media_info_gql", side_effect=ClientForbiddenError("gated")) as media_info_gql:
            with mock.patch.object(client, "media_info", return_value=private_media) as media_info:
                with mock.patch.object(client, "photo_download_by_url", return_value=expected) as download_by_url:
                    result = client.photo_download(media_pk, folder="/tmp", overwrite=False)

        media_info_gql.assert_called_once_with(media_pk)
        media_info.assert_called_once_with(media_pk)
        download_by_url.assert_called_once_with(
            str(private_media.thumbnail_url),
            f"example_{media_pk}",
            "/tmp",
            overwrite=False,
        )
        self.assertEqual(result, expected)

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
