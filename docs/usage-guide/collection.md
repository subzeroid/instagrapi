# Collections

Saved posts, collections, and liked media.

| Method | Return | Description |
| --- | --- | --- |
| collections() | List\[Collection] | Get all collections for the authenticated account |
| collection_pk_by_name(name: str) | int | Resolve collection ID by collection name |
| collection_medias_by_name(name: str) | List\[Media] | Get medias in a collection by collection name |
| collection_medias(collection_pk: str, amount: int = 21, last_media_pk: int = 0) | List\[Media] | Get medias in a collection; use `amount=0` to keep paginating |
| collection_medias_v1_chunk(collection_pk: str, max_id: str = "") | Tuple[List\[Media], str] | Low-level chunk fetch with raw `next_max_id` cursor |
| liked_medias(amount: int = 21, last_media_pk: int = 0) | List\[Media] | Get media liked by the current account |
| media_save(media_id: str, collection_pk: int = None) | bool | Save media, optionally into a specific collection |
| media_unsave(media_id: str, collection_pk: int = None) | bool | Remove media from saved posts or from a specific collection |

Example:

```python
from instagrapi import Client

cl = Client()
cl.login(USERNAME, PASSWORD)

collections = cl.collections()
print([(item.id, item.name) for item in collections])

liked = cl.liked_medias(amount=10)
saved = cl.collection_medias("liked", amount=10)

travel_pk = cl.collection_pk_by_name("Travel")
travel_medias = cl.collection_medias(travel_pk, amount=0)

media_id = cl.media_id(cl.media_pk_from_url("https://www.instagram.com/p/CP5h-I1FuPr/"))
cl.media_save(media_id, collection_pk=travel_pk)
cl.media_unsave(media_id, collection_pk=travel_pk)
```

Notes:

* `collection_pk` can be a numeric collection ID, `"liked"`, or a saved-posts style collection path handled by `collection_medias_v1_chunk()`.
* `liked_medias()` is a convenience wrapper over `collection_medias("liked", ...)`.
* `last_media_pk` in `collection_medias()` is a resume point based on already seen media, not the raw server cursor.
