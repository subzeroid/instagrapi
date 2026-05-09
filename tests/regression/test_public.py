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

    def test_media_info_gql_falls_back_to_a1_on_public_401(self):
        client = Client()
        expected = Mock(spec=Media)

        with mock.patch.object(
            client,
            "public_graphql_request",
            side_effect=ClientUnauthorizedError("401", response=Mock(status_code=401)),
        ):
            with mock.patch.object(
                client, "media_info_a1", return_value=expected
            ) as fallback:
                result = client.media_info_gql("2110901750722920960")

        self.assertIs(result, expected)
        fallback.assert_called_once_with("2110901750722920960")

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
            with mock.patch.object(
                client.private, "post", return_value=response
            ) as post:
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
