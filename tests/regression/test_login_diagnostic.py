import importlib.util
import json
import logging
import stat
from pathlib import Path
from unittest.mock import Mock

import pytest
import requests

from instagrapi import Client
from instagrapi.transports import _CurlH2Adapter

SCRIPT = Path(__file__).resolve().parents[2] / "examples" / "diagnose_login.py"
LOGIN = "https://i.instagram.com/api/v1/accounts/login/"
CAA = "https://b.i.instagram.com/api/v1/bloks/async_action/com.bloks.www.bloks.caa.login.async.send_login_request/"
SECRET = "DO_NOT_SHARE_test_secret_12345"


@pytest.fixture(autouse=True)
def deny_unexpected_network(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError("Unexpected network attempt in offline diagnostic test")

    monkeypatch.setattr(requests.adapters.HTTPAdapter, "send", deny)
    monkeypatch.setattr(_CurlH2Adapter, "send", deny)


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
        "private_transport": client.private_transport,
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


STAGE_APPS = [
    ("com.bloks.www.bloks.caa.login.process_client_data_and_redirect", "caa/process_client_data_and_redirect"),
    ("com.bloks.www.caa.login.oauth.token.fetch.async", "caa/oauth_token_fetch"),
    ("com.bloks.www.bloks.caa.login.async.send_login_request", "caa/send_login_request"),
    ("com.bloks.www.two_step_verification.entrypoint", "two_step/entrypoint"),
    ("com.bloks.www.two_step_verification.method_picker", "two_step/method_picker"),
    ("com.bloks.www.two_step_verification.method_picker.navigation.async", "two_step/select_method"),
    ("com.bloks.www.two_factor_login.enter_totp_code", "two_step/enter_totp_code"),
    ("com.bloks.www.two_factor_login.enter_backup_code", "two_step/enter_backup_code"),
    ("com.bloks.www.two_step_verification.verify_code.async", "two_step/verify_code"),
    ("com.bloks.www.two_step_verification.has_been_allowed.async", "two_step/has_been_allowed"),
    ("com.bloks.www.caa.notif_status.async", "caa/notif_status"),
    ("com.bloks.www.ap.two_step_verification.entrypoint_async", "profile_code/entrypoint"),
    ("com.bloks.www.ap.two_step_verification.code_entry", "profile_code/code_entry"),
    ("com.bloks.www.ap.two_step_verification.code_entry_async", "profile_code/code_entry_async"),
]


@pytest.mark.parametrize(("app", "label"), STAGE_APPS, ids=[label for _, label in STAGE_APPS])
def test_exact_new_endpoint_stages(diagnostic, app, label):
    assert diagnostic.endpoint_label(f"/api/v1/bloks/async_action/{app}/") == label
    assert diagnostic.endpoint_label(f"/api/v1/bloks/apps/{app}/") == label
    for unknown in (app + SECRET, app + ".unknown", SECRET + app):
        assert diagnostic.endpoint_label(f"/api/v1/bloks/async_action/{unknown}/") == "bloks"


def test_attestation_and_legacy_endpoint_categories(diagnostic):
    assert diagnostic.endpoint_label("/api/v1/attestation/create_android_keystore/") == (
        "attestation/create_android_keystore"
    )
    assert diagnostic.endpoint_label("/api/v1/attestation/" + SECRET) == "attestation"
    for suffix, category in (
        ("process_client_data/", "caa/process_client_data"),
        ("oauth_token.fetch/", "caa/oauth_token_fetch"),
        ("send_login_request/", "caa/send_login_request"),
        ("accounts/current_user/", "accounts/current_user"),
    ):
        assert diagnostic.endpoint_label("/api/v1/" + suffix) == category


@pytest.mark.parametrize("friendly_name_kind", ["exact", "missing", "unknown", "suffix", "prefix"])
def test_usdid_registration_uses_only_exact_friendly_name(diagnostic, friendly_name_kind):
    friendly_name = {
        "exact": "IGUSDIDRegistrationMutation",
        "missing": None,
        "unknown": SECRET,
        "suffix": "IGUSDIDRegistrationMutation" + SECRET,
        "prefix": SECRET + "IGUSDIDRegistrationMutation",
    }[friendly_name_kind]
    headers = {"x-fb-friendly-name": friendly_name} if friendly_name is not None else {}
    request = requests.Request("POST", "https://b.i.instagram.com/graphql_www", headers=headers, data=SECRET).prepare()
    raw = response(request, 200, b"{}")
    summary = diagnostic.summarize_response(raw)
    assert summary["endpoint"] == ("usdid/registration" if friendly_name_kind == "exact" else "other")
    assert SECRET not in json.dumps(summary)


@pytest.mark.parametrize(
    ("server", "proxy_status", "server_category", "proxy_category"),
    [
        ("proxygen-bolt", "http_request_error", "proxygen-bolt", "http_request_error"),
        ("proxygen-bolt", 'proxy; error=http_request_error; details="private"', "proxygen-bolt", "http_request_error"),
        ("proxygen-bolt", 'proxy; error="http_request_error"', "proxygen-bolt", "http_request_error"),
        (None, None, None, None),
        (SECRET, SECRET, "other", "other"),
        ("proxygen-bolt" + SECRET, "http_request_error" + SECRET, "other", "other"),
        (SECRET, 'proxy; details="error=http_request_error"', "other", "other"),
        (SECRET, 'proxy; details="private; error=http_request_error;"', "other", "other"),
        (SECRET, "proxy; error=http_request_error" + SECRET, "other", "other"),
    ],
    ids=[
        "bare",
        "parameter",
        "quoted",
        "absent",
        "unknown",
        "hostile-suffix",
        "details",
        "quoted-details",
        "hostile-error",
    ],
)
def test_response_metadata_is_allowlisted(diagnostic, server, proxy_status, server_category, proxy_category):
    request = requests.Request("POST", CAA).prepare()
    raw = response(request, 429, b"", "text/plain")
    if server is not None:
        raw.headers["Server"] = server
    if proxy_status is not None:
        raw.headers["Proxy-Status"] = proxy_status
    raw.headers["Retry-After"] = SECRET
    summary = diagnostic.summarize_response(raw)
    assert summary["server_category"] == server_category
    assert summary["proxy_error_category"] == proxy_category
    assert summary["retry_after_present"] is True
    assert SECRET not in json.dumps(summary)
    del raw.headers["Retry-After"]
    assert diagnostic.summarize_response(raw)["retry_after_present"] is False


def embedded_bloks(*, session=False, authorization=False, user=False):
    embedded = {
        "login_response": json.dumps({"logged_in_user": {"pk": "123", "username": SECRET}} if user else {}),
        "headers": json.dumps({"IG-Set-Authorization": SECRET} if authorization else {}),
        "cookies": f"Set-Cookie: sessionid={SECRET}; Path=/" if session else "Set-Cookie: sessionid=; Path=/",
        "private": SECRET,
    }
    return {"status": "ok", "layout": {"bloks_payload": {"action": f"(bk.action {json.dumps(json.dumps(embedded))})"}}}


@pytest.mark.parametrize("kind", ["empty", "fallback", "reference", "malformed", "decoded-empty", "session"])
def test_bloks_summary_distinguishes_references_and_current_session_material(diagnostic, kind):
    body = {
        "empty": {},
        "fallback": {"markers": ["CAA_LOGIN_FALLBACK:" + SECRET]},
        "reference": {"layout": {"bloks_payload": {"action": "login_response " + SECRET}}},
        "malformed": {"layout": {"bloks_payload": {"action": '"{invalid login_response ' + SECRET}}},
        "decoded-empty": embedded_bloks(),
        "session": embedded_bloks(session=True, authorization=True, user=True),
    }[kind]
    before = json.dumps(body, sort_keys=True)
    request = requests.Request("POST", CAA).prepare()
    raw = response(request, 200, json.dumps(body).encode())
    summary = diagnostic.summarize_response(raw)
    bloks = summary["bloks"]
    assert bloks["login_response_reference_present"] is (kind in {"reference", "malformed", "decoded-empty", "session"})
    assert bloks["login_response_decoded"] is (kind in {"decoded-empty", "session"})
    assert bloks["logged_in_user_present"] is (kind == "session")
    assert bloks["authorization_present"] is (kind == "session")
    assert bloks["sessionid_cookie_present"] is (kind == "session")
    assert bloks["fallback_reference_present"] is (kind == "fallback")
    assert bloks["inspection_error"] is False
    assert SECRET not in json.dumps(summary)
    assert json.dumps(body, sort_keys=True) == before


def test_bloks_referenced_apps_are_exact_and_closed(diagnostic):
    app = "com.bloks.www.two_step_verification.entrypoint"
    payload = {
        "layout": {"bloks_payload": {"action": f"{json.dumps(app)} {json.dumps(app + SECRET)}"}},
        "private": SECRET,
    }
    request = requests.Request("POST", CAA).prepare()
    summary = diagnostic.summarize_response(response(request, 200, json.dumps(payload).encode()))
    assert summary["bloks"]["referenced_apps"] == [app]
    assert SECRET not in json.dumps(summary)
    payload["layout"]["bloks_payload"]["action"] = json.dumps(app + SECRET)
    summary = diagnostic.summarize_response(response(request, 200, json.dumps(payload).encode()))
    assert summary["bloks"]["referenced_apps"] == []


@pytest.mark.parametrize("kind", ["success", "redirect", "continuation", "error", "ocl-error", "hostile"])
def test_bloks_marker_references_are_narrow_and_not_outcomes(diagnostic, kind):
    app = "com.bloks.www.two_step_verification.method_picker"
    body = {
        "success": {"layout": {"bloks_payload": {"action": json.dumps("login_success") + SECRET}}},
        "redirect": {"layout": {"bloks_payload": {"action": json.dumps("two_fac_redirect") + SECRET}}},
        "continuation": {"layout": {"bloks_payload": {"action": json.dumps(app) + SECRET}}},
        "error": {"error_type": "bad_password", "message": SECRET},
        "ocl-error": {"markers": ["CAA_LOGIN_OCL_ERROR:" + SECRET]},
        "hostile": {"layout": {"bloks_payload": {"action": json.dumps("login_success" + SECRET)}}},
    }[kind]
    raw = response(requests.Request("POST", CAA).prepare(), 200, json.dumps(body).encode())
    bloks = diagnostic.summarize_response(raw)["bloks"]
    assert bloks["login_success_reference_present"] is (kind in {"success", "redirect"})
    assert bloks["continuation_reference_present"] is (kind == "continuation")
    assert bloks["error_reference_present"] is (kind in {"error", "ocl-error"})
    assert bloks["login_response_decoded"] is False
    assert bloks["sessionid_cookie_present"] is False
    assert SECRET not in json.dumps(bloks)


def test_bloks_extraction_failure_uses_fixed_schema_without_session_changes(diagnostic, monkeypatch):
    body = embedded_bloks(session=True, authorization=True, user=True)
    raw = response(requests.Request("POST", CAA).prepare(), 200, json.dumps(body).encode())
    before = raw.content
    monkeypatch.setattr(diagnostic.BLOKS_PARSER, "bloks_extract_login_response", Mock(side_effect=ValueError(SECRET)))
    bloks = diagnostic.summarize_response(raw)["bloks"]
    assert set(bloks) == {
        "referenced_apps",
        "fallback_reference_present",
        "login_success_reference_present",
        "continuation_reference_present",
        "error_reference_present",
        "login_response_reference_present",
        "two_step_context_parsed",
        "profile_code_context_parsed",
        "login_response_decoded",
        "logged_in_user_present",
        "authorization_present",
        "sessionid_cookie_present",
        "inspection_error",
    }
    assert bloks["inspection_error"] is True
    assert bloks["login_response_decoded"] is False
    assert raw.content == before
    assert SECRET not in json.dumps(bloks)


@pytest.mark.parametrize(
    "kind", ["two-step-json", "two-step-action", "profile-action", "reference-only", "hostile-app"]
)
def test_current_response_context_booleans_withhold_values(diagnostic, kind):
    app = "com.bloks.www.two_step_verification.entrypoint"
    profile = "com.bloks.www.ap.two_step_verification.code_entry"
    body = {
        "two-step-json": {"two_step_verification_context": SECRET},
        "two-step-action": {
            "layout": {
                "bloks_payload": {
                    "action": (f'{json.dumps(app)} (f4i (dkc "two_step_verification_context") (dkc "{SECRET}"))')
                }
            }
        },
        "profile-action": {
            "layout": {
                "bloks_payload": {"action": (f'{json.dumps(profile)} (f4i (dkc "context_data") (dkc "{SECRET}"))')}
            }
        },
        "reference-only": {"layout": {"bloks_payload": {"action": json.dumps(profile)}}},
        "hostile-app": {
            "layout": {
                "bloks_payload": {
                    "action": (f'{json.dumps(profile + SECRET)} (f4i (dkc "context_data") (dkc "{SECRET}"))')
                }
            }
        },
    }[kind]
    before = json.dumps(body, sort_keys=True)
    raw = response(requests.Request("POST", CAA).prepare(), 200, json.dumps(body).encode())
    bloks = diagnostic.summarize_response(raw)["bloks"]
    assert bloks["two_step_context_parsed"] is (kind in {"two-step-json", "two-step-action"})
    assert bloks["profile_code_context_parsed"] is (kind == "profile-action")
    assert bloks["inspection_error"] is False
    assert json.dumps(body, sort_keys=True) == before
    assert SECRET not in json.dumps(bloks)


@pytest.mark.parametrize("transport", ["requests", "curl", "unknown"])
def test_private_transport_is_allowlisted(diagnostic, transport):
    client = Client(private_transport=transport if transport != "unknown" else "requests")
    client.login = Mock(return_value=True)
    if transport == "unknown":
        client.private_transport = SECRET
    report = diagnostic.diagnose(client, "synthetic-user", SECRET)
    assert report["client_profile"]["private_transport"] == ("other" if transport == "unknown" else transport)
    assert SECRET not in json.dumps(report)


@pytest.mark.parametrize("verification", ["session", "no-session", "credential-429", "pre-submit-429", "backup"])
@pytest.mark.parametrize("inspection_failure", [False, True])
def test_real_mocked_transport_two_factor_sequence_preserves_outcome(
    diagnostic, monkeypatch, verification, inspection_failure
):
    if inspection_failure:
        monkeypatch.setattr(
            diagnostic.BLOKS_PARSER, "bloks_extract_login_response", Mock(side_effect=ValueError(SECRET))
        )

    def run(observe):
        client = Client(private_transport="requests", settings={"request_timeout": 0, "session_retry_total": 0})
        client.private.trust_env = False
        client.public.trust_env = False
        client.caa_aac = '{"aaccs":"synthetic-context"}'
        if verification == "pre-submit-429":
            client.usdid_registered = True
        else:
            client.bloks_caa_login_prepare = Mock(return_value=True)
        client.password_encrypt = Mock(return_value="#PWD_INSTAGRAM:4:1:synthetic")
        client.login_flow = Mock(return_value=True)
        calls = []
        entry = "https://i.instagram.com/api/v1/bloks/apps/com.bloks.www.two_step_verification.entrypoint/"
        picker = "https://i.instagram.com/api/v1/bloks/apps/com.bloks.www.two_step_verification.method_picker/"
        select = "https://i.instagram.com/api/v1/bloks/async_action/com.bloks.www.two_step_verification.method_picker.navigation.async/"
        backup = "https://i.instagram.com/api/v1/bloks/apps/com.bloks.www.two_factor_login.enter_backup_code/"
        verify = (
            "https://i.instagram.com/api/v1/bloks/async_action/com.bloks.www.two_step_verification.verify_code.async/"
        )
        expected = [CAA, entry, picker, select] + ([backup] if verification == "backup" else []) + [verify]
        if verification == "credential-429":
            expected = expected[:1]
        elif verification == "pre-submit-429":
            expected = [
                "https://b.i.instagram.com/api/v1/bloks/async_action/"
                "com.bloks.www.bloks.caa.login.process_client_data_and_redirect/"
            ]

        def send(adapter, request, **kwargs):
            calls.append(request.url)
            assert calls == expected[: len(calls)], "Unexpected request/order in offline 2FA flow"
            assert request.method == "POST"
            if verification in {"credential-429", "pre-submit-429"}:
                return response(request, 429, b"", "text/plain")
            if request.url == CAA:
                body = {"status": "ok", "two_step_verification_context": SECRET}
            elif request.url == verify:
                body = embedded_bloks(session=verification in {"session", "backup"}, user=True)
            else:
                body = {"status": "ok", "layout": {"bloks_payload": {"action": SECRET}}}
            return response(request, 200, json.dumps(body).encode())

        monkeypatch.setattr(requests.adapters.HTTPAdapter, "send", send)
        code = "12345678" if verification == "backup" else "123456"
        if observe:
            report = diagnostic.diagnose(client, "synthetic-user", SECRET, verification_code=code)
            result = report["outcome"]
            error_type = report.get("exception", {}).get("type")
        else:
            with diagnostic.quiet_library():
                try:
                    result = (
                        "success" if client.login("synthetic-user", SECRET, verification_code=code) else "false_return"
                    )
                    error_type = None
                except Exception as exc:
                    result, error_type = "error", type(exc).__name__
            report = None
        assert calls == expected
        return result, error_type, calls, report, client

    baseline = run(False)
    observed = run(True)
    assert observed[:3] == baseline[:3]
    report, client = observed[3:]
    expected_labels = [
        "caa/send_login_request",
        "two_step/entrypoint",
        "two_step/method_picker",
        "two_step/select_method",
    ]
    if verification == "backup":
        expected_labels.append("two_step/enter_backup_code")
    expected_labels.append("two_step/verify_code")
    if verification == "credential-429":
        expected_labels = expected_labels[:1]
    elif verification == "pre-submit-429":
        expected_labels = ["caa/process_client_data_and_redirect"]
    assert [item["endpoint"] for item in report["responses"]] == expected_labels
    if verification in {"session", "backup"}:
        assert report["outcome"] == "success"
        assert report["responses"][-1]["bloks"]["sessionid_cookie_present"] is (not inspection_failure)
        client.login_flow.assert_called_once_with()
    else:
        assert report["outcome"] == "error"
        assert report["exception"]["type"] == (
            "ClientThrottledError" if verification in {"credential-429", "pre-submit-429"} else "TwoFactorRequired"
        )
        client.login_flow.assert_not_called()
    assert SECRET not in json.dumps(report)
    assert client.private.hooks["response"] == []
    assert client.public.hooks["response"] == []


@pytest.mark.parametrize("error_type", [None, [], {}], ids=["null", "list", "dict"])
def test_non_string_error_metadata_does_not_hide_decoded_payload(diagnostic, error_type):
    body = embedded_bloks(session=True)
    body["error_type"] = error_type
    raw = response(requests.Request("POST", CAA).prepare(), 200, json.dumps(body).encode())
    summary = diagnostic.summarize_response(raw)
    assert summary["bloks"]["sessionid_cookie_present"] is True
    assert summary["bloks"]["inspection_error"] is False
    assert SECRET not in json.dumps(summary)


def test_response_inspection_failure_and_old_cookies_cannot_change_login(diagnostic, monkeypatch):
    client = Client(private_transport="requests")
    client.private.cookies.set("sessionid", SECRET)
    client.public.cookies.set("sessionid", SECRET)
    original_hook = Mock(side_effect=lambda raw, **kwargs: raw)
    client.private.hooks["response"].append(original_hook)
    client.handle_exception = Mock()
    original_handler = client.handle_exception
    original_caa = client.bloks_caa_login
    raw = response(requests.Request("POST", CAA).prepare(), 200, b"{}")

    def login(*args, **kwargs):
        for hook in list(client.private.hooks["response"]):
            assert hook(raw) is raw
        return True

    client.login = login
    clean = diagnostic.diagnose(client, "synthetic-user", SECRET)
    assert clean["responses"][0]["bloks"]["sessionid_cookie_present"] is False
    assert clean["responses"][0]["bloks"]["authorization_present"] is False
    monkeypatch.setattr(diagnostic, "summarize_bloks", Mock(side_effect=ValueError(SECRET)))
    report = diagnostic.diagnose(client, "synthetic-user", SECRET)
    assert report["outcome"] == "success"
    assert len(report["responses"]) == 1
    assert report["responses"][0]["bloks"]["inspection_error"] is True
    assert client.handle_exception is original_handler
    assert client.bloks_caa_login == original_caa
    assert "bloks_caa_login" not in vars(client)
    assert client.private.hooks["response"] == [original_hook]
    assert client.public.hooks["response"] == []
    assert SECRET not in json.dumps(report)


def test_capture_failure_preserves_exception_identity_and_response_index(diagnostic, monkeypatch):
    client = Client()
    error = SystemExit(SECRET)
    raw = response(requests.Request("POST", CAA).prepare(), 429, b"", "text/plain")

    def login(*args, **kwargs):
        for hook in client.private.hooks["response"]:
            assert hook(raw) is raw
        raise error

    client.login = login
    monkeypatch.setattr(diagnostic, "summarize_response", Mock(side_effect=ValueError(SECRET)))
    with pytest.raises(SystemExit) as caught:
        diagnostic.diagnose(client, "synthetic-user", SECRET)
    assert caught.value is error
    assert client.private.hooks["response"] == []
    assert client.public.hooks["response"] == []
