import logging
import re
import subprocess
import sys

DEFAULT_FIRST_LIBRARY_VERSION = "0.0.1"

logging.basicConfig(level=logging.INFO)


def check_lib_version(lib_name, pypi_registry_uri):
    version = None

    # Try reading version from pyproject.toml
    with open(f"./pyproject.toml") as version_file:
        for line in version_file:
            if res := re.match(r"^version[ =\t'\"]+([0-9.]+)", line):
                version = res.group(1)
                break

    if version is None:
        logging.error("Did not find version in pyproject.toml")
        sys.exit(1)

    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
        logging.error("Version format seem incorrect, either incorrect or bug in pre-flight script")
        sys.exit(1)

    if version == DEFAULT_FIRST_LIBRARY_VERSION:
        logging.warning(
            f"No check for version {DEFAULT_FIRST_LIBRARY_VERSION} of the library {lib_name}. If {lib_name}=={DEFAULT_FIRST_LIBRARY_VERSION} has already been pushed in production, please bump the version."
        )
        return

    result = subprocess.run(
        [
            "python",
            "-m",
            "pip",
            "install",
            f"{lib_name}=={version}",
            "--index-url",
            f"{pypi_registry_uri}",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT
    )

    if result.returncode == 0:
        logging.error(
            f"Version {version} of library {lib_name} already exists in Production environment. "
            "Please update version before trying to push"
        )
        sys.exit(1)


def main():
    pypi_registry_uri = "https://pypi.heuritech.com"
    check_lib_version("instagrapi", pypi_registry_uri)


if __name__ == "__main__":
    main()
