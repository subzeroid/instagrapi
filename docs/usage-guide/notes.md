# Notes *WIP*

| Method                                                                  | Return          | Description
| ----------------------------------------------------------------------- | --------------- | ----------------------------------
| get_my_notes()                                                          | dict     | get your current notes
| send_note(note_content: str, audience: int = 0)                         | None     | Post a note
| delete_note(note_id: int, audience: int = 0)                         | dict (status ok)     | Delete a note

Example:

``` python
>>> cl.get_my_notes()

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

* `note_id` - get it from the get_my_notes() 
* `note_content` - Content of the note 
* `audience` - Who can see the note **(0 = Everyone, 1 = Close Friends only)**
