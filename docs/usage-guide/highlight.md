# Highlight

| Method                                                                         | Return           | Description
| ------------------------------------------------------------------------------ | ---------------- | ----------------------------------
| highlight_pk_from_url(url: str)                                                | int              | Get Highlight PK from URL
| highlight_info(highlight_pk: int)                                              | Highlight        | Get Highlight by pk or id
| user_highlights(user_id: int, amount: int = 0)                                 | List[Highlight]  | Get a user's highlights
| highlight_create(title: str, story_ids: List[str], cover_story_id: str = "", crop_rect: List[float] = [0.0, 0.21830457, 1.0, 0.78094524]) | Highlight | Create highlight
| highlight_change_title(highlight_pk: str, title: str)                          | Highlight        | Change title for highlight
| highlight_change_cover(highlight_pk: str, cover_path: Path)                    | Highlight        | Change cover for highlight
| highlight_add_stories(highlight_pk: str, added_media_ids: List[str])           | Highlight        | Add stories to highlight
| highlight_remove_stories(highlight_pk: str, removed_media_ids: List[str])      | Highlight        | Remove stories from highlight
| highlight_delete(highlight_pk: str)                                            | bool             | Delete highlight

Example:

``` python
>>> cl.highlight_info(17895485201104054).dict()
{
    'pk': 17895485201104054,
    'id': 'highlight:17895485201104054',
    'latest_reel_media': 1622366765,
    'cover_media': {
        'cropped_image_version': {'width': 150, 'height': 150, 'url': 'https://instagram.frix7-1.fna.fbcdn.net/v/t51.2885-...'},
        'crop_rect': [0, 0.21855760773966576, 1, 0.7814423922603342],
        'media_id': '2584323966581791455_8641392340'
    },
    'user': {
        'pk': 8641392340,
        'username': 'bestskatetrick',
        'full_name': 'The Best Skate Tricks',
        'profile_pic_url': HttpUrl('https://instagram.frix7-1.fna.fbcdn.net/v/t51.2885-19/s150x150/6526...'),
        'profile_pic_url_hd': None,
        'is_private': False,
        'stories': []
    },
    'title': 'Picnic 2021',
    'created_at': datetime.datetime(2021, 5, 29, 19, 39, 15, tzinfo=datetime.timezone.utc),
    'is_pinned_highlight': False,
    'media_count': 19,
    'media_ids': [2584323966581791455, 2584328925731679183, 2584328595757338887, ...],  # story ids
    'items': [Story, Story, Story, ...]
}

>>> cl.user_highlights(29817608135)
[Highlight(pk='17907771728171896', id='highlight:17907771728171896', latest_reel_media=1638039687, ...), ...]
```

Change highlight:

``` python
>>> cl.highlight_create("Test", ["2722223419628084989_29817608135"])
Highlight(pk='17920472818962144', id='highlight:17920472818962144', latest_reel_media=1638734336, ...)

>>> cl.highlight_change_title(17907771728171896, "Example title")
Highlight(pk='17907771728171896', id='highlight:17907771728171896', latest_reel_media=1638039687, ...)

>>> cl.highlight_change_cover(17907771728171896, "/tmp/test.jpg")  # recommend 720x720
Highlight(pk='17907771728171896', id='highlight:17907771728171896', ...)

>>> cl.highlight_add_stories(17907771728171896, [2722223419628084989])
Highlight(pk='17907771728171896', id='highlight:17907771728171896', latest_reel_media=1638734336, ...)

>>> cl.highlight_remove_stories(17907771728171896, [2722223419628084989])
Highlight(pk='17907771728171896', id='highlight:17907771728171896', latest_reel_media=1638039687, ...)

>>> cl.highlight_delete(17920472818962144)
True
```
