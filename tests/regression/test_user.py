from tests.helpers import *


class UserMixinRegressionTestCase(unittest.TestCase):
    def build_private_client(self):
        client = Client()
        client.settings = {}
        client.authorization_data = {"ds_user_id": "1"}
        client.uuid = "uuid"
        return client

    @staticmethod
    def build_web_profile_user(**overrides):
        user = {
            "id": "123",
            "username": "example",
            "full_name": "Example",
            "is_private": False,
            "is_verified": False,
            "profile_pic_url_hd": None,
            "profile_pic_url": "https://example.com/pic.jpg",
            "edge_owner_to_timeline_media": {"count": 0},
            "edge_followed_by": {"count": 0},
            "edge_follow": {"count": 0},
            "is_business_account": False,
            "business_email": None,
            "business_phone_number": None,
            "biography": "",
            "bio_links": [],
            "external_url": None,
            "business_category_name": None,
            "category_name": None,
            "fbid": "123",
            "pinned_channels_info": {"pinned_channels_list": []},
        }
        user.update(overrides)
        return {"data": {"user": user}}

    def test_user_short_gql_falls_back_to_web_profile_graphql(self):
        client = Client()
        web_user = {
            "id": "25025320",
            "username": "instagram",
            "full_name": "Instagram",
            "is_private": False,
            "profile_pic_url": "https://example.com/pic.jpg",
        }

        with mock.patch.object(
            client,
            "public_graphql_request",
            side_effect=ClientGraphqlError("Incorrect Query"),
        ):
            with mock.patch.object(client, "user_web_profile_info_gql", return_value=web_user) as fallback:
                user = client.user_short_gql("25025320", use_cache=False)

        self.assertEqual(user.username, "instagram")
        fallback.assert_called_once_with("25025320")

    def test_user_short_gql_uses_web_profile_doc_id_without_legacy_query_hash(self):
        client = Client()
        web_user = {
            "id": "25025320",
            "username": "instagram",
            "full_name": "Instagram",
            "is_private": False,
            "profile_pic_url": "https://example.com/pic.jpg",
        }

        with mock.patch.object(
            client,
            "public_graphql_request",
            side_effect=AssertionError("legacy query_hash should not be used"),
        ) as legacy_query:
            with mock.patch.object(client, "user_web_profile_info_gql", return_value=web_user) as profile_query:
                user = client.user_short_gql("25025320", use_cache=False)

        self.assertEqual(user.username, "instagram")
        profile_query.assert_called_once_with("25025320")
        legacy_query.assert_not_called()

    def test_user_web_profile_info_gql_uses_public_doc_id_endpoint(self):
        client = Client()
        client._fb_dtsg = "token"
        web_user = {
            "id": "25025320",
            "username": "instagram",
            "full_name": "Instagram",
            "is_private": False,
            "profile_pic_url": "https://example.com/pic.jpg",
        }

        with mock.patch.object(client, "inject_sessionid_to_public", return_value=True):
            with mock.patch.object(
                client,
                "public_request",
                side_effect=AssertionError("legacy /api/graphql endpoint should not be used"),
            ):
                with mock.patch.object(
                    client,
                    "public_doc_id_graphql_request",
                    return_value={"user": web_user},
                ) as doc_id_request:
                    user = client.user_web_profile_info_gql("25025320")

        self.assertEqual(user["username"], "instagram")
        doc_id_request.assert_called_once()
        args, kwargs = doc_id_request.call_args
        self.assertEqual(args[0], "26762473490008061")
        self.assertEqual(args[1]["id"], "25025320")
        self.assertEqual(args[1]["render_surface"], "PROFILE")
        self.assertEqual(kwargs["referer"], "https://www.instagram.com/25025320/")

    def test_user_info_by_username_gql_parses_web_profile_without_update_headers_kwarg(
        self,
    ):
        class DummyClient(UserMixin):
            response_body = None

            def __init__(self):
                self.public_request_calls = []

            def public_request(self, url, headers=None, **kwargs):
                self.public_request_calls.append({"url": url, "headers": headers, "kwargs": kwargs})
                return json.dumps(self.response_body)

        client = DummyClient()
        client.response_body = self.build_web_profile_user()
        user = client.user_info_by_username_gql("Example")
        self.assertEqual(user.pk, "123")
        self.assertEqual(user.username, "example")
        self.assertEqual(len(client.public_request_calls), 1)
        self.assertEqual(client.public_request_calls[0]["kwargs"], {})
        self.assertIn("web_profile_info/?username=example", client.public_request_calls[0]["url"])

    def test_user_info_by_username_suppresses_traceback_for_public_retry_error(self):
        client = Client()
        client._usernames_cache = {}
        client._users_cache = {}
        client.logger = Mock()
        fallback_user = User(
            pk="123",
            username="example",
            full_name="Example",
            is_private=False,
            is_verified=False,
            profile_pic_url="https://example.com/pic.jpg",
            media_count=0,
            follower_count=0,
            following_count=0,
            is_business=False,
        )

        with mock.patch.object(
            client,
            "user_info_by_username_gql",
            side_effect=RetryError("too many 429 error responses"),
        ):
            with mock.patch.object(client, "user_info_by_username_v1", return_value=fallback_user) as fallback:
                with mock.patch.object(client, "user_info", return_value=fallback_user) as user_info:
                    user = client.user_info_by_username("Example", use_cache=False)

        self.assertEqual(user.pk, "123")
        fallback.assert_called_once_with("example")
        user_info.assert_called_once_with("123")
        client.logger.exception.assert_not_called()
        client.logger.warning.assert_called_once()

    def test_user_info_by_username_gql_handles_missing_pinned_channels_info(self):
        class DummyClient(UserMixin):
            response_body = None

            def public_request(self, url, headers=None, **kwargs):
                return json.dumps(self.response_body)

        client = DummyClient()
        client.response_body = self.build_web_profile_user()
        client.response_body["data"]["user"].pop("pinned_channels_info")

        user = client.user_info_by_username_gql("Example")

        self.assertEqual(user.broadcast_channel, [])

    def test_user_info_by_username_gql_handles_bio_links_without_link_id(self):
        class DummyClient(UserMixin):
            response_body = None

            def public_request(self, url, headers=None, **kwargs):
                return json.dumps(self.response_body)

        client = DummyClient()
        client.response_body = self.build_web_profile_user(
            bio_links=[{"url": "https://example.com", "title": "Example"}]
        )

        user = client.user_info_by_username_gql("Example")

        self.assertEqual(len(user.bio_links), 1)
        self.assertIsNone(user.bio_links[0].link_id)
        self.assertEqual(user.bio_links[0].url, "https://example.com")

    def test_user_followers_v1_chunk_omits_empty_max_id_on_first_page(self):
        client = self.build_private_client()

        with mock.patch.object(
            client,
            "private_request",
            return_value={"users": [], "next_max_id": None},
        ) as private_request:
            client.user_followers_v1_chunk("123")

        params = private_request.call_args.kwargs["params"]
        self.assertNotIn("max_id", params)

    def test_user_followers_v1_chunk_sends_non_empty_max_id_on_next_page(self):
        client = self.build_private_client()

        with mock.patch.object(
            client,
            "private_request",
            return_value={"users": [], "next_max_id": None},
        ) as private_request:
            client.user_followers_v1_chunk("123", max_id="cursor")

        params = private_request.call_args.kwargs["params"]
        self.assertEqual(params["max_id"], "cursor")

    def test_user_following_v1_chunk_omits_empty_max_id_on_first_page(self):
        client = self.build_private_client()

        with mock.patch.object(
            client,
            "private_request",
            return_value={"users": [], "next_max_id": None},
        ) as private_request:
            client.user_following_v1_chunk("123")

        params = private_request.call_args.kwargs["params"]
        self.assertNotIn("max_id", params)

    def test_user_follow_requests_chunk_fetches_pending_users(self):
        client = self.build_private_client()

        with mock.patch.object(
            client,
            "private_request",
            return_value={
                "users": [
                    {
                        "pk": "42",
                        "username": "pending",
                        "full_name": "Pending User",
                        "profile_pic_url": None,
                    }
                ],
                "next_max_id": "next",
            },
        ) as private_request:
            users, next_max_id = client.user_follow_requests_chunk(max_amount=1)

        self.assertEqual(next_max_id, "next")
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].pk, "42")
        private_request.assert_called_once_with(
            "friendships/pending/",
            params={"count": 1},
        )

    def test_user_follow_requests_chunk_sends_non_empty_max_id(self):
        client = self.build_private_client()

        with mock.patch.object(
            client,
            "private_request",
            return_value={"users": [], "next_max_id": None},
        ) as private_request:
            client.user_follow_requests_chunk(max_amount=20, max_id="cursor")

        private_request.assert_called_once_with(
            "friendships/pending/",
            params={"count": 20, "max_id": "cursor"},
        )

    def test_user_follow_request_approve_posts_action_data_and_returns_status(self):
        client = self.build_private_client()

        with mock.patch.object(
            client,
            "private_request",
            return_value={"friendship_status": {"followed_by": True}},
        ) as private_request:
            result = client.user_follow_request_approve("42")

        self.assertTrue(result)
        endpoint, data = private_request.call_args.args
        self.assertEqual(endpoint, "friendships/approve/42/")
        self.assertEqual(data["user_id"], "42")

    def test_user_follow_request_decline_posts_action_data_and_returns_status(self):
        client = self.build_private_client()

        with mock.patch.object(
            client,
            "private_request",
            return_value={"friendship_status": {"followed_by": False}},
        ) as private_request:
            result = client.user_follow_request_decline("42")

        self.assertTrue(result)
        endpoint, data = private_request.call_args.args
        self.assertEqual(endpoint, "friendships/ignore/42/")
        self.assertEqual(data["user_id"], "42")

    def test_user_follow_requests_approve_batches_results(self):
        client = self.build_private_client()

        with mock.patch.object(
            client,
            "user_follow_request_approve",
            side_effect=[True, False],
        ) as approve:
            result = client.user_follow_requests_approve(["1", "2"])

        self.assertEqual(result, {"1": True, "2": False})
        approve.assert_has_calls([mock.call("1"), mock.call("2")])

    def test_user_follow_requests_decline_batches_results(self):
        client = self.build_private_client()

        with mock.patch.object(
            client,
            "user_follow_request_decline",
            side_effect=[False, True],
        ) as decline:
            result = client.user_follow_requests_decline(["1", "2"])

        self.assertEqual(result, {"1": False, "2": True})
        decline.assert_has_calls([mock.call("1"), mock.call("2")])

    def test_chaining_sends_expected_params_and_returns_payload(self):
        client = Client()
        expected = {"users": [{"pk": "9", "username": "suggested"}]}

        with mock.patch.object(client, "private_request", return_value=expected) as private_request:
            result = client.chaining("123")

        self.assertEqual(result, expected)
        private_request.assert_called_once_with(
            "discover/chaining/",
            params={
                "module": "profile",
                "target_id": "123",
                "profile_chaining_check": "false",
                "eligible_for_threads_cta": "false",
            },
        )

    def test_chaining_promotes_not_eligible_unknown_error(self):
        from instagrapi.exceptions import InvalidTargetUser

        client = Client()

        with mock.patch.object(
            client,
            "private_request",
            side_effect=UnknownError("Not eligible for chaining."),
        ):
            with self.assertRaises(InvalidTargetUser) as cm:
                client.chaining("123")

        self.assertIn("Not eligible for chaining.", str(cm.exception))

    def test_chaining_reraises_other_unknown_errors(self):
        client = Client()

        with mock.patch.object(
            client,
            "private_request",
            side_effect=UnknownError("Some other failure"),
        ):
            with self.assertRaises(UnknownError):
                client.chaining("123")

    def test_fetch_suggestion_details_sends_expected_params(self):
        client = Client()
        expected = {"users": []}

        with mock.patch.object(client, "private_request", return_value=expected) as private_request:
            result = client.fetch_suggestion_details("123", "9,10,11")

        self.assertEqual(result, expected)
        private_request.assert_called_once_with(
            "discover/fetch_suggestion_details/",
            params={
                "target_id": "123",
                "chained_ids": "9,10,11",
                "include_social_context": "1",
            },
        )

    def test_user_stream_by_id_v1_sends_expected_endpoint_and_data(self):
        client = Client()
        with mock.patch.object(client, "private_request", return_value={"stream_rows": []}) as private_request:
            client.user_stream_by_id_v1("123")

        private_request.assert_called_once_with(
            "users/123/info_stream/",
            data={
                "is_prefetch": False,
                "entry_point": "profile",
                "from_module": "feed_timeline",
            },
        )

    def test_user_stream_by_id_v1_promotes_not_found_to_user_not_found(self):
        from instagrapi.exceptions import ClientNotFoundError, UserNotFound

        client = Client()
        client.last_json = {}
        with mock.patch.object(
            client,
            "private_request",
            side_effect=ClientNotFoundError("404", response=Mock(status_code=404)),
        ):
            with self.assertRaises(UserNotFound):
                client.user_stream_by_id_v1("123")

    def test_user_stream_by_username_v1_sends_expected_endpoint(self):
        client = Client()
        with mock.patch.object(client, "private_request", return_value={"stream_rows": []}) as private_request:
            client.user_stream_by_username_v1("Example")

        endpoint = private_request.call_args.args[0]
        self.assertEqual(endpoint, "users/example/usernameinfo_stream/")

    def test_user_stream_by_id_flat_merges_rows_and_promotes_pk_id(self):
        client = Client()
        envelope = {
            "stream_rows": [
                {"user": {"pk_id": "9", "username": "alice", "is_private": False}},
                {"user": {"full_name": "Alice Example"}},
                {"user": {"username": "alice2"}},
            ]
        }
        with mock.patch.object(client, "user_stream_by_id_v1", return_value=envelope):
            user = client.user_stream_by_id_flat("9")

        self.assertEqual(user["username"], "alice2")
        self.assertEqual(user["full_name"], "Alice Example")
        self.assertEqual(user["pk"], "9")
        self.assertEqual(user["pk_id"], "9")

    def test_user_stream_by_username_flat_falls_back_when_empty(self):
        client = Client()
        client.last_json = {"sentinel": True}
        with mock.patch.object(client, "user_stream_by_username_v1", return_value={"stream_rows": []}) as stream_call:
            result = client.user_stream_by_username_flat("alice")

        # First call from _flat → empty → collector triggers second.
        self.assertEqual(stream_call.call_count, 2)
        self.assertEqual(result, {"sentinel": True})

    def test_user_web_profile_info_v1_unwraps_data(self):
        client = Client()
        with mock.patch.object(
            client,
            "private_request",
            return_value={"data": {"pk": "9", "username": "alice"}},
        ) as private_request:
            user = client.user_web_profile_info_v1("alice")

        private_request.assert_called_once_with("users/web_profile_info/", params={"username": "alice"})
        self.assertEqual(user, {"pk": "9", "username": "alice"})

    def test_user_web_profile_info_v1_raises_user_not_found_on_empty_data(self):
        from instagrapi.exceptions import UserNotFound

        client = Client()
        client.last_json = {}
        with mock.patch.object(client, "private_request", return_value={"data": {}}):
            with self.assertRaises(UserNotFound):
                client.user_web_profile_info_v1("missing")

    def test_discover_recommended_accounts_extracts_category_id_from_stream(self):
        client = Client()
        stream_resp = {
            "stream_rows": [
                {"user": {"username": "alice"}},
                {"user": {"category_id": 42, "is_business": True}},
            ]
        }

        with mock.patch.object(client, "user_stream_by_id_v1", return_value=stream_resp) as stream:
            with mock.patch.object(client, "private_request", return_value={"users": []}) as private_request:
                client.discover_recommended_accounts_for_category_v1("9")

        stream.assert_called_once_with("9")
        private_request.assert_called_once_with(
            "discover/recommended_accounts_for_category/",
            params={"target_id": "9", "category_id": 42},
        )

    def test_discover_recommended_accounts_falls_through_with_none_category(self):
        client = Client()
        stream_resp = {
            "stream_rows": [
                {"user": {"username": "alice"}},
                {"user": {"is_private": False}},
            ]
        }

        with mock.patch.object(client, "user_stream_by_id_v1", return_value=stream_resp):
            with mock.patch.object(client, "private_request", return_value={"users": []}) as private_request:
                client.discover_recommended_accounts_for_category_v1("9")

        params = private_request.call_args.kwargs["params"]
        self.assertEqual(params["target_id"], "9")
        self.assertIsNone(params["category_id"])

    def test_user_related_profiles_gql_extracts_edge_chaining_nodes(self):
        client = Client()
        gql_resp = {
            "user": {
                "edge_chaining": {
                    "edges": [
                        {
                            "node": {
                                "pk": "1",
                                "username": "alice",
                                "profile_pic_url": "https://example.com/a.jpg",
                                "is_private": False,
                            }
                        },
                        {
                            "node": {
                                "pk": "2",
                                "username": "bob",
                                "profile_pic_url": "https://example.com/b.jpg",
                                "is_private": False,
                            }
                        },
                    ]
                }
            }
        }

        with mock.patch.object(client, "public_graphql_request", return_value=gql_resp):
            users = client.user_related_profiles_gql("9")

        self.assertEqual(len(users), 2)
        self.assertEqual([u.username for u in users], ["alice", "bob"])

    def test_user_related_profiles_gql_raises_user_not_found_on_empty_response(self):
        from instagrapi.exceptions import UserNotFound

        client = Client()
        with mock.patch.object(client, "public_graphql_request", return_value={"user": None}):
            with self.assertRaises(UserNotFound):
                client.user_related_profiles_gql("9")

    def test_user_related_profiles_gql_returns_empty_list_when_no_edges(self):
        client = Client()
        with mock.patch.object(
            client,
            "public_graphql_request",
            return_value={"user": {"edge_chaining": {"edges": []}}},
        ):
            users = client.user_related_profiles_gql("9")

        self.assertEqual(users, [])

    def test_user_related_profiles_gql_raises_when_num_retry_under_threshold(self):
        from instagrapi.exceptions import RelatedProfileRequired

        client = Client()
        # Opt into retry semantics by setting num_retry < 4.
        client.num_retry = 0
        with mock.patch.object(
            client,
            "public_graphql_request",
            return_value={"user": {"edge_chaining": {"edges": []}}},
        ):
            with self.assertRaises(RelatedProfileRequired):
                client.user_related_profiles_gql("9")
