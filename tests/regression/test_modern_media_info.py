import copy
import unittest
from unittest.mock import Mock

from instagrapi import Client
from instagrapi.exceptions import ClientGraphqlError, MediaNotFound
from instagrapi.mixins.media import MEDIA_INFO_DOC_ID

GQL_MEDIA = {
    "__typename": "GraphImage",
    "id": "1",
    "shortcode": "B",
    "taken_at_timestamp": 1710000000,
    "owner": {"id": "2", "username": "example", "profile_pic_url": "https://example.com/profile.jpg"},
    "display_resources": [{"src": "https://example.com/x.jpg", "config_width": 100, "config_height": 100}],
    "edge_media_to_comment": {"count": 0},
    "edge_media_preview_like": {"count": 0},
    "edge_media_to_caption": {"edges": []},
    "edge_media_to_tagged_user": {"edges": []},
}
REST_MEDIA = {
    "id": "1",
    "code": "B",
    "taken_at_timestamp": 1710000000,
    "media_type": 1,
    "user": {"pk": "2", "username": "example", "profile_pic_url": "https://example.com/profile.jpg"},
    "image_versions2": {"candidates": [{"url": "https://example.com/x.jpg", "width": 100, "height": 100}]},
}


class ModernMediaInfoTests(unittest.TestCase):
    def setUp(self):
        self.client = Client()
        self.client.public_graphql_request = Mock(side_effect=AssertionError("legacy query dispatched"))

    def tearDown(self):
        for session in (self.client.public, self.client.private, self.client.graphql):
            session.close()

    def test_media_info_dispatches_modern_query_before_any_legacy_request(self):
        self.client.public_doc_id_graphql_request = Mock(return_value={"xdt_shortcode_media": copy.deepcopy(GQL_MEDIA)})
        media = self.client.media_info_gql("1_2")
        self.assertEqual((media.pk, media.code, media.media_type), ("1", "B", 1))
        self.client.public_graphql_request.assert_not_called()
        self.client.public_doc_id_graphql_request.assert_called_once_with(
            MEDIA_INFO_DOC_ID,
            {
                "shortcode": "B",
                "__relay_internal__pv__PolarisShortDramaEnabledrelayprovider": False,
                "__relay_internal__pv__PolarisMultiCaptionCarouselEnabledrelayprovider": True,
            },
            referer="https://www.instagram.com/p/B/",
            url=self.client.GRAPHQL_PUBLIC_WEB_API_URL,
            include_lsd=True,
            include_fb_dtsg=True,
            headers={"X-FB-Friendly-Name": "PolarisPostRootQuery"},
        )

    def test_modern_media_accepts_supported_graphql_and_rest_shapes_without_mutation(self):
        for data in [
            {"shortcode_media": copy.deepcopy(GQL_MEDIA)},
            {"xdt_api__v1__media__shortcode__web_info": {"items": [copy.deepcopy(REST_MEDIA)]}},
        ]:
            with self.subTest(shape=next(iter(data))):
                original = copy.deepcopy(data)
                self.client.public_doc_id_graphql_request = Mock(return_value=data)
                media = self.client.media_info_gql("1")
                self.assertEqual((media.pk, media.id, media.media_type), ("1", "1_2", 1))
                self.assertEqual(data, original)
                self.client.public_graphql_request.assert_not_called()

    def test_missing_modern_media_raises_typed_not_found_without_legacy(self):
        self.client.public_doc_id_graphql_request = Mock(return_value={})
        with self.assertRaises(MediaNotFound):
            self.client.media_info_gql("1")
        self.client.public_graphql_request.assert_not_called()

    def test_modern_error_is_preserved_without_legacy_fallback(self):
        error = ClientGraphqlError("query unavailable")
        self.client.public_doc_id_graphql_request = Mock(side_effect=error)
        with self.assertRaises(ClientGraphqlError) as caught:
            self.client.media_info_gql("1")
        self.assertIs(caught.exception, error)
        self.client.public_graphql_request.assert_not_called()
