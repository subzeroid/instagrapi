# Notes 

| Method                                                       | Return           | Description
|--------------------------------------------------------------|------------------| ----------------------------------
| get_all_notes()                                              | NoteResponse     | get all the note that the user can see
| get_note_by_user(note: NoteResponse[], username: str)        | NoteResponse     | get a note by a specified username
| get_note_content_by_user(note: NoteResponse[], username: str | NoteRequest      | get a note content by a specified username
| send_note(note_content: str, audience: int = 0)              | None             | Post a note
| delete_note(note_id: int, audience: int = 0)                 | dict (status ok) | Delete a note

Example:

``` python
>>> cl.get_all_notes()

>>> cl.delete_note(17887679456798301)

>>> cl.send_note("Hello from Instagrapi, everyone can see it !",0)
>>> cl.send_note("Hello from Instagrapi, only close friends can see it !",1)

```

## Get notes  |  Send notes  |  Delete notes
Get your personal notes
Send a note visible to others in the DM page
delete your notes

The note should not exceed 60 characters. The rate in between Notes requests should be fairly high *(*i.e : 1 request/ 2 min)* to avoid triggering Instagram API

Common arguments:

* `note_id` - get it from the note.uuid if the NoteResponse BaseModel is used
* `note_content` - Content of the note 
* `audience` - Who can see the note **(0 = Everyone, 1 = Close Friends only)**
