from instagrapi.extractors import extract_user_short, extract_user_v1
from instagrapi.mixins.user import MAX_USER_COUNT
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

    @staticmethod
    def build_user(**overrides):
        user = {
            "pk": "123",
            "username": "example",
            "full_name": "Example",
            "is_private": False,
            "is_verified": False,
            "profile_pic_url": "https://example.com/pic.jpg",
            "media_count": 0,
            "follower_count": 0,
            "following_count": 0,
            "is_business": False,
        }
        user.update(overrides)
        return User(**user)

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

    def test_extract_user_v1_maps_business_contact_fields(self):
        payload = {
            "pk": "123",
            "username": "business",
            "full_name": "Business",
            "is_private": False,
            "profile_pic_url": "https://example.com/pic.jpg",
            "is_verified": False,
            "media_count": 0,
            "follower_count": 0,
            "following_count": 0,
            "is_business": True,
            "business_email": "public@example.com",
            "business_phone_number": "+15551234567",
            "external_url": "",
        }

        user = extract_user_v1(payload)

        self.assertEqual(user.public_email, "public@example.com")
        self.assertEqual(user.contact_phone_number, "+15551234567")

    def test_extract_user_short_preserves_follower_payload_fields(self):
        payload = {
            "pk": 123,
            "id": "123",
            "username": "follower",
            "full_name": "Follower",
            "is_private": False,
            "is_verified": True,
            "latest_reel_media": 1710000123,
            "has_anonymous_profile_picture": False,
            "profile_pic_url": "https://example.com/pic.jpg",
        }

        user = extract_user_short(payload)

        self.assertEqual(user.pk, "123")
        self.assertTrue(user.is_verified)
        self.assertEqual(user.latest_reel_media, 1710000123)
        self.assertFalse(user.has_anonymous_profile_picture)

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

    def test_user_info_by_username_gql_normalizes_username(self):
        class DummyClient(UserMixin):
            response_body = None

            def __init__(self):
                self.public_request_calls = []

            def public_request(self, url, headers=None, **kwargs):
                self.public_request_calls.append({"url": url, "headers": headers, "kwargs": kwargs})
                return json.dumps(self.response_body)

        client = DummyClient()
        client.response_body = self.build_web_profile_user()

        user = client.user_info_by_username_gql(" @Example ")

        self.assertEqual(user.username, "example")
        self.assertIn("web_profile_info/?username=example", client.public_request_calls[0]["url"])

    def test_user_info_by_username_v1_normalizes_username(self):
        client = Client()
        payload = {
            "user": {
                "pk": "123",
                "username": "example",
                "full_name": "Example",
                "is_private": False,
                "is_verified": False,
                "profile_pic_url": "https://example.com/pic.jpg",
                "media_count": 0,
                "follower_count": 0,
                "following_count": 0,
                "is_business": False,
            }
        }

        with mock.patch.object(client, "private_request", return_value=payload) as private_request:
            user = client.user_info_by_username_v1(" @Example ")

        self.assertEqual(user.username, "example")
        private_request.assert_called_once_with("users/example/usernameinfo/")

    def test_user_info_by_username_uses_normalized_cache_key(self):
        client = Client()
        client._usernames_cache = {}
        client._users_cache = {}
        user = User(
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

        with mock.patch.object(client, "user_info_by_username_gql", return_value=user) as gql:
            with mock.patch.object(client, "user_info", return_value=user):
                client.user_info_by_username("@Example")
                client.user_info_by_username(" example ")

        gql.assert_called_once_with("example")
        self.assertEqual(client._usernames_cache, {"example": "123"})

    def test_authorized_user_info_by_username_uses_private_before_public(self):
        client = self.build_private_client()
        client._usernames_cache = {}
        client._users_cache = {}
        user = self.build_user()

        with mock.patch.object(client, "user_info_by_username_v1", return_value=user) as private_lookup:
            with mock.patch.object(
                client,
                "user_info_by_username_gql",
                side_effect=AssertionError("authorized lookup should use private API first"),
            ) as public_lookup:
                result = client.user_info_by_username("Example", use_cache=False)

        self.assertEqual(result.pk, "123")
        private_lookup.assert_called_once_with("example")
        public_lookup.assert_not_called()

    def test_authorized_user_id_from_username_uses_private_lookup(self):
        client = self.build_private_client()
        client._usernames_cache = {}
        client._users_cache = {}
        user = self.build_user()

        with mock.patch.object(client, "user_info_by_username_v1", return_value=user) as private_lookup:
            with mock.patch.object(
                client,
                "user_info_by_username_gql",
                side_effect=AssertionError("authorized lookup should use private API first"),
            ) as public_lookup:
                user_id = client.user_id_from_username("Example")

        self.assertEqual(user_id, "123")
        private_lookup.assert_called_once_with("example")
        public_lookup.assert_not_called()

    def test_cookie_session_user_info_by_username_uses_private_before_public(self):
        client = Client()
        client.private.cookies.set("sessionid", "1" * 40)
        client._usernames_cache = {}
        client._users_cache = {}
        user = self.build_user()

        with mock.patch.object(client, "user_info_by_username_v1", return_value=user) as private_lookup:
            with mock.patch.object(
                client,
                "user_info_by_username_gql",
                side_effect=AssertionError("cookie session lookup should use private API first"),
            ) as public_lookup:
                result = client.user_info_by_username("Example", use_cache=False)

        self.assertEqual(result.pk, "123")
        private_lookup.assert_called_once_with("example")
        public_lookup.assert_not_called()

    def test_authorized_user_info_by_username_falls_back_to_public(self):
        client = self.build_private_client()
        client._usernames_cache = {}
        client._users_cache = {}
        user = self.build_user()

        with mock.patch.object(
            client,
            "user_info_by_username_v1",
            side_effect=ClientError("private lookup failed"),
        ) as private_lookup:
            with mock.patch.object(client, "user_info_by_username_gql", return_value=user) as public_lookup:
                result = client.user_info_by_username("Example", use_cache=False)

        self.assertEqual(result.pk, "123")
        private_lookup.assert_called_once_with("example")
        public_lookup.assert_called_once_with("example")

    def test_authorized_user_info_uses_private_before_public(self):
        client = self.build_private_client()
        client._usernames_cache = {}
        client._users_cache = {}
        user = self.build_user()

        with mock.patch.object(client, "user_info_v1", return_value=user) as private_lookup:
            with mock.patch.object(
                client,
                "user_info_gql",
                side_effect=AssertionError("authorized lookup should use private API first"),
            ) as public_lookup:
                result = client.user_info("123", use_cache=False)

        self.assertEqual(result.pk, "123")
        private_lookup.assert_called_once_with("123")
        public_lookup.assert_not_called()

    def test_authorized_user_info_falls_back_to_public(self):
        client = self.build_private_client()
        client._usernames_cache = {}
        client._users_cache = {}
        user = self.build_user()

        with mock.patch.object(
            client, "user_info_v1", side_effect=ClientError("private lookup failed")
        ) as private_lookup:
            with mock.patch.object(client, "user_info_gql", return_value=user) as public_lookup:
                result = client.user_info("123", use_cache=False)

        self.assertEqual(result.pk, "123")
        private_lookup.assert_called_once_with("123")
        public_lookup.assert_called_once_with("123")

    def test_authorized_username_from_user_id_uses_private_lookup(self):
        client = self.build_private_client()
        user = self.build_user()

        with mock.patch.object(client, "user_info_v1", return_value=user) as private_lookup:
            with mock.patch.object(
                client,
                "username_from_user_id_gql",
                side_effect=ClientGraphqlError("public lookup should not run first"),
            ) as public_lookup:
                username = client.username_from_user_id("123")

        self.assertEqual(username, "example")
        private_lookup.assert_called_once_with("123")
        public_lookup.assert_not_called()

    def test_unauthorized_user_info_by_username_keeps_public_first(self):
        client = Client()
        client._usernames_cache = {}
        client._users_cache = {}
        user = self.build_user()

        with mock.patch.object(client, "user_info_by_username_gql", return_value=user) as public_lookup:
            with mock.patch.object(
                client,
                "user_info_by_username_v1",
                side_effect=AssertionError("unauthorized lookup should use public API first"),
            ) as private_lookup:
                result = client.user_info_by_username("Example", use_cache=False)

        self.assertEqual(result.pk, "123")
        public_lookup.assert_called_once_with("example")
        private_lookup.assert_not_called()

    def test_user_info_by_username_v2_gql_normalizes_search_query(self):
        client = Client()
        with mock.patch.object(client, "_inject_sessionid_for_v2_gql"):
            with mock.patch.object(
                client,
                "public_doc_id_graphql_request",
                return_value={
                    "xdt_api__v1__fbsearch__non_profiled_serp": {"users": [{"username": "example", "pk": "123"}]}
                },
            ) as search:
                with mock.patch.object(client, "user_info_v2_gql", return_value="user"):
                    result = client.user_info_by_username_v2_gql(" @Example ")

        self.assertEqual(result, "user")
        search.assert_called_once_with("26347858941511777", {"hasQuery": True, "query": "example"})

    def test_user_stream_by_username_v1_normalizes_endpoint(self):
        client = Client()
        with mock.patch.object(client, "private_request", return_value={"stream_rows": []}) as private_request:
            client.user_stream_by_username_v1(" @Example ")

        private_request.assert_called_once()
        self.assertEqual(private_request.call_args.args[0], "users/example/usernameinfo_stream/")

    def test_user_web_profile_info_v1_normalizes_username_param(self):
        client = Client()
        with mock.patch.object(
            client,
            "private_request",
            return_value={"data": {"pk": "9", "username": "example"}},
        ) as private_request:
            user = client.user_web_profile_info_v1(" @Example ")

        private_request.assert_called_once_with("users/web_profile_info/", params={"username": "example"})
        self.assertEqual(user, {"pk": "9", "username": "example"})

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

    def test_user_followers_v1_chunk_sends_order_when_provided(self):
        client = self.build_private_client()

        with mock.patch.object(
            client,
            "private_request",
            return_value={"users": [], "next_max_id": None},
        ) as private_request:
            client.user_followers_v1_chunk("123", order="date_followed_latest")

        params = private_request.call_args.kwargs["params"]
        self.assertEqual(params["order"], "date_followed_latest")

    def test_user_followers_v1_chunk_caps_count_to_max_user_count(self):
        client = self.build_private_client()

        with mock.patch.object(
            client,
            "private_request",
            return_value={"users": [], "next_max_id": None},
        ) as private_request:
            client.user_followers_v1_chunk("123", max_amount=MAX_USER_COUNT + 1)

        params = private_request.call_args.kwargs["params"]
        self.assertEqual(params["count"], MAX_USER_COUNT)

    def test_authorized_user_followers_falls_back_when_private_list_is_limited(self):
        client = self.build_private_client()
        private_user = UserShort(pk="private", username="private")
        public_user = UserShort(pk="public", username="public")

        def private_lookup(user_id, amount):
            client.last_json = {"should_limit_list_of_followers": True}
            return [private_user]

        with mock.patch.object(client, "user_followers_v1", side_effect=private_lookup) as private_lookup_mock:
            with mock.patch.object(client, "user_followers_gql", return_value=[public_user]) as public_lookup:
                followers = client.user_followers("123", use_cache=False, amount=2)

        private_lookup_mock.assert_called_once_with("123", 2)
        public_lookup.assert_called_once_with("123", 2)
        self.assertEqual(list(followers), ["public"])

    def test_authorized_user_followers_default_amount_falls_back_when_private_list_is_limited(self):
        client = self.build_private_client()
        private_user = UserShort(pk="private", username="private")
        public_user = UserShort(pk="public", username="public")

        def private_lookup(user_id, amount):
            client.last_json = {"should_limit_list_of_followers": True}
            return [private_user]

        with mock.patch.object(client, "user_followers_v1", side_effect=private_lookup) as private_lookup_mock:
            with mock.patch.object(client, "user_followers_gql", return_value=[public_user]) as public_lookup:
                followers = client.user_followers("123", use_cache=False)

        private_lookup_mock.assert_called_once_with("123", 0)
        public_lookup.assert_called_once_with("123", 0)
        self.assertEqual(list(followers), ["public"])

    def test_user_followers_with_order_uses_private_api_without_cache(self):
        client = self.build_private_client()
        cached_user = UserShort(pk="old", username="cached")
        sorted_user = UserShort(pk="new", username="sorted")
        client._users_followers = {"123": {cached_user.pk: cached_user}}

        with mock.patch.object(
            client,
            "user_followers_v1",
            return_value=[sorted_user],
        ) as user_followers_v1:
            with mock.patch.object(
                client,
                "user_followers_gql",
                side_effect=AssertionError("sorted followers should use private API"),
            ):
                followers = client.user_followers("123", order="date_followed_latest")

        user_followers_v1.assert_called_once_with("123", 0, order="date_followed_latest")
        self.assertEqual(list(followers), ["new"])
        self.assertEqual(list(client._users_followers["123"]), ["old"])

    def test_authorized_user_followers_uses_private_before_public(self):
        client = self.build_private_client()
        follower = UserShort(pk="456", username="follower")

        with mock.patch.object(client, "user_followers_v1", return_value=[follower]) as private_lookup:
            with mock.patch.object(
                client,
                "user_followers_gql",
                side_effect=AssertionError("authorized lookup should use private API first"),
            ) as public_lookup:
                followers = client.user_followers("123", use_cache=False, amount=1)

        private_lookup.assert_called_once_with("123", 1)
        public_lookup.assert_not_called()
        self.assertEqual(list(followers), ["456"])

    def test_authorized_user_followers_falls_back_to_public(self):
        client = self.build_private_client()
        follower = UserShort(pk="456", username="follower")

        with mock.patch.object(
            client,
            "user_followers_v1",
            side_effect=ClientError("private lookup failed"),
        ) as private_lookup:
            with mock.patch.object(client, "user_followers_gql", return_value=[follower]) as public_lookup:
                followers = client.user_followers("123", use_cache=False, amount=1)

        private_lookup.assert_called_once_with("123", 1)
        public_lookup.assert_called_once_with("123", 1)
        self.assertEqual(list(followers), ["456"])

    def test_unauthorized_user_followers_keeps_public_first(self):
        client = Client()
        follower = UserShort(pk="456", username="follower")

        with mock.patch.object(client, "user_followers_gql", return_value=[follower]) as public_lookup:
            with mock.patch.object(
                client,
                "user_followers_v1",
                side_effect=AssertionError("unauthorized lookup should use public API first"),
            ) as private_lookup:
                followers = client.user_followers("123", use_cache=False, amount=1)

        public_lookup.assert_called_once_with("123", 1)
        private_lookup.assert_not_called()
        self.assertEqual(list(followers), ["456"])

    def test_authorized_user_following_uses_private_before_public(self):
        client = self.build_private_client()
        following_user = UserShort(pk="456", username="following")

        with mock.patch.object(client, "user_following_v1", return_value=[following_user]) as private_lookup:
            with mock.patch.object(
                client,
                "user_following_gql",
                side_effect=AssertionError("authorized lookup should use private API first"),
            ) as public_lookup:
                following = client.user_following("123", use_cache=False, amount=1)

        private_lookup.assert_called_once_with("123", 1)
        public_lookup.assert_not_called()
        self.assertEqual(list(following), ["456"])

    def test_authorized_user_following_falls_back_to_public(self):
        client = self.build_private_client()
        following_user = UserShort(pk="456", username="following")

        with mock.patch.object(
            client,
            "user_following_v1",
            side_effect=ClientError("private lookup failed"),
        ) as private_lookup:
            with mock.patch.object(client, "user_following_gql", return_value=[following_user]) as public_lookup:
                following = client.user_following("123", use_cache=False, amount=1)

        private_lookup.assert_called_once_with("123", 1)
        public_lookup.assert_called_once_with("123", 1)
        self.assertEqual(list(following), ["456"])

    def test_unauthorized_user_following_keeps_public_first(self):
        client = Client()
        following_user = UserShort(pk="456", username="following")

        with mock.patch.object(client, "user_following_gql", return_value=[following_user]) as public_lookup:
            with mock.patch.object(
                client,
                "user_following_v1",
                side_effect=AssertionError("unauthorized lookup should use public API first"),
            ) as private_lookup:
                following = client.user_following("123", use_cache=False, amount=1)

        public_lookup.assert_called_once_with("123", 1)
        private_lookup.assert_not_called()
        self.assertEqual(list(following), ["456"])

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

    def test_user_following_v1_chunk_caps_count_to_max_user_count(self):
        client = self.build_private_client()

        with mock.patch.object(
            client,
            "private_request",
            return_value={"users": [], "next_max_id": None},
        ) as private_request:
            client.user_following_v1_chunk("123", max_amount=MAX_USER_COUNT + 1)

        params = private_request.call_args.kwargs["params"]
        self.assertEqual(params["count"], MAX_USER_COUNT)

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

    def test_user_follow_posts_current_action_context(self):
        client = self.build_private_client()
        client.android_device_id = "android-device"

        with mock.patch.object(
            client,
            "private_request",
            return_value={"friendship_status": {"following": True}},
        ) as private_request:
            self.assertTrue(client.user_follow("42"))

        endpoint, data = private_request.call_args.args
        self.assertEqual(endpoint, "friendships/create/42/")
        self.assertEqual(data["user_id"], "42")
        self.assertEqual(data["_uid"], "1")
        self.assertEqual(data["device_id"], "android-device")
        self.assertEqual(data["radio_type"], "wifi-none")
        self.assertEqual(data["include_follow_friction_check"], "1")
        self.assertEqual(data["container_module"], "profile")

    def test_user_follow_returns_true_for_pending_private_follow_request(self):
        client = self.build_private_client()

        with mock.patch.object(
            client,
            "private_request",
            return_value={"friendship_status": {"following": False, "outgoing_request": True}},
        ):
            self.assertTrue(client.user_follow("42"))

    def test_user_unfollow_posts_current_action_context(self):
        client = self.build_private_client()
        client.android_device_id = "android-device"

        with mock.patch.object(
            client,
            "private_request",
            return_value={"friendship_status": {"following": False}},
        ) as private_request:
            self.assertTrue(client.user_unfollow("42"))

        endpoint, data = private_request.call_args.args
        self.assertEqual(endpoint, "friendships/destroy/42/")
        self.assertEqual(data["user_id"], "42")
        self.assertEqual(data["_uid"], "1")
        self.assertEqual(data["device_id"], "android-device")
        self.assertEqual(data["radio_type"], "wifi-none")
        self.assertEqual(data["container_module"], "profile")

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

    def test_user_suggested_profiles_returns_chaining_payload_by_default(self):
        client = Client()
        chained = {"users": [{"pk": "9", "username": "a"}, {"pk": "10", "username": "b"}]}

        with mock.patch.object(client, "chaining", return_value=chained) as chaining:
            with mock.patch.object(client, "fetch_suggestion_details") as fetch_details:
                result = client.user_suggested_profiles("123")

        self.assertEqual(result, chained)
        chaining.assert_called_once_with("123")
        fetch_details.assert_not_called()

    def test_user_suggested_profiles_expands_suggestion_details(self):
        client = Client()
        chained = {"users": [{"pk": "9"}, {"pk": "10"}]}
        expanded = {"items": [{"user": {"pk": "9"}, "social_context": "Followed by you"}]}

        with mock.patch.object(client, "chaining", return_value=chained) as chaining:
            with mock.patch.object(client, "fetch_suggestion_details", return_value=expanded) as fetch_details:
                result = client.user_suggested_profiles("123", expand_suggestion=True)

        self.assertEqual(result, expanded)
        chaining.assert_called_once_with("123")
        fetch_details.assert_called_once_with("123", "9,10")

    def test_user_suggested_profiles_expand_without_users_returns_chaining(self):
        client = Client()
        chained = {"users": []}

        with mock.patch.object(client, "chaining", return_value=chained):
            with mock.patch.object(client, "fetch_suggestion_details") as fetch_details:
                result = client.user_suggested_profiles("123", expand_suggestion=True)

        self.assertEqual(result, chained)
        fetch_details.assert_not_called()

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

    def test_user_stream_by_id_v1_parses_first_json_line_from_stream_response(self):
        from instagrapi.exceptions import ClientJSONDecodeError

        client = Client()
        client.last_json = {}

        def private_request(*args, **kwargs):
            client.last_response = Mock(
                text='{"user":{"pk":123,"username":"example"},"status":"ok"}\n{"stream_tail":true}\n',
                status_code=200,
            )
            raise ClientJSONDecodeError("stream response")

        with mock.patch.object(client, "private_request", side_effect=private_request):
            result = client.user_stream_by_id_v1("123")

        self.assertEqual(result["user"]["username"], "example")
        self.assertEqual(result["status"], "ok")

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

    def test_user_stream_by_id_flat_accepts_top_level_user_payload(self):
        client = Client()
        envelope = {"user": {"pk": "9", "username": "alice"}}

        with mock.patch.object(client, "user_stream_by_id_v1", return_value=envelope):
            user = client.user_stream_by_id_flat("9")

        self.assertEqual(user["pk"], "9")
        self.assertEqual(user["username"], "alice")

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

    def test_user_info_v2_gql_uses_profile_doc_id(self):
        client = Client()
        payload = self.build_web_profile_user(id="25025320")["data"]["user"]
        payload["pk"] = payload["id"]
        payload["media_count"] = 0
        payload["follower_count"] = 0
        payload["following_count"] = 0
        payload["profile_pic_url"] = "https://example.com/pic.jpg"

        with mock.patch.object(client, "_inject_sessionid_for_v2_gql") as inject:
            with mock.patch.object(client, "public_doc_id_graphql_request", return_value={"user": payload}) as gql:
                user = client.user_info_v2_gql("25025320")

        inject.assert_called_once_with()
        gql.assert_called_once()
        self.assertEqual(gql.call_args.args[0], "25980296051578533")
        self.assertEqual(gql.call_args.args[1]["id"], "25025320")
        self.assertEqual(user.pk, "25025320")

    def test_user_info_by_username_v2_gql_resolves_username_then_profile(self):
        client = Client()
        with mock.patch.object(client, "_inject_sessionid_for_v2_gql"):
            with mock.patch.object(
                client,
                "public_doc_id_graphql_request",
                return_value={
                    "xdt_api__v1__fbsearch__non_profiled_serp": {"users": [{"username": "example", "pk": "123"}]}
                },
            ) as search:
                with mock.patch.object(client, "user_info_v2_gql", return_value="user") as profile:
                    result = client.user_info_by_username_v2_gql("Example")

        self.assertEqual(result, "user")
        search.assert_called_once_with("26347858941511777", {"hasQuery": True, "query": "example"})
        profile.assert_called_once_with("123")

    def test_user_about_v1_calls_bloks_action_and_extracts_last_json(self):
        client = self.build_private_client()
        client.bloks_versioning_id = "bloks"
        client.last_json = {"layout": {"bloks_payload": {"data": []}}}
        expected = object()
        with mock.patch.object(client, "bloks_action", return_value={}) as bloks_action:
            with mock.patch("instagrapi.mixins.user.extract_about_v1", return_value=expected) as extract:
                result = client.user_about_v1("123")

        self.assertIs(result, expected)
        bloks_action.assert_called_once()
        self.assertEqual(bloks_action.call_args.args[0], "com.instagram.interactions.about_this_account")
        self.assertEqual(bloks_action.call_args.args[1]["target_user_id"], "123")
        extract.assert_called_once_with(client.last_json)

    def test_user_guides_v1_extracts_guides(self):
        client = Client()
        with mock.patch.object(client, "private_request", return_value={"guides": [{"summary": {"id": "1"}}]}) as req:
            with mock.patch("instagrapi.mixins.user.extract_guide_v1", side_effect=lambda item: item["summary"]):
                guides = client.user_guides_v1("123")

        self.assertEqual(guides, [{"id": "1"}])
        req.assert_called_once_with("guides/user/123/")

    def test_feed_user_stream_item_posts_uuid_payload(self):
        client = Client()
        client.uuid = "uuid"
        with mock.patch.object(client, "private_request", return_value={"stream_rows": []}) as private_request:
            client.feed_user_stream_item("123", is_pull_to_refresh=True)

        private_request.assert_called_once_with(
            "feed/user_stream/123/",
            data={"_uuid": "uuid", "is_pull_to_refresh": "true"},
        )

    def test_private_graphql_followers_list_builds_query_wrapper(self):
        client = Client()
        with mock.patch.object(client, "private_graphql_query_request", return_value={"data": {}}) as query:
            client.private_graphql_followers_list(
                "123",
                "rank",
                max_id=10,
                priority="u=3, i",
                order="date_followed_latest",
            )

        query.assert_called_once()
        self.assertEqual(query.call_args.kwargs["friendly_name"], "FollowersList")
        self.assertEqual(query.call_args.kwargs["root_field_name"], "xdt_api__v1__friendships__followers")
        self.assertEqual(query.call_args.kwargs["client_doc_id"], "28479704797510738576165798526")
        self.assertEqual(query.call_args.kwargs["variables"]["user_id"], "123")
        self.assertEqual(query.call_args.kwargs["variables"]["max_id"], 10)
        self.assertEqual(query.call_args.kwargs["variables"]["order"], "date_followed_latest")
        self.assertTrue(query.call_args.kwargs["variables"]["skip_suggested_users"])
        self.assertTrue(query.call_args.kwargs["variables"]["skip_page_size"])
        self.assertTrue(query.call_args.kwargs["variables"]["skip_pending_admins"])
        self.assertEqual(query.call_args.kwargs["priority"], "u=3, i")
        self.assertEqual(query.call_args.kwargs["extra_headers"]["X-FB-RMD"], "state=URL_ELIGIBLE")

    def test_user_followers_private_gql_chunk_extracts_users_and_cursor(self):
        client = Client()
        response = {
            "data": {
                "1$xdt_api__v1__friendships__followers(_request_data:$request_data,user_id:$user_id)": {
                    "users": [
                        {
                            "id": "1",
                            "username": "one",
                            "full_name": "One",
                            "profile_pic_url": "https://example.com/one.jpg",
                            "is_private": False,
                        },
                        {
                            "pk": "2",
                            "username": "two",
                            "full_name": "Two",
                            "profile_pic_url": "https://example.com/two.jpg",
                            "is_private": True,
                        },
                    ],
                    "next_max_id": "25",
                }
            }
        }
        with mock.patch.object(client, "private_graphql_followers_list", return_value=response) as followers_list:
            users, next_max_id = client.user_followers_private_gql_chunk(
                "123",
                max_amount=2,
                max_id="10",
                rank_token="rank",
                order="date_followed_latest",
            )

        self.assertEqual([user.pk for user in users], ["1", "2"])
        self.assertEqual([user.username for user in users], ["one", "two"])
        self.assertEqual(next_max_id, "25")
        followers_list.assert_called_once_with(
            "123",
            "rank",
            max_id="10",
            order="date_followed_latest",
            priority="u=3, i",
        )

    def test_user_followers_private_gql_paginates_until_amount(self):
        client = Client()
        pages = [
            {
                "data": {
                    "xdt_api__v1__friendships__followers": {
                        "users": [
                            {"id": "1", "username": "one"},
                            {"id": "2", "username": "two"},
                        ],
                        "next_max_id": "25",
                    }
                }
            },
            {
                "data": {
                    "xdt_api__v1__friendships__followers": {
                        "users": [
                            {"id": "3", "username": "three"},
                            {"id": "4", "username": "four"},
                        ],
                        "next_max_id": "50",
                    }
                }
            },
        ]
        with mock.patch.object(client, "private_graphql_followers_list", side_effect=pages) as followers_list:
            users = client.user_followers_private_gql("123", amount=3, rank_token="rank")

        self.assertEqual([user.pk for user in users], ["1", "2", "3"])
        self.assertEqual(followers_list.call_args_list[0].kwargs["max_id"], None)
        self.assertEqual(followers_list.call_args_list[1].kwargs["max_id"], "25")

    def test_private_graphql_following_list_builds_query_wrapper(self):
        client = Client()
        with mock.patch.object(client, "private_graphql_query_request", return_value={"data": {}}) as query:
            client.private_graphql_following_list("123", "rank", order="date_followed_earliest")

        self.assertEqual(query.call_args.kwargs["friendly_name"], "FollowingList")
        self.assertEqual(query.call_args.kwargs["root_field_name"], "xdt_api__v1__friendships__following")
        self.assertEqual(query.call_args.kwargs["client_doc_id"], "161046392817718486717479294775")
        self.assertEqual(query.call_args.kwargs["variables"]["user_id"], "123")
        self.assertEqual(query.call_args.kwargs["variables"]["order"], "date_followed_earliest")
        self.assertTrue(query.call_args.kwargs["variables"]["skip_use_clickable_see_more"])
        self.assertTrue(query.call_args.kwargs["variables"]["skip_page_size"])
        self.assertTrue(query.call_args.kwargs["variables"]["skip_friend_requests"])
        self.assertEqual(query.call_args.kwargs["extra_headers"]["X-FB-RMD"], "state=URL_ELIGIBLE")

    def test_private_graphql_clips_profile_builds_query_wrapper(self):
        client = Client()
        with mock.patch.object(client, "private_graphql_query_request", return_value={"data": {}}) as query:
            client.private_graphql_clips_profile("123", page_size=9, no_of_medias_in_each_chunk=3)

        variables = query.call_args.kwargs["variables"]
        self.assertEqual(query.call_args.kwargs["friendly_name"], "ClipsProfileQuery")
        self.assertEqual(variables["data"]["target_user_id"], "123")
        self.assertEqual(variables["data"]["page_size"], 9)
        self.assertEqual(variables["data"]["no_of_medias_in_each_chunk"], 3)

    def test_private_graphql_inbox_tray_for_user_builds_query_wrapper(self):
        client = Client()
        with mock.patch.object(client, "private_graphql_query_request", return_value={"data": {}}) as query:
            client.private_graphql_inbox_tray_for_user("123", priority="u=3, i")

        self.assertEqual(query.call_args.kwargs["friendly_name"], "InboxTrayRequestForUserQuery")
        self.assertEqual(query.call_args.kwargs["root_field_name"], "xdt_get_inbox_tray_items")
        self.assertEqual(query.call_args.kwargs["variables"]["user_id"], "123")
        self.assertEqual(query.call_args.kwargs["priority"], "u=3, i")

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
