import multiprocessing
import os
import queue
import time
import traceback
import unittest
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests

from instagrapi import Client
from instagrapi.exceptions import MediaError
from tests.helpers import TEST_ACCOUNTS_URL


def _insights_test_accounts_url(count=3):
    parts = urlsplit(TEST_ACCOUNTS_URL)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["count"] = str(count)
    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            parts.path,
            urlencode(query),
            parts.fragment,
        )
    )


def _insights_client_from_test_account(acc):
    settings = dict(acc["client_settings"])
    totp_seed = settings.pop("totp_seed", None)
    cl = Client(settings=settings, proxy=os.getenv("IG_PROXY") or acc["proxy"])
    login_kwargs = {
        "username": acc["username"],
        "password": acc["password"],
        "relogin": True,
    }
    if totp_seed:
        totp_code = cl.totp_generate_code(totp_seed)
        cl.totp_seed = totp_seed
        cl.totp_code = totp_code
        login_kwargs["verification_code"] = totp_code
    cl.login(**login_kwargs)
    cl._user_id = acc.get("user_id")
    return cl


def _insights_fresh_account():
    response = requests.get(_insights_test_accounts_url(), verify=False, timeout=30)
    response.raise_for_status()
    last_exc = None
    for acc in response.json()[:3]:
        try:
            return _insights_client_from_test_account(acc)
        except Exception as exc:
            last_exc = exc
            continue
    if last_exc:
        raise RuntimeError(f"No usable fresh account returned: {last_exc}") from last_exc
    raise RuntimeError("No usable fresh account returned")


def _ensure_creator_account(cl):
    account = cl.account_info()
    if account.account_type == 3:
        return
    account = cl.account_convert_to_creator(
        category_id="2347428775505624",
        should_show_category=True,
        should_show_public_contacts=False,
    )
    if account.account_type != 3:
        raise AssertionError(f"Expected creator account type 3, got {account.account_type}")


def _uploaded_media_payload(cl, media, attempts=5, delay=3):
    last_result = None
    for attempt in range(attempts):
        if attempt:
            time.sleep(delay)
        result = cl.private_request(f"media/{media.pk}/info/")
        last_result = result
        items = result.get("items") or []
        if items:
            return items[0]
    raise AssertionError(f"Uploaded media was not accessible: {last_result}")


def _wait_for_media_insights(cl, media, attempts=6, delay=5):
    last_error = None
    for attempt in range(attempts):
        if attempt:
            time.sleep(delay)
        try:
            result = cl.insights_media(media.pk)
        except MediaError as exc:
            last_error = exc
            continue
        inline_insights = result.get("inline_insights_node")
        if not isinstance(inline_insights, dict):
            raise AssertionError(f"inline_insights_node is not a dict: {inline_insights!r}")
        if not inline_insights.get("state"):
            raise AssertionError(f"inline insights state is empty: {inline_insights!r}")
        if not isinstance(inline_insights.get("metrics"), dict):
            raise AssertionError(f"inline insights metrics are missing: {inline_insights!r}")
        return result
    raise MediaError(f"Instagram did not expose inline insights for uploaded media: {last_error}")


def _run_insights_media_owned_photo_live(result_queue):
    if not TEST_ACCOUNTS_URL:
        result_queue.put({"status": "skip", "reason": "TEST_ACCOUNTS_URL is required for insights live tests"})
        return

    cl = None
    media = None
    try:
        cl = _insights_fresh_account()
        _ensure_creator_account(cl)
        media = cl.photo_upload(Path("examples/kanada.jpg"), "Insights media live test")
        payload = _uploaded_media_payload(cl, media)
        if str(payload.get("pk")) != str(media.pk):
            raise AssertionError(f"Uploaded media payload pk mismatch: {payload.get('pk')} != {media.pk}")
        result = _wait_for_media_insights(cl, media)
        result_queue.put(
            {
                "status": "ok",
                "instagram_media_id": str(result.get("instagram_media_id")),
                "media_pk": str(media.pk),
                "has_like_count": "like_count" in result,
                "has_comment_count": "comment_count" in result,
            }
        )
    except MediaError as exc:
        result_queue.put({"status": "skip", "reason": str(exc)})
    except Exception:
        result_queue.put({"status": "error", "traceback": traceback.format_exc()})
    finally:
        if cl and media:
            try:
                cl.media_delete(media.id)
            except Exception:
                pass


class ClientInsightsLiveTestCase(unittest.TestCase):
    def run_insights_worker(self):
        if not TEST_ACCOUNTS_URL:
            self.skipTest("TEST_ACCOUNTS_URL is required for insights live tests")
        ctx = multiprocessing.get_context("spawn")
        result_queue = ctx.Queue()
        process = ctx.Process(target=_run_insights_media_owned_photo_live, args=(result_queue,))
        process.start()
        timeout = int(os.getenv("INSTAGRAPI_INSIGHTS_LIVE_TIMEOUT", "180"))
        process.join(timeout)
        if process.is_alive():
            process.terminate()
            process.join(10)
            self.skipTest(f"Insights live workflow timed out after {timeout} seconds")
        try:
            return result_queue.get(timeout=5)
        except queue.Empty:
            if process.exitcode:
                self.fail(f"Insights live workflow exited with code {process.exitcode}")
            self.fail("Insights live workflow did not return a result")

    def test_insights_media_owned_photo_live(self):
        result = self.run_insights_worker()
        if result["status"] == "skip":
            self.skipTest(result["reason"])
        if result["status"] == "error":
            self.fail(result["traceback"])
        self.assertEqual(result["instagram_media_id"], result["media_pk"])
        self.assertTrue(result["has_like_count"])
        self.assertTrue(result["has_comment_count"])
