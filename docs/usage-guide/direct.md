# Direct

| Method                                                                    | Return                  | Description
| ------------------------------------------------------------------------- | ----------------------- | ----------------------------------
| direct_threads(amount: int = 20)                                          | List[DirectThread]      | Get all Threads
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

Example:

```
>>> cl.direct_thread_mark_unread(340282366841710301949128122292511813703)
True
```
