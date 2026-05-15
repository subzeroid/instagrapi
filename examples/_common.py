from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

from instagrapi import Client

DEFAULT_SESSION_FILE = "ig_settings.json"


def env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value


def require_env(name: str) -> str:
    value = env(name)
    if value is None:
        raise SystemExit(f"Set {name} environment variable before running this example.")
    return value


def env_int(name: str, default: int) -> int:
    value = env(name)
    if value is None:
        return default
    return int(value)


def parse_ids(values: Iterable[str] | str | None) -> list[int]:
    if values is None:
        return []
    if isinstance(values, str):
        values = values.split(",")
    return [int(value.strip()) for value in values if value.strip()]


def make_client(login: bool = True) -> Client:
    kwargs = {}
    public_transport = env("IG_PUBLIC_TRANSPORT")
    if public_transport:
        kwargs["public_transport"] = public_transport
    public_transport_impersonate = env("IG_PUBLIC_TRANSPORT_IMPERSONATE")
    if public_transport_impersonate:
        kwargs["public_transport_impersonate"] = public_transport_impersonate

    cl = Client(**kwargs)
    proxy = env("IG_PROXY")
    if proxy:
        cl.set_proxy(proxy)

    if not login:
        return cl

    username = require_env("IG_USERNAME")
    password = require_env("IG_PASSWORD")
    session_file = Path(env("IG_SESSION_FILE", DEFAULT_SESSION_FILE)).expanduser()

    if session_file.exists():
        cl.load_settings(session_file)

    cl.login(username, password, verification_code=env("IG_VERIFICATION_CODE", ""))
    cl.dump_settings(session_file)
    return cl
