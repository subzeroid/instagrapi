# Modern Batched User Stories Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the rejected legacy batch-story query with the already proven modern XDT query while preserving the `users_stories_gql` API.

**Architecture:** Send 50-ID batches through `graphql_request`, validate the XDT envelope, and convert each nonempty reel into one `UserShort` using the existing `extract_story_web`. Do not add a new public method, a legacy fallback, or changes to private story routing.

**Tech Stack:** Python 3.11+, Pydantic models, unittest/mock, pytest, Ruff, MkDocs.

**Final live-driven adjustments:** The server rejected 50-ID requests with HTTP 200 and `data:null`, while 25-ID requests succeeded. The final code and regressions use 25+25+1 for 51 IDs. `extract_story_web` additionally maps observed `story_feed_media.id` and `media_code` to `media_id`; this was added by a separate failing-first regression. The exact final live candidates are instagrapi `9fef5358` and aiograpi `b3374f7a`.

---

### Task 1: Modern request and batch regressions

**Files:**
- Modify: `tests/regression/test_story.py:101-130`
- Modify: `tests/regression/test_legacy_routing.py:1-2,143-184`

- [ ] **Step 1: Replace the single-user legacy test with a modern contract test**

Use the existing `web_story_payload()` fixture and this test body:

```python
def test_users_stories_gql_populates_user_short_stories(self):
    client = Client()
    client._fb_dtsg = "token"
    body = {
        "data": {
            "xdt_api__v1__feed__reels_media": {
                "reels_media": [{"items": [web_story_payload(), web_story_payload()]}]
            }
        }
    }
    with mock.patch.object(client, "graphql_request", return_value=body) as request:
        users = client.users_stories_gql(["271828182845904"], amount=1)

    self.assertEqual(len(users), 1)
    self.assertEqual(users[0].pk, "271828182845904")
    self.assertEqual(len(users[0].stories), 1)
    self.assertEqual(users[0].stories[0].pk, "314159265358979")
    request.assert_called_once_with(
        data={
            "variables": json.dumps(
                {
                    "reel_ids_arr": ["271828182845904"],
                    "__relay_internal__pv__PolarisCommunityNoteStoriesLabelEnabledrelayprovider": True,
                }
            ),
            "doc_id": "29184890191114309",
            "fb_dtsg": "token",
            "fb_api_caller_class": "RelayModern",
            "fb_api_req_friendly_name": "PolarisStoriesV3ReelPageStandaloneQuery",
            "server_timestamps": "true",
        }
    )
```

- [ ] **Step 2: Convert the 50+1 and empty-input tests to XDT**

Add `import json`. Use this response factory in `test_story_batches_keep_every_response`:

```python
def reel(pk):
    owner = {
        "id": str(pk),
        "username": "example",
        "full_name": "Example",
        "profile_pic_url": "https://example.com/photo",
        "is_private": False,
    }
    story = {
        "pk": pk,
        "id": f"{pk}_{pk}",
        "code": f"story-{pk}",
        "taken_at": 1700000000,
        "media_type": 1,
        "user": owner,
        "image_versions2": {
            "candidates": [{"url": "https://example.com/story", "width": 720, "height": 1280}]
        },
    }
    return {"id": str(pk), "items": [story, story]}


def body(*reels):
    return {"data": {"xdt_api__v1__feed__reels_media": {"reels_media": list(reels)}}}
```

Set `self.client._fb_dtsg = "token"`, patch `graphql_request` with `side_effect=[body(reel(1)), body(reel(51))]`, and call `users_stories_gql(list(range(1, 52)), amount=1)`. Keep the existing assertions for users `1` and `51` and one story per user. Assert two calls, with `json.loads(call.kwargs["data"]["variables"])["reel_ids_arr"]` lengths of 50 and 1. In the empty-input test, patch `graphql_request` instead of `public_graphql_request` and assert no call and no session injection.

- [ ] **Step 3: Add empty-reel, malformed-response, and error-propagation tests**

Add this test to `tests/regression/test_story.py`:

```python
def test_users_stories_gql_validates_modern_response_and_preserves_errors(self):
    client = Client()
    client._fb_dtsg = "token"
    empty = {"data": {"xdt_api__v1__feed__reels_media": {"reels_media": [{"items": []}]}}}
    with mock.patch.object(client, "graphql_request", return_value=empty):
        self.assertEqual(client.users_stories_gql(["123"]), [])

    bodies = [
        {},
        {"data": {}},
        {"data": {"xdt_api__v1__feed__reels_media": None}},
        {"data": {"xdt_api__v1__feed__reels_media": {"reels_media": None}}},
        {"data": {"xdt_api__v1__feed__reels_media": {"reels_media": [{}]}}},
    ]
    for body in bodies:
        with self.subTest(body=body):
            with mock.patch.object(client, "graphql_request", return_value=body):
                with self.assertRaises(ClientGraphqlError):
                    client.users_stories_gql(["123"])

    error = ClientGraphqlError("request failed")
    with mock.patch.object(client, "graphql_request", side_effect=error):
        with self.assertRaises(ClientGraphqlError) as caught:
            client.users_stories_gql(["123"])
    self.assertIs(caught.exception, error)
```

- [ ] **Step 4: Run the focused tests and verify RED**

Run:

```bash
PYTHONPATH=/tmp/instagrapi-current-meta /Users/colinfrl/work/sub/instagrapi/.venv/bin/python -m pytest -q tests/regression/test_story.py tests/regression/test_legacy_routing.py
```

Expected: failures because the implementation still calls `public_graphql_request` and expects the legacy `reels_media` body.

### Task 2: Minimal modern batch implementation

**Files:**
- Modify: `instagrapi/mixins/story.py:115-158`
- Test: `tests/regression/test_story.py`
- Test: `tests/regression/test_legacy_routing.py`

- [ ] **Step 1: Replace only the body of `users_stories_gql`**

Keep the existing signature, list assertion, empty-input guard, and docstring. Use:

```python
users = []
for start in range(0, len(user_ids), 50):
    batch = [str(user_id) for user_id in user_ids[start : start + 50]]
    body = self.graphql_request(
        data={
            "variables": json.dumps(
                {
                    "reel_ids_arr": batch,
                    "__relay_internal__pv__PolarisCommunityNoteStoriesLabelEnabledrelayprovider": True,
                }
            ),
            "doc_id": "29184890191114309",
            "fb_dtsg": self.fb_dtsg,
            "fb_api_caller_class": "RelayModern",
            "fb_api_req_friendly_name": "PolarisStoriesV3ReelPageStandaloneQuery",
            "server_timestamps": "true",
        }
    )
    try:
        root = body["data"]["xdt_api__v1__feed__reels_media"]
    except (KeyError, TypeError) as exc:
        raise ClientGraphqlError("Malformed web stories response") from exc
    if not isinstance(root, dict) or not isinstance(root.get("reels_media"), list):
        raise ClientGraphqlError("Malformed web stories response")
    for reel in root["reels_media"]:
        if not isinstance(reel, dict) or not isinstance(reel.get("items"), list):
            raise ClientGraphqlError("Malformed web stories response")
        items = reel["items"][:amount] if amount else reel["items"]
        if not items:
            continue
        stories = [extract_story_web(item) for item in items]
        user = stories[0].user
        user.stories = stories
        users.append(user)
return users
```

Do not call `inject_sessionid_to_public` directly: `graphql_request` owns that behavior. Do not catch request or extractor exceptions.

- [ ] **Step 2: Run the focused tests and verify GREEN**

Run the Task 1 command. Expected: all tests in both files pass.

- [ ] **Step 3: Commit the tested implementation**

```bash
git add instagrapi/mixins/story.py tests/regression/test_story.py tests/regression/test_legacy_routing.py
git commit -m "fix: use modern GraphQL for batched user stories"
```

### Task 3: Documentation and complete offline verification

**Files:**
- Modify: `docs/usage-guide/story.md:3-7`

- [ ] **Step 1: Document the existing batch method**

Add this row directly below `user_stories_web`:

```markdown
| users_stories_gql(user_ids: List[int], amount: int = 0)              | List[UserShort] | Get users and their stories through the modern web GraphQL path in batches of up to 50 IDs
```

- [ ] **Step 2: Run the complete regression suite**

Run:

```bash
PYTHONPATH=/tmp/instagrapi-current-meta /Users/colinfrl/work/sub/instagrapi/.venv/bin/python -m pytest -q tests/regression
```

Expected: zero failures; preserve the baseline skip and subtest counts apart from the intentional test-count changes.

- [ ] **Step 3: Run quality and documentation gates**

Run:

```bash
/Users/colinfrl/work/sub/instagrapi/.venv/bin/python -m ruff check .
/Users/colinfrl/work/sub/instagrapi/.venv/bin/python -m ruff format --check .
/Users/colinfrl/work/sub/instagrapi/.venv/bin/python -m bandit -c pyproject.toml -r instagrapi
/Users/colinfrl/work/sub/instagrapi/.venv/bin/python -m mkdocs build --strict
pre-commit run --all-files
```

Expected: every command exits zero.

- [ ] **Step 4: Commit the documentation**

```bash
git add docs/usage-guide/story.md
git commit -m "docs: describe modern batched user stories"
```

### Task 4: Bounded live validation and publication gate

**Files:** No repository files.

- [ ] **Step 1: Verify account-selection constraints and candidate source**

Confirm the candidate commit and all runtime source hashes. Review the current held-pair registry before selecting any account; do not reuse the reserved pair from the earlier single-user story validation and do not perform password, factor, account-write, retry, or rotation operations.

- [ ] **Step 2: Exercise the exact candidate with one saved session**

Validate saved identity and one single-user `users_stories_gql` call, then one bounded 50+1 call. Record only HTTP status, request batch sizes, typed `UserShort`/`Story` shapes, owner matches, and counts. Require both batch responses to succeed before claiming multi-user support; stop on challenge, 400, 401, 403, 429, or malformed data.

- [ ] **Step 3: Publish only after evidence and owner verification**

Verify `gh api user --jq .login` is `subzeroid` immediately before every publication, inspect the final commit message for attribution trailers, and confirm the final live-tested commit. If the GitHub rate limit still prevents owner verification, leave the branch local and report the blocker rather than publishing through another identity. After paired instagrapi/aiograpi evidence exists, follow the normal review and release flow before any hiker-next port.
