from tests import helpers as _helpers
from tests.helpers import *


class ClientNoteLiveTestCase(_helpers.ClientPrivateTestCase):
    def __init__(self, *args, **kwargs):
        self.cl = None
        return unittest.TestCase.__init__(self, *args, **kwargs)

    def setup_method(self, *args, **kwargs):
        return None

    def setUp(self):
        if not TEST_ACCOUNTS_URL:
            self.skipTest("TEST_ACCOUNTS_URL is required for Notes live tests")
        try:
            self.cl = self.fresh_account()
        except RuntimeError as exc:
            self.skipTest(str(exc))

    def first_notes_music_track(self, music):
        for item in music.get("items") or []:
            candidates = []
            playlist = item.get("playlist") or {}
            candidates.extend(playlist.get("preview_items") or [])
            candidates.extend(item.get("preview_items") or [])
            for candidate in candidates:
                track = candidate.get("track") or candidate
                if (track.get("audio_asset_id") or track.get("id")) and track.get(
                    "audio_cluster_id"
                ):
                    return track
        return None

    def delete_own_note_if_exists(self):
        for note in self.cl.get_notes():
            if str(note.user_id) == str(self.cl.user_id):
                try:
                    self.cl.delete_note(note.id)
                except Exception as exc:
                    print(
                        "Notes live cleanup delete_note failed: "
                        f"{exc.__class__.__name__} {exc}"
                    )

    def test_create_music_note_from_notes_music_browser(self):
        self.delete_own_note_if_exists()
        music = self.cl.notes_music_browser()
        self.assertEqual(music.get("status"), "ok")
        alacorn_session_id = music.get("alacorn_session_id")
        if not alacorn_session_id:
            self.skipTest("notes_music_browser did not return alacorn_session_id")
        track = self.first_notes_music_track(music)
        if not track:
            self.skipTest("notes_music_browser did not return a usable track")

        note = None
        try:
            note = self.cl.create_music_note(
                track=track,
                text="",
                audience=0,
                alacorn_session_id=alacorn_session_id,
            )
            self.assertIsInstance(note, Note)
            self.assertTrue(note.id)
            self.assertEqual(note.audience, 0)
            self.assertEqual(note.note_style, 1)
        finally:
            if note:
                try:
                    self.cl.delete_note(note.id)
                except Exception as exc:
                    print(
                        "Notes live cleanup delete_note failed: "
                        f"{exc.__class__.__name__} {exc}"
                    )
