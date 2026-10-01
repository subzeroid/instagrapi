import json

import pytest
import requests

from instagrapi.exceptions import ClientError, ClientForbiddenError


@pytest.mark.parametrize("status_code", [200, 302, 400, 401, 403, 404, 408, 429, 500])
def test_client_error_retains_response_http_status(status_code):
    response = requests.Response()
    response.status_code = status_code

    error = ClientError("Request failed", response=response)

    assert error.code == status_code
    assert error.response is response


def test_forbidden_error_keeps_api_payload_separate_from_http_status():
    payload = {"error_code": 1404006, "message": "Send rejected"}
    response = requests.Response()
    response.status_code = 403
    response._content = json.dumps({"status": "fail", "payload": payload}).encode()

    error = ClientForbiddenError("Request failed", "extra argument", response=response, payload=payload)

    assert error.code == 403
    assert error.response is response
    assert error.payload is payload
    assert error.response.json()["payload"]["error_code"] == 1404006
    assert error.message == "Request failed"
    assert error.args == ("Request failed", "extra argument")


@pytest.mark.parametrize("kwargs", [{}, {"response": None}])
def test_client_error_without_response_has_no_http_status(kwargs):
    error = ClientError("Request failed", **kwargs)

    assert error.response is None
    assert error.code is None


def test_client_error_without_response_preserves_explicit_code():
    error = ClientError("Local failure", code=123)

    assert error.code == 123
