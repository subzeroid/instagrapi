# Modern batched user stories design

## Context

`users_stories_gql` still uses legacy `query_hash=303a4ae99711322310f25250d988f3b7`. A bounded live probe of the current implementation returned HTTP 400 with a small JSON `status="fail"` body for one user, before any batch merging occurred. The previous implementation used the same request, so this is not a regression from the batch-accumulation fix.

The current `user_stories_web` already uses `PolarisStoriesV3ReelPageStandaloneQuery`, `doc_id=29184890191114309`, `reel_ids_arr`, and the XDT `data.xdt_api__v1__feed__reels_media.reels_media` response. Its contract has captured-response evidence and successful live parsing of photo and video stories. `extract_story_web` already normalizes nullable collections and dimensionless video candidates.

## Approaches

1. Replace the internals of `users_stories_gql` with the proven modern web contract while preserving its public signature and result type. This fixes existing callers and is the selected approach.
2. Add another parallel batch helper and leave `users_stories_gql` unchanged. This avoids changing an existing method but leaves the broken public API in place and duplicates an already modern helper.
3. Move the batch method to private mobile `feed/reels_media/`. This changes the public/private semantics and requires a separate mobile contract validation, so it is out of scope.

## API and request behavior

Keep `users_stories_gql(user_ids, amount=0)` and `List[UserShort]`. An empty input returns `[]` without session injection or network activity. Convert every user ID to a string and preserve batches of at most 50 IDs.

Each batch sends one `graphql_request` with `doc_id=29184890191114309`, friendly name `PolarisStoriesV3ReelPageStandaloneQuery`, `reel_ids_arr`, the existing community-note Relay variable, `fb_dtsg`, `fb_api_caller_class=RelayModern`, and `server_timestamps=true`. There is no retry or fallback to the rejected legacy query.

Apply `amount` independently to each reel's items, preserving response order. Extract stories with `extract_story_web`. Build each `UserShort` from the first typed story owner and attach that reel's typed stories. Skip reels with no selected items because they contain no owner from which to construct an honest `UserShort`; do not invent a user object or emit empty-story users.

Leave `user_stories_web`, `user_stories_v1`, the default `user_stories` routing, method signatures, and package versions unchanged.

## Validation and errors

Propagate transport and GraphQL exceptions unchanged. A missing or non-object XDT root, a non-list `reels_media`, or a reel with a non-list `items` value raises `ClientGraphqlError` rather than returning partial success. Extraction errors remain visible.

Regression tests must fail against the legacy implementation and then verify the exact modern form, 50+1 batching, result accumulation across both responses, per-user amount limiting, typed photo and video stories, empty input without dispatch, skipped empty reels, malformed responses, and original exception propagation.

Run each repository's complete regression suite and standard quality checks. Perform a relevant saved-session live test for each candidate without password, factor, account writes, retries, or account rotation. Validate one modern single-user call and a bounded 50+1 call, recording only HTTP outcomes, batch sizes, typed shapes, and counts. Do not claim that offline fixtures prove multi-user server behavior.

After both libraries have successful live evidence, prepare their normal review and release flow. Port the proven contract to hiker-next only afterward, validate it separately on hapi4, and do not use this task to change hapi routes.

## Final live findings

A 50-ID request returned HTTP 200 with `data:null` and a GraphQL `field_exception`, while 10-ID and 25-ID requests returned usable data. The final implementation therefore uses batches of at most 25 IDs; a 51-ID acceptance call is split as 25+25+1. Live web responses also showed `story_feed_media` entries with `id` and `media_code` instead of private `media_id`; `extract_story_web` now decodes `media_code` or falls back to the numeric prefix of `id`, preserving an existing `media_id`.

Both candidates passed saved-session identity, single-user, and 51-ID live checks with HTTP 200 for every GraphQL request. Each batch returned typed `UserShort` and photo/video `Story` objects with owners in the requested ID set. Runtime manifests matched all 73 instagrapi and 74 aiograpi files.

## Assumptions

The already approved direction is to repair the existing batch API rather than add a second public batch API. The existing modern single-user helper is the reference implementation; multi-user acceptance still requires live validation. No current web `owner` object is assumed: typed story owner data is the source for the returned `UserShort`.
