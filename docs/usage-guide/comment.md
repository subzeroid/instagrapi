# Comment

| Method                                             | Return             | Description                                                   |
| -------------------------------------------------- | ------------------ | ------------------------------------------------------------- |
| media_comment(media_id: str, message: str)         | bool               | Add new comment to media                                      |
| media_comments(media_id: str)                      | List\[Comment]     | Get all comments for media                                    |
| comment_like(comment_pk: int)                      | bool               | Like comment                                                  |
| comment_unlike(comment_pk: int)                    | bool               | Unlike comment                                                |