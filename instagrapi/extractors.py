from copy import deepcopy

from .types import (
    Account,
    Collection,
    Comment,
    DirectMessage,
    DirectResponse,
    DirectShortThread,
    DirectThread,
    Hashtag,
    Location,
    Media,
    MediaOembed,
    Resource,
    Story,
    StoryLink,
    StoryMention,
    User,
    UserShort,
    Usertag,
)
from .utils import InstagramIdCodec, json_value

MEDIA_TYPES_GQL = {"GraphImage": 1, "GraphVideo": 2, "GraphSidecar": 8, "StoryVideo": 2}


def extract_media_v1(data):
    """Extract media from Private API"""
    media = deepcopy(data)
    if "video_versions" in media:
        # Select Best Quality by Resolutiuon
        media["video_url"] = sorted(
            media["video_versions"], key=lambda o: o["height"] * o["width"]
        )[-1]["url"]
    if media["media_type"] == 2 and not media.get("product_type"):
        media["product_type"] = "feed"
    if "image_versions2" in media:
        media["thumbnail_url"] = sorted(
            media["image_versions2"]["candidates"],
            key=lambda o: o["height"] * o["width"],
        )[-1]["url"]
    if media["media_type"] == 8:
        # remove thumbnail_url and video_url for albums
        # see resources
        media.pop("thumbnail_url", "")
        media.pop("video_url", "")
    location = media.get("location")
    media["location"] = location and extract_location(location)
    media["user"] = extract_user_short(media.get("user"))
    media["usertags"] = sorted(
        [
            extract_usertag(usertag)
            for usertag in media.get("usertags", {}).get("in", [])
        ],
        key=lambda tag: tag.user.pk,
    )
    media["like_count"] = media.get("like_count", 0)
    return Media(
        caption_text=(media.get("caption") or {}).get("text", ""),
        resources=[
            extract_resource_v1(edge) for edge in media.get("carousel_media", [])
        ],
        **media,
    )


def extract_media_gql(data):
    """Extract media from GraphQL"""
    media = deepcopy(data)
    user = extract_user_short(media["owner"])
    # if "full_name" in user:
    #     user = extract_user_short(user)
    # else:
    #     user["pk"] = user.pop("id")
    try:
        media["media_type"] = MEDIA_TYPES_GQL[media["__typename"]]
    except KeyError:
        media["media_type"] = 0
    if media.get("media_type") == 2 and not media.get("product_type"):
        media["product_type"] = "feed"
    media["thumbnail_url"] = sorted(
        # display_resources - user feed, thumbnail_resources - hashtag feed
        media.get("display_resources", media.get("thumbnail_resources")),
        key=lambda o: o["config_width"] * o["config_height"],
    )[-1]["src"]
    if media.get("media_type") == 8:
        # remove thumbnail_url and video_url for albums
        # see resources
        media.pop("thumbnail_url", "")
        media.pop("video_url", "")
    location = media.pop("location", None)
    media_id = media.get("id")
    media["pk"] = media_id
    media["id"] = f"{media_id}_{user.pk}"
    return Media(
        code=media.get("shortcode"),
        taken_at=media.get("taken_at_timestamp"),
        location=extract_location(location) if location else None,
        user=user,
        view_count=media.get("video_view_count", 0),
        comment_count=json_value(media, "edge_media_to_comment", "count"),
        like_count=json_value(media, "edge_media_preview_like", "count"),
        caption_text=json_value(
            media, "edge_media_to_caption", "edges", 0, "node", "text", default=""
        ),
        usertags=sorted(
            [
                extract_usertag(usertag["node"])
                for usertag in media.get("edge_media_to_tagged_user", {}).get(
                    "edges", []
                )
            ],
            key=lambda tag: tag.user.pk,
        ),
        resources=[
            extract_resource_gql(edge["node"])
            for edge in media.get("edge_sidecar_to_children", {}).get("edges", [])
        ],
        **media,
    )


def extract_resource_v1(data):
    if "video_versions" in data:
        data["video_url"] = sorted(
            data["video_versions"], key=lambda o: o["height"] * o["width"]
        )[-1]["url"]
    data["thumbnail_url"] = sorted(
        data["image_versions2"]["candidates"],
        key=lambda o: o["height"] * o["width"],
    )[-1]["url"]
    return Resource(**data)


def extract_resource_gql(data):
    data["media_type"] = MEDIA_TYPES_GQL[data["__typename"]]
    return Resource(pk=data["id"], thumbnail_url=data["display_url"], **data)


def extract_usertag(data):
    """Extract user tag"""
    x, y = data.get("position", [data.get("x"), data.get("y")])
    return Usertag(user=extract_user_short(data["user"]), x=x, y=y)


def extract_user_short(data):
    """Extract User Short info"""
    data["pk"] = data.get("id", data.get("pk", None))
    assert data["pk"], f'User without pk "{data}"'
    return UserShort(**data)


def extract_user_gql(data):
    """For Public GraphQL API"""
    return User(
        pk=data["id"],
        media_count=data["edge_owner_to_timeline_media"]["count"],
        follower_count=data["edge_followed_by"]["count"],
        following_count=data["edge_follow"]["count"],
        is_business=data["is_business_account"],
        public_email=data["business_email"],
        contact_phone_number=data["business_phone_number"],
        **data,
    )


def extract_user_v1(data):
    """For Private API"""
    data["external_url"] = data.get("external_url") or None
    return User(**data)


def extract_location(data):
    """Extract location info"""
    if not data:
        return None
    data["pk"] = data.get("id", data.get("pk", None))
    data["external_id"] = data.get("external_id", data.get("facebook_places_id"))
    data["external_id_source"] = data.get(
        "external_id_source", data.get("external_source")
    )
    # address_json = data.get("address_json", "{}")
    # if isinstance(address_json, str):
    #     address_json = json.loads(address_json)
    # data['address_json'] = address_json
    return Location(**data)


def extract_comment(data):
    """Extract comment"""
    data["has_liked"] = data.get("has_liked_comment")
    data["like_count"] = data.get("comment_like_count")
    return Comment(**data)


def extract_collection(data):
    """Extract collection for authorized account
    Example:
    {'collection_id': '17851406186124602',
    'collection_name': 'Repost',
    'collection_type': 'MEDIA',
    'collection_media_count': 1,
    'cover_media': {...}
    """
    data = {key.replace("collection_", ""): val for key, val in data.items()}
    # data['pk'] = data.get('id')
    return Collection(**data)


def extract_media_oembed(data):
    """Return short version of Media"""
    return MediaOembed(**data)


def extract_direct_thread(data):
    data["messages"] = [extract_direct_message(item) for item in data["items"]]
    data["users"] = [extract_user_short(u) for u in data["users"]]
    if "inviter" in data:
        data["inviter"] = extract_user_short(data["inviter"])
    data["pk"] = data.get("thread_v2_id")
    data["id"] = data.get("thread_id")
    data["left_users"] = data.get("left_users", [])
    return DirectThread(**data)


def extract_direct_short_thread(data):
    data["users"] = [extract_user_short(u) for u in data["users"]]
    data["id"] = data.get("thread_id")
    return DirectShortThread(**data)


def extract_direct_response(data):
    return DirectResponse(**data)


def extract_direct_message(data):
    data["id"] = data.get("item_id")
    if "media_share" in data:
        data["media_share"] = extract_media_v1(data["media_share"])
    return DirectMessage(**data)


def extract_account(data):
    data["external_url"] = data.get("external_url") or None
    return Account(**data)


def extract_hashtag_gql(data):
    data["media_count"] = data.get("edge_hashtag_to_media", {}).get("count")
    return Hashtag(**data)


def extract_hashtag_v1(data):
    data["allow_following"] = data.get("allow_following") == 1
    return Hashtag(**data)


def extract_story_v1(data):
    """Extract story from Private API"""
    story = deepcopy(data)
    if "video_versions" in story:
        # Select Best Quality by Resolutiuon
        story["video_url"] = sorted(
            story["video_versions"], key=lambda o: o["height"] * o["width"]
        )[-1]["url"]
    if story["media_type"] == 2 and not story.get("product_type"):
        story["product_type"] = "feed"
    if "image_versions2" in story:
        story["thumbnail_url"] = sorted(
            story["image_versions2"]["candidates"],
            key=lambda o: o["height"] * o["width"],
        )[-1]["url"]
    story["mentions"] = [
        StoryMention(**mention) for mention in story.get("reel_mentions", [])
    ]
    story["locations"] = []
    story["hashtags"] = []
    story["stickers"] = []
    story["links"] = []
    for cta in story.get("story_cta", []):
        for link in cta.get("links", []):
            story["links"].append(StoryLink(**link))
    story["user"] = extract_user_short(story.get("user"))
    return Story(**story)


def extract_story_gql(data):
    """Extract story from Public API"""
    story = deepcopy(data)
    if "video_resources" in story:
        # Select Best Quality by Resolutiuon
        story["video_url"] = sorted(
            story["video_resources"], key=lambda o: o["config_height"] * o["config_width"]
        )[-1]["src"]
    # if story["tappable_objects"] and "GraphTappableFeedMedia" in [x["__typename"] for x in story["tappable_objects"]]:
    story["product_type"] = "feed"
    story["thumbnail_url"] = story.get("display_url")
    story["mentions"] = []
    for mention in story.get("tappable_objects", []):
        if mention["__typename"] == "GraphTappableMention":
            mention["id"] = 1
            mention["user"] = extract_user_short(mention)
            story["mentions"].append(StoryMention(**mention))
    story["locations"] = []
    story["hashtags"] = []
    story["stickers"] = []
    story["links"] = []
    story_cta_url = story.get("story_cta_url", [])
    if story_cta_url:
        story["links"] = [StoryLink(**{'webUri': story_cta_url})]
    story["user"] = extract_user_short(story.get("owner"))
    story["pk"] = int(story["id"])
    story["id"] = f"{story['id']}_{story['owner']['id']}"
    story["code"] = InstagramIdCodec.encode(story["pk"])
    story["taken_at"] = story["taken_at_timestamp"]
    story["media_type"] = 2 if story["is_video"] else 1
    return Story(**story)
