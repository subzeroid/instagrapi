# Public Transport

`instagrapi` uses two network surfaces:

* private mobile API requests, used for authenticated mobile flows;
* public web requests, used by helpers such as public profile and public media lookups.

The default public web transport is `requests`. It has the smallest dependency footprint and keeps the existing
transport-level retry behavior.

For public web endpoints that are sensitive to browser TLS fingerprints, you can install the optional curl transport:

```bash
pip install "instagrapi[curl]"
```

Then opt in explicitly:

```python
from instagrapi import Client

cl = Client(public_transport="curl", public_transport_impersonate="chrome136")
```

Private mobile API requests still use the regular mobile session. The curl transport only changes the public web
session.

## Live Comparison

This is a point-in-time live comparison from May 15, 2026. Instagram public web behavior changes frequently, so treat
these numbers as a practical signal, not a guarantee.

Method:

* branch: curl public transport PR branch;
* environment: fresh remote Linux clone with `instagrapi[curl]` installed;
* Python: 3.12;
* rounds: 4;
* public request retry loop: disabled with `public_request_retries_count = 1`;
* curl impersonation: `chrome136`;
* identical inputs for both transports.

| Public web helper | `requests` | `curl` |
| --- | ---: | ---: |
| `user_info_by_username_gql("instagram")` | 0/4 ok, p50 12.05s | 3/4 ok, p50 1.42s |
| `user_info_by_username_gql("1fexd")` | 0/4 ok, p50 12.05s | 2/4 ok, p50 0.20s |
| `media_pk_from_url("https://www.instagram.com/p/C_BM2yAN4Rm/")` | 4/4 ok, p50 0.00s | 4/4 ok, p50 0.00s |
| `media_info_gql("3441088131388376166")` | 0/4 ok, p50 2.49s | 0/4 ok, p50 2.45s |
| Total | 4/16 ok, p50 7.28s | 9/16 ok, p50 0.23s |

Observed failures:

* `requests` repeatedly hit `429` on `users/web_profile_info`;
* `curl` avoided those `429` responses in early rounds, then hit `401` on the same public endpoint;
* both transports hit `404` on the tested public media info path.

## Recommendation

Use the default `requests` transport unless you specifically need public web endpoints that are being rate limited or
blocked by TLS fingerprint checks.

Use `public_transport="curl"` when:

* public profile web lookups return repeated `429` responses with the default transport;
* you can install the optional native dependencies pulled by `instagrapi[curl]`;
* you understand that public web access is still opportunistic and can return `401`, `403`, `404`, or `429`.

Prefer authenticated private API helpers for production workflows when an equivalent private/mobile path exists.
