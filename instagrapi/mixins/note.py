from typing import List

from instagrapi.types import Note


class NoteMixin:
    def get_notes(self) -> List[Note]:
        """
        Retrieves Notes in Direct

        Returns
        -------
        List[Notes]
            List of all the Notes in Direct
        """
        result = self.private_request("notes/get_notes/")
        assert result.get("status", "") == "ok", "Failed to retrieve Notes in Direct"

        notes = []
        for item in result.get("items", []):
            notes.append(Note(**item))
        return notes

    def last_seen_update_note(self) -> bool:
        """
        Updating your Notes last seen

        Returns
        -------
        bool
            A boolean value
        """
        result = self.private_request(
            "notes/update_notes_last_seen_timestamp/", data={"_uuid": self.uuid}
        )
        return result.get("status", "") == "ok"

    def delete_note(self, note_id: int) -> bool:
        """
        Delete one of your personal notes

        Parameters
        ----------
        note_id: int
            ID of the Note to delete

        Returns
        -------
        bool
            A boolean value
        """
        result = self.private_request(
            "notes/delete_note/", data={"id": note_id, "_uuid": self.uuid}
        )
        return result.get("status", "") == "ok"

    def create_note(self, text: str, audience: int = 0) -> Note:
        """
        Create personal Note

        Parameters
        ----------
        text: str
            Content of the Note
        audience: optional
            Audience to see Note, deafult 0 (Followers you follow back).
            Best Friends - 1

        Returns
        -------
        Note
            Created Note

        """
        assert self.user_id, "Login required"
        assert audience in (
            0,
            1,
        ), f"Invalid audience parameter={audience} (must be 0 or 1)"

        data = {"note_style": 0, "text": text, "_uuid": self.uuid, "audience": audience}
        result = self.private_request("notes/create_note", data=data)

        assert result.pop("status", "") == "ok", "Failed to create new Note"
        return Note(**result)
