# Changelog

Earlier release notes are available in [GitHub Releases](https://github.com/subzeroid/instagrapi/releases).

## Unreleased

- Reels pagination now stops when the next cursor is missing or already visited, preserving collected media without repeating the same requests.

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
