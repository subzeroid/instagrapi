# Instagrapi Fork with Security & Proxy Improvements

Custom fork of [subzeroid/instagrapi](https://github.com/subzeroid/instagrapi) with critical fixes for security, proxy support, and Pydantic validation.

## Quick Start

### For pyinstabot-downloader

Update your `pyproject.toml`:

```toml
[tool.poetry.dependencies]
# Use the fork with fixes
instagrapi = { git = "https://github.com/obervinov/instagrapi.git", branch = "fix/security-and-proxy" }
```

Then rebuild:
```bash
docker build -f Dockerfile.local -t pyinstabot-downloader:local .
```

---

## What's Fixed

### 🛡️ Security Improvements
- **Private API First:** All media queries use authenticated mobile endpoints instead of public GraphQL
- **Proxy Support:** All downloads (photos, videos, audio) now route through configured SOCKS proxy
- **User-Agent Consistency:** Eliminates Safari/Android mixing that triggers detection
- **No 401 Errors:** Removes suspicious web requests that cause "Please wait few minutes" blocks

### 🐛 Bug Fixes (Version 2.2.1)
- **Issue #2254:** `clips_metadata.original_sound_info` validation error fixed
- **Issue #2257:** `image_versions2.candidates.scans_profile` missing field error fixed
- **Issue #2257:** `pinned_channels_info` KeyError for private accounts fixed

### 📊 Proxy Routing
All these now use authenticated session with proxy:
- ✅ `video_download()`
- ✅ `photo_download()`  
- ✅ `album_download()`
- ✅ `track_download()`
- ✅ `direct_threads()`
- ✅ `hashtag_medias_top()`
- ✅ `user_medias_v1()`
- ✅ `collection_medias()`

---

## Branch Details

### `fix/security-and-proxy`

Two commits on top of upstream master:

1. **Pydantic validation fixes** (686a353)
   - Makes `scans_profile` optional
   - Adds defensive check for `pinned_channels_info`

2. **Security & Proxy implementation** (841e9d1)
   - Reverse API priority (private first)
   - Replace `requests.get()` with `self.private.get()`
   - Use private API in all download methods

---

## Files Modified

```
instagrapi/mixins/
  ├── media.py      (media_info() logic reversed)
  ├── video.py      (proxy routing + private API)
  ├── photo.py      (proxy routing + private API)
  ├── album.py      (private API enforcement)
  ├── track.py      (proxy routing)
  └── extractors.py (pinned_channels_info fix)

instagrapi/
  └── types.py      (scans_profile optional)
```

---

## Testing

```python
from instagrapi import Client

cl = Client(proxy="socks5://localhost:1080")
cl.login(username, password)

# These should all work without ValidationErrors
threads = cl.direct_threads()
medias = cl.hashtag_medias_top("test", 10)  
user_medias = cl.user_medias_v1(user_id, 10)

# Check proxy logs - all requests should appear there
# No www.instagram.com/graphql/query requests should be visible
```

---

## Compatibility

- **Upstream:** subzeroid/instagrapi master
- **Python:** 3.9+
- **Pydantic:** 2.10+
- **Requests:** 2.32+

---

## Usage with Custom Proxy

```python
from instagrapi import Client

# SOCKS5 proxy (recommended for Instagram)
client = Client(proxy="socks5://user:pass@proxy.example.com:1080")
client.login(username, password)

# Direct media download now routes through proxy
path = client.video_download(media_pk="...")
```

---

## Related Documentation

- [INSTAGRAPI_FIXES.md](./INSTAGRAPI_FIXES.md) - Detailed changes and patches
- [INSTAGRAPI_PYDANTIC_ISSUES.md](./INSTAGRAPI_PYDANTIC_ISSUES.md) - Issue analysis
- [INSTAGRAPI_FORK_SUMMARY.md](./INSTAGRAPI_FORK_SUMMARY.md) - Branch summary

---

## Original Upstream

- **Repository:** https://github.com/subzeroid/instagrapi
- **License:** MIT

---

## Contributing

To use improvements from upstream, rebase on master:

```bash
git fetch origin master
git rebase origin/master fix/security-and-proxy
```

## Support

For issues related to these fixes, see:
- [obervinov/pyinstabot-downloader#144](https://github.com/obervinov/pyinstabot-downloader/pull/144)
- [subzeroid/instagrapi#2254](https://github.com/subzeroid/instagrapi/issues/2254)
- [subzeroid/instagrapi#2257](https://github.com/subzeroid/instagrapi/issues/2257)

