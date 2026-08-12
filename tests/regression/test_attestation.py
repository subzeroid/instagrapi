import base64
import json

from Cryptodome.Hash import SHA256
from Cryptodome.PublicKey import ECC
from Cryptodome.Signature import DSS

from instagrapi.mixins.attestation import USDID_REFRESH_MARGIN, USDID_REGISTRATION_CLIENT_DOC_ID
from instagrapi.mixins.bloks import AP_2SV_ENTRYPOINT
from tests.helpers import *


def _b64u_decode(value):
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


class DeviceAttestationRegressionTestCase(unittest.TestCase):
    def build_client(self):
        client = Client()
        client.uuid = "00000000-0000-4000-8000-000000000000"
        client.phone_id = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
        client.bloks_versioning_id = "bloks-version"
        return client

    def test_usdid_header_is_three_segments_signed_over_uuid_and_expiry(self):
        client = self.build_client()
        client.usdid_generate()

        value = client.usdid_header()

        parts = value.split(".")
        self.assertEqual(len(parts), 3)
        usdid, expires_at, signature = parts
        self.assertEqual(usdid, client.usdid)
        self.assertTrue(expires_at.isdigit())
        verifier = DSS.new(ECC.import_key(client.usdid_public_key_der), "fips-186-3", encoding="der")
        verifier.verify(SHA256.new(f"{usdid}.{expires_at}".encode()), _b64u_decode(signature))

    def test_usdid_header_absent_until_key_is_generated_and_then_cached(self):
        client = self.build_client()
        self.assertNotIn("X-Meta-Usdid", client.base_headers)

        client.usdid_generate()

        self.assertEqual(client.base_headers["X-Meta-Usdid"], client.usdid_header())
        self.assertEqual(client.usdid_header(), client.usdid_header())

    def test_usdid_identity_reuse_force_rotation_and_header_refresh(self):
        client = self.build_client()
        client.usdid_generate()
        original_identity = (client.usdid, client.usdid_kid, client.usdid_private_key)

        self.assertEqual(client.usdid_generate(), original_identity[0])
        self.assertEqual((client.usdid, client.usdid_kid, client.usdid_private_key), original_identity)

        with mock.patch("instagrapi.mixins.attestation.time.time", return_value=1000):
            original_header = client.usdid_header()
            client._usdid_header_expires_at = 1000 + USDID_REFRESH_MARGIN
            refreshed_header = client.usdid_header()

        self.assertNotEqual(refreshed_header, original_header)
        client.usdid_generate(force=True)
        self.assertNotEqual((client.usdid, client.usdid_kid, client.usdid_private_key), original_identity)
        self.assertFalse(client.usdid_registered)

    def test_usdid_registration_token_is_valid_es256_jws(self):
        client = self.build_client()
        client.usdid_generate()

        token = json.loads(_b64u_decode(client.usdid_registration_token()))
        payload = json.loads(_b64u_decode(token["payload"]))
        protected = json.loads(_b64u_decode(token["signatures"][0]["protected"]))

        self.assertEqual(payload["sub"], client.usdid)
        self.assertEqual(payload["aud"], client.app_id)
        self.assertEqual(payload["exp"] - payload["iat"], 3600)
        self.assertEqual(protected["alg"], "ES256")
        self.assertEqual(protected["kid"], client.usdid_kid)
        public_key = ECC.import_key(base64.b64decode(payload["pub"]))
        verifier = DSS.new(public_key, "fips-186-3", encoding="der")
        signing_input = f"{token['signatures'][0]['protected']}.{token['payload']}"
        verifier.verify(SHA256.new(signing_input.encode()), _b64u_decode(token["signatures"][0]["signature"]))

    def test_usdid_register_uses_app_428_document_and_family_device_id(self):
        client = self.build_client()
        response = {"data": {"1$usdid_registration(data:$input)": {"success": True}}}

        with mock.patch.object(client, "private_graphql_www_request", return_value=response) as graphql_request:
            result = client.usdid_register()

        self.assertTrue(result)
        self.assertEqual(USDID_REGISTRATION_CLIENT_DOC_ID, "124930351917786857261002920888")
        graphql_request.assert_called_once()
        friendly_name, variables = graphql_request.call_args.args[:2]
        self.assertEqual(friendly_name, "IGUSDIDRegistrationMutation")
        self.assertEqual(
            variables["input"]["fdid"]["sensitive_string_value"],
            client.phone_id,
        )
        self.assertTrue(variables["input"]["usdid_token"]["sensitive_string_value"])
        self.assertEqual(graphql_request.call_args.kwargs["client_doc_id"], USDID_REGISTRATION_CLIENT_DOC_ID)
        self.assertNotIn("domain", graphql_request.call_args.kwargs)

    def test_usdid_register_returns_false_for_rejection_or_missing_payload(self):
        client = self.build_client()
        responses = [
            {"data": {"1$usdid_registration(data:$input)": {"success": False}}},
            {"data": None},
        ]

        with mock.patch.object(client, "private_graphql_www_request", side_effect=responses):
            self.assertFalse(client.usdid_register())
            self.assertFalse(client.usdid_register())

        self.assertFalse(client.usdid_registered)

    def test_attestation_create_stores_nonce_and_uses_app_scoped_device_id(self):
        client = self.build_client()
        response = {"challenge_nonce": "challenge", "key_nonce": "key", "status": "ok"}

        with mock.patch.object(client, "private_request", return_value=response) as private_request:
            result = client.attestation_create_android_keystore(domain="b.i.instagram.com")

        self.assertEqual(result, response)
        self.assertEqual(client.attestation_challenge_nonce, "challenge")
        self.assertEqual(client.attestation_key_nonce, "key")
        private_request.assert_called_once_with(
            "attestation/create_android_keystore/",
            data={"app_scoped_device_id": client.uuid, "key_hash": ""},
            with_signature=False,
            headers={"X-FB-Friendly-Name": "IgApi: attestation/create_android_keystore/"},
            login=True,
            domain="b.i.instagram.com",
        )

    def test_attestation_create_uses_default_domain_and_clears_missing_nonces(self):
        client = self.build_client()
        client.attestation_challenge_nonce = "stale"
        client.attestation_key_nonce = "stale"

        with mock.patch.object(client, "private_request", return_value={"status": "ok"}) as private_request:
            client.attestation_create_android_keystore()

        self.assertEqual(client.attestation_challenge_nonce, "")
        self.assertEqual(client.attestation_key_nonce, "")
        self.assertNotIn("domain", private_request.call_args.kwargs)

    def test_attestation_params_match_accepted_keystore_error_state(self):
        client = self.build_client()

        params = json.loads(client.attestation_params("challenge"))

        self.assertEqual(
            params,
            {
                "attestation": [
                    {
                        "version": 2,
                        "type": "keystore",
                        "errors": [-1013],
                        "challenge_nonce": "challenge",
                        "signed_nonce": "",
                        "key_hash": "",
                    }
                ]
            },
        )
        self.assertEqual(client.attestation_params(""), "")

    def test_usdid_settings_roundtrip_does_not_leak_between_clients(self):
        client = self.build_client()
        other = self.build_client()
        client.usdid_generate()
        client.usdid_registered = True

        self.assertFalse(other.usdid_private_key)
        settings = client.get_settings()
        self.assertIn("usdid", settings)

        restored = Client(settings=settings)
        self.assertEqual(restored.usdid, client.usdid)
        self.assertEqual(restored.usdid_public_key_der, client.usdid_public_key_der)
        self.assertTrue(restored.usdid_registered)

    def test_clearing_usdid_settings_removes_stale_session_header(self):
        client = self.build_client()
        client.usdid_generate()
        client.private.headers.update(client.base_headers)
        self.assertIn("X-Meta-Usdid", client.private.headers)

        client.set_usdid_settings({})

        self.assertNotIn("X-Meta-Usdid", client.private.headers)

    def test_resetting_device_rotates_family_id_and_clears_bound_usdid(self):
        client = self.build_client()
        client.usdid_generate()
        client.usdid_registered = True
        client.private.headers.update(client.base_headers)
        old_phone_id = client.phone_id

        client.set_device(reset=True)

        self.assertNotEqual(client.phone_id, old_phone_id)
        self.assertEqual(client.get_usdid_settings(), {})
        self.assertFalse(client.usdid_registered)
        self.assertNotIn("X-Meta-Usdid", client.private.headers)
        self.assertNotIn("usdid", client.get_settings())


class CaaLoginRegressionTestCase(unittest.TestCase):
    def build_client(self):
        client = Client()
        client.uuid = "00000000-0000-4000-8000-000000000000"
        client.phone_id = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
        client.android_device_id = "android-123"
        client.mid = "mid-123"
        client.bloks_versioning_id = "bloks-version"
        client.username = "example_user"
        client.password = "dummy_password"
        return client

    @staticmethod
    def aac_response(aac):
        return {
            "layout": {
                "bloks_payload": {
                    "data": [
                        {
                            "data": {
                                "key": "CAA_ACCOUNT_ACCESS_CONTEXT:aac",
                                "initial_lispy": f"(fhy {json.dumps(aac)})",
                            }
                        }
                    ]
                }
            }
        }

    def test_process_client_data_extracts_server_issued_aac(self):
        client = self.build_client()
        aac = '{"aac_init_timestamp":1,"aacjid":"j","aaccs":"server"}'

        with mock.patch.object(client, "bloks_async_action", return_value=self.aac_response(aac)) as action:
            result = client.bloks_caa_login_process_client_data(domain="b.i.instagram.com")

        self.assertEqual(result, self.aac_response(aac))
        self.assertEqual(client.caa_aac, aac)
        called_action, params = action.call_args.args[:2]
        self.assertEqual(called_action, "com.bloks.www.bloks.caa.login.process_client_data_and_redirect")
        self.assertEqual(params["family_device_id"], client.phone_id)
        self.assertEqual(params["device_id"], client.android_device_id)
        self.assertEqual(params["qe_device_id"], client.uuid)
        self.assertEqual(action.call_args.kwargs["domain"], "b.i.instagram.com")
        self.assertTrue(action.call_args.kwargs["login"])

    def test_extract_aac_supports_initial_and_rejects_malformed_payloads(self):
        client = self.build_client()
        direct = {
            "layout": {
                "bloks_payload": {
                    "data": [{"data": {"key": "CAA_ACCOUNT_ACCESS_CONTEXT:aac", "initial": "server-aac"}}]
                }
            }
        }

        self.assertEqual(client.bloks_extract_aac(direct), "server-aac")
        self.assertEqual(client.bloks_extract_aac({"layout": {"bloks_payload": {"data": {}}}}), "")
        self.assertEqual(
            client.bloks_extract_aac(
                {
                    "layout": {
                        "bloks_payload": {
                            "data": [
                                {
                                    "data": {
                                        "key": "CAA_ACCOUNT_ACCESS_CONTEXT:aac",
                                        "initial_lispy": "not-json",
                                    }
                                }
                            ]
                        }
                    }
                }
            ),
            "",
        )

    def test_bloks_transport_forwards_login_domain_and_extra_headers(self):
        client = self.build_client()

        with mock.patch.object(client, "private_request", side_effect=[{"kind": "action"}, {"kind": "app"}]) as request:
            action_result = client.bloks_async_action(
                "com.example.action",
                {"value": 1},
                domain="b.i.instagram.com",
                extra_headers={"X-Test": "yes"},
                login=True,
            )
            app_result = client.bloks_app(
                "com.example.app",
                {"value": 2},
                domain="b.i.instagram.com",
                login=True,
            )

        self.assertEqual(action_result, {"kind": "action"})
        self.assertEqual(app_result, {"kind": "app"})
        action_call, app_call = request.call_args_list
        self.assertEqual(action_call.args[0], "bloks/async_action/com.example.action/")
        self.assertEqual(action_call.kwargs["headers"]["X-Test"], "yes")
        self.assertEqual(action_call.kwargs["domain"], "b.i.instagram.com")
        self.assertTrue(action_call.kwargs["login"])
        self.assertEqual(app_call.args[0], "bloks/apps/com.example.app/")
        self.assertEqual(app_call.kwargs["domain"], "b.i.instagram.com")
        self.assertTrue(app_call.kwargs["login"])

    def test_oauth_preflight_uses_username_aac_and_waterfall(self):
        client = self.build_client()
        client.caa_aac = "server-aac"

        with mock.patch.object(client, "bloks_async_action", return_value={"status": "ok"}) as action:
            client.bloks_caa_login_oauth_token_fetch(
                username="override_user",
                waterfall_id="waterfall-1",
                domain="b.i.instagram.com",
            )

        called_action, params = action.call_args.args[:2]
        self.assertEqual(called_action, "com.bloks.www.caa.login.oauth.token.fetch.async")
        self.assertEqual(params["client_input_params"]["username_input"], "override_user")
        self.assertEqual(params["client_input_params"]["aac"], "server-aac")
        self.assertEqual(params["server_params"]["waterfall_id"], "waterfall-1")
        self.assertEqual(action.call_args.kwargs["domain"], "b.i.instagram.com")
        self.assertTrue(action.call_args.kwargs["login"])

    def test_prepare_runs_current_preflight_sequence(self):
        client = self.build_client()
        order = []

        def register():
            order.append("register")
            client.usdid_registered = True
            return True

        def process(**kwargs):
            order.append("process")
            client.caa_aac = '{"aaccs":"server"}'
            return {}

        def attest(**kwargs):
            order.append("attestation")
            client.attestation_challenge_nonce = "challenge"
            return {"challenge_nonce": "challenge"}

        def oauth(**kwargs):
            order.append("oauth")
            return {}

        with (
            mock.patch.object(client, "usdid_register", side_effect=register),
            mock.patch.object(client, "bloks_caa_login_process_client_data", side_effect=process),
            mock.patch.object(client, "attestation_create_android_keystore", side_effect=attest),
            mock.patch.object(client, "bloks_caa_login_oauth_token_fetch", side_effect=oauth),
        ):
            result = client.bloks_caa_login_prepare(domain="b.i.instagram.com")

        self.assertTrue(result)
        self.assertEqual(order, ["register", "process", "attestation", "oauth"])

    def test_prepare_stops_when_usdid_registration_is_rejected(self):
        client = self.build_client()

        with (
            mock.patch.object(client, "usdid_register", return_value=False),
            mock.patch.object(client, "bloks_caa_login_process_client_data") as process,
            mock.patch.object(client, "attestation_create_android_keystore") as attest,
            mock.patch.object(client, "bloks_caa_login_oauth_token_fetch") as oauth,
        ):
            result = client.bloks_caa_login_prepare()

        self.assertFalse(result)
        process.assert_not_called()
        attest.assert_not_called()
        oauth.assert_not_called()

    def test_prepare_skips_registration_and_oauth_without_aac(self):
        client = self.build_client()
        client.usdid_registered = True

        def process(**kwargs):
            client.caa_aac = ""
            return {}

        def attest(**kwargs):
            client.attestation_challenge_nonce = "challenge"
            return {"challenge_nonce": "challenge"}

        with (
            mock.patch.object(client, "usdid_register") as register,
            mock.patch.object(client, "bloks_caa_login_process_client_data", side_effect=process),
            mock.patch.object(client, "attestation_create_android_keystore", side_effect=attest),
            mock.patch.object(client, "bloks_caa_login_oauth_token_fetch") as oauth,
        ):
            result = client.bloks_caa_login_prepare()

        self.assertFalse(result)
        register.assert_not_called()
        oauth.assert_not_called()

    def test_prepare_returns_false_when_attestation_nonce_is_missing(self):
        client = self.build_client()
        client.usdid_registered = True

        def process(**kwargs):
            client.caa_aac = "server-aac"
            return {}

        with (
            mock.patch.object(client, "bloks_caa_login_process_client_data", side_effect=process),
            mock.patch.object(client, "attestation_create_android_keystore", return_value={}),
            mock.patch.object(client, "bloks_caa_login_oauth_token_fetch", return_value={}) as oauth,
        ):
            result = client.bloks_caa_login_prepare(username="override_user")

        self.assertFalse(result)
        oauth.assert_called_once_with(username="override_user", domain=None)

    def test_send_login_requires_server_issued_aac(self):
        client = self.build_client()

        with mock.patch.object(client, "bloks_async_action") as action, self.assertRaises(ClientError) as cm:
            client.bloks_caa_login_send_request("dummy_password")

        self.assertIn("server-issued aac", str(cm.exception))
        action.assert_not_called()

    def test_send_login_uses_server_aac_and_attestation_only_on_final_request(self):
        client = self.build_client()
        client.caa_aac = '{"aac_init_timestamp":1,"aacjid":"j","aaccs":"server"}'
        client.attestation_challenge_nonce = "challenge"
        client.password_encrypt = Mock(return_value="#PWD_INSTAGRAM:4:1:encrypted")

        with mock.patch.object(client, "bloks_async_action", return_value={"status": "ok"}) as action:
            client.bloks_caa_login_send_request("dummy_password", domain="b.i.instagram.com")

        called_action, params = action.call_args.args[:2]
        self.assertEqual(called_action, "com.bloks.www.bloks.caa.login.async.send_login_request")
        self.assertEqual(params["client_input_params"]["aac"], client.caa_aac)
        self.assertEqual(params["client_input_params"]["password"], "#PWD_INSTAGRAM:4:1:encrypted")
        self.assertEqual(params["client_input_params"]["gms_incoming_call_retriever_eligibility"], "eligible")
        self.assertEqual(params["server_params"]["waterfall_id"], client.caa_waterfall_id)
        self.assertEqual(action.call_args.kwargs["domain"], "b.i.instagram.com")
        self.assertTrue(action.call_args.kwargs["login"])
        attest = json.loads(action.call_args.kwargs["extra_headers"]["X-IG-Attest-Params"])
        self.assertEqual(attest["attestation"][0]["challenge_nonce"], "challenge")

    def test_send_login_accepts_encrypted_password_and_explicit_overrides_without_attestation(self):
        client = self.build_client()
        client.caa_aac = "server-aac"
        client.password_encrypt = Mock(side_effect=AssertionError("encrypted passwords must not be encrypted twice"))

        with mock.patch.object(client, "bloks_async_action", return_value={"status": "ok"}) as action:
            client.bloks_caa_login_send_request(
                "#PWD_INSTAGRAM:4:1:encrypted",
                username="override_user",
                waterfall_id="waterfall-1",
            )

        params = action.call_args.args[1]
        self.assertEqual(params["client_input_params"]["password"], "#PWD_INSTAGRAM:4:1:encrypted")
        self.assertEqual(params["client_input_params"]["contact_point"], "override_user")
        self.assertEqual(params["server_params"]["waterfall_id"], "waterfall-1")
        self.assertIsNone(action.call_args.kwargs["extra_headers"])
        client.password_encrypt.assert_not_called()

    def test_full_caa_login_applies_direct_embedded_login_response(self):
        client = self.build_client()
        authorization = "Bearer IGT:2:token"
        embedded = json.dumps(
            {
                "login_response": json.dumps({"status": "ok", "logged_in_user": {"pk": 123}}),
                "headers": json.dumps({"IG-Set-Authorization": authorization}),
            }
        )
        send_result = {"layout": {"bloks_payload": {"action": f"(x {json.dumps(embedded)})"}}}

        with (
            mock.patch.object(client, "bloks_caa_login_prepare", return_value=True),
            mock.patch.object(client, "bloks_caa_login_send_request", return_value=send_result),
            mock.patch.object(client, "parse_authorization", return_value={"ds_user_id": "123"}) as parse_auth,
        ):
            outcome = client.bloks_caa_login()

        self.assertTrue(outcome["logged_in"])
        self.assertEqual(outcome["result"], send_result)
        parse_auth.assert_called_once_with(authorization)

    def test_full_caa_login_returns_reason_when_preflight_is_incomplete(self):
        client = self.build_client()

        with (
            mock.patch.object(client, "bloks_caa_login_prepare", return_value=False),
            mock.patch.object(client, "bloks_caa_login_send_request") as send,
        ):
            outcome = client.bloks_caa_login()

        self.assertFalse(outcome["logged_in"])
        self.assertIn("preflight", outcome["reason"])
        send.assert_not_called()

    def test_full_caa_login_can_skip_preflight_for_prepared_client(self):
        client = self.build_client()

        with (
            mock.patch.object(client, "bloks_caa_login_prepare") as prepare,
            mock.patch.object(client, "bloks_caa_login_send_request", return_value={}) as send,
            mock.patch.object(client, "bloks_apply_login_response", return_value=False),
        ):
            outcome = client.bloks_caa_login(prepare=False)

        self.assertFalse(outcome["logged_in"])
        prepare.assert_not_called()
        send.assert_called_once_with(
            client.password,
            username=client.username,
            domain="b.i.instagram.com",
        )

    def test_full_caa_login_dispatches_profile_code_challenge(self):
        client = self.build_client()
        send_result = {"layout": {"bloks_payload": {"action": AP_2SV_ENTRYPOINT}}}

        with (
            mock.patch.object(client, "bloks_caa_login_prepare", return_value=True),
            mock.patch.object(client, "bloks_caa_login_send_request", return_value=send_result),
            mock.patch.object(client, "bloks_apply_login_response", return_value=False),
            mock.patch.object(
                client,
                "bloks_caa_resolve_two_step_verification",
                return_value={"logged_in": True, "reason": "", "result": {}},
            ) as resolve,
        ):
            outcome = client.bloks_caa_login(verification_code="654321")

        self.assertTrue(outcome["logged_in"])
        resolve.assert_called_once_with(
            send_result,
            verification_code="654321",
            domain="b.i.instagram.com",
        )

    def test_full_caa_login_returns_legacy_context_when_no_session_is_applied(self):
        client = self.build_client()

        with (
            mock.patch.object(client, "bloks_caa_login_prepare", return_value=True),
            mock.patch.object(client, "bloks_caa_login_send_request", return_value={}),
            mock.patch.object(client, "bloks_apply_login_response", return_value=False),
            mock.patch.object(client, "bloks_extract_two_step_verification_context", return_value="legacy-context"),
        ):
            outcome = client.bloks_caa_login()

        self.assertFalse(outcome["logged_in"])
        self.assertEqual(outcome["two_step_verification_context"], "legacy-context")
        self.assertIn("did not return a session", outcome["reason"])


class CaaVerifyProfileRegressionTestCase(unittest.TestCase):
    ENTRYPOINT = "com.bloks.www.ap.two_step_verification.entrypoint_async"
    CODE_ENTRY = "com.bloks.www.ap.two_step_verification.code_entry"
    CODE_ENTRY_ASYNC = "com.bloks.www.ap.two_step_verification.code_entry_async"

    def build_client(self):
        client = Client()
        client.uuid = "00000000-0000-4000-8000-000000000000"
        client.phone_id = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
        client.android_device_id = "android-123"
        client.mid = "mid-123"
        client.bloks_versioning_id = "bloks-version"
        client.username = "example_user"
        client.caa_aac = '{"aaccs":"server"}'
        return client

    @staticmethod
    def action(app_id, context_data, container="action"):
        payload = {container: (f'"{app_id}" (f4i (dkc "context_data" "device_id") (dkc "{context_data}" "device"))')}
        return {"layout": {"bloks_payload": payload}}

    def test_context_extraction_matches_exact_app_and_reads_template_map(self):
        client = self.build_client()
        result = {
            "layout": {
                "bloks_payload": {
                    "action": (
                        f'"{self.CODE_ENTRY}_help" (f4i (dkc "context_data") (dkc "wrong")) '
                        f'"{self.CODE_ENTRY}" (f4i (dkc "context_data") (dkc "entry-context"))'
                    ),
                    "ft": {
                        "template": (f'"{self.CODE_ENTRY_ASYNC}" (f4i (dkc "context_data") (dkc "submit-context"))')
                    },
                }
            }
        }

        self.assertEqual(client.bloks_extract_context_data(result, self.CODE_ENTRY), "entry-context")
        self.assertEqual(client.bloks_extract_context_data(result, self.CODE_ENTRY_ASYNC), "submit-context")

    def test_context_extraction_pairs_context_key_with_value_at_same_index(self):
        client = self.build_client()
        result = {
            "layout": {
                "bloks_payload": {
                    "action": (
                        f'"{self.CODE_ENTRY}" (f4i (dkc "device_id" "context_data") (dkc "device" "expected-context"))'
                    )
                }
            }
        }

        self.assertEqual(client.bloks_extract_context_data(result, self.CODE_ENTRY), "expected-context")

    def test_context_extraction_stays_in_target_string_and_decodes_escapes(self):
        client = self.build_client()
        expected = 'context-with-"quotes"'
        result = {
            "layout": {
                "bloks_payload": {
                    "unrelated": f'"{self.CODE_ENTRY}" without-a-map',
                    "target": (
                        f'"{self.CODE_ENTRY}" '
                        f'(f4i (dkc "device_id" "context_data") (dkc "device" {json.dumps(expected)}))'
                    ),
                }
            }
        }

        self.assertEqual(client.bloks_extract_context_data(result, self.CODE_ENTRY), expected)

    def test_context_extraction_does_not_use_a_later_apps_map(self):
        client = self.build_client()
        result = {
            "layout": {
                "bloks_payload": {
                    "action": (
                        f'"{self.CODE_ENTRY}" (noop) '
                        '"com.bloks.www.unrelated.action" '
                        '(f4i (dkc "context_data") (dkc "wrong-context"))'
                    )
                }
            }
        }

        self.assertEqual(client.bloks_extract_context_data(result, self.CODE_ENTRY), "")

    def test_context_extraction_returns_empty_for_missing_anchor_or_context(self):
        client = self.build_client()

        self.assertEqual(client.bloks_extract_context_data({}, self.CODE_ENTRY), "")
        self.assertEqual(
            client.bloks_extract_context_data(
                {"layout": {"bloks_payload": {"action": f'"{self.CODE_ENTRY}" (dkc "other" "value")'}}},
                self.CODE_ENTRY,
            ),
            "",
        )

    def test_verify_profile_chains_contexts_and_applies_terminal_login(self):
        client = self.build_client()
        send_result = self.action(self.ENTRYPOINT, "entry-context")
        entry_result = self.action(self.CODE_ENTRY, "code-context")
        code_result = self.action(self.CODE_ENTRY_ASYNC, "submit-context", container="ft")
        submit_result = {"layout": {"bloks_payload": {"action": "embedded-login"}}}
        calls = []

        with (
            mock.patch.object(
                client,
                "bloks_ap_two_step_verification_entrypoint",
                side_effect=lambda context, **kwargs: calls.append(("entry", context)) or entry_result,
            ),
            mock.patch.object(
                client,
                "bloks_ap_two_step_verification_code_entry",
                side_effect=lambda context, **kwargs: calls.append(("code", context)) or code_result,
            ),
            mock.patch.object(
                client,
                "bloks_ap_two_step_verification_submit_code",
                side_effect=lambda context, code, **kwargs: calls.append(("submit", context, code)) or submit_result,
            ),
            mock.patch.object(client, "bloks_apply_login_response", return_value=True),
        ):
            outcome = client.bloks_caa_resolve_two_step_verification(send_result, verification_code="654321")

        self.assertTrue(outcome["logged_in"])
        self.assertEqual(
            calls,
            [("entry", "entry-context"), ("code", "code-context"), ("submit", "submit-context", "654321")],
        )

    def test_verify_profile_uses_existing_challenge_code_handler(self):
        client = self.build_client()
        send_result = self.action(self.ENTRYPOINT, "entry-context")
        entry_result = self.action(self.CODE_ENTRY, "code-context")
        code_result = self.action(self.CODE_ENTRY_ASYNC, "submit-context", container="ft")
        client.challenge_code_handler = Mock(return_value="123456")

        with (
            mock.patch.object(client, "bloks_ap_two_step_verification_entrypoint", return_value=entry_result),
            mock.patch.object(client, "bloks_ap_two_step_verification_code_entry", return_value=code_result),
            mock.patch.object(client, "bloks_ap_two_step_verification_submit_code", return_value={}) as submit,
            mock.patch.object(client, "bloks_apply_login_response", return_value=False),
        ):
            client.bloks_caa_resolve_two_step_verification(send_result)

        client.challenge_code_handler.assert_called_once()
        self.assertEqual(submit.call_args.args[:2], ("submit-context", "123456"))

    def test_verify_profile_reports_each_missing_context(self):
        client = self.build_client()
        send_result = self.action(self.ENTRYPOINT, "entry-context")
        entry_result = self.action(self.CODE_ENTRY, "code-context")

        self.assertEqual(
            client.bloks_caa_resolve_two_step_verification({})["reason"],
            "missing entrypoint context_data",
        )
        with mock.patch.object(client, "bloks_ap_two_step_verification_entrypoint", return_value={}):
            self.assertEqual(
                client.bloks_caa_resolve_two_step_verification(send_result)["reason"],
                "missing code_entry context_data",
            )
        with (
            mock.patch.object(client, "bloks_ap_two_step_verification_entrypoint", return_value=entry_result),
            mock.patch.object(client, "bloks_ap_two_step_verification_code_entry", return_value={}),
        ):
            self.assertEqual(
                client.bloks_caa_resolve_two_step_verification(send_result)["reason"],
                "missing code_entry_async context_data",
            )

    def test_verify_profile_raises_when_code_handler_returns_no_code(self):
        client = self.build_client()
        send_result = self.action(self.ENTRYPOINT, "entry-context")
        entry_result = self.action(self.CODE_ENTRY, "code-context")
        code_result = self.action(self.CODE_ENTRY_ASYNC, "submit-context", container="ft")
        client.challenge_code_handler = Mock(return_value=None)

        with (
            mock.patch.object(client, "bloks_ap_two_step_verification_entrypoint", return_value=entry_result),
            mock.patch.object(client, "bloks_ap_two_step_verification_code_entry", return_value=code_result),
            self.assertRaises(ChallengeRequired),
        ):
            client.bloks_caa_resolve_two_step_verification(send_result)

    def test_verify_profile_surfaces_submit_code_rejection_as_challenge_error(self):
        client = self.build_client()
        send_result = self.action(self.ENTRYPOINT, "entry-context")
        entry_result = self.action(self.CODE_ENTRY, "code-context")
        code_result = self.action(self.CODE_ENTRY_ASYNC, "submit-context", container="ft")
        rejection = UnknownError("The security code is invalid")

        with (
            mock.patch.object(client, "bloks_ap_two_step_verification_entrypoint", return_value=entry_result),
            mock.patch.object(client, "bloks_ap_two_step_verification_code_entry", return_value=code_result),
            mock.patch.object(client, "bloks_ap_two_step_verification_submit_code", side_effect=rejection),
            self.assertRaises(ChallengeError) as raised,
        ):
            client.bloks_caa_resolve_two_step_verification(send_result, verification_code="654321")

        self.assertIn("profile-code submission failed", str(raised.exception))
        self.assertIs(raised.exception.__cause__, rejection)

    def test_verify_profile_requests_are_prelogin_and_use_caa_domain(self):
        client = self.build_client()

        with mock.patch.object(client, "bloks_async_action", return_value={}) as action:
            client.bloks_ap_two_step_verification_entrypoint("entry-context", domain="b.i.instagram.com")
            client.bloks_ap_two_step_verification_submit_code("submit-context", "123456", domain="b.i.instagram.com")

        for call in action.call_args_list:
            self.assertTrue(call.kwargs["login"])
            self.assertEqual(call.kwargs["domain"], "b.i.instagram.com")

        with mock.patch.object(client, "bloks_app", return_value={}) as app:
            client.bloks_ap_two_step_verification_code_entry("code-context", domain="b.i.instagram.com")

        self.assertTrue(app.call_args.kwargs["login"])
        self.assertEqual(app.call_args.kwargs["domain"], "b.i.instagram.com")
