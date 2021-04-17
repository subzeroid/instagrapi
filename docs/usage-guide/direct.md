# Direct

| Method                                                                    | Return              | Description
| ------------------------------------------------------------------------- | ------------------- | ----------------------------------
| direct_threads(amount: int = 20)                                          | List[DirectThread]  | Get all Threads
| direct_thread(thread_id: int, amount: int = 20)                           | DirectThread        | Get Thread with Messages
| direct_messages(thread_id: int, amount: int = 20)                         | List[DirectMessage] | Get only Messages in Thread
| direct_answer(thread_id: int, text: str)                                  | DirectMessage       | Add Message to exist Thread
| direct_send(text: str, users: List[int] = [], threads: List[int] = [])    | DirectMessage       | Send Message to Users or Threads
| direct_search(query: str)                                                 | DirectShortThread   | Search threads (for example by username)