from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, FilePath, HttpUrl, ValidationError, validator


def validate_external_url(cls, v):
    if v is None or (v.startswith('http') and '://' in v) or isinstance(v, str):
        return v
    raise ValidationError('external_url must been URL or string')


class Resource(BaseModel):
    pk: int
    video_url: Optional[HttpUrl]  # for Video and IGTV
    thumbnail_url: HttpUrl
    media_type: int


class User(BaseModel):
    pk: int
    username: str
    full_name: str
    is_private: bool
    profile_pic_url: HttpUrl
    profile_pic_url_hd: Optional[HttpUrl]
    is_verified: bool
    media_count: int
    follower_count: int
    following_count: int
    biography: Optional[str] = ""
    external_url: Optional[str]
    is_business: bool

    public_email: Optional[str]
    contact_phone_number: Optional[str]
    business_contact_method: Optional[str]
    business_category_name: Optional[str]
    category_name: Optional[str]

    _external_url = validator('external_url', allow_reuse=True)(validate_external_url)


class Account(BaseModel):
    pk: int
    username: str
    full_name: str
    is_private: bool
    profile_pic_url: HttpUrl
    is_verified: bool
    biography: Optional[str] = ""
    external_url: Optional[str]
    is_business: bool
    birthday: Optional[str]
    phone_number: Optional[str]
    gender: Optional[int]
    email: Optional[str]

    _external_url = validator('external_url', allow_reuse=True)(validate_external_url)


class UserShort(BaseModel):
    pk: int
    username: Optional[str]
    full_name: Optional[str] = ""
    profile_pic_url: Optional[HttpUrl]
    profile_pic_url_hd: Optional[HttpUrl]
    is_private: Optional[bool]
    # is_verified: bool  # not found in hashtag_medias_v1
    stories: List = []


class Usertag(BaseModel):
    user: UserShort
    x: float
    y: float


class Location(BaseModel):
    pk: Optional[int]
    name: str
    phone: Optional[str] = ""
    website: Optional[str] = ""
    category: Optional[str] = ""
    hours: Optional[dict] = {}  # opening hours
    address: Optional[str] = ""
    city: Optional[str] = ""
    zip: Optional[str] = ""
    lng: Optional[float]
    lat: Optional[float]
    external_id: Optional[int]
    external_id_source: Optional[str]
    # address_json: Optional[dict] = {}
    # profile_pic_url: Optional[HttpUrl]
    # directory: Optional[dict] = {}


class Media(BaseModel):
    pk: int
    id: str
    code: str
    taken_at: datetime
    media_type: int
    product_type: Optional[str] = ""  # igtv or feed
    thumbnail_url: Optional[HttpUrl]
    location: Optional[Location] = None
    user: UserShort
    comment_count: Optional[int] = 0
    like_count: int
    has_liked: Optional[bool]
    caption_text: str
    usertags: List[Usertag]
    video_url: Optional[HttpUrl]  # for Video and IGTV
    view_count: Optional[int] = 0  # for Video and IGTV
    video_duration: Optional[float] = 0.0  # for Video and IGTV
    title: Optional[str] = ""
    resources: List[Resource] = []


class MediaOembed(BaseModel):
    title: str
    author_name: str
    author_url: str
    author_id: int
    media_id: str
    provider_name: str
    provider_url: HttpUrl
    type: str
    width: Optional[int] = None
    height: Optional[int] = None
    html: str
    thumbnail_url: HttpUrl
    thumbnail_width: int
    thumbnail_height: int
    can_view: bool


class Collection(BaseModel):
    id: str
    name: str
    type: str
    media_count: int


class Comment(BaseModel):
    pk: int
    text: str
    user: UserShort
    created_at_utc: datetime
    content_type: str
    status: str
    has_liked: Optional[bool]
    like_count: Optional[int]


class Hashtag(BaseModel):
    id: int
    name: str
    media_count: Optional[int]
    profile_pic_url: Optional[HttpUrl]


class StoryMention(BaseModel):
    user: UserShort
    x: Optional[float]
    y: Optional[float]
    width: Optional[float]
    height: Optional[float]


class StoryMedia(BaseModel):
    # Instagram does not return the feed_media object when requesting story,
    # so you will have to make an additional request to get media and this is overhead:
    # media: Media
    x: float = 0.5
    y: float = 0.4997396
    z: float = 0
    width: float = 0.8
    height: float = 0.60572916
    rotation: float = 0.0
    is_pinned: Optional[bool]
    is_hidden: Optional[bool]
    is_sticker: Optional[bool]
    is_fb_sticker: Optional[bool]
    media_pk: int
    user_id: Optional[int]
    product_type: Optional[str]
    media_code: Optional[str]


class StoryHashtag(BaseModel):
    hashtag: Hashtag
    x: Optional[float]
    y: Optional[float]
    width: Optional[float]
    height: Optional[float]


class StoryLocation(BaseModel):
    location: Location
    x: Optional[float]
    y: Optional[float]
    width: Optional[float]
    height: Optional[float]


class StorySticker(BaseModel):
    id: str
    type: Optional[str] = 'gif'
    x: float
    y: float
    z: Optional[int] = 1000005
    width: float
    height: float
    rotation: Optional[float] = 0.0


class StoryBuild(BaseModel):
    mentions: List[StoryMention]
    path: FilePath
    paths: List[FilePath] = []


class StoryLink(BaseModel):
    webUri: HttpUrl


class Story(BaseModel):
    pk: int
    id: str
    code: str
    taken_at: datetime
    media_type: int
    product_type: Optional[str] = ""
    thumbnail_url: Optional[HttpUrl]
    user: UserShort
    video_url: Optional[HttpUrl]  # for Video and IGTV
    video_duration: Optional[float] = 0.0  # for Video and IGTV
    mentions: List[StoryMention]
    links: List[StoryLink]
    hashtags: List[StoryHashtag]
    locations: List[StoryLocation]
    stickers: List[StorySticker]
    medias: List[StoryMedia] = []


class DirectMedia(BaseModel):
    id: str
    media_type: int
    user: Optional[UserShort]
    thumbnail_url: Optional[HttpUrl]
    video_url: Optional[HttpUrl]


class DirectMessage(BaseModel):
    id: int  # e.g. 28597946203914980615241927545176064
    user_id: Optional[int]
    thread_id: Optional[int]
    timestamp: datetime
    item_type: Optional[str]
    is_shh_mode: Optional[bool]
    reactions: Optional[dict]
    text: Optional[str]
    link: Optional[dict]
    media: Optional[DirectMedia]
    media_share: Optional[Media]
    reel_share: Optional[dict]
    story_share: Optional[dict]
    felix_share: Optional[dict]
    clip: Optional[Media]
    placeholder: Optional[dict]


class DirectResponse(BaseModel):
    unseen_count: Optional[int]
    unseen_count_ts: Optional[int]
    status: Optional[str]


class DirectShortThread(BaseModel):
    id: int
    users: List[UserShort]
    named: bool
    thread_title: str
    pending: bool
    thread_type: str
    viewer_id: int
    is_group: bool


class DirectThread(BaseModel):
    pk: int  # thread_v2_id, e.g. 17898572618026348
    id: int  # thread_id, e.g. 340282366841510300949128268610842297468
    messages: List[DirectMessage]
    users: List[UserShort]
    inviter: Optional[UserShort]
    left_users: List[UserShort] = []
    admin_user_ids: list
    last_activity_at: datetime
    muted: bool
    is_pin: Optional[bool]
    named: bool
    canonical: bool
    pending: bool
    archived: bool
    thread_type: str
    thread_title: str
    folder: int
    vc_muted: bool
    is_group: bool
    mentions_muted: bool
    approval_required_for_new_members: bool
    input_mode: int
    business_thread_folder: int
    read_state: int
    is_close_friend_thread: bool
    assigned_admin_id: int
    shh_mode_enabled: bool
    last_seen_at: dict

    def is_seen(self, user_id: int):
        """Have I seen this thread?
        :param user_id: You account user_id
        """
        user_id = str(user_id)
        own_timestamp = int(self.last_seen_at[user_id]["timestamp"])
        timestamps = [
            (int(v["timestamp"]) - own_timestamp) > 0
            for k, v in self.last_seen_at.items()
            if k != user_id
        ]
        return not any(timestamps)


class Relationship(BaseModel):
    blocking: bool
    followed_by: bool
    following: bool
    incoming_request: bool
    is_bestie: bool
    is_blocking_reel: bool
    is_muting_reel: bool
    is_private: bool
    is_restricted: bool
    muting: bool
    outgoing_request: bool
    status: str


class Highlight(BaseModel):
    pk: int  # 17895485401104052
    id: str  # highlight:17895485401104052
    latest_reel_media: int
    cover_media: dict
    user: UserShort
    title: str
    created_at: datetime
    is_pinned_highlight: bool
    media_count: int
    media_ids: List[int]
    items: List[Story]
