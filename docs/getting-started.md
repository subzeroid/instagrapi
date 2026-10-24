# Getting Started

## Installation

Install `instagrapi` with pip:

```bash
python -m pip install instagrapi
```

Requires **Python 3.11+** and **Pillow 13+**.

Pillow 13 provides upstream security fixes, including [CVE-2026-96778](https://github.com/python-pillow/Pillow/security/advisories/GHSA-g7cr-3p24-7wf7), and [requires Python 3.11 or newer](https://pypi.org/project/pillow/13.0.0/). `instagrapi==3.1.0` is the last release compatible with Python 3.10; its Pillow dependency range excludes these fixes. Upgrade to Python 3.11+ before installing instagrapi 3.2.0 or newer.

## Introduction

`instagrapi` is an unofficial Instagram API wrapper for Python. It combines public web and private mobile flows, supports session persistence and challenge handling, and exposes a broad set of primitives for users, media, stories, direct messages, notes, uploads, and insights.

A good first production habit is to avoid password login on every run. Prefer:

```python
from instagrapi import Client

cl = Client()
cl.login(USERNAME, PASSWORD)
cl.dump_settings("session.json")
```

Then on the next run:

```python
from instagrapi import Client

cl = Client()
cl.load_settings("session.json")
cl.login(USERNAME, PASSWORD)
cl.dump_settings("session.json")
```

The saved session is validated during `login()`. If Instagram rejects it with
`login_required`, instagrapi performs a fresh login with the supplied
credentials. Saving the settings again persists any refreshed session.

## What's Next?

* [Runnable examples](usage-guide/examples.md)
* [Fundamentals](usage-guide/fundamentals.md)
* [Interactions](usage-guide/interactions.md)
* [Best Practices](usage-guide/best-practices.md)
* [Handle Exceptions](usage-guide/handle_exception.md)
* [Challenge Resolver](usage-guide/challenge_resolver.md)
* [Exceptions](exceptions.md)

[docs-main]: index.md
