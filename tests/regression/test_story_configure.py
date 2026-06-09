from tests.helpers import *


class StoryConfigureRegressionTestCase(unittest.TestCase):
    def build_client(self):
        client = Client()
        client.settings = {}
        client._user_id = "1"
        client.uuid = "uuid"
        client.android_device_id = "device"
        client.client_session_id = "client-session"
        client.timezone_offset = 0
        client.set_device({})
        client.with_default_data = lambda data: data
        return client

    def build_location(self):
        return Location(
            pk=213597007,
            name="Palace Square",
            address="Palace Square, Saint Petersburg",
            lat=59.939166,
            lng=30.315833,
            external_id=107617247320879,
            external_id_source="facebook_places",
        )

    def assert_story_location_model(self, data):
        self.assertEqual(data["story_sticker_ids"], "location_sticker")

        tap_models = json.loads(data["tap_models"])
        self.assertEqual(len(tap_models), 1)
        location_model = tap_models[0]
        self.assertEqual(location_model["type"], "location")
        self.assertTrue(location_model["is_sticker"])
        self.assertEqual(location_model["tap_state"], 0)
        self.assertEqual(location_model["tap_state_str_id"], "location_sticker_vibrant")
        self.assertNotIn("location", location_model)
        self.assertEqual(location_model["location_id"], "107617247320879")

    def test_photo_story_sticker_ids_include_all_stickers(self):
        client = self.build_client()

        with mock.patch.object(client, "private_request") as private_request:
            private_request.side_effect = [
                {"status": "ok"},
                {"status": "ok"},
            ]
            client.photo_configure_to_story(
                upload_id="1",
                width=720,
                height=1280,
                caption="",
                links=[StoryLink(webUri="https://example.com")],
                hashtags=[
                    StoryHashtag(
                        hashtag=Hashtag(id="1", name="example"),
                        x=0.2,
                        y=0.3,
                        width=0.5,
                        height=0.2,
                    )
                ],
            )

        validate_args, _ = private_request.call_args_list[0]
        self.assertEqual(validate_args[1]["url"], "https://example.com/")
        configure_args, _ = private_request.call_args_list[1]
        self.assertEqual(
            configure_args[1]["story_sticker_ids"],
            "hashtag_sticker,link_sticker_default",
        )

    def test_photo_story_location_uses_external_location_id_tap_model(self):
        client = self.build_client()
        location = self.build_location()

        with mock.patch.object(client, "location_complete", return_value=location):
            with mock.patch.object(client, "private_request") as private_request:
                private_request.return_value = {"status": "ok"}
                client.photo_configure_to_story(
                    upload_id="1",
                    width=720,
                    height=1280,
                    caption="",
                    locations=[
                        StoryLocation(
                            location=location,
                            x=0.2,
                            y=0.3,
                            width=0.4,
                            height=0.1,
                        )
                    ],
                )

        configure_args, _ = private_request.call_args
        self.assertEqual(configure_args[0], "media/configure_to_story/")
        self.assert_story_location_model(configure_args[1])

    def test_photo_story_interactive_metadata_builds_tap_models(self):
        client = self.build_client()
        location = self.build_location()
        user = UserShort(pk="2", username="artist", full_name="Artist", profile_pic_url=None)
        hashtag = Hashtag(id="1", name="event")

        with mock.patch.object(client, "location_complete", return_value=location):
            with mock.patch.object(client, "private_request") as private_request:
                private_request.side_effect = [
                    {"status": "ok"},
                    {"status": "ok"},
                ]
                client.photo_configure_to_story(
                    upload_id="1",
                    width=720,
                    height=1280,
                    caption="",
                    mentions=[StoryMention(user=user, x=0.2, y=0.3, width=0.4, height=0.1)],
                    links=[StoryLink(webUri="https://example.com")],
                    hashtags=[StoryHashtag(hashtag=hashtag, x=0.3, y=0.4, width=0.4, height=0.1)],
                    locations=[StoryLocation(location=location, x=0.4, y=0.5, width=0.4, height=0.1)],
                )

        configure_args, _ = private_request.call_args_list[1]
        data = configure_args[1]
        tap_models = json.loads(data["tap_models"])
        self.assertEqual(
            [model["type"] for model in tap_models],
            ["mention", "hashtag", "location", "story_link"],
        )
        self.assertEqual(
            data["story_sticker_ids"],
            "hashtag_sticker,location_sticker,link_sticker_default",
        )
        self.assertIn("reel_mentions", data)

    def test_video_story_location_uses_external_location_id_tap_model(self):
        client = self.build_client()
        location = self.build_location()

        with mock.patch.object(client, "location_complete", return_value=location):
            with mock.patch.object(client, "private_request") as private_request:
                private_request.return_value = {"status": "ok"}
                client.video_configure_to_story(
                    upload_id="1",
                    width=720,
                    height=1280,
                    duration=3,
                    thumbnail=Path("thumbnail.jpg"),
                    caption="",
                    locations=[
                        StoryLocation(
                            location=location,
                            x=0.2,
                            y=0.3,
                            width=0.4,
                            height=0.1,
                        )
                    ],
                )

        configure_args, _ = private_request.call_args
        self.assertEqual(configure_args[0], "media/configure_to_story/?video=1")
        self.assert_story_location_model(configure_args[1])
