from pathlib import Path


def test_pydantic_dependency_allows_termux_android_wheel_version():
    pyproject = Path("pyproject.toml").read_text()
    required_dependencies = pyproject.split("[project.optional-dependencies]", 1)[0]

    assert "\"pydantic==2.12.5; sys_platform == 'android'\"" in required_dependencies
    assert "\"pydantic>=2.12.5,<2.14; sys_platform != 'android'\"" in required_dependencies
    assert '"pydantic==2.13.4"' not in required_dependencies


def test_termux_guide_documents_android_pydantic_core_wheel_index():
    termux_guide = Path("docs/usage-guide/termux.md").read_text()

    assert "https://termux-user-repository.github.io/pypi/" in termux_guide
    assert "pydantic==2.12.5" in termux_guide
