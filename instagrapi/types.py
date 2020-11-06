from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, HttpUrl, FilePath


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
    is_verified: bool
    media_count: int
    follower_count: int
    following_count: int
    biography: Optional[str] = ''
    external_url: Optional[HttpUrl]
    is_business: bool


class UserShort(BaseModel):
    pk: int
    username: str
    full_name: Optional[str] = ''
    profile_pic_url: Optional[HttpUrl]
    # is_private: bool
    # is_verified: bool


class Usertag(BaseModel):
    user: UserShort
    x: float
    y: float


class Location(BaseModel):
    pk: Optional[int]
    name: str
    address: Optional[str] = ''
    lng: float
    lat: float
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
    product_type: Optional[str] = ''  # only for IGTV
    thumbnail_url: Optional[HttpUrl]
    location: Optional[Location] = None
    user: UserShort
    comment_count: int
    like_count: int
    caption_text: str
    usertags: List[Usertag]
    video_url: Optional[HttpUrl]  # for Video and IGTV
    view_count: Optional[int] = 0  # for Video and IGTV
    video_duration: Optional[float] = 0.0  # for Video and IGTV
    title: Optional[str] = ''
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


class StoryMention(BaseModel):
    user: UserShort
    x: Optional[float]
    y: Optional[float]
    width: Optional[float]
    height: Optional[float]


class StoryBuild(BaseModel):
    mentions: List[StoryMention]
    path: FilePath


class StoryLink(BaseModel):
    webUri: HttpUrl


class DirectMessage(BaseModel):
    id: int  # e.g. 28597946203914980615241927545176064
    user_id: Optional[int]
    thread_id: Optional[int]
    timestamp: datetime
    item_type: Optional[str]
    is_shh_mode: Optional[bool]
    reactions: Optional[dict]
    text: Optional[str]
    media_share: Optional[Media]
    reel_share: Optional[dict]
    story_share: Optional[dict]
    felix_share: Optional[dict]
    placeholder: Optional[dict]


class DirectThread(BaseModel):
    pk: int  # thread_v2_id, e.g. 17898572618026348
    id: int  # thread_id, e.g. 340282366841510300949128268610842297468
    messages: List[DirectMessage]
    users: List[UserShort]
    inviter: UserShort
    left_users: List[UserShort]
    admin_user_ids: list
    last_activity_at: datetime
    muted: bool
    is_pin: bool
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
