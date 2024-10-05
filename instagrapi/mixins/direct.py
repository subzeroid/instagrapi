import random
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from instagrapi.exceptions import ClientNotFoundError, DirectThreadNotFound
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
from instagrapi.utils import dumps

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

try:
    from typing import Literal

    SELECTED_FILTER = Literal[SELECTED_FILTERS]
    SEARCH_MODE = Literal[SEARCH_MODES]
    SEND_ATTRIBUTE = Literal[SEND_ATTRIBUTES]
    SEND_ATTRIBUTE_MEDIA = Literal[SEND_ATTRIBUTES_MEDIA]
    BOX = Literal[BOXES]
except ImportError:
    # python <= 3.8
    SELECTED_FILTER = str
    SEARCH_MODE = str
    SEND_ATTRIBUTE = str
    BOX = str


class DirectMixin:
    """
    Helpers for managing Direct Messaging
    """

    def direct_threads(
        self,
        amount: int = 20,
        selected_filter: SELECTED_FILTER = "",
        box: BOX = "",
        thread_message_limit: Optional[int] = None,
    ) -> List[DirectThread]:
        """
        Get direct message threads

        Parameters
        ----------
        amount: int, optional
            Maximum number of media to return, default is 20
        selected_filter: str, optional
            Filter to apply to threads (flagged or unread)
        box: str, optional
            Box to gather threads from (primary or general) (business accounts only)
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
            threads_chunk, cursor = self.direct_threads_chunk(
                selected_filter, box, thread_message_limit, cursor
            )
            for thread in threads_chunk:
                threads.append(thread)

            if not cursor or (amount and len(threads) >= amount):
                break
        if amount:
            threads = threads[:amount]
        return threads

    def direct_threads_chunk(
        self,
        selected_filter: SELECTED_FILTER = "",
        box: BOX = "",
        thread_message_limit: Optional[int] = None,
        cursor: str = None,
    ) -> Tuple[List[DirectThread], str]:
        """
        Get direct a chunk of threads by cursor value

        Parameters
        ----------
        selected_filter: str, optional
            Filter to apply to threads (flagged or unread)
        thread_message_limit: int, optional
            Thread message limit, deafult is 10
        box: str, optional
            Box to gather threads from (primary or general) (business accounts only)
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
            "thread_message_limit": "10",
            "persistentBadging": "true",
            "limit": "20",
            "is_prefetching": "false",
        }
        if selected_filter:
            assert (
                selected_filter in SELECTED_FILTERS
            ), f'Unsupported selected_filter="{selected_filter}" {SELECTED_FILTERS}'
            params.update({"selected_filter": selected_filter})
        if box:
            assert box in BOXES, f'Unsupported box="{box}" {BOXES}'
            params.update({"folder": "1" if box == "general" else "0"})
        if thread_message_limit:
            params.update({"thread_message_limit": thread_message_limit})
        if cursor:
            params.update(
                {"cursor": cursor, "direction": "older", "fetch_reason": "page_scroll"}
            )

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

    def direct_pending_chunk(
        self, cursor: str = None
    ) -> Tuple[List[DirectThread], str]:
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

        Returns
        -------
        DirectMessage
            An object of DirectMessage
        """
        assert self.user_id, "Login required"
        assert (user_ids or thread_ids) and not (
            user_ids and thread_ids
        ), "Specify user_ids or thread_ids, but not both"
        assert (
            send_attribute in SEND_ATTRIBUTES
        ), f'Unsupported send_attribute="{send_attribute}" {SEND_ATTRIBUTES}'
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

    def direct_send_photo(
        self, path: Path, user_ids: List[int] = [], thread_ids: List[int] = []
    ) -> DirectMessage:
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

    def direct_send_video(
        self, path: Path, user_ids: List[int] = [], thread_ids: List[int] = []
    ) -> DirectMessage:
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
        return self.direct_send_file(path, user_ids, thread_ids, content_type="video")

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
        assert (user_ids or thread_ids) and not (
            user_ids and thread_ids
        ), "Specify user_ids or thread_ids, but not both"
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
        upload_id, width, height = getattr(self, f"{content_type}_rupload")(
            path, upload_id, **kwargs
        )[:3]
        data["upload_id"] = upload_id
        # data['content_type'] = content_type
        result = self.private_request(
            f"direct_v2/threads/broadcast/{method}/",
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
        assert (
            result.get("status") == "ok"
        ), f"Failed to retrieve presence of user_id={user_ids}"
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
        result = self.private_request(
            "direct_v2/get_presence_active_now/", params=params
        )
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

    def direct_search(
        self, query: str, mode: SEARCH_MODE = "universal"
    ) -> List[UserShort]:
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
            "max_ig_bus_results": "10",
            "mode": mode,
            "show_threads": "true",
            "query": str(query),
            "max_ig_results": "10",
            "max_fb_results": "0",
        }
        result = self.private_request(
            "direct_v2/ranked_recipients/",
            params=params,
        )
        return [
            extract_user_short(item.get("user", {}))
            for item in result.get("ranked_recipients", [])
            if "user" in item
            and item.get("user", {}).get("username", "")
            != ""  # Check to exclude suggestions from FB
        ]

    def direct_message_search(
        self, query: str
    ) -> List[Tuple[DirectMessage, DirectShortThread]]:
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

    def direct_media_share(
        self,
        media_id: str,
        user_ids: List[int],
        send_attribute: SEND_ATTRIBUTES_MEDIA = "feed_timeline",
        media_type: str = "photo",
    ) -> DirectMessage:
        """
        Share a media to list of users

        Parameters
        ----------
        media_id: str
            Unique Media ID
        user_ids: List[int]
            List of unique identifier of Users id
        send_attribute: str, optional
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
        media_id = self.media_id(media_id)
        recipient_users = dumps([[int(uid) for uid in user_ids]])
        kwargs = {
            "recipient_users": recipient_users,
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

    def direct_story_share(
        self, story_id: str, user_ids: List[int] = [], thread_ids: List[int] = []
    ) -> DirectMessage:
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
        assert (user_ids or thread_ids) and not (
            user_ids and thread_ids
        ), "Specify user_ids or thread_ids, but not both"
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
        result = self.private_request(
            f"direct_v2/threads/{thread_id}/mark_unread/", data=data
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
        data.pop("_uid", None)
        data.pop("device_id", None)
        result = self.private_request(
            f"direct_v2/threads/{thread_id}/items/{message_id}/delete/", data=data
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
            f"direct_v2/threads/{thread_id}/{name}/", data={"_uuid": self.uuid}
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

    def direct_thread_mute_video_call(
        self, thread_id: int, revert: bool = False
    ) -> bool:
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
            f"direct_v2/threads/{thread_id}/{name}/", data={"_uuid": self.uuid}
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

    def direct_profile_share(
        self, user_id: str, user_ids: List[int] = [], thread_ids: List[int] = []
    ) -> DirectMessage:
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
        assert (user_ids or thread_ids) and not (
            user_ids and thread_ids
        ), "Specify user_ids or thread_ids, but not both"
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
        params = {"limit": 20, "media_type": "photos_and_videos"}
        max_timestamp = None
        items = []
        while True:
            if max_timestamp:
                params["max_timestamp"] = max_timestamp
            try:
                result = self.private_request(
                    f"direct_v2/threads/{thread_id}/media/", params=params
                )
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
