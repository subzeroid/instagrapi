import io
import itertools
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import requests
from requests.adapters import HTTPAdapter

from instagrapi import Client
from instagrapi.mixins import public as public_mixin

LEGACY_GRAPHQL_UA = "Instagram 273.0.0.16.70 (iPhone15,2; iOS 17_5_1; en_US; en-US; scale=3.00; 1290x2796; 470085518)"
PROFILE = {
    "pk": "123",
    "username": "example",
    "full_name": "Example",
    "is_private": False,
    "is_verified": False,
    "profile_pic_url": "https://example.test/pic.jpg",
    "media_count": 1,
    "follower_count": 2,
    "following_count": 3,
    "is_business": False,
}
LSD_HTML = '<script>["LSD",[],{"token":"lsd-token"}]</script>'


class PublicUserAgentTestCase(unittest.TestCase):
    def setUp(self):
        self.clients = []
        ticks = itertools.count(10, 2)
        patcher = mock.patch.object(
            public_mixin, "time", SimpleNamespace(time=lambda: next(ticks), sleep=lambda _: None)
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def build_client(self, payloads=None, client_class=Client, **kwargs):
        client = client_class(request_timeout=0, **kwargs)
        self.clients.append(client)
        self.addCleanup(client.public.close)
        self.addCleanup(client.private.close)
        self.bind_recording(client, payloads)
        return client

    def bind_recording(self, client, payloads=None):
        client._recorded = []
        queue = list(payloads or [])

        class RecordingAdapter(HTTPAdapter):
            def send(self, request, **kwargs):
                client._recorded.append({"method": request.method, "agents": [request.headers["User-Agent"]]})
                payload = queue.pop(0) if queue else {"status": "ok", "data": {"user": PROFILE, "ok": True}}
                body = payload.encode() if isinstance(payload, str) else json.dumps(payload).encode()
                response = requests.Response()
                response.status_code = 200
                response._content = body
                response.raw = io.BytesIO(body)
                response.url = request.url
                response.request = request
                return response

        client.public.mount("https://", RecordingAdapter())
        client.last_response_ts = 0

    def test_defaults_keep_the_existing_route_profiles(self):
        client = self.build_client()
        web_ua = client.public_user_agent
        private_ua = client.user_agent
        client.public_request("https://www.instagram.com/", return_json=True)
        client.public_doc_id_graphql_request("1", {})
        self.assertEqual(client._recorded[0]["agents"], [web_ua])
        self.assertEqual(client._recorded[1]["agents"], [LEGACY_GRAPHQL_UA])
        self.assertEqual(client.public.headers["User-Agent"], web_ua)
        self.assertEqual(client.user_agent, private_ua)

    def test_constructor_graphql_agent_reaches_a_high_level_profile_helper(self):
        client = self.build_client(
            public_user_agent="fixture-web-agent", public_graphql_user_agent="fixture-graphql-agent"
        )
        profile = client.user_info_v2_gql("123")
        self.assertEqual(profile.username, "example")
        self.assertEqual(client._recorded[-1]["agents"], ["fixture-graphql-agent"])
        self.assertEqual(client.public.headers["User-Agent"], "fixture-web-agent")

    def test_changing_graphql_agent_reaches_username_search_and_profile(self):
        client = self.build_client(
            payloads=[
                {
                    "data": {
                        "xdt_api__v1__fbsearch__non_profiled_serp": {"users": [{"pk": "123", "username": "example"}]}
                    }
                },
                {"data": {"user": PROFILE}},
            ]
        )
        client.public_graphql_user_agent = "fixture-next-graphql-agent"
        profile = client.user_info_by_username_v2_gql("example")
        self.assertEqual(profile.pk, "123")
        self.assertEqual([r["agents"] for r in client._recorded], [["fixture-next-graphql-agent"]] * 2)

    def test_none_graphql_agent_shares_the_web_agent(self):
        client = self.build_client(public_user_agent="fixture-shared-agent", public_graphql_user_agent=None)
        client.public_request("https://www.instagram.com/", return_json=True)
        client.public_graphql_request({}, query_hash="fixture-query")
        client.public_doc_id_graphql_request("1", {})
        self.assertEqual([r["agents"] for r in client._recorded], [["fixture-shared-agent"]] * 3)

    def test_lsd_preparation_and_post_keep_the_web_agent(self):
        client = self.build_client(
            payloads=[LSD_HTML, {"data": {"ok": True}}],
            public_user_agent="fixture-web-agent",
            public_graphql_user_agent="fixture-graphql-agent",
        )
        result = client.public_doc_id_graphql_request("1", {}, include_lsd=True)
        self.assertEqual(result, {"ok": True})
        self.assertEqual([r["method"] for r in client._recorded], ["GET", "POST"])
        self.assertEqual([r["agents"] for r in client._recorded], [["fixture-web-agent"]] * 2)

    def test_request_agent_override_is_case_insensitive_and_does_not_persist(self):
        client = self.build_client(public_user_agent="fixture-web-agent")
        for key in ["User-Agent", "user-agent", "USER-AGENT"]:
            with self.subTest(key=key):
                client.public_doc_id_graphql_request("1", {}, headers={key: "fixture-request-agent"})
                self.assertEqual(client._recorded[-1]["agents"], ["fixture-request-agent"])
                self.assertEqual(client.public.headers["User-Agent"], "fixture-web-agent")
        client.public_doc_id_graphql_request("1", {})
        self.assertEqual(client._recorded[-1]["agents"], [LEGACY_GRAPHQL_UA])

    def test_agents_are_independent_between_clients(self):
        first = self.build_client(public_graphql_user_agent="fixture-first-agent")
        second = self.build_client()
        first.public_doc_id_graphql_request("1", {})
        second.public_doc_id_graphql_request("1", {})
        self.assertEqual(first._recorded[-1]["agents"], ["fixture-first-agent"])
        self.assertEqual(second._recorded[-1]["agents"], [LEGACY_GRAPHQL_UA])

    def test_subclass_graphql_default_is_preserved(self):
        class CustomClient(Client):
            public_graphql_user_agent = "fixture-subclass-agent"

        client = self.build_client(client_class=CustomClient)
        client.public_doc_id_graphql_request("1", {})
        self.assertEqual(client._recorded[-1]["agents"], ["fixture-subclass-agent"])

    def test_custom_agents_survive_settings_roundtrip(self):
        original = self.build_client(
            public_user_agent="fixture-web-agent", public_graphql_user_agent="fixture-graphql-agent"
        )
        settings = json.loads(json.dumps(original.get_settings()))
        self.assertEqual(settings.get("public_user_agent"), "fixture-web-agent")
        self.assertEqual(settings.get("public_graphql_user_agent"), "fixture-graphql-agent")
        restored = self.build_client(settings=settings)
        restored.public_request("https://www.instagram.com/", return_json=True)
        restored.public_doc_id_graphql_request("1", {})
        self.assertEqual([r["agents"] for r in restored._recorded], [["fixture-web-agent"], ["fixture-graphql-agent"]])

    def test_saved_agents_take_precedence_over_constructor_agents(self):
        settings = {
            "public_transport": "requests",
            "public_user_agent": "fixture-saved-web",
            "public_graphql_user_agent": "fixture-saved-graphql",
        }
        client = self.build_client(
            settings=settings,
            public_user_agent="fixture-constructor-web",
            public_graphql_user_agent="fixture-constructor-graphql",
        )
        client.public_doc_id_graphql_request("1", {})
        self.assertEqual(client.public.headers["User-Agent"], "fixture-saved-web")
        self.assertEqual(client._recorded[-1]["agents"], ["fixture-saved-graphql"])

    def test_explicit_constructor_agent_is_kept_with_legacy_settings(self):
        client = self.build_client(settings={"public_transport": "requests"}, public_user_agent="fixture-explicit-web")
        client.public_request("https://www.instagram.com/", return_json=True)
        self.assertEqual(client._recorded[-1]["agents"], ["fixture-explicit-web"])

    def test_legacy_settings_keep_the_selected_transport_default(self):
        # This settings test records prepared requests without requiring the optional curl adapter.
        adapter = mock.Mock(side_effect=lambda **kwargs: HTTPAdapter())
        with mock.patch.dict("sys.modules", {"curl_adapter": SimpleNamespace(CurlCffiAdapter=adapter)}):
            for transport in ["requests", "curl"]:
                with self.subTest(transport=transport):
                    client = self.build_client(settings={"public_transport": transport})
                    self.assertEqual(
                        client.public_user_agent, client._default_public_user_agent(transport, "chrome136")
                    )
                    self.assertEqual(client.public.headers["User-Agent"], client.public_user_agent)
                    client.public_doc_id_graphql_request("1", {})
                    self.assertEqual(client._recorded[-1]["agents"], [LEGACY_GRAPHQL_UA])

    def test_setter_shares_agent_and_updates_saved_settings(self):
        client = self.build_client()
        private_ua = client.user_agent
        self.assertTrue(client.set_public_user_agent("fixture-shared-agent"))
        client.public_doc_id_graphql_request("1", {})
        self.assertEqual(client._recorded[-1]["agents"], ["fixture-shared-agent"])
        self.assertIsNone(client.public_graphql_user_agent)
        self.assertEqual(client.public.headers["User-Agent"], "fixture-shared-agent")
        self.assertEqual(client.settings["public_user_agent"], "fixture-shared-agent")
        self.assertIsNone(client.settings["public_graphql_user_agent"])
        self.assertEqual(client.user_agent, private_ua)

    def test_setter_supports_independent_agents_and_file_roundtrip(self):
        client = self.build_client()
        client.set_public_user_agent("fixture-web-agent", "fixture-graphql-agent")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            client.dump_settings(path)
            restored = self.build_client()
            restored.load_settings(path)
            self.bind_recording(restored)
            restored.public_doc_id_graphql_request("1", {})
        self.assertEqual(restored.public.headers["User-Agent"], "fixture-web-agent")
        self.assertEqual(restored._recorded[-1]["agents"], ["fixture-graphql-agent"])

    def test_shared_none_survives_roundtrip_and_follows_later_web_changes(self):
        client = self.build_client(public_user_agent="fixture-web-agent", public_graphql_user_agent=None)
        restored = self.build_client(settings=client.get_settings())
        self.assertIsNone(restored.public_graphql_user_agent)
        restored.set_public_user_agent("fixture-next-web-agent")
        restored.public_doc_id_graphql_request("1", {})
        self.assertEqual(restored._recorded[-1]["agents"], ["fixture-next-web-agent"])

    def test_transport_selection_updates_the_saved_web_profile(self):
        client = self.build_client(public_user_agent="fixture-custom-web", public_graphql_user_agent=None)
        client.set_retry_config(public_transport="requests")
        self.bind_recording(client)
        expected = client._default_public_user_agent("requests", "chrome136")
        client.public_doc_id_graphql_request("1", {})
        self.assertEqual(client._recorded[-1]["agents"], [expected])
        self.assertEqual(client.settings["public_user_agent"], expected)
        self.assertIsNone(client.settings["public_graphql_user_agent"])
        client.init()
        self.bind_recording(client)
        self.assertEqual(client.public.headers["User-Agent"], expected)

    def test_transport_selection_preserves_an_independent_graphql_profile(self):
        client = self.build_client(public_graphql_user_agent="fixture-graphql-agent")
        client.set_retry_config(public_transport="requests")
        self.bind_recording(client)
        client.public_doc_id_graphql_request("1", {})
        self.assertEqual(client._recorded[-1]["agents"], ["fixture-graphql-agent"])
        self.assertEqual(client.get_settings()["public_graphql_user_agent"], "fixture-graphql-agent")
