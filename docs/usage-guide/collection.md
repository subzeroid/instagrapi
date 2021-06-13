# Collections

| Method                                                                          | Return             | Description                                      |
| ------------------------------------------------------------------------------- | ------------------ | ------------------------------------------------ |
| collections()                                                                   | List\[Collection]  | Get all account collections
| collection_pk_by_name(name: str)                                                | int                | Get collection_pk by name
| collection_medias_by_name(name: str)                                            | List\[Media]       | Get medias in collection by name
| collection_medias(collection_pk: int, amount: int = 21, last_media_pk: int = 0) | List\[Media]       | Get medias in collection by collection_id; Use **amount=0** to return all medias in collection; Use **last_media_pk** to return medias by cursor
| liked_medias(amount: int = 21, last_media_pk: int = 0)                          | List\[Media]       | Get media you have liked
| media_save(media_id: str, collection_pk: int = None)                            | bool               | Save media to collection
| media_unsave(media_id: str, collection_pk: int = None)                          | bool               | Unsave media from collection
