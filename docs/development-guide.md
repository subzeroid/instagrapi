# Development Guide

Welcome! Thank you for wanting to make the project better. This section provides an overview on how repository structure
and how to work with the code base.

Before you dive into this, it is best to read:

* The [Contributing guide](https://github.com/subzeroid/instagrapi/blob/master/CONTRIBUTING.md)

## Local Environment

Use a virtual environment and install the project from `pyproject.toml` with test extras:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
pre-commit install
```

This installs the library, runtime dependencies, test tools, lint tools, and documentation tooling in one environment.

## Debugging

Python's built-in [pdb][pdb-docs] debugger is enough for most local debugging. You can create a breakpoint anywhere in
the code:

```python
def my_function():
    breakpoint()
    ...
```

When the code reaches the breakpoint, it will drop into an interactive debugger.

See the documentation on [pdb][pdb-docs] for more information.

## Testing

You'll be unable to merge code unless linting and tests pass. The main local checks are:

```bash
pytest -sv tests/regression
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
flake8 . --count --exit-zero --statistics
isort --check-only instagrapi
bandit --ini .bandit -r instagrapi
mkdocs build --strict
```

Before committing, run the pre-commit hooks against changed files or the whole tree:

```bash
pre-commit run --all-files
```

Generally we should endeavor to write tests for every feature. Every new feature branch should increase the test
coverage rather than decreasing it.

We use [pytest][pytest-docs] as our testing framework. Regression tests live in `tests/regression/`; live-account tests
live in `tests/live/`.

#### Stages

To customize / override a specific testing stage, please read the documentation specific to that tool:

1. [PyTest][pytest-docs]
2. [Isort][isort-docs]
3. [Flake8][flake8-docs]
4. [Bandit][bandit-docs]

### `pyproject.toml`

Setuptools is used to package the library through `pyproject.toml`.

`pyproject.toml` is the source of truth for package metadata, runtime dependencies, and test/development extras.

### Dependencies

* `[project].dependencies` lists runtime dependencies imported by the library.
* `[project.optional-dependencies].test` lists tools needed for tests, linting, docs, and local development.

This will trigger the CI system to build a wheel and a source distributions of the package and push them to
[PyPI][pypi].

## Continuous Integration Pipeline

TODO: Add CI documentation.

[pdb-docs]: https://docs.python.org/3/library/pdb.html
[pytest-docs]: https://docs.pytest.org/en/latest/
[isort-docs]: https://pycqa.github.io/isort/
[flake8-docs]: http://flake8.pycqa.org/en/stable/
[bandit-docs]: https://bandit.readthedocs.io/en/stable/
[sem-ver]: https://semver.org/
[pypi]: https://pypi.org/project/instagrapi/
