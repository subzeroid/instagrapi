# Notes *WIP*

| Method                                                                 | Return          | Description
| ---------------------------------------------------------------------- | --------------- | ----------------------------------
| send_note(note_content: str, audience: int = 0)                         | None     | Post a note

Example:

``` python
>>> cl.send_note("Hello from Instagrapi, everyone can see it !",0)


>>> s = cl.send_note("Hello from Instagrapi, only close friends can see it !",1)
```

## Send a Note

Send a note visible to others in the DM page

The note should not exceed 60 characters. The rate in between Notes requests should be fairly high *(*i.e : 1 request/ 2 min)* to avoid triggering Instagram API

Common arguments:

* `note_content` - Content of the note 
* `audience` - Who can see the note **(0 = Everyone, 1 = Close Friends only)**

## To-do next 

* Delete note from profile.
* Get note from another User

More about Notes  here [https://about.instagram.com/blog/announcements/updates-to-instagram-messenger-and-stories//](https://www.instagram.com/wrclive/)
