"""Capture shareable login diagnostics without exporting credentials or payloads.

Download this file and run it with the same Python environment and instagrapi
version as the failing script. Use --settings for its existing settings file,
--proxy to enter the same proxy privately, and --relogin to test password login
even if the settings already contain an authorized session. Only the report is
intended for sharing; the settings file contains private session credentials.
"""

import argparse
import contextlib
import getpass
import json
import logging
import os
import platform
import tempfile
import warnings
from importlib.metadata import version
from pathlib import Path
from urllib.parse import urlsplit

from instagrapi import Client
from instagrapi.exceptions import ChallengeRequired

ERROR_TYPES = {
    "bad_password",
    "challenge_required",
    "checkpoint_required",
    "login_required",
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


def allowed(value, choices):
    """Never copy arbitrary server strings, even from normally harmless fields."""
    if value is None:
        return None
    return value if isinstance(value, str) and value in choices else "other"


def message_category(value):
    if not isinstance(value, str) or not value:
        return None
    text = value.lower()
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


def endpoint_label(path):
    for suffix, label in (
        ("/accounts/login/", "accounts/login"),
        ("/accounts/two_factor_login/", "accounts/two_factor_login"),
        ("/accounts/current_user/", "accounts/current_user"),
        ("send_login_request/", "caa/send_login_request"),
        ("process_client_data/", "caa/process_client_data"),
        ("oauth_token.fetch/", "caa/oauth_token_fetch"),
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


def summarize_response(response):
    url = urlsplit(response.url)
    try:
        body = summarize_json(response.json())
    except ValueError:
        body = {"type": "non_json"}
    return {
        "host": allowed(url.hostname, {"i.instagram.com", "b.i.instagram.com", "www.instagram.com"}),
        "endpoint": endpoint_label(url.path),
        "method": allowed(response.request.method if response.request else None, {"GET", "POST"}),
        "http_status": response.status_code,
        "content_type": allowed(response.headers.get("Content-Type", "").split(";", 1)[0], CONTENT_TYPES),
        "body_bytes": len(response.content),
        "json": body,
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
    report = {"outcome": "error", "responses": []}

    def capture(response, *args, **kwargs):
        report["responses"].append(summarize_response(response))
        return response

    def stop_on_error(client, exc):
        # Legacy challenge resolution can create unobserved requests.Session objects.
        # Re-raise the original error; login() can still perform its CAA fallback.
        raise exc

    sessions = (client.private, client.public)
    previous_handler = client.handle_exception
    client.handle_exception = stop_on_error
    for session in sessions:
        session.hooks.setdefault("response", []).append(capture)
    try:
        with quiet_library():
            try:
                result = client.login(username, password, relogin=relogin, verification_code=verification_code)
                report["outcome"] = "success" if result else "false_return"
            except (Exception, KeyboardInterrupt) as exc:
                report["exception"] = {**summarize_json(vars(exc)), "type": type(exc).__name__}
    finally:
        client.handle_exception = previous_handler
        for session in sessions:
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
