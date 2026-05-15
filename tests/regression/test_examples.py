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
