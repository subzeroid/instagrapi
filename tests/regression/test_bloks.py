import base64

from tests.helpers import *


class BloksRegressionTestCase(unittest.TestCase):
    def build_client(self):
        client = Client()
        client.uuid = "uuid-1"
        client.bloks_versioning_id = "bloks-version"
        return client

    def test_bloks_async_action_posts_unsigned_bloks_payload(self):
        client = self.build_client()
        params = {"server_params": {"flow": "example_flow"}}
        expected = {"status": "ok"}

        with mock.patch.object(client, "private_request", return_value=expected) as private_request:
            result = client.bloks_async_action("com.example.action", params)

        self.assertEqual(result, expected)
        private_request.assert_called_once_with(
            "bloks/async_action/com.example.action/",
            data={
                "params": dumps(params),
                "_uuid": "uuid-1",
                "bk_client_context": dumps({"bloks_version": "bloks-version", "styles_id": "instagram"}),
                "bloks_versioning_id": "bloks-version",
            },
            with_signature=False,
            headers={"X-FB-Friendly-Name": "IgApi: bloks/async_action/com.example.action/"},
        )

    def test_bloks_async_action_accepts_domain_override(self):
        client = self.build_client()
        params = {"server_params": {"flow": "example_flow"}}
        expected = {"status": "ok"}

        with mock.patch.object(client, "private_request", return_value=expected) as private_request:
            result = client.bloks_async_action("com.example.action", params, domain="b.i.instagram.com")

        self.assertEqual(result, expected)
        private_request.assert_called_once_with(
            "bloks/async_action/com.example.action/",
            data={
                "params": dumps(params),
                "_uuid": "uuid-1",
                "bk_client_context": dumps({"bloks_version": "bloks-version", "styles_id": "instagram"}),
                "bloks_versioning_id": "bloks-version",
            },
            with_signature=False,
            headers={"X-FB-Friendly-Name": "IgApi: bloks/async_action/com.example.action/"},
            domain="b.i.instagram.com",
        )

    def test_bloks_async_action_does_not_leak_friendly_name_onto_session(self):
        client = self.build_client()
        client.request_timeout = 0
        response = mock.Mock(status_code=200)
        response.headers = {}
        response.json.return_value = {"status": "ok"}
        response.raise_for_status.return_value = None
        client.private.post = mock.Mock(return_value=response)

        client.bloks_async_action("com.example.action", {"server_params": {"flow": "example_flow"}})

        # The friendly name is sent per-request...
        sent_headers = client.private.post.call_args.kwargs["headers"]
        self.assertEqual(
            sent_headers["X-FB-Friendly-Name"],
            "IgApi: bloks/async_action/com.example.action/",
        )
        # ...but must not stick to the persistent session headers, where it would
        # leak onto every later unrelated private request.
        self.assertNotIn("X-FB-Friendly-Name", client.private.headers)

    def test_bloks_app_posts_unsigned_bloks_payload(self):
        client = self.build_client()
        params = {"server_params": {"flow": "example_flow"}}
        expected = {"status": "ok"}

        with mock.patch.object(client, "private_request", return_value=expected) as private_request:
            result = client.bloks_app("com.example.app", params)

        self.assertEqual(result, expected)
        private_request.assert_called_once_with(
            "bloks/apps/com.example.app/",
            data={
                "params": dumps(params),
                "_uuid": "uuid-1",
                "bk_client_context": dumps({"bloks_version": "bloks-version", "styles_id": "instagram"}),
                "bloks_versioning_id": "bloks-version",
            },
            with_signature=False,
        )

    def test_bloks_graphql_app_posts_wrapped_bloks_payload(self):
        client = self.build_client()
        params = {
            "client_input_params": {"device_id": "android-id"},
            "server_params": {"flow": "example_flow"},
        }
        expected = {"data": {"ok": True}}

        with mock.patch.object(client, "private_graphql_www_request", return_value=expected) as graphql_request:
            result = client.bloks_graphql_app(
                "com.example.app",
                params,
                client_doc_id="doc-id",
                infra_device_id="qe-device-id",
            )

        self.assertEqual(result, expected)
        graphql_request.assert_called_once()
        friendly_name, variables = graphql_request.call_args.args[:2]
        self.assertEqual(friendly_name, "IGBloksAppRootQuery-com.example.app")
        self.assertEqual(
            graphql_request.call_args.kwargs,
            {"client_doc_id": "doc-id", "domain": "b.i.instagram.com"},
        )
        self.assertEqual(
            variables["bk_context"],
            {
                "is_flipper_enabled": False,
                "theme_params": [],
                "debug_tooling_metadata_token": None,
            },
        )
        wrapped_params = variables["params"]
        self.assertEqual(wrapped_params["app_id"], "com.example.app")
        self.assertEqual(wrapped_params["bloks_versioning_id"], "bloks-version")
        self.assertEqual(wrapped_params["infra_params"], {"device_id": "qe-device-id"})
        outer_params = json.loads(wrapped_params["params"])
        self.assertEqual(json.loads(outer_params["params"]), params)

    def test_bloks_challenge_take_challenge_posts_unsigned_direct_payload(self):
        client = self.build_client()
        challenge_context = "Af4sGj7RsOARkOpaqueContext"
        expected = {"status": "ok"}

        with mock.patch.object(client, "private_request", return_value=expected) as private_request:
            result = client.bloks_challenge_take_challenge(
                challenge_context=challenge_context,
                choice=0,
                extra_data={"is_bloks_web": False},
            )

        self.assertEqual(result, expected)
        private_request.assert_called_once_with(
            "bloks/apps/com.instagram.challenge.navigation.take_challenge/",
            data={
                "_uuid": "uuid-1",
                "has_follow_up_screens": "0",
                "bk_client_context": dumps({"bloks_version": "bloks-version", "styles_id": "instagram"}),
                "bloks_versioning_id": "bloks-version",
                "challenge_context": challenge_context,
                "choice": "0",
                "is_bloks_web": False,
            },
            with_signature=False,
        )

    def test_bloks_change_password_preserves_opaque_challenge_context(self):
        client = self.build_client()
        challenge_context = "Af4sGj7RsOARkOpaqueContext"
        client.password_encrypt = Mock(return_value="#PWD_INSTAGRAM:4:1:encrypted")

        with mock.patch.object(client, "private_request", return_value={"status": "ok"}) as private_request:
            result = client.bloks_change_password("new-password", challenge_context)

        self.assertTrue(result)
        private_request.assert_called_once_with(
            "bloks/apps/com.instagram.challenge.navigation.take_challenge/",
            data={
                "_uuid": "uuid-1",
                "has_follow_up_screens": "0",
                "bk_client_context": dumps({"bloks_version": "bloks-version", "styles_id": "instagram"}),
                "bloks_versioning_id": "bloks-version",
                "challenge_context": challenge_context,
                "enc_new_password1": "#PWD_INSTAGRAM:4:1:encrypted",
                "enc_new_password2": "#PWD_INSTAGRAM:4:1:encrypted",
            },
            with_signature=False,
        )

    def test_bloks_fxcal_link_reels_share_uses_current_flow_payload(self):
        client = self.build_client()
        expected = {"status": "ok"}

        with mock.patch.object(client, "bloks_async_action", return_value=expected) as bloks_async_action:
            result = client.bloks_fxcal_link_reels_share(cds_client_value=2)

        self.assertEqual(result, expected)
        bloks_async_action.assert_called_once_with(
            "com.bloks.www.fxcal.link.async",
            {
                "server_params": {
                    "flow": "ig_fb_reels_composer_rowshare",
                    "logging_event": "linking_flow_initiated",
                    "cds_client_value": 2,
                    "opaque_verified_native_auth_data": None,
                    "native_auth_data": [],
                    "account_type": 0,
                }
            },
            bloks_versioning_id="",
        )

    def test_bloks_two_step_verification_entrypoint_uses_current_payload(self):
        client = self.build_client()
        client.android_device_id = "android-1"
        client.phone_id = "family-device-1"
        client.mid = "machine-1"
        expected = {"status": "ok"}

        with mock.patch.object(client, "bloks_app", return_value=expected) as bloks_app:
            result = client.bloks_two_step_verification_entrypoint(
                "context-1",
                screen_id="screen-1",
                should_fallback_to_sms=True,
            )

        self.assertEqual(result, expected)
        bloks_app.assert_called_once_with(
            "com.bloks.www.two_step_verification.entrypoint",
            {
                "client_input_params": {
                    "device_id": "android-1",
                    "is_whatsapp_installed": 0,
                    "machine_id": "machine-1",
                },
                "server_params": {
                    "should_fallback_to_sms": 1,
                    "family_device_id": "family-device-1",
                    "device_id": "android-1",
                    "INTERNAL_INFRA_screen_id": "screen-1",
                    "two_step_verification_context": "context-1",
                    "flow_source": "two_factor_login",
                },
            },
            bloks_versioning_id="",
        )

    def test_bloks_two_step_verification_method_picker_uses_current_payload(self):
        client = self.build_client()
        client.android_device_id = "android-1"
        expected = {"status": "ok"}

        with mock.patch.object(client, "bloks_app", return_value=expected) as bloks_app:
            result = client.bloks_two_step_verification_method_picker("context-1")

        self.assertEqual(result, expected)
        bloks_app.assert_called_once_with(
            "com.bloks.www.two_step_verification.method_picker",
            {
                "client_input_params": {"is_whatsapp_installed": 0},
                "server_params": {
                    "should_fallback_to_sms": 0,
                    "device_id": "android-1",
                    "two_step_verification_context": "context-1",
                    "flow_source": "two_factor_login",
                },
            },
            bloks_versioning_id="",
        )

    def test_bloks_two_step_verification_select_method_uses_current_payload(self):
        client = self.build_client()
        client.android_device_id = "android-1"
        expected = {"status": "ok"}

        with mock.patch.object(client, "bloks_async_action", return_value=expected) as bloks_async_action:
            result = client.bloks_two_step_verification_select_method(
                "context-1",
                selected_method="sms",
                latency_qpl_marker_id=36707139,
                latency_qpl_instance_id=123,
            )

        self.assertEqual(result, expected)
        bloks_async_action.assert_called_once_with(
            "com.bloks.www.two_step_verification.method_picker.navigation.async",
            {
                "client_input_params": {
                    "selected_method": "sms",
                    "cloud_trust_token": None,
                    "network_bssid": None,
                },
                "server_params": {
                    "should_fallback_to_sms": 0,
                    "INTERNAL__latency_qpl_marker_id": 36707139,
                    "device_id": "android-1",
                    "spectra_reg_login_data": None,
                    "INTERNAL__latency_qpl_instance_id": 123,
                    "two_step_verification_context": "context-1",
                    "flow_source": "two_factor_login",
                },
            },
            bloks_versioning_id="",
        )

    def test_bloks_two_step_verification_verify_code_uses_current_payload(self):
        client = self.build_client()
        client.android_device_id = "android-1"
        client.phone_id = "family-device-1"
        client.mid = "machine-1"
        expected = {"status": "ok"}

        with mock.patch.object(client, "bloks_async_action", return_value=expected) as bloks_async_action:
            result = client.bloks_two_step_verification_verify_code(
                "context-1",
                "123456",
                challenge="sms",
                should_trust_device=False,
            )

        self.assertEqual(result, expected)
        bloks_async_action.assert_called_once_with(
            "com.bloks.www.two_step_verification.verify_code.async",
            {
                "client_input_params": {
                    "auth_secure_device_id": "",
                    "block_store_machine_id": "",
                    "code": "123456",
                    "should_trust_device": 0,
                    "family_device_id": "family-device-1",
                    "device_id": "android-1",
                    "cloud_trust_token": None,
                    "network_bssid": None,
                    "machine_id": "machine-1",
                },
                "server_params": {
                    "should_fallback_to_sms": 0,
                    "device_id": "android-1",
                    "spectra_reg_login_data": None,
                    "challenge": "sms",
                    "two_step_verification_context": "context-1",
                    "flow_source": "two_factor_login",
                },
            },
            bloks_versioning_id="",
        )

    def test_bloks_two_step_verification_enter_backup_code_uses_current_payload(self):
        client = self.build_client()
        client.android_device_id = "android-1"
        expected = {"status": "ok"}

        with mock.patch.object(client, "bloks_app", return_value=expected) as bloks_app:
            result = client.bloks_two_step_verification_enter_backup_code(
                "context-1",
                screen_id="screen-1",
            )

        self.assertEqual(result, expected)
        bloks_app.assert_called_once_with(
            "com.bloks.www.two_factor_login.enter_backup_code",
            {
                "server_params": {
                    "device_id": "android-1",
                    "INTERNAL_INFRA_screen_id": "screen-1",
                    "two_step_verification_context": "context-1",
                    "flow_source": "two_factor_login",
                },
            },
            bloks_versioning_id="",
        )

    def test_bloks_caa_login_send_request_uses_current_payload(self):
        client = self.build_client()
        client.username = "example"
        client.android_device_id = "android-1"
        client.phone_id = "family-device-1"
        client.uuid = "uuid-1"
        client.mid = "machine-1"
        client.password_encrypt = Mock(return_value="#PWD_INSTAGRAM:4:1:encrypted")
        expected = {"status": "ok"}

        with mock.patch.object(client, "bloks_async_action", return_value=expected) as bloks_async_action:
            result = client.bloks_caa_login_send_request("password", login_attempt_count=1)

        self.assertEqual(result, expected)
        bloks_async_action.assert_called_once()
        action, params = bloks_async_action.call_args.args[:2]
        self.assertEqual(action, "com.bloks.www.bloks.caa.login.async.send_login_request")
        self.assertEqual(params["client_input_params"]["contact_point"], "example")
        self.assertEqual(params["client_input_params"]["password"], "#PWD_INSTAGRAM:4:1:encrypted")
        self.assertEqual(params["client_input_params"]["device_id"], "android-1")
        self.assertEqual(params["client_input_params"]["family_device_id"], "family-device-1")
        self.assertEqual(params["client_input_params"]["machine_id"], "machine-1")
        self.assertEqual(params["client_input_params"]["login_attempt_count"], 1)
        self.assertEqual(params["client_input_params"]["try_num"], 1)
        self.assertEqual(params["server_params"]["login_credential_type"], "none")
        self.assertEqual(params["server_params"]["credential_type"], "password")
        self.assertEqual(params["server_params"]["family_device_id"], "family-device-1")
        self.assertEqual(params["server_params"]["device_id"], "android-1")
        self.assertIn("waterfall_id", params["server_params"])

    def test_bloks_extract_two_step_verification_context_from_caa_action(self):
        client = self.build_client()
        result = {
            "layout": {
                "bloks_payload": {
                    "action": (
                        '(... "com.bloks.www.two_step_verification.entrypoint" '
                        '(dkc "server_params" "client_input_params") '
                        '(dkc (f4i (dkc "two_step_verification_context" "flow_source" '
                        '"device_id" "should_fallback_to_sms" "family_device_id" '
                        '"INTERNAL_INFRA_screen_id") '
                        '(dkc "context-1" "two_factor_login" "android-1" 0 '
                        '"family-device-1" "screen-1"))))'
                    )
                }
            }
        }

        self.assertEqual(client.bloks_extract_two_step_verification_context(result), "context-1")

    def test_bloks_extract_login_response_parses_embedded_action_payload(self):
        client = self.build_client()
        login_payload = {
            "login_response": dumps(
                {
                    "logged_in_user": {"pk": 123, "username": "example"},
                    "trusted_device_nonce": "nonce-1",
                    "credential_type": "password",
                }
            ),
            "headers": dumps({"IG-Set-Authorization": "Bearer IGT:2:encoded"}),
            "cookies": (
                "Set-Cookie: csrftoken=token-1; Domain=.instagram.com; Path=/; Secure\r\n"
                "Set-Cookie: ds_user_id=123; Domain=.instagram.com; Path=/; Secure\r\n"
                "Set-Cookie: sessionid=123%3Aabc; Domain=.instagram.com; Path=/; Secure"
            ),
            "exact_profile_identified": "1",
        }
        result = {
            "layout": {
                "bloks_payload": {
                    "action": f"BK.action({dumps('ignored')}, {dumps(dumps(login_payload))})",
                }
            }
        }

        parsed = client.bloks_extract_login_response(result)

        self.assertEqual(parsed["login_response"]["logged_in_user"]["username"], "example")
        self.assertEqual(parsed["headers"]["IG-Set-Authorization"], "Bearer IGT:2:encoded")
        self.assertEqual(parsed["cookies"]["sessionid"], "123%3Aabc")
        self.assertEqual(parsed["raw_cookies"], login_payload["cookies"])
        self.assertEqual(parsed["raw"]["exact_profile_identified"], "1")

    def test_bloks_apply_login_response_updates_client_session(self):
        client = self.build_client()
        authorization_data = {
            "ds_user_id": "123",
            "sessionid": "123%3Aabc",
            "should_use_header_over_cookies": True,
        }
        authorization = "Bearer IGT:2:" + base64.b64encode(dumps(authorization_data).encode()).decode()

        result = client.bloks_apply_login_response(
            {
                "headers": {
                    "IG-Set-Authorization": authorization,
                    "ig-set-ig-u-rur": "RUR,123,1:token",
                    "x-ig-set-www-claim": "hmac.claim",
                },
                "cookies": {
                    "csrftoken": "token-1",
                    "ds_user_id": "123",
                    "sessionid": "123%3Aabc",
                },
            }
        )

        self.assertTrue(result)
        self.assertEqual(client.authorization_data, authorization_data)
        self.assertEqual(client.private.cookies.get("csrftoken"), "token-1")
        self.assertEqual(client.private.cookies.get("ds_user_id"), "123")
        self.assertEqual(client.private.cookies.get("sessionid"), "123%3Aabc")
        self.assertEqual(client.public.cookies.get("sessionid"), "123%3Aabc")
        self.assertEqual(client.private.headers["Authorization"], client.authorization)
        self.assertEqual(client.ig_u_rur, "RUR,123,1:token")
        self.assertEqual(client.ig_www_claim, "hmac.claim")
