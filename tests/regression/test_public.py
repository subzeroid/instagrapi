from instagrapi.exceptions import ClientForbiddenError, ClientNotFoundError
from tests.helpers import *


class PublicRegressionTestCase(unittest.TestCase):
    def test_public_request_uses_post_for_post_bodies(self):
        client = Client()
        response = Mock()
        response.headers = {"Content-Length": "0"}
        response.raw.tell.return_value = 0
        response.status_code = 200
        response.url = "https://www.instagram.com/api/graphql"
        response.json.return_value = {"status": "ok", "data": {"user": {}}}
        response.raise_for_status.return_value = None

        with mock.patch.object(client.public, "post", return_value=response) as post:
            body = client.public_request(
                "https://www.instagram.com/api/graphql",
                data={"doc_id": "1"},
                return_json=True,
            )

        self.assertEqual(body["status"], "ok")
        post.assert_called_once()

    def test_public_request_passes_non_persistent_headers_per_request(self):
        client = Client()
        response = Mock()
        response.headers = {"Content-Length": "0"}
        response.raw.tell.return_value = 0
        response.status_code = 200
        response.url = "https://www.instagram.com/graphql/query/"
        response.json.return_value = {"status": "ok", "data": {"media": {}}}
        response.raise_for_status.return_value = None

        headers = {"User-Agent": "temporary-agent"}
        original_user_agent = client.public.headers.get("User-Agent")
        with mock.patch.object(client.public, "post", return_value=response) as post:
            client.public_request(
                "https://www.instagram.com/graphql/query/",
                data={"doc_id": "1"},
                headers=headers,
                update_headers=False,
                return_json=True,
            )

        post.assert_called_once()
        self.assertEqual(post.call_args.kwargs["headers"], headers)
        self.assertEqual(client.public.headers.get("User-Agent"), original_user_agent)

    def test_public_doc_id_graphql_request_posts_doc_id_form(self):
        client = Client()

        with mock.patch.object(client, "public_request", return_value={"data": {"ok": True}}) as public_request:
            data = client.public_doc_id_graphql_request(
                "8845758582119845",
                {"shortcode": "C_BM2yAN4Rm"},
                referer="https://www.instagram.com/p/C_BM2yAN4Rm/",
            )

        self.assertEqual(data, {"ok": True})
        public_request.assert_called_once()
        kwargs = public_request.call_args.kwargs
        self.assertEqual(kwargs["data"]["doc_id"], "8845758582119845")
        self.assertEqual(kwargs["data"]["variables"], '{"shortcode":"C_BM2yAN4Rm"}')
        self.assertEqual(kwargs["data"]["server_timestamps"], "true")
        self.assertEqual(kwargs["headers"]["Referer"], "https://www.instagram.com/p/C_BM2yAN4Rm/")
        self.assertFalse(kwargs["update_headers"])
        self.assertTrue(kwargs["return_json"])

    def test_public_graphql_request_raises_client_graphql_error_when_data_missing(self):
        client = Client()
        body = {
            "errors": [
                {
                    "message": "execution error",
                    "summary": "Incorrect Query",
                    "description": "The query provided was invalid.",
                }
            ],
            "status": "ok",
        }

        with mock.patch.object(client, "public_request", return_value=body):
            with self.assertRaises(ClientGraphqlError) as cm:
                client.public_graphql_request(
                    {"user_id": "123", "include_reel": True},
                    query_hash="ad99dd9d3646cc3c0dda65debcd266a7",
                )

        self.assertIn("Missing 'data' in GraphQL response", str(cm.exception))
        self.assertIn("Incorrect Query", str(cm.exception))

    def test_user_stories_anonymous_does_not_fallback_to_private(self):
        client = Client()

        with mock.patch.object(
            client,
            "user_stories_gql",
            side_effect=ClientGraphqlError("Incorrect Query"),
        ):
            with mock.patch.object(client, "user_stories_v1") as private_fallback:
                with self.assertRaises(ClientGraphqlError) as cm:
                    client.user_stories("4776134209", amount=5)

        private_fallback.assert_not_called()
        self.assertIn("Incorrect Query", str(cm.exception))

    def test_media_info_gql_falls_back_to_a1_when_doc_id_is_unauthorized(self):
        client = Client()
        expected = Mock(spec=Media)

        with mock.patch.object(
            client,
            "public_graphql_request",
            side_effect=ClientUnauthorizedError("401", response=Mock(status_code=401)),
        ):
            with mock.patch.object(
                client,
                "public_doc_id_graphql_request",
                side_effect=ClientForbiddenError("403", response=Mock(status_code=403)),
            ):
                with mock.patch.object(client, "media_info_a1", return_value=expected) as fallback:
                    result = client.media_info_gql("2110901750722920960")

        self.assertIs(result, expected)
        fallback.assert_called_once_with("2110901750722920960")

    def test_media_info_gql_falls_back_to_doc_id_on_public_404(self):
        client = Client()
        media_payload = {
            "__typename": "XDTGraphVideo",
            "id": "2110901750722920960",
            "shortcode": "B1LbfVPlwIA",
            "taken_at_timestamp": 1565796000,
            "owner": {
                "id": "1903424587",
                "username": "example",
                "profile_pic_url": "https://example.com/profile.jpg",
                "is_private": False,
            },
            "display_resources": [
                {
                    "src": "https://example.com/thumbnail.jpg",
                    "config_width": 360,
                    "config_height": 640,
                }
            ],
            "product_type": "clips",
            "is_video": True,
            "video_url": "https://example.com/video.mp4",
            "video_duration": 13.3,
            "video_view_count": 7694,
            "video_play_count": 22346,
            "edge_media_preview_comment": {"count": 3, "edges": []},
            "edge_media_preview_like": {"count": -1, "edges": []},
            "edge_media_to_caption": {"edges": [{"node": {"text": "caption"}}]},
            "edge_media_to_tagged_user": {"edges": []},
            "edge_media_to_sponsor_user": {"edges": []},
            "viewer_has_liked": False,
        }

        with mock.patch.object(
            client,
            "public_graphql_request",
            side_effect=ClientNotFoundError("404", response=Mock(status_code=404)),
        ):
            with mock.patch.object(
                client,
                "public_doc_id_graphql_request",
                return_value={"xdt_shortcode_media": media_payload},
            ) as doc_id_request:
                media = client.media_info_gql("2110901750722920960")

        doc_id_request.assert_called_once_with(
            "8845758582119845",
            {"shortcode": "B1LbfVPlwIA"},
            referer="https://www.instagram.com/p/B1LbfVPlwIA/",
        )
        self.assertEqual(media.media_type, 2)
        self.assertEqual(media.comment_count, 3)
        self.assertEqual(media.like_count, -1)
        self.assertEqual(media.play_count, 22346)
        self.assertEqual(media.view_count, 7694)
        self.assertFalse(media.has_liked)

    def test_public_head_defaults_to_no_redirect_follow(self):
        client = Client()
        before = client.public_requests_count
        response = Mock(status_code=302, headers={"location": "https://target/"})

        with mock.patch.object(client.public, "head", return_value=response) as head:
            result = client.public_head("https://instagram.com/share/abc")

        self.assertIs(result, response)
        self.assertEqual(client.public_requests_count, before + 1)
        head.assert_called_once()
        kwargs = head.call_args.kwargs
        self.assertFalse(kwargs["allow_redirects"])

    def test_public_head_follow_redirects_override(self):
        client = Client()
        response = Mock(status_code=200)

        with mock.patch.object(client.public, "head", return_value=response) as head:
            client.public_head("https://instagram.com/share/abc", follow_redirects=True)

        kwargs = head.call_args.kwargs
        self.assertTrue(kwargs["allow_redirects"])


class PrivateGraphQLRequestRegressionTestCase(unittest.TestCase):
    def test_private_graphql_request_posts_to_app_graphql_endpoint(self):
        client = Client()
        client.request_timeout = 0
        data = {
            "fb_api_req_friendly_name": "ExampleQuery",
            "variables": "{}",
        }
        response = Mock()
        response.url = "https://i.instagram.com/graphql/query"
        response.json.return_value = {"data": {"ok": True}}
        response.raise_for_status.return_value = None

        with mock.patch.object(client, "request_log") as request_log:
            with mock.patch.object(client.private, "post", return_value=response) as post:
                result = client.private_graphql_request(data)

        self.assertEqual(result, {"data": {"ok": True}})
        post.assert_called_once_with(
            "https://i.instagram.com/graphql/query",
            data=data,
            proxies=client.private.proxies,
        )
        request_log.assert_called_once_with(response)
        self.assertEqual(client.private.headers["X-FB-Friendly-Name"], "ExampleQuery")
        self.assertEqual(
            client.private.headers["Content-Type"],
            "application/x-www-form-urlencoded; charset=UTF-8",
        )
