import os
import tempfile

from PIL import Image

from instagrapi.exceptions import ClientError
from tests import helpers as _helpers
from tests.helpers import *


class ClientPhotoDownloadLiveTestCase(unittest.TestCase):
    def photo_clients(self):
        try:
            import curl_adapter  # noqa: F401
        except ImportError:
            pass
        else:
            yield (
                "anonymous/curl",
                Client(
                    public_transport="curl",
                    request_timeout=1,
                    public_request_retries_count=1,
                ),
            )

        yield (
            "anonymous/requests",
            Client(
                public_transport="requests",
                request_timeout=1,
                public_request_retries_count=1,
            ),
        )

        if not TEST_ACCOUNTS_URL:
            return

        for idx, account in enumerate(_helpers.fetch_test_accounts(count=3, timeout=20)[:3], start=1):
            settings = dict(account["client_settings"])
            settings.pop("totp_seed", None)
            yield (
                f"saved-session/{idx}",
                Client(
                    settings=settings,
                    proxy=os.getenv("IG_PROXY") or account.get("proxy"),
                    override_app_version=True,
                    request_timeout=1,
                    public_request_retries_count=1,
                ),
            )

    def test_photo_download_public_highest_resolution_live(self):
        media_pk = Client().media_pk_from_code("Ci_fQ5YsS0m")
        errors = []
        for label, cl in self.photo_clients():
            try:
                media = cl.media_info_gql(media_pk)
                self.assertEqual(media.media_type, 1)
                self.assertTrue(media.thumbnail_url)
                cl.request_timeout = 20
                with tempfile.TemporaryDirectory() as tmpdir:
                    with (
                        mock.patch.object(cl, "media_info_gql", return_value=media) as media_info_gql,
                        mock.patch.object(cl, "media_info", side_effect=AssertionError("media_info fallback used")),
                    ):
                        path = cl.photo_download(media_pk, folder=tmpdir)
                    media_info_gql.assert_called_once_with(media_pk)
                    with Image.open(path) as image:
                        width, height = image.size
            except ClientError as exc:
                errors.append(f"{label}: {exc.__class__.__name__}")
                continue
            break
        else:
            self.skipTest("Instagram public media info endpoint is gated: " + "; ".join(errors))

        self.assertGreaterEqual(width, 1080)
        self.assertGreaterEqual(height, 1080)
