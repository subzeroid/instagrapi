from tests import helpers as _helpers
from tests.helpers import *


class TOTPTestCase(_helpers.ClientPrivateTestCase):
    def test_totp_code(self):
        seed = self.cl.totp_generate_seed()
        code = self.cl.totp_generate_code(seed)
        self.assertIsInstance(code, str)
        self.assertTrue(code.isdigit())
        self.assertEqual(len(code), 6)
