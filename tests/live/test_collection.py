from tests import helpers as _helpers
from tests.helpers import *


class ClientCollectionTestCase(_helpers.ClientPrivateTestCase):
    def test_collections(self):
        collections = self.cl.collections()
        self.assertTrue(len(collections) > 0)
        collection = collections[0]
        self.assertIsInstance(collection, Collection)
        for field in ("id", "name", "type", "media_count"):
            self.assertTrue(hasattr(collection, field))

    def test_collection_medias_by_name(self):
        medias = self.cl.collection_medias_by_name("Repost")
        self.assertTrue(len(medias) > 0)
        media = medias[0]
        self.assertIsInstance(media, Media)
        for field in REQUIRED_MEDIA_FIELDS:
            self.assertTrue(hasattr(media, field))

    def test_media_save_to_collection(self):
        media_pk = self.cl.media_pk_from_url("https://www.instagram.com/p/B3mr1-OlWMG/")
        collection_pk = self.cl.collection_pk_by_name("Repost")
        # clear and check
        self.cl.media_unsave(media_pk)
        medias = self.cl.collection_medias(collection_pk)
        self.assertNotIn(media_pk, [m.pk for m in medias])
        # save
        self.cl.media_save(media_pk, collection_pk)
        medias = self.cl.collection_medias(collection_pk)
        self.assertIn(media_pk, [m.pk for m in medias])
        # unsave
        self.cl.media_unsave(media_pk, collection_pk)
        medias = self.cl.collection_medias(collection_pk)
        self.assertNotIn(media_pk, [m.pk for m in medias])
