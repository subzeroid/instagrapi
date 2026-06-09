import multiprocessing
import os
import queue
import traceback
import unittest

from tests.helpers import TEST_ACCOUNTS_URL, fresh_test_account


def _run_search_hashtags_live(result_queue):
    if not TEST_ACCOUNTS_URL:
        result_queue.put({"status": "skip", "reason": "TEST_ACCOUNTS_URL is required for hashtag search live tests"})
        return
    try:
        cl = fresh_test_account(count=3, attempts=3, timeout=30)
        hashtags = cl.search_hashtags("restaurant")
        if not hashtags:
            result_queue.put({"status": "skip", "reason": "Instagram returned no hashtags for restaurant"})
            return
        first = hashtags[0]
        raw_id = cl.last_json["results"][0]["id"]
        result_queue.put(
            {
                "status": "ok",
                "raw_id": raw_id,
                "raw_id_type": type(raw_id).__name__,
                "id": first.id,
                "id_type": type(first.id).__name__,
                "name": first.name,
                "count": len(hashtags),
            }
        )
    except Exception:
        result_queue.put({"status": "error", "traceback": traceback.format_exc()})


class ClientHashtagSearchLiveTestCase(unittest.TestCase):
    def run_worker(self):
        if not TEST_ACCOUNTS_URL:
            self.skipTest("TEST_ACCOUNTS_URL is required for hashtag search live tests")
        ctx = multiprocessing.get_context("spawn")
        result_queue = ctx.Queue()
        process = ctx.Process(target=_run_search_hashtags_live, args=(result_queue,))
        process.start()
        timeout = int(os.getenv("INSTAGRAPI_HASHTAG_SEARCH_LIVE_TIMEOUT", "120"))
        process.join(timeout)
        if process.is_alive():
            process.terminate()
            process.join(10)
            self.skipTest(f"Hashtag search live workflow timed out after {timeout} seconds")
        try:
            return result_queue.get(timeout=5)
        except queue.Empty:
            if process.exitcode:
                self.fail(f"Hashtag search live workflow exited with code {process.exitcode}")
            self.fail("Hashtag search live workflow did not return a result")

    def test_search_hashtags_accepts_private_numeric_ids_live(self):
        result = self.run_worker()
        if result["status"] == "skip":
            self.skipTest(result["reason"])
        if result["status"] == "error":
            self.fail(result["traceback"])
        self.assertEqual(result["raw_id_type"], "int")
        self.assertEqual(result["id_type"], "str")
        self.assertEqual(result["id"], str(result["raw_id"]))
        self.assertTrue(result["id"])
        self.assertTrue(result["name"])
        self.assertGreater(result["count"], 0)
