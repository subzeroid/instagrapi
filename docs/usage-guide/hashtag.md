# Hashtag

| Method                                                               | Return              | Description                             |
| -------------------------------------------------------------------- | ------------------- | --------------------------------------- |
| hashtag_info(name: str)                                              | Hashtag             | Return Hashtag info (id, name, picture) |
| hashtag_related_hashtags(name: str)                                  | List[Hashtag]       | Return list of related Hashtags         |
| hashtag_medias_top(name: str, amount: int = 9)                       | List[Media]         | Return Top posts by Hashtag             |
| hashtag_medias_recent(name: str, amount: int = 27)                   | List[Media]         | Return Most recent posts by Hashtag     |