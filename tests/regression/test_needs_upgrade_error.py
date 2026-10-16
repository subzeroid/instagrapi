# Value: protects=exact HTTP 400 needs_upgrade classification and its public diagnostics;
# fails_when=generic, broad, or reordered classification loses the original failure;
# why_new=existing login tests only see generic errors; seam=none
"""Exercise needs_upgrade classification through the requests transport boundary."""

import json

import pytest
import requests

from instagrapi import Client, exceptions


def classify(monkeypatch, payload, status=400, endpoint="accounts/login/"):
    client = Client(private_transport="requests", settings={"session_retry_total": 0, "request_timeout": 0})
    client.private.trust_env = False
    responses = []

    def send(adapter, request, **kwargs):
        assert not responses, "Classification must not resend the request"
        assert request.url == f"https://i.instagram.com/api/v1/{endpoint}"
        response = requests.Response()
        response.status_code = status
        response.url = request.url
        response.request = request
        response.headers["Content-Type"] = "application/json"
        response._content = json.dumps(payload).encode()
        responses.append(response)
        return response

    monkeypatch.setattr(requests.adapters.HTTPAdapter, "send", send)
    try:
        with pytest.raises(exceptions.ClientError) as raised:
            client._send_private_request(endpoint, login=True)
    finally:
        client.private.close()
        client.public.close()
        client.graphql.close()
    assert len(responses) == 1
    assert client.last_response is responses[0]
    return client, responses[0], raised.value


@pytest.mark.parametrize("extra", [{}, {"response": {}, "code": 999}])
def test_http400_needs_upgrade_has_typed_original_diagnostics(monkeypatch, extra):
    payload = {
        "status": "fail",
        "error_type": "needs_upgrade",
        "message": "Your version of Instagram is out of date. 🚧",
        **extra,
    }

    client, response, error = classify(monkeypatch, payload)

    # Keep baseline collection working so RED reports the actual generic error.
    assert type(error).__name__ == "ClientNeedsUpgradeError"
    assert type(error) is exceptions.ClientNeedsUpgradeError
    assert isinstance(error, exceptions.UnknownError)
    assert error.response is response
    assert error.code == 400
    assert error.message == payload["message"]
    assert str(error) == payload["message"]
    assert error.error_type == "needs_upgrade"
    assert client.last_json == payload


@pytest.mark.parametrize("flag", [None, "", "temporary_error", "NEEDS_UPGRADE", " needs_upgrade", "needs_upgrade "])
def test_other_flags_remain_unknown_error(monkeypatch, flag):
    payload = {"status": "fail", "message": "needs_upgrade", "error_type": flag}

    client, _, error = classify(monkeypatch, payload)

    assert type(error) is exceptions.UnknownError
    assert client.last_json == payload


@pytest.mark.parametrize(
    ("endpoint", "extra", "expected"),
    [
        ("accounts/login/", {"message": "challenge_required", "challenge": {}}, exceptions.ChallengeRequired),
        ("accounts/login/", {"two_factor_info": {"two_factor_identifier": "synthetic"}}, exceptions.TwoFactorRequired),
        ("accounts/login/", {"message": "feedback_required"}, exceptions.FeedbackRequired),
        (
            "accounts/login/",
            {"message": "Please wait a few minutes before you try again"},
            exceptions.PleaseWaitFewMinutes,
        ),
        (
            "accounts/edit_profile/",
            {"message": "You need an email or confirmed phone number."},
            exceptions.AccountContactPointRequired,
        ),
        ("accounts/edit_profile/", {}, exceptions.AccountEditError),
        (
            "direct_v2/threads/broadcast/text/",
            {"message": "You can't message this account unless they follow you."},
            exceptions.DirectMessageRequestsDisabled,
        ),
        ("media/123/info/", {"message": "Media is unavailable"}, exceptions.MediaUnavailable),
    ],
)
def test_higher_priority_failures_keep_their_classification(monkeypatch, endpoint, extra, expected):
    payload = {"status": "fail", "error_type": "needs_upgrade", "message": "Upgrade requested", **extra}

    _, _, error = classify(monkeypatch, payload, endpoint=endpoint)

    assert type(error) is expected


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (200, exceptions.ClientError),
        (401, exceptions.ClientUnauthorizedError),
        (403, exceptions.ClientForbiddenError),
        (404, exceptions.ClientNotFoundError),
        (408, exceptions.ClientRequestTimeout),
        (429, exceptions.ClientThrottledError),
        (500, exceptions.ClientError),
    ],
)
def test_other_statuses_keep_their_classification(monkeypatch, status, expected):
    payload = {"status": "fail", "error_type": "needs_upgrade", "message": "Upgrade requested"}

    _, _, error = classify(monkeypatch, payload, status=status)

    assert type(error) is expected
