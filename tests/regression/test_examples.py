from __future__ import annotations

import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "examples"
DOCS_EXAMPLES = ROOT / "docs" / "usage-guide" / "examples.md"
GITHUB_EXAMPLES_URL = "https://github.com/subzeroid/instagrapi/blob/master/examples"

EXPECTED_EXAMPLE_SCRIPTS = [
    "_common.py",
    "public_lookup.py",
    "download_user_media.py",
    "upload_media.py",
    "upload_story.py",
    "direct_message.py",
]

DOCS_EXAMPLE_SCRIPTS = [
    "public_lookup.py",
    "download_user_media.py",
    "upload_media.py",
    "upload_story.py",
    "direct_message.py",
    "handle_exception.py",
]


def test_examples_readme_links_practical_scripts():
    readme = EXAMPLES / "README.md"
    assert readme.exists()

    content = readme.read_text()
    for filename in EXPECTED_EXAMPLE_SCRIPTS:
        assert (EXAMPLES / filename).exists()
        assert f"[`{filename}`]({filename})" in content


def test_docs_examples_links_to_github_scripts():
    content = DOCS_EXAMPLES.read_text()
    for filename in DOCS_EXAMPLE_SCRIPTS:
        assert (EXAMPLES / filename).exists()
        assert f"[`{filename}`]({GITHUB_EXAMPLES_URL}/{filename})" in content


def test_practical_examples_compile():
    for filename in EXPECTED_EXAMPLE_SCRIPTS:
        py_compile.compile(str(EXAMPLES / filename), doraise=True)


def test_public_lookup_uses_modern_with_explicit_saved_session(monkeypatch, capsys):
    import runpy
    import sys
    from types import ModuleType, SimpleNamespace

    events = []
    user = SimpleNamespace(
        pk="123",
        username="example",
        full_name="Example",
        media_count=0,
        follower_count=0,
        following_count=0,
        is_private=False,
        is_verified=False,
    )

    def modern(username):
        events.append(("modern", username))
        return user

    client = SimpleNamespace(
        load_settings=lambda path: events.append(("load", path)), user_info_by_username_v2_gql=modern
    )

    def make_client(login=True):
        assert login is False
        return client

    common = ModuleType("_common")
    common.make_client = make_client
    monkeypatch.setitem(sys.modules, "_common", common)
    monkeypatch.setattr(sys, "argv", ["public_lookup.py", "example", "--session-file", "saved-session.json"])
    namespace = runpy.run_path(str(EXAMPLES / "public_lookup.py"), run_name="example_test")
    namespace["main"]()
    assert events == [("load", "saved-session.json"), ("modern", "example")]
    assert '"username": "example"' in capsys.readouterr().out
