from tests import helpers as helper_module
from tests.helpers import *


class LiveAccountHelperRegressionTestCase(unittest.TestCase):
    def _account_payload(self, username="fresh.account"):
        return {
            "client_settings": {},
            "username": username,
            "password": "password",
            "proxy": "",
            "user_id": "123",
        }

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

    def test_client_private_fresh_account_uses_shared_helper(self):
        case = object.__new__(helper_module.ClientPrivateTestCase)
        client = object()

        with mock.patch.object(helper_module, "fresh_test_account", return_value=client) as fresh_test_account:
            result = case.fresh_account()

        self.assertIs(result, client)
        fresh_test_account.assert_called_once_with()

    def test_client_private_fresh_accounts_uses_shared_helper(self):
        case = object.__new__(helper_module.ClientPrivateTestCase)
        clients = [object()]
        exclude_user_ids = {"123"}

        with mock.patch.object(helper_module, "fresh_test_accounts", return_value=clients) as fresh_test_accounts:
            result = case.fresh_accounts(1, exclude_user_ids=exclude_user_ids)

        self.assertIs(result, clients)
        fresh_test_accounts.assert_called_once_with(1, exclude_user_ids=exclude_user_ids)

    @unittest.skipUnless(hasattr(signal, "SIGALRM"), "SIGALRM is required for login timeout guard")
    def test_client_from_test_account_times_out_hung_login(self):
        client = Mock()
        client.login.side_effect = lambda **kwargs: time.sleep(1)

        with mock.patch.dict(helper_module.os.environ, {"INSTAGRAPI_TEST_LOGIN_TIMEOUT": "0.01", "IG_PROXY": ""}):
            with mock.patch.object(helper_module, "Client", return_value=client):
                with self.assertRaises(helper_module.FreshAccountLoginTimeout):
                    helper_module.client_from_test_account(self._account_payload())

    def test_fresh_test_account_tries_next_account_after_login_timeout(self):
        accounts = [self._account_payload("first.account"), self._account_payload("second.account")]
        client = object()

        with mock.patch.object(helper_module, "fetch_test_accounts", return_value=accounts):
            with mock.patch.object(
                helper_module,
                "client_from_test_account",
                side_effect=[helper_module.FreshAccountLoginTimeout("timeout"), client],
            ) as client_from_test_account:
                result = helper_module.fresh_test_account(count=2, attempts=2)

        self.assertIs(result, client)
        self.assertEqual(client_from_test_account.call_count, 2)
