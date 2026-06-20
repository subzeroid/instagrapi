from datetime import datetime, timedelta, timezone
from enum import IntEnum
from typing import Dict, List, Optional, Union

from instagrapi.exceptions import ClientGraphqlError
from instagrapi.types import Note, Track, UserShort
from instagrapi.utils.serialization import dumps

INBOX_TRAY_CLIENT_DOC_ID = "26838444193647008103482058049"
INBOX_TRAY_FRIENDLY_NAME = "InboxTrayRequest"
INBOX_TRAY_ROOT_FIELD = "xdt_get_inbox_tray_items"
CREATE_INBOX_TRAY_ITEM_CLIENT_DOC_ID = "3510400299951610199199089856"
CREATE_INBOX_TRAY_ITEM_FRIENDLY_NAME = "CreateInboxTrayItemRequest"


class NoteAudience(IntEnum):
    MUTUAL_FOLLOWERS = 0
    CLOSE_FRIENDS = 1


class NoteMixin:
    @staticmethod
    def _note_audience_value(audience: NoteAudience) -> int:
        assert isinstance(audience, NoteAudience), (
            f"Invalid audience parameter={audience} (must be NoteAudience.MUTUAL_FOLLOWERS "
            "or NoteAudience.CLOSE_FRIENDS)"
        )
        return int(audience)

    @staticmethod
    def _track_value(track: Union[Track, Dict], key: str):
        if isinstance(track, dict):
            return track.get(key)
        return getattr(track, key, None)

    @classmethod
    def _track_highlight_start(cls, track: Union[Track, Dict]) -> int:
        highlight_times = cls._track_value(track, "highlight_start_times_in_ms") or []
        return int(highlight_times[0]) if highlight_times else 0

    @staticmethod
    def _note_from_note_dict(data: Dict) -> Note:
        note_id = data.get("note_id") or data.get("id")
        author = data.get("author") or {}
        user_id = str(data.get("author_id") or author.get("pk") or author.get("id") or "")
        created_at = int(data.get("1lcreated_at") or data.get("created_at") or 0)
        expires_at = data.get("1lexpires_at") or data.get("expires_at")
        if expires_at is None:
            # Inbox tray GraphQL omits expires_at in current web responses; Notes expire after 24 hours.
            expires_at = int((datetime.fromtimestamp(created_at, tz=timezone.utc) + timedelta(days=1)).timestamp())
        user = UserShort(
            pk=str(author.get("pk") or author.get("id") or user_id),
            username=author.get("username"),
            full_name=author.get("full_name") or "",
            profile_pic_url=author.get("profile_pic_url"),
            is_private=author.get("is_private"),
        )
        return Note(
            id=str(note_id),
            text=data.get("text") or "",
            user_id=user_id,
            user=user,
            audience=int(data.get("audience", 0)),
            created_at=datetime.fromtimestamp(created_at, tz=timezone.utc),
            expires_at=datetime.fromtimestamp(int(expires_at), tz=timezone.utc),
            is_emoji_only=bool(data.get("is_emoji_only", False)),
            has_translation=bool(data.get("has_translation", False)),
            note_style=int(data.get("note_style", 0)),
        )

    @staticmethod
    def _user_from_inbox_tray_item(item: Dict, user_id: str) -> Dict:
        users = (item.get("pog_info") or {}).get("pog_users") or []
        for user in users:
            if str(user.get("id") or user.get("pk")) == str(user_id):
                return user
        return users[0] if users else {}

    @classmethod
    def _note_dict_from_inbox_tray_item(cls, item: Dict) -> Dict:
        note_dict = dict(item.get("note_dict") or {})
        if not note_dict:
            return {}
        note_dict.setdefault("note_id", item.get("inbox_tray_item_id") or item.get("id"))
        author = note_dict.get("author") or {}
        user_id = str(note_dict.get("author_id") or author.get("pk") or author.get("id") or "")
        if not author:
            user = cls._user_from_inbox_tray_item(item, user_id)
            if user:
                note_dict["author"] = {
                    "pk": user.get("pk") or user.get("id"),
                    "username": user.get("username"),
                    "full_name": user.get("full_name") or "",
                    "profile_pic_url": user.get("profile_pic_url"),
                    "is_private": user.get("is_private"),
                }
        return note_dict

    @staticmethod
    def _note_dict_from_create_inbox_tray_item(result: Dict) -> Dict:
        for payload in (result.get("data") or {}).values():
            if payload and payload.get("success"):
                note_dict = payload.get("inbox_tray_item", {}).get("note_dict") or {}
                if note_dict:
                    return note_dict
        raise ClientGraphqlError("Failed to create music Note")

    @staticmethod
    def _inbox_tray_from_graphql_result(result: Dict) -> Dict:
        for payload in (result.get("data") or {}).values():
            if isinstance(payload, dict) and "inbox_tray_items" in payload:
                return payload
        raise ClientGraphqlError("Failed to retrieve Notes in Direct")

    def get_notes(self) -> List[Note]:
        """
        Retrieves Notes in Direct

        Returns
        -------
        List[Notes]
            List of all the Notes in Direct
        """
        result = self.private_graphql_query_request(
            friendly_name=INBOX_TRAY_FRIENDLY_NAME,
            root_field_name=INBOX_TRAY_ROOT_FIELD,
            variables={
                "should_fetch_friend_map_user": True,
                "should_fetch_friend_map_entrypoint": False,
                "should_fetch_comment_info": False,
                "request": {
                    "include_quicksnap_pog": False,
                    "include_friend_map_pog": False,
                    "inbox_tray_item_ids_on_client": [],
                },
                "is_saved_media_on_map_enabled": False,
                "is_location_likes_v2_enabled": True,
            },
            client_doc_id=INBOX_TRAY_CLIENT_DOC_ID,
            priority="u=3, i",
        )
        inbox_tray = self._inbox_tray_from_graphql_result(result)

        notes = []
        for item in inbox_tray.get("inbox_tray_items") or []:
            note_dict = self._note_dict_from_inbox_tray_item(item)
            if note_dict:
                notes.append(self._note_from_note_dict(note_dict))
        return notes

    def get_note_by_user(self, notes: List[Note], username: str) -> Optional[Note]:
        """
        Retrieve a Note for a given username from a notes list.

        Parameters
        ----------
        notes: List[Note]
            Notes returned by get_notes()
        username: str
            Username to search for

        Returns
        -------
        Optional[Note]
            Matching Note or None if not found
        """
        username = str(username).lower()
        for note in notes:
            if note.user and note.user.username and note.user.username.lower() == username:
                return note
        return None

    def get_note_text_by_user(self, notes: List[Note], username: str) -> Optional[str]:
        """
        Retrieve note text for a given username from a notes list.

        Parameters
        ----------
        notes: List[Note]
            Notes returned by get_notes()
        username: str
            Username to search for

        Returns
        -------
        Optional[str]
            Matching note text or None if not found
        """
        note = self.get_note_by_user(notes, username)
        return note.text if note else None

    def last_seen_update_note(self) -> bool:
        """
        Updating your Notes last seen

        Returns
        -------
        bool
            A boolean value
        """
        result = self.private_request("notes/update_notes_last_seen_timestamp/", data={"_uuid": self.uuid})
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
        result = self.private_request("notes/delete_note/", data={"id": note_id, "_uuid": self.uuid})
        return result.get("status", "") == "ok"

    def notes_music_browser(self) -> Dict:
        """
        Retrieve music candidates for Instagram Notes.

        Returns
        -------
        Dict
            Raw response from ``music/notes_audio_browser/``.
        """
        result = self.private_request(
            "music/notes_audio_browser/",
            data={"product": "music_notes", "_uuid": self.uuid},
            with_signature=False,
        )
        assert result.get("status", "") == "ok", "Failed to retrieve Notes music"
        return result

    def create_note(self, text: str, audience: NoteAudience = NoteAudience.MUTUAL_FOLLOWERS) -> Note:
        """
        Create personal Note

        Parameters
        ----------
        text: str
            Content of the Note
        audience: NoteAudience, optional
            Audience to see the Note. Use NoteAudience.MUTUAL_FOLLOWERS
            or NoteAudience.CLOSE_FRIENDS.

        Returns
        -------
        Note
            Created Note

        """
        assert self.user_id, "Login required"
        audience_value = self._note_audience_value(audience)

        data = {"note_style": 0, "text": text, "_uuid": self.uuid, "audience": audience_value}
        result = self.private_request("notes/create_note", data=data)

        assert result.pop("status", "") == "ok", "Failed to create new Note"
        return Note(**result)

    def create_music_note(
        self,
        track: Union[Track, Dict],
        text: str = "",
        audience: NoteAudience = NoteAudience.MUTUAL_FOLLOWERS,
        start_time: Optional[int] = None,
        duration: int = 30000,
        browse_session_id: Optional[str] = None,
        alacorn_session_id: Optional[str] = None,
    ) -> Note:
        """
        Create personal Note with attached music.

        Parameters
        ----------
        track: Track or dict
            Track from ``notes_music_browser()`` or a compatible dict.
        text: str, optional
            Content of the Note.
        audience: NoteAudience, optional
            Audience to see the Note. Use NoteAudience.MUTUAL_FOLLOWERS
            or NoteAudience.CLOSE_FRIENDS.
        start_time: int, optional
            Audio start time in milliseconds. Defaults to the first highlighted
            start time from the track, or 0.
        duration: int, optional
            Audio clip duration in milliseconds, default 30000.
        browse_session_id: str, optional
            Browser session id. Generated when omitted.
        alacorn_session_id: str, optional
            Session id from ``notes_music_browser()``. If omitted, a browser
            request is made to obtain one.

        Returns
        -------
        Note
            Created music Note.
        """
        assert self.user_id, "Login required"
        audience_value = self._note_audience_value(audience)
        audio_asset_id = self._track_value(track, "audio_asset_id") or self._track_value(track, "id")
        audio_cluster_id = self._track_value(track, "audio_cluster_id")
        assert audio_asset_id, "track.audio_asset_id or track.id is required"
        assert audio_cluster_id, "track.audio_cluster_id is required"
        if start_time is None:
            start_time = self._track_highlight_start(track)
        if not browse_session_id:
            browse_session_id = self.generate_uuid()
        if not alacorn_session_id:
            alacorn_session_id = self.notes_music_browser().get("alacorn_session_id")
        assert alacorn_session_id, "alacorn_session_id is required"

        variables = {
            "should_fetch_content_note_stack_video_info": False,
            "request": {
                "inbox_tray_item_type": "note",
                "audience": audience_value,
                "additional_params": {
                    "note_create_params": {
                        "text": text,
                        "note_style": 1,
                        "note_create_info": {
                            "music_note_create_info": {
                                "start_time": int(start_time),
                                "is_reshare_eligible": False,
                                "selected_lyrics": None,
                                "audio_asset_id": str(audio_asset_id),
                                "duration": int(duration),
                                "original_note_id": None,
                                "original_author_id": None,
                                "audio_cluster_id": str(audio_cluster_id),
                                "browse_session_id": browse_session_id,
                                "alacorn_session_id": alacorn_session_id,
                            }
                        },
                    }
                },
            },
        }
        data = {
            "client_doc_id": CREATE_INBOX_TRAY_ITEM_CLIENT_DOC_ID,
            "method": "post",
            "pretty": "false",
            "format": "json",
            "server_timestamps": "true",
            "fb_api_req_friendly_name": CREATE_INBOX_TRAY_ITEM_FRIENDLY_NAME,
            "variables": dumps(variables),
            "enable_canonical_naming": "true",
            "enable_canonical_variable_overrides": "true",
            "enable_canonical_naming_ambiguous_type_prefixing": "true",
            "locale": self.locale,
        }
        result = self.private_graphql_request(data)
        note_dict = self._note_dict_from_create_inbox_tray_item(result)
        return self._note_from_note_dict(note_dict)
