import base64

from tests import helpers as _helpers
from tests.helpers import *


class ClientLocationTestCase(_helpers.ClientPrivateTestCase):
    def test_location_search(self):
        loc = self.cl.location_search(51.0536111111, 13.8108333333)[0]
        self.assertIsInstance(loc, Location)
        self.assertIn("Dresden", loc.name)
        self.assertIn("Dresden", loc.address)
        self.assertEqual(150300262230285, loc.external_id)
        self.assertEqual("facebook_places", loc.external_id_source)

    def test_location_complete_pk(self):
        source = Location(
            name="Daily Surf Supply",
            external_id=533689780360041,
            external_id_source="facebook_places",
        )
        result = self.cl.location_complete(source)
        self.assertIsInstance(result, Location)
        self.assertEqual(result.pk, 533689780360041)

    def test_location_complete_lat_lng(self):
        source = Location(
            pk=150300262230285,
            name="Blaues Wunder (Dresden)",
        )
        result = self.cl.location_complete(source)
        self.assertIsInstance(result, Location)
        self.assertEqual(result.lat, 51.0536111111)
        self.assertEqual(result.lng, 13.8108333333)

    def test_location_complete_external_id(self):
        source = Location(name="Blaues Wunder (Dresden)", lat=51.0536111111, lng=13.8108333333)
        result = self.cl.location_complete(source)
        self.assertIsInstance(result, Location)
        self.assertEqual(result.external_id, 150300262230285)
        self.assertEqual(result.external_id_source, "facebook_places")

    def test_location_build(self):
        loc = self.cl.location_info(150300262230285)
        self.assertIsInstance(loc, Location)
        json_data = self.cl.location_build(loc)
        self.assertIsInstance(json_data, str)
        data = json.loads(json_data)
        self.assertIsInstance(data, dict)
        self.assertDictEqual(
            data,
            {
                "name": "Blaues Wunder (Dresden)",
                "address": "Dresden, Germany",
                "lat": 51.053611111111,
                "lng": 13.810833333333,
                "facebook_places_id": 150300262230285,
                "external_source": "facebook_places",
            },
        )

    def test_location_info(self):
        loc = self.cl.location_info(150300262230285)
        self.assertIsInstance(loc, Location)
        self.assertEqual(loc.pk, 150300262230285)
        self.assertEqual(loc.name, "Blaues Wunder (Dresden)")
        self.assertEqual(loc.lng, 13.8108333333)
        self.assertEqual(loc.lat, 51.0536111111)

    def test_location_info_without_lat_lng(self):
        loc = self.cl.location_info(197780767581661)
        self.assertIsInstance(loc, Location)
        self.assertEqual(loc.pk, 197780767581661)
        self.assertEqual(loc.name, "In The Clouds")

    def test_location_medias_top(self):
        medias = self.cl.location_medias_top(197780767581661, amount=2)
        self.assertEqual(len(medias), 2)
        self.assertIsInstance(medias[0], Media)

    def test_location_medias_recent(self):
        medias = self.cl.location_medias_recent(197780767581661, amount=2)
        self.assertEqual(len(medias), 2)
        self.assertIsInstance(medias[0], Media)


class ClientLocationPaginationLiveTestCase(_helpers.ClientPrivateTestCase):
    def __init__(self, *args, **kwargs):
        self.cl = None
        return unittest.TestCase.__init__(self, *args, **kwargs)

    def setup_method(self, *args, **kwargs):
        return None

    def setUp(self):
        if not TEST_ACCOUNTS_URL:
            self.skipTest("TEST_ACCOUNTS_URL is required for location pagination live tests")
        try:
            self.cl = self.fresh_account()
        except Exception as exc:
            self.skipTest(str(exc))

    def test_location_medias_v1_chunk_live_cursor_shape(self):
        medias, max_id = self.cl.location_medias_v1_chunk(197780767581661, tab_key="recent")
        self.assertIsInstance(medias, list)
        if medias:
            self.assertIsInstance(medias[0], Media)
        if not max_id:
            return

        next_max_id, page, media_ids = json.loads(base64.b64decode(max_id))
        self.assertTrue(next_max_id)
        self.assertIsInstance(page, int)
        self.assertIsInstance(media_ids, list)

        next_medias, _ = self.cl.location_medias_v1_chunk(197780767581661, tab_key="recent", max_id=max_id)
        self.assertIsInstance(next_medias, list)
        if next_medias:
            self.assertIsInstance(next_medias[0], Media)
