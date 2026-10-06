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

`login()` uses CAA directly. Since instagrapi 3.0.3, an explicit `CAA_LOGIN_FALLBACK` instruction from Instagram continues through `login_legacy()`, allowing the accounts endpoint to complete login or surface its typed error. Other CAA failures retain their normal error handling. All private mobile API requests use curl with HTTP/2 by default. Public web and GraphQL transports retain their separate configuration.

## Keep the previous login flow

The previous method is now named `login_legacy()`. It keeps the same arguments and can fall back to CAA:

```python
cl = Client()
cl.login_legacy(USERNAME, PASSWORD, verification_code="123456")
```

Login flow and transport are independent choices. To explicitly use the previous Requests private transport as well:

```python
cl = Client(private_transport="requests")
cl.login_legacy(USERNAME, PASSWORD)
```

An explicit legacy login may invoke its CAA fallback, including when the accounts endpoint returns `needs_upgrade`. The default CAA flow enters legacy login only when Instagram explicitly requests it. `relogin()` uses the new default CAA flow; use `login_legacy(relogin=True)` to explicitly repeat the previous flow.

If that CAA fallback raises a throttling, rate-limit, feedback, or other login error, its exception propagates instead of being replaced by the earlier legacy `needs_upgrade` or `BadPassword`. The original legacy error is retained when CAA returns no session or its endpoint is unavailable (HTTP 404, or a `field_exception` reporting a null payload). An outdated-app error alone therefore does not identify the cause of every failed login; inspect the actual failure before retrying.

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

Continue to pass `verification_code` for supported two-factor challenges. The CAA profile-code flow also supports `challenge_code_handler`; see [TOTP](totp.md). Native CAA exceptions propagate. If CAA returns neither a usable session, a supported verification context, nor an explicit fallback instruction, `login()` raises `ClientError` with the CAA failure reason. Curl does not automatically retry a failed password POST.

## Shareable login diagnostics

Download [examples/diagnose_login.py](https://github.com/subzeroid/instagrapi/blob/master/examples/diagnose_login.py) and run it in the same Python environment as the failing application, with its existing private settings and proxy:

```bash
python diagnose_login.py --settings session.json --report login-diagnostic.json --proxy
```

The script prompts privately for the proxy and password. Credentials can also come from `IG_USERNAME`, `IG_PASSWORD` and `IG_PROXY`. Add `--two-factor` to supply a current verification code, or `--relogin` to explicitly request password login even when settings contain an authorized session. Running the script performs a real login attempt; the library can make several requests or enter its existing fallback flow. The script disables transport retries for this run, bounds request timeouts, stops automatic checkpoint handling, and saves updated settings after failure or interruption. Share only the report after reviewing it; settings contain private session credentials.

Each `responses` entry records the received HTTP status and a closed endpoint label. Labels distinguish USDID registration, CAA client-data preparation, Android keystore attestation, OAuth preparation and credential submission; `two_step/` labels identify entrypoint, method picker, method selection, TOTP or backup-code entry, code verification and the allowed-status step. `profile_code/` labels identify the separate AP entrypoint, code-entry and submission flow. A stage appears only if the installed library actually requested it. Unrecognized endpoints use the existing broad categories such as `bloks`, `challenge`, `attestation` or `usdid`. USDID registration is identified by the exact `IGUSDIDRegistrationMutation` request header, without inspecting or exporting its request body.

Bloks response entries also contain a fixed `bloks` summary. `referenced_apps` contains only known app names; `continuation_reference_present` records a known verification-app reference. `fallback_reference_present` records `CAA_LOGIN_FALLBACK`, `login_success_reference_present` records the exact `login_success` or `two_fac_redirect` reference, and `error_reference_present` records a known error category or `CAA_LOGIN_OCL_ERROR` reference. These references can occur in unexecuted branches: none proves that Instagram executed the instruction, accepted a code or completed login. HTTP 200 alone does not establish success.

`two_step_context_parsed` and `profile_code_context_parsed` indicate that the installed pure parsers recognized nonempty context in this response; the latter examines only referenced, known AP profile-code apps. A false value does not prove that no context exists in an unsupported Bloks grammar. Context recognition does not establish that the next step executed or succeeded, and context values are withheld.

`login_response_reference_present` distinguishes a payload reference from `login_response_decoded`, which means the installed pure Bloks parser actually decoded an embedded payload. `logged_in_user_present`, `authorization_present` and `sessionid_cookie_present` record nonempty material from that decoded response only. They do not inspect the client's old cookies, apply the payload, expose its values or verify the resulting identity. `inspection_error` marks unavailable or failing optional inspection; the observer preserves the original response and login outcome. Existing `caa_attempts` retain each CAA result and its response-index range before fallback replaces the last response.

Response metadata includes only `server_category` (`proxygen-bolt`, `other` or absent), `proxy_error_category` (`http_request_error`, `other` or absent) and `retry_after_present`. The proxy category comes from the exact reported token or a separate `error=` parameter, without copying proxy details. These fields do not explain the cause of a 429. The client profile records only a catalogued app version, Bloks-hash presence and `private_transport` (`curl`, `requests`, `other` or absent); raw URLs, headers, response bodies, credentials, contexts and cookies are withheld.

Downloading the latest diagnostic script does not upgrade the installed package or change its login flow. Use it with a package exposing the existing CAA helpers; older installed parsers may provide less structural information or set `inspection_error`. Keep the package version in the report when comparing results.

## Installation requirements

Private HTTP/2 requires `curl_cffi>=0.15.0` and libcurl 8.10 or newer. `curl_cffi` normally supplies libcurl in its wheels; a system `curl` executable and the Python `h2` package are not required for this transport. A compatible wheel or a supported native build is required for your platform. Android/Termux has not been verified.

The optional `instagrapi[curl]` extra remains available for public web browser impersonation through `curl-adapter`. It is not required for private HTTP/2. See [private HTTP/2 transport](interactions.md#private-http2-transport) for TLS, proxy and timeout behavior.
