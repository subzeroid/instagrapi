# HTTPCloak Integration

With this change instagrapi now uses [HTTPCloak](https://github.com/sardanioss/httpcloak) to bypass Instagram's TLS fingerprinting bot detection.

## Overview

Instagram uses sophisticated bot detection including:

- **JA3/JA4 TLS Fingerprinting** - Identifies the TLS client by its handshake patterns
- **HTTP/2 Frame Analysis** - Detects non-browser request patterns
- **QUIC Parameter Matching** - Identifies transport layer anomalies

Python's standard `requests` library has a distinct TLS fingerprint that Instagram can easily detect and block. HTTPCloak solves this by mimicking real browser fingerprints.

## How It Works

HTTPCloak uses browser presets that match:
- TLS extensions, cipher suites, and curves exactly
- HTTP/2 frame prioritization patterns
- QUIC connection parameters

The integration is transparent - no code changes required in your existing instagrapi code.

## Preset Selection

**Important:** Instagram blocks certain TLS fingerprints. We've tested which presets work:

### Working Presets

| Preset | Status | Use Case |
|--------|--------|----------|
| `ios-chrome-143` | Works | Private API (default for mobile requests) |
| `ios-safari-17` | Works | Alternative mobile preset |
| `safari-18` | Works | Public API (default for web requests) |

### Blocked Presets

| Preset | Status | Reason |
|--------|--------|--------|
| `android-chrome-143` | Blocked | Instagram detects and blocks |
| `chrome-143` | Blocked | Desktop Chrome fingerprint detected |
| `firefox-133` | Blocked | Firefox fingerprint detected |

## Usage

### Basic Usage (No Changes Required)

```python
from instagrapi import Client

cl = Client()
cl.login(username, password)  # Uses HTTPCloak automatically

# All API calls work as before
user = cl.user_info_by_username("instagram")
```

### Session Persistence

Sessions are automatically saved and restored with full HTTPCloak state:

```python
# Save session
cl.dump_settings("session.json")

# Restore session (includes TLS session state)
cl = Client()
cl.load_settings("session.json")
cl.login(username, password)
```

### Proxy Support

Proxies work seamlessly:

```python
cl = Client()
cl.set_proxy("http://user:pass@proxy:port")
cl.login(username, password)
```

## Migration from v2.x

### For End Users

**No code changes required.** The public API remains identical.

### For Advanced Users

If you directly access `client.private` or `client.public` sessions:

#### Cookie Access

```python
# v2.x (requests)
cookies = client.private.cookies.get_dict()

# v3.x (HTTPCloak)
cookies = client.private.cookies  # Already a dict
```

#### Setting Cookies

```python
# v2.x (requests)
client.private.cookies.set("name", "value")

# v3.x (HTTPCloak)
client.private.set_cookie("name", "value")
```

#### Clearing Cookies

```python
# v2.x (requests)
client.private.cookies.clear()

# v3.x (HTTPCloak)
client.private.clear_cookies()
```

#### Proxy Access

```python
# v2.x (requests)
proxy = client.private.proxies.get("https")

# v3.x (HTTPCloak)
proxy = client.private.get_proxy()
```

## Troubleshooting

### "No valid ID given" Error

This error means Instagram detected and blocked the TLS fingerprint. This typically happens with non-iOS presets. The default configuration uses working presets, so you should not see this error unless you've customized the presets.

### Old Session Files

Session files from v2.x will partially work - cookies will be restored but full TLS session state won't be available. The first request will establish a new TLS session. For best results, create a fresh session after upgrading.

### Type Checking Warnings

Some type checkers may show warnings since HTTPCloak doesn't have complete type stubs. These are cosmetic and don't affect runtime behavior.

## Technical Details

### Presets Used Internally

- **Private API (mobile):** `ios-chrome-143`
- **Public API (web):** `safari-18`

### Session State

HTTPCloak sessions preserve:
- Cookies
- Headers
- TLS session tickets
- HTTP/2 connection state

This is saved using `session.marshal()` and restored with `session.unmarshal()`.

## See Also

- [HTTPCloak GitHub](https://github.com/sardanioss/httpcloak)
- [JA3 Fingerprinting](https://github.com/salesforce/ja3) - How TLS fingerprinting works
