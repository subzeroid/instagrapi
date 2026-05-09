from tests import helpers as _helpers
from tests.helpers import *


class ClientStoryTestCase(_helpers.ClientPrivateTestCase):
    def test_story_pk_from_url(self):
        story_pk = self.cl.story_pk_from_url(
            "https://www.instagram.com/stories/instagram/2581281926631793076/"
        )
        self.assertEqual(story_pk, 2581281926631793076)

    def test_upload_photo_story(self):
        media_pk = self.cl.media_pk_from_url("https://www.instagram.com/p/B3mr1-OlWMG/")
        path = self.cl.photo_download(media_pk)
        self.assertIsInstance(path, Path)
        caption = "Test photo caption"
        instagram = self.user_info_by_username("instagram")
        self.assertIsInstance(instagram, User)
        mentions = [StoryMention(user=instagram)]
        medias = [StoryMedia(media_pk=media_pk, x=0.5, y=0.5, width=0.6, height=0.8)]
        links = [StoryLink(webUri="https://instagram.com/")]
        # hashtags = [StoryHashtag(hashtag=self.cl.hashtag_info('instagram'))]
        # locations = [
        #     StoryLocation(
        #         location=Location(
        #             pk=150300262230285,
        #             name='Blaues Wunder (Dresden)',
        #         )
        #     )
        # ]
        stickers = [
            StorySticker(
                id="Igjf05J559JWuef4N5",
                type="gif",
                x=0.5,
                y=0.5,
                width=0.4,
                height=0.08,
            )
        ]
        try:
            story = self.cl.photo_upload_to_story(
                path,
                caption,
                mentions=mentions,
                links=links,
                # hashtags=hashtags,
                # locations=locations,
                stickers=stickers,
                medias=medias,
            )
            self.assertIsInstance(story, Story)
            self.assertTrue(story)
            s = self.cl.story_info(story.pk)
            self.assertIsInstance(s, Story)
            self.assertTrue(s)
            m, sm = medias[0], s.medias[0]
            self.assertEqual(m.media_pk, sm.media_pk)
            self.assertEqual(m.x, sm.x)
            self.assertEqual(m.y, sm.y)
        finally:
            if path:
                cleanup(path)
            self.assertTrue(self.cl.story_delete(story.id))

    def test_upload_video_story(self):
        media_pk = self.cl.media_pk_from_url("https://www.instagram.com/p/Bk2tOgogq9V/")
        story = None
        path = self.cl.video_download(media_pk)
        self.assertIsInstance(path, Path)
        caption = "Test video caption"
        instagram = self.user_info_by_username("instagram")
        self.assertIsInstance(instagram, User)
        mentions = [StoryMention(user=instagram)]
        medias = [StoryMedia(media_pk=media_pk, x=0.5, y=0.5, width=0.6, height=0.8)]
        links = [StoryLink(webUri="https://instagram.com/")]
        # hashtags = [StoryHashtag(hashtag=self.cl.hashtag_info('instagram'))]
        # locations = [
        #     StoryLocation(
        #         location=Location(
        #             pk=150300262230285,
        #             name='Blaues Wunder (Dresden)',
        #         )
        #     )
        # ]
        try:
            buildout = StoryBuilder(
                path, caption, mentions, Path("./examples/background.png")
            ).video(1)
            story = self.cl.video_upload_to_story(
                buildout.path,
                caption,
                mentions=buildout.mentions,
                links=links,
                # hashtags=hashtags,
                # locations=locations,
                medias=medias,
            )
            self.assertIsInstance(story, Story)
            self.assertTrue(story)
            s = self.cl.story_info(story.pk)
            self.assertIsInstance(s, Story)
            self.assertTrue(s)
            m, sm = medias[0], s.medias[0]
            self.assertEqual(m.media_pk, sm.media_pk)
            self.assertEqual(m.x, sm.x)
            self.assertEqual(m.y, sm.y)
        finally:
            cleanup(path)
            if story:
                self.assertTrue(self.cl.story_delete(story.id))

    def test_user_stories(self):
        user_id = self.user_id_from_username("instagram")
        stories = self.cl.user_stories(user_id, 2)
        self.assertEqual(len(stories), 2)
        story = stories[0]
        self.assertIsInstance(story, Story)
        for field in REQUIRED_STORY_FIELDS:
            self.assertTrue(hasattr(story, field))
        stories = self.cl.user_stories(self.user_id_from_username("instagram"))
        self.assertIsInstance(stories, list)

    def test_extract_user_stories(self):
        user_id = self.user_id_from_username("instagram")
        stories_v1 = self.cl.user_stories_v1(user_id, amount=2)
        stories_gql = self.cl.user_stories_gql(user_id, amount=2)
        self.assertEqual(len(stories_v1), 2)
        self.assertIsInstance(stories_v1[0], Story)
        self.assertEqual(len(stories_gql), 2)
        self.assertIsInstance(stories_gql[0], Story)
        for i, gql in enumerate(stories_gql[:2]):
            gql = gql.dict()
            v1 = stories_v1[i].dict()
            for f in REQUIRED_STORY_FIELDS:
                gql_val, v1_val = gql[f], v1[f]
                is_video = v1.get("video_duration") > 0
                if f == "video_url" and is_video:
                    gql_val = gql[f].path.rsplit(".", 1)[1]
                    v1_val = v1[f].path.rsplit(".", 1)[1]
                elif f == "thumbnail_url":
                    self.assertIn(".jpg", gql_val)
                    self.assertIn(".jpg", v1_val)
                    continue
                elif f == "user":
                    gql_val.pop("full_name")
                    v1_val.pop("full_name")
                    gql_val.pop("is_private")
                    v1_val.pop("is_private")
                    gql_val["profile_pic_url"] = gql_val["profile_pic_url"].path
                    v1_val["profile_pic_url"] = v1_val["profile_pic_url"].path
                elif f == "mentions":
                    for item in [*gql_val, *v1_val]:
                        item["user"].pop("pk")
                        item["user"].pop("profile_pic_url")
                        item.pop("width")
                        item.pop("height")
                        item["x"] = round(item["x"], 4)
                        item["y"] = round(item["y"], 4)
                elif f == "links":
                    # [{'webUri': HttpUrl('https://youtu.be/x3GYpar-e64', scheme='https', host='youtu.be', tld='be', host_type='domain', path='/x3GYpar-e64')}]
                    # [{'webUri': HttpUrl('https://l.instagram.com/?u=https%3A%2F%2Fyoutu.be%2Fx3GYpar-e64&e=ATM59nvUNmptw8vUsyoX835T....}]
                    self.assertEqual(len(v1_val), len(gql_val))
                    if gql_val:
                        self.assertIn(
                            gql_val[0]["webUri"].host, v1_val[0]["webUri"].query
                        )
                    continue
                if gql_val != v1_val:
                    import pudb

                    pudb.set_trace()
                self.assertEqual(gql_val, v1_val)

    def test_story_info(self):
        user_id = self.user_id_from_username("instagram")
        stories = self.cl.user_stories(user_id, amount=1)
        story = self.cl.story_info(stories[0].pk)
        self.assertIsInstance(story, Story)
        story = self.cl.story_info(stories[0].id)
        self.assertIsInstance(story, Story)
        self.assertTrue(self.cl.story_seen([story.pk]))


# class BloksTestCase(_helpers.ClientPrivateTestCase):
#
#     def test_bloks_change_password(self):
#         last_json = {
#             'step_name': 'change_password',
#             'step_data': {'new_password1': 'None', 'new_password2': 'None'},
#             'flow_render_type': 3,
#             'bloks_action': 'com.instagram.challenge.navigation.take_challenge',
#             'cni': 12346879508000123,
#             'challenge_context': '{"step_name": "change_password", "cni": 12346879508000123, "is_stateless": false, "challenge_type_enum": "PASSWORD_RESET"}',
#             'challenge_type_enum_str': 'PASSWORD_RESET',
#             'status': 'ok'
#         }
#        self.assertTrue(self.cl.bloks_change_password("2r9j20r9j4230t8hj39tHW4"))
