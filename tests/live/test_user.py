from tests import helpers as _helpers
from tests.helpers import *


class ClientUserTestCase(_helpers.ClientPrivateTestCase):
    def test_user_followers(self):
        user_id = self.user_id_from_username("instagram")
        followers = self.cl.user_followers(user_id, amount=10)
        self.assertTrue(len(followers) == 10)
        self.assertIsInstance(list(followers.values())[0], UserShort)

    def test_user_followers_sorted_v1(self):
        user_id = self.user_id_from_username("instagram")
        followers = self.cl.user_followers_v1(user_id, amount=5, order="date_followed_latest")
        self.assertTrue(len(followers) == 5)
        self.assertIsInstance(followers[0], UserShort)

    def test_private_graphql_followers_list_sorted(self):
        user_id = self.user_id_from_username("instagram")
        result = None
        for _ in range(3):
            try:
                result = self.cl.private_graphql_followers_list(
                    user_id,
                    self.cl.rank_token,
                    order="date_followed_latest",
                )
                break
            except ClientGraphqlError:
                time.sleep(2)
        if result is None:
            result = self.cl.private_graphql_followers_list(
                user_id,
                self.cl.rank_token,
                order="date_followed_latest",
            )

        data = result.get("data") or {}
        followers = next(
            (value for key, value in data.items() if "xdt_api__v1__friendships__followers" in key),
            None,
        )
        self.assertIsInstance(followers, dict)
        self.assertGreater(len(followers.get("users", [])), 0)

    def test_user_followers_private_gql(self):
        user_id = self.user_id_from_username("instagram")
        followers = self.cl.user_followers_private_gql(user_id, amount=5, order="date_followed_latest")
        self.assertEqual(len(followers), 5)
        self.assertIsInstance(followers[0], UserShort)


class ClientFollowersLiveTestCase(_helpers.ClientPrivateTestCase):
    def __init__(self, *args, **kwargs):
        self.cl = None
        return unittest.TestCase.__init__(self, *args, **kwargs)

    def setup_method(self, *args, **kwargs):
        return None

    def setUp(self):
        if not TEST_ACCOUNTS_URL:
            self.skipTest("TEST_ACCOUNTS_URL is required for followers live tests")
        try:
            self.cl = self.fresh_account()
        except Exception as exc:
            self.skipTest(str(exc))

    def test_user_followers_uses_private_api_live(self):
        user_id = self.user_id_from_username("instagram")

        with mock.patch.object(
            self.cl,
            "user_followers_gql",
            side_effect=AssertionError("authorized user_followers should not call public GraphQL first"),
        ) as public_lookup:
            followers = self.cl.user_followers(user_id, use_cache=False, amount=10)

        self.assertTrue(len(followers) == 10)
        self.assertIsInstance(list(followers.values())[0], UserShort)
        public_lookup.assert_not_called()

    def test_user_followers_gql_chunk_paginates_two_pages(self):
        user_id = self.user_id_from_username("instagram")

        first_page, end_cursor = self.cl.user_followers_gql_chunk(user_id, max_amount=12)
        self.assertGreater(len(first_page), 0)
        self.assertLessEqual(len(first_page), 12)
        self.assertTrue(end_cursor)
        self.assertIsInstance(first_page[0], UserShort)

        next_page, _ = self.cl.user_followers_gql_chunk(user_id, max_amount=12, end_cursor=end_cursor)
        self.assertGreater(len(next_page), 0)
        self.assertLessEqual(len(next_page), 12)
        self.assertIsInstance(next_page[0], UserShort)

        first_ids = {user.pk for user in first_page}
        next_ids = {user.pk for user in next_page}
        self.assertTrue(first_ids.isdisjoint(next_ids), f"Duplicate followers across pages: {first_ids & next_ids}")


class ClientGraphQLQueryLiveTestCase(_helpers.ClientPrivateTestCase):
    def test_user_short_gql(self):
        user = self.cl.user_short_gql("25025320", use_cache=False)
        self.assertIsInstance(user, UserShort)
        self.assertEqual(user.pk, "25025320")
        self.assertEqual(user.username, "instagram")

    def test_username_from_user_id(self):
        self.assertEqual(self.cl.username_from_user_id(25025320), "instagram")

    def test_user_medias_gql(self):
        user_id = self.user_id_from_username("instagram")
        medias = self.cl.user_medias_gql(user_id, amount=2, sleep=0)
        self.assertGreater(len(medias), 0)
        media = medias[0]
        self.assertIsInstance(media, Media)
        for field in REQUIRED_MEDIA_FIELDS:
            self.assertTrue(hasattr(media, field))


class ClientUserMediasPaginationLiveTestCase(_helpers.ClientPrivateTestCase):
    def __init__(self, *args, **kwargs):
        self.cl = None
        return unittest.TestCase.__init__(self, *args, **kwargs)

    def setup_method(self, *args, **kwargs):
        return None

    def setUp(self):
        if not TEST_ACCOUNTS_URL:
            self.skipTest("TEST_ACCOUNTS_URL is required for user media pagination live tests")
        try:
            self.cl = self.fresh_account()
        except Exception as exc:
            self.skipTest(str(exc))

    def assertMediaPage(self, medias, amount):
        self.assertGreater(len(medias), 0)
        self.assertLessEqual(len(medias), amount)
        media = medias[0]
        self.assertIsInstance(media, Media)
        for field in REQUIRED_MEDIA_FIELDS:
            self.assertTrue(hasattr(media, field))

    def assertNoDuplicateMediasAcrossPages(self, first_page, next_page):
        first_ids = {media.pk for media in first_page}
        next_ids = {media.pk for media in next_page}
        self.assertTrue(first_ids.isdisjoint(next_ids), f"Duplicate medias across pages: {first_ids & next_ids}")

    def test_user_medias_paginated_live(self):
        user_id = self.user_id_from_username("instagram")

        first_page, end_cursor = self.cl.user_medias_paginated(user_id, amount=2)
        self.assertMediaPage(first_page, 2)
        self.assertTrue(end_cursor)

        next_page, _ = self.cl.user_medias_paginated(user_id, amount=2, end_cursor=end_cursor)
        self.assertMediaPage(next_page, 2)
        self.assertNoDuplicateMediasAcrossPages(first_page, next_page)


class ClientUsertagPaginationLiveTestCase(_helpers.ClientPrivateTestCase):
    def __init__(self, *args, **kwargs):
        self.cl = None
        return unittest.TestCase.__init__(self, *args, **kwargs)

    def setup_method(self, *args, **kwargs):
        return None

    def setUp(self):
        if not TEST_ACCOUNTS_URL:
            self.skipTest("TEST_ACCOUNTS_URL is required for usertag pagination live tests")
        try:
            self.cl = self.fresh_account()
        except Exception as exc:
            self.skipTest(str(exc))

    def assertTaggedMediaPage(self, medias, amount):
        self.assertGreater(len(medias), 0)
        self.assertLessEqual(len(medias), amount)
        media = medias[0]
        self.assertIsInstance(media, Media)
        for field in REQUIRED_MEDIA_FIELDS:
            self.assertTrue(hasattr(media, field))

    def assertNoDuplicateMediasAcrossPages(self, first_page, next_page):
        first_ids = {media.pk for media in first_page}
        next_ids = {media.pk for media in next_page}
        self.assertTrue(first_ids.isdisjoint(next_ids), f"Duplicate medias across pages: {first_ids & next_ids}")

    def test_usertag_medias_paginated_live(self):
        user_id = self.user_id_from_username("instagram")

        first_page, end_cursor = self.cl.usertag_medias_paginated(user_id, amount=2)
        self.assertTaggedMediaPage(first_page, 2)
        self.assertTrue(end_cursor)

        next_page, _ = self.cl.usertag_medias_paginated(user_id, amount=2, end_cursor=end_cursor)
        self.assertTaggedMediaPage(next_page, 2)
        self.assertNoDuplicateMediasAcrossPages(first_page, next_page)

    def test_usertag_medias_paginated_v1_live(self):
        user_id = self.user_id_from_username("instagram")

        first_page, end_cursor = self.cl.usertag_medias_paginated_v1(user_id, amount=2)
        self.assertTaggedMediaPage(first_page, 2)
        self.assertTrue(end_cursor)

        next_page, _ = self.cl.usertag_medias_paginated_v1(user_id, amount=2, end_cursor=end_cursor)
        self.assertTaggedMediaPage(next_page, 2)
        self.assertNoDuplicateMediasAcrossPages(first_page, next_page)


class ClientUserExtendTestCase(_helpers.ClientPrivateTestCase):
    def test_username_from_user_id(self):
        self.assertEqual(self.cl.username_from_user_id(25025320), "instagram")

    def test_user_following(self):
        user_id = self.user_id_from_username("instagram")
        self.cl.user_follow(user_id)
        following = self.cl.user_following(self.cl.user_id, amount=1)
        self.assertIn(user_id, following)
        self.assertEqual(following[user_id].username, "instagram")
        self.assertTrue(len(following) == 1)
        self.assertIsInstance(list(following.values())[0], UserShort)

    def test_user_info(self):
        user_id = self.user_id_from_username("instagram")
        user = self.cl.user_info(user_id)
        self.assertIsInstance(user, User)
        self.assertEqual(user.pk, "25025320")
        self.assertEqual(user.username, "instagram")
        self.assertEqual(user.full_name, "Instagram")
        self.assertFalse(user.is_private)
        self.assertTrue(user.is_verified)
        self.assertTrue(str(user.profile_pic_url).startswith("https://"))

    def test_user_info_by_username(self):
        user = self.user_info_by_username("instagram")
        self.assertIsInstance(user, User)
        self.assertEqual(user.pk, "25025320")
        self.assertEqual(user.full_name, "Instagram")
        self.assertFalse(user.is_private)

    def test_user_medias(self):
        user_id = self.user_id_from_username("instagram")
        medias = self.cl.user_medias(user_id, amount=10)
        self.assertGreater(len(medias), 5)
        media = medias[0]
        self.assertIsInstance(media, Media)
        for field in REQUIRED_MEDIA_FIELDS:
            self.assertTrue(hasattr(media, field))

    def test_usertag_medias(self):
        user_id = self.user_id_from_username("instagram")
        medias = self.cl.usertag_medias(user_id, amount=10)
        self.assertGreater(len(medias), 5)
        media = medias[0]
        self.assertIsInstance(media, Media)
        for field in REQUIRED_MEDIA_FIELDS:
            self.assertTrue(hasattr(media, field))

    def test_user_follow_unfollow(self):
        user_id = self.user_id_from_username("instagram")
        try:
            self.assertTrue(self.cl.user_follow(user_id))
            relationship = self.cl.user_friendship_v1(user_id)
            self.assertTrue(relationship.following)
        finally:
            self.cl.user_unfollow(user_id)
        relationship = self.cl.user_friendship_v1(user_id)
        self.assertFalse(relationship.following)

    # def test_send_new_note(self):
    #     self.cl.create_note("Hello from Instagrapi!", 0)


class ClientFollowRequestLiveTestCase(_helpers.ClientPrivateTestCase):
    def wait_for_pending_user_ids(self, client, expected_user_ids, timeout=30):
        expected_user_ids = {str(user_id) for user_id in expected_user_ids}
        deadline = time.time() + timeout
        last_pending_ids = set()
        while time.time() < deadline:
            pending = client.user_follow_requests(amount=20)
            last_pending_ids = {user.pk for user in pending}
            if expected_user_ids.issubset(last_pending_ids):
                return pending
            time.sleep(2)
        missing = expected_user_ids - last_pending_ids
        self.fail(f"Pending follow requests did not appear for user ids: {missing}")

    def wait_for_no_pending_user_ids(self, client, rejected_user_ids, timeout=30):
        rejected_user_ids = {str(user_id) for user_id in rejected_user_ids}
        deadline = time.time() + timeout
        last_pending_ids = set()
        while time.time() < deadline:
            pending = client.user_follow_requests(amount=20)
            last_pending_ids = {user.pk for user in pending}
            if not rejected_user_ids.intersection(last_pending_ids):
                return pending
            time.sleep(2)
        self.fail(
            "Rejected follow requests are still pending for user ids: "
            f"{rejected_user_ids.intersection(last_pending_ids)}"
        )

    def wait_for_friendship(self, client, user_id, predicate, timeout=30):
        deadline = time.time() + timeout
        last_relationship = None
        while time.time() < deadline:
            last_relationship = client.user_friendship_v1(user_id)
            if last_relationship and predicate(last_relationship):
                return last_relationship
            time.sleep(2)
        self.fail(f"Friendship state did not match for {user_id}: {last_relationship}")

    def cleanup_follow_request_live_clients(self, target, requesters):
        for requester in requesters:
            try:
                requester.user_unfollow(target.user_id)
            except Exception as exc:
                print(f"Follow request live cleanup user_unfollow failed: {exc.__class__.__name__} {exc}")
        try:
            target.account_set_public()
        except Exception as exc:
            print(f"Follow request live cleanup account_set_public failed: {exc.__class__.__name__} {exc}")

    def test_follow_request_helpers_live(self):
        target = self.cl
        requesters = self.fresh_accounts(4, exclude_user_ids={target.user_id})
        single_approve, single_decline, batch_approve, batch_decline = requesters
        requester_ids = [str(requester.user_id) for requester in requesters]

        try:
            self.assertTrue(target.account_set_private())

            for requester in requesters:
                requester.user_follow(target.user_id)

            pending = self.wait_for_pending_user_ids(target, requester_ids)
            pending_ids = {user.pk for user in pending}
            self.assertTrue(set(requester_ids).issubset(pending_ids))
            self.assertTrue(all(isinstance(user, UserShort) for user in pending))

            chunk_users, _ = target.user_follow_requests_chunk(max_amount=20)
            chunk_user_ids = {user.pk for user in chunk_users}
            self.assertTrue(set(requester_ids).issubset(chunk_user_ids))

            listed_users = target.user_follow_requests(amount=20)
            listed_user_ids = {user.pk for user in listed_users}
            self.assertTrue(set(requester_ids).issubset(listed_user_ids))

            self.assertTrue(target.user_follow_request_approve(single_approve.user_id))
            self.wait_for_friendship(
                single_approve,
                target.user_id,
                lambda relationship: relationship.following is True,
            )

            self.assertTrue(target.user_follow_request_decline(single_decline.user_id))
            self.wait_for_no_pending_user_ids(target, {single_decline.user_id})
            self.wait_for_friendship(
                single_decline,
                target.user_id,
                lambda relationship: relationship.following is False and relationship.outgoing_request is False,
            )

            batch_approve_result = target.user_follow_requests_approve([str(batch_approve.user_id)])
            self.assertEqual(batch_approve_result, {str(batch_approve.user_id): True})
            self.wait_for_friendship(
                batch_approve,
                target.user_id,
                lambda relationship: relationship.following is True,
            )

            batch_decline_result = target.user_follow_requests_decline([str(batch_decline.user_id)])
            self.assertEqual(batch_decline_result, {str(batch_decline.user_id): True})
            self.wait_for_no_pending_user_ids(target, {batch_decline.user_id})
            self.wait_for_friendship(
                batch_decline,
                target.user_id,
                lambda relationship: relationship.following is False and relationship.outgoing_request is False,
            )
        finally:
            self.cleanup_follow_request_live_clients(target, requesters)
