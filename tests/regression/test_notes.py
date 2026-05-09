from tests.helpers import *


class NoteMixinRegressionTestCase(unittest.TestCase):
    def test_get_note_helpers_by_user(self):
        client = Client()
        notes = [
            Note(
                id="1",
                text="hello",
                user_id="10",
                user=UserShort(pk="10", username="example"),
                audience=0,
                created_at=datetime(2024, 1, 1, tzinfo=UTC()),
                expires_at=datetime(2024, 1, 2, tzinfo=UTC()),
                is_emoji_only=False,
                has_translation=False,
                note_style=0,
            )
        ]

        note = client.get_note_by_user(notes, "Example")
        self.assertIsNotNone(note)
        self.assertEqual(note.id, "1")
        self.assertEqual(client.get_note_text_by_user(notes, "example"), "hello")
        self.assertIsNone(client.get_note_by_user(notes, "missing"))
        self.assertIsNone(client.get_note_text_by_user(notes, "missing"))

    def test_notes_music_browser_requests_notes_music_product(self):
        client = Client()
        client.uuid = "uuid-1"
        expected = {
            "status": "ok",
            "alacorn_session_id": "alacorn-1",
            "items": [],
        }

        with mock.patch.object(client, "private_request", return_value=expected) as private_request:
            result = client.notes_music_browser()

        private_request.assert_called_once_with(
            "music/notes_audio_browser/",
            data={"product": "music_notes", "_uuid": "uuid-1"},
            with_signature=False,
        )
        self.assertEqual(result, expected)

    def test_create_music_note_uses_create_inbox_tray_item_graphql_payload(self):
        client = Client()
        client.uuid = "uuid-1"
        client.private.cookies.set("ds_user_id", "123")
        track = {
            "id": "818914077374464",
            "audio_asset_id": "818914077374464",
            "audio_cluster_id": "745666024934797",
            "highlight_start_times_in_ms": [66000],
        }
        graphql_response = {
            "data": {
                "mutation": {
                    "success": True,
                    "inbox_tray_item": {
                        "note_dict": {
                            "note_id": "18072502430410984",
                            "text": "Now playing",
                            "author_id": "123",
                            "audience": 1,
                            "note_style": 1,
                            "is_emoji_only": False,
                            "has_translation": False,
                            "1lcreated_at": 1710000000,
                            "1lexpires_at": 1710086400,
                            "author": {
                                "pk": "123",
                                "username": "example",
                                "full_name": "",
                            },
                        }
                    },
                }
            }
        }

        with mock.patch.object(client, "private_graphql_request", return_value=graphql_response) as graphql_query:
            note = client.create_music_note(
                track=track,
                text="Now playing",
                audience=1,
                start_time=66000,
                duration=30000,
                browse_session_id="browse-1",
                alacorn_session_id="alacorn-1",
            )

        graphql_query.assert_called_once()
        data = graphql_query.call_args.args[0]
        self.assertEqual(data["client_doc_id"], "3510400299951610199199089856")
        self.assertEqual(data["fb_api_req_friendly_name"], "CreateInboxTrayItemRequest")
        variables = json.loads(data["variables"])
        request = variables["request"]
        self.assertEqual(request["inbox_tray_item_type"], "note")
        self.assertEqual(request["audience"], 1)
        note_params = request["additional_params"]["note_create_params"]
        self.assertEqual(note_params["text"], "Now playing")
        self.assertEqual(note_params["note_style"], 1)
        music_info = note_params["note_create_info"]["music_note_create_info"]
        self.assertEqual(music_info["audio_asset_id"], "818914077374464")
        self.assertEqual(music_info["audio_cluster_id"], "745666024934797")
        self.assertEqual(music_info["start_time"], 66000)
        self.assertEqual(music_info["duration"], 30000)
        self.assertEqual(music_info["browse_session_id"], "browse-1")
        self.assertEqual(music_info["alacorn_session_id"], "alacorn-1")
        self.assertIsNone(music_info["selected_lyrics"])
        self.assertFalse(music_info["is_reshare_eligible"])
        self.assertEqual(note.id, "18072502430410984")
        self.assertEqual(note.text, "Now playing")
        self.assertEqual(note.audience, 1)
        self.assertEqual(note.note_style, 1)
