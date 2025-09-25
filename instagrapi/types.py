from datetime import datetime
from typing import Dict, List, Optional, Union

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
    raise ValidationError(
        "external_url must be a URL or string"
    )  # Corrected 'been' to 'be'


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
    creator_igid: Optional[str] = None
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

    @field_validator("external_url")
    @classmethod
    def validate_external_url(cls, v):
        if v is None or (v.startswith("http") and "://" in v) or isinstance(v, str):
            return v
        raise ValidationError("external_url must be a URL or string")


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

    @field_validator("external_url")
    @classmethod
    def validate_external_url(cls, v):
        if v is None or (v.startswith("http") and "://" in v) or isinstance(v, str):
            return v
        raise ValidationError("external_url must be a URL or string")


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


class SharedMediaImageCandidate(TypesBaseModel):
    """Image candidate for shared media clips with video features"""

    estimated_scans_sizes: List[int] = []
    height: int
    scans_profile: str
    url: str
    width: int


class ScrubberSpritesheetInfo(TypesBaseModel):
    """Spritesheet information for video scrubbing"""

    file_size_kb: int
    max_thumbnails_per_sprite: int
    rendered_width: int
    sprite_height: int
    sprite_urls: List[str]
    sprite_width: int
    thumbnail_duration: float
    thumbnail_height: int
    thumbnail_width: int
    thumbnails_per_row: int
    total_thumbnail_num_per_sprite: int
    video_length: float


class ScrubberSpritesheetInfoCandidates(TypesBaseModel):
    """Container for spritesheet information candidates"""

    default: ScrubberSpritesheetInfo


class AdditionalCandidates(TypesBaseModel):
    """Additional candidates structure in image_versions2"""

    first_frame: Optional[SharedMediaImageCandidate] = None
    igtv_first_frame: Optional[SharedMediaImageCandidate] = None
    smart_frame: Optional[SharedMediaImageCandidate] = None


class SharedMediaImageVersions(TypesBaseModel):
    """Complete image_versions2 structure for shared media clips"""

    additional_candidates: Optional[AdditionalCandidates] = None
    candidates: List[SharedMediaImageCandidate] = []
    scrubber_spritesheet_info_candidates: Optional[
        ScrubberSpritesheetInfoCandidates
    ] = None


class ClipsAchievementsInfo(TypesBaseModel):
    """Information about achievements in clips"""

    num_earned_achievements: Optional[int] = None
    show_achievements: bool = False


class AudioReattributionInfo(TypesBaseModel):
    """Audio reattribution settings"""

    should_allow_restore: bool = False


class ClipsAdditionalAudioInfo(TypesBaseModel):
    """Additional audio information for clips"""

    additional_audio_username: Optional[str] = None
    audio_reattribution_info: AudioReattributionInfo


class ClipsAudioRankingInfo(TypesBaseModel):
    """Audio ranking information for clips"""

    best_audio_cluster_id: str


class ClipsBrandedContentTagInfo(TypesBaseModel):
    """Branded content tag information for clips"""

    can_add_tag: bool = False


class ClipsContentAppreciationInfo(TypesBaseModel):
    """Content appreciation information for clips"""

    enabled: bool = False
    entry_point_container: Optional[str] = None


class ClipsMashupInfo(TypesBaseModel):
    """Mashup information for clips"""

    can_toggle_mashups_allowed: bool = False
    formatted_mashups_count: Optional[str] = None
    has_been_mashed_up: bool = False
    has_nonmimicable_additional_audio: bool = False
    is_creator_requesting_mashup: bool = False
    is_light_weight_check: bool = True
    is_light_weight_reuse_allowed_check: bool = False
    is_pivot_page_available: bool = False
    is_reuse_allowed: bool = True
    mashup_type: Optional[str] = None
    mashups_allowed: bool = True
    non_privacy_filtered_mashups_media_count: int = 0
    privacy_filtered_mashups_media_count: Optional[int] = None
    original_media: Optional[dict] = None


class ClipsConsumptionInfo(TypesBaseModel):
    """Consumption information for clips original sound"""

    display_media_id: Optional[str] = None
    is_bookmarked: bool = False
    is_trending_in_clips: bool = False
    should_mute_audio_reason: str = ""
    should_mute_audio_reason_type: Optional[str] = None
    user_notes: Optional[str] = None


class ClipsFbDownstreamUseXpostMetadata(TypesBaseModel):
    """Facebook downstream use xpost metadata for clips"""

    downstream_use_xpost_deny_reason: str = "NONE"


class ClipsIgArtist(TypesBaseModel):
    """Instagram artist information for clips original sound"""

    pk: int
    pk_id: str
    id: str
    username: str
    full_name: str
    is_private: bool = False
    is_verified: bool = False
    profile_pic_id: str
    profile_pic_url: str
    strong_id__: str


class ClipsOriginalSoundInfo(TypesBaseModel):
    """Original sound information for clips"""

    allow_creator_to_rename: bool = True
    audio_asset_id: int
    attributed_custom_audio_asset_id: Optional[int] = None
    can_remix_be_shared_to_fb: bool = True
    can_remix_be_shared_to_fb_expansion: bool = True
    dash_manifest: str
    duration_in_ms: int
    formatted_clips_media_count: Optional[str] = None
    hide_remixing: bool = False
    is_audio_automatically_attributed: bool = False
    is_eligible_for_audio_effects: bool = True
    is_eligible_for_vinyl_sticker: bool = True
    is_explicit: bool = False
    is_original_audio_download_eligible: bool = True
    is_reuse_disabled: bool = False
    is_xpost_from_fb: bool = False
    music_canonical_id: Optional[str] = None
    oa_owner_is_music_artist: bool = False
    original_audio_subtype: str = "default"
    original_audio_title: str = "Original audio"
    original_media_id: int
    progressive_download_url: str
    should_mute_audio: bool = False
    time_created: int
    trend_rank: Optional[int] = None
    previous_trend_rank: Optional[int] = None
    overlap_duration_in_ms: Optional[int] = None
    audio_asset_start_time_in_ms: Optional[int] = None
    ig_artist: ClipsIgArtist
    audio_filter_infos: List[dict] = []
    audio_parts: List[dict] = []
    audio_parts_by_filter: List[dict] = []
    consumption_info: ClipsConsumptionInfo
    xpost_fb_creator_info: Optional[dict] = None
    fb_downstream_use_xpost_metadata: ClipsFbDownstreamUseXpostMetadata


class ClipsMetadata(TypesBaseModel):
    """Complete clips metadata structure for Media objects"""

    clips_creation_entry_point: str = "clips"
    featured_label: Optional[str] = None
    is_public_chat_welcome_video: bool = False
    professional_clips_upsell_type: int = 0
    show_tips: Optional[str] = None
    achievements_info: ClipsAchievementsInfo
    additional_audio_info: ClipsAdditionalAudioInfo
    asset_recommendation_info: Optional[dict] = None
    audio_ranking_info: ClipsAudioRankingInfo
    audio_type: str = "original_sounds"
    branded_content_tag_info: ClipsBrandedContentTagInfo
    breaking_content_info: Optional[dict] = None
    breaking_creator_info: Optional[dict] = None
    challenge_info: Optional[dict] = None
    content_appreciation_info: ClipsContentAppreciationInfo
    contextual_highlight_info: Optional[dict] = None
    cutout_sticker_info: List[dict] = []
    disable_use_in_clips_client_cache: bool = False
    external_media_info: Optional[dict] = None
    is_fan_club_promo_video: bool = False
    is_shared_to_fb: bool = False
    mashup_info: Optional[ClipsMashupInfo] = None
    merchandising_pill_info: Optional[dict] = None
    music_canonical_id: str
    music_info: Optional[dict] = None
    nux_info: Optional[dict] = None
    original_sound_info: Optional[ClipsOriginalSoundInfo] = None
    originality_info: Optional[dict] = None
    reels_on_the_rise_info: Optional[dict] = None
    reusable_text_attribute_string: Optional[str] = None
    reusable_text_info: Optional[dict] = None
    shopping_info: Optional[dict] = None
    show_achievements: bool = False
    template_info: Optional[dict] = None
    may_have_template_info: Optional[dict] = None
    viewer_interaction_settings: Optional[dict] = None


class Media(TypesBaseModel):
    pk: Union[str, int]
    id: str
    code: str
    taken_at: datetime
    media_type: int
    image_versions2: Optional[SharedMediaImageVersions] = None
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
    clips_metadata: Optional[ClipsMetadata] = None


class MediaXma(TypesBaseModel):
    # media_type: int
    video_url: HttpUrl  # for Video and IGTV
    title: Optional[str] = ""
    preview_url: Optional[str] = None
    preview_url_mime_type: Optional[str] = None
    header_icon_url: Optional[str] = None
    header_icon_width: Optional[int] = None
    header_icon_height: Optional[int] = None
    header_title_text: Optional[str] = None
    preview_media_fbid: Optional[str] = None

    @field_validator("preview_url", "header_icon_url")
    @classmethod
    def validate_url_fields(cls, v):
        """Validate URL fields allowing None, valid URLs, or any string"""
        if v is None or (v.startswith("http") and "://" in v) or isinstance(v, str):
            return v
        raise ValidationError("URL field must be a URL or string")


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


class StoryPoll(TypesBaseModel):
    id: Optional[str] = None
    type: Optional[str] = "poll"
    x: float
    y: float
    z: Optional[int] = 0
    width: float
    height: float
    rotation: Optional[float] = 0.0
    is_multi_option: Optional[bool] = True
    is_shared_result: Optional[bool] = False
    viewer_can_vote: Optional[bool] = True
    finished: Optional[bool] = False
    color: Optional[str] = "black"
    poll_type: Optional[str] = ""
    question: str
    options: list
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
    polls: List[StoryPoll] = []


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


class MessageReaction(TypesBaseModel):
    """Individual emoji reaction on a direct message"""

    timestamp: datetime
    client_context: Optional[str] = None
    sender_id: int
    emoji: str
    super_react_type: str = "none"


class MessageReactions(TypesBaseModel):
    """Reactions structure for direct messages"""

    likes: List[dict] = []  # Structure unknown from current examples
    likes_count: Optional[int] = 0
    emojis: List[MessageReaction] = []


class LinkContext(TypesBaseModel):
    """Link context metadata for direct message links"""

    link_url: str
    link_title: Optional[str] = ""
    link_summary: Optional[str] = ""
    link_image_url: Optional[str] = ""


class MessageLink(TypesBaseModel):
    """Link structure for direct messages"""

    text: str
    link_context: LinkContext
    client_context: Optional[str] = None
    mutation_token: Optional[str] = None


class DisappearingMessagesSeenState(TypesBaseModel):
    """Disappearing messages seen state information"""

    item_id: str
    timestamp: datetime
    created_at: datetime


class LastSeenInfo(TypesBaseModel):
    """Last seen information for a user in a direct thread"""

    item_id: str
    timestamp: datetime
    created_at: datetime
    shh_seen_state: dict = {}
    disappearing_messages_seen_state: Optional[DisappearingMessagesSeenState] = None


class FallbackUrl(TypesBaseModel):
    """Fallback URL structure for media candidates"""

    url: str


class DirectMessageImageCandidate(TypesBaseModel):
    """Image candidate for ephemeral visual media in direct messages"""

    width: int
    height: int
    url: str
    scans_profile: Optional[str] = None
    fallback: Optional[FallbackUrl] = None
    url_expiration_timestamp_us: Optional[datetime] = None


class DirectMessageImageVersions(TypesBaseModel):
    """Image versions for ephemeral visual media in direct messages"""

    candidates: List[DirectMessageImageCandidate] = []


class VideoVersion(TypesBaseModel):
    """Individual video version with specific resolution and quality"""

    id: Optional[str] = ""
    type: Optional[int] = None
    width: int
    height: int
    url: str
    fallback: Optional[FallbackUrl] = None
    url_expiration_timestamp_us: Optional[datetime] = None
    bandwidth: Optional[int] = 0


class FriendshipStatus(TypesBaseModel):
    """Friendship status information for visual media user"""

    blocking: bool = False
    is_messaging_only_blocking: bool = False
    is_messaging_pseudo_blocking: bool = False
    is_unavailable: bool = False


class VisualMediaUser(TypesBaseModel):
    """User information in visual media (enhanced UserShort)"""

    id: str
    strong_id__: Optional[str] = None
    pk: int
    pk_id: str
    full_name: str
    username: str
    account_type: Optional[int] = None
    short_name: Optional[str] = None
    profile_pic_url: str
    is_verified: bool = False
    interop_messaging_user_fbid: Optional[int] = None
    fbid_v2: Optional[int] = None
    has_ig_profile: bool = True
    interop_user_type: Optional[int] = 0
    is_using_unified_inbox_for_direct: bool = False
    is_private: bool = False
    is_creator_agent_enabled: bool = False
    is_creator_automated_response_enabled: bool = False
    friendship_status: Optional[FriendshipStatus] = None
    is_shared_account: bool = False
    is_shared_account_with_messaging_access: bool = False
    ai_agent_banner_type: Optional[str] = None
    is_eligible_for_ai_bot_group_chats: bool = False


class ExpiringMediaActionSummary(TypesBaseModel):
    """Summary of expiring media actions"""

    type: str
    timestamp: datetime
    count: int


class VisualMediaContent(TypesBaseModel):
    """Content structure for visual media (can be rich or minimal)"""

    media_type: int  # Always present: 1=image, 2=video
    id: Optional[str] = None
    media_id: Optional[int] = None
    image_versions2: Optional[DirectMessageImageVersions] = None
    video_versions: Optional[List[VideoVersion]] = None
    original_width: Optional[int] = None
    original_height: Optional[int] = None
    user: Optional[VisualMediaUser] = None
    organic_tracking_token: Optional[str] = None
    video_duration: Optional[int] = None
    video_dash_manifest: Optional[str] = None
    is_dash_eligible: Optional[int] = None
    create_mode_attribution: Optional[dict] = None
    creative_config: Optional[dict] = None
    expiring_media_action_summary: Optional[ExpiringMediaActionSummary] = None


class VisualMedia(TypesBaseModel):
    """Complete visual media structure for direct messages"""

    media: VisualMediaContent
    seen_user_ids: List[str] = []
    seen_count: int = 0
    view_mode: str  # 'replayable', 'permanent', etc.
    replay_expiring_at_us: Optional[int] = None
    reply_type: Optional[str] = None
    url_expire_at_secs: Optional[int] = None
    story_app_attribution: Optional[dict] = None
    playback_duration_secs: Optional[int] = None
    tap_models: List[dict] = []
    expiring_media_action_summary: Optional[ExpiringMediaActionSummary] = None


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
    visual_media: Optional[VisualMedia] = None
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
    reactions: Optional[MessageReactions] = None
    text: Optional[str] = None
    reply: Optional[ReplyMessage] = None
    link: Optional[MessageLink] = None
    animated_media: Optional[dict] = None
    media: Optional[DirectMedia] = None
    visual_media: Optional[VisualMedia] = None
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
    last_seen_at: Dict[str, LastSeenInfo] = {}

    def is_seen(self, user_id: str):
        """Have I seen this thread?
        :param user_id: You account user_id
        """
        user_id = str(user_id)
        if user_id not in self.last_seen_at:
            return False
        own_timestamp = self.last_seen_at[user_id].timestamp.timestamp()
        timestamps = [
            (v.timestamp.timestamp() - own_timestamp) > 0
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
