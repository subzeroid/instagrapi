import os
import unittest

from tests import helpers as _helpers
from tests.helpers import *

INSTAGRAM_USER_ID = "25025320"


class ClientFbSearchLiveTestCase(unittest.TestCase):
    def live_client(self):
        if not TEST_ACCOUNTS_URL:
            self.skipTest("TEST_ACCOUNTS_URL is required for fbsearch live tests")
        last_error = None
        for account in _helpers.fetch_test_accounts(count=20):
            try:
                cl = Client(settings=dict(account["client_settings"]), proxy=os.getenv("IG_PROXY") or account["proxy"])
                cl._user_id = account.get("user_id")
                cl.fbsearch_topsearch_v2("instagram")
                return cl
            except Exception as exc:
                last_error = f"{type(exc).__name__}: {str(exc)[:120]}"
        self.skipTest(f"Could not build a usable fbsearch test client: {last_error}")

    def test_fbsearch_suggested_profiles_returns_user_short_live(self):
        cl = self.live_client()

        users = cl.fbsearch_suggested_profiles(INSTAGRAM_USER_ID)

        if not users:
            self.skipTest("Instagram returned no suggested profiles")
        self.assertIsInstance(users[0], UserShort)
        self.assertIsInstance(users[0].stories, list)

    def test_media_search_returns_media_live(self):
        cl = self.live_client()

        medias = cl.media_search("space", amount=3)

        if not medias:
            self.skipTest("Instagram returned no media search results")
        self.assertLessEqual(len(medias), 3)
        self.assertIsInstance(medias[0], Media)
        self.assertTrue(medias[0].pk)
        self.assertTrue(medias[0].code)
