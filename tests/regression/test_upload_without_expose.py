from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock

import pytest

from instagrapi.exceptions import ClientNotFoundError
from instagrapi.types import Media, Story
from tests.regression import test_upload as upload_tests

UPLOADS = [
    ("photo_upload", "media/configure/", 1, Media),
    ("photo_upload_to_story", "media/configure_to_story/", 1, Story),
    ("album_upload", "media/configure_sidecar/", 8, Media),
    ("video_upload", "media/configure/?video=1", 2, Media),
    ("video_upload_to_story", "media/configure_to_story/?video=1", 2, Story),
    ("clip_upload", "media/configure_to_clips/?video=1", 2, Media),
    ("igtv_upload", "media/configure_to_igtv/?video=1", 2, Media),
]


@pytest.fixture
def upload_client(monkeypatch, tmp_path):
    helpers = upload_tests.UploadRegressionTestCase()
    client = helpers.build_client()
    del client.expose
    video = tmp_path / "video.mp4"
    video.write_bytes(b"synthetic-video")
    thumbnail = tmp_path / "thumbnail.jpg"
    monkeypatch.setattr(client, "_current_media_ids", Mock(return_value=set()))
    monkeypatch.setattr(client, "_current_story_ids", Mock(return_value=set()))
    monkeypatch.setattr(client, "photo_rupload", Mock(side_effect=[(str(i), 720, 1280) for i in range(10, 14)]))
    monkeypatch.setattr(client, "video_rupload", Mock(return_value=("20", 720, 1280, 5, thumbnail)))
    monkeypatch.setattr(client.private, "get", Mock(return_value=Mock(status_code=200)))
    monkeypatch.setattr(client.private, "post", Mock(return_value=Mock(status_code=200)))
    monkeypatch.setattr("instagrapi.mixins.clip.analyze_video", Mock(return_value=(thumbnail, 720, 1280, 5)))
    monkeypatch.setattr("instagrapi.mixins.igtv.analyze_video", Mock(return_value=(thumbnail, 720, 1280, 5)))
    monkeypatch.setattr("time.sleep", Mock())
    yield client, helpers, video
    client.private.close()
    client.public.close()


def upload(client, method, video):
    if method == "album_upload":
        return client.album_upload([Path("first.jpg"), Path("second.jpg")], "caption")
    if method == "igtv_upload":
        return client.igtv_upload(video, "title", "caption")
    path = Path("photo.jpg") if method.startswith("photo_") else video
    return getattr(client, method)(path, "caption")


@pytest.mark.parametrize("method,endpoint,media_type,result_type", UPLOADS, ids=[row[0] for row in UPLOADS])
def test_upload_returns_configured_result_without_exposure(
    upload_client, monkeypatch, method, endpoint, media_type, result_type
):
    client, helpers, video = upload_client
    media = helpers.build_media_payload(media_type=media_type)
    if media_type == 8:
        media["carousel_media"] = [helpers.build_media_payload(1), helpers.build_media_payload(1)]
        media["carousel_media"][1].update(pk="2", id="2_1")

    def request(request_endpoint, *args, **kwargs):
        if request_endpoint == "qe/expose/":
            raise ClientNotFoundError("Exposure endpoint is unavailable")
        assert request_endpoint == endpoint
        client.last_json = {"status": "ok", "media": deepcopy(media)}
        return client.last_json

    private_request = Mock(side_effect=request)
    monkeypatch.setattr(client, "private_request", private_request)

    result = upload(client, method, video)

    assert isinstance(result, result_type)
    assert result.id == "1_1"
    assert result.media_type == media_type
    if isinstance(result, Media):
        assert result.caption_text == "caption"
    assert [call.args[0] for call in private_request.call_args_list] == [endpoint]
    if media_type == 8:
        assert len(result.resources) == 2


@pytest.mark.parametrize("method,endpoint,media_type,result_type", UPLOADS, ids=[row[0] for row in UPLOADS])
def test_upload_preserves_configure_error(upload_client, monkeypatch, method, endpoint, media_type, result_type):
    client, _, video = upload_client
    error = ClientNotFoundError("Configure endpoint is unavailable")
    private_request = Mock(side_effect=error)
    monkeypatch.setattr(client, "private_request", private_request)

    with pytest.raises(ClientNotFoundError) as caught:
        upload(client, method, video)

    assert caught.value is error
    assert [call.args[0] for call in private_request.call_args_list] == [endpoint]
