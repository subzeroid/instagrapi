from instagrapi.types import StoryArchiveDay
from tests import helpers as _helpers
from tests.helpers import *


class ClientArchiveLiveTestCase(_helpers.ClientPrivateTestCase):
    _live_client = None
    _live_account_error = None

    def __init__(self, *args, **kwargs):
        self.cl = None
        return unittest.TestCase.__init__(self, *args, **kwargs)

    def setup_method(self, *args, **kwargs):
        return None

    def setUp(self):
        if not TEST_ACCOUNTS_URL:
            self.skipTest("Dedicated live account is required for archive tests")
        if self.__class__._live_account_error:
            self.skipTest(self.__class__._live_account_error)
        if self.__class__._live_client:
            self.cl = self.__class__._live_client
            return
        try:
            self.cl = self.fresh_account()
        except Exception as exc:
            self.__class__._live_account_error = f"Could not prepare live account: {exc.__class__.__name__}"
            self.skipTest(self.__class__._live_account_error)
        self.__class__._live_client = self.cl

    def test_archive_medias(self):
        media = None
        try:
            media = self.cl.photo_upload(Path("examples/kanada.jpg"), "")
            self.assertIsInstance(media, Media)
            self.assertTrue(self.cl.media_archive(media.id))

            archived = self.cl.archive_medias(amount=10)
            self.assertIn(media.pk, [item.pk for item in archived])

            self.assertTrue(self.cl.media_unarchive(media.id))
            archived = self.cl.archive_medias(amount=10)
            self.assertNotIn(media.pk, [item.pk for item in archived])
        finally:
            if media:
                try:
                    self.cl.media_unarchive(media.id)
                except Exception:
                    pass
                self.assertTrue(self.cl.media_delete(media.id))

    def test_archive_story_days(self):
        days = self.cl.archive_story_days(amount=1)
        self.assertIsInstance(days, list)
        if days:
            self.assertIsInstance(days[0], StoryArchiveDay)

    def test_archive_stories(self):
        days = self.cl.archive_story_days(amount=1)
        if not days:
            self.skipTest("Story archive is empty")

        stories = self.cl.archive_stories(amount=1)
        self.assertIsInstance(stories, list)
        if stories:
            self.assertIsInstance(stories[0], Story)
