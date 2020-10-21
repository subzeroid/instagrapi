import re

from .utils import dumps


class Direct:

    def direct_threads(self, amount: int = 20) -> list:
        """Return last threads
        """
        assert self.user_id, "Login required"
        cursor = None
        threads = []
        self.private_request("direct_v2/get_presence/")
        while True:
            params = {
                "visual_message_return_type": "unseen",
                "thread_message_limit": "10",
                "persistentBadging": "true",
                "limit": "20",
            }
            if cursor:
                params['cursor'] = cursor
            result = self.private_request("direct_v2/inbox/", params=params)
            inbox = result.get("inbox", {})
            for thread in inbox.get("threads", []):
                threads.append(thread)
            cursor = inbox.get("oldest_cursor")
            if not cursor or (amount and len(threads) >= amount):
                break
        if amount:
            threads = threads[:amount]
        return threads

    def direct_thread(self, thread_id: int, cursor: int = 0) -> dict:
        """Return full information by thread
        """
        assert self.user_id, "Login required"
        params = {
            "visual_message_return_type": "unseen",
            "direction": "older",
            "seq_id": "40065",  # 59663
            "limit": "20",
        }
        if cursor:
            params['cursor'] = cursor
        return self.private_request(f"direct_v2/threads/{thread_id}/", params=params)['thread']

    def direct_messages(self, thread_id: int, amount: int = 20) -> list:
        """Fetch list of messages by thread
        """
        assert self.user_id, "Login required"
        cursor = None
        messages = []
        while True:
            thread = self.direct_thread(thread_id, cursor)
            for message in thread.get("items", []):
                messages.append(message)
            cursor = thread.get("oldest_cursor")
            if not cursor or (amount and len(messages) >= amount):
                break
        if amount:
            messages = messages[:amount]
        return messages

    def direct_answer(self, thread_id: int, message: str) -> dict:
        """Send message
        """
        assert self.user_id, "Login required"
        return self.direct_send(message, [], [int(thread_id)])

    def direct_send(self, message: str, users: list = [], threads: list = []) -> dict:
        """Send message
        """
        assert self.user_id, "Login required"
        method = "text"
        kwargs = {}
        if 'http' in message:
            method = "link"
            kwargs["link_text"] = message
            kwargs["link_urls"] = dumps(
                re.findall(r"(https?://[^\s]+)", message))
        else:
            kwargs["text"] = message
        if threads:
            kwargs["thread_ids"] = dumps([int(tid) for tid in threads])
        if users:
            kwargs["recipient_users"] = dumps([[int(uid) for uid in users]])
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
        return result["payload"]
