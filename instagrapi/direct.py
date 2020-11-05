import re
from typing import List

from .utils import dumps
from .types import DirectThread, DirectMessage
from .exceptions import ClientNotFoundError, DirectThreadNotFound
from .extractors import extract_direct_thread, extract_direct_message


class Direct:

    def direct_threads(self, amount: int = 20) -> List[DirectThread]:
        """Return last threads
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
                params['cursor'] = cursor
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
        """Return full information by thread
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
                params['cursor'] = cursor
            try:
                result = self.private_request(f"direct_v2/threads/{thread_id}/", params=params)
            except ClientNotFoundError as e:
                raise DirectThreadNotFound(e, thread_id=thread_id, **self.last_json)
            thread = result['thread']
            for item in thread['items']:
                items.append(item)
            cursor = thread.get("oldest_cursor")
            if not cursor or (amount and len(items) >= amount):
                break
        if amount:
            items = items[:amount]
        thread['items'] = items
        return extract_direct_thread(thread)

    def direct_messages(self, thread_id: int, amount: int = 20) -> List[DirectMessage]:
        """Fetch list of messages by thread (helper)
        """
        assert self.user_id, "Login required"
        return self.direct_thread(thread_id, amount).messages

    def direct_answer(self, thread_id: int, text: str) -> DirectMessage:
        """Send message
        """
        assert self.user_id, "Login required"
        return self.direct_send(text, [], [int(thread_id)])

    def direct_send(self, text: str, user_ids: List[int] = [], thread_ids: List[int] = []) -> DirectMessage:
        """Send message
        """
        assert self.user_id, "Login required"
        method = "text"
        kwargs = {}
        if 'http' in text:
            method = "link"
            kwargs["link_text"] = text
            kwargs["link_urls"] = dumps(
                re.findall(r"(https?://[^\s]+)", text))
        else:
            kwargs["text"] = text
        if thread_ids:
            kwargs["thread_ids"] = dumps([int(tid) for tid in thread_ids])
        if user_ids:
            kwargs["recipient_users"] = dumps([[int(uid) for uid in user_ids]])
        data = {
            "client_context": self.generate_uuid(),
            "action": "send_item",
            **kwargs
        }
        result = self.private_request(
            "direct_v2/threads/broadcast/%s/" % method,
            data=self.with_default_data(data),
            with_signature=False
        )
        return extract_direct_message(result["payload"])
