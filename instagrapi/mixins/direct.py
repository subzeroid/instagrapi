import random
import re
import time
from pathlib import Path
from typing import List

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


class DirectMixin:
    """
    Helpers for managing Direct Messaging
    """

    def direct_threads(self, amount: int = 20) -> List[DirectThread]:
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

    def direct_send(
            self, text: str, user_ids: List[int] = [], thread_ids: List[int] = []
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

        Returns
        -------
        DirectMessage
            An object of DirectMessage
        """
        assert self.user_id, "Login required"
        method = "text"
        kwargs = {}
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
        data = {"client_context": self.generate_uuid(), "action": "send_item", **kwargs}
        result = self.private_request(
            f"direct_v2/threads/broadcast/{method}/",
            data=self.with_default_data(data),
            with_signature=False,
        )
        return extract_direct_message(result["payload"])

    def direct_send_photo(
            self, filepath: str, user_ids: List[int] = [], thread_ids: List[int] = []
    ) -> DirectMessage:
        """
        Send a direct photo to list of users or threads

        Parameters
        ----------
        filepath: str
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
        assert self.user_id, "Login required"
        method = "configure_photo"
        kwargs = {}
        if user_ids:
            kwargs["recipient_users"] = dumps([[int(uid) for uid in user_ids]])
        if thread_ids:
            kwargs["thread_ids"] = dumps([int(tid) for tid in thread_ids])

        path = Path(filepath)

        upload_id = str(int(time.time() * 1000))
        upload_id, width, height = self.photo_rupload(path, upload_id)

        kwargs['upload_id'] = upload_id
        kwargs['content_type'] = 'photo'

        data = {"client_context": self.generate_uuid(), "action": "send_item", **kwargs}

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
        media_id = self.media_id(media_id)
        recipient_users = dumps([[int(uid) for uid in user_ids]])
        token = random.randint(6800011111111111111, 6800099999999999999)
        data = {
            'recipient_users': recipient_users,
            'action': 'send_item',
            'is_shh_mode': 0,
            'send_attribution': 'feed_timeline',
            'client_context': token,
            'media_id': media_id,
            'mutation_token': token,
            'nav_chain': '1VL:feed_timeline:1,1VL:feed_timeline:2,1VL:feed_timeline:5,DirectShareSheetFragment:direct_reshare_sheet:6',
            'offline_threading_id': token
        }
        result = self.private_request(
            "direct_v2/threads/broadcast/media_share/",
            # params={'media_type': 'video'},
            data=self.with_default_data(data),
            with_signature=False,
        )
        return extract_direct_message(result["payload"])
