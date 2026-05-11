import importlib

from tests.helpers import *


class UtilsPackageRegressionTestCase(unittest.TestCase):
    def test_legacy_utils_exports_stay_available(self):
        import instagrapi.utils as utils

        self.assertEqual(utils.InstagramIdCodec.decode(utils.InstagramIdCodec.encode(123456789)), 123456789)
        self.assertEqual(utils.dumps({"enabled": True}), '{"enabled":true}')
        self.assertEqual(utils.json_value({"a": [{"b": 1}]}, "a", 0, "b"), 1)
        self.assertTrue(utils.gen_token(8))
        self.assertTrue(utils.gen_password(8))
        self.assertTrue(utils.generate_signature("{}").startswith("signed_body=SIGNATURE."))
        self.assertEqual(utils.generate_jazoest("abc"), "2294")
        self.assertEqual(utils.date_time_original(time.gmtime(0)), "19700101T000000.000Z")

    def test_utils_submodules_are_importable(self):
        expected = {
            "instagrapi.utils.auth": ["gen_token", "generate_signature", "generate_jazoest"],
            "instagrapi.utils.ids": ["InstagramIdCodec"],
            "instagrapi.utils.serialization": ["InstagrapiJSONEncoder", "dumps", "json_value"],
            "instagrapi.utils.timing": ["date_time_original", "random_delay"],
            "instagrapi.utils.validation": ["vassert"],
            "instagrapi.utils.video": ["analyze_video_for_upload", "read_video_metadata"],
        }
        for module_name, names in expected.items():
            module = importlib.import_module(module_name)
            for name in names:
                self.assertTrue(hasattr(module, name), f"{module_name}.{name} is missing")
