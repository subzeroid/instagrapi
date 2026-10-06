"""Capture shareable login diagnostics without exporting credentials or payloads.

Download this file and run it with the same Python environment and instagrapi
version as the failing script. Use --settings for its existing settings file,
--proxy to enter the same proxy privately, and --relogin to test password login
even if the settings already contain an authorized session. Only the report is
intended for sharing; the settings file contains private session credentials.

The report records response stages and each CAA outcome before a fallback
replaces the last response. Marker presence means a reference was found, not
that Instagram executed it or accepted a verification code.
"""

import argparse
import contextlib
import getpass
import json
import logging
import os
import platform
import re
import tempfile
import warnings
from importlib.metadata import version
from pathlib import Path
from urllib.parse import urlsplit

from instagrapi import Client
from instagrapi.config import APP_SETTINGS
from instagrapi.exceptions import ChallengeRequired
from instagrapi.mixins.bloks import AP_2SV_ENTRYPOINT, BloksMixin

ERROR_TYPES = {
    "bad_password",
    "challenge_required",
    "checkpoint_required",
    "login_required",
    "needs_upgrade",
    "two_factor_required",
    "rate_limit_error",
    "sentry_block",
    "feedback_required",
}
STEPS = {
    "select_verify_method",
    "verify_code",
    "submit_phone",
    "submit_phone_number",
    "verify_email",
    "verify_sms",
    "change_password",
    "force_set_new_password",
    "delta_login_review",
    "select_contact_point_recovery",
}
CONTENT_TYPES = {"application/json", "text/json", "text/html", "text/plain"}
CAA_REASONS = {
    "",
    "CAA login did not return a session",
    "CAA preflight did not return account access and attestation data",
    "missing entrypoint context_data",
    "missing code_entry context_data",
    "missing code_entry_async context_data",
}
BLOKS_APPS = {
    "com.bloks.www.bloks.caa.login.process_client_data_and_redirect": "caa/process_client_data_and_redirect",
    "com.bloks.www.caa.login.oauth.token.fetch.async": "caa/oauth_token_fetch",
    "com.bloks.www.bloks.caa.login.async.send_login_request": "caa/send_login_request",
    "com.bloks.www.two_step_verification.entrypoint": "two_step/entrypoint",
    "com.bloks.www.two_step_verification.method_picker": "two_step/method_picker",
    "com.bloks.www.two_step_verification.method_picker.navigation.async": "two_step/select_method",
    "com.bloks.www.two_factor_login.enter_totp_code": "two_step/enter_totp_code",
    "com.bloks.www.two_factor_login.enter_backup_code": "two_step/enter_backup_code",
    "com.bloks.www.two_step_verification.verify_code.async": "two_step/verify_code",
    "com.bloks.www.two_step_verification.has_been_allowed.async": "two_step/has_been_allowed",
    "com.bloks.www.caa.notif_status.async": "caa/notif_status",
    "com.bloks.www.ap.two_step_verification.entrypoint_async": "profile_code/entrypoint",
    "com.bloks.www.ap.two_step_verification.code_entry": "profile_code/code_entry",
    "com.bloks.www.ap.two_step_verification.code_entry_async": "profile_code/code_entry_async",
}
# These helpers only parse their input; this instance has no client sessions.
BLOKS_PARSER = BloksMixin()


def allowed(value, choices):
    """Never copy arbitrary server strings, even from normally harmless fields."""
    if value is None:
        return None
    return value if isinstance(value, str) and value in choices else "other"


def message_category(value):
    if not isinstance(value, str) or not value:
        return None
    text = value.lower()
    if text.startswith("your version of instagram is out of date"):
        return "app_out_of_date"
    if "email" in text and "back into your account" in text:
        return "email_account_recovery"
    for marker in (
        "challenge_required",
        "login_required",
        "two_factor_required",
        "feedback_required",
        "please wait a few minutes",
        "too many requests",
        "bad password",
        "incorrect password",
        "manual verification",
    ):
        if marker in text:
            return marker.replace(" ", "_")
    return "other"


def challenge_path(value):
    if not isinstance(value, str) or not value:
        return None
    for prefix in ("/api/v1/challenge/", "/api/challenge/", "/challenge/", "/auth_platform/"):
        if value.startswith(prefix):
            return prefix + "<redacted>"
    return "other"


def summarize_json(data):
    if not isinstance(data, dict):
        return {"type": type(data).__name__}
    challenge = data.get("challenge")
    if not isinstance(challenge, dict):
        challenge = {}
    native = challenge.get("native_flow")
    return {
        "type": "dict",
        "empty": not bool(data),
        "message_category": message_category(data.get("message")),
        "error_type": allowed(data.get("error_type"), ERROR_TYPES),
        "status": allowed(data.get("status"), {"ok", "fail"}),
        "step_name": allowed(data.get("step_name"), STEPS),
        "bloks_action": allowed(data.get("bloks_action"), {"com.bloks.www.ig.challenge.redirect.async"}),
        "challenge_native_flow": native if isinstance(native, bool) or native is None else "other",
        "challenge_api_path": challenge_path(challenge.get("api_path")),
    }


def endpoint_label(path, request_headers=None):
    for app, label in BLOKS_APPS.items():
        if any(path.endswith(f"/bloks/{kind}/{app}/") for kind in ("apps", "async_action")):
            return label
    if path.endswith("/graphql_www") and (request_headers or {}).get("X-FB-Friendly-Name") == (
        "IGUSDIDRegistrationMutation"
    ):
        return "usdid/registration"
    for suffix, label in (
        ("/accounts/login/", "accounts/login"),
        ("/accounts/two_factor_login/", "accounts/two_factor_login"),
        ("/accounts/current_user/", "accounts/current_user"),
        ("/send_login_request/", "caa/send_login_request"),
        ("/process_client_data/", "caa/process_client_data"),
        ("/oauth_token.fetch/", "caa/oauth_token_fetch"),
        ("/attestation/create_android_keystore/", "attestation/create_android_keystore"),
        ("/launcher/sync/", "launcher/sync"),
        ("/qe/sync/", "qe/sync"),
        ("/feed/timeline/", "feed/timeline"),
        ("/feed/reels_tray/", "feed/reels_tray"),
    ):
        if path.endswith(suffix):
            return label
    for marker in ("challenge", "attestation", "usdid", "bloks"):
        if marker in path:
            return marker
    return "other"


def proxy_error_category(value):
    """Read a reported token or error parameter without copying proxy details."""
    if value is None:
        return None
    if value.strip() == "http_request_error":
        return "http_request_error"
    # Keep quoted parameter values intact so a details string cannot supply
    # an apparent error parameter through its own semicolons or commas.
    parts = []
    current = ""
    index = 0
    while index < len(value):
        token = re.match(r'"(?:[^"\\]|\\.)*"|[^;,\"]+|[;,]', value[index:])
        if token is None:
            return "other"
        item = token.group()
        if item in {";", ","}:
            parts.append(current.strip())
            current = ""
        else:
            current += item
        index += len(item)
    parts.append(current.strip())
    if any(re.fullmatch(r'error\s*=\s*(?:http_request_error|"http_request_error")', part) for part in parts[1:]):
        return "http_request_error"
    return "other"


def empty_bloks_summary():
    return {
        "referenced_apps": [],
        "fallback_reference_present": False,
        "login_success_reference_present": False,
        "continuation_reference_present": False,
        "two_step_context_parsed": False,
        "profile_code_context_parsed": False,
        "error_reference_present": False,
        "login_response_reference_present": False,
        "login_response_decoded": False,
        "logged_in_user_present": False,
        "authorization_present": False,
        "sessionid_cookie_present": False,
        "inspection_error": False,
    }


def summarize_bloks(data):
    """Inspect only this received payload, without executing or applying it."""
    summary = empty_bloks_summary()
    if not isinstance(data, dict):
        return summary
    try:
        strings = []
        BLOKS_PARSER._bloks_collect_strings(data, strings)
        text = "\n".join(strings)
        apps = [app for app in BLOKS_APPS if re.search(r"(?<![\w.])" + re.escape(app) + r"(?![\w.])", text)]
        summary["referenced_apps"] = apps
        summary["continuation_reference_present"] = any(
            BLOKS_APPS[app].startswith(("two_step/", "profile_code/")) for app in apps
        )
        summary["fallback_reference_present"] = any(value.startswith("CAA_LOGIN_FALLBACK:") for value in strings)
        summary["login_success_reference_present"] = any(
            marker in strings or f'"{marker}"' in text for marker in ("login_success", "two_fac_redirect")
        )
        summary["error_reference_present"] = (
            allowed(data.get("error_type"), ERROR_TYPES) not in {None, "other"}
            or message_category(data.get("message")) not in {None, "other"}
            or any(value.startswith("CAA_LOGIN_OCL_ERROR:") for value in strings)
        )
        summary["login_response_reference_present"] = bool(re.search(r"(?<![\w])login_response(?![\w])", text))
        summary["two_step_context_parsed"] = bool(BLOKS_PARSER.bloks_extract_two_step_verification_context(data))
        summary["profile_code_context_parsed"] = any(
            BLOKS_PARSER.bloks_extract_context_data(data, app)
            for app in apps
            if BLOKS_APPS[app].startswith("profile_code/")
        )
        parsed = BLOKS_PARSER.bloks_extract_login_response(data)
        summary["login_response_decoded"] = bool(parsed)
        login = parsed.get("login_response")
        headers = parsed.get("headers")
        cookies = parsed.get("cookies")
        summary["logged_in_user_present"] = isinstance(login, dict) and bool(login.get("logged_in_user"))
        summary["authorization_present"] = isinstance(headers, dict) and bool(
            headers.get("IG-Set-Authorization") or headers.get("ig-set-authorization")
        )
        summary["sessionid_cookie_present"] = isinstance(cookies, dict) and bool(cookies.get("sessionid"))
    except Exception:
        summary["inspection_error"] = True
    return summary


def summarize_response(response):
    url = urlsplit(response.url)
    data = None
    try:
        data = response.json()
        body = summarize_json(data)
    except ValueError:
        body = {"type": "non_json"}
    summary = {
        "host": allowed(url.hostname, {"i.instagram.com", "b.i.instagram.com", "www.instagram.com"}),
        "endpoint": endpoint_label(url.path, response.request.headers if response.request is not None else None),
        "method": allowed(response.request.method if response.request else None, {"GET", "POST"}),
        "http_status": response.status_code,
        "content_type": allowed(response.headers.get("Content-Type", "").split(";", 1)[0], CONTENT_TYPES),
        "body_bytes": len(response.content),
        "json": body,
        "server_category": allowed(response.headers.get("Server"), {"proxygen-bolt"}),
        "proxy_error_category": proxy_error_category(response.headers.get("Proxy-Status")),
        "retry_after_present": "Retry-After" in response.headers,
    }
    if "/bloks/" in url.path:
        try:
            summary["bloks"] = summarize_bloks(data)
        except Exception:
            summary["bloks"] = {**empty_bloks_summary(), "inspection_error": True}
    return summary


def summarize_caa_outcome(client, outcome):
    """Record parsed state and reference presence without copying context values."""
    result = outcome.get("result")
    result = result if isinstance(result, dict) else {}
    markers = client._caa_result_action_markers(outcome)
    return {
        "logged_in": bool(outcome.get("logged_in")),
        "two_factor_context_present": bool(client._extract_two_step_verification_context(outcome)),
        "reason": allowed(outcome.get("reason"), CAA_REASONS),
        "fallback_marker_present": any(marker.startswith("CAA_LOGIN_FALLBACK:") for marker in markers),
        "profile_code_reference_present": client.bloks_caa_login_needs_two_step(result),
        "profile_code_context_parsed": bool(client.bloks_extract_context_data(result, AP_2SV_ENTRYPOINT)),
    }


@contextlib.contextmanager
def quiet_library():
    """Library logs and exception messages can contain raw responses or proxies."""
    previous = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        with open(os.devnull, "w") as sink, warnings.catch_warnings():
            warnings.simplefilter("ignore")
            with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
                yield
    finally:
        logging.disable(previous)


def manual_checkpoint(*args, **kwargs):
    raise ChallengeRequired("Manual verification required; no automatic input in diagnostic mode")


def diagnose(client, username, password, *, relogin=False, verification_code=""):
    """Observe one login() call; snapshot each response before fallback mutates state."""
    report = {
        "outcome": "error",
        "responses": [],
        "caa_attempts": [],
        "client_profile": {
            "app_version": allowed(client.device_settings.get("app_version"), APP_SETTINGS),
            "bloks_versioning_id_present": bool(client.bloks_versioning_id),
            "private_transport": allowed(getattr(client, "private_transport", None), {"curl", "requests"}),
        },
    }

    original_caa = client.bloks_caa_login
    missing = object()
    previous_caa_override = vars(client).get("bloks_caa_login", missing)

    def observe_caa(*args, **kwargs):
        attempt = {"outcome": "error", "response_start": len(report["responses"])}
        report["caa_attempts"].append(attempt)
        try:
            outcome = original_caa(*args, **kwargs)
            attempt["outcome"] = "returned"
            try:
                attempt.update(summarize_caa_outcome(client, outcome))
            except Exception:
                # Inspection must not change the original result or expose an
                # exception message containing an unexpected response payload.
                attempt["inspection_error"] = True
            return outcome
        finally:
            attempt["response_end"] = len(report["responses"])

    def capture(response, *args, **kwargs):
        try:
            summary = summarize_response(response)
        except Exception:
            # Keep the response's position even if optional inspection fails.
            summary = {"inspection_error": True}
        report["responses"].append(summary)
        return response

    def stop_on_error(client, exc):
        # Legacy challenge resolution can create unobserved requests.Session objects.
        # Re-raise the original error; login() can still perform its CAA fallback.
        raise exc

    sessions = (client.private, client.public)
    registered = []
    previous_handler = client.handle_exception
    try:
        client.handle_exception = stop_on_error
        client.bloks_caa_login = observe_caa
        for session in sessions:
            session.hooks.setdefault("response", []).append(capture)
            registered.append(session)
        with quiet_library():
            try:
                result = client.login(username, password, relogin=relogin, verification_code=verification_code)
                report["outcome"] = "success" if result else "false_return"
            except (Exception, KeyboardInterrupt) as exc:
                report["exception"] = {**summarize_json(vars(exc)), "type": type(exc).__name__}
    finally:
        client.handle_exception = previous_handler
        if previous_caa_override is missing:
            del client.bloks_caa_login
        else:
            client.bloks_caa_login = previous_caa_override
        for session in registered:
            session.hooks["response"].remove(capture)
    report["last_json"] = summarize_json(client.last_json)
    return report


def write_private_json(path, data):
    """Replace atomically with a mode-0600 file, including when a file already exists."""
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(data, stream, indent=2, ensure_ascii=True)
            stream.write("\n")
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def bound_requests(session):
    original = session.request

    def request(*args, **kwargs):
        if kwargs.get("timeout") is None:
            kwargs["timeout"] = (10, 30)
        return original(*args, **kwargs)

    session.request = request


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--settings",
        type=Path,
        default=Path(os.getenv("IG_SESSION_FILE", "session.json")),
        help="private settings file to load and update, including after failure (default: session.json)",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("login-diagnostic.json"),
        help="sanitized JSON report to share (default: login-diagnostic.json)",
    )
    parser.add_argument(
        "--relogin", action="store_true", help="test password login even with an authorized saved session"
    )
    parser.add_argument("--proxy", action="store_true", help="prompt privately for the same proxy used by your script")
    parser.add_argument("--two-factor", action="store_true", help="prompt privately for a current 2FA code")
    args = parser.parse_args(argv)
    settings_path, report_path = args.settings.resolve(), args.report.resolve()
    if settings_path == report_path:
        parser.error("--settings and --report must be different files")

    client = None
    report = {"outcome": "setup_error", "responses": []}
    report_written = True
    try:
        settings = json.loads(settings_path.read_text()) if settings_path.exists() else {}
        if not isinstance(settings, dict):
            raise ValueError("Settings must be a JSON object")
        report["environment"] = {
            "instagrapi": version("instagrapi"),
            "python": platform.python_version(),
            "os": platform.system(),
            "settings_loaded": settings_path.exists(),
            "relogin": args.relogin,
            "transport_retries": 0,
            "connect_timeout_seconds": 10,
            "read_timeout_seconds": 30,
        }
        # Check report destination and settings permissions before making requests.
        write_private_json(report_path, report)
        write_private_json(settings_path, settings)
        username = os.getenv("IG_USERNAME") or input("Instagram username: ").strip()
        password = os.getenv("IG_PASSWORD") or getpass.getpass("Instagram password: ")
        proxy = getpass.getpass("Proxy URL: ") if args.proxy else os.getenv("IG_PROXY")
        code = getpass.getpass("Current 2FA code: ") if args.two_factor else ""
        if not username or not password:
            raise ValueError("Credentials are required")
        with quiet_library():
            client = Client(
                settings={**settings, "session_retry_total": 0, "public_request_retries_count": 1}, proxy=proxy
            )
        client.challenge_code_handler = manual_checkpoint
        client.change_password_handler = manual_checkpoint
        for session in (client.private, client.public):
            bound_requests(session)
        report["environment"]["proxy_configured"] = bool(proxy)
        report["environment"]["two_factor_code_supplied"] = bool(code)
        print("Running one login attempt; please wait...")
        report.update(diagnose(client, username, password, relogin=args.relogin, verification_code=code))
    except (Exception, KeyboardInterrupt) as exc:
        report["exception"] = {"type": type(exc).__name__}
    finally:
        if client is not None:
            try:
                updated_settings = client.get_settings()
                for key in ("session_retry_total", "public_request_retries_count"):
                    if key in settings:
                        updated_settings[key] = settings[key]
                    else:
                        updated_settings.pop(key, None)
                write_private_json(settings_path, updated_settings)
                report["settings_saved"] = True
            except Exception as exc:
                report["settings_saved"] = False
                report["settings_save_error"] = type(exc).__name__
        try:
            write_private_json(report_path, report)
        except Exception as exc:
            print(f"Could not write the report ({type(exc).__name__}).")
            report_written = False
    if not report_written:
        return 1
    print("Report saved to --report (default: login-diagnostic.json). Review it before sharing.")
    print("Keep the --settings file private: it contains session credentials.")
    return 0 if report["outcome"] == "success" and report.get("settings_saved") else 1


if __name__ == "__main__":
    raise SystemExit(main())
