from tests.helpers import *


class TempfileHelperRegressionTestCase(unittest.TestCase):
    """Verify the safe-tempfile helper actually creates the file (TOCTOU
    fix for the previous ``tempfile.mktemp`` usage that was flagged by
    CodeQL ``py/insecure-temporary-file``)."""

    def test_clip_helper_creates_file_with_suffix(self):
        from instagrapi.mixins.clip import _make_tmp_path

        path = _make_tmp_path(".m4a")
        try:
            self.assertTrue(os.path.exists(path))
            self.assertTrue(path.endswith(".m4a"))
        finally:
            os.remove(path)

    def test_clip_helper_returns_unique_paths(self):
        from instagrapi.mixins.clip import _make_tmp_path

        a = _make_tmp_path(".mp4")
        b = _make_tmp_path(".mp4")
        try:
            self.assertNotEqual(a, b)
        finally:
            os.remove(a)
            os.remove(b)

    def test_story_helper_creates_file_with_suffix(self):
        from instagrapi.story import _make_tmp_path

        path = _make_tmp_path(".mp4")
        try:
            self.assertTrue(os.path.exists(path))
            self.assertTrue(path.endswith(".mp4"))
        finally:
            os.remove(path)
