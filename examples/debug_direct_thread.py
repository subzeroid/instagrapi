"""Inspect parsed and raw direct-thread payloads for debugging message types."""

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlparse

from instagrapi import Client
from instagrapi.extractors import extract_direct_message

SESSION_FILE = "session.json"


def login() -> Client:
    cl = Client()
    username = os.environ.get("IG_USERNAME")
    password = os.environ.get("IG_PASSWORD")

    if os.path.exists(SESSION_FILE):
        cl.load_settings(SESSION_FILE)
        if username and password:
            cl.login(username, password)
        return cl

    if not username or not password:
        raise RuntimeError("Set IG_USERNAME and IG_PASSWORD, or place a session.json next to this script.")

    cl.login(username, password)
    cl.dump_settings(SESSION_FILE)
    return cl


def summarize_xma(items: List[Any]) -> List[Dict[str, str]]:
    return [
        {
            "video_url": str(item.video_url),
            "title": item.title or "",
            "preview_url": item.preview_url or "",
        }
        for item in items
    ]


def slugify(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("_") or "item"


def guess_extension(url: str, content_type: str = "") -> str:
    suffix = Path(urlparse(url).path).suffix
    if suffix:
        return suffix
    if "mp4" in content_type:
        return ".mp4"
    if "jpeg" in content_type:
        return ".jpg"
    if "png" in content_type:
        return ".png"
    if "webp" in content_type:
        return ".webp"
    return ".bin"


def download_url(cl: Client, url: str, dest: Path) -> Path:
    response = cl.private.get(url, stream=True, timeout=cl.request_timeout)
    response.raise_for_status()
    content_type = response.headers.get("Content-Type", "")
    path = dest.with_suffix(dest.suffix or guess_extension(url, content_type))
    with open(path, "wb") as fh:
        for chunk in response.iter_content(chunk_size=1024 * 64):
            if chunk:
                fh.write(chunk)
    return path.resolve()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("thread_id", help="Direct thread id")
    parser.add_argument("--amount", type=int, default=20, help="Messages to fetch")
    parser.add_argument(
        "--message-id",
        help="Optional message id filter to print only one message",
    )
    parser.add_argument(
        "--download-dir",
        help="Optional directory for downloading xma/generic_xma URLs",
    )
    args = parser.parse_args()

    cl = login()
    params = {
        "visual_message_return_type": "unseen",
        "direction": "older",
        "seq_id": "40065",
        "limit": str(min(args.amount, 20)),
    }
    result = cl.private_request(f"direct_v2/threads/{args.thread_id}/", params=params)
    raw_items = result["thread"]["items"][: args.amount]

    download_dir = Path(args.download_dir) if args.download_dir else None
    if download_dir:
        download_dir.mkdir(parents=True, exist_ok=True)

    for raw in raw_items:
        if args.message_id and str(raw.get("item_id")) != args.message_id:
            continue

        message = extract_direct_message(dict(raw))
        downloads = []
        if download_dir:
            candidates = []
            if message.xma_share:
                candidates.append(
                    (
                        f"{message.id}_xma_share",
                        str(message.xma_share.video_url),
                    )
                )
                if message.xma_share.preview_url:
                    candidates.append(
                        (
                            f"{message.id}_xma_share_preview",
                            str(message.xma_share.preview_url),
                        )
                    )
            for idx, item in enumerate(message.generic_xma or []):
                candidates.append(
                    (
                        f"{message.id}_generic_xma_{idx}",
                        str(item.video_url),
                    )
                )
                if item.preview_url:
                    candidates.append(
                        (
                            f"{message.id}_generic_xma_{idx}_preview",
                            str(item.preview_url),
                        )
                    )
            for stem, url in candidates:
                try:
                    path = download_url(cl, url, download_dir / slugify(stem))
                    downloads.append({"url": url, "path": str(path)})
                except Exception as exc:
                    downloads.append({"url": url, "error": f"{exc.__class__.__name__}: {exc}"})
        summary = {
            "message_id": message.id,
            "item_type": message.item_type,
            "text": message.text,
            "raw_keys": sorted(raw.keys()),
            "has_media": bool(message.media),
            "has_xma_share": bool(message.xma_share),
            "generic_xma_count": len(message.generic_xma or []),
            "xma_share": (
                {
                    "video_url": str(message.xma_share.video_url),
                    "title": message.xma_share.title or "",
                    "preview_url": message.xma_share.preview_url or "",
                }
                if message.xma_share
                else None
            ),
            "generic_xma": summarize_xma(message.generic_xma or []),
            "raw_generic_xma": raw.get("generic_xma"),
            "raw_xma_clip": raw.get("xma_clip"),
            "raw_xma_media_share": raw.get("xma_media_share"),
            "downloads": downloads,
        }
        print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
