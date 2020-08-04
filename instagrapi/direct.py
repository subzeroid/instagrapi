from .decorators import check_login


class Direct:

    @check_login
    def direct_threads(self, amount: int = 20) -> list:
        """Return last threads
        """
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

    @check_login
    def direct_thread(self, thread_id: int, cursor: int = 0) -> dict:
        """Return full information by thread
        """
        params = {
            "visual_message_return_type": "unseen",
            "direction": "older",
            "seq_id": "40065",  # 59663
            "limit": "20",
        }
        if cursor:
            params['cursor'] = cursor
        return self.private_request(f"direct_v2/threads/{thread_id}/", params=params)['thread']

    @check_login
    def direct_messages(self, thread_id: int, amount: int = 20) -> list:
        """Fetch list of messages by thread
        """
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
