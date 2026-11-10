# Private Comment Likers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a private-mobile comment-likers API without changing the explicit public GraphQL helpers.

**Architecture:** `comment_likers_v1` performs the observed one-shot private request and returns raw user dictionaries. Unsuffixed `comment_likers` delegates to it; GraphQL methods and their cursors remain unchanged.

**Tech Stack:** Python, instagrapi mixins, unittest/mock, pytest.

---

### Task 1: Private API regressions

**Files:**
- Modify: `tests/regression/test_comments.py`
- Modify: `instagrapi/mixins/comment.py`

- [ ] **Step 1: Add failing tests**

Add a `CommentLikersRegressionTestCase(unittest.TestCase)` with:

```python
def test_v1_fetches_private_comment_likers(self):
    client = Client()
    users = [{"pk": "1", "username": "alice"}]
    with mock.patch.object(client, "private_request", return_value={"users": users, "status": "ok"}) as request:
        result = client.comment_likers_v1("100")
    self.assertEqual(result, users)
    request.assert_called_once_with("media/100/comment_likers/")

def test_v1_applies_amount_to_one_shot_users(self):
    client = Client()
    users = [{"pk": "1", "username": "alice"}, {"pk": "2", "username": "bob"}]
    with mock.patch.object(client, "private_request", return_value={"users": users, "status": "ok"}):
        result = client.comment_likers_v1("100", amount=1)
    self.assertEqual(result, users[:1])

def test_unsuffixed_helper_delegates_to_v1(self):
    client = Client()
    with mock.patch.object(client, "comment_likers_v1", return_value=[{"pk": "1"}]) as v1:
        result = client.comment_likers("100", amount=1)
    self.assertEqual(result, [{"pk": "1"}])
    v1.assert_called_once_with("100", 1)
```

- [ ] **Step 2: Verify RED**

Run: `/Users/colinfrl/work/sub/instagrapi/.venv/bin/python -m pytest -q tests/regression/test_comments.py -k comment_likers`

Expected: the new tests fail because `comment_likers_v1` and `comment_likers` do not exist; the existing GraphQL test remains green.

- [ ] **Step 3: Implement minimal methods**

Add before `comment_likers_gql_chunk` in `instagrapi/mixins/comment.py`:

```python
def comment_likers_v1(self, comment_pk: str, amount: int = 0) -> List[dict]:
    """Get users who liked a comment through the private mobile API."""
    result = self.private_request(f"media/{comment_pk}/comment_likers/")
    users = result.get("users") or []
    return users[:amount] if amount else users


def comment_likers(self, comment_pk: str, amount: int = 0) -> List[dict]:
    """Get users who liked a comment through the private mobile API."""
    return self.comment_likers_v1(comment_pk, amount)
```

- [ ] **Step 4: Verify GREEN**

Run: `/Users/colinfrl/work/sub/instagrapi/.venv/bin/python -m pytest -q tests/regression/test_comments.py`

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add instagrapi/mixins/comment.py tests/regression/test_comments.py
git commit -m "feat: add private comment likers"
```

### Task 2: Documentation and offline gates

**Files:**
- Modify: `docs/usage-guide/comment.md`

- [ ] **Step 1: Document the additive contract**

Add `comment_likers` and `comment_likers_v1` to the method table. State that both return the one-shot private `users` list, positive `amount` truncates it, and no private cursor is exposed; retain both GraphQL rows.

- [ ] **Step 2: Run quality checks**

Run focused tests, full `tests/regression`, Ruff lint/format, Bandit, strict MkDocs, build/Twine, and `git diff --check`. Confirm no external calls in the offline suite.

- [ ] **Step 3: Commit**

```bash
git add docs/usage-guide/comment.md
git commit -m "docs: describe private comment likers"
```

### Task 3: Bounded live validation and publication gate

**Files:**
- Use private evidence outside the repository: `/Users/colinfrl/.codex/backups/instagrapi/comment-likers-20261111/`

- [ ] **Step 1: Validate the endpoint and exact candidate**

Use one new saved-session pair outside all holds. Verify neutral HTTPS and account identity, fetch comments for the existing public fixture, select one with `like_count > 0`, then make exactly one `media/{comment_pk}/comment_likers/` request. Stop after its first outcome; require HTTP success, `status == "ok"`, and nonempty raw `users` with PK/username fields. Do not rotate accounts or submit passwords/factors/writes.

- [ ] **Step 2: Record limits and decide publication**

Save only sanitized counts, status, selected hashes, and source SHA locally. Keep raw account/session/response material remote and reserve the pair. Create the paired instagrapi/aiograpi PRs only after the same relevant live contract passes in both libraries; otherwise retain the branches unpublicized and report the blocker.
