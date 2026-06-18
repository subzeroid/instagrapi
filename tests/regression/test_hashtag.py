from tests.helpers import *


class HashtagRegressionTestCase(unittest.TestCase):
    def _media_gql_payload(self, pk="1"):
        return {
            "__typename": "GraphImage",
            "id": pk,
            "shortcode": f"code-{pk}",
            "taken_at_timestamp": 1710000000,
            "owner": {
                "id": "2",
                "username": "example",
                "profile_pic_url": "https://example.com/profile.jpg",
            },
            "display_resources": [{"src": f"https://example.com/{pk}.jpg", "config_width": 100, "config_height": 100}],
            "edge_media_to_comment": {"count": 0},
            "edge_media_preview_like": {"count": 0},
            "edge_media_to_caption": {"edges": []},
            "edge_media_to_tagged_user": {"edges": []},
        }

    def test_dead_public_a1_methods_are_removed(self):
        client = Client()
        removed_methods = (
            "public_a1_request",
            "public_a1_request_user_info_by_username",
            "media_info_a1",
            "user_info_by_username_a1",
            "location_info_a1",
            "location_medias_a1_chunk",
            "location_medias_a1",
            "location_medias_top_a1",
            "location_medias_recent_a1",
            "hashtag_info_a1",
            "hashtag_medias_a1_chunk",
            "hashtag_medias_a1",
            "hashtag_medias_top_a1",
            "hashtag_medias_recent_a1",
            "hashtag_related_hashtags",
        )

        for method_name in removed_methods:
            self.assertFalse(hasattr(client, method_name), method_name)

    def test_hashtag_medias_recent_strips_leading_hash_and_warns(self):
        client = Client()
        client.hashtag_medias_recent_v1 = Mock(return_value=["media"])

        with self.assertWarnsRegex(UserWarning, "leading '#'"):
            medias = client.hashtag_medias_recent("#pizza", amount=1)

        self.assertEqual(medias, ["media"])
        client.hashtag_medias_recent_v1.assert_called_once_with("pizza", 1)

    def test_hashtag_name_cannot_be_empty_after_normalization(self):
        client = Client()

        with self.assertRaisesRegex(ValueError, "Hashtag name cannot be empty"):
            client.hashtag_medias_recent("#")

    def test_hashtag_medias_v1_chunk_sends_tab_key(self):
        client = Client()
        client.private_request = Mock(
            return_value={
                "sections": [],
                "more_available": False,
                "next_max_id": None,
            }
        )

        client.hashtag_medias_v1_chunk("pizza", tab_key="recent")

        request_data = client.private_request.call_args.kwargs["data"]
        self.assertEqual(request_data["tab"], "recent")
        self.assertEqual(request_data["media_recency_filter"], "top_recent_posts")

    def test_hashtag_medias_v1_chunk_reads_top_level_section_layout_items(self):
        client = Client()

        def media(pk):
            return {
                "pk": pk,
                "id": f"{pk}_2",
                "code": f"code-{pk}",
                "taken_at": 1710000000,
                "media_type": 1,
                "user": {
                    "pk": "2",
                    "username": "example",
                    "profile_pic_url": "https://example.com/profile.jpg",
                },
                "image_versions2": {
                    "candidates": [
                        {
                            "url": f"https://example.com/{pk}.jpg",
                            "width": 100,
                            "height": 100,
                        }
                    ]
                },
            }

        client.private_request = Mock(
            return_value={
                "sections": [
                    {
                        "layout_type": "one_by_two_left",
                        "feed_type": "clips",
                        "layout_content": {
                            "one_by_two_item": {
                                "clips": {
                                    "items": [
                                        {"media": media("1")},
                                        {"media": media("2")},
                                    ]
                                }
                            },
                            "fill_items": [
                                {"media": media("3")},
                                {"media": media("4")},
                            ],
                        },
                    },
                    {
                        "layout_type": "media_grid",
                        "feed_type": "media",
                        "layout_content": {
                            "medias": [
                                {"media": media("5")},
                            ]
                        },
                    },
                ],
                "more_available": False,
                "next_max_id": None,
            }
        )

        medias, next_max_id = client.hashtag_medias_v1_chunk("example", 0, "top")

        self.assertEqual([media.pk for media in medias], ["1", "2", "3", "4", "5"])
        self.assertIsNone(next_max_id)

    def test_hashtag_medias_paginated_gql_returns_page_and_cursor(self):
        client = Client()
        payload = self._media_gql_payload()

        with mock.patch.object(
            client,
            "public_graphql_request",
            return_value={
                "hashtag": {
                    "edge_hashtag_to_media": {
                        "page_info": {"has_next_page": True, "end_cursor": "next-page"},
                        "edges": [{"node": payload}],
                    }
                }
            },
        ) as public_graphql_request:
            medias, end_cursor = client.hashtag_medias_paginated_gql("python", amount=1, end_cursor="cursor-1")

        public_graphql_request.assert_called_once_with(
            {"tag_name": "python", "show_ranked": False, "first": 1, "after": "cursor-1"},
            query_hash="f92f56d47dc7a55b606908374b43a314",
        )
        self.assertEqual(end_cursor, "next-page")
        self.assertEqual([media.pk for media in medias], ["1"])

    def test_hashtag_medias_paginated_v1_delegates_to_chunk(self):
        client = Client()

        with mock.patch.object(client, "hashtag_medias_v1_chunk", return_value=(["m1"], "next-page")) as chunk:
            medias, end_cursor = client.hashtag_medias_paginated_v1(
                "#python",
                amount=2,
                tab_key="recent",
                end_cursor="cursor-1",
            )

        chunk.assert_called_once_with("python", max_amount=2, tab_key="recent", max_id="cursor-1")
        self.assertEqual(medias, ["m1"])
        self.assertEqual(end_cursor, "next-page")

    def test_authorized_hashtag_medias_paginated_uses_private_before_public(self):
        client = Client()
        client.authorization_data = {"sessionid": "sid"}

        with mock.patch.object(client, "hashtag_medias_paginated_v1", return_value=(["m1"], "next-page")) as v1:
            with mock.patch.object(client, "hashtag_medias_paginated_gql") as gql:
                medias, end_cursor = client.hashtag_medias_paginated("python", amount=5, end_cursor="cursor-1")

        v1.assert_called_once_with("python", amount=5, tab_key="recent", end_cursor="cursor-1")
        gql.assert_not_called()
        self.assertEqual(medias, ["m1"])
        self.assertEqual(end_cursor, "next-page")

    def test_hashtag_medias_paginated_falls_back_to_private(self):
        client = Client()

        with mock.patch.object(
            client, "hashtag_medias_paginated_gql", side_effect=ClientError("public unavailable")
        ) as gql:
            with mock.patch.object(client, "hashtag_medias_paginated_v1", return_value=(["m1"], "next-page")) as v1:
                medias, end_cursor = client.hashtag_medias_paginated("python", amount=5, end_cursor="cursor-1")

        gql.assert_called_once_with("python", amount=5, end_cursor="cursor-1")
        v1.assert_called_once_with("python", amount=5, tab_key="recent", end_cursor="cursor-1")
        self.assertEqual(medias, ["m1"])
        self.assertEqual(end_cursor, "next-page")

    def test_iter_hashtag_medias_streams_paginated_pages_and_respects_amount(self):
        client = Client()
        medias = [
            Media(
                pk=str(i),
                id=f"{i}_1",
                code=f"code-{i}",
                taken_at=datetime.now(UTC()),
                media_type=1,
                user=UserShort(pk="1", username="example"),
                like_count=0,
                caption_text="",
                usertags=[],
                sponsor_tags=[],
            )
            for i in range(1, 5)
        ]

        with mock.patch.object(
            client,
            "hashtag_medias_paginated",
            side_effect=[(medias[:2], "cursor-1"), (medias[2:], "cursor-2")],
        ) as paginated:
            result = list(client.iter_hashtag_medias("python", amount=3, page_size=2, tab_key="recent"))

        self.assertEqual([media.pk for media in result], ["1", "2", "3"])
        paginated.assert_has_calls(
            [
                mock.call("python", amount=2, tab_key="recent", end_cursor=None),
                mock.call("python", amount=1, tab_key="recent", end_cursor="cursor-1"),
            ]
        )
        self.assertEqual(paginated.call_count, 2)

    def test_hashtag_following_fetches_current_account_hashtags(self):
        client = Client()
        client.authorization_data = {"ds_user_id": "123"}
        response = {
            "data": {
                "1$xdt_api__v1__friendships__following(_request_data:$request_data,user_id:$user_id)": {
                    "hashtag_count": 2,
                    "preview_hashtags": [
                        {
                            "id": "17843845123043063",
                            "name": "fotodestages",
                            "media_count": 716293,
                            "profile_pic_url": "https://example.com/fotodestages.jpg",
                        },
                        {
                            "id": "17875609661266431",
                            "name": "coachingbydregold",
                            "media_count": 1,
                            "profile_pic_url": "https://example.com/coachingbydregold.jpg",
                        },
                    ],
                }
            }
        }
        client.private_graphql_following_list = Mock(return_value=response)

        hashtags = client.hashtag_following(amount=1)

        self.assertEqual(len(hashtags), 1)
        self.assertIsInstance(hashtags[0], Hashtag)
        self.assertEqual(hashtags[0].id, "17843845123043063")
        self.assertEqual(hashtags[0].name, "fotodestages")
        self.assertEqual(hashtags[0].media_count, 716293)
        client.private_graphql_following_list.assert_called_once_with(
            "123",
            client.rank_token,
            priority="u=3, i",
            skip_preview_hashtags=False,
            skip_hashtag_count=False,
        )
