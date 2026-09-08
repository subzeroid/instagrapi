"""Explicitly enabled, single-attempt CAA checks on ten fresh test accounts.

Run with INSTAGRAPI_RUN_CAA_LIVE=1 and TEST_ACCOUNTS_URL configured. A private
INSTAGRAPI_CAA_ACCOUNTS_FILE may instead supply ten freshly assigned records.
Do not reuse these records for a second run. Credentials and responses are never
included in pytest failures; successful settings are saved only in the private
INSTAGRAPI_CAA_LIVE_DIR (or pytest's temporary directory).
"""

import copy
import json
import logging
import os
import time
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import pytest
import requests

from instagrapi import Client

pytestmark = pytest.mark.skipif(
    os.getenv("INSTAGRAPI_RUN_CAA_LIVE") != "1", reason="fresh CAA logins require explicit opt-in"
)


class ProbeStopped(BaseException):
    """Leave library fallback/retry handlers immediately."""


@pytest.fixture(scope="module")
def fresh_accounts():
    try:
        if path := os.getenv("INSTAGRAPI_CAA_ACCOUNTS_FILE"):
            accounts = json.loads(Path(path).read_text())
        else:
            parts = urlsplit(os.environ["TEST_ACCOUNTS_URL"])
            query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k != "count"]
            source = urlunsplit(
                (parts.scheme, parts.netloc, parts.path, urlencode([*query, ("count", "10")]), parts.fragment)
            )
            response = requests.get(source, timeout=(10, 40))
            response.raise_for_status()
            accounts = response.json()
        assert isinstance(accounts, list) and len(accounts) == 10
        assert len({account["username"].casefold() for account in accounts}) == 10
        assert all(
            all(account.get(key) for key in ("username", "password", "user_id", "proxy", "client_settings"))
            for account in accounts
        )
    except Exception as exc:
        pytest.fail(f"Fresh-account setup failed ({type(exc).__name__})", pytrace=False)
    return accounts


@pytest.fixture(scope="module")
def private_results(tmp_path_factory):
    path = os.getenv("INSTAGRAPI_CAA_LIVE_DIR")
    root = Path(path) if path else tmp_path_factory.mktemp("caa-live")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    root.chmod(0o700)
    return root


def write_private(path, data):
    with path.open("w") as stream:
        path.chmod(0o600)
        json.dump(data, stream, indent=2)


@pytest.mark.parametrize("index", range(10), ids=[f"account-{n:02d}" for n in range(1, 11)])
def test_caa_login_with_private_curl(fresh_accounts, private_results, index):
    account = fresh_accounts[index]
    result_dir = private_results / f"account-{index + 1:02d}"
    result_dir.mkdir(mode=0o700, exist_ok=True)
    marker = result_dir / "started.json"
    try:
        with marker.open("x") as stream:
            marker.chmod(0o600)
            json.dump({"max_password_submissions": 1}, stream)
    except FileExistsError:
        pytest.fail(
            "This account probe was already started; use fresh records and a new results directory", pytrace=False
        )

    report = {"password_submissions": 0, "responses": [], "session_validated": False}
    started = time.monotonic()
    previous_logging = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    client = None
    try:
        settings = copy.deepcopy(account["client_settings"])
        settings.pop("totp_seed", None)
        settings.update(session_retry_total=0, public_request_retries_count=1, private_transport="curl")
        client = Client(settings=settings, proxy=account["proxy"])
        client.username, client.password = account["username"], account["password"]
        if not client.bloks_versioning_id:
            pytest.skip("Assigned profile has no known CAA Bloks hash")

        def stop(*args, **kwargs):
            raise ProbeStopped("Manual account verification required")

        def capture(response, *args, **kwargs):
            report["responses"].append(response.status_code)
            if response.status_code == 429:
                raise ProbeStopped("HTTP 429; no further requests sent")
            if 300 <= response.status_code < 400:
                raise ProbeStopped("Unexpected redirect")
            return response

        client.challenge_code_handler = stop
        client.change_password_handler = stop
        client.handle_exception = lambda _client, exc: (_ for _ in ()).throw(exc)
        for session in (client.private, client.public, client.graphql):
            session.trust_env = False
            session.hooks["response"].append(capture)
            original_send = session.send

            def send(prepared, _send=original_send, **kwargs):
                target = urlsplit(prepared.url)
                if target.hostname not in {"i.instagram.com", "b.i.instagram.com", "www.instagram.com"}:
                    raise ProbeStopped("Unexpected destination")
                if (
                    "/challenge/" in target.path
                    or "/auth_platform/" in target.path
                    or "/accounts/login/" in target.path
                ):
                    raise ProbeStopped("Unexpected login or verification route")
                if len(report["responses"]) >= 25 or time.monotonic() - started > 180:
                    raise ProbeStopped("Probe request or time budget reached")
                if "caa.login.async.send_login_request" in target.path:
                    if report["password_submissions"]:
                        raise ProbeStopped("Duplicate password submission blocked")
                    report["password_submissions"] += 1
                kwargs.update(timeout=(10, 25), allow_redirects=False)
                return _send(prepared, **kwargs)

            session.send = send

        client._clear_session_state(
            clear_authorization_data=True,
            clear_authorization_header=True,
            clear_private_cookies=True,
            clear_public_cookies=True,
            clear_last_login=True,
        )
        assert not client.user_id
        assert client.bloks_caa_login_prepare(username=client.username)
        response = client.bloks_caa_login_send_request(client.password, username=client.username, auto_prepare=False)
        if not client.bloks_apply_login_response(response):
            if client.bloks_extract_two_step_verification_context(response) or client.bloks_caa_login_needs_two_step(
                response
            ):
                report["verification_required"] = True
                pytest.skip("CAA reached account verification; session success was not established")
            pytest.fail("CAA did not return a session", pytrace=False)
        report["session_validated"] = str(client.account_info().pk) == str(account["user_id"])
        assert report["session_validated"]
        assert report["password_submissions"] == 1
        write_private(result_dir / "settings.private.json", client.get_settings())
    except ProbeStopped as exc:
        report["stop_reason"] = str(exc)
        pytest.fail(str(exc), pytrace=False)
    except Exception as exc:
        report["exception"] = type(exc).__name__
        pytest.fail(f"CAA probe failed ({type(exc).__name__})", pytrace=False)
    finally:
        if client:
            for session in (client.private, client.public, client.graphql):
                session.close()
        logging.disable(previous_logging)
        report["elapsed_seconds"] = round(time.monotonic() - started, 2)
        write_private(result_dir / "result.sanitized.json", report)
