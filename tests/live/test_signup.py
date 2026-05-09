from tests.helpers import *


class SignUpTestCase(unittest.TestCase):
    def test_signup(self):
        cl = Client()
        username = gen_password()
        password = gen_password(12)
        email = f"{username}@gmail.com"
        phone_number = os.environ.get("IG_PHONE_NUMBER")
        full_name = f"John {username}"
        user = cl.signup(
            username,
            password,
            email,
            phone_number,
            full_name,
            year=random.randint(1980, 1990),
            month=random.randint(1, 12),
            day=random.randint(1, 30),
        )
        self.assertIsInstance(user, UserShort)
        for key, val in {"username": username, "full_name": full_name}.items():
            self.assertEqual(getattr(user, key), val)
        self.assertTrue(user.profile_pic_url.startswith("https://"))
