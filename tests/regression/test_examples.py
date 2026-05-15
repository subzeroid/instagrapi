from __future__ import annotations

import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "examples"

EXPECTED_EXAMPLE_SCRIPTS = [
    "_common.py",
    "public_lookup.py",
    "download_user_media.py",
    "upload_media.py",
    "upload_story.py",
    "direct_message.py",
]


def test_examples_readme_links_practical_scripts():
    readme = EXAMPLES / "README.md"
    assert readme.exists()

    content = readme.read_text()
    for filename in EXPECTED_EXAMPLE_SCRIPTS:
        assert (EXAMPLES / filename).exists()
        assert filename in content


def test_practical_examples_compile():
    for filename in EXPECTED_EXAMPLE_SCRIPTS:
        py_compile.compile(str(EXAMPLES / filename), doraise=True)
