from tests import helpers as _helpers
from tests.helpers import *


class ClientCutoutStickerTestCase(_helpers.ClientPrivateTestCase):
    """Test cases for Cutout Sticker functionality (PR #2342)"""

    def test_photo_upload_to_cutout_sticker_bypass_ai(self):
        """Test uploading a photo as cutout sticker with AI bypass (full image selection)"""
        # Download a test photo
        media_pk = self.cl.media_pk_from_url("https://www.instagram.com/p/BVDOOolFFxg/")
        path = self.cl.photo_download(media_pk)
        self.assertIsInstance(path, Path)
        media = None
        try:
            # Upload as cutout sticker with bypass_ai=True (default)
            media = self.cl.photo_upload_to_cutout_sticker(path, bypass_ai=True)
            self.assertIsInstance(media, Media)
            # Cutout stickers should have product_type "custom_sticker"
            self.assertEqual(media.product_type, "custom_sticker")
        finally:
            cleanup(path)
            if media:
                self.cl.media_delete(media.id)

    def test_photo_upload_to_cutout_sticker_with_ai(self):
        """Test uploading a photo as cutout sticker with AI detection"""
        # Download a test photo
        media_pk = self.cl.media_pk_from_url("https://www.instagram.com/p/BVDOOolFFxg/")
        path = self.cl.photo_download(media_pk)
        self.assertIsInstance(path, Path)
        media = None
        try:
            # Upload as cutout sticker with AI detection
            media = self.cl.photo_upload_to_cutout_sticker(path, bypass_ai=False)
            self.assertIsInstance(media, Media)
            self.assertEqual(media.product_type, "custom_sticker")
        finally:
            cleanup(path)
            if media:
                self.cl.media_delete(media.id)
