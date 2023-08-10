import uuid

from instagrapi.types import NoteRequest
from instagrapi.extractors import extract_note
import json


class NoteMixin:
    def get_all_notes(self):
        """
        Get all notes from a user's friends and their note
        """
        headers = self.base_headers
        headers["X-IG-Client-Endpoint"] = "DirectInboxFragment:direct_inbox"
        response = self.private_request("notes/get_notes/", headers=headers)
        #print(response)
        notes_data = response["items"]
        notes = []
        for note_data in notes_data:
            note = extract_note(note_data)
            notes.append(note)
        return notes

    def get_note_by_user(self, notes: [], username: str):
        """
        Search notes by user and return the corresponding NoteResponse object.
        If the user is not found, return None.
        """
        for note_data in notes:
            user_data = note_data.user
            if user_data and user_data.username == username:
                return note_data
        return None

    def get_note_content_by_user(self, notes: [], username: str):
        """
        Search notes by user and return the corresponding note text content.
        If the user is not found, return None.
        """
        for note_data in notes:
            user_data = note_data.user
            if user_data and user_data.username == username:
                return note_data.text
        return None

    def delete_note(self, note_id: int):
        """
        Delete your personal notes
        It uses note_id to delete a note
        Use get_my_notes() to get note_id
        """
        headers = dict(self.base_headers)
        headers["X-IG-Client-Endpoint"] = "DirectInboxFragment:direct_inbox"
        return self.private_request(
            "notes/delete_note/",
            headers=headers,
            data={"id": note_id, "_uuid": self.uuid},
            with_signature=False,
        )

    def send_note(self, note_content: str, audience: int) -> NoteRequest:
        assert self.user_id, "Login required"
        data = {"text": note_content, "uuid": uuid.uuid4(), "audience": audience}
        return self.private_request(
            "notes/create_note",
            data=self.with_default_data(data),
            with_signature=False,
        )
