# Story

| Method                                                          | Return      | Description
| --------------------------------------------------------------- | ----------- | ---------------------------------- |
| user_stories(user_id: int, amount: int = None)                  | List[Story] | Get list of stories by user_id
| story_info(story_pk: int, use_cache: bool = True)               | Story       | Return story info
| story_delete(story_pk: int)                                     | bool        | Delete story
| story_seen(story_pks: List[int], skipped_story_pks: List[int])  | bool        | Mark a story as seen

## Upload Stories

Upload medias to your stories. Common arguments:

* `path` - Path to media file
* `caption` - Caption for story (now use to fetch mentions)
* `thumbnail` - Thumbnail instead capture from source file
* `mentions` - Tag profiles in story
* `locations` - Add locations to story
* `links` - "Swipe Up" links (now use first)
* `hashtags` - Add hashtags to story
* `stickers` - Add stickers to story

| Method                                                                                           | Return   | Description   |
| ------------------------------------------------------------------------------------------------ | -------- | ------------- |
| photo_upload_to_story(path: Path, caption: str, upload_id: str, mentions: List[Usertag], locations: List[StoryLocation], links: List[StoryLink], hashtags: List[StoryHashtag], stickers: List[StorySticker])  | Story  | Upload photo (Support JPG files)
| video_upload_to_story(path: Path, caption: str, thumbnail: Path, mentions: List[Usertag], locations: List[StoryLocation], links: List[StoryLink], hashtags: List[StoryHashtag], stickers: List[StorySticker]) | Story  | Upload video (Support MP4 files)

Examples:

``` python
from instagrapi import Client
from instagrapi.types import Location, StoryMention, StoryLocation, StoryLink, StoryHashtag

cl = Client()
cl.login(USERNAME, PASSWORD)

media_path = cl.video_download(
    cl.media_pk_from_url('https://www.instagram.com/p/CGgDsi7JQdS/')
)
adw0rd = cl.user_info_by_username('adw0rd')
loc = cl.location_complete(Location(name='Test', lat=42.0, lng=42.0))
ht = cl.hashtag_info('dhbastards')

cl.video_upload_to_story(
    media_path,
    "Credits @adw0rd",
    mentions=[StoryMention(user=adw0rd, x=0.49892962, y=0.703125, width=0.8333333333333334, height=0.125)],
    locations=[StoryLocation(location=loc, x=0.33, y=0.22, width=0.4, height=0.7)],
    links=[StoryLink(webUri='https://github.com/adw0rd/instagrapi')],
    hashtags=[StoryHashtag(hashtag=ht, x=0.23, y=0.32, width=0.5, height=0.22)],
)
```

## Build Story to Upload

| Method                                                | Return     | Description                              |
| ----------------------------------------------------- | ---------- | ---------------------------------------- |
| build_clip(clip: moviepy.Clip, max_duration: int = 0) | StoryBuild | Build CompositeVideoClip with background and mentioned users. Return MP4 file and mentions with coordinates |
| video(max_duration: int = 0)  # in seconds            | StoryBuild | Call build_clip(VideoClip, max_duration) |
| photo(max_duration: int = 0)  # in seconds            | StoryBuild | Call build_clip(ImageClip, max_duration) |

Example:

``` python
from instagrapi.story import StoryBuilder

media_path = cl.video_download(
    cl.media_pk_from_url('https://www.instagram.com/p/CGgDsi7JQdS/')
)
adw0rd = cl.user_info_by_username('adw0rd')

buildout = StoryBuilder(
    media_path,
    'Credits @adw0rd',
    [StoryMention(user=adw0rd)],
    Path('/path/to/background_720x1280.jpg')
).video(15)  # seconds

cl.video_upload_to_story(
    buildout.path,
    "Credits @adw0rd",
    mentions=buildout.mentions,
    links=[StoryLink(webUri='https://github.com/adw0rd/instagrapi')]
)
```

Result:

![](https://github.com/adw0rd/instagrapi/blob/master/examples/dhb.gif)

More stories here https://www.instagram.com/surferyone/