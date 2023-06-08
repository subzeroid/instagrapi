import uuid

from instagrapi.types import NoteRequest


class NoteMixin:
    def get_my_notes(self):
        """
        Get your personal notes
        """
        headers = self.base_headers
        headers["X-IG-Client-Endpoint"] = "DirectInboxFragment:direct_inbox"
        return self.private_request("notes/get_notes/", headers=headers)

    def delete_note(self, note_id: int):
        """
        Delete one of your personal notes
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
