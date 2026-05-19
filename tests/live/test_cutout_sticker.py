from tests import helpers as _helpers
from tests.helpers import *


class ClientCutoutStickerTestCase(_helpers.ClientPrivateTestCase):
    """Test cases for Cutout Sticker functionality (PR #2342)"""

    def __init__(self, *args, **kwargs):
        self.cl = None
        return unittest.TestCase.__init__(self, *args, **kwargs)

    def test_photo_upload_to_cutout_sticker_bypass_ai(self):
        """Test uploading a photo as cutout sticker with AI bypass (full image selection)"""
        path = self.copy_media_fixture("examples/kanada.jpg")
        self.assertIsInstance(path, Path)
        media = None
        try:
            # Upload as cutout sticker with bypass_ai=True (default)
            media = self.cl.photo_upload_to_cutout_sticker(path, bypass_ai=True)
            self.assertIsInstance(media, Media)
            # Cutout stickers should have product_type "custom_sticker"
            self.assertEqual(media.product_type, "custom_sticker")
            self.assertUploadedMediaAccessible(media, media_type=1, product_type="custom_sticker")
        finally:
            if media:
                self.cl.media_delete(media.id)

    def test_photo_upload_to_cutout_sticker_with_ai(self):
        """Test uploading a photo as cutout sticker with AI detection"""
        path = self.copy_media_fixture("examples/kanada.jpg")
        self.assertIsInstance(path, Path)
        media = None
        try:
            # Upload as cutout sticker with AI detection
            media = self.cl.photo_upload_to_cutout_sticker(path, bypass_ai=False)
            self.assertIsInstance(media, Media)
            self.assertEqual(media.product_type, "custom_sticker")
            self.assertUploadedMediaAccessible(media, media_type=1, product_type="custom_sticker")
        finally:
            if media:
                self.cl.media_delete(media.id)
