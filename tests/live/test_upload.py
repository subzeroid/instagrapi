from tests import helpers as _helpers
from tests.helpers import *


class ClienUploadTestCase(_helpers.ClientPrivateTestCase):
    def get_location(self):
        location = self.cl.location_search(lat=59.939095, lng=30.315868)[0]
        self.assertIsInstance(location, Location)
        return location

    def assertLocation(self, location):
        # Instagram sometimes changes location by GEO coordinates:
        locations = [
            dict(
                pk=213597007,
                name="Palace Square",
                lat=59.939166666667,
                lng=30.315833333333,
            ),
            dict(
                pk=107617247320879,
                name="Russia, Saint-Petersburg",
                address="Russia, Saint-Petersburg",
                lat=59.93318,
                lng=30.30605,
                external_id=107617247320879,
                external_id_source="facebook_places",
            ),
        ]
        for data in locations:
            if data["pk"] == location.pk:
                break
        for key, val in data.items():
            itm = getattr(location, key)
            if isinstance(val, float):
                val = round(val, 2)
                itm = round(itm, 2)
            self.assertEqual(itm, val)

    def test_photo_upload_without_location(self):
        media_pk = self.cl.media_pk_from_url("https://www.instagram.com/p/BVDOOolFFxg/")
        path = self.cl.photo_download(media_pk)
        self.assertIsInstance(path, Path)
        try:
            media = self.cl.photo_upload(path, "Test caption for photo")
            self.assertIsInstance(media, Media)
            self.assertEqual(media.caption_text, "Test caption for photo")
            self.assertFalse(media.location)
        finally:
            cleanup(path)
            self.assertTrue(self.cl.media_delete(media.id))

    def test_photo_upload(self):
        media_pk = self.cl.media_pk_from_url("https://www.instagram.com/p/BVDOOolFFxg/")
        path = self.cl.photo_download(media_pk)
        self.assertIsInstance(path, Path)
        try:
            media = self.cl.photo_upload(
                path, "Test caption for photo", location=self.get_location()
            )
            self.assertIsInstance(media, Media)
            self.assertEqual(media.caption_text, "Test caption for photo")
            self.assertLocation(media.location)
        finally:
            cleanup(path)
            self.assertTrue(self.cl.media_delete(media.id))

    def test_video_upload(self):
        media_pk = self.cl.media_pk_from_url("https://www.instagram.com/p/Bk2tOgogq9V/")
        path = self.cl.video_download(media_pk)
        self.assertIsInstance(path, Path)
        try:
            media = self.cl.video_upload(
                path, "Test caption for video", location=self.get_location()
            )
            self.assertIsInstance(media, Media)
            self.assertEqual(media.caption_text, "Test caption for video")
            self.assertLocation(media.location)
        finally:
            cleanup(path)
            self.assertTrue(self.cl.media_delete(media.id))

    def test_album_upload(self):
        media_pk = self.cl.media_pk_from_url("https://www.instagram.com/p/BjNLpA1AhXM/")
        paths = self.cl.album_download(media_pk)
        [self.assertIsInstance(path, Path) for path in paths]
        try:
            instagram = self.user_info_by_username("instagram")
            usertag = Usertag(user=instagram, x=0.5, y=0.5)
            location = self.get_location()
            media = self.cl.album_upload(
                paths, "Test caption for album", usertags=[usertag], location=location
            )
            self.assertIsInstance(media, Media)
            self.assertEqual(media.caption_text, "Test caption for album")
            self.assertEqual(len(media.resources), 3)
            self.assertLocation(media.location)
            keep_path(media.usertags[0].user)
            keep_path(usertag.user)
            self.assertEqual(media.usertags, [usertag])
        finally:
            cleanup(*paths)
            self.assertTrue(self.cl.media_delete(media.id))

    def test_igtv_upload(self):
        media_pk = self.cl.media_pk_from_url(
            "https://www.instagram.com/tv/B91gKCcpnTk/"
        )
        path = self.cl.igtv_download(media_pk)
        self.assertIsInstance(path, Path)
        try:
            title = "6/6: The Transceiver Failure"
            caption_text = "Test caption for IGTV"
            media = self.cl.igtv_upload(
                path, title, caption_text, location=self.get_location()
            )
            self.assertIsInstance(media, Media)
            self.assertEqual(media.title, title)
            self.assertEqual(media.caption_text, caption_text)
            self.assertLocation(media.location)
        finally:
            cleanup(path)
            self.assertTrue(self.cl.media_delete(media.id))

    def test_clip_upload(self):
        # media_type: 2 (video, not IGTV)
        # product_type: clips
        media_pk = self.cl.media_pk_from_url("https://www.instagram.com/p/CEjXskWJ1on/")
        path = self.cl.clip_download(media_pk)
        self.assertIsInstance(path, Path)
        try:
            # location = self.get_location()
            caption_text = "Upload clip"
            media = self.cl.clip_upload(
                path,
                caption_text,
                # location=location
            )
            self.assertIsInstance(media, Media)
            self.assertEqual(media.caption_text, caption_text)
            # self.assertLocation(media.location)
        finally:
            cleanup(path)
            self.assertTrue(self.cl.media_delete(media.id))

    def test_reel_upload_with_music(self):
        # media_type: 2 (video, not IGTV)
        # product_type: reels

        media_pk = self.cl.media_pk_from_url("https://www.instagram.com/p/CEjXskWJ1on/")
        path = self.cl.clip_download(media_pk)
        self.assertIsInstance(path, Path)
        try:
            title = "Kill My Vibe (feat. Tom G)"
            caption = "Test caption for reel"
            track = self.cl.search_music(title)[0]
            media = self.cl.clip_upload_as_reel_with_music(path, caption, track)
            self.assertIsInstance(media, Media)
            self.assertEqual(media.caption_text, caption)
        finally:
            cleanup(path)
            self.assertTrue(self.cl.media_delete(media.id))
