# Direct

| Method                                                                    | Return                  | Description
| ------------------------------------------------------------------------- | ----------------------- | ----------------------------------
| `direct_threads(amount: int = 20, selected_filter: str = "", thread_message_limit: Optional[int] = None)` <br> Note: selected_filter = "", "flagged" or "unread" | List[DirectThread] | Get all threads from inbox
| direct_pending_inbox(amount: int = 20)                                    | List[DirectThread]      | Get all threads from pending inbox
| direct_thread(thread_id: int, amount: int = 20)                           | DirectThread            | Get Thread with Messages
| direct_messages(thread_id: int, amount: int = 20)                         | List[DirectMessage]     | Get only Messages in Thread
| direct_answer(thread_id: int, text: str)                                  | DirectMessage           | Add Message to exist Thread
| direct_send(text: str, user_ids: List[int] = [], thread_ids: List[int] = []) | DirectMessage        | Send Message to Users or Threads
| direct_search(query: str)                                                 | List[DirectShortThread] | Search threads (for example by username)
| direct_thread_by_participants(user_ids: List[int])                        | DirectThread            | Get thread by user_id
| direct_thread_hide(thread_id: int)                                        | bool                    | Delete (called "hide")
| direct_media_share(media_id: str, user_ids: List[int])                    | DirectMessage           | Share a media to list of users
| direct_story_share(story_id: str, user_ids: List[int], thread_ids: List[int]) | DirectMessage       | Share a story to list of users
| direct_thread_mark_unread(thread_id: int)                                 | bool                    | Mark a thread as unread
| direct_message_delete(thread_id: int, message_id: int)                    | bool                    | Delete a message from thread
| direct_thread_mute(thread_id: int, revert: bool = False)                  | bool                    | Mute the thread
| direct_thread_unmute(thread_id: int)                                      | bool                    | Unmute the thread
| direct_thread_mute_video_call(thread_id: int, revert: bool = False)       | bool                    | Mute video call for the thread
| direct_thread_unmute_video_call(thread_id: int)                           | bool                    | Unmute video call for the thread
| direct_send_photo(path: Path, user_ids: List[int], thread_ids: List[int]) | DirectMessage           | Send a direct photo to list of users or threads
| direct_send_video(path: Path, user_ids: List[int], thread_ids: List[int]) | DirectMessage           | Send a direct video to list of users or threads
| video_upload_to_direct(path: Path, caption: str, thumbnail: Path, mentions: List[StoryMention], thread_ids: List[int] = [], extra_data: Dict[str, str] = {}) | DirectMessage | Upload video to direct thread as a story and configure it

Example of basic actions:

``` python
>>> from instagrapi import Client
>>> cl = Client()
>>> cl.login(USERNAME, PASSWORD)

>>> thread = cl.direct_threads(1)[0]
>>> thread.pk
18123276039123479

>>> thread.users
[UserShort(pk=123123123, username='something', full_name='Dima Something', profile_pic_url=HttpUrl('https://instagram.frix7-1.fna.fbcdn.net/v/t51.2885-19/s150x150/11374323_1630877790512376_1081658215_a.jpg?_nc_ht=instagram.frix7-1.fna.fbcdn.net&_nc_ohc=k22oMvVv8xEAX-UEVRB&edm=AI8ESKwBAAAA&ccb=7-4&oh=be799948b28f19d85158153d886d16d3&oe=6135D80F&_nc_sid=195af5', scheme='https', host='instagram.frix7-1.fna.fbcdn.net', tld='net', host_type='domain', path='/v/t51.2885-19/s150x150/11374323_1630877790512376_1081658215_a.jpg', query='_nc_ht=instagram.frix7-1.fna.fbcdn.net&_nc_ohc=k22oMvVv8xEAX-UEVRB&edm=AI8ESKwBAAAA&ccb=7-4&oh=be799948b28f19d85158153d886d16d3&oe=6135D80F&_nc_sid=195af5'), profile_pic_url_hd=None, is_private=False, stories=[])]

>>> thread.messages[0]
DirectMessage(id=300761992574947211231231241955932160, user_id=123123123, thread_id=None, timestamp=datetime.datetime(2021, 8, 31, 18, 20, 28, 754135, tzinfo=datetime.timezone.utc), item_type='text', is_shh_mode=False, reactions=None, text='Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua', media=None, media_share=None, reel_share=None, story_share=None, felix_share=None, clip=None, placeholder=None)

>>> cl.direct_pending_inbox(1)[0]
DirectThread(
    pk=17881231232408606,
    id=3402823668123123123949128156938656669726,
    messages=[
        DirectMessage(
            id=30073094913010429825449992959033344,
            user_id=123123123123,
            ...
        )
    ],
    ...
)

>>> cl.direct_thread(thread.id, 1)
DirectThread(
    pk=18103276039108479,
    id=340282366841710300949128373114263369599,
    messages=[
        DirectMessage(
            id=30076199257494728485375741955932160,
            user_id=7789547,
            ...
        )
    ],
    ...
)

>>> message = cl.direct_messages(thread.id, 1)[0]
DirectMessage(id=300712312341231237412312312360, user_id=12312312, thread_id=None, timestamp=datetime.datetime(2021, 8, 31, 18, 20, 28, 754135, tzinfo=datetime.timezone.utc), item_type='text', is_shh_mode=False, reactions=None, text='Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua', media=None, media_share=None, reel_share=None, story_share=None, felix_share=None, clip=None, placeholder=None)

>>> cl.direct_answer(thread.id, 'Hello!')
DirectMessage(id=30076213210116812312341061613568, user_id=None, thread_id=34028236684171031231231231233331238762, timestamp=datetime.datetime(2021, 8, 31, 18, 33, 5, 127298, tzinfo=datetime.timezone.utc), item_type=None, is_shh_mode=None, reactions=None, text=None, media=None, media_share=None, reel_share=None, story_share=None, felix_share=None, clip=None, placeholder=None)

>>> cl.direct_send('How are you?', user_ids=[cl.user_id])  # send youself
DirectMessage(id=30076213210116812312341061613568, user_id=None, thread_id=34028236684171031231231231233331238762, timestamp=datetime.datetime(2021, 8, 31, 18, 33, 5, 127298, tzinfo=datetime.timezone.utc), item_type=None, is_shh_mode=None, reactions=None, text=None, media=None, media_share=None, reel_share=None, story_share=None, felix_share=None, clip=None, placeholder=None)

>>> cl.direct_send('How are you?', thread_ids=[thread.id])
DirectMessage(id=30076213210116812312341061613568, user_id=None, thread_id=34028236684171031231231231233331238762, timestamp=datetime.datetime(2021, 8, 31, 18, 33, 5, 127298, tzinfo=datetime.timezone.utc), item_type=None, is_shh_mode=None, reactions=None, text=None, media=None, media_share=None, reel_share=None, story_share=None, felix_share=None, clip=None, placeholder=None)

>>> cl.direct_thread_by_participants([cl.user_id])
DirectThread(pk=178612312342, id=340282366812312312312341298762, messages=[DirectMessage(id=30076214123123123123123864, user_id=1903424587, thread_id=None, timestamp=datetime.datetime(2021, 8, 31, 18, 33, 49, 107154, ...)

>>> cl.direct_media_share(media.pk, user_ids=[cl.user_id])
DirectMessage(id=3007629312312312312312300374016, user_id=None, thread_id=340282366812313212334410641298762, timestamp=datetime.datetime(2021, 8, 31, 19, 45, 20, 708276, tzinfo=datetime.timezone.utc), item_type=None, is_shh_mode=None, reactions=None, text=None, media=None, media_share=None, reel_share=None, story_share=None, felix_share=None, clip=None, placeholder=None)

>>> cl.direct_story_share(media.pk, user_ids=[cl.user_id])
DirectMessage(id=30076291231321231369939116032, user_id=None, thread_id=340282312312312334410641298762, timestamp=datetime.datetime(2021, 8, 31, 19, 48, 12, 217677, tzinfo=datetime.timezone.utc), item_type=None, is_shh_mode=None, reactions=None, text=None, media=None, media_share=None, reel_share=None, story_share=None, felix_share=None, clip=None, placeholder=None)

>>> cl.direct_story_share(media.pk, thread_ids=[thread.id])
DirectMessage(id=30076291231231230352896, user_id=None, thread_id=3402812312312310641298762, timestamp=datetime.datetime(2021, 8, 31, 19, 48, 38, 482706, tzinfo=datetime.timezone.utc), item_type=None, is_shh_mode=None, reactions=None, text=None, media=None, media_share=None, reel_share=None, story_share=None, felix_share=None, clip=None, placeholder=None)

>>> cl.direct_message_delete(thread.id, message.pk)
True

>>> photo_path = cl.photo_download(cl.media_pk_from_url('https://www.instagram.com/p/BgqFyjqloOr/'))
>>> cl.direct_send_photo(photo_path, user_ids=[cl.user_id])  # or
>>> cl.direct_send_photo(photo_path, thread_ids=[thread.id])
DirectMessage(id=300775273512312312312321568, user_id=None, thread_id=34028236123123123123128762, timestamp=datetime.datetime(2021, 9, 1, 14, 20, 24, 949673, tzinfo=datetime.timezone.utc), item_type=None, is_shh_mode=None, reactions=None, text=None, media=None, media_share=None, reel_share=None, story_share=None, felix_share=None, clip=None, placeholder=None)

>>> video_path = cl.video_download(cl.media_pk_from_url('https://www.instagram.com/p/B3rFQPblq40/'))
>>> cl.direct_send_video(video_path, user_ids=[cl.user_id])  # or
>>> cl.direct_send_video(video_path, thread_ids=[thread.id])
Analizing video file "/.../adw0rd_2155839952940084788.mp4"
DirectMessage(id=300775489123123123123664, user_id=None, thread_id=34012312312312312398762, timestamp=datetime.datetime(2021, 9, 1, 14, 39, 56, 959454, tzinfo=datetime.timezone.utc), item_type=None, is_shh_mode=None, reactions=None, text=None, media=None, media_share=None, reel_share=None, story_share=None, felix_share=None, clip=None, placeholder=None)

>>> cl.video_upload_to_direct(video_path, thread_ids=[thread.id])
Analizing video file "/.../adw0rd_2155839952940084788.mp4"
Generating thumbnail "/.../adw0rd_2155839952940084788.mp4.jpg"...
DirectMessage(id=3007123123123123664, user_id=None, thread_id=3401212312312312398762, timestamp=datetime.datetime(2021, 9, 1, 14, 39, 56, 959454, tzinfo=datetime.timezone.utc), item_type=None, is_shh_mode=None, reactions=None, text=None, media=None, media_share=None, reel_share=None, story_share=None, felix_share=None, clip=None, placeholder=None)

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
