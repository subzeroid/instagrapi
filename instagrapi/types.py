from datetime import datetime
from typing import List, Optional, Union

from pydantic import (
    BaseModel,
    ConfigDict,
    FilePath,
    HttpUrl,
    ValidationError,
    field_validator,
)

class TypesBaseModel(BaseModel):
    model_config = ConfigDict(
        coerce_numbers_to_str=True
    )  # (jarrodnorwell) fixed city_id issue

def validate_external_url(cls, v):
    if v is None or (v.startswith("http") and "://" in v) or isinstance(v, str):
        return v
    raise ValidationError("external_url must be a URL or string")  # Corrected 'been' to 'be'

class Resource(TypesBaseModel):
    pk: str
    video_url: Optional[HttpUrl] = None  # for Video and IGTV
    thumbnail_url: HttpUrl
    media_type: int

class BioLink(TypesBaseModel):
    link_id: str
    url: str
    lynx_url: Optional[str] = None
    link_type: Optional[str] = None
    title: Optional[str] = None
    is_pinned: Optional[bool] = None
    open_external_url_with_in_app_browser: Optional[bool] = None

class Broadcast(TypesBaseModel):
    title: str
    thread_igid: str
    subtitle: str
    invite_link: str
    is_member: bool
    group_image_uri: str
    group_image_background_uri: str
    thread_subtype: int
    number_of_members: int
    creator_igid: Optional[str] = None  # Changed from str | None to Optional[str]
    creator_username: str

class User(TypesBaseModel):
    pk: str
    username: str
    full_name: str
    is_private: bool
    profile_pic_url: HttpUrl
    profile_pic_url_hd: Optional[HttpUrl] = None
    is_verified: bool
    media_count: int
    follower_count: int
    following_count: int
    biography: Optional[str] = ""
    bio_links: List[BioLink] = []
    external_url: Optional[str] = None
    account_type: Optional[int] = None
    is_business: bool

    broadcast_channel: List[Broadcast] = []

    public_email: Optional[str] = None
    contact_phone_number: Optional[str] = None
    public_phone_country_code: Optional[str] = None
    public_phone_number: Optional[str] = None
    business_contact_method: Optional[str] = None
    business_category_name: Optional[str] = None
    category_name: Optional[str] = None
    category: Optional[str] = None

    address_street: Optional[str] = None
    city_id: Optional[str] = None
    city_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    zip: Optional[str] = None
    instagram_location_id: Optional[str] = None
    interop_messaging_user_fbid: Optional[str] = None

    _external_url = field_validator("external_url")(validate_external_url)  # Updated to use field_validator

class Account(TypesBaseModel):
    pk: str
    username: str
    full_name: str
    is_private: bool
    profile_pic_url: HttpUrl
    is_verified: bool
    biography: Optional[str] = ""
    external_url: Optional[str] = None
    is_business: bool
    birthday: Optional[str] = None
    phone_number: Optional[str] = None
    gender: Optional[int] = None
    email: Optional[str] = None

    _external_url = field_validator("external_url")(validate_external_url)  # Updated to use field_validator

class UserShort(TypesBaseModel):
    def __hash__(self):
        return hash(self.pk)

    def __eq__(self, other):
        if isinstance(other, UserShort):
            return self.pk == other.pk
        return NotImplemented

    pk: str
    username: Optional[str] = None
    full_name: Optional[str] = ""
    profile_pic_url: Optional[HttpUrl] = None
    profile_pic_url_hd: Optional[HttpUrl] = None
    is_private: Optional[bool] = None
    # is_verified: bool  # not found in hashtag_medias_v1
    # stories: List = [] # not found in fbsearch_suggested_profiles


class Usertag(TypesBaseModel):
    user: UserShort
    x: float
    y: float


class Location(TypesBaseModel):
    pk: Optional[int] = None
    name: str
    phone: Optional[str] = ""
    website: Optional[str] = ""
    category: Optional[str] = ""
    hours: Optional[dict] = {}  # opening hours
    address: Optional[str] = ""
    city: Optional[str] = ""
    zip: Optional[str] = ""
    lng: Optional[float] = None
    lat: Optional[float] = None
    external_id: Optional[int] = None
    external_id_source: Optional[str] = None
    # address_json: Optional[dict] = {}
    # profile_pic_url: Optional[HttpUrl]
    # directory: Optional[dict] = {}


class Media(TypesBaseModel):
    pk: Union[str, int]
    id: str
    code: str
    taken_at: datetime
    media_type: int
    image_versions2: Optional[dict] = {}
    product_type: Optional[str] = ""  # igtv or feed
    thumbnail_url: Optional[HttpUrl] = None
    location: Optional[Location] = None
    user: UserShort
    comment_count: Optional[int] = 0
    comments_disabled: Optional[bool] = False
    commenting_disabled_for_viewer: Optional[bool] = False
    like_count: int
    play_count: Optional[int] = None
    has_liked: Optional[bool] = None
    caption_text: str
    accessibility_caption: Optional[str] = None
    usertags: List[Usertag]
    sponsor_tags: List[UserShort]
    video_url: Optional[HttpUrl] = None  # for Video and IGTV
    view_count: Optional[int] = 0  # for Video and IGTV
    video_duration: Optional[float] = 0.0  # for Video and IGTV
    title: Optional[str] = ""
    resources: List[Resource] = []
    clips_metadata: dict = {}


class MediaXma(TypesBaseModel):
    # media_type: int
    video_url: HttpUrl  # for Video and IGTV
    title: Optional[str] = ""
    preview_url: Optional[HttpUrl] = None
    preview_url_mime_type: Optional[str] = None
    header_icon_url: Optional[HttpUrl] = None
    header_icon_width: Optional[int] = None
    header_icon_height: Optional[int] = None
    header_title_text: Optional[str] = None
    preview_media_fbid: Optional[str] = None


class MediaOembed(TypesBaseModel):
    title: str
    author_name: str
    author_url: str
    author_id: str
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


class Collection(TypesBaseModel):
    id: str
    name: str
    type: str
    media_count: int


class Comment(TypesBaseModel):
    pk: str
    text: str
    user: UserShort
    created_at_utc: datetime
    content_type: str
    status: str
    replied_to_comment_id: Optional[str] = None
    has_liked: Optional[bool] = None
    like_count: Optional[int] = None


class Hashtag(TypesBaseModel):
    id: str
    name: str
    media_count: Optional[int] = None
    profile_pic_url: Optional[HttpUrl] = None


class StoryMention(TypesBaseModel):
    user: UserShort
    x: Optional[float] = None
    y: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    rotation: Optional[float] = None


class StoryMedia(TypesBaseModel):
    # Instagram does not return the feed_media object when requesting story,
    # so you will have to make an additional request to get media and this is overhead:
    # media: Media
    x: float = 0.5
    y: float = 0.4997396
    z: float = 0
    width: float = 0.8
    height: float = 0.60572916
    rotation: float = 0.0
    is_pinned: Optional[bool] = None
    is_hidden: Optional[bool] = None
    is_sticker: Optional[bool] = None
    is_fb_sticker: Optional[bool] = None
    media_pk: int
    user_id: Optional[int] = None
    product_type: Optional[str] = None
    media_code: Optional[str] = None


class StoryHashtag(TypesBaseModel):
    hashtag: Hashtag
    x: Optional[float] = None
    y: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    rotation: Optional[float] = None


class StoryLocation(TypesBaseModel):
    location: Location
    x: Optional[float] = None
    y: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    rotation: Optional[float] = None


class StoryStickerLink(TypesBaseModel):
    url: HttpUrl
    link_title: Optional[str] = None
    link_type: Optional[str] = None
    display_url: Optional[str] = None


class StorySticker(TypesBaseModel):
    id: Optional[str] = None
    type: Optional[str] = "gif"
    x: float
    y: float
    z: Optional[int] = 1000005
    width: float
    height: float
    rotation: Optional[float] = 0.0
    story_link: Optional[StoryStickerLink] = None
    extra: Optional[dict] = {}


class StoryBuild(TypesBaseModel):
    mentions: List[StoryMention]
    path: FilePath
    paths: List[FilePath] = []
    stickers: List[StorySticker] = []


class StoryLink(TypesBaseModel):
    webUri: HttpUrl
    x: float = 0.5126011
    y: float = 0.5168225
    z: float = 0.0
    width: float = 0.50998676
    height: float = 0.25875
    rotation: float = 0.0


class Story(TypesBaseModel):
    pk: str
    id: str
    code: str
    taken_at: datetime
    imported_taken_at: Optional[datetime] = None
    media_type: int
    product_type: Optional[str] = ""
    thumbnail_url: Optional[HttpUrl] = None
    user: UserShort
    video_url: Optional[HttpUrl] = None  # for Video and IGTV
    video_duration: Optional[float] = 0.0  # for Video and IGTV
    sponsor_tags: List[UserShort]
    is_paid_partnership: Optional[bool] = False
    mentions: List[StoryMention]
    links: List[StoryLink]
    hashtags: List[StoryHashtag]
    locations: List[StoryLocation]
    stickers: List[StorySticker]
    medias: List[StoryMedia] = []


class Guide(TypesBaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    description: str
    cover_media: Media
    feedback_item: Optional[dict] = None


class DirectMedia(TypesBaseModel):
    id: str
    media_type: int
    user: Optional[UserShort] = None
    thumbnail_url: Optional[HttpUrl] = None
    video_url: Optional[HttpUrl] = None
    audio_url: Optional[HttpUrl] = None


class ReplyMessage(TypesBaseModel):
    id: str
    user_id: Optional[str] = None
    timestamp: datetime
    item_type: Optional[str] = None
    is_sent_by_viewer: Optional[bool] = None
    is_shh_mode: Optional[bool] = None
    text: Optional[str] = None
    link: Optional[dict] = None
    animated_media: Optional[dict] = None
    media: Optional[DirectMedia] = None
    visual_media: Optional[dict] = None
    media_share: Optional[Media] = None
    reel_share: Optional[dict] = None
    story_share: Optional[dict] = None
    felix_share: Optional[dict] = None
    xma_share: Optional[MediaXma] = None
    clip: Optional[Media] = None
    placeholder: Optional[dict] = None


class DirectMessage(TypesBaseModel):
    id: str  # e.g. 28597946203914980615241927545176064
    user_id: Optional[str] = None
    thread_id: Optional[int] = None  # e.g. 340282366841710300949128531777654287254
    timestamp: datetime
    item_type: Optional[str] = None
    is_sent_by_viewer: Optional[bool] = None
    is_shh_mode: Optional[bool] = None
    reactions: Optional[dict] = None
    text: Optional[str] = None
    reply: Optional[ReplyMessage] = None
    link: Optional[dict] = None
    animated_media: Optional[dict] = None
    media: Optional[DirectMedia] = None
    visual_media: Optional[dict] = None
    media_share: Optional[Media] = None
    reel_share: Optional[dict] = None
    story_share: Optional[dict] = None
    felix_share: Optional[dict] = None
    xma_share: Optional[MediaXma] = None
    clip: Optional[Media] = None
    placeholder: Optional[dict] = None
    client_context: Optional[str] = None


class DirectResponse(TypesBaseModel):
    unseen_count: Optional[int] = None
    unseen_count_ts: Optional[int] = None
    status: Optional[str] = None


class DirectShortThread(TypesBaseModel):
    id: str
    users: List[UserShort]
    named: bool
    thread_title: str
    pending: bool
    thread_type: str
    viewer_id: str
    is_group: bool


class DirectThread(TypesBaseModel):
    pk: str  # thread_v2_id, e.g. 17898572618026348
    id: str  # thread_id, e.g. 340282366841510300949128268610842297468
    messages: List[DirectMessage]
    users: List[UserShort]
    inviter: Optional[UserShort] = None
    left_users: List[UserShort] = []
    admin_user_ids: list
    last_activity_at: datetime
    muted: bool
    is_pin: Optional[bool] = None
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

    def is_seen(self, user_id: str):
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


class Relationship(TypesBaseModel):
    user_id: str
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


class RelationshipShort(TypesBaseModel):
    user_id: str
    following: bool
    incoming_request: bool
    is_bestie: bool
    is_feed_favorite: bool
    is_private: bool
    is_restricted: bool
    outgoing_request: bool


class Highlight(TypesBaseModel):
    pk: str  # 17895485401104052
    id: str  # highlight:17895485401104052
    latest_reel_media: int
    cover_media: dict
    user: UserShort
    title: str
    created_at: datetime
    is_pinned_highlight: bool
    media_count: int
    media_ids: List[int] = []
    items: List[Story] = []


class Share(TypesBaseModel):
    pk: str
    type: str


class Track(TypesBaseModel):
    id: str
    title: str
    subtitle: str
    display_artist: str
    audio_cluster_id: int
    artist_id: Optional[int] = None
    cover_artwork_uri: Optional[HttpUrl] = None
    cover_artwork_thumbnail_uri: Optional[HttpUrl] = None
    progressive_download_url: Optional[HttpUrl] = None
    fast_start_progressive_download_url: Optional[HttpUrl] = None
    reactive_audio_download_url: Optional[HttpUrl] = None
    highlight_start_times_in_ms: List[int]
    is_explicit: bool
    dash_manifest: str
    uri: Optional[HttpUrl] = None
    has_lyrics: bool
    audio_asset_id: int
    duration_in_ms: int
    dark_message: Optional[str] = None
    allows_saving: bool
    territory_validity_periods: dict


class Note(TypesBaseModel):
    id: str
    text: str
    user_id: str
    user: UserShort
    audience: int
    created_at: datetime
    expires_at: datetime
    is_emoji_only: bool
    has_translation: bool
    note_style: int
