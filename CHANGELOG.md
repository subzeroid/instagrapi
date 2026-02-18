# Change Log
All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](http://keepachangelog.com/) and this project adheres to [Semantic Versioning](http://semver.org/).

## v2.2.2 - 2026-02-18
### What's Changed
**CDN Download Fix**: Direct CDN requests with proxy support for media downloads
#### 🐛 Bug Fixes
* **Fixed 404 errors on media downloads through proxy**: CDN URLs now use direct requests but still route through proxy

## v2.2.1 - 2026-02-18
### What's Changed
**Security & Proxy Improvements**: Comprehensive security hardening and proxy routing for all media operations
#### 🛡️ Security
* **Reversed media_info() priority**: Private API first, public GraphQL fallback only
  - Eliminates default use of unauthenticated public endpoints
  - Prevents triggering Instagram detection systems
  - Fixes issue #2162 (401 "Please wait a few minutes before you try again" errors)
* **All downloads through proxy**: Authenticated session routing for video, photo, album, and track operations
  - Changed from `requests.get()` to `self.private.get()` for proxy consistency
* **Consistent User-Agent handling**: All requests use mobile app User-Agent
  - Prevents Safari web User-Agent triggering detection

#### 🐛 Bug Fixes
* **Fixed Pydantic ValidationError #2254**: Added defensive checks for pinned_channels_info in extract_broadcast_channel()
  - Private accounts don't always include this field
  - Now gracefully returns empty list instead of KeyError
* **Fixed Pydantic ValidationError #2257**: Made scans_profile optional in SharedMediaImageCandidate model
  - Instagram API sometimes omits this field in image_versions2 candidates
  - Changed from required to Optional[str] with default None

#### 💥 Breaking Changes
* None - fully backward compatible. Proxy configuration and authentication remain the same, just more secure by default.

## v2.2.0 - 2026-02-10
* Initial release of fork (upstream: subzeroid/instagrapi)
