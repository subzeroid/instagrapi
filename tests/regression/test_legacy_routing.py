import unittest
from unittest.mock import patch

from instagrapi import Client
from instagrapi.exceptions import (
    AccountSuspended,
    ClientError,
    ClientForbiddenError,
    ClientGraphqlError,
    ClientLoginRequired,
    ClientThrottledError,
    ClientUnauthorizedError,
    PleaseWaitFewMinutes,
    WrongCursorError,
)


class LegacyRoutingRegressionTests(unittest.TestCase):
    def setUp(self):
        self.client = Client()
        self.client.authorization_data = {"ds_user_id": "1"}

    def tearDown(self):
        for session in (self.client.private, self.client.public, self.client.graphql):
            session.close()

    def test_authenticated_routes_do_not_fall_back_to_legacy(self):
        routes = (
            ("user_stories", "user_stories_v1", "user_stories_gql", ("123",), {}),
            ("usertag_medias", "usertag_medias_v1", "usertag_medias_gql", ("123",), {}),
            ("usertag_medias_paginated", "usertag_medias_paginated_v1", "usertag_medias_paginated_gql", ("123",), {}),
            (
                "hashtag_medias_paginated",
                "hashtag_medias_paginated_v1",
                "hashtag_medias_paginated_gql",
                ("python",),
                {},
            ),
        )
        for method, primary, legacy, args, kwargs in routes:
            with self.subTest(method=method):
                failure = ClientError("primary unavailable")
                with patch.object(self.client, primary, side_effect=failure), patch.object(self.client, legacy) as old:
                    with self.assertRaises(ClientError) as caught:
                        getattr(self.client, method)(*args, **kwargs)
                self.assertIs(caught.exception, failure)
                old.assert_not_called()

    def test_follow_lists_preserve_final_modern_failure(self):
        for kind in ("followers", "following"):
            with self.subTest(kind=kind):
                failure = ClientGraphqlError("modern unavailable")
                with (
                    patch.object(self.client, "user_" + kind + "_v1", side_effect=ClientError("primary unavailable")),
                    patch.object(self.client, "user_" + kind + "_private_gql", side_effect=failure),
                    patch.object(self.client, "user_" + kind + "_gql") as old,
                ):
                    with self.assertRaises(ClientGraphqlError) as caught:
                        getattr(self.client, "user_" + kind)("123", use_cache=False)
                self.assertIs(caught.exception, failure)
                old.assert_not_called()

    def test_terminal_failures_and_programming_errors_do_not_switch_endpoint(self):
        failures = (
            PleaseWaitFewMinutes,
            WrongCursorError,
            ClientThrottledError,
            ClientUnauthorizedError,
            ClientForbiddenError,
            ClientLoginRequired,
            AccountSuspended,
            KeyError,
        )
        for kind in failures:
            for method, primary, alternate in (
                ("user_followers", "user_followers_v1", "user_followers_private_gql"),
                ("user_following", "user_following_v1", "user_following_private_gql"),
                ("user_medias", "user_medias_v1", "user_medias_gql"),
                ("user_medias_paginated", "user_medias_paginated_v1", "user_medias_paginated_gql"),
            ):
                with self.subTest(error=kind.__name__, method=method):
                    failure = kind("stop")
                    with (
                        patch.object(self.client, primary, side_effect=failure),
                        patch.object(self.client, alternate) as other,
                    ):
                        with self.assertRaises(kind) as caught:
                            getattr(self.client, method)("123")
                    self.assertIs(caught.exception, failure)
                    other.assert_not_called()

    def test_app_timeline_never_falls_back_to_legacy_when_authenticated(self):
        failure = ClientGraphqlError("modern unavailable")
        with (
            patch.object(self.client, "_user_medias_paginated_app_gql", side_effect=failure),
            patch.object(self.client, "_user_medias_paginated_public_gql") as old,
        ):
            with self.assertRaises(ClientGraphqlError) as caught:
                self.client.user_medias_paginated_gql("123")
        self.assertIs(caught.exception, failure)
        old.assert_not_called()

    def test_pagination_does_not_replay_cursor_on_another_endpoint(self):
        routes = (("user_medias_paginated", "user_medias_paginated_v1", "user_medias_paginated_gql"),)
        for method, primary, alternate in routes:
            failure = ClientError("unavailable")
            with patch.object(self.client, primary, side_effect=failure), patch.object(self.client, alternate) as other:
                with self.assertRaises(ClientError) as caught:
                    getattr(self.client, method)("123", end_cursor="opaque")
            self.assertIs(caught.exception, failure)
            other.assert_not_called()

    def test_anonymous_cursor_failure_does_not_switch_to_private(self):
        self.client.authorization_data = {}
        routes = (
            ("user_medias_paginated", "user_medias_paginated_gql", "user_medias_paginated_v1", "123"),
            ("usertag_medias_paginated", "usertag_medias_paginated_gql", "usertag_medias_paginated_v1", "123"),
            ("hashtag_medias_paginated", "hashtag_medias_paginated_gql", "hashtag_medias_paginated_v1", "python"),
            ("user_medias_paginated_gql", "_user_medias_paginated_app_gql", "_user_medias_paginated_public_gql", "123"),
        )
        for method, primary, alternate, target in routes:
            with self.subTest(method=method):
                failure = ClientGraphqlError("unavailable")
                with (
                    patch.object(self.client, primary, side_effect=failure),
                    patch.object(self.client, alternate) as other,
                ):
                    with self.assertRaises(ClientGraphqlError) as caught:
                        getattr(self.client, method)(target, end_cursor="opaque")
                self.assertIs(caught.exception, failure)
                other.assert_not_called()

    def test_private_media_errors_are_not_empty_or_partial_success(self):
        for method in ("user_medias_paginated_v1", "user_medias_v1", "usertag_medias_v1"):
            for kind in (ClientThrottledError, ClientUnauthorizedError, ClientGraphqlError, KeyError):
                with self.subTest(method=method, error=kind.__name__):
                    failure = kind("stop")
                    with patch.object(self.client, "private_request", side_effect=failure):
                        with self.assertRaises(kind) as caught:
                            getattr(self.client, method)("123")
                    self.assertIs(caught.exception, failure)

    def test_story_batches_keep_every_response(self):
        def reel(pk):
            owner = {
                "id": str(pk),
                "username": "example",
                "full_name": "Example",
                "profile_pic_url": "https://example.com/photo",
                "is_private": False,
            }
            story = {
                "id": str(pk),
                "owner": owner,
                "display_url": "https://example.com/story",
                "taken_at_timestamp": 1700000000,
                "is_video": False,
                "tappable_objects": [],
                "edge_media_to_sponsor_user": {"edges": []},
            }
            return {"owner": owner, "items": [story, story]}

        with (
            patch.object(self.client, "inject_sessionid_to_public"),
            patch.object(
                self.client,
                "public_graphql_request",
                side_effect=[{"reels_media": [reel(1)]}, {"reels_media": [reel(51)]}],
            ) as query,
        ):
            users = self.client.users_stories_gql(list(range(1, 52)), amount=1)
        self.assertEqual([str(user.pk) for user in users], ["1", "51"])
        self.assertEqual([len(user.stories) for user in users], [1, 1])
        self.assertEqual(len(query.call_args_list[0].kwargs["variables"]["reel_ids"]), 50)
        self.assertEqual(len(query.call_args_list[1].kwargs["variables"]["reel_ids"]), 1)

    def test_empty_story_batch_is_empty_without_dispatch(self):
        with (
            patch.object(self.client, "inject_sessionid_to_public") as inject,
            patch.object(self.client, "public_graphql_request") as query,
        ):
            self.assertEqual(self.client.users_stories_gql([]), [])
        inject.assert_not_called()
        query.assert_not_called()

    def test_app_fallback_cursor_continues_on_originating_endpoint(self):
        with (
            patch.object(
                self.client, "user_medias_paginated_v1", side_effect=ClientGraphqlError("unavailable")
            ) as mobile,
            patch.object(
                self.client, "_user_medias_paginated_app_gql", side_effect=[(["first"], "app-next"), (["second"], None)]
            ) as app,
        ):
            first, cursor = self.client.user_medias_paginated("123")
            second, end = self.client.user_medias_paginated("123", end_cursor=cursor)
        self.assertEqual((first, second, end), (["first"], ["second"], None))
        mobile.assert_called_once()
        self.assertEqual(app.call_args_list[-1].kwargs["end_cursor"], "app-next")

    def test_public_fallback_cursor_continues_on_originating_endpoint(self):
        self.client.authorization_data = {}
        with (
            patch.object(
                self.client, "_user_medias_paginated_app_gql", side_effect=ClientGraphqlError("unavailable")
            ) as app,
            patch.object(
                self.client,
                "_user_medias_paginated_public_gql",
                side_effect=[(["first"], "public-next"), (["second"], None)],
            ) as public,
        ):
            first, cursor = self.client.user_medias_paginated_gql("123")
            second, end = self.client.user_medias_paginated_gql("123", end_cursor=cursor)
        self.assertEqual((first, second, end), (["first"], ["second"], None))
        app.assert_called_once()
        self.assertEqual(public.call_args_list[-1].kwargs["end_cursor"], "public-next")

    def test_tagged_private_fallback_cursor_continues_on_originating_endpoint(self):
        self.client.authorization_data = {}
        with (
            patch.object(
                self.client, "usertag_medias_paginated_gql", side_effect=ClientGraphqlError("unavailable")
            ) as public,
            patch.object(
                self.client,
                "usertag_medias_paginated_v1",
                side_effect=[(["first"], "private-next"), (["second"], None)],
            ) as mobile,
        ):
            first, cursor = self.client.usertag_medias_paginated("123")
            second, end = self.client.usertag_medias_paginated("123", end_cursor=cursor)
        self.assertEqual((first, second, end), (["first"], ["second"], None))
        public.assert_called_once()
        self.assertEqual(mobile.call_args_list[-1].kwargs["end_cursor"], "private-next")

    def test_routed_cursor_rejects_wrong_method_or_auth_before_dispatch(self):
        with (
            patch.object(self.client, "private_request") as private,
            patch.object(self.client, "public_graphql_request") as public,
        ):
            for method, cursor in (
                ("user_medias_paginated", "ig-route:tagged-v1:opaque"),
                ("user_medias_paginated", "ig-route:timeline-public:opaque"),
                ("user_medias_paginated_gql", "ig-route:timeline-app:opaque"),
                ("usertag_medias_paginated", "ig-route:timeline-v1:opaque"),
                ("user_medias_paginated", "ig-route:timeline-app:"),
                ("user_medias_paginated", "ig-route::opaque"),
            ):
                with self.subTest(method=method, cursor=cursor):
                    with self.assertRaises(WrongCursorError):
                        getattr(self.client, method)("123", end_cursor=cursor)
        private.assert_not_called()
        public.assert_not_called()

    def test_anonymous_follow_restriction_does_not_switch_to_private(self):
        self.client.authorization_data = {}
        for kind in ("followers", "following"):
            with self.subTest(kind=kind):
                failure = ClientThrottledError("stop")
                with (
                    patch.object(self.client, "user_" + kind + "_gql", side_effect=failure),
                    patch.object(self.client, "user_" + kind + "_v1") as other,
                ):
                    with self.assertRaises(ClientThrottledError) as caught:
                        getattr(self.client, "user_" + kind)("123")
                self.assertIs(caught.exception, failure)
                other.assert_not_called()
