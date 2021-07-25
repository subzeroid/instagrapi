# Direct

| Method                                                                    | Return                  | Description
| ------------------------------------------------------------------------- | ----------------------- | ----------------------------------
| direct_threads(amount: int = 20)                                          | List[DirectThread]      | Get all threads from inbox
| direct_pending_inbox(amount: int = 20)                                    | List[DirectThread]      | Get all threads from pending inbox
| direct_thread(thread_id: int, amount: int = 20)                           | DirectThread            | Get Thread with Messages
| direct_messages(thread_id: int, amount: int = 20)                         | List[DirectMessage]     | Get only Messages in Thread
| direct_answer(thread_id: int, text: str)                                  | DirectMessage           | Add Message to exist Thread
| direct_send(text: str, users: List[int] = [], threads: List[int] = [])    | DirectMessage           | Send Message to Users or Threads
| direct_search(query: str)                                                 | List[DirectShortThread] | Search threads (for example by username)
| direct_thread_by_participants(user_ids: List[int])                        | DirectThread            | Get thread by user_id
| direct_thread_hide(thread_id: int)                                        | bool                    | Delete (called "hide")
| direct_media_share(media_id: str, user_ids: List[int])                    | DirectMessage           | Share a media to list of users
| direct_thread_mark_unread(thread_id: int)                                 | bool                    | Mark a thread as unread
| direct_message_delete(thread_id: int, message_id: int)                    | bool                    | Delete a message from thread
| direct_thread_mute(thread_id: int, revert: bool = False)                  | bool                    | Mute the thread
| direct_thread_unmute(thread_id: int)                                      | bool                    | Unmute the thread
| direct_thread_mute_video_call(thread_id: int, revert: bool = False)       | bool                    | Mute video call for the thread
| direct_thread_unmute_video_call(thread_id: int)                           | bool                    | Unmute video call for the thread
| video_upload_to_direct(path: Path, caption: str, thumbnail: Path, mentions: List[StoryMention], thread_ids: List[int] = [], extra_data: Dict[str, str] = {}) | DirectMessage | Upload video to direct thread as a story and configure it

Example:

```
>>> from instagrapi import Client
>>> cl = Client()
>>> cl.login(USERNAME, PASSWORD)

>>> cl.direct_thread_mark_unread(340282366841710301949128122292511813703)
True

>>> cl.direct_thread_mute(340282366841710301949128122292511813703)
True

>>> cl.direct_thread_mute_video_call(340282366841710301949128122292511813703)
True

>>> cl.direct_thread_unmute_video_call(340282366841710301949128122292511813703)
True

>>> cl.direct_thread_unmute(340282366841710301949128122292511813703)
True
```
