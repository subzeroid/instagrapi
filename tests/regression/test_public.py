from instagrapi.exceptions import ClientForbiddenError, ClientLoginRequired, ClientNotFoundError
from instagrapi.mixins.public import JSONDecodeError as PublicJSONDecodeError
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
        self.assertIn("Instagram 273.0.0.16.70", kwargs["headers"]["User-Agent"])
        self.assertFalse(kwargs["update_headers"])
        self.assertTrue(kwargs["return_json"])

    def test_public_doc_id_graphql_request_posts_web_api_with_lsd(self):
        client = Client()
        client.public.cookies.set("csrftoken", "csrf-token")
        html = '<html><script>["LSD",[],{"token":"lsd-token"}]</script></html>'

        with mock.patch.object(
            client,
            "public_request",
            side_effect=[html, {"data": {"ok": True}}],
        ) as public_request:
            data = client.public_doc_id_graphql_request(
                "27128499623469141",
                {"shortcode": "DaHEdwgogl4"},
                referer="https://www.instagram.com/p/DaHEdwgogl4/",
                url=client.GRAPHQL_PUBLIC_WEB_API_URL,
                include_lsd=True,
                headers={"X-FB-Friendly-Name": "PolarisPostRootQuery"},
            )

        self.assertEqual(data, {"ok": True})
        bootstrap_call, query_call = public_request.call_args_list
        self.assertEqual(bootstrap_call.args[0], "https://www.instagram.com/p/DaHEdwgogl4/")
        self.assertFalse(bootstrap_call.kwargs["return_json"])
        self.assertEqual(query_call.args[0], client.GRAPHQL_PUBLIC_WEB_API_URL)
        kwargs = query_call.kwargs
        self.assertEqual(kwargs["data"]["doc_id"], "27128499623469141")
        self.assertEqual(kwargs["data"]["variables"], '{"shortcode":"DaHEdwgogl4"}')
        self.assertEqual(kwargs["data"]["lsd"], "lsd-token")
        self.assertEqual(kwargs["headers"]["X-FB-LSD"], "lsd-token")
        self.assertEqual(kwargs["headers"]["X-CSRFToken"], "csrf-token")
        self.assertEqual(kwargs["headers"]["X-FB-Friendly-Name"], "PolarisPostRootQuery")
        self.assertEqual(kwargs["headers"]["X-IG-App-ID"], "936619743392459")
        self.assertFalse(kwargs["update_headers"])
        self.assertTrue(kwargs["return_json"])

    def test_public_request_maps_challenge_redirect_html_to_login_required(self):
        client = Client()
        client.request_timeout = 0
        client.last_response_ts = 0
        response = Mock()
        response.headers = {"Content-Length": "0"}
        response.raw.tell.return_value = 0
        response.status_code = 200
        response.url = "https://www.instagram.com/challenge/?next=/graphql/query/"
        response.text = '<!DOCTYPE html><html lang="en" class="no-js logged-in client-root"></html>'
        response.raise_for_status.return_value = None
        response.json.side_effect = PublicJSONDecodeError("bad", response.text, 0)

        with mock.patch.object(client.public, "get", return_value=response):
            with self.assertRaises(ClientLoginRequired):
                client._send_public_request("https://www.instagram.com/graphql/query/", return_json=True)

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

    def test_public_doc_id_graphql_request_raises_when_data_is_null(self):
        client = Client()
        body = {
            "data": None,
            "errors": [
                {
                    "summary": "Login required",
                    "description": "Anonymous GraphQL access is blocked.",
                }
            ],
            "status": "ok",
        }

        with mock.patch.object(client, "public_request", return_value=body):
            with self.assertRaises(ClientGraphqlError) as cm:
                client.public_doc_id_graphql_request(
                    "8845758582119845",
                    {"shortcode": "DaHEdwgogl4"},
                )

        self.assertIn("Missing 'data' in doc_id GraphQL response", str(cm.exception))
        self.assertIn("Login required", str(cm.exception))

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

    def test_media_info_gql_does_not_fallback_to_private_when_doc_id_is_unauthorized(self):
        client = Client()

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
                with mock.patch.object(
                    client, "media_info_v1", side_effect=AssertionError("private fallback")
                ) as fallback:
                    with self.assertRaises(ClientForbiddenError):
                        client.media_info_gql("2110901750722920960")

        fallback.assert_not_called()

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
            "caption_is_edited": True,
            "dimensions": {"height": 1916, "width": 1080},
            "has_audio": True,
            "like_and_view_counts_disabled": True,
            "viewer_can_reshare": True,
            "viewer_has_saved": True,
            "is_paid_partnership": True,
            "is_affiliate": True,
            "dash_info": {
                "is_dash_eligible": False,
                "video_dash_manifest": None,
                "number_of_qualities": 0,
            },
            "clips_music_attribution_info": {
                "artist_name": "example",
                "song_name": "Original audio",
                "uses_original_audio": True,
                "should_mute_audio": False,
                "should_mute_audio_reason": "",
                "audio_id": "1192260532058807",
            },
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
            "27128499623469141",
            {
                "shortcode": "B1LbfVPlwIA",
                "__relay_internal__pv__PolarisAIGMMediaWebLabelEnabledrelayprovider": False,
            },
            referer="https://www.instagram.com/p/B1LbfVPlwIA/",
            url=client.GRAPHQL_PUBLIC_WEB_API_URL,
            include_lsd=True,
            headers={"X-FB-Friendly-Name": "PolarisPostRootQuery"},
        )
        self.assertEqual(media.media_type, 2)
        self.assertEqual(media.comment_count, 3)
        self.assertEqual(media.like_count, -1)
        self.assertEqual(media.play_count, 22346)
        self.assertEqual(media.view_count, 7694)
        self.assertFalse(media.has_liked)
        self.assertTrue(media.caption_is_edited)
        self.assertEqual(media.dimensions.height, 1916)
        self.assertEqual(media.dimensions.width, 1080)
        self.assertTrue(media.has_audio)
        self.assertTrue(media.like_and_view_counts_disabled)
        self.assertTrue(media.viewer_can_reshare)
        self.assertTrue(media.viewer_has_saved)
        self.assertTrue(media.is_paid_partnership)
        self.assertTrue(media.is_affiliate)
        self.assertFalse(media.dash_info.is_dash_eligible)
        self.assertEqual(media.dash_info.number_of_qualities, 0)
        self.assertEqual(media.clips_music_attribution_info.artist_name, "example")
        self.assertTrue(media.clips_music_attribution_info.uses_original_audio)

    def test_media_info_gql_extracts_current_web_info_payload(self):
        client = Client()
        media_payload = {
            "pk": "3929128837042014584",
            "id": "3929128837042014584_1713591624",
            "code": "DaHEdwgogl4",
            "taken_at": 1782608696,
            "media_type": 2,
            "product_type": "clips",
            "user": {
                "id": "1713591624",
                "username": "example",
                "profile_pic_url": "https://example.com/profile.jpg",
                "is_private": False,
            },
            "image_versions2": {
                "candidates": [
                    {
                        "url": "https://example.com/thumbnail.jpg",
                        "width": 720,
                        "height": 1280,
                    }
                ]
            },
            "video_versions": [
                {
                    "url": "https://example.com/video.mp4",
                    "width": 720,
                    "height": 1280,
                    "type": 101,
                }
            ],
            "caption": {"text": "#suomi"},
            "comment_count": 1114,
            "like_count": 113000,
            "view_count": 200000,
            "play_count": 210000,
            "has_liked": False,
            "has_viewer_saved": True,
        }

        with mock.patch.object(
            client,
            "public_graphql_request",
            side_effect=ClientUnauthorizedError("401", response=Mock(status_code=401)),
        ):
            with mock.patch.object(
                client,
                "public_doc_id_graphql_request",
                return_value={"xdt_api__v1__media__shortcode__web_info": {"items": [media_payload]}},
            ) as doc_id_request:
                media = client.media_info_gql("3929128837042014584")

        doc_id_request.assert_called_once_with(
            "27128499623469141",
            {
                "shortcode": "DaHEdwgogl4",
                "__relay_internal__pv__PolarisAIGMMediaWebLabelEnabledrelayprovider": False,
            },
            referer="https://www.instagram.com/p/DaHEdwgogl4/",
            url=client.GRAPHQL_PUBLIC_WEB_API_URL,
            include_lsd=True,
            headers={"X-FB-Friendly-Name": "PolarisPostRootQuery"},
        )
        self.assertEqual(media.pk, "3929128837042014584")
        self.assertEqual(media.id, "3929128837042014584_1713591624")
        self.assertEqual(media.code, "DaHEdwgogl4")
        self.assertEqual(media.media_type, 2)
        self.assertEqual(media.product_type, "clips")
        self.assertEqual(media.user.pk, "1713591624")
        self.assertEqual(str(media.thumbnail_url), "https://example.com/thumbnail.jpg")
        self.assertEqual(str(media.video_url), "https://example.com/video.mp4")
        self.assertEqual(media.caption_text, "#suomi")
        self.assertEqual(media.comment_count, 1114)
        self.assertEqual(media.like_count, 113000)
        self.assertEqual(media.view_count, 200000)
        self.assertEqual(media.play_count, 210000)
        self.assertFalse(media.has_liked)

    def test_media_info_gql_normalizes_xdt_sidecar_children(self):
        client = Client()
        child_payload = {
            "__typename": "XDTGraphImage",
            "id": "3150818668564738953",
            "shortcode": "Cu59OMFPQde",
            "display_url": "https://example.com/child.jpg",
            "edge_media_to_tagged_user": {"edges": []},
        }
        media_payload = {
            "__typename": "XDTGraphSidecar",
            "id": "3150818670205011806",
            "shortcode": "Cu59OMFPQde",
            "taken_at_timestamp": 1690160400,
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
            "is_video": False,
            "edge_media_preview_comment": {"count": 3, "edges": []},
            "edge_media_preview_like": {"count": -1, "edges": []},
            "edge_media_to_caption": {"edges": [{"node": {"text": "caption"}}]},
            "edge_media_to_tagged_user": {"edges": []},
            "edge_media_to_sponsor_user": {"edges": []},
            "edge_sidecar_to_children": {"edges": [{"node": child_payload}]},
            "viewer_has_liked": False,
        }

        with mock.patch.object(
            client,
            "public_graphql_request",
            side_effect=ClientForbiddenError("blocked", response=Mock(status_code=403)),
        ):
            with mock.patch.object(
                client,
                "public_doc_id_graphql_request",
                return_value={"xdt_shortcode_media": media_payload},
            ):
                media = client.media_info_gql("3150818670205011806")

        self.assertEqual(media.media_type, 8)
        self.assertEqual(media.pk, "3150818670205011806")
        self.assertEqual(len(media.resources), 1)
        self.assertEqual(media.resources[0].media_type, 1)
        self.assertEqual(str(media.resources[0].thumbnail_url), "https://example.com/child.jpg")

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
    def test_send_private_request_ignores_non_json_body_on_http_error(self):
        client = Client()
        client.request_timeout = 0
        client.authorization_data = {"ds_user_id": "1"}
        response = Mock()
        response.status_code = 404
        response.content = b"<html>not json</html>"
        response.headers = {}
        response.url = "https://i.instagram.com/api/v1/nonexistent/"
        response.text = response.content.decode("utf-8")
        response.request = Mock(method="GET")
        response.json.side_effect = ValueError("bad json")
        response.raise_for_status.side_effect = requests.HTTPError(response=response)

        with mock.patch.object(client.private, "get", return_value=response):
            with self.assertRaises(ClientNotFoundError):
                client._send_private_request("nonexistent/")

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

    def test_private_graphql_request_accepts_incremental_json_lines(self):
        client = Client()
        client.request_timeout = 0
        data = {
            "fb_api_req_friendly_name": "ExampleQuery",
            "variables": "{}",
        }
        response = Mock()
        response.url = "https://i.instagram.com/graphql/query"
        response.text = (
            '{"data":{"timeline":{"items":[{"media":{"id":"1"}}]}},"status":"ok"}\n'
            '{"path":["timeline","items",0,"media"],"data":{"code":"abc"}}\n'
        )
        response.json.side_effect = JSONDecodeError("Extra data", response.text, 68)
        response.raise_for_status.return_value = None

        with mock.patch.object(client, "request_log"):
            with mock.patch.object(client.private, "post", return_value=response):
                result = client.private_graphql_request(data)

        self.assertEqual(result["data"]["timeline"]["items"][0]["media"]["id"], "1")
        self.assertEqual(result["data"]["timeline"]["items"][0]["media"]["code"], "abc")

    def test_private_graphql_www_request_posts_to_app_graphql_www_endpoint(self):
        client = Client()
        client.request_timeout = 0
        variables = {"params": {"app_id": "com.example.app"}}
        response = Mock()
        response.url = "https://b.i.instagram.com/graphql_www"
        response.json.return_value = {"data": {"ok": True}}
        response.raise_for_status.return_value = None

        with mock.patch.object(client, "request_log") as request_log:
            with mock.patch.object(client.private, "post", return_value=response) as post:
                result = client.private_graphql_www_request(
                    "IGBloksAppRootQuery-com.example.app",
                    variables,
                    client_doc_id="doc-id",
                )

        self.assertEqual(result, {"data": {"ok": True}})
        data = post.call_args.kwargs["data"]
        self.assertEqual(post.call_args.args, ("https://b.i.instagram.com/graphql_www",))
        self.assertEqual(data["purpose"], "fetch")
        self.assertEqual(data["fb_api_req_friendly_name"], "IGBloksAppRootQuery-com.example.app")
        self.assertEqual(data["client_doc_id"], "doc-id")
        self.assertEqual(json.loads(data["variables"]), variables)
        self.assertEqual(post.call_args.kwargs["headers"]["X-FB-Friendly-Name"], "IGBloksAppRootQuery-com.example.app")
        self.assertEqual(post.call_args.kwargs["headers"]["X-Client-Doc-Id"], "doc-id")
        self.assertEqual(post.call_args.kwargs["headers"]["Host"], "b.i.instagram.com")
        self.assertEqual(post.call_args.kwargs["proxies"], client.private.proxies)
        request_log.assert_called_once_with(response)
