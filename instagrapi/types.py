from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, HttpUrl, FilePath


class Resource(BaseModel):
    pk: int
    video_url: Optional[HttpUrl] = ''  # for Video and IGTV
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
    external_url: Optional[HttpUrl] = ''
    is_business: bool


class UserShort(BaseModel):
    pk: int
    username: str
    full_name: Optional[str] = ''
    profile_pic_url: Optional[HttpUrl] = ''
    # is_private: bool
    # is_verified: bool


class Usertag(BaseModel):
    user: UserShort
    x: float
    y: float


class Location(BaseModel):
    pk: int
    name: str
    address: Optional[str] = ''
    lng: Optional[float] = None
    lat: Optional[float] = None


class Media(BaseModel):
    pk: int
    id: str
    code: str
    taken_at: datetime
    media_type: int
    product_type: Optional[str] = ''  # only for IGTV
    thumbnail_url: Optional[HttpUrl] = ''
    location: Optional[Location] = None
    user: UserShort
    comment_count: int
    like_count: int
    caption_text: str
    usertags: List[Usertag]
    video_url: Optional[HttpUrl] = ''  # for Video and IGTV
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
    x: float
    y: float
    width: float
    height: float


class StoryBuild(BaseModel):
    mentions: List[StoryMention]
    path: FilePath
