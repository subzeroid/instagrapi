# Notes *WIP*

| Method                      | Return            | Description                     |
| --------------------------- | ----------------- | ------------------------------- |
| get_notes()                 | List[Note]        | Retrieve direct Notes           |
| create_note(text: str, audience: int = 0) | Note | Post a new Note                 |
| delete_note(note_id: int)   | bool              | Delete a posted Note            |
| update_last_seen_note()     | bool              | Update the last seen time |

Example:

``` python
>>> note = cl.create_note("Hello from Instagrapi, everyone can see it!", 0)
>>> print(note.dict())
{'id': '17849203563031468', 
'text': 'Hello from Instagrapi, everyone can see it!', 
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

>>> cl.last_seen_update_note()

>>> cl.delete_note(note.id)
```

## Get Notes  |  Post Notes  |  Delete Notes
- *Get Notes from Direct*
- *Publish a new note with the ability to select an audience*
- *Delete posted Notes*
- *Update last seen of Notes*

The note should not exceed 60 characters. The rate in between Notes requests should be fairly high *(*i.e : 1 request/ 2 min)* to avoid triggering Instagram API

Common arguments:

* `note_id` - ID of the Note object
* `text` - Content of the Note 
* `audience` - Who can see the note **(0 = Followers you follow back, 1 = Close Friends only)**
