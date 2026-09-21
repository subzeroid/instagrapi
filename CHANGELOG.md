# Changelog

Earlier release notes are available in [GitHub Releases](https://github.com/subzeroid/instagrapi/releases).

## 3.0.12 — 2026-09-21

- Restore optional `public_transport="curl"` response-body reads with urllib3 2.8 by requiring `curl-adapter>=1.2.3`. This also fixes password-encryption key fetching through that transport (#2827; thanks to @marnelle1 for the report).
- Add regression coverage and CI checks for buffered and streamed public curl responses with plain, gzip and deflate bodies.

## 3.0.11 — 2026-09-21

- Reuse an available saved private session before the first `user_related_profiles_gql()` request, so related-profile lookup no longer depends on an earlier public lookup having copied the session (#2824).
- Restore authenticated `user_short_gql()` and `user_info_v2_gql()` lookups with the current shared web profile query and complete Relay variables. Remove the short-profile friendly-name override that caused HTML responses in verified requests (#2825).

## 3.0.10 — 2026-09-21

- Preserve CAA fallback errors, including throttling and rate limits, instead of masking them with the earlier legacy `needs_upgrade` or `BadPassword`. Keep the original legacy error when the CAA endpoint is unavailable or returns no session.
- Parse media responses with `crosspost: null` or `coauthor_producers: null` as empty lists, avoiding validation and extraction errors while preserving valid values and rejecting malformed values (#2821, #2822).

### For contributors

- Fail manually dispatched live test jobs when test account configuration is missing, so an unconfigured run cannot appear to validate live behavior (#2820).

## 3.0.9 — 2026-09-20

- Separate HTTP timeouts from the `request_timeout` pacing delay in download, share-link, public HEAD, and legacy DTSG helpers. Their `read_timeout` defaults to 25 seconds and can be changed independently of request pacing (#2817, thanks to @marnelle1 for the report).
- Clarify the existing CAA-to-legacy transition in the login guides: it follows an explicit fallback instruction from Instagram.

## 3.0.8 — 2026-09-20

- Keep user, media, story, follower, and following caches separate for each `Client`, so one client cannot reuse or clear another client's cached data (#2813).
- Make `user_highlights()` and `user_highlights_v1()` respect positive `amount` limits before parsing the returned tray. `amount=0` continues to return all Highlights (#2814).

## 3.0.7 — 2026-09-19

- The default app profile is now the current Android app: `448.0.0.0.20` (version_code `1065560286`, captured bloks_versioning_id). New clients present the current app version by default, avoiding the server-side "Your version of Instagram is out of date" login gate reported in #2807. Saved 446 sessions keep resolving; the 446 profile remains explicitly selectable via `set_app("446.0.0.49.77")` (#2812).

## 3.0.6 — 2026-09-19

- Align the Reels configure payload (`clip_configure`) with the current Android app: send `clips_segments_metadata`, `clips_audio_metadata`, `additional_audio_info`, nested `edits`, and the current capture metadata fields; drop `media_folder` and `date_time_original` the app no longer sends (#2808).
- Story captions now use the current app rich text format: `rich_text_format_types: ["modern_refreshed_v2"]` and matching `text_metadata` fields (#2809).
- New helpers: `media_upload_status(post_client_id)` polls `media/get_upload_status_REST/` for asynchronous clip/story publishing until `COMPLETED`, and `video_refresh_resources(media_id)` returns a fresh `video_versions` list when previously returned video URLs have expired (#2810).

## 3.0.5 — 2026-09-18

- Refresh the private GraphQL `FollowersList`/`FollowingList` doc ids to the ones the current Android app sends (`284797047911918316998205836755`, `16104639286363954576550227636`); the previous ids still resolve but are one generation behind (#2798).

## 3.0.4 — 2026-09-17

- `get_settings()` now returns `fbns_auth` from the live FBNS auth object when present (falling back to previously saved values), so `dump_settings()`/`load_settings()` preserve the FBNS device auth across a settings round trip. Mirror of the aiograpi 2.0.4 fix.

## 3.0.3 — 2026-09-17

- `login()` now follows Instagram's CAA fallback instruction (`CAA_LOGIN_FALLBACK:fallback_triggered`) and completes the legacy accounts flow, so typed failure reasons such as `PleaseWaitFewMinutes` or `BadPassword` surface instead of the generic "CAA login did not return a session" error (#2800).
- `ClientError` raised by CAA login now carries the observed CAA step markers as `caa_actions` (for example `CAA_LOGIN_FORM:account_list`) for diagnostics.

## 3.0.2 — 2026-09-13

- Reels feed readers now accept media from current `items_with_ads` responses when legacy `items` is empty or absent, avoiding empty results and unnecessary pagination. Existing feed ordering and cursor behavior are preserved.
- Reels readers now stop as soon as the requested amount is collected, including on the final page or before a later stop marker.
- Reels pagination now stops when the next cursor is missing or already visited, preserving collected media without repeating the same requests.
- Reels readers now honor last_media_pk when the server returns media IDs as strings, stopping before the matching media.

## 3.0.1 — 2026-09-13

- Return configured photos, videos, albums, Reels, IGTV and Stories without a follow-up `qe/expose/` request, preventing an exposure endpoint error from hiding a successful upload (#2790).

## 3.0.0 — 2026-09-13

- **Breaking:** Make `login()` use CAA directly; retain the previous login flow and arguments as `login_legacy()`. Default login does not automatically fall back to legacy login.
- Reject CAA login with a clear error before preflight when saved app settings lack the required Bloks hash; document explicit app-profile migration.
- **Breaking:** Use `curl_cffi` and private HTTP/2 by default and install `curl_cffi` as a runtime dependency. Preserve explicit saved transport choices and the `private_transport="requests"` compatibility option.

- Update the default Android app profile to Instagram `446.0.0.49.77` while retaining the previous `428.0.0.47.67` profile for saved settings and explicit selection.
- Try the existing CAA login flow when `login_legacy()` returns `needs_upgrade`, preserving the original error if no session or supported two-factor flow is available.

## 2.18.20 — 2026-09-12

- Advertise the hybrid `X25519MLKEM768` TLS group in the optional private curl transport to address connection failures on proxy paths that reject a classical-only ClientHello. Preserve classical groups and h2-only ALPN; this changes TLS reachability, not authentication handling.

## 2.18.19 — 2026-09-09

- Add optional private HTTP/2 transport through `Client(private_transport="curl")` and the `curl` extra. TLS offers only `h2`; private requests retain mobile headers, proxy configuration, cookies and saved device settings. The default transport and login routing remain unchanged. See the [private transport guide](https://github.com/subzeroid/instagrapi/blob/master/docs/usage-guide/interactions.md#private-http2-transport).
- Add a [login diagnostic script](https://github.com/subzeroid/instagrapi/blob/master/examples/diagnose_login.py) that preserves a sanitized summary of each login response, including failures hidden by a later fallback.
- Add real TLS/HTTP2 regression tests and guarded CAA live validation, with minimum/current curl dependency checks on Python 3.10 and 3.14.
- Update Ruff and CodeQL tooling.

The transport change addresses a verified transport-sensitive CAA failure mode. It does not remove account restrictions or guarantee successful login. Follow [issue #2778](https://github.com/subzeroid/instagrapi/issues/2778) for the remaining investigation.
