import uuid
from instagrapi.extractors import (
   extract_note,
)
from instagrapi.types import (
    NoteRequest,
)
from instagrapi.utils import dumps


class NoteMixin:

    def send_note(self, note_content: str, audience: int) -> NoteRequest:
    
        assert self.user_id, "Login required"
        method = "text"

        data = {
            "text": note_content,
            "uuid": uuid.uuid4(),
            "audience":audience
        }

        self.private_request(
            f"notes/create_note",
            data = self.with_default_data(data),
            with_signature=False
        )

