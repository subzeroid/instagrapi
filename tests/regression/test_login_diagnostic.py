import importlib.util
import json
import logging
import stat
from pathlib import Path
from unittest.mock import Mock

import pytest
import requests

from instagrapi import Client

SCRIPT = Path(__file__).resolve().parents[2] / "examples" / "diagnose_login.py"
LOGIN = "https://i.instagram.com/api/v1/accounts/login/"
CAA = "https://b.i.instagram.com/api/v1/bloks/async_action/com.bloks.www.bloks.caa.login.async.send_login_request/"
SECRET = "DO_NOT_SHARE_test_secret_12345"


@pytest.fixture
def diagnostic():
    assert SCRIPT.exists(), "The standalone login diagnostic script is missing"
    spec = importlib.util.spec_from_file_location("login_diagnostic", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def response(request, status, body, content_type="application/json"):
    result = requests.Response()
    result.status_code = status
    result.reason = "Bad Request" if status == 400 else "Too Many Requests"
    result.request = request
    result.url = request.url
    result._content = body
    result.encoding = "utf-8"
    result.headers["Content-Type"] = content_type
    return result


def failing_login(monkeypatch, caa_body, content_type):
    client = Client()
    client.private.trust_env = False
    client.public.trust_env = False
    client.caa_aac = '{"aaccs":"synthetic-context"}'
    client.pre_login_flow = Mock(return_value=True)
    client.password_encrypt = Mock(return_value="#PWD_INSTAGRAM:4:1:synthetic")
    client.bloks_caa_login_prepare = Mock(return_value=True)
    calls = []

    def send(adapter, request, **kwargs):
        calls.append(request.url)
        assert request.method == "POST"
        if calls == [LOGIN]:
            body = {
                "message": "We can send you an email to help you get back into your account. " + SECRET,
                "error_type": "bad_password",
                "status": "fail",
                "username": SECRET,
                "challenge_context": SECRET,
            }
            return response(request, 400, json.dumps(body).encode())
        assert calls == [LOGIN, CAA], "Unexpected request in offline test"
        return response(request, 429, caa_body, content_type)

    monkeypatch.setattr(requests.adapters.HTTPAdapter, "send", send)
    return client, calls


@pytest.mark.parametrize(
    ("body", "content_type", "body_kind", "empty"),
    [
        (b"", "text/plain", "non_json", True),
        (b"<html>private response</html>", "text/html", "non_json", True),
        (b"{}", "application/json", "dict", True),
        (b'{"message":"limit","status":"fail"}', "application/json", "dict", False),
    ],
)
def test_captures_original_and_caa_before_last_json_is_overwritten(
    diagnostic, monkeypatch, body, content_type, body_kind, empty
):
    client, calls = failing_login(monkeypatch, body, content_type)
    previous_logging = logging.root.manager.disable

    report = diagnostic.diagnose(client, "synthetic-user", SECRET)

    assert calls == [LOGIN, CAA]
    assert report["outcome"] == "error"
    assert report["exception"]["type"] == "BadPassword"
    assert report["exception"]["error_type"] == "bad_password"
    assert report["last_json"]["empty"] is empty
    assert [(item["endpoint"], item["http_status"]) for item in report["responses"]] == [
        ("accounts/login", 400),
        ("caa/send_login_request", 429),
    ]
    assert report["responses"][0]["json"]["error_type"] == "bad_password"
    assert report["responses"][1]["json"]["type"] == body_kind
    assert SECRET not in json.dumps(report)
    assert "private response" not in json.dumps(report)
    assert logging.root.manager.disable == previous_logging
    assert client.private.hooks["response"] == []


def test_response_summary_never_copies_untrusted_strings(diagnostic):
    req = requests.Request("POST", f"https://i.instagram.com/api/v1/challenge/{SECRET}/?token={SECRET}").prepare()
    payload = {
        "message": SECRET,
        "status": SECRET,
        "error_type": SECRET,
        "step_name": SECRET,
        "bloks_action": SECRET,
        "challenge": {"native_flow": SECRET, "api_path": f"/challenge/{SECRET}/", "challenge_context": SECRET},
        "authorization_data": {"sessionid": SECRET},
    }
    raw = response(req, 400, json.dumps(payload).encode(), SECRET)
    raw.headers["Set-Cookie"] = f"sessionid={SECRET}"
    raw.headers["Location"] = f"https://instagram.com/{SECRET}"
    summary = diagnostic.summarize_response(raw)

    assert SECRET not in json.dumps(summary)
    assert summary["endpoint"] == "challenge"
    assert summary["json"]["challenge_api_path"] == "/challenge/<redacted>"
    assert summary["json"]["error_type"] == "other"
    assert summary["content_type"] == "other"
    assert "Set-Cookie" not in summary


def test_native_challenge_fields_remain_useful(diagnostic):
    summary = diagnostic.summarize_json(
        {
            "message": "challenge_required",
            "status": "fail",
            "challenge": {"native_flow": True, "api_path": f"/api/v1/challenge/{SECRET}/"},
        }
    )
    assert summary["message_category"] == "challenge_required"
    assert summary["challenge_native_flow"] is True
    assert summary["challenge_api_path"] == "/api/v1/challenge/<redacted>"
    assert SECRET not in json.dumps(summary)


@pytest.mark.parametrize("custom_handler", [False, True])
def test_stops_before_automatic_challenge_requests_and_restores_handler(diagnostic, monkeypatch, custom_handler):
    client = Client(settings={"session_retry_total": 0, "request_timeout": 0})
    client.pre_login_flow = Mock(return_value=True)
    client.password_encrypt = Mock(return_value="synthetic")
    original_handler = Mock(side_effect=RuntimeError("must not call user handler")) if custom_handler else None
    client.handle_exception = original_handler
    calls = []

    def send(adapter, request, **kwargs):
        calls.append(request.url)
        assert calls == [LOGIN], "Diagnostic must not resolve a challenge automatically"
        body = {
            "message": "challenge_required",
            "status": "fail",
            "challenge": {"api_path": f"/challenge/123/{SECRET}/"},
        }
        return response(request, 400, json.dumps(body).encode())

    monkeypatch.setattr(requests.adapters.HTTPAdapter, "send", send)
    report = diagnostic.diagnose(client, "synthetic-user", SECRET)

    assert calls == [LOGIN]
    assert report["exception"]["type"] == "ChallengeRequired"
    assert report["responses"][0]["json"]["challenge_api_path"] == "/challenge/<redacted>"
    assert client.handle_exception is original_handler
    if custom_handler:
        original_handler.assert_not_called()
    assert SECRET not in json.dumps(report)


def test_main_saves_private_settings_and_sanitized_report_after_failure(diagnostic, monkeypatch, tmp_path, capsys):
    client, _ = failing_login(monkeypatch, b"", "text/html")
    client.private.cookies.set("synthetic_private_cookie", SECRET)
    factory = Mock(return_value=client)
    monkeypatch.setattr(diagnostic, "Client", factory)
    monkeypatch.setenv("IG_USERNAME", "synthetic-user")
    monkeypatch.setenv("IG_PASSWORD", SECRET)
    monkeypatch.delenv("IG_PROXY", raising=False)
    monkeypatch.delenv("IG_SESSION_FILE", raising=False)
    settings = tmp_path / "session.json"
    output = tmp_path / "report.json"
    settings.write_text(json.dumps({"uuids": {"uuid": "saved-device"}}))

    code = diagnostic.main(["--settings", str(settings), "--report", str(output)])

    assert code == 1
    assert factory.call_args.kwargs["settings"]["uuids"]["uuid"] == "saved-device"
    assert json.loads(output.read_text())["exception"]["type"] == "BadPassword"
    assert SECRET not in output.read_text()
    assert SECRET in settings.read_text()
    assert stat.S_IMODE(settings.stat().st_mode) == 0o600
    assert stat.S_IMODE(output.stat().st_mode) == 0o600
    streams = capsys.readouterr()
    assert SECRET not in streams.out + streams.err


def test_report_cannot_overwrite_settings(diagnostic, monkeypatch, tmp_path):
    client = Mock()
    monkeypatch.setattr(diagnostic, "Client", client)
    path = tmp_path / "session.json"
    path.write_text(SECRET)
    with pytest.raises(SystemExit) as exc:
        diagnostic.main(["--settings", str(path), "--report", str(path)])
    assert exc.value.code == 2
    assert path.read_text() == SECRET
    client.assert_not_called()


def test_library_stdout_logs_and_exception_text_are_not_exported(diagnostic, capsys, caplog):
    client = Client()
    # Test blanket output suppression independently of the credential fixtures.
    output_marker = "synthetic-library-output"

    def reject(*args, **kwargs):
        print(output_marker)
        logging.getLogger("instagrapi").error(output_marker)
        raise RuntimeError(output_marker)

    client.login = reject
    report = diagnostic.diagnose(client, "synthetic-user", SECRET)
    assert report["exception"]["type"] == "RuntimeError"
    assert SECRET not in json.dumps(report)
    assert output_marker not in json.dumps(report)
    streams = capsys.readouterr()
    assert SECRET not in streams.out + streams.err
    assert output_marker not in streams.out + streams.err + caplog.text


def test_interruption_still_saves_settings_and_report(diagnostic, monkeypatch, tmp_path):
    client = Client()
    client.login = Mock(side_effect=KeyboardInterrupt())
    monkeypatch.setattr(diagnostic, "Client", Mock(return_value=client))
    monkeypatch.setenv("IG_USERNAME", "synthetic-user")
    monkeypatch.setenv("IG_PASSWORD", SECRET)
    monkeypatch.delenv("IG_PROXY", raising=False)
    settings = tmp_path / "session.json"
    output = tmp_path / "report.json"

    assert diagnostic.main(["--settings", str(settings), "--report", str(output), "--relogin"]) == 1
    report = json.loads(output.read_text())
    assert report["exception"]["type"] == "KeyboardInterrupt"
    assert report["settings_saved"] is True
    assert json.loads(settings.read_text())["uuids"]["uuid"] == client.uuid
    assert client.login.call_args.kwargs["relogin"] is True


def test_invalid_report_destination_stops_before_login(diagnostic, monkeypatch, tmp_path):
    factory = Mock()
    monkeypatch.setattr(diagnostic, "Client", factory)
    settings = tmp_path / "session.json"
    settings.write_text('{"uuids": {"uuid": "keep-existing"}}')
    original = settings.read_bytes()
    output = tmp_path / "missing-directory" / "report.json"

    assert diagnostic.main(["--settings", str(settings), "--report", str(output)]) == 1
    assert settings.read_bytes() == original
    factory.assert_not_called()


@pytest.mark.parametrize("retry_settings", [{}, {"session_retry_total": 4, "public_request_retries_count": 2}])
def test_diagnostic_retry_overrides_do_not_change_saved_preferences(diagnostic, monkeypatch, tmp_path, retry_settings):
    client = Client(settings={"session_retry_total": 0, "public_request_retries_count": 1})
    client.login = Mock(return_value=True)
    monkeypatch.setattr(diagnostic, "Client", Mock(return_value=client))
    monkeypatch.setenv("IG_USERNAME", "synthetic-user")
    monkeypatch.setenv("IG_PASSWORD", SECRET)
    monkeypatch.delenv("IG_PROXY", raising=False)
    settings = tmp_path / "session.json"
    settings.write_text(json.dumps(retry_settings))

    assert diagnostic.main(["--settings", str(settings), "--report", str(tmp_path / "report.json")]) == 0
    saved = json.loads(settings.read_text())
    for key in ("session_retry_total", "public_request_retries_count"):
        assert saved.get(key) == retry_settings.get(key)
