# Modern Batched User Stories Implementation Plan

**Goal:** Replace the rejected legacy batch-story query with the proven modern XDT query while preserving the `users_stories_gql` API.

**Architecture:** Send batches of at most 25 IDs through `graphql_request`, validate the XDT envelope, and convert each nonempty reel into one `UserShort` using `extract_story_web`. Do not add a public method, a legacy fallback, or changes to private story routing.

**Tech Stack:** Python 3.11+, Pydantic models, unittest/mock, pytest, Ruff, MkDocs.

### Task 1: Modern request and batch regressions

- [x] Replace legacy request expectations with `PolarisStoriesV3ReelPageStandaloneQuery`, `doc_id=29184890191114309`, `reel_ids_arr`, and the XDT response path.
- [x] Verify 25+25+1 batching for 51 IDs, empty input without dispatch, per-reel amount limits, empty-reel skipping, malformed responses, and original exception propagation.
- [x] Add failing-first coverage for `story_feed_media` identifiers and independent story owners.

### Task 2: Minimal modern batch implementation

- [x] Preserve the existing signature and return `List[UserShort]`.
- [x] Validate `data.xdt_api__v1__feed__reels_media.reels_media` and raise `ClientGraphqlError` for malformed data.
- [x] Extract each reel's selected stories and attach them to a deep copy of the first story owner, avoiding a cyclic `user.stories[0].user` graph.
- [x] Preserve an existing `media_id`; otherwise decode `media_code` or use the numeric prefix of `id`.

### Task 3: Documentation and offline verification

- [x] Document `users_stories_gql` in the story guide with the 25-ID batch limit.
- [x] Run `python -m pytest -q tests/regression`: 1440 passed, 7 skipped, 250 subtests.
- [x] Run focused story/routing tests: 38 passed, 73 subtests.
- [x] Pass Ruff, Bandit, strict MkDocs, and pre-commit.

### Task 4: Bounded live validation and publication gate

- [x] Verify the exact runtime candidate and all 73 runtime source files.
- [x] On runtime commit `f9b012f8`, validate saved identity, one single-user call, and one 51-ID call. Every request returned HTTP 200 with batch sizes 1,25,25,1; typed photo/video stories, requested owners, and independent owner objects were verified.
- [x] Perform no password, factor, account-write, retry, or rotation operations.
- [x] Publish as `subzeroid` after owner verification. The paired aiograpi live runtime commit is `247da16c`; later commits on both branches change documentation only.
