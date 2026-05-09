from tests import helpers as _helpers
from tests.helpers import *


class ClientShareTestCase(_helpers.ClientPrivateTestCase):
    def test_share_code_from_url(self):
        url = "https://www.instagram.com/s/aGlnaGxpZ2h0OjE3OTMzOTExODE2NTY4Njcx?utm_medium=share_sheet"
        code = self.cl.share_code_from_url(url)
        self.assertEqual(code, "aGlnaGxpZ2h0OjE3OTMzOTExODE2NTY4Njcx")

    def test_share_info_by_url(self):
        url = "https://www.instagram.com/s/aGlnaGxpZ2h0OjE3OTMzOTExODE2NTY4Njcx?utm_medium=share_sheet"
        share = self.cl.share_info_by_url(url)
        self.assertIsInstance(share, Share)
        self.assertEqual(share.pk, "17933911816568671")
        self.assertEqual(share.type, "highlight")

    def test_share_info(self):
        share = self.cl.share_info("aGlnaGxpZ2h0OjE3OTMzOTExODE2NTY4Njcx")
        self.assertIsInstance(share, Share)
        self.assertEqual(share.pk, "17933911816568671")
        self.assertEqual(share.type, "highlight")
        # UnicodeDecodeError: 'utf-8' codec can't decode byte 0xb1 in position 6: invalid start byte
        share = self.cl.share_info("aGlnaGxpsdsdZ2h0OjE3OTg4MDg5NjI5MzgzNzcw")
        self.assertIsInstance(share, Share)
        self.assertEqual(share.pk, "17988089629383770")
        self.assertEqual(share.type, "highlight")
