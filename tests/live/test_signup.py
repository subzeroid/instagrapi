from tests.helpers import *


class SignUpTestCase(unittest.TestCase):
    def run_signup_command(self, command, context):
        env = os.environ.copy()
        env.update({key: value for key, value in context.items() if value})
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
        return result.stdout.strip()

    def signup_email(self, username):
        email = os.environ.get("IG_SIGNUP_EMAIL")
        if email:
            return email
        command = os.environ.get("IG_SIGNUP_EMAIL_COMMAND")
        if not command:
            self.skipTest("IG_SIGNUP_EMAIL or IG_SIGNUP_EMAIL_COMMAND is required for email signup live test")
        email = self.run_signup_command(command, {"IG_SIGNUP_USERNAME": username})
        if not email:
            self.skipTest("IG_SIGNUP_EMAIL_COMMAND did not return an email address")
        return email

    def signup_phone_number(self):
        return os.environ.get("IG_SIGNUP_PHONE_NUMBER") or os.environ.get("IG_PHONE_NUMBER")

    def signup_code_handler(self, code_env, command_env, context):
        code = os.environ.get(code_env)
        if code:
            return code
        command = os.environ.get(command_env)
        if not command:
            self.skipTest(f"{code_env} or {command_env} is required for signup live tests")
        code = self.run_signup_command(command, context)
        if not code:
            self.skipTest(f"{command_env} did not return a signup code")
        return code

    def test_email_signup_live(self):
        cl = Client()
        username = gen_password()
        email = self.signup_email(username)
        password = gen_password(12)
        phone_number = self.signup_phone_number()
        full_name = f"John {username}"
        cl.challenge_code_handler = lambda username, choice: self.signup_code_handler(
            "IG_SIGNUP_EMAIL_CODE",
            "IG_SIGNUP_EMAIL_CODE_COMMAND",
            {
                "IG_SIGNUP_USERNAME": username,
                "IG_SIGNUP_EMAIL": email,
            },
        )
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

    def test_email_signup_caa_live(self):
        cl = Client()
        username = gen_password()
        email = self.signup_email(username)
        password = gen_password(12)
        full_name = f"John {username}"
        cl.challenge_code_handler = lambda username, choice: self.signup_code_handler(
            "IG_SIGNUP_EMAIL_CODE",
            "IG_SIGNUP_EMAIL_CODE_COMMAND",
            {
                "IG_SIGNUP_USERNAME": username,
                "IG_SIGNUP_EMAIL": email,
            },
        )
        user = cl.signup_caa_email(
            username,
            password,
            email,
            full_name,
            year=random.randint(1980, 1990),
            month=random.randint(1, 12),
            day=random.randint(1, 28),
        )
        self.assertIsInstance(user, UserShort)
        for key, val in {"username": username, "full_name": full_name}.items():
            self.assertEqual(getattr(user, key), val)
        self.assertTrue(user.profile_pic_url.startswith("https://"))

    def test_phone_signup_live(self):
        phone_number = self.signup_phone_number()
        if not phone_number:
            self.skipTest("IG_SIGNUP_PHONE_NUMBER or IG_PHONE_NUMBER is required for phone signup live test")
        cl = Client()
        username = gen_password()
        password = gen_password(12)
        full_name = f"John {username}"
        cl.challenge_code_handler = lambda username, choice: self.signup_code_handler(
            "IG_SIGNUP_SMS_CODE",
            "IG_SIGNUP_SMS_CODE_COMMAND",
            {
                "IG_SIGNUP_USERNAME": username,
                "IG_SIGNUP_PHONE_NUMBER": phone_number,
            },
        )
        user = cl.signup(
            username,
            password,
            email="",
            phone_number=phone_number,
            full_name=full_name,
            year=random.randint(1980, 1990),
            month=random.randint(1, 12),
            day=random.randint(1, 30),
        )
        self.assertIsInstance(user, UserShort)
        for key, val in {"username": username, "full_name": full_name}.items():
            self.assertEqual(getattr(user, key), val)
        self.assertTrue(user.profile_pic_url.startswith("https://"))
