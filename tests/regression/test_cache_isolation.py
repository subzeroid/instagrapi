import unittest
from unittest.mock import Mock, patch

from instagrapi import Client

CACHE_NAMES = (
    "_users_cache",
    "_userhorts_cache",
    "_usernames_cache",
    "_users_following",
    "_users_followers",
    "_medias_cache",
    "_stories_cache",
)


class ClientCacheIsolationTestCase(unittest.TestCase):
    def test_clients_have_independent_cache_maps(self):
        first = Client()
        second = Client()

        for cache_name in CACHE_NAMES:
            first_cache = getattr(first, cache_name)
            second_cache = getattr(second, cache_name)
            self.assertIsNot(first_cache, second_cache)
            first_cache["shared-key"] = object()
            self.assertNotIn("shared-key", second_cache)
            second_cache.pop("shared-key", None)
            self.assertIn("shared-key", first_cache)

        third = Client()
        for cache_name in CACHE_NAMES:
            self.assertIn("shared-key", getattr(first, cache_name))
            self.assertNotIn("shared-key", getattr(third, cache_name))

    def test_cached_username_lookup_does_not_cross_clients(self):
        first = Client()
        second = Client()
        first_user = Mock(pk="1", username="shared")
        second_user = Mock(pk="2", username="shared")

        with patch.object(first, "_user_info_by_username_public", return_value=first_user) as first_lookup:
            self.assertEqual(first.user_info_by_username("shared").pk, "1")
        with patch.object(second, "_user_info_by_username_public", return_value=second_user) as second_lookup:
            self.assertEqual(second.user_info_by_username("shared").pk, "2")

        first_lookup.assert_called_once_with("shared")
        second_lookup.assert_called_once_with("shared")
