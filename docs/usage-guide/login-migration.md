# CAA login migration

Version 3.0.0 changes the default login flow and private transport. This guide explains how to migrate existing applications and saved settings.

## Default usage

Install the package normally; `curl_cffi` is a required dependency:

```bash
pip install instagrapi
```

The application code stays simple:

```python
from instagrapi import Client

cl = Client()
cl.login(USERNAME, PASSWORD)
```

`login()` uses CAA directly. It does not try `accounts/login/` first and does not automatically fall back to that endpoint after a CAA failure. All private mobile API requests use curl with HTTP/2 by default. Public web and GraphQL transports retain their separate configuration.

## Keep the previous login flow

The previous method is now named `login_legacy()`. Its arguments and existing fallback behavior are preserved:

```python
cl = Client()
cl.login_legacy(USERNAME, PASSWORD, verification_code="123456")
```

Login flow and transport are independent choices. To explicitly use the previous Requests private transport as well:

```python
cl = Client(private_transport="requests")
cl.login_legacy(USERNAME, PASSWORD)
```

An explicit legacy login may still invoke its existing CAA fallback. There is no automatic fallback in the opposite direction. `relogin()` uses the new default CAA flow; use `login_legacy(relogin=True)` to explicitly repeat the previous flow.

## Reuse saved sessions

Both entry points validate an existing session before using the supplied credentials. If Instagram rejects that session with `LoginRequired`, each repeats its own login flow after clearing the expired authorization state.

```python
cl = Client()
cl.load_settings("session.json")
cl.login(USERNAME, PASSWORD)
cl.dump_settings("session.json")
```

Settings with an explicit `private_transport` keep that choice, even when it differs from the constructor. Settings without that field keep the selected constructor transport, which now defaults to `curl`.

To migrate settings that explicitly saved `requests`:

```python
cl.load_settings("session.json")
cl.set_retry_config(private_transport="curl")
cl.login(USERNAME, PASSWORD)
cl.dump_settings("session.json")
```

This transport change does not replace the saved device profile, proxy, cookies or authorization data. Keep the account's existing proxy configuration when restoring its session.

## Older app profiles without a Bloks hash

CAA needs a Bloks hash matching the configured app version. Saved settings for an older unsupported version may lack this hash. If the session cannot be reused, `login()` raises `ClientError` before starting CAA requests and explains how to update the profile.

Use the supported profile explicitly when migrating those settings:

```python
cl = Client()
cl.load_settings("session.json", override_app_version=True)
cl.set_retry_config(private_transport="curl")  # migrate an explicit saved requests choice
cl.login(USERNAME, PASSWORD)
cl.dump_settings("session.json")
```

`override_app_version=True` updates the app version, version code and Bloks hash. It retains hardware settings and device identifiers. Keep using the account's existing proxy. Alternatively, provide the correct Bloks hash for the original profile or explicitly use `login_legacy()`.

## Verification and failures

Continue to pass `verification_code` for supported two-factor challenges. The CAA profile-code flow also supports `challenge_code_handler`; see [TOTP](totp.md). Native CAA exceptions propagate. A response without a session or a supported verification context raises `ClientError` with the CAA failure reason. Curl does not automatically retry a failed password POST.

## Installation requirements

Private HTTP/2 requires `curl_cffi>=0.15.0` and libcurl 8.10 or newer. `curl_cffi` normally supplies libcurl in its wheels; a system `curl` executable and the Python `h2` package are not required for this transport. A compatible wheel or a supported native build is required for your platform. Android/Termux has not been verified.

The optional `instagrapi[curl]` extra remains available for public web browser impersonation through `curl-adapter`. It is not required for private HTTP/2. See [private HTTP/2 transport](interactions.md#private-http2-transport) for TLS, proxy and timeout behavior.
