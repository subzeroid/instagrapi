import uuid

from instagrapi.types import NoteRequest


class NoteMixin:
    def send_note(self, note_content: str, audience: int) -> NoteRequest:
        assert self.user_id, "Login required"
        data = {"text": note_content, "uuid": uuid.uuid4(), "audience": audience}
        self.private_request(
            "notes/create_note",
            data=self.with_default_data(data),
            with_signature=False,
        )
