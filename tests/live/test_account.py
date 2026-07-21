from tests import helpers as _helpers
from tests.helpers import *


class ClientAccountTestCase(_helpers.ClientPrivateTestCase):
    @unittest.skipUnless(os.getenv("IG_RUN_AI_INFO_LIVE"), "set IG_RUN_AI_INFO_LIVE=1 to run the account mutation test")
    def test_account_set_ai_info(self):
        enabled = self.cl.account_set_ai_info(True)
        self.assertIsInstance(enabled, Account)

        disabled = self.cl.account_set_ai_info(False)
        self.assertIsInstance(disabled, Account)

    def test_account_edit(self):
        # current
        one = self.cl.user_info(self.cl.user_id)
        self.assertIsInstance(one, User)
        # change
        url = "https://trotiq.com/"
        two = self.cl.account_edit(external_url=url)
        self.assertIsInstance(two, Account)
        self.assertEqual(str(two.external_url), url)
        # return back
        three = self.cl.account_edit(external_url=one.external_url)
        self.assertIsInstance(three, Account)
        self.assertEqual(one.external_url, three.external_url)

    def test_account_change_picture(self):
        # current
        one = self.cl.user_info(self.cl.user_id)
        self.assertIsInstance(one, User)
        instagram = self.user_info_by_username("instagram")
        # change
        two = self.cl.account_change_picture(self.cl.photo_download_by_url(instagram.profile_pic_url))
        self.assertIsInstance(two, UserShort)
        # return back
        three = self.cl.account_change_picture(self.cl.photo_download_by_url(one.profile_pic_url))
        self.assertIsInstance(three, UserShort)
