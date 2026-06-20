# Notes

| Method                      | Return            | Description                     |
| --------------------------- | ----------------- | ------------------------------- |
| get_notes()                 | List[Note]        | Retrieve direct Notes           |
| get_note_by_user(notes: List[Note], username: str) | Optional[Note] | Find a Note by username |
| get_note_text_by_user(notes: List[Note], username: str) | Optional[str] | Get note text by username |
| create_note(text: str, audience: NoteAudience = NoteAudience.MUTUAL_FOLLOWERS) | Note | Post a new Note                 |
| notes_music_browser()      | Dict              | Retrieve music candidates for Notes |
| create_music_note(track: Track \| Dict, text: str = "", audience: NoteAudience = NoteAudience.MUTUAL_FOLLOWERS, start_time: Optional[int] = None, duration: int = 30000, browse_session_id: Optional[str] = None, alacorn_session_id: Optional[str] = None) | Note | Post a new Note with music |
| delete_note(note_id: int)   | bool              | Delete a posted Note            |
| last_seen_update_note()     | bool              | Update the last seen time |

Example:

``` python
>>> from instagrapi.mixins.note import NoteAudience
>>> note = cl.create_note("Hello from Instagrapi!", audience=NoteAudience.MUTUAL_FOLLOWERS)
>>> print(note.dict())
{'id': '17849203563031468',
'text': 'Hello from Instagrapi!',
'user_id': 12312312312,
'user': {
  'pk': '12312312312',
  'username': 'something',
  'full_name': 'merimi on top',
  'profile_pic_url': HttpUrl('https://scontent-dus1-1.cdninstagram.com/v/t51.2885-19/364347953_6289474204435297_7603222331512295081_n.jpg?stp=dst-jpg_s150x150&_nc_ht=scontent-dus1-1.cdninstagram.com&_nc_cat=101&_nc_ohc=DVaE0MQwn0YAX8-S8dm&edm=AE-H4JwBAAAA&ccb=7-5&oh=00_AfAnH4mHGMl7B5tqzU7b9PMz9qSC4QE_-EX067lwPHnN1w&oe=64DDA1CB&_nc_sid=cff473', ),
  'profile_pic_url_hd': None,
  'is_private': False,
  'stories': []},
'audience': 0,
'created_at': datetime.datetime(2023, 8, 13, 14, 33, 43, tzinfo=datetime.timezone.utc),
'expires_at': datetime.datetime(2023, 8, 14, 14, 33, 43, tzinfo=datetime.timezone.utc),
'is_emoji_only': False,
'has_translation': False,
'note_style': 0}
>>> notes = cl.get_notes()
>>> print(notes)
[Note(id='17849203563031468', text='Hello from Instagrapi, everyone can see it!', ..., has_translation=False, note_style=0), Note(id='17902958207826742', text='Am so happy 💃💃💃💃🙈🤭', ..., has_translation=False, note_style=0)]

>>> cl.get_note_by_user(notes, "something")
Note(id='17849203563031468', text='Hello from Instagrapi, everyone can see it!', ...)

>>> cl.get_note_text_by_user(notes, "something")
'Hello from Instagrapi, everyone can see it!'

>>> cl.last_seen_update_note()

>>> cl.delete_note(note.id)
```

Music Notes use the same audience values as text Notes. A typical flow is to
fetch candidates from `notes_music_browser()`, choose a track from the response,
and pass it to `create_music_note()`:

```python
music = cl.notes_music_browser()
track = music["items"][0]["playlist"]["preview_items"][0]["track"]

note = cl.create_music_note(
    track=track,
    text="",
    audience=NoteAudience.CLOSE_FRIENDS,
    alacorn_session_id=music.get("alacorn_session_id"),
)
cl.delete_note(note.id)
```

## Get Notes  |  Post Notes  |  Delete Notes
- *Get Notes from Direct*
- *Publish a new note with the ability to select an audience*
- *Publish a new note with music*
- *Delete posted Notes*
- *Update last seen of Notes*

The note should not exceed 60 characters. The rate in between Notes requests should be fairly high *(*i.e : 1 request/ 2 min)* to avoid triggering Instagram API

Common arguments:

* `note_id` - ID of the Note object
* `text` - Content of the Note
* `audience` - Who can see the note. Use `NoteAudience.MUTUAL_FOLLOWERS` for followers you follow back or `NoteAudience.CLOSE_FRIENDS` for Close Friends only. Instagram still receives the numeric wire value internally.
* `username` - Username used to search in an existing `notes` list
* `track` - Track object or raw track dict from `notes_music_browser()`

Typical flow:

```python
notes = cl.get_notes()
note = cl.get_note_by_user(notes, "instagram")
if note:
    print(note.text)
```
