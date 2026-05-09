from tests.helpers import *


class LocationMixinRegressionTestCase(unittest.TestCase):
    def test_location_search_name_handles_top_search_place_wrapper(self):
        client = Client()
        client.top_search = lambda query: {
            "places": [
                {
                    "place": {
                        "location": {
                            "pk": "123",
                            "name": "Choroni",
                            "address": "Aragua, Venezuela",
                            "lat": 10.5,
                            "lng": -67.6,
                            "facebook_places_id": 456,
                            "external_source": "facebook_places",
                        }
                    }
                }
            ]
        }

        locations = client.location_search_name("Choroni")
        self.assertEqual(len(locations), 1)
        self.assertEqual(locations[0].pk, 123)
        self.assertEqual(locations[0].external_id, 456)

    def test_extract_location_coerces_external_id_to_int(self):
        """IG sometimes ships external_id as a numeric string."""
        from instagrapi.extractors import extract_location

        location = extract_location(
            {
                "pk": "239130043",
                "name": "Choroni",
                "external_id": "108835465815492",
            }
        )
        self.assertEqual(location.external_id, 108835465815492)

    def test_extract_location_handles_missing_external_id(self):
        """IG returns None / '' / the literal 'None' for degraded location
        payloads — used to crash media_info_gql with a pydantic
        int_parsing error. See issue #72."""
        from instagrapi.extractors import extract_location

        for raw in (None, "", "None"):
            with self.subTest(external_id=raw):
                location = extract_location(
                    {"pk": "1", "name": "Nowhere", "external_id": raw}
                )
                self.assertIsNone(location.external_id)

    def test_extract_location_falls_back_to_facebook_places_id(self):
        from instagrapi.extractors import extract_location

        location = extract_location(
            {
                "pk": "1",
                "name": "Choroni",
                "facebook_places_id": "456",
            }
        )
        self.assertEqual(location.external_id, 456)

    def test_location_search_pk_returns_exact_match(self):
        client = Client()
        client.location_info = lambda pk: Location(pk=str(pk), name="Choroni")
        client.top_search = lambda query: {
            "places": [
                {"place": {"location": {"pk": "111", "name": "Choroni"}}},
                {
                    "place": {
                        "location": {
                            "pk": "239130043",
                            "name": "Choroni",
                            "facebook_places_id": 108835465815492,
                            "external_source": "facebook_places",
                        }
                    }
                },
            ]
        }

        location = client.location_search_pk(239130043)
        self.assertEqual(location.pk, 239130043)
        self.assertEqual(location.external_id, 108835465815492)
