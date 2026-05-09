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
