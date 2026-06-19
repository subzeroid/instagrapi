import random
import re
import secrets
import time
import uuid
from pathlib import Path
from typing import Dict, List, Literal, Optional, Tuple

from instagrapi.exceptions import (
    ClientError,
    ClientNotFoundError,
    DirectMessageNotFound,
    DirectThreadNotFound,
)
from instagrapi.extractors import (
    extract_direct_media,
    extract_direct_message,
    extract_direct_short_thread,
    extract_direct_thread,
    extract_user_short,
)
from instagrapi.types import (
    DirectMessage,
    DirectShortThread,
    DirectThread,
    Media,
    UserShort,
)
from instagrapi.utils.serialization import dumps
from instagrapi.utils.video import read_video_metadata, read_video_metadata_with_moviepy

SELECTED_FILTERS = ("flagged", "unread")
SEARCH_MODES = ("raven", "universal")
SEND_ATTRIBUTES = ("message_button", "inbox_search")
SEND_ATTRIBUTES_MEDIA = (
    "feed_timeline",
    "feed_contextual_chain",
    "feed_short_url",
    "feed_contextual_self_profile",
    "feed_contextual_profile",
)
BOXES = ("general", "primary")


def _direct_id_list(ids) -> List[int]:
    if ids is None:
        return []
    if isinstance(ids, (int, str)):
        return [int(ids)]
    return [int(item) for item in ids]


SELECTED_FILTER = Literal["flagged", "unread"]
SEARCH_MODE = Literal["raven", "universal"]
SEND_ATTRIBUTE = Literal["message_button", "inbox_search"]
SEND_ATTRIBUTE_MEDIA = Literal[
    "feed_timeline",
    "feed_contextual_chain",
    "feed_short_url",
    "feed_contextual_self_profile",
    "feed_contextual_profile",
]
BOX = Literal["general", "primary"]


class DirectMixin:
    """
    Helpers for managing Direct Messaging
    """

    def _direct_request_tracking_params(self) -> Dict[str, str]:
        return {
            "eb_device_id": "0",
            "igd_request_log_tracking_id": self.generate_uuid(),
        }

    def direct_threads(
        self,
        amount: int = 20,
        selected_filter: Optional[SELECTED_FILTER] = None,
        box: Optional[BOX] = None,
        thread_message_limit: Optional[int] = None,
    ) -> List[DirectThread]:
        """
        Get direct message threads

        Parameters
        ----------
        amount: int, optional
            Maximum number of media to return, default is 20
        selected_filter: str, optional
            Filter to apply to threads ("flagged" or "unread")
        box: str, optional
            Box to gather threads from ("primary" or "general") (business accounts only)
        thread_message_limit: int, optional
            Thread message limit, deafult is 10

        Returns
        -------
        List[DirectThread]
            A list of objects of DirectThread
        """

        cursor = None
        threads = []
        # self.private_request("direct_v2/get_presence/")
        while True:
            threads_chunk, cursor = self.direct_threads_chunk(selected_filter, box, thread_message_limit, cursor)
            for thread in threads_chunk:
                threads.append(thread)

            if not cursor or (amount and len(threads) >= amount):
                break
        if amount:
            threads = threads[:amount]
        return threads

    def direct_threads_chunk(
        self,
        selected_filter: Optional[SELECTED_FILTER] = None,
        box: Optional[BOX] = None,
        thread_message_limit: Optional[int] = None,
        cursor: str = None,
    ) -> Tuple[List[DirectThread], str]:
        """
        Get direct a chunk of threads by cursor value

        Parameters
        ----------
        selected_filter: str, optional
            Filter to apply to threads ("flagged" or "unread")
        thread_message_limit: int, optional
            Thread message limit, deafult is 10
        box: str, optional
            Box to gather threads from ("primary" or "general") (business accounts only)
        cursor: str, optional
            Cursor from the previous chunk request

        Returns
        -------
        Tuple[List[DirectThread], str]
            A tuple of list of objects of DirectThread and str (cursor)
        """
        assert self.user_id, "Login required"
        params = {
            **self._direct_request_tracking_params(),
            "visual_message_return_type": "unseen",
            "thread_message_limit": "10",
            "persistentBadging": "true",
            "limit": "20",
            "is_prefetching": "false",
            "fetch_reason": "initial_snapshot",
            "include_old_mrs": "false",
            "no_pending_badge": "true",
            "push_disabled": self._bool_to_ig_string(self.push_disabled),
        }
        if selected_filter:
            if selected_filter not in SELECTED_FILTERS:
                raise ValueError(f"selected_filter must be one of {SELECTED_FILTERS}")
            params.update({"selected_filter": selected_filter})
        if box:
            assert box in BOXES, f'Unsupported box="{box}" {BOXES}'
            params.update({"folder": "1" if box == "general" else "0"})
        if thread_message_limit:
            params.update({"thread_message_limit": thread_message_limit})
        if cursor:
            params.update({"cursor": cursor, "direction": "older", "fetch_reason": "page_scroll"})

        threads = []
        result = self.private_request("direct_v2/inbox/", params=params)
        inbox = result.get("inbox", {})
        for thread in inbox.get("threads", []):
            threads.append(extract_direct_thread(thread))
        cursor = inbox.get("oldest_cursor")
        return threads, cursor

    def direct_pending_inbox(self, amount: int = 20) -> List[DirectThread]:
        """
        Get direct threads of Pending inbox

        Parameters
        ----------
        amount: int, optional
            Maximum number of threads to return, default is 20

        Returns
        -------
        List[DirectThread]
            A list of objects of DirectThread
        """

        cursor = None
        threads = []
        while True:
            new_threads, cursor = self.direct_pending_chunk(cursor)
            for thread in new_threads:
                threads.append(thread)

            if not cursor or (amount and len(threads) >= amount):
                break
        if amount:
            threads = threads[:amount]
        return threads

    def direct_requests(self, amount: int = 20) -> List[DirectThread]:
        """
        Get Direct message request threads, also known as pending inbox or invitations.

        Parameters
        ----------
        amount: int, optional
            Maximum number of threads to return, default is 20

        Returns
        -------
        List[DirectThread]
            A list of objects of DirectThread
        """
        return self.direct_pending_inbox(amount)

    def direct_pending_requests_preview(self, pending_inbox_filters: Optional[List[str]] = None) -> Dict:
        """
        Get the lightweight Direct message requests preview.

        This mirrors the Android app's inbox bootstrap request and returns
        counters such as ``pending_requests_total`` and
        ``unread_pending_requests`` without loading the full pending inbox.

        Parameters
        ----------
        pending_inbox_filters: List[str], optional
            Optional pending inbox filters. Defaults to an empty list.

        Returns
        -------
        Dict
            Raw response from ``direct_v2/async_get_pending_requests_preview/``.
        """
        assert self.user_id, "Login required"
        params = {"pending_inbox_filters": dumps(pending_inbox_filters or [])}
        return self.private_request("direct_v2/async_get_pending_requests_preview/", params=params)

    def direct_pending_chunk(self, cursor: str = None) -> Tuple[List[DirectThread], str]:
        """
        Get direct threads of Pending inbox. Chunk

        Parameters
        ----------
        cursor: str, optional
            Cursor from the previous chunk request

        Returns
        -------
        Tuple[List[DirectThread], str]
            A tuple of list of objects of DirectThread and str (cursor)
        """
        assert self.user_id, "Login required"
        params = {
            "visual_message_return_type": "unseen",
            "persistentBadging": "true",
            "is_prefetching": "false",
            "request_session_id": self.request_id,
        }
        if cursor:
            params.update({"cursor": cursor})

        threads = []
        result = self.private_request("direct_v2/pending_inbox/", params=params)
        inbox = result.get("inbox", {})
        for thread in inbox.get("threads", []):
            threads.append(extract_direct_thread(thread))
        cursor = inbox.get("oldest_cursor")
        return threads, cursor

    def direct_pending_approve(self, thread_id: int) -> bool:
        """
        Approve pending direct thread

        Parameters
        ----------
        thread_id: int
            ID of thread to approve

        Returns
        -------
        bool
            A boolean value
        """
        assert self.user_id, "Login required"

        result = self.private_request(
            f"direct_v2/threads/{thread_id}/approve/",
            data={"filter": "DEFAULT", "_uuid": self.uuid},
            with_signature=False,
        )
        return result.get("status", "") == "ok"

    def direct_request_approve(self, thread_id: int) -> bool:
        """
        Approve a Direct message request thread.

        Parameters
        ----------
        thread_id: int
            ID of thread to approve

        Returns
        -------
        bool
            A boolean value
        """
        return self.direct_pending_approve(thread_id)

    def direct_spam_inbox(self, amount: int = 20) -> List[DirectThread]:
        """
        Get direct threads of Spam inbox (hidden requests)

        Parameters
        ----------
        amount: int, optional
            Maximum number of threads to return, default is 20

        Returns
        -------
        List[DirectThread]
            A list of objects of DirectThread
        """
        cursor = None
        threads = []
        while True:
            new_threads, cursor = self.direct_spam_chunk(cursor)
            for thread in new_threads:
                threads.append(thread)

            if not cursor or (amount and len(threads) >= amount):
                break
        if amount:
            threads = threads[:amount]
        return threads

    def direct_spam_chunk(self, cursor: str = None) -> Tuple[List[DirectThread], str]:
        """
        Get direct threads of Spam inbox (hidden requests). Chunk

        Parameters
        ----------
        cursor: str, optional
            Cursor from the previous chunk request

        Returns
        -------
        Tuple[List[DirectThread], str]
            A tuple of list of objects of DirectThread and str (cursor)
        """
        assert self.user_id, "Login required"
        params = {
            "visual_message_return_type": "unseen",
            "persistentBadging": "true",
            "is_prefetching": "false",
        }
        if cursor:
            params.update({"cursor": cursor})

        threads = []
        result = self.private_request("direct_v2/spam_inbox/", params=params)
        inbox = result.get("inbox", {})
        for thread in inbox.get("threads", []):
            threads.append(extract_direct_thread(thread))
        cursor = inbox.get("oldest_cursor")
        return threads, cursor

    def direct_thread(self, thread_id: int, amount: int = 20) -> DirectThread:
        """
        Get all the information about a Direct Message thread

        Parameters
        ----------
        thread_id: int
            Unique identifier of a Direct Message thread

        amount: int, optional
            Maximum number of media to return, default is 20

        Returns
        -------
        DirectThread
            An object of DirectThread
        """
        assert self.user_id, "Login required"
        params = {
            "visual_message_return_type": "unseen",
            "direction": "older",
            "seq_id": "40065",  # 59663
            "limit": "20",
        }
        cursor = None
        items = []
        while True:
            if cursor:
                params["cursor"] = cursor
            try:
                result = self.private_request(f"direct_v2/threads/{thread_id}/", params=params)
            except ClientNotFoundError as e:
                raise DirectThreadNotFound(e, thread_id=thread_id, **self.last_json)
            thread = result["thread"]
            for item in thread["items"]:
                items.append(item)
            cursor = thread.get("oldest_cursor")
            if not cursor or (amount and len(items) >= amount):
                break
        if amount:
            items = items[:amount]
        thread["items"] = items
        return extract_direct_thread(thread)

    def direct_messages(self, thread_id: int, amount: int = 20) -> List[DirectMessage]:
        """
        Get all the messages from a thread

        Parameters
        ----------
        thread_id: int
            Unique identifier of a Direct Message thread

        amount: int, optional
            Maximum number of media to return, default is 20

        Returns
        -------
        List[DirectMessage]
            A list of objects of DirectMessage
        """
        assert self.user_id, "Login required"
        return self.direct_thread(thread_id, amount).messages

    def direct_message(self, thread_id: int, message_id: int, amount: int = 20) -> DirectMessage:
        """
        Get a Direct message from a thread by message id.

        Parameters
        ----------
        thread_id: int
            Unique identifier of a Direct Message thread

        message_id: int
            Unique identifier of a Direct Message item

        amount: int, optional
            Maximum number of latest messages to scan, default is 20

        Returns
        -------
        DirectMessage
            An object of DirectMessage
        """
        message_id = str(message_id)
        for message in self.direct_messages(thread_id, amount):
            if message.id == message_id:
                return message
        raise DirectMessageNotFound(
            f"Direct message {message_id} not found in thread {thread_id}",
            thread_id=thread_id,
            message_id=message_id,
        )

    def direct_answer(self, thread_id: int, text: str) -> DirectMessage:
        """
        Post a message on a Direct Message thread

        Parameters
        ----------
        thread_id: int
            Unique identifier of a Direct Message thread

        text: str
            String to be posted on the thread

        Returns
        -------
        DirectMessage
            An object of DirectMessage
        """
        assert self.user_id, "Login required"
        return self.direct_send(text, [], [int(thread_id)])

    def direct_send(
        self,
        text: str,
        user_ids: List[int] = [],
        thread_ids: List[int] = [],
        send_attribute: SEND_ATTRIBUTE = "message_button",
        reply_to_message: Optional[DirectMessage] = None,
    ) -> DirectMessage:
        """
        Send a direct message to list of users or threads

        Parameters
        ----------
        text: str
            String to be posted on the thread

        user_ids: List[int]
            List of unique identifier of Users id

        thread_ids: List[int]
            List of unique identifier of Direct Message thread id

        send_attribute: str, optional
            Sending option. Default is "message_button"
        reply_to_message: DirectMessage, optional
            Message to reply to in the target thread

        Returns
        -------
        DirectMessage
            An object of DirectMessage
        """
        assert self.user_id, "Login required"
        user_ids = _direct_id_list(user_ids)
        thread_ids = _direct_id_list(thread_ids)
        assert (user_ids or thread_ids) and not (user_ids and thread_ids), (
            "Specify user_ids or thread_ids, but not both"
        )
        assert send_attribute in SEND_ATTRIBUTES, f'Unsupported send_attribute="{send_attribute}" {SEND_ATTRIBUTES}'
        method = "text"
        token = self.generate_mutation_token()

        kwargs = {
            "action": "send_item",
            "is_x_transport_forward": "false",
            "send_silently": "false",
            "is_shh_mode": "0",
            "send_attribution": send_attribute,
            "client_context": token,
            "device_id": self.android_device_id,
            "mutation_token": token,
            "_uuid": self.uuid,
            "btt_dual_send": "false",
            "nav_chain": (
                "1qT:feed_timeline:1,1qT:feed_timeline:2,1qT:feed_timeline:3,"
                "7Az:direct_inbox:4,7Az:direct_inbox:5,5rG:direct_thread:7"
            ),
            "is_ae_dual_send": "false",
            "offline_threading_id": token,
        }
        if "http" in text:
            method = "link"
            kwargs["link_text"] = text
            kwargs["link_urls"] = dumps(re.findall(r"(https?://[^\s]+)", text))
        else:
            kwargs["text"] = text
        if thread_ids:
            kwargs["thread_ids"] = dumps([int(tid) for tid in thread_ids])
        if user_ids:
            kwargs["recipient_users"] = dumps([[int(uid) for uid in user_ids]])
        if reply_to_message:
            kwargs["replied_to_action_source"] = "swipe"
            kwargs["replied_to_item_id"] = reply_to_message.id
            kwargs["replied_to_client_context"] = reply_to_message.client_context
        result = self.private_request(
            f"direct_v2/threads/broadcast/{method}/",
            data=self.with_default_data(kwargs),
            with_signature=False,
        )
        return extract_direct_message(result["payload"])

    def _direct_message_reaction(
        self,
        thread_id: int,
        message_id: int,
        emoji: str,
        reaction_status: str,
        client_context: Optional[str] = None,
        action_source: str = "double_tap",
        target_item_type: Optional[str] = None,
    ) -> bool:
        assert self.user_id, "Login required"
        assert reaction_status in ("created", "deleted"), 'Unsupported reaction_status="%s"' % reaction_status
        token = self.generate_mutation_token()
        data = {
            "action": "send_item",
            "is_x_transport_forward": "false",
            "send_silently": "false",
            "is_shh_mode": "0",
            "send_attribution": "message_reaction",
            "client_context": token,
            "device_id": self.android_device_id,
            "mutation_token": token,
            "btt_dual_send": "false",
            "nav_chain": (
                "1qT:feed_timeline:1,1qT:feed_timeline:2,1qT:feed_timeline:3,"
                "7Az:direct_inbox:4,7Az:direct_inbox:5,5rG:direct_thread:7"
            ),
            "is_ae_dual_send": "false",
            "offline_threading_id": token,
            "thread_ids": dumps([str(thread_id)]),
            "item_type": "reaction",
            "reaction_type": "like",
            "reaction_status": reaction_status,
            "node_type": "item",
            "item_id": str(message_id),
            "emoji": emoji,
            "reaction_action_source": action_source,
        }
        if client_context:
            data["original_message_client_context"] = client_context
        if target_item_type:
            data["target_item_type"] = target_item_type
        result = self.private_request(
            "direct_v2/threads/broadcast/reaction/",
            data=self.with_default_data(data),
            with_signature=False,
        )
        return result.get("status") == "ok"

    def direct_send_reaction(
        self,
        thread_id: int,
        message_id: int,
        emoji: str = "❤",
        client_context: Optional[str] = None,
        action_source: str = "double_tap",
        target_item_type: Optional[str] = None,
    ) -> bool:
        """
        Send an emoji reaction to a Direct message item.

        Parameters
        ----------
        thread_id: int
            Direct Message thread id
        message_id: int
            Direct Message item id to react to
        emoji: str, optional
            Emoji reaction. Default is heart
        client_context: str, optional
            Original message client_context when available
        action_source: str, optional
            Reaction source. Default is "double_tap"
        target_item_type: str, optional
            Original message item type for special items like raven_media or voice_media

        Returns
        -------
        bool
            A boolean value
        """
        return self._direct_message_reaction(
            thread_id,
            message_id,
            emoji,
            "created",
            client_context=client_context,
            action_source=action_source,
            target_item_type=target_item_type,
        )

    def direct_delete_reaction(
        self,
        thread_id: int,
        message_id: int,
        emoji: str = "❤",
        client_context: Optional[str] = None,
        action_source: str = "double_tap",
        target_item_type: Optional[str] = None,
    ) -> bool:
        """
        Delete the current user's emoji reaction from a Direct message item.

        Parameters
        ----------
        thread_id: int
            Direct Message thread id
        message_id: int
            Direct Message item id to remove the reaction from
        emoji: str, optional
            Emoji reaction to remove. Default is heart
        client_context: str, optional
            Original message client_context when available
        action_source: str, optional
            Reaction source. Default is "double_tap"
        target_item_type: str, optional
            Original message item type for special items like raven_media or voice_media

        Returns
        -------
        bool
            A boolean value
        """
        return self._direct_message_reaction(
            thread_id,
            message_id,
            emoji,
            "deleted",
            client_context=client_context,
            action_source=action_source,
            target_item_type=target_item_type,
        )

    def direct_message_like(
        self,
        thread_id: int,
        message_id: int,
        client_context: Optional[str] = None,
    ) -> bool:
        """
        Like a Direct message item with a heart reaction.
        """
        return self.direct_send_reaction(thread_id, message_id, client_context=client_context)

    def direct_message_unlike(
        self,
        thread_id: int,
        message_id: int,
        client_context: Optional[str] = None,
    ) -> bool:
        """
        Remove the current user's heart reaction from a Direct message item.
        """
        return self.direct_delete_reaction(thread_id, message_id, client_context=client_context)

    def direct_send_photo(self, path: Path, user_ids: List[int] = [], thread_ids: List[int] = []) -> DirectMessage:
        """
        Send a direct photo to list of users or threads

        Parameters
        ----------
        path: Path
            Path to photo that will be posted on the thread
        user_ids: List[int]
            List of unique identifier of Users id
        thread_ids: List[int]
            List of unique identifier of Direct Message thread id

        Returns
        -------
        DirectMessage
            An object of DirectMessage
        """
        return self.direct_send_file(path, user_ids, thread_ids, content_type="photo")

    def _direct_video_metadata(self, path: Path) -> Tuple[int, int, float]:
        width, height, duration_sec = 720, 1280, 1.0
        try:
            metadata = read_video_metadata(path)
        except Exception:
            try:
                metadata = read_video_metadata_with_moviepy(path)
            except ImportError:
                return width, height, duration_sec
            except Exception:  # noqa: BLE001
                return width, height, duration_sec
        return metadata.width, metadata.height, metadata.duration or duration_sec

    def _direct_thread_id_from_user_ids(self, user_ids: List[int], media_kind: str) -> int:
        user_ids = _direct_id_list(user_ids)
        thread = self.direct_thread_by_participants(user_ids)
        thread_id = thread.get("thread_v2_id") or thread.get("thread_id")
        if not thread_id and isinstance(self.last_json, dict):
            thread = self.last_json.get("thread") or {}
            thread_id = thread.get("thread_v2_id") or thread.get("thread_id")
        if not thread_id:
            raise DirectThreadNotFound(
                "No existing direct thread found for participants; "
                f"direct {media_kind} send currently requires an existing thread",
                user_ids=user_ids,
                **(self.last_json if isinstance(self.last_json, dict) else {}),
            )
        return int(thread_id)

    def direct_send_video(self, path: Path, user_ids: List[int] = [], thread_ids: List[int] = []) -> DirectMessage:
        """
        Send a direct video to a list of users or threads.

        Replicates the IG Android client's three-step protocol (captured
        2026-05-06). Instagram retired
        ``direct_v2/threads/broadcast/configure_video/`` and migrated to
        ``raven_attachment/?video=1``:

        1. ``GET https://rupload.facebook.com/messenger_video/{32hex}-{seg}-{size}-{ms}-{ms}``
           returns the resumable upload offset.
        2. ``POST`` to the same URL with raw mp4 bytes returns
           ``{"media_id": <int>, "id": 0}``.
        3. ``POST direct_v2/threads/broadcast/raven_attachment/?video=1`` with a
           signed body whose ``attachment_fbid`` and ``video_result`` both equal
           the ``media_id`` from step 2.

        The video MUST be H.264 in an MP4 container (``.mp4``); the server
        ``x-entity-type`` is fixed at ``video/mp4``.

        Parameters
        ----------
        path: Path
            Path to a .mp4 file (H.264 + AAC).
        user_ids: List[int]
            List of unique identifiers of Users id.
        thread_ids: List[int]
            List of unique identifiers of Direct Message thread id.

        Returns
        -------
        DirectMessage
            An object of DirectMessage.
        """
        assert self.user_id, "Login required"
        user_ids = _direct_id_list(user_ids)
        thread_ids = _direct_id_list(thread_ids)
        assert (user_ids or thread_ids) and not (user_ids and thread_ids), (
            "Specify user_ids or thread_ids, but not both"
        )
        if user_ids:
            thread_ids = [self._direct_thread_id_from_user_ids(user_ids, "video")]

        path = Path(path)
        video_bytes = path.read_bytes()
        size = len(video_bytes)

        width, height, duration_sec = self._direct_video_metadata(path)

        # Steps 1 + 2: FB-domain rupload, returns media_id.
        hex_id = secrets.token_hex(16)
        ms = int(time.time() * 1000)
        entity = f"{hex_id}-0-{size}-{ms}-{ms}"
        upload_id = str(random.randint(10**11, 10**12 - 1))
        waterfall_id = f"{upload_id}_{hex_id[:12].upper()}_Mixed_0"
        media_id = self._video_rupload(video_bytes, entity, waterfall_id)

        # Step 3: signed broadcast to raven_attachment/?video=1.
        token = self.generate_mutation_token()
        composition_id = str(uuid.uuid4())
        camera_session_id = str(uuid.uuid4())
        data = {
            "recipient_users": "[]",
            "view_mode": "permanent",
            "has_camera_metadata": "1",
            "camera_entry_point": "3",
            "thread_ids": dumps([str(tid) for tid in thread_ids]),
            "reshare_mode": "allow_reshare",
            "original_media_type": "2",  # 2 = video
            "send_attribution": "direct_composer",
            "client_context": token,
            "camera_session_id": camera_session_id,
            "attachment_fbid": str(media_id),
            "include_e2ee_mentioned_user_list": "1",
            "hide_from_profile_grid": "false",
            "timezone_offset": "0",
            "client_shared_at": str(int(time.time())),
            "configure_mode": "2",
            "source_type": "3",
            "camera_position": "back",
            "video_result": str(media_id),
            "_uid": str(self.user_id),
            "device_id": self.android_device_id,
            "composition_id": composition_id,
            "mutation_token": token,
            "_uuid": self.uuid,
            "creation_surface": "camera",
            "has_ig_camera_edits": "false",
            "capture_type": "normal",
            "audience": "default",
            "upload_id": upload_id,
            "client_timestamp": str(int(time.time())),
            "media_transformation_info": dumps(
                {
                    "width": str(width),
                    "height": str(height),
                    "x_transform": "0",
                    "y_transform": "0",
                    "zoom": "1.0",
                    "rotation": "0.0",
                    "background_coverage": "0.0",
                }
            ),
            "clips": [{"length": duration_sec, "source_type": "3", "camera_position": "back"}],
            "poster_frame_index": 0,
            "length": duration_sec,
            "audio_muted": False,
            "edits": {"filter_type": 0, "filter_strength": 1.0},
            "extra": {"source_width": width, "source_height": height},
            "device": {
                "manufacturer": "Google",
                "model": "sdk_gphone_arm64",
                "android_version": 30,
                "android_release": "11",
            },
        }
        result = self.private_request(
            "direct_v2/threads/broadcast/raven_attachment/?video=1",
            data=self.with_default_data(data),
            with_signature=True,
        )
        return extract_direct_message(result["payload"])

    def _messenger_rupload_headers(self, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        bearer = self.private.headers.get("Authorization") or self.authorization
        user_id = str(self.user_id)
        rur = self.private.headers.get("IG-U-RUR", "")
        mid = self.private.headers.get("X-MID", "")

        headers = {
            "authorization": bearer,
            "ig-intended-user-id": user_id,
            "ig-u-ds-user-id": user_id,
            # The real client may send zstd; requests cannot decode zstd, and
            # rupload accepts gzip for these Direct attachment flows.
            "accept-encoding": "gzip",
            "accept-language": "en-US",
            "priority": "u=6, i",
            "user-agent": self.user_agent,
            "x-fb-client-ip": "True",
            "x-fb-friendly-name": "undefined:media-upload",
            "x-fb-http-engine": "Tigon/MNS/TCP",
            "x-fb-request-analytics-tags": (
                '{"network_tags":{"product":"567067343352427",'
                '"surface":"undefined","request_category":"media_upload",'
                '"purpose":"none","retry_attempt":"0"}}'
            ),
            "x-fb-rmd": "state=URL_ELIGIBLE",
            "x-fb-server-cluster": "True",
            "x-tigon-is-retry": "False",
            "x-ig-salt-ids": "51052545",
        }
        if rur:
            headers["ig-u-rur"] = rur
        if mid:
            headers["x-mid"] = mid
        if extra_headers:
            headers.update(extra_headers)
        return headers

    def _video_rupload(self, video_bytes: bytes, entity_name: str, waterfall_id: str) -> int:
        """Upload mp4 bytes to ``rupload.facebook.com/messenger_video/...`` and
        return the ``media_id`` used as ``attachment_fbid`` in the broadcast.

        Notes
        -----
        Same constraint as :meth:`_voice_rupload` — ``self.private`` pins ~30
        IG-mobile-only headers (``X-IG-*``, ``X-Bloks-*``, ``X-Pigeon-*``,
        plus ``Host: i.instagram.com``) that FB's rupload edge rejects with a
        generic 404. We use a fresh ``requests.Session`` here with only the
        captured allow-list.
        """
        import requests

        url = f"https://rupload.facebook.com/messenger_video/{entity_name}"

        sess = requests.Session()
        sess.verify = self.tls_verify
        if getattr(self, "proxy", None):
            sess.proxies = {"http": self.proxy, "https": self.proxy}

        headers = self._messenger_rupload_headers(
            {
                "video_type": "FILE_ATTACHMENT",
                "segment-start-offset": "0",
                "segment-type": "3",
                "ephemeral_media_view_mode": "2",
                "ig_raven_metadata": "{}",
                "x_fb_video_waterfall_id": waterfall_id,
            }
        )

        # 1. fetch resumable offset
        r = sess.get(url, headers=headers, timeout=30)
        if r.status_code != 200:
            raise ClientError(f"messenger_video offset GET failed: {r.status_code} {r.text[:300]}")
        try:
            offset = int(r.json().get("offset", 0))
        except Exception:
            offset = 0

        # 2. POST video bytes
        post_headers = dict(headers)
        post_headers.update(
            {
                "content-type": "application/octet-stream",
                "offset": str(offset),
                "x-entity-length": str(len(video_bytes)),
                "x-entity-name": entity_name,
                "x-entity-type": "video/mp4",
            }
        )
        r = sess.post(url, data=video_bytes[offset:], headers=post_headers, timeout=300)
        if r.status_code != 200:
            raise ClientError(f"messenger_video upload POST failed: {r.status_code} {r.text[:300]}")
        try:
            media_id = int(r.json()["media_id"])
        except Exception as exc:
            raise ClientError(f"messenger_video response missing media_id: {r.text[:300]}") from exc
        return media_id

    def direct_send_voice(
        self,
        path: Path,
        user_ids: List[int] = [],
        thread_ids: List[int] = [],
        waveform: Optional[List[float]] = None,
    ) -> DirectMessage:
        """
        Send a voice (audio) DM to a list of users or threads.

        Replicates the IG Android client's three-step protocol:

        1. ``GET https://rupload.facebook.com/messenger_audio/{upload_id}_0_{key}``
           returns the resumable upload offset.
        2. ``POST`` to the same URL with the audio bytes returns
           ``{"media_id": <int>}``.
        3. ``POST direct_v2/threads/broadcast/voice_attachment/`` with that
           ``media_id`` as ``attachment_fbid`` sends the message.

        The audio file MUST be AAC in an MP4 container (``.m4a``); the server
        rejects other formats at upload_finish.

        Parameters
        ----------
        path: Path
            Path to an m4a/AAC voice clip.
        user_ids: List[int]
            List of unique identifiers of Users id.
        thread_ids: List[int]
            List of unique identifiers of Direct Message thread id.
        waveform: Optional[List[float]]
            Optional list of 70 amplitude values in ``[0.0, 1.0]`` for the IG
            voice-bubble UI. The server does not validate amplitudes — it is
            UI-cosmetic only. Defaults to random values that produce a natural
            buzzy bubble (zeros render as flat dots, not bars).

        Returns
        -------
        DirectMessage
            An object of DirectMessage.
        """
        assert self.user_id, "Login required"
        user_ids = _direct_id_list(user_ids)
        thread_ids = _direct_id_list(thread_ids)
        assert (user_ids or thread_ids) and not (user_ids and thread_ids), (
            "Specify user_ids or thread_ids, but not both"
        )
        if user_ids:
            thread_ids = [self._direct_thread_id_from_user_ids(user_ids, "voice")]

        audio_bytes = Path(path).read_bytes()
        upload_id = str(int(time.time() * 1000))
        rand_key = random.randint(-(2**31), 2**31 - 1)

        # Steps 1 + 2: upload to rupload.facebook.com, get media_id.
        media_id = self._voice_rupload(audio_bytes, upload_id, rand_key)

        # Step 3: broadcast voice_attachment with media_id as attachment_fbid.
        if waveform is None:
            waveform = [round(random.uniform(0.2, 0.95), 3) for _ in range(70)]
        token = self.generate_mutation_token()
        data = {
            "action": "send_item",
            "thread_ids": dumps([int(tid) for tid in thread_ids]),
            "send_attribution": "inbox",
            "client_context": token,
            "attachment_fbid": str(media_id),
            "device_id": self.android_device_id,
            "mutation_token": token,
            "_uuid": self.uuid,
            "waveform": dumps(waveform),
            "waveform_sampling_frequency_hz": "10",
            "upload_id": upload_id,
            "offline_threading_id": token,
        }
        result = self.private_request(
            "direct_v2/threads/broadcast/voice_attachment/",
            data=self.with_default_data(data),
            with_signature=False,
        )
        return extract_direct_message(result["payload"])

    def _voice_rupload(self, audio_bytes: bytes, upload_id: str, rand_key: int) -> int:
        """Upload audio to rupload.facebook.com and return the media_id used as
        attachment_fbid in the voice_attachment broadcast.

        Notes
        -----
        The IG mobile app strips most ``X-IG-*`` / ``X-Bloks-*`` / ``X-Pigeon-*``
        headers when calling FB-domain endpoints. ``self.private`` keeps a full
        IG-mobile header set pinned on its session, which leaks into per-call
        requests via session-merging and causes FB rupload to return a generic
        404 ("We're sorry, but something went wrong"). We therefore use a fresh
        ``requests.Session`` here with only the headers FB rupload expects.

        The captured request from the official client also included
        ``x-meta-zca`` (Play Integrity attestation) and ``x-meta-usdid`` (signed
        device id) headers. Empirical testing shows the server accepts the
        upload without them — they appear to be informational/risk-scoring
        rather than strictly validated.
        """
        import requests

        entity = f"{upload_id}_0_{rand_key}"
        url = f"https://rupload.facebook.com/messenger_audio/{entity}"

        sess = requests.Session()
        sess.verify = self.tls_verify
        if getattr(self, "proxy", None):
            sess.proxies = {"http": self.proxy, "https": self.proxy}

        headers = self._messenger_rupload_headers({"audio_type": "FILE_ATTACHMENT"})

        # 1. fetch resumable offset
        r = sess.get(url, headers=headers, timeout=30)
        if r.status_code != 200:
            raise ClientError(f"messenger_audio offset GET failed: {r.status_code} {r.text[:300]}")
        try:
            offset = int(r.json().get("offset", 0))
        except Exception:
            offset = 0

        # 2. POST audio bytes
        post_headers = dict(headers)
        post_headers.update(
            {
                "content-type": "application/octet-stream",
                "offset": str(offset),
                "x-entity-length": str(len(audio_bytes)),
                "x-entity-name": entity,
                "x-entity-type": "audio/mp4",
            }
        )
        r = sess.post(url, data=audio_bytes[offset:], headers=post_headers, timeout=120)
        if r.status_code != 200:
            raise ClientError(f"messenger_audio upload POST failed: {r.status_code} {r.text[:300]}")
        try:
            media_id = int(r.json()["media_id"])
        except Exception as exc:
            raise ClientError(f"messenger_audio response missing media_id: {r.text[:300]}") from exc
        return media_id

    def direct_send_file(
        self,
        path: Path,
        user_ids: List[int] = [],
        thread_ids: List[int] = [],
        content_type: str = "photo",
    ) -> DirectMessage:
        """
        Send a direct file to list of users or threads

        Parameters
        ----------
        path: Path
            Path to file that will be posted on the thread
        user_ids: List[int]
            List of unique identifier of Users id
        thread_ids: List[int]
            List of unique identifier of Direct Message thread id

        Returns
        -------
        DirectMessage
            An object of DirectMessage
        """
        assert self.user_id, "Login required"
        user_ids = _direct_id_list(user_ids)
        thread_ids = _direct_id_list(thread_ids)
        assert (user_ids or thread_ids) and not (user_ids and thread_ids), (
            "Specify user_ids or thread_ids, but not both"
        )
        method = f"configure_{content_type}"
        token = self.generate_mutation_token()
        nav_chains = [
            (
                "6xQ:direct_media_picker_photos_fragment:1,5rG:direct_thread:2,"
                "5ME:direct_quick_camera_fragment:3,5ME:direct_quick_camera_fragment:4,"
                "4ju:reel_composer_preview:5,5rG:direct_thread:6,5rG:direct_thread:7,"
                "6xQ:direct_media_picker_photos_fragment:8,5rG:direct_thread:9"
            ),
            (
                "1qT:feed_timeline:1,7Az:direct_inbox:2,7Az:direct_inbox:3,"
                "5rG:direct_thread:4,6xQ:direct_media_picker_photos_fragment:5,"
                "5rG:direct_thread:6,5rG:direct_thread:7,"
                "6xQ:direct_media_picker_photos_fragment:8,5rG:direct_thread:9"
            ),
        ]
        kwargs = {}
        data = {
            "action": "send_item",
            "is_shh_mode": "0",
            "send_attribution": "direct_thread",
            "client_context": token,
            "mutation_token": token,
            "nav_chain": random.choices(nav_chains),
            "offline_threading_id": token,
        }
        if content_type == "video":
            data["video_result"] = ""
            kwargs["to_direct"] = True
        if content_type == "photo":
            data["send_attribution"] = "inbox"
            data["allow_full_aspect_ratio"] = "true"
        if user_ids:
            data["recipient_users"] = dumps([[int(uid) for uid in user_ids]])
        if thread_ids:
            data["thread_ids"] = dumps([int(tid) for tid in thread_ids])
        path = Path(path)
        upload_id = str(int(time.time() * 1000))
        upload_id, width, height = getattr(self, f"{content_type}_rupload")(path, upload_id, **kwargs)[:3]
        data["upload_id"] = upload_id
        # data['content_type'] = content_type
        result = self.private_request(
            f"direct_v2/threads/broadcast/{method}/",
            data=self.with_default_data(data),
            with_signature=False,
        )
        return extract_direct_message(result["payload"])

    def direct_send_cutout_sticker(
        self,
        sticker_pk: str,
        user_ids: List[int] = None,
        thread_ids: List[int] = None,
    ) -> DirectMessage:
        """
        Send a cutout sticker to list of users or threads

        Parameters
        ----------
        sticker_pk: str
            Unique ID of the Sticker (Cutout) e.g. "123456789"
        user_ids: List[int]
            List of unique identifier of Users id
        thread_ids: List[int]
            List of unique identifier of Direct Message thread id

        Returns
        -------
        DirectMessage
            An object of DirectMessage
        """
        assert self.user_id, "Login required"
        user_ids = _direct_id_list(user_ids)
        thread_ids = _direct_id_list(thread_ids)
        assert (user_ids or thread_ids) and not (user_ids and thread_ids), (
            "Specify user_ids or thread_ids, but not both"
        )

        token = self.generate_mutation_token()

        sticker_id_full = f"cutout_photo_{sticker_pk}"
        json_payload = {"sticker_id": sticker_id_full, "embedded_ent_type": 101}

        data = {
            "action": "send_item",
            "embedded_ent_type": "101",
            "json_params": dumps(json_payload),
            "client_context": token,
            "mutation_token": token,
            "device_id": self.android_device_id,
            "_uuid": self.uuid,
            "offline_threading_id": token,
        }

        if user_ids:
            data["recipient_users"] = dumps([[int(uid) for uid in user_ids]])
        if thread_ids:
            data["thread_ids"] = dumps([int(tid) for tid in thread_ids])

        result = self.private_request(
            "direct_v2/threads/broadcast/generic_share/",
            data=self.with_default_data(data),
            with_signature=False,
        )
        return extract_direct_message(result["payload"])

    def direct_users_presence(self, user_ids: List[int]) -> Dict:
        """
        Get a presence of User

        Parameters
        ----------
        user_ids: List[int]
            List of unique identifier of Users ID

        Returns
        -------
        Dict
            Dict with User's presences
        """
        assert self.user_id, "Login Required"
        user_ids = _direct_id_list(user_ids)
        data = {
            "_uuid": self.uuid,
            "subscriptions_off": "false",
            "request_data": dumps([int(uid) for uid in user_ids]),
        }
        result = self.private_request(
            "direct_v2/fetch_and_subscribe_presence/",
            data=self.with_default_data(data),
            with_signature=False,
        )
        assert result.get("status") == "ok", f"Failed to retrieve presence of user_id={user_ids}"
        return result

    def direct_active_presence(self) -> Dict:
        """
        Getting active presences in Direct

        Returns
        -------
        Dict
            Dict with active presences
        """
        params = {"recent_thread_limit": 0, "suggested_followers_limit": 100}
        result = self.private_request("direct_v2/get_presence_active_now/", params=params)
        assert result.get("status") == "ok", "Failed to retrieve active presences"

        return result.get("user_presence", {})

    def direct_message_seen(self, thread_id: int, message_id: int) -> bool:
        """
        Mark direct message as seen

        Parameters
        ----------
        thread_id: int
            ID of the thread with message
        message_id: int
            ID of the message to mark as seen

        Returns
        -------
        bool
            A boolean value
        """
        token = self.generate_mutation_token()
        data = {
            "thread_id": str(thread_id),
            "action": "mark_seen",
            "client_context": token,
            "_uuid": self.uuid,
            "offline_threading_id": token,
        }
        result = self.private_request(
            f"direct_v2/threads/{thread_id}/items/{message_id}/seen/",
            data=data,
            with_signature=False,
        )
        return result.get("status", "") == "ok"

    def direct_send_seen(self, thread_id: int) -> bool:
        """
        Mark direct thread as seen

        Parameters
        ----------
        thread_id: int
            ID of thread to mark as read

        Returns
        -------
        bool
            A boolean value
        """
        thread = self.direct_thread(thread_id=thread_id)
        return self.direct_message_seen(thread_id, thread.messages[0].id)

    def direct_search(self, query: str, mode: SEARCH_MODE = "universal") -> List[UserShort]:
        """
        Search threads by query

        Parameters
        ----------
        query: str
            Text query, e.g. username
        mode: str, optional
            Mode for searching, by deafult "universal"

        Returns
        -------
        List[UserShort]
            List of short version of Users
        """
        assert mode in SEARCH_MODES, f'Unsupported mode="{mode}" {SEARCH_MODES}'

        params = {
            "max_ai_bot_results": "0",
            "max_ig_bus_results": "10",
            "mode": mode,
            "show_threads": "true",
            "query": str(query),
            "max_ig_results": "10",
            "max_ibc_results": "20",
            "max_fb_results": "0",
        }
        result = self.private_request(
            "direct_v2/ranked_recipients/",
            params=params,
        )
        return [
            extract_user_short(item.get("user", {}))
            for item in result.get("ranked_recipients", [])
            if "user" in item and item.get("user", {}).get("username", "") != ""  # Check to exclude suggestions from FB
        ]

    def direct_message_search(self, query: str) -> List[Tuple[DirectMessage, DirectShortThread]]:
        """
        Search query mentions in direct messages

        Parameters
        ----------
        query: str
            Text query

        Returns
        -------
        List[Tuple[DirectMessage, DirectThread]]
            List of Tuples with DirectMessage (matched query) and its DirectThread
        """
        params = {
            "hide_locked_threads": '{"message_content":"false"}',
            "offsets": '{"message_content":"0","reshared_content":""}',
            "query": query,
            "result_types": '["message_content","reshared_content"]',
        }
        result = self.private_request(
            "direct_v2/search_secondary/",
            params=params,
        )
        assert result.get("status", "") == "ok"
        search_results = result.get("message_search_results", {})

        data = []
        for item in search_results.get("message_search_result_items", []):
            message = item.get("matched_message_info", {})
            thread = item.get("thread", {})
            data.append(
                (
                    extract_direct_message(message.get("item_info", {})),
                    extract_direct_short_thread(thread),
                )
            )
        return data

    def direct_has_interop_upgraded(self) -> bool:
        """
        Check whether the account's Direct inbox has upgraded interop messaging.

        Returns
        -------
        bool
            ``True`` when the account reports upgraded Direct interop state.
        """
        assert self.user_id, "Login required"
        result = self.private_request("direct_v2/has_interop_upgraded/")
        return bool(result.get("has_interop_upgraded"))

    def direct_search_gen_ai_bots(self, amount: int = 20) -> List[UserShort]:
        """
        Search Instagram's generated AI Direct bot suggestions.

        Parameters
        ----------
        amount: int, optional
            Maximum number of AI bot suggestions requested from the API.

        Returns
        -------
        List[UserShort]
            User-like bot entries returned by Direct search.
        """
        assert self.user_id, "Login required"
        result = self.private_request(
            "direct_v2/search_gen_ai_bots/",
            params={"num_ai_bots": str(amount)},
        )
        return [extract_user_short(item) for item in result.get("user_search_results", []) if item.get("username")]

    def direct_channels(self, user_id: Optional[int] = None, thread_subtypes: Optional[List[int]] = None) -> List[Dict]:
        """
        Get all Direct channels for a user.

        Parameters
        ----------
        user_id: int, optional
            Instagram user id. Defaults to the authenticated user.
        thread_subtypes: List[int], optional
            Direct channel thread subtype filters. Defaults to ``[29]`` as used
            by the Android app.

        Returns
        -------
        List[Dict]
            Raw channel entries from ``all_channels_list``.
        """
        assert self.user_id, "Login required"
        params = {
            "user_id": str(user_id or self.user_id),
            "thread_subtypes": dumps(thread_subtypes or [29]),
        }
        result = self.private_request("direct_v2/get_all_channels/", params=params)
        return result.get("all_channels_list", [])

    def direct_thread_by_participants(self, user_ids: List[int]) -> Dict:
        """
        Get direct thread by participants

        Parameters
        ----------
        user_ids: List[int]
            List of unique identifier of Users id

        Returns
        -------
        Dict
            Some information about thread.
            List of UserShort under "users" key
        """
        user_ids = _direct_id_list(user_ids)
        recipient_users = dumps([int(uid) for uid in user_ids])
        result = self.private_request(
            "direct_v2/threads/get_by_participants/",
            params={"recipient_users": recipient_users, "seq_id": 2580572, "limit": 20},
        )
        users = []
        for user in result.get("users", []):
            # User dict object also contains fields like follower_count,
            #     following_count, mutual_followers_count, media_count
            users.append(
                UserShort(
                    pk=user["pk"],
                    username=user["username"],
                    full_name=user["full_name"],
                    profile_pic_url=user["profile_pic_url"],
                    is_private=user["is_private"],
                )
            )
        result["users"] = users
        return result

    def direct_thread_hide(self, thread_id: int, move_to_spam: bool = False) -> bool:
        """
        Hide (delete) a thread
        When you click delete, Instagram hides a thread

        Parameters
        ----------
        thread_id: int
            ID of thread to hide
        move_to_spam: bool, optional
            True - move to the hidden requests (spam) folder, False - just hide (default - False)

        Returns
        -------
        bool
            A boolean value
        """
        assert self.user_id, "Login required"

        result = self.private_request(
            f"direct_v2/threads/{thread_id}/hide/",
            data={
                "should_move_future_requests_to_spam": move_to_spam,
                "_uuid": self.uuid,
            },
            with_signature=False,
        )
        return result.get("status", "") == "ok"

    def direct_thread_update_title(self, thread_id: int, title: str) -> bool:
        """
        Update a direct thread title

        Parameters
        ----------
        thread_id: int
            ID of thread to update
        title: str
            New thread title

        Returns
        -------
        bool
            A boolean value
        """
        assert self.user_id, "Login required"

        result = self.private_request(
            f"direct_v2/threads/{thread_id}/update_title/",
            data={"_uuid": self.uuid, "title": title},
            with_signature=False,
        )
        return result.get("status", "") == "ok"

    def direct_thread_add_users(self, thread_id: int, user_ids: List[int]) -> bool:
        """
        Add users to a group Direct thread.

        Parameters
        ----------
        thread_id: int
            ID of thread to add users to
        user_ids: List[int]
            List of unique identifiers of users to add to the group thread

        Returns
        -------
        bool
            A boolean value
        """
        assert self.user_id, "Login required"
        user_ids = _direct_id_list(user_ids)
        assert user_ids, "At least one user_id required"

        result = self.private_request(
            f"direct_v2/threads/{thread_id}/add_user/",
            data={"_uuid": self.uuid, "user_ids": dumps([str(uid) for uid in user_ids])},
            with_signature=False,
        )
        return result.get("status", "") == "ok"

    def direct_set_e2ee_eligibility(self, e2ee_eligibility: int = 4) -> bool:
        """
        Set Direct end-to-end encryption eligibility state.

        Parameters
        ----------
        e2ee_eligibility: int, optional
            Raw eligibility value accepted by Instagram. The Android 428 app
            sends ``4`` during Direct bootstrap.

        Returns
        -------
        bool
            A boolean value.
        """
        assert self.user_id, "Login required"

        result = self.private_request(
            "direct_v2/set_e2ee_eligibility/",
            data={"_uuid": self.uuid, "e2ee_eligibility": str(e2ee_eligibility)},
            with_signature=False,
        )
        return result.get("status", "") == "ok"

    def direct_thread_create(self, user_ids: List[int], title: str = "") -> str:
        """
        Create a group Direct thread.

        Parameters
        ----------
        user_ids: List[int]
            List of unique identifiers of users to add to the group thread.
            Instagram group threads require at least two recipients besides
            the authenticated user.
        title: str, optional
            Initial group thread title.

        Returns
        -------
        str
            Created Direct thread id.
        """
        assert self.user_id, "Login required"
        user_ids = _direct_id_list(user_ids)
        assert len(user_ids) >= 2, "Group threads require at least two recipient user_ids"

        result = self.private_request(
            "direct_v2/create_group_thread/",
            data={
                "_uuid": self.uuid,
                "_uid": str(self.user_id),
                "client_context": self.generate_mutation_token(),
                "is_partnership_folder": "false",
                "recipient_users": dumps([int(uid) for uid in user_ids]),
                "thread_title": title,
            },
        )
        thread_id = result.get("thread_id") or result.get("thread", {}).get("thread_id")
        if not thread_id:
            raise ClientError("Create group thread response missing thread_id", **result)
        return str(thread_id)

    def direct_media_share(
        self,
        media_id: str,
        user_ids: List[int] = [],
        thread_ids: List[int] = [],
        send_attribute: SEND_ATTRIBUTE_MEDIA = "feed_timeline",
        media_type: str = "photo",
    ) -> DirectMessage:
        """
        Share a media to list of users

        Parameters
        ----------
        media_id: str
            Unique Media ID
        user_ids: List[int]
            List of unique identifier of Users id (recipients)
        thread_ids: List[int]
            List of unique identifier of Direct thread id
        send_attribute: SEND_ATTRIBUTE_MEDIA, optional
            Sending option. Default is "feed_timeline"
        media_type: str, optional
            Type of the shared media. Default is "photo", also can be "video"

        Returns
        -------
        DirectMessage
            An object of DirectMessage
        """
        assert self.user_id, "Login required"
        token = self.generate_mutation_token()
        user_ids = _direct_id_list(user_ids)
        thread_ids = _direct_id_list(thread_ids)
        assert (user_ids or thread_ids) and not (user_ids and thread_ids), (
            "Specify user_ids or thread_ids, but not both"
        )
        media_id = self.media_id(media_id)
        kwargs = {
            "action": "send_item",
            "is_shh_mode": "0",
            "send_attribution": send_attribute,
            "client_context": token,
            "media_id": media_id,
            "device_id": self.android_device_id,
            "mutation_token": token,
            "_uuid": self.uuid,
            "btt_dual_send": "false",
            "nav_chain": (
                "1qT:feed_timeline:1,1qT:feed_timeline:2,1qT:feed_timeline:3,"
                "7Az:direct_inbox:4,7Az:direct_inbox:5,5rG:direct_thread:7"
            ),
            "is_ae_dual_send": "false",
            "offline_threading_id": token,
        }
        if user_ids:
            kwargs["recipient_users"] = dumps([[int(uid) for uid in user_ids]])
        if thread_ids:
            kwargs["thread_ids"] = dumps([int(tid) for tid in thread_ids])
        if send_attribute in ["feed_contextual_chain", "feed_short_url"]:
            kwargs["inventory_source"] = "recommended_explore_grid_cover_model"
        if send_attribute == "feed_timeline":
            kwargs["inventory_source"] = "media_or_ad"

        result = self.private_request(
            "direct_v2/threads/broadcast/media_share/",
            params={"media_type": media_type},
            data=self.with_default_data(kwargs),
            with_signature=False,
        )
        assert result.get("status", "") == "ok"

        return extract_direct_message(result["payload"])

    def direct_story_share(self, story_id: str, user_ids: List[int] = [], thread_ids: List[int] = []) -> DirectMessage:
        """
        Share a story to list of users

        Parameters
        ----------
        story_id: str
            Unique Story ID
        user_ids: List[int]
            List of unique identifier of Users id
        thread_ids: List[int]
            List of unique identifier of Users id

        Returns
        -------
        DirectMessage
            An object of DirectMessage
        """
        assert self.user_id, "Login required"
        user_ids = _direct_id_list(user_ids)
        thread_ids = _direct_id_list(thread_ids)
        assert (user_ids or thread_ids) and not (user_ids and thread_ids), (
            "Specify user_ids or thread_ids, but not both"
        )
        story_id = self.media_id(story_id)
        story_pk = self.media_pk(story_id)
        token = self.generate_mutation_token()
        data = {
            "action": "send_item",
            "is_shh_mode": "0",
            "send_attribution": "reel_feed_timeline",
            "client_context": token,
            "mutation_token": token,
            "nav_chain": (
                "1qT:feed_timeline:1,ReelViewerFragment:reel_feed_timeline:4,"
                "DirectShareSheetFragment:direct_reshare_sheet:5"
            ),
            "reel_id": story_pk,
            "containermodule": "reel_feed_timeline",
            "story_media_id": story_id,
            "offline_threading_id": token,
        }
        if user_ids:
            data["recipient_users"] = dumps([[int(uid) for uid in user_ids]])
        if thread_ids:
            data["thread_ids"] = dumps([int(tid) for tid in thread_ids])
        result = self.private_request(
            "direct_v2/threads/broadcast/story_share/",
            # params={'story_type': 'video'},
            data=self.with_default_data(data),
            with_signature=False,
        )
        return extract_direct_message(result["payload"])

    def direct_thread_mark_unread(self, thread_id: int) -> bool:
        """
        Mark a thread as unread

        Parameters
        ----------
        thread_id: int
            Id of thread

        Returns
        -------
        bool
            A boolean value
        """
        data = self.with_default_data({})
        data.pop("_uid", None)
        data.pop("device_id", None)
        result = self.private_request(f"direct_v2/threads/{thread_id}/mark_unread/", data=data)
        return result["status"] == "ok"

    def direct_message_delete(self, thread_id: int, message_id: int) -> bool:
        """
        Delete a message from thread

        Parameters
        ----------
        thread_id: int
            Id of thread
        message_id: int
            Id of message

        Returns
        -------
        bool
            A boolean value
        """
        data = self.with_default_data({})
        data.pop("_uid", None)
        data.pop("device_id", None)
        result = self.private_request(f"direct_v2/threads/{thread_id}/items/{message_id}/delete/", data=data)
        return result["status"] == "ok"

    def direct_message_unsend(self, thread_id: int, message_id: int) -> bool:
        """
        Unsend a message from a Direct thread.

        Parameters
        ----------
        thread_id: int
            Id of thread
        message_id: int
            Id of message

        Returns
        -------
        bool
            A boolean value
        """
        return self.direct_message_delete(thread_id, message_id)

    def direct_thread_mute(self, thread_id: int, revert: bool = False) -> bool:
        """
        Mute the thread

        Parameters
        ----------
        thread_id: int
            Id of thread
        revert: bool, optional
            If muted, whether or not to unmute. Default is False

        Returns
        -------
        bool
            A boolean value
        """
        name = "unmute" if revert else "mute"
        result = self.private_request(f"direct_v2/threads/{thread_id}/{name}/", data={"_uuid": self.uuid})
        return result["status"] == "ok"

    def direct_thread_unmute(self, thread_id: int) -> bool:
        """
        Unmute the thread

        Parameters
        ----------
        thread_id: int
            Id of thread

        Returns
        -------
        bool
            A boolean value
        """
        return self.direct_thread_mute(thread_id, revert=True)

    def direct_thread_mute_video_call(self, thread_id: int, revert: bool = False) -> bool:
        """
        Mute video call for the thread

        Parameters
        ----------
        thread_id: int
            Id of thread
        revert: bool, optional
            If muted, whether or not to unmute. Default is False

        Returns
        -------
        bool
            A boolean value
        """
        name = "unmute_video_call" if revert else "mute_video_call"
        result = self.private_request(f"direct_v2/threads/{thread_id}/{name}/", data={"_uuid": self.uuid})
        return result["status"] == "ok"

    def direct_thread_unmute_video_call(self, thread_id: int) -> bool:
        """
        Unmute video call for the thread

        Parameters
        ----------
        thread_id: int
            Id of thread

        Returns
        -------
        bool
            A boolean value
        """
        return self.direct_thread_mute_video_call(thread_id, revert=True)

    def direct_profile_share(self, user_id: str, user_ids: List[int] = [], thread_ids: List[int] = []) -> DirectMessage:
        """
        Share a profile to list of users

        Parameters
        ----------
        user_id: str
            Unique User ID (profile)
        user_ids: List[int]
            List of unique identifier of Users id (recipients)
        thread_ids: List[int]
            List of unique identifier of Users id

        Returns
        -------
        DirectMessage
            An object of DirectMessage
        """
        assert self.user_id, "Login required"
        user_ids = _direct_id_list(user_ids)
        thread_ids = _direct_id_list(thread_ids)
        assert (user_ids or thread_ids) and not (user_ids and thread_ids), (
            "Specify user_ids or thread_ids, but not both"
        )
        token = self.generate_mutation_token()
        kwargs = {
            "profile_user_id": user_id,
            "action": "send_item",
            "is_shh_mode": "0",
            "send_attribution": "profile",
            "client_context": token,
            "device_id": self.android_device_id,
            "mutation_token": token,
            "_uuid": self.uuid,
            "btt_dual_send": "false",
            "nav_chain": (
                "1qT:feed_timeline:1,1qT:feed_timeline:2,1qT:feed_timeline:3,"
                "7Az:direct_inbox:4,7Az:direct_inbox:5,5rG:direct_thread:7"
            ),
            "is_ae_dual_send": "false",
            "offline_threading_id": token,
        }
        if user_ids:
            kwargs["recipient_users"] = dumps([[int(uid) for uid in user_ids]])
        if thread_ids:
            kwargs["thread_ids"] = dumps([int(tid) for tid in thread_ids])
        result = self.private_request(
            "direct_v2/threads/broadcast/profile/",
            data=self.with_default_data(kwargs),
            with_signature=False,
        )
        assert result.get("status", "") == "ok"

        return extract_direct_message(result["payload"])

    def direct_media(self, thread_id: int, amount: int = 20) -> List[Media]:
        """
        Get all the media from a thread

        Parameters
        ----------
        thread_id: int
            Unique identifier of a Direct Message thread

        amount: int, optional
            Maximum number of media to return, default is 20

        Returns
        -------
        List[Media]
            A list of objects of Media
        """
        assert self.user_id, "Login required"
        params = {
            **self._direct_request_tracking_params(),
            "limit": 20,
            "media_type": "media_shares",
        }
        max_timestamp = None
        items = []
        while True:
            if max_timestamp:
                params["max_timestamp"] = max_timestamp
            try:
                result = self.private_request(f"direct_v2/threads/{thread_id}/media/", params=params)
            except ClientNotFoundError as e:
                raise DirectThreadNotFound(e, thread_id=thread_id, **self.last_json)
            for item in result["items"]:
                media = item.get("media")
                items.append(extract_direct_media(media))
                max_timestamp = item.get("timestamp")
            more_available = result.get("more_available")
            if not more_available or (amount and len(items) >= amount):
                break
        if amount:
            items = items[:amount]
        return items
