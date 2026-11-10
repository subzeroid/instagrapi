# Private comment likers design

## Goal

Add a current private-mobile alternative for reading users who liked a comment while preserving the explicit public GraphQL API and its cursor contract.

## Evidence and scope

Android 449 constructs `GET media/%s/comment_likers/` for the comment-likers page and consumes the returned user items. A separate live check must confirm the response shape and that the path parameter is the comment PK before publication. The change does not claim a modern public GraphQL replacement, pagination, or deprecation of `comment_likers_gql*`.

## API

Add `comment_likers_v1(comment_pk: str, amount: int = 0) -> List[dict]`. It calls `private_request("media/{comment_pk}/comment_likers/")`, returns the raw user dictionaries from `users`, and slices the result when `amount` is positive. A zero amount returns the complete one-shot response. No cursor is invented because the observed first-party request has no pagination parameters.

Add unsuffixed `comment_likers(comment_pk: str, amount: int = 0) -> List[dict]` as the private-first convenience API and delegate directly to `comment_likers_v1`. Keep `comment_likers_gql` and `comment_likers_gql_chunk` byte-for-byte compatible. Apply the same contract to instagrapi and aiograpi with normal sync/async syntax.

## Errors and compatibility

Private transport, authentication, challenge, and malformed-response errors propagate normally. There is no retry, fallback, fabricated empty result, or new typed model. Existing GraphQL errors and pagination behavior remain untouched.

## Verification

Add regression tests for the exact private path, returned users, amount slicing, and unsuffixed delegation; prove they fail before implementation. Run focused and full offline suites, Ruff, formatting, Bandit, strict docs, builds, and the async type/lock gates. Validate the exact candidate against one new saved-session pair outside prior holds: verify identity, find a comment with likes, perform one candidate GET, and stop after its first outcome. Do not create paired PRs without that relevant live evidence.
