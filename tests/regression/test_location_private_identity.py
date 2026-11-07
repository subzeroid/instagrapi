import json
import unittest
from unittest.mock import Mock

from instagrapi.exceptions import ClientConnectionError, ClientThrottledError, LoginRequired
from instagrapi.extractors import extract_location
from instagrapi.mixins.location import LocationMixin
from instagrapi.types import Location


class PrivateLocationIdentityTestCase(unittest.TestCase):
    def setUp(self):
        self.client = LocationMixin()
        self.payload = {
            "location_id": "6889842",
            "name": "Times Square",
            "facebook_places_id": "987654321",
            "lat": None,
            "lng": None,
            "phone": "venue phone",
            "hours": {"schedule": []},
        }
        self.client.private_request = Mock(side_effect=lambda *a, **kw: dict(self.payload))
        self.client.top_search = Mock(side_effect=AssertionError("Unexpected legacy search"))

    def test_private_facebook_id_supplies_missing_source_without_coordinates(self):
        for raw_id in ("987654321", 987654321):
            with self.subTest(raw_id=raw_id):
                self.payload["facebook_places_id"] = raw_id
                location = self.client.location_info(6889842)
                self.assertEqual(location.pk, 6889842)
                self.assertEqual(location.external_id, 987654321)
                self.assertEqual(location.external_id_source, "facebook_places")
                self.assertIsNone(location.lat)
                self.assertIsNone(location.lng)
        self.client.private_request.assert_called_with("locations/6889842/location_info/")

    def test_source_is_not_inferred_for_generic_or_unusable_external_ids(self):
        for fields in (
            {"facebook_places_id": None},
            {"facebook_places_id": ""},
            {"facebook_places_id": "None"},
            {"facebook_places_id": 0},
            {"facebook_places_id": -1},
            {"facebook_places_id": True},
            {"facebook_places_id": 1.5},
            {"external_id": "123"},
            {"external_id": "987654321"},
            {"external_id": "None"},
        ):
            with self.subTest(fields=fields):
                self.payload.update(fields)
                location = self.client.location_info(6889842)
                self.assertIsNone(location.external_id_source)
                self.payload.pop("external_id", None)
                self.payload["facebook_places_id"] = "987654321"
        self.payload.pop("facebook_places_id")
        location = self.client.location_info(6889842)
        self.assertIsNone(location.external_id_source)

    def test_explicit_source_keys_are_preserved_even_when_empty(self):
        for key in ("external_id_source", "external_source"):
            for source in ("custom_provider", "facebook_places", None, ""):
                with self.subTest(key=key, source=source):
                    self.payload[key] = source
                    location = self.client.location_info(6889842)
                    self.assertEqual(location.external_id_source, source)
                    self.payload.pop(key)
        self.payload.update(external_id_source=None, external_source="custom_provider")
        location = self.client.location_info(6889842)
        self.assertIsNone(location.external_id_source)

    def test_generic_extractor_does_not_guess_source(self):
        self.assertIsNone(extract_location(dict(self.payload)).external_id_source)

    def test_exact_private_identity_skips_legacy_and_preserves_metadata(self):
        location = self.client.location_search_pk(6889842)
        self.assertEqual(location.pk, 6889842)
        self.assertEqual(location.phone, "venue phone")
        self.assertEqual(location.hours, {"schedule": []})
        self.assertEqual(location.external_id_source, "facebook_places")
        self.client.top_search.assert_not_called()
        self.client.private_request.assert_called_once_with("locations/6889842/location_info/")

    def test_build_serializes_private_identity_without_legacy(self):
        payload = json.loads(self.client.location_build(Location(pk=6889842, name="Input name")))
        self.assertEqual(payload["name"], "Times Square")
        self.assertEqual(payload["facebook_places_id"], 987654321)
        self.assertEqual(payload["external_source"], "facebook_places")
        self.assertIsNone(payload["lat"])
        self.assertIsNone(payload["lng"])
        self.client.top_search.assert_not_called()
        self.client.private_request.assert_called_once_with("locations/6889842/location_info/")

    def test_complete_can_use_private_identity_when_coordinates_are_missing(self):
        location = self.client.location_complete(Location(pk=6889842, name="Times Square"))
        self.assertEqual(location.external_id, 987654321)
        self.assertEqual(location.external_id_source, "facebook_places")
        self.assertIsNone(location.lat)
        self.assertIsNone(location.lng)
        self.client.top_search.assert_not_called()

    def test_incomplete_private_identity_retains_exact_pk_search_fallback(self):
        for fields in (
            {"facebook_places_id": None},
            {"external_source": None},
            {"facebook_places_id": 0, "external_source": "facebook_places"},
            {"facebook_places_id": -1, "external_source": "facebook_places"},
        ):
            with self.subTest(fields=fields):
                payload = dict(self.payload, **fields)
                self.client.private_request = Mock(return_value=payload)
                exact = {
                    "pk": "6889842",
                    "name": "Match",
                    "facebook_places_id": "42",
                    "external_source": "facebook_places",
                }
                self.client.top_search = Mock(return_value={"places": [{"pk": "123", "name": "Other"}, exact]})
                location = self.client.location_search_pk(6889842)
                self.assertEqual(location.pk, 6889842)
                self.assertEqual(location.external_id, 42)
                self.client.top_search.assert_called_once_with("Times Square")

    def test_complete_private_identity_with_different_pk_does_not_skip_search(self):
        self.payload.update(location_id="123", external_source="facebook_places")
        self.client.top_search = Mock(return_value={"places": [{"pk": "6889842", "name": "Match"}]})
        location = self.client.location_search_pk(6889842)
        self.assertEqual(location.pk, 6889842)
        self.client.top_search.assert_called_once_with("Times Square")

    def test_private_request_failures_propagate_without_legacy_retry(self):
        for error in (ClientConnectionError, ClientThrottledError, LoginRequired):
            with self.subTest(error=error):
                self.client.private_request = Mock(side_effect=error("Private failure"))
                with self.assertRaises(error):
                    self.client.location_build(Location(pk=6889842, name="Times Square"))
                self.client.top_search.assert_not_called()
