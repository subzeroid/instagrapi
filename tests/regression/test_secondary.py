import base64
import json
import unittest


def literal(value):
    if isinstance(value, dict):
        keys = " ".join(json.dumps(k) for k in value)
        values = " ".join(literal(v) for v in value.values())
        return f"(f4i (dkc {keys}) (dkc {values}))"
    return json.dumps(value)


def envelope(action="", maps=(), embedded=()):
    bundle = {
        "layout": {
            "bloks_payload": {
                "action": action,
                "tree": {"button": " ".join(literal(m) for m in maps)},
                "embedded_payloads": list(embedded),
            }
        }
    }
    return {"data": {"1$bloks_action": {"action": {"action_bundle": {"bloks_bundle_action": json.dumps(bundle)}}}}}


def server(stage, context="opaque-context"):
    value = {
        "reg_context": context,
        "reg_info": json.dumps({"username": "extra_profile"}),
        "flow_info": json.dumps({"flow_name": "secondary_profile_creation_ig_default", "flow_type": "spc"}),
        "device_id": "android-example",
        "family_device_id": "family-example",
        "qe_device_id": "uuid-example",
        "waterfall_id": "waterfall-example",
        "current_step": {"username": 0, "optin": 2, "create": 4}[stage],
        "is_from_logged_out": False,
    }
    value.update(
        {
            "username": {"action": 1},
            "optin": {"is_tds_reg_flow": False},
            "create": {"should_ignore_suma_check": False, "app_id": 0},
        }[stage]
    )
    return value


def success(pk="202", username="extra_profile", user_id=None, auth_override=None):
    auth = {"ds_user_id": pk, "sessionid": "test-session"}
    if auth_override is not None:
        auth = auth_override
    token = "Bearer IGT:2:" + base64.b64encode(json.dumps(auth).encode()).decode()
    wrapper = {
        "registration_response": json.dumps(
            {
                "status": "ok",
                "account_created": True,
                "created_user": {
                    "pk": pk,
                    **({"id": user_id} if user_id is not None else {}),
                    "username": username,
                    "full_name": "",
                    "profile_pic_url": "https://example.com/avatar.jpg",
                },
            }
        ),
        "headers": json.dumps({"ig-set-authorization": token, "ig-set-x-mid": "new-mid"}),
        "cookies": json.dumps({"sessionid": "test-session", "ds_user_id": pk}),
    }
    return envelope(action="(dsh (fom 1 1 " + json.dumps(json.dumps(wrapper)) + "))")


class SecondaryContractTests(unittest.TestCase):
    def helpers(self):
        from instagrapi import secondary

        return secondary

    def test_selects_button_context_not_last_context(self):
        helpers = self.helpers()
        selected = server("username", "next-context")
        other = dict(selected, action=0, reg_context="typing-context")
        result = helpers.continuation(envelope(maps=[selected, other]), "username")
        self.assertEqual(result["reg_context"], "next-context")
        self.assertEqual(result["is_from_logged_out"], 0)

    def test_duplicate_literal_maps_and_nested_network_data(self):
        helpers = self.helpers()
        value = server("optin")
        value["si_device_param_network_info"] = {"is_wifi": True, "default_subscription_info": {"sim_count": 1}}
        result = helpers.continuation(envelope(maps=[value, value]), "optin")
        self.assertEqual(result["si_device_param_network_info"]["is_wifi"], 1)

    def test_conflicting_continuations_are_rejected(self):
        helpers = self.helpers()
        with self.assertRaises(ValueError):
            helpers.continuation(envelope(maps=[server("username", "a"), server("username", "b")]), "username")

    def test_missing_wrong_flow_and_nonliteral_maps_are_rejected(self):
        helpers = self.helpers()
        for response in [
            envelope(),
            envelope(maps=[dict(server("create"), flow_info="{}")]),
            envelope(action='(f4i (dkc "reg_context") (dkc (execute "something")))'),
        ]:
            with self.subTest(response=str(response)[:20]), self.assertRaises(ValueError):
                helpers.continuation(response, "create")

    def test_embedded_registration_headers_are_paired_with_user(self):
        helpers = self.helpers()
        user, auth, headers, cookies = helpers.registration(success(), "101", "extra_profile")
        self.assertEqual(str(user["pk"]), "202")
        self.assertEqual(auth["ds_user_id"], "202")
        self.assertEqual(headers["ig-set-x-mid"], "new-mid")
        self.assertEqual(cookies["sessionid"], auth["sessionid"])

    def test_rejects_parent_identity_and_wrong_username(self):
        helpers = self.helpers()
        for response in [success(pk="101"), success(username="somebody_else")]:
            with self.subTest(response=str(response)[:20]), self.assertRaises(ValueError):
                helpers.registration(response, "101", "extra_profile")

    def test_rejects_conflicting_id_and_pk(self):
        with self.assertRaises(ValueError):
            self.helpers().registration(success(user_id="101"), "101", "extra_profile")

    def test_rejects_invalid_authorization_identity_or_session(self):
        for auth in [
            {},
            {"ds_user_id": "101", "sessionid": "test"},
            {"ds_user_id": "202", "sessionid": ""},
            {"ds_user_id": "202", "sessionid": 123},
        ]:
            with self.subTest(auth=auth), self.assertRaises(ValueError):
                self.helpers().registration(success(auth_override=auth), "101", "extra_profile")

    def test_does_not_accept_success_from_embedded_unexecuted_template(self):
        helpers = self.helpers()
        with self.assertRaises(ValueError):
            helpers.registration(envelope(embedded=[success()]), "101", "extra_profile")

    def test_parenthesis_ui_label_is_not_an_action(self):
        helpers = self.helpers()
        response = envelope(maps=[server("username")])
        response["ui_label"] = "("
        self.assertEqual(helpers.continuation(response, "username")["action"], 1)

    def test_rejects_excessive_payload(self):
        helpers = self.helpers()
        with self.assertRaises(ValueError):
            helpers.continuation({"data": "x" * 2_000_001}, "username")


class SecondaryFlowTests(unittest.TestCase):
    def setUp(self):
        from instagrapi import Client

        self.parent = Client(
            settings={
                "authorization_data": {"ds_user_id": "101", "sessionid": "parent-session"},
                "cookies": {"sessionid": "parent-session", "ds_user_id": "101"},
            },
            proxy="http://127.0.0.1:12345",
            private_transport="requests",
            request_timeout=0,
        )
        self.before = json.dumps(self.parent.get_settings(), sort_keys=True)
        self.calls = []
        self.closed = []

    def tearDown(self):
        for session in (self.parent.private, self.parent.public, self.parent.graphql):
            session.close()

    def transport(self, fail_at=None, redirect=False, interrupt=False):
        from urllib.parse import parse_qs

        import requests

        replies = [
            envelope(maps=[server("username")]),
            envelope(maps=[server("optin")]),
            envelope(maps=[server("create")]),
            success(),
        ]
        test = self

        def send(adapter, request, **kwargs):
            form = parse_qs(request.body)
            variables = json.loads(form["variables"][0])
            test.calls.append((request, variables))
            test.assertEqual(adapter.max_retries.total, 0)
            test.assertEqual(kwargs["timeout"], test.parent.read_timeout)
            test.assertEqual(kwargs["proxies"]["https"], test.parent.proxy)
            test.assertEqual(kwargs["verify"], test.parent.tls_verify)
            index = len(test.calls) - 1
            response = requests.Response()
            response.request = request
            response.url = request.url
            response.status_code = 200
            if index == fail_at:
                if interrupt:
                    raise KeyboardInterrupt()
                if redirect:
                    response.status_code = 307
                    response.headers["location"] = "https://example.com/redirect"
                    response._content = b"{}"
                    return response
                raise requests.ReadTimeout("sensitive request detail")
            response._content = json.dumps(replies[index]).encode()
            return response

        return send

    def run_flow(self, **transport_options):
        from unittest.mock import patch

        import requests

        original = requests.Session.close
        test = self

        def close(session):
            test.closed.append(session)
            original(session)

        with (
            patch("requests.adapters.HTTPAdapter.send", self.transport(**transport_options)),
            patch.object(requests.Session, "close", close),
        ):
            return self.parent.create_secondary_account("extra_profile")

    def test_isolated_session_and_embedded_credentials(self):
        result = self.run_flow()
        self.assertEqual(result.user.pk, "202")
        self.assertEqual(result.settings["authorization_data"]["ds_user_id"], "202")
        self.assertNotIn("test-session", repr(result))
        self.assertNotIn("parent-session", json.dumps(result.settings))
        self.assertEqual(json.dumps(self.parent.get_settings(), sort_keys=True), self.before)
        self.assertEqual(len(self.calls), 4)
        self.assertEqual(len(self.closed), 3)
        self.assertNotIn(self.parent.private, self.closed)
        for request, variables in self.calls:
            self.assertNotIn("authorization", request.headers)
            self.assertNotIn("cookie", request.headers)
            self.assertNotIn("ig-u-ds-user-id", request.headers)
            self.assertEqual(request.url, "https://b.i.instagram.com/graphql_www")
        entry = json.loads(self.calls[0][1]["params"]["params"])
        self.assertEqual(entry["auth_token"], self.parent.authorization)
        from instagrapi import Client

        additional = Client(settings=result.settings, proxy=self.parent.proxy)
        try:
            self.assertEqual(str(additional.user_id), "202")
            self.assertEqual(additional.sessionid, "test-session")
            self.assertEqual(additional.proxy, self.parent.proxy)
            self.assertEqual(additional.tls_verify, self.parent.tls_verify)
        finally:
            for session in (additional.private, additional.public, additional.graphql):
                session.close()

    def test_timeout_is_not_retried_and_reports_unknown_outcome(self):
        from instagrapi.exceptions import SecondaryAccountError

        with self.assertRaises(SecondaryAccountError) as raised:
            self.run_flow(fail_at=3)
        self.assertEqual(len(self.calls), 4)
        self.assertEqual(raised.exception.stage, "create")
        self.assertTrue(raised.exception.creation_may_have_succeeded)
        self.assertNotIn("sensitive", str(raised.exception))
        self.assertEqual(len(self.closed), 3)
        self.assertEqual(json.dumps(self.parent.get_settings(), sort_keys=True), self.before)

    def test_creation_redirect_is_not_followed(self):
        from instagrapi.exceptions import SecondaryAccountError

        with self.assertRaises(SecondaryAccountError):
            self.run_flow(fail_at=3, redirect=True)
        self.assertEqual(len(self.calls), 4)

    def test_keyboard_interrupt_closes_temporary_sessions(self):
        with self.assertRaises(KeyboardInterrupt):
            self.run_flow(fail_at=1, interrupt=True)
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(len(self.closed), 3)
        self.assertEqual(json.dumps(self.parent.get_settings(), sort_keys=True), self.before)

    def test_rejects_invalid_input_before_network(self):
        from unittest.mock import patch

        with patch("requests.adapters.HTTPAdapter.send", self.transport()):
            for username in ["", "with space", "x" * 31, "name\n", "name/other"]:
                with self.subTest(username=username), self.assertRaises(ValueError):
                    self.parent.create_secondary_account(username)
            with self.assertRaises(ValueError):
                self.parent.create_secondary_account("extra_profile", link_to_main_account=False)
        self.assertEqual(self.calls, [])

    def test_cleanup_failure_attempts_every_close_and_preserves_flow_error(self):
        from unittest.mock import patch

        import requests

        from instagrapi.exceptions import SecondaryAccountError

        for failure in (RuntimeError, KeyboardInterrupt):
            for fail_at in (None, 1):
                with self.subTest(failure=failure, fail_at=fail_at):
                    self.calls = []
                    closed = []
                    original = requests.Session.close

                    def close(session):
                        closed.append(session)
                        original(session)
                        if len(closed) == 1:
                            raise failure("sensitive cleanup detail")

                    with (
                        patch("requests.adapters.HTTPAdapter.send", self.transport(fail_at=fail_at)),
                        patch.object(requests.Session, "close", close),
                    ):
                        expected = (
                            KeyboardInterrupt
                            if failure is KeyboardInterrupt and fail_at is None
                            else SecondaryAccountError
                        )
                        with self.assertRaises(expected) as raised:
                            self.parent.create_secondary_account("extra_profile")
                    self.assertEqual(len(closed), 3)
                    if expected is SecondaryAccountError:
                        self.assertEqual(raised.exception.stage, "cleanup" if fail_at is None else "username")
                        self.assertNotIn("sensitive", str(raised.exception))

    def test_requires_authenticated_parent_before_network(self):
        from unittest.mock import patch

        from instagrapi import Client
        from instagrapi.exceptions import LoginRequired

        client = Client()
        try:
            with patch("requests.adapters.HTTPAdapter.send", self.transport()):
                with self.assertRaises(LoginRequired):
                    client.create_secondary_account("extra_profile")
            self.assertEqual(self.calls, [])
        finally:
            for session in (client.private, client.public, client.graphql):
                session.close()

    def test_rejects_unbounded_timeout_before_allocating_worker(self):
        from unittest.mock import patch

        from instagrapi import Client

        for value in (None, 0, -1, float("inf"), float("nan"), True, "30"):
            with self.subTest(timeout=value):
                self.parent.read_timeout = value
                with patch.object(Client, "__init__", side_effect=AssertionError("worker allocated")):
                    with self.assertRaises(ValueError):
                        self.parent.create_secondary_account("extra_profile")

    def test_partial_worker_initialization_interrupt_closes_allocated_sessions(self):
        from unittest.mock import patch

        import requests

        from instagrapi import Client

        for count in (1, 2, 3):
            allocated = []
            closed = []
            original_close = requests.Session.close

            def initialize(worker, *args, **kwargs):
                for name in ("private", "public", "graphql")[:count]:
                    session = requests.Session()
                    allocated.append(session)
                    setattr(worker, name, session)
                raise KeyboardInterrupt()

            def close(session):
                closed.append(session)
                original_close(session)

            with (
                self.subTest(count=count),
                patch.object(Client, "__init__", initialize),
                patch.object(requests.Session, "close", close),
            ):
                with self.assertRaises(KeyboardInterrupt):
                    self.parent.create_secondary_account("extra_profile")
            self.assertEqual(closed, allocated)
