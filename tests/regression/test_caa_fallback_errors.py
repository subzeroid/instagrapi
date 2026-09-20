"""CAA failures must not be replaced by an earlier legacy-login error."""

import json
from unittest.mock import Mock

import pytest
import requests

from instagrapi import Client
from instagrapi.exceptions import BadPassword, ClientThrottledError, FeedbackRequired, RateLimitError, UnknownError

LOGIN = "https://i.instagram.com/api/v1/accounts/login/"
CAA = "https://b.i.instagram.com/api/v1/bloks/async_action/com.bloks.www.bloks.caa.login.async.send_login_request/"


def login_responses(monkeypatch, *, entrypoint, legacy_error, caa_status, caa_body):
    client = Client(private_transport="requests", settings={"session_retry_total": 0, "request_timeout": 0})
    client.private.trust_env = False
    client.public.trust_env = False
    client.caa_aac = '{"aaccs":"synthetic-context"}'
    client.pre_login_flow = Mock(return_value=True)
    client.password_encrypt = Mock(return_value="#PWD_INSTAGRAM:4:1:synthetic")
    client.bloks_caa_login_prepare = Mock(return_value=True)
    client.login_flow = Mock(side_effect=AssertionError("Failed login must not finalize"))
    responses = []
    sequence = []
    if entrypoint == "login":
        sequence.append(
            (CAA, 200, {"status": "ok", "layout": {"bloks_payload": {"data": ["CAA_LOGIN_FALLBACK:synthetic"]}}})
        )
    sequence.extend(
        [
            (LOGIN, 400, {"status": "fail", "error_type": legacy_error, "message": "Legacy login rejected"}),
            (CAA, caa_status, caa_body),
        ]
    )

    def stop_on_error(_client, exc):
        raise exc

    client.handle_exception = stop_on_error

    def send(adapter, request, **kwargs):
        assert len(responses) < len(sequence), "Unexpected extra login request"
        url, status, body = sequence[len(responses)]
        assert request.url == url
        assert request.method == "POST"
        result = requests.Response()
        result.status_code = status
        result.url = request.url
        result.request = request
        result.headers["Content-Type"] = "application/json"
        result._content = json.dumps(body).encode()
        responses.append(result)
        return result

    monkeypatch.setattr(requests.adapters.HTTPAdapter, "send", send)
    return client, responses, sequence


@pytest.mark.parametrize("entrypoint", ["login", "login_legacy"])
@pytest.mark.parametrize("legacy_error", ["needs_upgrade", "bad_password"])
@pytest.mark.parametrize(
    ("caa_status", "caa_body", "expected"),
    [
        (429, {"status": "fail", "message": "Request limited"}, ClientThrottledError),
        (400, {"status": "fail", "error_type": "rate_limit_error", "message": "Request limited"}, RateLimitError),
        (400, {"status": "fail", "message": "feedback_required"}, FeedbackRequired),
        (400, {"status": "fail", "error_type": "field_exception", "message": "Different server error"}, UnknownError),
    ],
)
def test_login_surfaces_caa_failure_after_legacy_rejection(
    monkeypatch, entrypoint, legacy_error, caa_status, caa_body, expected
):
    client, responses, sequence = login_responses(
        monkeypatch, entrypoint=entrypoint, legacy_error=legacy_error, caa_status=caa_status, caa_body=caa_body
    )

    with pytest.raises(expected) as raised:
        getattr(client, entrypoint)("synthetic-user", "synthetic-password")

    assert len(responses) == len(sequence)
    assert getattr(raised.value, "error_type", None) == caa_body.get("error_type")
    assert client.last_response is responses[-1]
    assert client.last_json == caa_body
    assert not client.user_id
    client.login_flow.assert_not_called()


@pytest.mark.parametrize("entrypoint", ["login", "login_legacy"])
@pytest.mark.parametrize(("legacy_error", "expected"), [("needs_upgrade", UnknownError), ("bad_password", BadPassword)])
@pytest.mark.parametrize(
    ("caa_status", "caa_body"),
    [
        (404, {"status": "fail", "message": "Not found"}),
        (
            400,
            {"status": "fail", "error_type": "field_exception", "message": "Payload returned is null."},
        ),
    ],
)
def test_unavailable_caa_endpoint_keeps_legacy_failure(
    monkeypatch, entrypoint, legacy_error, expected, caa_status, caa_body
):
    client, responses, sequence = login_responses(
        monkeypatch, entrypoint=entrypoint, legacy_error=legacy_error, caa_status=caa_status, caa_body=caa_body
    )

    with pytest.raises(expected) as raised:
        getattr(client, entrypoint)("synthetic-user", "synthetic-password")

    assert len(responses) == len(sequence)
    assert raised.value.error_type == legacy_error
    client.login_flow.assert_not_called()
