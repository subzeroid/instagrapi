# Insights

Get statistics by medias. Common arguments:

* `post_type` - Media type: "ALL", "CAROUSEL_V2", "IMAGE", "SHOPPING", "VIDEO".
* `time_frame` - Time frame for media publishing date: "ONE_WEEK", "ONE_MONTH", "THREE_MONTHS", "SIX_MONTHS", "ONE_YEAR", "TWO_YEARS".
* `data_ordering` - Data ordering in instagram response: "REACH_COUNT", "LIKE_COUNT", "FOLLOW", "SHARE_COUNT", "BIO_LINK_CLICK", "COMMENT_COUNT", "IMPRESSION_COUNT", "PROFILE_VIEW", "VIDEO_VIEW_COUNT", "SAVE_COUNT".

| Method                                                                                             | Return             | Description
| -------------------------------------------------------------------------------------------------- | ------------------ | ------------------------------- 
| insights_media_feed_all(post_type: str = "ALL", time_frame: str = "TWO_YEARS", data_ordering: str = "REACH_COUNT", count: int = 0, sleep: int = 2) | list | Return medias with insights
| insights_account()                                                                                 | dict               | Get statistics by your account
| insights_media(media_pk: int)                                                                      | dict               | Get statistics by your media