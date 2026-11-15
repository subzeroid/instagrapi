"""Text Note GraphQL contract and Unicode regressions; no live calls."""

import json
import unittest
from unittest.mock import Mock
from urllib.parse import parse_qs

from instagrapi import Client
from instagrapi.exceptions import ClientGraphqlError
from instagrapi.mixins.note import NoteAudience


class TextNoteGraphQLTests(unittest.TestCase):
    def setUp(self):
        self.client = Client(private_transport="requests")
        self.client.request_timeout = 0
        self.client.authorization_data = {"ds_user_id": "123"}
        self.client.request_log = Mock()
        self.payload = None
        self.post = Mock(side_effect=self.reply)
        self.client.private.post = self.post

    def tearDown(self):
        for name in ("private", "public", "graphql"):
            getattr(self.client, name).close()

    @staticmethod
    def note_dict(text, audience):
        return {
            "note_id": "42",
            "text": text,
            "author_id": "123",
            "audience": audience,
            "note_style": 0,
            "created_at": 1710000000,
            "expires_at": 1710086400,
            "author": {"pk": "123", "username": "synthetic", "full_name": ""},
        }

    def reply(self, url, **kwargs):
        if url.endswith("/api/v1/notes/create_note"):
            fields = parse_qs(kwargs["data"])
            payload = json.loads(fields["signed_body"][0].split(".", 1)[1])
            text = payload["text"].replace("🚀", "\ufffd")
            body = {
                "status": "ok",
                "id": "42",
                "text": text,
                "user_id": "123",
                "user": {"pk": "123", "username": "synthetic"},
                "audience": payload["audience"],
                "created_at": 1710000000,
                "expires_at": 1710086400,
                "is_emoji_only": False,
                "has_translation": False,
                "note_style": 0,
            }
        else:
            self.assertEqual(url, "https://i.instagram.com/graphql/query")
            request = json.loads(kwargs["data"]["variables"])["request"]
            note = self.note_dict(request["additional_params"]["note_create_params"]["text"], request["audience"])
            body = (
                self.payload
                if self.payload is not None
                else {
                    "data": {
                        "__typename": "Mutation",
                        "1$xdt_create_inbox_tray_item(request:$request)": {
                            "success": True,
                            "inbox_tray_item": {"note_dict": note},
                        },
                    }
                }
            )
        response = Mock(status_code=200, url=url, headers={"Content-Type": "application/json"})
        response.json.return_value = body
        response.text = json.dumps(body)
        response.content = response.text.encode()
        return response

    def test_preserves_emoji_through_modern_operation(self):
        text = "Test 🚀"
        note = self.client.create_note(text)
        self.assertEqual(note.text, text)
        self.assertEqual(note.audience, 0)
        self.assertEqual(note.note_style, 0)
        self.assertEqual(note.id, "42")
        self.assertEqual(note.user_id, "123")
        self.assertEqual(self.post.call_count, 1)
        self.assertEqual(self.post.call_args.args[0], "https://i.instagram.com/graphql/query")

    def test_contract_preserves_text_and_audience_without_music_payload(self):
        for text in ("ASCII", "Привет café 漢字", "☀ 👍🏽 👩‍💻 🇺🇳 ❤️", "e\u0301"):
            for audience in NoteAudience:
                with self.subTest(text=text, audience=audience):
                    self.post.reset_mock()
                    before = dict(self.client.private.headers)
                    note = self.client.create_note(text, audience=audience)
                    self.assertEqual((note.text, note.audience), (text, int(audience)))
                    self.assertEqual(self.post.call_count, 1)
                    form = self.post.call_args.kwargs["data"]
                    self.assertIsInstance(form, dict)
                    self.assertEqual(form["client_doc_id"], "3510400299951610199199089856")
                    self.assertEqual(form["fb_api_req_friendly_name"], "CreateInboxTrayItemRequest")
                    self.assertEqual(form["locale"], self.client.locale)
                    self.assertEqual(
                        json.loads(form["variables"]),
                        {
                            "should_fetch_content_note_stack_video_info": False,
                            "request": {
                                "inbox_tray_item_type": "note",
                                "audience": int(audience),
                                "additional_params": {"note_create_params": {"text": text, "note_style": 0}},
                            },
                        },
                    )
                    headers = self.post.call_args.kwargs["headers"]
                    self.assertEqual(headers["X-Root-Field-Name"], "xdt_create_inbox_tray_item")
                    self.assertEqual(headers["X-GraphQL-Client-Library"], "pando")
                    self.assertEqual(dict(self.client.private.headers), before)

    def test_failure_is_explicit_and_never_retries_or_falls_back(self):
        for payload in (
            None,
            {"success": False},
            {"success": True, "inbox_tray_item": None},
            {"success": True, "inbox_tray_item": {}},
            {"success": True, "inbox_tray_item": {"note_dict": None}},
            {"success": True, "inbox_tray_item": {"note_dict": "invalid"}},
        ):
            with self.subTest(payload=payload):
                self.post.reset_mock()
                self.payload = {"data": {"__typename": "Mutation", "xdt_create_inbox_tray_item": payload}}
                before = dict(self.client.private.headers)
                with self.assertRaisesRegex(ClientGraphqlError, "Failed to create Note"):
                    self.client.create_note("Test 🚀")
                self.assertEqual(self.post.call_count, 1)
                self.assertEqual(dict(self.client.private.headers), before)

    def test_graphql_error_does_not_replay(self):
        self.payload = {"errors": [{"message": "mutation rejected"}]}
        with self.assertRaises(ClientGraphqlError):
            self.client.create_note("Test 🚀")
        self.assertEqual(self.post.call_count, 1)

    def test_audience_validation_prevents_dispatch(self):
        with self.assertRaisesRegex(AssertionError, "NoteAudience"):
            self.client.create_note("Test 🚀", audience=1)
        self.post.assert_not_called()

    def test_authentication_required_before_dispatch(self):
        self.client.authorization_data = {}
        with self.assertRaisesRegex(AssertionError, "Login required"):
            self.client.create_note("Test 🚀")
        self.post.assert_not_called()
