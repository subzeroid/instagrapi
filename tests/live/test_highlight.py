from tests import helpers as _helpers
from tests.helpers import *


class ClientHighlightTestCase(_helpers.ClientPrivateTestCase):
    def test_highlight_pk_from_url(self):
        highlight_pk = self.cl.highlight_pk_from_url("https://www.instagram.com/stories/highlights/17983407089364361/")
        self.assertEqual(highlight_pk, "17983407089364361")

    def test_highlight_info(self):
        highlight = self.cl.highlight_info(17983407089364361)
        self.assertIsInstance(highlight, Highlight)
        self.assertEqual(highlight.pk, "17983407089364361")
        self.assertTrue(len(highlight.items) > 0)
        self.assertEqual(len(highlight.items), highlight.media_count)
        self.assertEqual(len(highlight.items), len(highlight.media_ids))
