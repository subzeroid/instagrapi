from instagrapi.exceptions import FeedbackRequired, SignupSpamError
from instagrapi.mixins.challenge import ChallengeChoice
from instagrapi.mixins.signup import CHOICE_EMAIL
from tests.helpers import *
from tests.live.test_signup import SignUpTestCase


class PasswordEncryptionRegressionTestCase(unittest.TestCase):
    def test_password_enrypt(self):
        cl = Client()
        enc_password = cl.password_encrypt("test")
        parts = enc_password.split(":")
        self.assertEqual(parts[0], "#PWD_INSTAGRAM")
        self.assertEqual(parts[1], "4")
        self.assertTrue(int(parts[2]) > 1607612345)
        self.assertTrue(len(parts[3]) == 392)


class SignupHelperRegressionTestCase(unittest.TestCase):
    def caa_response(
        self,
        reg_info='{"contactpoint":"addr@example.com"}',
        reg_context="ctx-1",
        email_token="email-token-1",
        registration_response=None,
    ):
        escaped_reg_info = reg_info.replace('"', '\\"')
        chunks = [
            (
                '(f4i (dkc "reg_info" "reg_context" "email_token") '
                f'(dkc "{escaped_reg_info}" "{reg_context}" "{email_token}"))'
            )
        ]
        if registration_response:
            response_json = json.dumps(
                {"registration_response": json.dumps(registration_response, separators=(",", ":"))}
            )
            chunks.append(f"(dsh (fom 1 1 {json.dumps(response_json)}))")
        return {
            "layout": {
                "bloks_payload": {
                    "ft": {"state": " ".join(chunks)},
                }
            },
            "status": "ok",
        }

    def test_caa_extract_state_reads_bloks_dkc_maps_and_registration_response(self):
        client = Client()
        registration_response = {
            "account_created": True,
            "created_user": {
                "pk": "123",
                "username": "example",
                "full_name": "Example User",
                "profile_pic_url": "https://example.com/avatar.jpg",
            },
        }

        state = client._caa_extract_state(self.caa_response(registration_response=registration_response))

        self.assertEqual(state["reg_context"], "ctx-1")
        self.assertEqual(state["email_token"], "email-token-1")
        self.assertEqual(state["reg_info"], '{"contactpoint":"addr@example.com"}')
        self.assertEqual(state["registration_response"], registration_response)

    def test_caa_extract_state_reads_graphql_bloks_bundle_action(self):
        client = Client()
        response = {
            "data": {
                "1$bloks_action(bk_context:$bk_context,params:$params)": {
                    "action": {
                        "action_bundle": {
                            "bloks_bundle_action": json.dumps(
                                self.caa_response(reg_context="ctx-from-graphql", email_token="token-from-graphql"),
                                separators=(",", ":"),
                            )
                        }
                    }
                }
            }
        }

        state = client._caa_extract_state(response)

        self.assertEqual(state["reg_context"], "ctx-from-graphql")
        self.assertEqual(state["email_token"], "token-from-graphql")

    def test_signup_caa_email_runs_modern_email_flow(self):
        client = Client()
        client.uuid = "uuid-1"
        client.phone_id = "family-device-id"
        client.android_device_id = "android-id"
        client.mid = "machine-id"
        client.bloks_versioning_id = "bloks-version"
        client.waterfall_id = "waterfall-id"
        client.wait_seconds = 0
        client.challenge_code_handler = mock.Mock(return_value="123456")
        registration_response = {
            "account_created": True,
            "created_user": {
                "pk": "123",
                "username": "example",
                "full_name": "Example User",
                "profile_pic_url": "https://example.com/avatar.jpg",
            },
        }
        graphql_responses = [
            self.caa_response(reg_context=f"ctx-gql-{index}", email_token=f"email-token-{index}") for index in range(8)
        ]
        graphql_responses.append(self.caa_response(registration_response=registration_response))
        async_responses = [
            self.caa_response(reg_context=f"ctx-async-{index}", email_token=f"email-token-async-{index}")
            for index in range(4)
        ]

        with mock.patch.object(client, "caa_reg_graphql", side_effect=graphql_responses) as caa_reg_graphql:
            with mock.patch.object(client, "caa_reg_async_action", side_effect=async_responses) as caa_reg_async_action:
                user = client.signup_caa_email(
                    username="example",
                    password="password",
                    email="addr@example.com",
                    full_name="Example User",
                    year=1995,
                    month=6,
                    day=9,
                )

        self.assertIsInstance(user, UserShort)
        self.assertEqual(user.pk, "123")
        self.assertEqual(user.username, "example")
        self.assertEqual(user.full_name, "Example User")
        self.assertEqual(
            [call.args[0] for call in caa_reg_graphql.call_args_list],
            [
                "com.bloks.www.bloks.caa.reg.aymh_create_account_button.async",
                "com.bloks.www.bloks.caa.reg.async.contactpoint_prefill.async",
                "com.bloks.www.bloks.caa.reg.contactpoint_phone",
                "com.bloks.www.bloks.caa.reg.contactpoint_email",
                "com.bloks.www.bloks.caa.reg.confirmation.async",
                "com.bloks.www.bloks.caa.reg.password.async",
                "com.bloks.www.bloks.caa.reg.birthday.async",
                "com.bloks.www.bloks.caa.reg.username.async",
                "com.bloks.www.bloks.caa.reg.create.account.async",
            ],
        )
        self.assertEqual(
            [call.args[0] for call in caa_reg_async_action.call_args_list],
            [
                "com.bloks.www.bloks.caa.reg.async.expose_ntm_experiment.async",
                "com.bloks.www.bloks.caa.reg.async.contactpoint_email_new.async",
                "com.bloks.www.bloks.caa.reg.send_confirmation_email.async",
                "com.bloks.www.bloks.caa.reg.name_vtwo.async",
            ],
        )
        client.challenge_code_handler.assert_called_once_with("example", CHOICE_EMAIL)
        password_call = caa_reg_graphql.call_args_list[5]
        self.assertRegex(
            password_call.kwargs["client_input_params"]["encrypted_password"],
            r"^#PWD_INSTAGRAM:0:\d+:password$",
        )
        self.assertEqual(password_call.kwargs["client_input_params"]["spi_action"], 1)
        self.assertEqual(
            password_call.kwargs["server_params"]["flow_modifier"],
            dumps({"flow_name": "new_to_family_ig_default", "flow_type": "ntf"}),
        )
        birthday_call = caa_reg_graphql.call_args_list[6]
        self.assertEqual(birthday_call.kwargs["client_input_params"]["birthday_or_current_date_string"], "09-06-1995")
        username_call = caa_reg_graphql.call_args_list[7]
        self.assertEqual(username_call.kwargs["server_params"]["action"], 1)
        self.assertEqual(username_call.kwargs["server_params"]["post_tos"], 0)
        email_new_call = caa_reg_async_action.call_args_list[1]
        self.assertIsNone(email_new_call.kwargs["server_params"]["reg_context"])
        self.assertEqual(email_new_call.kwargs["client_input_params"]["email_prefilled"], 0)
        self.assertEqual(email_new_call.kwargs["client_input_params"]["prefetch_version"], 11)
        self.assertEqual(email_new_call.kwargs["server_params"]["cp_funnel"], 0)
        self.assertEqual(email_new_call.kwargs["server_params"]["prefetch_on_field"], 1)

    def test_signup_caa_email_reports_bloks_rejection_message(self):
        client = Client()
        client.uuid = "uuid-1"
        client.phone_id = "family-device-id"
        client.android_device_id = "android-id"
        client.mid = "machine-id"
        client.bloks_versioning_id = "bloks-version"
        client.waterfall_id = "waterfall-id"
        client.wait_seconds = 0
        client.challenge_code_handler = mock.Mock(return_value="123456")
        rejection_text = "We're sorry, but something went wrong. Please try again."
        graphql_responses = [
            self.caa_response(reg_context=f"ctx-gql-{index}", email_token=f"email-token-{index}") for index in range(8)
        ]
        graphql_responses.append(
            {
                "data": {
                    "1$bloks_action(bk_context:$bk_context,params:$params)": {
                        "action": {
                            "action_bundle": {
                                "bloks_bundle_action": json.dumps(
                                    {"layout": {"bloks_payload": {"data": [{"data": {"initial": rejection_text}}]}}}
                                )
                            }
                        }
                    }
                }
            }
        )
        async_responses = [
            self.caa_response(reg_context=f"ctx-async-{index}", email_token=f"email-token-async-{index}")
            for index in range(4)
        ]

        with mock.patch.object(client, "caa_reg_graphql", side_effect=graphql_responses):
            with mock.patch.object(client, "caa_reg_async_action", side_effect=async_responses):
                with self.assertRaisesRegex(
                    ClientError,
                    "CAA signup was rejected by Instagram: "
                    r"We're sorry, but something went wrong\. Please try again\.",
                ):
                    client.signup_caa_email(
                        username="example",
                        password="password",
                        email="addr@example.com",
                        full_name="Example User",
                        year=1995,
                        month=6,
                        day=9,
                    )

    def test_check_username_posts_uuid_payload(self):
        client = Client()
        client.uuid = "uuid"
        with mock.patch.object(client, "private_request", return_value={"available": True}) as private_request:
            result = client.check_username("example")

        self.assertEqual(result, {"available": True})
        private_request.assert_called_once_with(
            "users/check_username/",
            data={"username": "example", "_uuid": "uuid"},
        )

    def test_check_phone_number_posts_signup_payload(self):
        client = Client()
        client.phone_id = "phone-id"
        client.uuid = "uuid"
        client.android_device_id = "android-id"
        with mock.patch.object(client, "private_request", return_value={"valid": True}) as private_request:
            result = client.check_phone_number("+15551234567")

        self.assertEqual(result, {"valid": True})
        private_request.assert_called_once_with(
            "accounts/check_phone_number/",
            data={
                "phone_id": "phone-id",
                "login_nonce_map": "{}",
                "phone_number": "+15551234567",
                "guid": "uuid",
                "device_id": "android-id",
                "prefill_shown": "False",
            },
        )

    def test_signup_requires_email_or_phone_number(self):
        client = Client()

        with self.assertRaises(ClientError) as ctx:
            client.signup("example", "password", email="", phone_number="")

        self.assertIn("email or phone_number", str(ctx.exception))

    def test_signup_with_phone_number_uses_sms_flow(self):
        client = Client()
        client.wait_seconds = 0
        client.challenge_code_handler = mock.Mock(return_value="123456")
        client.send_signup_sms_code = mock.Mock(return_value={"status": "ok"})

        with mock.patch.object(client, "get_signup_config", return_value={}):
            with mock.patch.object(client, "check_email") as check_email:
                with mock.patch.object(client, "check_phone_number", return_value={"status": "ok"}) as check_phone:
                    with mock.patch.object(
                        client,
                        "accounts_create",
                        return_value={"created_user": {"pk": "1", "username": "example"}},
                    ) as accounts_create:
                        with mock.patch(
                            "instagrapi.mixins.signup.extract_user_short",
                            return_value="created-user",
                        ):
                            with self.assertWarnsRegex(RuntimeWarning, "legacy account-create flow"):
                                result = client.signup(
                                    username="example",
                                    password="password",
                                    email="",
                                    phone_number="+15551234567",
                                    full_name="Example User",
                                    year=2000,
                                    month=5,
                                    day=12,
                                )

        self.assertEqual(result, "created-user")
        check_email.assert_not_called()
        check_phone.assert_called_once_with("+15551234567")
        client.send_signup_sms_code.assert_called_once_with("+15551234567")
        client.challenge_code_handler.assert_called_once_with("example", ChallengeChoice.SMS)
        accounts_create.assert_called_once_with(
            username="example",
            password="password",
            full_name="Example User",
            year=2000,
            month=5,
            day=12,
            phone_number="+15551234567",
            phone_code="123456",
        )

    def test_signup_warns_about_legacy_flow(self):
        client = Client()
        client.wait_seconds = 0
        client.challenge_code_handler = mock.Mock(return_value="123456")
        client.send_signup_sms_code = mock.Mock(return_value={"status": "ok"})

        with mock.patch.object(client, "get_signup_config", return_value={}):
            with mock.patch.object(client, "check_phone_number", return_value={"status": "ok"}):
                with mock.patch.object(
                    client,
                    "accounts_create",
                    return_value={"created_user": {"pk": "1", "username": "example"}},
                ):
                    with mock.patch(
                        "instagrapi.mixins.signup.extract_user_short",
                        return_value="created-user",
                    ):
                        with self.assertWarnsRegex(RuntimeWarning, "legacy account-create flow"):
                            result = client.signup(
                                username="example",
                                password="password",
                                email="",
                                phone_number="+15551234567",
                            )

        self.assertEqual(result, "created-user")

    def test_accounts_create_primary_signup_omits_secondary_account_flag(self):
        client = Client()
        client.phone_id = "phone-id"
        client.uuid = "uuid"
        client.android_device_id = "android-id"
        client.adid = "adid"
        client.waterfall_id = "waterfall-id"
        client.password_encrypt = mock.Mock(return_value="enc-password")

        with mock.patch.object(
            client, "private_request", return_value={"created_user": {"pk": "1"}}
        ) as private_request:
            result = client.accounts_create(
                username="example",
                password="password",
                email="addr@example.com",
                signup_code="signup-code",
                full_name="Example User",
                year=2000,
                month=5,
                day=12,
            )

        self.assertEqual(result, {"created_user": {"pk": "1"}})
        data = private_request.call_args.args[1]
        self.assertNotIn("is_secondary_account_creation", data)
        self.assertEqual(data["username"], "example")
        self.assertEqual(data["force_sign_up_code"], "signup-code")
        private_request.assert_called_once()

    def test_accounts_create_phone_signup_uses_validated_endpoint(self):
        client = Client()
        client.phone_id = "phone-id"
        client.uuid = "uuid"
        client.android_device_id = "android-id"
        client.adid = "adid"
        client.waterfall_id = "waterfall-id"
        client.password_encrypt = mock.Mock(return_value="enc-password")

        with mock.patch.object(
            client, "private_request", return_value={"created_user": {"pk": "1"}}
        ) as private_request:
            result = client.accounts_create(
                username="example",
                password="password",
                phone_number="+15551234567",
                phone_code="123456",
                full_name="Example User",
                year=2000,
                month=5,
                day=12,
            )

        self.assertEqual(result, {"created_user": {"pk": "1"}})
        endpoint, data = private_request.call_args.args
        self.assertEqual(endpoint, "accounts/create_validated/")
        self.assertNotIn("is_secondary_account_creation", data)
        self.assertNotIn("email", data)
        self.assertEqual(data["username"], "example")
        self.assertEqual(data["phone_number"], "+15551234567")
        self.assertEqual(data["verification_code"], "123456")
        self.assertEqual(data["force_sign_up_code"], "")
        self.assertEqual(data["has_sms_consent"], "true")
        private_request.assert_called_once()

    def test_accounts_create_requires_email_or_phone_number(self):
        client = Client()

        with mock.patch.object(client, "private_request") as private_request:
            with self.assertRaises(ClientError) as ctx:
                client.accounts_create(username="example", password="password")

        self.assertIn("email or phone_number", str(ctx.exception))
        private_request.assert_not_called()

    def test_accounts_create_spam_feedback_raises_signup_specific_error(self):
        client = Client()
        client.phone_id = "phone-id"
        client.uuid = "uuid"
        client.android_device_id = "android-id"
        client.adid = "adid"
        client.waterfall_id = "waterfall-id"
        client.password_encrypt = mock.Mock(return_value="enc-password")
        feedback = FeedbackRequired(
            message="feedback_required: Try Again Later",
            feedback_message="We limit how often you can do certain things on Instagram.",
            spam=True,
        )

        with mock.patch.object(client, "private_request", side_effect=feedback):
            with self.assertRaises(SignupSpamError) as ctx:
                client.accounts_create(
                    username="example",
                    password="password",
                    email="addr@example.com",
                    signup_code="signup-code",
                )

        self.assertIn("legacy signup flow", str(ctx.exception))
        self.assertTrue(ctx.exception.spam)
        self.assertEqual(ctx.exception.feedback_message, "We limit how often you can do certain things on Instagram.")

    def test_challenge_api_rejects_external_api_path(self):
        client = Client()
        client.uuid = "uuid"
        client.android_device_id = "android-id"
        client.private.get = mock.Mock()

        for api_path in ("@attacker.example/steal", "//attacker.example/steal"):
            with self.subTest(api_path=api_path):
                with self.assertRaises(ClientError):
                    client.challenge_api(
                        {
                            "api_path": api_path,
                            "challenge_context": "{}",
                        }
                    )

        client.private.get.assert_not_called()

    def test_challenge_captcha_rejects_external_api_path_before_solver(self):
        client = Client()
        client.captcha_resolve = mock.Mock(side_effect=AssertionError("solver should not be called"))
        client.private.post = mock.Mock()

        with self.assertRaises(ClientError):
            client.challenge_captcha(
                {
                    "api_path": "@attacker.example/steal",
                    "fields": {"sitekey": "site-key"},
                    "challengeType": "RecaptchaChallengeForm",
                }
            )

        client.captcha_resolve.assert_not_called()
        client.private.post.assert_not_called()

    def test_challenge_submit_phone_number_rejects_external_forward_path(self):
        client = Client()
        client.private.post = mock.Mock(json=mock.Mock(return_value={"status": "ok"}))

        with self.assertRaises(ClientError):
            client.challenge_submit_phone_number(
                {
                    "navigation": {"forward": "@attacker.example/steal"},
                    "challenge_context": "{}",
                },
                "+15551234567",
            )

        client.private.post.assert_not_called()

    def test_challenge_verify_sms_captcha_rejects_external_forward_path(self):
        client = Client()
        client.private.post = mock.Mock(json=mock.Mock(return_value={"status": "ok"}))

        with self.assertRaises(ClientError):
            client.challenge_verify_sms_captcha(
                {
                    "navigation": {"forward": "@attacker.example/steal"},
                    "challenge_context": "{}",
                },
                "123456",
            )

        client.private.post.assert_not_called()

    def test_challenge_flow_submits_phone_number_then_sms_code(self):
        client = Client()
        start = {"api_path": "/challenge/start", "challenge_context": "{}"}
        submit_phone_step = {
            "challengeType": "SubmitPhoneNumberForm",
            "navigation": {"forward": "/challenge/phone"},
            "challenge_context": "{}",
        }
        verify_sms_step = {
            "challengeType": "VerifySMSCodeFormForSMSCaptcha",
            "navigation": {"forward": "/challenge/sms"},
            "challenge_context": "{}",
        }

        with mock.patch.object(client, "challenge_api", return_value=submit_phone_step):
            with mock.patch.object(
                client,
                "challenge_submit_phone_number",
                return_value=verify_sms_step,
            ) as submit_phone:
                with mock.patch.object(
                    client,
                    "challenge_verify_sms_captcha",
                    return_value={"status": "ok"},
                ) as verify_sms:
                    with mock.patch.object(client, "challenge_code_handler", return_value="123456") as code_handler:
                        result = client.challenge_flow(
                            start,
                            phone_number="+15551234567",
                            username="example",
                            wait_seconds=0,
                        )

        self.assertTrue(result)
        submit_phone.assert_called_once_with(submit_phone_step, "+15551234567")
        code_handler.assert_called_once()
        self.assertEqual(code_handler.call_args.args[0], "example")
        self.assertEqual(code_handler.call_args.args[1], ChallengeChoice.SMS)
        verify_sms.assert_called_once_with(verify_sms_step, "123456")

    def test_challenge_flow_requires_phone_number_for_sms_challenge(self):
        client = Client()
        start = {"api_path": "/challenge/start", "challenge_context": "{}"}
        submit_phone_step = {
            "challengeType": "SubmitPhoneNumberForm",
            "navigation": {"forward": "/challenge/phone"},
            "challenge_context": "{}",
        }

        with mock.patch.object(client, "challenge_api", return_value=submit_phone_step):
            with self.assertRaises(ClientError) as ctx:
                client.challenge_flow(start, username="example", wait_seconds=0)

        self.assertIn("phone_number is required", str(ctx.exception))

    def test_challenge_flow_requires_sms_code(self):
        client = Client()
        start = {"api_path": "/challenge/start", "challenge_context": "{}"}
        verify_sms_step = {
            "challengeType": "VerifySMSCodeFormForSMSCaptcha",
            "navigation": {"forward": "/challenge/sms"},
            "challenge_context": "{}",
        }

        with mock.patch.object(client, "challenge_api", return_value=verify_sms_step):
            with mock.patch.object(client, "challenge_code_handler", return_value=False):
                with self.assertRaises(ChallengeRequired) as ctx:
                    client.challenge_flow(
                        start,
                        phone_number="+15551234567",
                        username="example",
                        wait_seconds=0,
                        attempts=1,
                    )

        self.assertIn("SMS code required", str(ctx.exception))

    def test_signup_passes_phone_number_to_challenge_flow(self):
        client = Client()
        client.wait_seconds = 0
        challenge = {"api_path": "/challenge/start", "challenge_context": "{}"}

        with mock.patch.object(client, "get_signup_config", return_value={}):
            with mock.patch.object(client, "check_email", return_value={"valid": True, "available": True}):
                with mock.patch.object(client, "send_verify_email", return_value={"email_sent": True}):
                    with mock.patch.object(client, "challenge_code_handler", return_value="654321"):
                        with mock.patch.object(
                            client,
                            "check_confirmation_code",
                            return_value={"signup_code": "signup-code"},
                        ):
                            with mock.patch.object(
                                client,
                                "accounts_create",
                                side_effect=[
                                    {"message": "challenge_required", "challenge": challenge},
                                    {"created_user": {"pk": "1", "username": "example"}},
                                ],
                            ):
                                with mock.patch.object(client, "challenge_flow", return_value=True) as challenge_flow:
                                    with mock.patch(
                                        "instagrapi.mixins.signup.extract_user_short",
                                        return_value="created-user",
                                    ):
                                        with self.assertWarnsRegex(RuntimeWarning, "legacy account-create flow"):
                                            result = client.signup(
                                                "example",
                                                "password",
                                                "example@example.com",
                                                "+15551234567",
                                            )

        self.assertEqual(result, "created-user")
        challenge_flow.assert_called_once_with(
            challenge,
            phone_number="+15551234567",
            username="example",
        )


class SignupLiveHelperRegressionTestCase(unittest.TestCase):
    def test_get_signup_email_address_command_receives_username_context(self):
        case = SignUpTestCase("test_email_signup_live")
        completed = subprocess.CompletedProcess(args="email-command", returncode=0, stdout="fresh@example.test\n")

        with mock.patch.dict(os.environ, {"IG_SIGNUP_EMAIL_COMMAND": "email-command"}, clear=True):
            with mock.patch("tests.live.test_signup.subprocess.run", return_value=completed) as run:
                email = case._get_signup_email_address("freshuser")

        self.assertEqual(email, "fresh@example.test")
        self.assertEqual(run.call_args.kwargs["env"]["IG_SIGNUP_USERNAME"], "freshuser")

    def test_signup_code_command_receives_signup_context(self):
        case = SignUpTestCase("test_email_signup_live")
        completed = subprocess.CompletedProcess(args="code-command", returncode=0, stdout="123456\n")

        with mock.patch.dict(os.environ, {"IG_SIGNUP_EMAIL_CODE_COMMAND": "code-command"}, clear=True):
            with mock.patch("tests.live.test_signup.subprocess.run", return_value=completed) as run:
                code = case.signup_code_handler(
                    "IG_SIGNUP_EMAIL_CODE",
                    "IG_SIGNUP_EMAIL_CODE_COMMAND",
                    {
                        "IG_SIGNUP_USERNAME": "freshuser",
                        "IG_SIGNUP_EMAIL": "fresh@example.test",
                    },
                )

        self.assertEqual(code, "123456")
        self.assertEqual(run.call_args.kwargs["env"]["IG_SIGNUP_USERNAME"], "freshuser")
        self.assertEqual(run.call_args.kwargs["env"]["IG_SIGNUP_EMAIL"], "fresh@example.test")

    def test_get_signup_email_address_skips_without_static_email_or_command(self):
        case = SignUpTestCase("test_email_signup_live")

        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(unittest.SkipTest):
                case._get_signup_email_address("freshuser")

    def test_signup_phone_number_prefers_signup_specific_env(self):
        case = SignUpTestCase("test_phone_signup_live")

        with mock.patch.dict(
            os.environ,
            {
                "IG_PHONE_NUMBER": "+15550000000",
                "IG_SIGNUP_PHONE_NUMBER": "+15551234567",
            },
            clear=True,
        ):
            phone_number = case.signup_phone_number()

        self.assertEqual(phone_number, "+15551234567")
