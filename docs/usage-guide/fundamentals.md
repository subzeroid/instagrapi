# Usage Guide

This section provides detailed descriptions of all the ways `instagrapi` can be used. If you are new to `instagrapi`, the
[Getting Started](getting-started.md) page provides a gradual introduction of the basic functionality with examples.

## Public vs Private Requests

* `Public` (anonymous request via web api) methods have a suffix `_gql` (Instagram `GraphQL`) or `_a1` (example `https://www.instagram.com/adw0rd/?__a=1`)
* `Private` (authorized request via mobile api) methods have `_v1` suffix

The first request to fetch media/user is `public` (anonymous), if instagram raise exception, then use `private` (authorized).

## Detailed Sections

* [Index](index.md)
* [Getting Started](getting-started.md)
* [Interactions](usage-guide/interactions.md)
  * [`Media`](usage-guide/media.md) - Publication (also called post): Photo, Video, Album, IGTV and Reels
  * [`Resource`](usage-guide/media.md) - Part of Media (for albums)
  * [`MediaOembed`](usage-guide/media.md) - Short version of Media
  * [`Account`](usage-guide/account.md) - Full private info for your account (e.g. email, phone_number)
  * [`User`](usage-guide/user.md) - Full public user data
  * [`UserShort`](usage-guide/user.md) - Short public user data (used in Usertag, Comment, Media, Direct Message)
  * [`Usertag`](usage-guide/user.md) - Tag user in Media (coordinates + UserShort)
  * [`Location`](usage-guide/location.md) - GEO location (GEO coordinates, name, address)
  * [`Hashtag`](usage-guide/hashtag.md) - Hashtag object (id, name, picture)
  * [`Collection`](usage-guide/collection.md) - Collection of medias (name, picture and list of medias)
  * [`Comment`](usage-guide/comment.md) - Comments to Media
  * [`Story`](usage-guide/story.md) - Story
  * [`StoryLink`](usage-guide/story.md) - Link (Swipe up)
  * [`StoryLocation`](usage-guide/story.md) - Tag Location in Story (as sticker)
  * [`StoryMention`](usage-guide/story.md) - Mention users in Story (user, coordinates and dimensions)
  * [`StoryHashtag`](usage-guide/story.md) - Hashtag for story (as sticker)
  * [`StorySticker`](usage-guide/story.md) - Tag sticker to story (for example from giphy)
  * [`StoryBuild`](usage-guide/story.md) - [StoryBuilder](https://github.com/adw0rd/instagrapi/blob/master/instagrapi/story.py) return path to photo/video and mention co-ordinates
  * [`DirectThread`](usage-guide/direct.md) - Thread (topic) with messages in Direct Message
  * [`DirectMessage`](usage-guide/direct.md) - Message in Direct Message
  * [`Insight`](usage-guide/insight.md) - Insights for a post
* [Development Guide](development-guide.md)
* [Handle Exceptions](usage-guide/handle_exception.md)
* [Exceptions](exceptions.md)
