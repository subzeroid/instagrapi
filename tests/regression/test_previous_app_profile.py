from instagrapi import Client

PREVIOUS_APP = "428.0.0.47.67"
PREVIOUS_CODE = "961145276"
PREVIOUS_BLOKS = "7189b949425f9bf80ea8bd880cf5a3080b292d9b1c4b38a18d112f7c4b71e7a8"


def test_restore_previous_default_profile_hydrates_bloks_without_changing_device():
    client = Client({"device_settings": {"app_version": PREVIOUS_APP, "version_code": PREVIOUS_CODE}})
    assert client.device_settings["app_version"] == PREVIOUS_APP
    assert client.device_settings["version_code"] == PREVIOUS_CODE
    assert client._bloks_payload({})["bloks_versioning_id"] == PREVIOUS_BLOKS


def test_explicit_previous_default_app_still_selects_its_matching_profile():
    client = Client()
    client.set_app(PREVIOUS_APP)
    assert client.device_settings["app_version"] == PREVIOUS_APP
    assert client.device_settings["version_code"] == PREVIOUS_CODE
    assert client._bloks_payload({})["bloks_versioning_id"] == PREVIOUS_BLOKS
