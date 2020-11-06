# import json
from .utils import json_value
from .types import (
    Media, Resource, User, UserShort, Usertag,
    Location, Collection, Comment, MediaOembed,
    DirectThread, DirectMessage, Account
)


MEDIA_TYPES_GQL = {
    "GraphImage": 1,
    "GraphVideo": 2,
    "GraphSidecar": 8
}


def extract_media_v1(data):
    """Extract media from Private API
    """
    if "video_versions" in data:
        # Select Best Quality by Resolutiuon
        data['video_url'] = sorted(
            data["video_versions"], key=lambda o: o["height"] * o["width"]
        ).pop()["url"]
    if data["media_type"] == 2 and not data.get("product_type"):
        data["product_type"] = "feed"
    if 'image_versions2' in data:
        data['thumbnail_url'] = sorted(
            data["image_versions2"]["candidates"],
            key=lambda o: o["height"] * o["width"],
        ).pop()["url"]
    if data["media_type"] == 8:
        # remove thumbnail_url and video_url for albums
        # see resources
        data.pop('thumbnail_url', '')
        data.pop('video_url', '')
    location = data.pop("location", None)
    return Media(
        location=extract_location(location) if location else None,
        user=extract_user_short(data.pop("user")),
        caption_text=data.get("caption", {}).get("text", ""),
        usertags=sorted([
            extract_usertag(usertag)
            for usertag in data.pop("usertags", {}).get("in", [])
        ], key=lambda tag: tag.user.pk),
        resources=[
            extract_resource_v1(edge)
            for edge in data.get('carousel_media', [])
        ],
        like_count=data.pop('like_count', 0),
        **data
    )


def extract_media_gql(data):
    """Extract media from GraphQL
    """
    user = extract_user_short(data["owner"])
    # if "full_name" in user:
    #     user = extract_user_short(user)
    # else:
    #     user["pk"] = user.pop("id")
    data['media_type'] = MEDIA_TYPES_GQL[data["__typename"]]
    if data['media_type'] == 2 and not data.get('product_type'):
        data['product_type'] = "feed"
    data["thumbnail_url"] = sorted(
        # display_resources - user feed, thumbnail_resources - hashtag feed
        data.get("display_resources", data.get('thumbnail_resources')),
        key=lambda o: o["config_width"] * o["config_height"],
    ).pop()["src"]
    if data['media_type'] == 8:
        # remove thumbnail_url and video_url for albums
        # see resources
        data.pop('thumbnail_url', '')
        data.pop('video_url', '')
    location = data.pop("location", None)
    return Media(
        pk=data['id'],
        id=f"{data.pop('id')}_{user.pk}",
        code=data.get("shortcode"),
        taken_at=data["taken_at_timestamp"],
        location=extract_location(location) if location else None,
        user=user,
        view_count=data.get('video_view_count', 0),
        comment_count=json_value(data, "edge_media_to_comment", "count"),
        like_count=json_value(data, "edge_media_preview_like", "count"),
        caption_text=json_value(
            data, "edge_media_to_caption", "edges", 0, "node", "text", default=""
        ),
        usertags=sorted([
            extract_usertag(usertag['node'])
            for usertag in data.get("edge_media_to_tagged_user", {}).get("edges", [])
        ], key=lambda tag: tag.user.pk),
        resources=[
            extract_resource_gql(edge['node'])
            for edge in data.get('edge_sidecar_to_children', {}).get('edges', [])
        ],
        **data
    )


def extract_resource_v1(data):
    if 'video_versions' in data:
        data['video_url'] = sorted(
            data["video_versions"], key=lambda o: o["height"] * o["width"]
        ).pop()["url"]
    data['thumbnail_url'] = sorted(
        data["image_versions2"]["candidates"],
        key=lambda o: o["height"] * o["width"],
    ).pop()["url"]
    return Resource(**data)


def extract_resource_gql(data):
    data['media_type'] = MEDIA_TYPES_GQL[data["__typename"]]
    return Resource(
        pk=data["id"],
        thumbnail_url=data["display_url"],
        **data
    )


def extract_usertag(data):
    """Extract user tag
    """
    x, y = data.get('position', [
        data.get('x'),
        data.get('y')
    ])
    return Usertag(
        user=extract_user_short(data['user']),
        x=x, y=y
    )


def extract_user_short(data):
    """Extract User Short info
    """
    data['pk'] = data.get("id", data.get("pk", None))
    assert data['pk'], 'User without pk "%s"' % data
    return UserShort(**data)


def extract_user_gql(data):
    """For Public GraphQL API
    """
    return User(
        pk=data["id"],
        media_count=data["edge_owner_to_timeline_media"]["count"],
        follower_count=data["edge_followed_by"]["count"],
        following_count=data["edge_follow"]["count"],
        is_business=data["is_business_account"],
        **data
    )


def extract_user_v1(data):
    """For Private API
    """
    data['external_url'] = data.get('external_url') or None
    return User(**data)


def extract_location(data):
    """Extract location info
    """
    data['pk'] = data.get("id", data.get("pk", None))
    data['external_id'] = data.get('external_id', data.get('facebook_places_id'))
    data['external_id_source'] = data.get('external_id_source', data.get('external_source'))
    # address_json = data.get("address_json", "{}")
    # if isinstance(address_json, str):
    #     address_json = json.loads(address_json)
    # data['address_json'] = address_json
    return Location(**data)


def extract_comment(data):
    """Extract comment
    """
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
    data = {
        key.replace('collection_', ''): val
        for key, val in data.items()
    }
    # data['pk'] = data.get('id')
    return Collection(**data)


def extract_media_oembed(data):
    """Return short version of Media
    """
    return MediaOembed(**data)


def extract_direct_thread(data):
    data['messages'] = [extract_direct_message(item) for item in data['items']]
    data['users'] = [extract_user_short(u) for u in data['users']]
    data['inviter'] = extract_user_short(data['inviter'])
    data['pk'] = data.get('thread_v2_id')
    data['id'] = data.get('thread_id')
    return DirectThread(**data)


def extract_direct_message(data):
    data['id'] = data.get('item_id')
    if 'media_share' in data:
        data['media_share'] = extract_media_v1(data['media_share'])
    return DirectMessage(**data)


def extract_account(data):
    return Account(**data)
