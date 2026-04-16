# Getting Started

## Installation

Install `instagrapi` with pip:

```bash
python -m pip install instagrapi
```

Supported runtime:

* Main support: `Python 3.10+`
* `Python 3.9` is in maintenance mode through **December 31, 2026**

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
```

## What's Next?

* [Fundamentals](usage-guide/fundamentals.md)
* [Interactions](usage-guide/interactions.md)
* [Best Practices](usage-guide/best-practices.md)
* [Handle Exceptions](usage-guide/handle_exception.md)
* [Challenge Resolver](usage-guide/challenge_resolver.md)
* [Exceptions](exceptions.md)

[docs-main]: index.md
