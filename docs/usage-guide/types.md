# Types

`instagrapi.types` contains the public Pydantic models returned by high-level client methods and accepted by upload/story helpers.

Import models directly when you need structured input objects:

```python
from instagrapi.types import Location, Media, StoryMention, UserShort, Usertag
```

## How To Read Fields

Required fields have no default value. `Optional[...]` fields may be absent from Instagram responses or returned as `null`. Fields with raw `dict` or `list` types intentionally preserve Instagram data whose shape is not stable enough for a dedicated public model yet.

## Common Models

| Model | Common source | Notes |
| --- | --- | --- |
| `Account` | `account_info()` | Private account profile for the authenticated user, including email/phone fields when Instagram returns them. |
| `User` | `user_info(...)`, `user_info_by_username(...)` | Full public profile fields such as counts, biography, public contacts, business category, location, and messaging ids. |
| `UserShort` | user lists, tags, comments, direct threads | Compact user profile used inside many other models. Preserves newer v2 fields such as `fbid_v2`, `profile_pic_id`, `account_badges`, and `friendship_status`. |
| `Media` | `media_info(...)`, feeds, timelines, hashtag media | Main post/Reel/album object. Includes caption/count flags, resources, usertags, coauthors, DASH info, music attribution, and inline comment previews when returned. |
| `Resource` | `Media.resources` | Album child media with thumbnail/video URLs and nested usertags. |
| `Comment` | comment helpers | Public comment model with author, text, like state/count, and reply target. |
| `DirectThread` | direct thread helpers | Direct conversation shell with participants, messages, mute/pin/group state, and activity metadata. |
| `DirectMessage` | direct message helpers | Individual direct item with text, media shares, visual media, links, reactions, replies, and seen state. |
| `Story` | story/reel helpers | Story media object with stickers, mentions, hashtags, links, locations, sponsor tags, and video metadata. |
| `Location` | location helpers and upload metadata | Place metadata used by media and story publishing flows. |
| `Hashtag` | hashtag helpers | Hashtag identity, media count, and profile picture. |
| `Track` | music/Reels helpers | Music track metadata and audio URLs when available. |
| `Note` | notes helpers | Direct Notes payload with author, audience, timestamps, and style flags. |

## Account And User Models

::: instagrapi.types.Account

::: instagrapi.types.User

::: instagrapi.types.UserShort

::: instagrapi.types.RelationshipShort

::: instagrapi.types.Relationship

::: instagrapi.types.Viewer

::: instagrapi.types.Usertag

::: instagrapi.types.About

::: instagrapi.types.BioLink

::: instagrapi.types.Broadcast

::: instagrapi.types.AddressBookPhone

::: instagrapi.types.AddressBookEmail

::: instagrapi.types.AddressBookContact

## Media Models

::: instagrapi.types.Media

::: instagrapi.types.Resource

::: instagrapi.types.MediaOembed

::: instagrapi.types.MediaXma

::: instagrapi.types.MediaDimensions

::: instagrapi.types.MediaDashInfo

::: instagrapi.types.MediaInlineComment

::: instagrapi.types.MediaCommentsPreview

::: instagrapi.types.SharedMediaImageCandidate

::: instagrapi.types.SharedMediaImageVersions

::: instagrapi.types.AdditionalCandidates

::: instagrapi.types.ScrubberSpritesheetInfo

::: instagrapi.types.ScrubberSpritesheetInfoCandidates

::: instagrapi.types.Collection

::: instagrapi.types.Comment

::: instagrapi.types.Location

::: instagrapi.types.Hashtag

::: instagrapi.types.Guide

::: instagrapi.types.Highlight

::: instagrapi.types.Share

## Reels And Music Models

::: instagrapi.types.ClipsMetadata

::: instagrapi.types.ClipsAchievementsInfo

::: instagrapi.types.AudioReattributionInfo

::: instagrapi.types.ClipsAdditionalAudioInfo

::: instagrapi.types.ClipsAudioRankingInfo

::: instagrapi.types.ClipsBrandedContentTagInfo

::: instagrapi.types.ClipsContentAppreciationInfo

::: instagrapi.types.ClipsMashupInfo

::: instagrapi.types.ClipsConsumptionInfo

::: instagrapi.types.ClipsFbDownstreamUseXpostMetadata

::: instagrapi.types.ClipsIgArtist

::: instagrapi.types.ClipsOriginalSoundInfo

::: instagrapi.types.ClipsReusableTextColor

::: instagrapi.types.ClipsReusableTextInfo

::: instagrapi.types.ClipsMusicAttributionInfo

::: instagrapi.types.Track

## Story Models

::: instagrapi.types.Story

::: instagrapi.types.StoryMention

::: instagrapi.types.StoryMedia

::: instagrapi.types.StoryHashtag

::: instagrapi.types.StoryLocation

::: instagrapi.types.StoryStickerLink

::: instagrapi.types.StorySticker

::: instagrapi.types.StoryPoll

::: instagrapi.types.StoryBuild

::: instagrapi.types.StoryLink

::: instagrapi.types.StoryArchiveDay

## Direct Models

::: instagrapi.types.DirectThread

::: instagrapi.types.DirectShortThread

::: instagrapi.types.DirectMessage

::: instagrapi.types.DirectResponse

::: instagrapi.types.DirectMedia

::: instagrapi.types.ReplyMessage

::: instagrapi.types.MessageReaction

::: instagrapi.types.MessageReactions

::: instagrapi.types.MessageLink

::: instagrapi.types.LinkContext

::: instagrapi.types.LastSeenInfo

::: instagrapi.types.DisappearingMessagesSeenState

::: instagrapi.types.FallbackUrl

::: instagrapi.types.DirectMessageImageCandidate

::: instagrapi.types.DirectMessageImageVersions

::: instagrapi.types.VideoVersion

::: instagrapi.types.FriendshipStatus

::: instagrapi.types.VisualMedia

::: instagrapi.types.VisualMediaContent

::: instagrapi.types.VisualMediaUser

::: instagrapi.types.ExpiringMediaActionSummary

## Notes

::: instagrapi.types.Note
