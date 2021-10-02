import random
import re
import time
from pathlib import Path
from typing import List, Optional

from instagrapi.exceptions import ClientNotFoundError, DirectThreadNotFound
from instagrapi.extractors import (
    extract_direct_message,
    extract_direct_response,
    extract_direct_short_thread,
    extract_direct_thread,
)
from instagrapi.types import (
    DirectMessage,
    DirectResponse,
    DirectShortThread,
    DirectThread,
)
from instagrapi.utils import dumps

SELECTED_FILTERS = ("flagged", "unread")

try:
    from typing import Literal
    SELECTED_FILTER = Literal[SELECTED_FILTERS]
except ImportError:
    # python <= 3.8
    SELECTED_FILTER = str


class DirectMixin:
    """
    Helpers for managing Direct Messaging
    """

    def direct_threads(self, amount: int = 20, selected_filter: SELECTED_FILTER = "",
                       thread_message_limit: Optional[int] = None) -> List[DirectThread]:
        """
        Get direct message threads

        Parameters
        ----------
        amount: int, optional
            Maximum number of media to return, default is 20

        Returns
        -------
        List[DirectThread]
            A list of objects of DirectThread
        """
        assert self.user_id, "Login required"
        params = {
            "visual_message_return_type": "unseen",
            "thread_message_limit": "10",
            "persistentBadging": "true",
            "limit": "20",
        }
        if selected_filter:
            assert selected_filter in SELECTED_FILTERS, \
                f'Unsupported selected_filter="{selected_filter}" {SELECTED_FILTERS}'
            params.update({
                "selected_filter": selected_filter,
                "fetch_reason": "manual_refresh",
            })
        if thread_message_limit:
            params.update({
                "thread_message_limit": thread_message_limit
            })
        cursor = None
        threads = []
        self.private_request("direct_v2/get_presence/")
        while True:
            if cursor:
                params["cursor"] = cursor
            result = self.private_request("direct_v2/inbox/", params=params)
            inbox = result.get("inbox", {})
            for thread in inbox.get("threads", []):
                threads.append(extract_direct_thread(thread))
            cursor = inbox.get("oldest_cursor")
            if not cursor or (amount and len(threads) >= amount):
                break
        if amount:
            threads = threads[:amount]
        return threads

    def direct_pending_inbox(self, amount: int = 20) -> List[DirectThread]:
        """
        Get direct message pending threads

        Parameters
        ----------
        amount: int, optional
            Maximum number of media to return, default is 20

        Returns
        -------
        List[DirectThread]
            A list of objects of DirectThread
        """
        assert self.user_id, "Login required"
        params = {
            "visual_message_return_type": "unseen",
            "persistentBadging": "true",
        }
        cursor = None
        threads = []
        # self.private_request("direct_v2/get_presence/")
        while True:
            if cursor:
                params["cursor"] = cursor
            result = self.private_request("direct_v2/pending_inbox/", params=params)
            inbox = result.get("inbox", {})
            for thread in inbox.get("threads", []):
                threads.append(extract_direct_thread(thread))
            cursor = inbox.get("oldest_cursor")
            if not cursor or (amount and len(threads) >= amount):
                break
        if amount:
            threads = threads[:amount]
        return threads

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
                result = self.private_request(
                    f"direct_v2/threads/{thread_id}/", params=params
                )
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

    def direct_send(self, text: str, user_ids: List[int] = [], thread_ids: List[int] = []) -> DirectMessage:
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

        Returns
        -------
        DirectMessage
            An object of DirectMessage
        """
        assert self.user_id, "Login required"
        assert (user_ids or thread_ids) and not (user_ids and thread_ids), "Specify user_ids or thread_ids, but not both"
        method = "text"
        token = self.generate_mutation_token()
        kwargs = {
            "action": "send_item",
            "is_shh_mode": "0",
            "send_attribution": "direct_thread",
            "client_context": token,
            "mutation_token": token,
            "nav_chain": "1qT:feed_timeline:1,1qT:feed_timeline:2,1qT:feed_timeline:3,7Az:direct_inbox:4,7Az:direct_inbox:5,5rG:direct_thread:7",
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
        result = self.private_request(
            f"direct_v2/threads/broadcast/{method}/",
            data=self.with_default_data(kwargs),
            with_signature=False
        )
        return extract_direct_message(result["payload"])

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
        return self.direct_send_file(path, user_ids, thread_ids, content_type='photo')

    def direct_send_video(self, path: Path, user_ids: List[int] = [], thread_ids: List[int] = []) -> DirectMessage:
        """
        Send a direct video to list of users or threads

        Parameters
        ----------
        path: Path
            Path to video that will be posted on the thread
        user_ids: List[int]
            List of unique identifier of Users id
        thread_ids: List[int]
            List of unique identifier of Direct Message thread id

        Returns
        -------
        DirectMessage
            An object of DirectMessage
        """
        return self.direct_send_file(path, user_ids, thread_ids, content_type='video')

    def direct_send_file(self, path: Path, user_ids: List[int] = [], thread_ids: List[int] = [], content_type: str = 'photo') -> DirectMessage:
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
        assert (user_ids or thread_ids) and not (user_ids and thread_ids), "Specify user_ids or thread_ids, but not both"
        method = f"configure_{content_type}"
        token = self.generate_mutation_token()
        nav_chains = [
            "6xQ:direct_media_picker_photos_fragment:1,5rG:direct_thread:2,5ME:direct_quick_camera_fragment:3,5ME:direct_quick_camera_fragment:4,4ju:reel_composer_preview:5,5rG:direct_thread:6,5rG:direct_thread:7,6xQ:direct_media_picker_photos_fragment:8,5rG:direct_thread:9",
            "1qT:feed_timeline:1,7Az:direct_inbox:2,7Az:direct_inbox:3,5rG:direct_thread:4,6xQ:direct_media_picker_photos_fragment:5,5rG:direct_thread:6,5rG:direct_thread:7,6xQ:direct_media_picker_photos_fragment:8,5rG:direct_thread:9",
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
        upload_id, width, height = getattr(self, f'{content_type}_rupload')(path, upload_id, **kwargs)[:3]
        data['upload_id'] = upload_id
        # data['content_type'] = content_type
        result = self.private_request(
            f"direct_v2/threads/broadcast/{method}/",
            data=self.with_default_data(data),
            with_signature=False,
        )
        return extract_direct_message(result["payload"])

    def direct_send_seen(self, thread_id: int) -> DirectResponse:
        """
        Send seen to thread

        Parameters
        ----------
        thread_id: int
            Id of thread which messages will be read

        Returns
        -------
            An object of DirectResponse
        """
        data = {}

        thread = self.direct_thread(thread_id=thread_id)
        result = self.private_request(
            f"direct_v2/threads/{thread_id}/items/{thread.messages[0].id}/seen/",
            data=self.with_default_data(data),
            with_signature=False,
        )
        return extract_direct_response(result)

    def direct_search(self, query: str) -> List[DirectShortThread]:
        """
        Search threads by query

        Parameters
        ----------
        query: String
            Text query, e.g. username

        Returns
        -------
        List[DirectShortThread]
            List of short version of DirectThread
        """
        result = self.private_request(
            "direct_v2/ranked_recipients/",
            params={"mode": "raven", "show_threads": "true", "query": str(query)}
        )
        return [
            extract_direct_short_thread(item.get('thread', {}))
            for item in result.get('ranked_recipients', [])
            if 'thread' in item
        ]

    def direct_thread_by_participants(self, user_ids: List[int]) -> DirectThread:
        """
        Get direct thread by participants

        Parameters
        ----------
        user_ids: List[int]
            List of unique identifier of Users id

        Returns
        -------
        DirectThread
            An object of DirectThread
        """
        recipient_users = dumps([int(uid) for uid in user_ids])
        result = self.private_request(
            "direct_v2/threads/get_by_participants/",
            params={"recipient_users": recipient_users, "seq_id": 2580572, "limit": 20}
        )
        if 'thread' not in result:
            raise DirectThreadNotFound(
                f'Thread not found by recipient_users={recipient_users}',
                user_ids=user_ids,
                **self.last_json
            )
        return extract_direct_thread(result['thread'])

    def direct_thread_hide(self, thread_id: int) -> bool:
        """
        Hide (delete) a thread
        When you click delete, Instagram hides a thread

        Parameters
        ----------
        thread_id: int
            Id of thread which messages will be read

        Returns
        -------
        bool
            A boolean value
        """
        data = self.with_default_data({})
        data.pop('_uid', None)
        data.pop('device_id', None)
        result = self.private_request(
            f"direct_v2/threads/{thread_id}/hide/",
            data=data
        )
        return result["status"] == "ok"

    def direct_media_share(self, media_id: str, user_ids: List[int]) -> DirectMessage:
        """
        Share a media to list of users

        Parameters
        ----------
        media_id: str
            Unique Media ID
        user_ids: List[int]
            List of unique identifier of Users id

        Returns
        -------
        DirectMessage
            An object of DirectMessage
        """
        assert self.user_id, "Login required"
        token = self.generate_mutation_token()
        media_id = self.media_id(media_id)
        recipient_users = dumps([[int(uid) for uid in user_ids]])
        data = {
            'recipient_users': recipient_users,
            'action': 'send_item',
            'is_shh_mode': 0,
            'send_attribution': 'feed_timeline',
            'client_context': token,
            'media_id': media_id,
            'mutation_token': token,
            'nav_chain': '1VL:feed_timeline:1,1VL:feed_timeline:2,1VL:feed_timeline:5,DirectShareSheetFragment:direct_reshare_sheet:6',
            'offline_threading_id': token,
        }
        result = self.private_request(
            "direct_v2/threads/broadcast/media_share/",
            # params={'media_type': 'video'},
            data=self.with_default_data(data),
            with_signature=False,
        )
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
        assert (user_ids or thread_ids) and not (user_ids and thread_ids), "Specify user_ids or thread_ids, but not both"
        story_id = self.media_id(story_id)
        story_pk = self.media_pk(story_id)
        token = self.generate_mutation_token()
        data = {
            "action": "send_item",
            "is_shh_mode": "0",
            "send_attribution": "reel_feed_timeline",
            "client_context": token,
            "mutation_token": token,
            "nav_chain": "1qT:feed_timeline:1,ReelViewerFragment:reel_feed_timeline:4,DirectShareSheetFragment:direct_reshare_sheet:5",
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
        data.pop('_uid', None)
        data.pop('device_id', None)
        result = self.private_request(
            f"direct_v2/threads/{thread_id}/mark_unread/",
            data=data
        )
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
        data.pop('_uid', None)
        data.pop('device_id', None)
        data['is_shh_mode'] = 0
        data['send_attribution'] = 'direct_thread'
        data['original_message_client_context'] = self.generate_mutation_token()
        result = self.private_request(
            f"direct_v2/threads/{thread_id}/items/{message_id}/delete/",
            data=data
        )
        return result["status"] == "ok"

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
        result = self.private_request(
            f"direct_v2/threads/{thread_id}/{name}/",
            data={'_uuid': self.uuid}
        )
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
        result = self.private_request(
            f"direct_v2/threads/{thread_id}/{name}/",
            data={'_uuid': self.uuid}
        )
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
