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


def failing_legacy_login(monkeypatch, caa_body, content_type):
    client = Client(private_transport="requests")
    client.login = client.login_legacy
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
def test_captures_legacy_and_caa_before_last_json_is_overwritten(
    diagnostic, monkeypatch, body, content_type, body_kind, empty
):
    client, calls = failing_legacy_login(monkeypatch, body, content_type)
    previous_logging = logging.root.manager.disable

    report = diagnostic.diagnose(client, "synthetic-user", SECRET)

    assert calls == [LOGIN, CAA]
    assert report["outcome"] == "error"
    assert report["exception"]["type"] == "ClientThrottledError"
    assert report["exception"]["error_type"] is None
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


@pytest.mark.parametrize(
    ("error_type", "exception_type"),
    [("bad_password", "BadPassword"), ("rate_limit_error", "RateLimitError")],
)
def test_default_caa_captures_one_request_and_preserves_sanitized_native_error(
    diagnostic, monkeypatch, error_type, exception_type
):
    client = Client(settings={"session_retry_total": 0, "request_timeout": 0})
    client.private.trust_env = False
    client.public.trust_env = False
    client.caa_aac = '{"aaccs":"synthetic-context"}'
    client.pre_login_flow = Mock(side_effect=AssertionError("Unexpected legacy preflight"))
    client.login_legacy = Mock(side_effect=AssertionError("Unexpected legacy login"))
    client.password_encrypt = Mock(return_value="#PWD_INSTAGRAM:4:1:synthetic")
    client.bloks_caa_login_prepare = Mock(return_value=True)
    client.login_flow = Mock(side_effect=AssertionError("Unexpected success finalization"))
    calls = []
    previous_logging = logging.root.manager.disable
    previous_handler = client.handle_exception

    def send(request, **kwargs):
        calls.append(request.url)
        assert calls == [CAA], "Default login must submit credentials once through CAA"
        assert request.method == "POST"
        body = {
            "message": SECRET,
            "error_type": error_type,
            "status": "fail",
            "username": SECRET,
            "challenge_context": SECRET,
            "authorization_data": {"sessionid": SECRET},
        }
        result = response(request, 400, json.dumps(body).encode())
        result.headers["Set-Cookie"] = f"sessionid={SECRET}"
        return result

    # Patch the selected adapter so this exercises Client's default transport
    # and the real response hooks without sending a network request.
    monkeypatch.setattr(client.private.get_adapter(CAA), "send", send)
    monkeypatch.setattr(
        client.public,
        "send",
        Mock(side_effect=AssertionError("Unexpected public request")),
    )

    report = diagnostic.diagnose(client, "synthetic-user", SECRET)

    assert calls == [CAA]
    assert report["outcome"] == "error"
    assert report["exception"]["type"] == exception_type
    assert report["exception"]["error_type"] == error_type
    assert report["last_json"]["error_type"] == error_type
    assert [(item["endpoint"], item["http_status"]) for item in report["responses"]] == [
        ("caa/send_login_request", 400),
    ]
    assert report["responses"][0]["json"]["error_type"] == error_type
    assert SECRET not in json.dumps(report)
    assert logging.root.manager.disable == previous_logging
    assert client.handle_exception is previous_handler
    assert client.private.hooks["response"] == []
    assert client.public.hooks["response"] == []
    client.bloks_caa_login_prepare.assert_called_once_with(username="synthetic-user", domain="b.i.instagram.com")
    client.pre_login_flow.assert_not_called()
    client.login_legacy.assert_not_called()
    client.login_flow.assert_not_called()


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


@pytest.mark.parametrize(
    "message",
    [
        "Your version of Instagram is out of date.",
        "Your version of Instagram is out of date. Please upgrade your app to log in to Instagram.",
    ],
)
def test_outdated_app_response_keeps_signal_without_copying_message(diagnostic, message):
    request = requests.Request("POST", LOGIN).prepare()
    raw = response(
        request,
        400,
        json.dumps({"message": message + SECRET, "error_type": "needs_upgrade", "status": "fail"}).encode(),
    )

    summary = diagnostic.summarize_response(raw)

    assert summary["endpoint"] == "accounts/login"
    assert summary["json"]["error_type"] == "needs_upgrade"
    assert summary["json"]["message_category"] == "app_out_of_date"
    assert SECRET not in json.dumps(summary)


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
    client = Client(private_transport="requests", settings={"session_retry_total": 0, "request_timeout": 0})
    client.login = client.login_legacy
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
    client, _ = failing_legacy_login(monkeypatch, b"", "text/html")
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
    assert json.loads(output.read_text())["exception"]["type"] == "ClientThrottledError"
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


def test_caa_legacy_caa_records_each_outcome_before_state_changes(diagnostic, monkeypatch):
    client = Client(private_transport="requests", settings={"session_retry_total": 0, "request_timeout": 0})
    client.caa_aac = '{"aaccs":"synthetic-context"}'
    client.bloks_caa_login_prepare = Mock(return_value=True)
    client.pre_login_flow = Mock(return_value=True)
    client.password_encrypt = Mock(return_value="#PWD_INSTAGRAM:4:1:synthetic")
    original_caa = client.bloks_caa_login
    calls = []

    def send(adapter, request, **kwargs):
        calls.append(request.url)
        assert calls == [CAA, LOGIN, CAA][: len(calls)]
        if request.url == LOGIN:
            body = {"status": "fail", "error_type": "needs_upgrade", "message": SECRET}
            return response(request, 400, json.dumps(body).encode())
        body = {
            "status": "ok",
            "layout": {"bloks_payload": {"action": SECRET}},
            "markers": ["CAA_LOGIN_FALLBACK:fallback_triggered", SECRET],
        }
        return response(request, 200, json.dumps(body).encode())

    monkeypatch.setattr(requests.adapters.HTTPAdapter, "send", send)
    report = diagnostic.diagnose(client, "synthetic-user", SECRET, verification_code="123456")

    assert calls == [CAA, LOGIN, CAA]
    assert report["exception"]["error_type"] == "needs_upgrade"
    assert report["last_json"]["status"] == "ok"
    assert [(a["response_start"], a["response_end"]) for a in report["caa_attempts"]] == [(0, 1), (2, 3)]
    for attempt in report["caa_attempts"]:
        assert attempt["outcome"] == "returned"
        assert attempt["logged_in"] is False
        assert attempt["two_factor_context_present"] is False
        assert attempt["reason"] == "CAA login did not return a session"
        assert attempt["fallback_marker_present"] is True
        assert attempt["profile_code_reference_present"] is False
        assert attempt["profile_code_context_parsed"] is False
    assert SECRET not in json.dumps(report)
    assert client.bloks_caa_login == original_caa
    assert "bloks_caa_login" not in vars(client)
    assert client.private.hooks["response"] == []
    assert client.public.hooks["response"] == []


@pytest.mark.parametrize(
    "reason",
    [
        "CAA preflight did not return account access and attestation data",
        "missing entrypoint context_data",
        "missing code_entry context_data",
        "missing code_entry_async context_data",
    ],
)
def test_caa_reason_categories_are_preserved(diagnostic, reason):
    result = diagnostic.summarize_caa_outcome(Client(), {"logged_in": False, "reason": reason, "result": {}})
    assert result["reason"] == reason


def test_caa_summary_withholds_contexts_unknown_reasons_and_marker_suffixes(diagnostic):
    client = Client()
    body = {
        "logged_in": False,
        "two_step_verification_context": SECRET,
        "reason": SECRET,
        "result": {"markers": ["CAA_LOGIN_FALLBACK:" + SECRET], "token": SECRET},
    }
    before = json.dumps(body, sort_keys=True)
    summary = diagnostic.summarize_caa_outcome(client, body)
    assert summary["two_factor_context_present"] is True
    assert summary["reason"] == "other"
    assert summary["fallback_marker_present"] is True
    assert SECRET not in json.dumps(summary)
    assert json.dumps(body, sort_keys=True) == before


@pytest.mark.parametrize("has_context", [False, True])
def test_caa_summary_distinguishes_profile_reference_from_parsed_context(diagnostic, has_context):
    app = "com.bloks.www.ap.two_step_verification.entrypoint_async"
    action = json.dumps(app)
    if has_context:
        action += f' (f4i (dkc "context_data") (dkc "{SECRET}"))'
    body = {"logged_in": False, "result": {"layout": {"bloks_payload": {"action": action}}}}
    summary = diagnostic.summarize_caa_outcome(Client(), body)
    assert summary["profile_code_reference_present"] is True
    assert summary["profile_code_context_parsed"] is has_context
    assert SECRET not in json.dumps(summary)


@pytest.mark.parametrize("exc", [RuntimeError(SECRET), KeyboardInterrupt()])
def test_caa_observer_records_failure_and_restores_instance_override(diagnostic, exc):
    client = Client()
    original = Mock(side_effect=exc)
    client.bloks_caa_login = original
    previous_handler = client.handle_exception
    report = diagnostic.diagnose(client, "synthetic-user", SECRET)
    assert report["exception"]["type"] == type(exc).__name__
    assert report["caa_attempts"] == [{"outcome": "error", "response_start": 0, "response_end": 0}]
    original.assert_called_once_with(verification_code="")
    assert client.bloks_caa_login is original
    assert client.handle_exception is previous_handler
    assert SECRET not in json.dumps(report)


def test_caa_inspection_failure_cannot_change_login_result(diagnostic, monkeypatch):
    client = Client()
    outcome = {"logged_in": True, "result": {}, "reason": ""}
    client.bloks_caa_login = Mock(return_value=outcome)
    client.login_flow = Mock(return_value=True)
    monkeypatch.setattr(diagnostic, "summarize_caa_outcome", Mock(side_effect=ValueError(SECRET)))
    report = diagnostic.diagnose(client, "synthetic-user", SECRET)
    assert report["outcome"] == "success"
    assert report["caa_attempts"] == [
        {"outcome": "returned", "response_start": 0, "response_end": 0, "inspection_error": True}
    ]
    assert client.bloks_caa_login.return_value is outcome
    assert SECRET not in json.dumps(report)


def test_partial_hook_setup_restores_client_without_calling_login(diagnostic):
    client = Client()
    original_caa = Mock()
    original_handler = Mock()
    original_hook = Mock()
    client.bloks_caa_login = original_caa
    client.handle_exception = original_handler
    client.private.hooks["response"] = [original_hook]
    client.public.hooks["response"] = ()
    client.login = Mock(side_effect=AssertionError("Setup must fail before login"))
    with pytest.raises(AttributeError):
        diagnostic.diagnose(client, "synthetic-user", SECRET)
    client.login.assert_not_called()
    assert client.bloks_caa_login is original_caa
    assert client.handle_exception is original_handler
    assert client.private.hooks["response"] == [original_hook]
    assert client.public.hooks["response"] == ()


@pytest.mark.parametrize("known_profile", [False, True])
@pytest.mark.parametrize("has_hash", [False, True])
def test_diagnostic_reports_only_catalogued_app_versions(diagnostic, known_profile, has_hash):
    client = Client()
    expected_version = client.device_settings["app_version"]
    if not known_profile:
        client.device_settings["app_version"] = SECRET
        expected_version = "other"
    client.bloks_versioning_id = SECRET if has_hash else ""
    client.login = Mock(return_value=True)
    report = diagnostic.diagnose(client, "synthetic-user", SECRET)
    assert report["client_profile"] == {
        "app_version": expected_version,
        "bloks_versioning_id_present": has_hash,
    }
    assert report["caa_attempts"] == []
    assert SECRET not in json.dumps(report)


@pytest.mark.parametrize("raw_result", [{}, None, []])
def test_caa_observer_preserves_success_object_and_summarizes_empty_results(diagnostic, raw_result):
    client = Client()
    outcome = {"logged_in": True, "result": raw_result, "reason": ""}
    original = Mock(return_value=outcome)
    client.bloks_caa_login = original

    def login(*args, **kwargs):
        assert client.bloks_caa_login(verification_code="123456") is outcome
        return True

    client.login = login
    report = diagnostic.diagnose(client, "synthetic-user", SECRET)
    attempt = report["caa_attempts"][0]
    assert report["outcome"] == "success"
    assert attempt["logged_in"] is True
    assert attempt["reason"] == ""
    assert attempt["profile_code_reference_present"] is False
    assert attempt["profile_code_context_parsed"] is False
    assert client.bloks_caa_login is original
    original.assert_called_once_with(verification_code="123456")


def test_caa_observer_preserves_system_exit_identity_and_restores_hooks(diagnostic):
    client = Client()
    error = SystemExit(SECRET)
    original = Mock(side_effect=error)
    client.bloks_caa_login = original
    handler = client.handle_exception
    with pytest.raises(SystemExit) as caught:
        diagnostic.diagnose(client, "synthetic-user", SECRET)
    assert caught.value is error
    assert client.bloks_caa_login is original
    assert client.handle_exception is handler
    assert client.private.hooks["response"] == []
    assert client.public.hooks["response"] == []
