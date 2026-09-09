# Changelog

Earlier release notes are available in [GitHub Releases](https://github.com/subzeroid/instagrapi/releases).

## 2.18.19 — 2026-09-09

- Add optional private HTTP/2 transport through `Client(private_transport="curl")` and the `curl` extra. TLS offers only `h2`; private requests retain mobile headers, proxy configuration, cookies and saved device settings. The default transport and login routing remain unchanged. See the [private transport guide](https://github.com/subzeroid/instagrapi/blob/master/docs/usage-guide/interactions.md#private-http2-transport).
- Add a [login diagnostic script](https://github.com/subzeroid/instagrapi/blob/master/examples/diagnose_login.py) that preserves a sanitized summary of each login response, including failures hidden by a later fallback.
- Add real TLS/HTTP2 regression tests and guarded CAA live validation, with minimum/current curl dependency checks on Python 3.10 and 3.14.
- Update Ruff and CodeQL tooling.

The transport change addresses a verified transport-sensitive CAA failure mode. It does not remove account restrictions or guarantee successful login. Follow [issue #2778](https://github.com/subzeroid/instagrapi/issues/2778) for the remaining investigation.
