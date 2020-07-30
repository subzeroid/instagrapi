from .utils import json_value


def extract_media_v1(data):
    """Extract media from Private API
    """
    user = data["user"]
    location = data.get("location")
    if location:
        location = {"pk": int(location.get("pk")), "name": location.get("name")}
    video_url = ""
    if "video_versions" in data:
        video_url = sorted(
            data["video_versions"], key=lambda o: o["height"] * o["width"]
        ).pop()["url"]
    product_type = data.get("product_type", "")
    if data["media_type"] == 2 and not product_type:
        product_type = "feed"
    thumbnail_url = ''
    if 'image_versions2' in data:
        thumbnail_url = sorted(
            data["image_versions2"]["candidates"],
            key=lambda o: o["height"] * o["width"],
        ).pop()["url"]
    return {
        "pk": int(data["pk"]),
        "taken_at": int(data["taken_at"]),
        "id": data["id"],
        "media_type": data["media_type"],
        "product_type": product_type,
        "code": data["code"],
        "thumbnail_url": thumbnail_url,
        "location": location,
        "user": extract_user_short(user),
        "comment_count": int(data.get("comment_count") or 0),
        "like_count": int(data.get("like_count") or 0),  # the media just published has no like_count
        "caption_text": json_value(data, "caption", "text", default=""),
        "usertags": [
            extract_usertag(usertag)
            for usertag in data.get("usertags", {}).get("in", [])
        ],
        "video_url": video_url,
        "view_count": int(data.get('view_count') or 0),
        "video_duration": data.get('video_duration'),
        "title": data.get("title") or None,
        "resources": [
            extract_resource_v1(edge)
            for edge in data.get('carousel_media', [])
        ]
    }


def extract_media_gql(data):
    """Extract media from GraphQL
    """
    user = data["owner"]
    media_id = "%s_%s" % (data["id"], user["id"])
    if "full_name" in user:
        # for hashtag user contain {'id': '2041641294'}
        user = extract_user_short(user)
    else:
        user["pk"] = user.pop("id")
    location = data.get("location")
    if location:
        location = {"pk": int(location.get("id")), "name": location.get("name")}
    media_type = {"GraphImage": 1, "GraphVideo": 2, "GraphSidecar": 8}[data["__typename"]]
    product_type = data.get("product_type", "")
    video_url = ""
    if media_type == 2:
        video_url = data["video_url"]
        if not product_type:
            product_type = "feed"
    shortcode = ''
    if 'shortcode' in data:
        shortcode = data["shortcode"]
    return {
        "pk": int(data["id"]),
        "taken_at": int(data["taken_at_timestamp"]),
        "id": media_id,
        "media_type": media_type,
        "product_type": product_type,
        "code": shortcode,
        "thumbnail_url": sorted(
            data.get("display_resources", data.get('thumbnail_resources')),  # display_resources - user feed, thumbnail_resources - hashtag feed
            key=lambda o: o["config_width"] * o["config_height"],
        ).pop()["src"],
        "location": location,
        "user": user,
        "comment_count": json_value(data, "edge_media_to_comment", "count"),
        "like_count": json_value(data, "edge_media_preview_like", "count"),
        "caption_text": json_value(
            data, "edge_media_to_caption", "edges", 0, "node", "text", default=""
        ),
        "usertags": [
            extract_usertag(usertag['node'])
            for usertag in data.get("edge_media_to_tagged_user", {}).get("edges", [])
        ],
        "video_url": video_url,
        "view_count": int(data.get('video_view_count') or 0),
        "video_duration": data.get('video_duration'),
        "title": data.get("title") or None,
        "resources": [
            extract_resource_gql(edge['node'])
            for edge in data.get('edge_sidecar_to_children', {}).get('edges', [])
        ]
    }


def extract_resource_v1(data):
    video_url = ""
    if 'video_versions' in data:
        video_url = sorted(
            data["video_versions"], key=lambda o: o["height"] * o["width"]
        ).pop()["url"]
    thumbnail_url = sorted(
        data["image_versions2"]["candidates"],
        key=lambda o: o["height"] * o["width"],
    ).pop()["url"]
    return {
        "video_url": video_url,
        "thumbnail_url": thumbnail_url,
        "media_type": data['media_type'],
        "pk": int(data["pk"]),
        # "video_duration": data.get('video_duration'),
    }


def extract_resource_gql(data):
    media_type = {"GraphImage": 1, "GraphVideo": 2, "GraphSidecar": 8}[data["__typename"]]
    return {
        "video_url": data.get("video_url", ""),
        "thumbnail_url": data["display_url"],
        "media_type": media_type,
        "pk": int(data["id"]),
        # "view_count": int(data.get("video_view_count") or 0),
        # "shortcode": data["shortcode"],
        # "accessibility_caption": data.get("accessibility_caption")
    }


def extract_usertag(data):
    """Extract user tag
    """
    user = data['user']
    position = data.get('position')
    if not position:
        position = [data['x'], data['y']]
    return {
        "user": {
            "pk": int(user.get("id", user.get("pk"))),
            "username": user["username"],
            "full_name": user.get("full_name"),
            "profile_pic_url": user.get("profile_pic_url"),
            "is_verified": user.get("is_verified"),
        },
        "position": position
    }


def extract_user_short(data):
    """For Public GraphQL API
    """
    user_pk = data.get("id", data.get("pk"))
    assert user_pk, 'User without pk "%s"' % data
    return {
        "pk": int(user_pk),
        "username": data["username"],
        "full_name": data["full_name"],
        "is_private": data.get("is_private"),
        "profile_pic_url": data["profile_pic_url"],
        "is_verified": data.get("is_verified"),
        # "is_unpublished": data.get("is_unpublished"),
    }


def extract_user_gql(data):
    """For Public GraphQL API
    """
    return {
        "pk": int(data["id"]),
        "username": data["username"],
        "full_name": data["full_name"],
        "is_private": data["is_private"],
        "profile_pic_url": data["profile_pic_url"],
        "is_verified": data.get("is_verified"),
        "media_count": data["edge_owner_to_timeline_media"]["count"],
        "follower_count": data["edge_followed_by"]["count"],
        "following_count": data["edge_follow"]["count"],
        "biography": data["biography"],
        "external_url": data["external_url"],
        "is_business": data["is_business_account"],
    }


def extract_user_v1(data):
    """For Private API
    """
    return {
        "pk": int(data["pk"]),
        "username": data["username"],
        "full_name": data["full_name"],
        "is_private": data["is_private"],
        "profile_pic_url": data["profile_pic_url"],
        "is_verified": data.get("is_verified"),
        "media_count": data["media_count"],
        "follower_count": data["follower_count"],
        "following_count": data["following_count"],
        "biography": data["biography"],
        "external_url": data["external_url"],
        "is_business": data["is_business"],
    }
