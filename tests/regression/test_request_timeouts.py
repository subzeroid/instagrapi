from io import BytesIO
from unittest import mock

import pytest
import requests

from instagrapi import Client
from instagrapi.mixins.user import UserMixin


@pytest.fixture(params=[{}, {"request_timeout": 0}, {"request_timeout": 7}], ids=["default", "zero", "custom"])
def client(request):
    return Client(**request.param)


@pytest.fixture(params=[None, 30], ids=["default-read-timeout", "custom-read-timeout"])
def read_timeout(client, request):
    if request.param is not None:
        client.read_timeout = request.param
    return 25 if request.param is None else request.param


def test_share_link_resolution_uses_read_timeout(client, read_timeout):
    url = "https://www.instagram.com/share/p/example/"
    response = requests.Response()
    response.status_code = 302
    response.headers["Location"] = "https://www.instagram.com/p/B1LbfVPlwIA/"

    with mock.patch.object(client.public, "get", return_value=response) as get:
        media_pk = client.media_pk_from_url(url)

    assert media_pk == "2110901750722920960"
    get.assert_called_once_with(
        url,
        proxies=client.public.proxies,
        timeout=read_timeout,
        allow_redirects=False,
    )


@pytest.mark.parametrize("media_type, extension", [("track", "m4a"), ("photo", "jpg"), ("video", "mp4")])
def test_media_download_uses_read_timeout(client, read_timeout, tmp_path, media_type, extension):
    url = f"https://example.com/media.{extension}"
    content = b"downloaded media bytes"
    response = requests.Response()
    response.status_code = 200
    response.headers["Content-Length"] = str(len(content))
    response.raw = BytesIO(content)

    with mock.patch(f"instagrapi.mixins.{media_type}.requests.get", return_value=response) as get:
        path = getattr(client, f"{media_type}_download_by_url")(url, filename="download", folder=tmp_path)

    assert path == tmp_path / f"download.{extension}"
    assert path.read_bytes() == content
    get.assert_called_once_with(url, stream=True, timeout=read_timeout)


@pytest.mark.parametrize("media_type, extension", [("photo", "jpg"), ("video", "mp4")])
def test_media_download_origin_uses_read_timeout(client, read_timeout, media_type, extension):
    url = f"https://example.com/media.{extension}"
    content = b"downloaded media bytes"
    response = requests.Response()
    response.status_code = 200
    response.headers["Content-Length"] = str(len(content))
    response.raw = BytesIO(content)

    with mock.patch(f"instagrapi.mixins.{media_type}.requests.get", return_value=response) as get:
        result = getattr(client, f"{media_type}_download_by_url_origin")(url)

    assert result == content
    get.assert_called_once_with(url, stream=True, timeout=read_timeout)


def test_story_download_uses_read_timeout(client, read_timeout, tmp_path):
    url = "https://example.com/story.mp4"
    content = b"downloaded story bytes"
    response = requests.Response()
    response.status_code = 200
    response.url = url
    response.headers["Content-Length"] = str(len(content))
    response.raw = BytesIO(content)
    client.last_response_ts = 0

    with (
        mock.patch.object(client.public, "get", return_value=response) as get,
        mock.patch("instagrapi.mixins.public.time.sleep") as sleep,
    ):
        path = client.story_download_by_url(url, filename="download", folder=tmp_path)

    assert path == tmp_path / "download.mp4"
    assert path.read_bytes() == content
    get.assert_called_once_with(
        url,
        params=None,
        headers=None,
        proxies=client.public.proxies,
        stream=True,
        timeout=read_timeout,
    )
    if client.request_timeout:
        sleep.assert_called_once_with(client.request_timeout)
    else:
        sleep.assert_not_called()


def test_user_mixin_fetch_fb_dtsg_uses_read_timeout(client, read_timeout):
    response = requests.Response()
    response.status_code = 200
    response._content = b'<html><script id="__eqmc">{"f":"synthetic-dtsg"}</script></html>'

    with (
        mock.patch.object(client.public, "get", return_value=response) as get,
        mock.patch.object(client.graphql, "get", side_effect=AssertionError("unexpected GraphQL request")),
    ):
        result = UserMixin.fetch_fb_dtsg(client)

    assert result == "synthetic-dtsg"
    get.assert_called_once_with(client.PUBLIC_API_URL, proxies=client.public.proxies, timeout=read_timeout)


def test_public_head_uses_read_timeout(client, read_timeout):
    url = "https://www.instagram.com/share/p/example/"
    response = requests.Response()
    response.status_code = 302
    response.headers["Location"] = "https://www.instagram.com/p/B1LbfVPlwIA/"

    with mock.patch.object(client.public, "head", return_value=response) as head:
        result = client.public_head(url)

    assert result.status_code == 302
    assert result.headers["Location"] == "https://www.instagram.com/p/B1LbfVPlwIA/"
    head.assert_called_once_with(
        url,
        allow_redirects=False,
        proxies=client.public.proxies,
        timeout=read_timeout,
    )


@pytest.mark.parametrize("surface", ["public", "private"])
def test_read_timeout_preserves_request_pacing(client, surface):
    client.read_timeout = 30
    client.last_response_ts = 0
    response = requests.Response()
    response.status_code = 200
    response.url = "https://www.instagram.com/api/test/"
    response._content = b'{"status": "ok"}'
    response.raw = BytesIO(response.content)
    response.request = requests.Request("GET", response.url).prepare()

    with (
        mock.patch.object(getattr(client, surface), "get", return_value=response),
        mock.patch(f"instagrapi.mixins.{surface}.time.sleep") as sleep,
    ):
        if surface == "public":
            result = client._send_public_request(response.url, return_json=True)
        else:
            result = client._send_private_request("test/")

    assert result == {"status": "ok"}
    if surface == "public" and client.request_timeout == 0:
        sleep.assert_not_called()
    else:
        sleep.assert_called_once_with(client.request_timeout)


@pytest.mark.parametrize("request_timeout", [0, 7])
def test_settings_preserve_request_pacing(request_timeout):
    client = Client(settings={"request_timeout": request_timeout})
    client.read_timeout = 30

    assert client.request_timeout == request_timeout
    assert client.get_settings()["request_timeout"] == request_timeout
