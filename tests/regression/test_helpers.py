from tests import helpers as helper_module
from tests.helpers import *


class LiveAccountHelperRegressionTestCase(unittest.TestCase):
    def test_build_test_accounts_url_overrides_existing_default_count(self):
        case = object.__new__(helper_module.ClientPrivateTestCase)
        with mock.patch.object(
            helper_module,
            "TEST_ACCOUNTS_URL",
            "https://accounts.example.test/take?pool=live&count=1",
        ):
            url = case.build_test_accounts_url()

        self.assertEqual(url, "https://accounts.example.test/take?pool=live&count=5")

    def test_build_test_accounts_url_uses_requested_count(self):
        case = object.__new__(helper_module.ClientPrivateTestCase)
        with mock.patch.object(
            helper_module,
            "TEST_ACCOUNTS_URL",
            "https://accounts.example.test/take?pool=live&count=1",
        ):
            url = case.build_test_accounts_url(count=8)

        self.assertEqual(url, "https://accounts.example.test/take?pool=live&count=8")
