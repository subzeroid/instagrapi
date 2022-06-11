# Usage Guide

This section provides detailed descriptions of all the ways `instagrapi` can be used. If you are new to `instagrapi`, the
[Getting Started](../getting-started.md) page provides a gradual introduction of the basic functionality with examples.

## Public vs Private Requests

* `Public` (anonymous request via web api) methods have a suffix `_gql` (Instagram `GraphQL`) or `_a1` (example `https://www.instagram.com/adw0rd/?__a=1`)
* `Private` (authorized request via mobile api) methods have `_v1` suffix

The first request to fetch media/user is `public` (anonymous), if instagram raise exception, then use `private` (authorized).

## Detailed Sections

* [Index](../index.md)
* [Getting Started](../getting-started.md)
* [Interactions](interactions.md)
  * [`Media`](media.md) - Publication (also called post): Photo, Video, Album, IGTV and Reels
  * [`Resource`](media.md) - Part of Media (for albums)
  * [`MediaOembed`](media.md) - Short version of Media
  * [`Account`](account.md) - Full private info for your account (e.g. email, phone_number)
  * [`User`](user.md) - Full public user data
  * [`UserShort`](user.md) - Short public user data (used in Usertag, Comment, Media, Direct Message)
  * [`Usertag`](user.md) - Tag user in Media (coordinates + UserShort)
  * [`Location`](location.md) - GEO location (GEO coordinates, name, address)
  * [`Hashtag`](hashtag.md) - Hashtag object (id, name, picture)
  * [`Collection`](collection.md) - Collection of medias (name, picture and list of medias)
  * [`Comment`](comment.md) - Comments to Media
  * [`Highlight`](highlight.md) - Highlights
  * [`Story`](story.md) - Story
  * [`StoryLink`](story.md) - Link (Swipe up)
  * [`StoryLocation`](story.md) - Tag Location in Story (as sticker)
  * [`StoryMention`](story.md) - Mention users in Story (user, coordinates and dimensions)
  * [`StoryHashtag`](story.md) - Hashtag for story (as sticker)
  * [`StorySticker`](story.md) - Tag sticker to story (for example from giphy)
  * [`StoryBuild`](story.md) - [StoryBuilder](https://github.com/adw0rd/instagrapi/blob/master/instagrapi/story.py) return path to photo/video and mention co-ordinates
  * [`DirectThread`](direct.md) - Thread (topic) with messages in Direct Message
  * [`DirectMessage`](direct.md) - Message in Direct Message
  * [`Insight`](insight.md) - Insights for a post
* [Development Guide](../development-guide.md)
* [Handle Exceptions](handle_exception.md)
* [Exceptions](../exceptions.md)
