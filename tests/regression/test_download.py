from tests.helpers import *


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
