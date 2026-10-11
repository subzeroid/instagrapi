"""Pinned tls-client assets. Downloads are explicit install/build operations."""

import ctypes
import hashlib
import os
import platform
import tempfile
from dataclasses import dataclass
from pathlib import Path

from requests import get

NATIVE_VERSION = "1.16.0"
_ASSETS = {
    ("Darwin", "arm64"): ("darwin-arm64", "dylib", "99984d013921c753ab29d28720cb099eff6adf63538347e13652cb5cfe5bdc02"),
    ("Darwin", "x86_64"): ("darwin-amd64", "dylib", "6463457ea713a96b3b8c94fd9d8746e7bc510cb6784fcf0f4bb64d9c83e3251a"),
    ("Linux", "x86_64"): (
        "linux-ubuntu-amd64",
        "so",
        "2ec853496634545e7a7ea028715763948d55bbdd97aca7ecaa9fea8c2ebb08df",
    ),
    ("Linux", "aarch64"): ("linux-arm64", "so", "e398622f99c0ce8fccb50ff6e414f373b5932a0277ece90468a796992f0ae518"),
    ("Linux", "armv7l"): ("linux-armv7", "so", "22baa029d4ee8cf327d10cda0e66c29cf256b3eb48e1fe9d6a76954b66f77711"),
    ("Windows", "AMD64"): ("windows-64", "dll", "53dca636b32d965ee6fe4562f39df959b2063febaa3d740efa925d1873cf11d7"),
    ("Windows", "x86"): ("windows-32", "dll", "5203a36f80ea3f9cdfa43bf072a775702d1802acb8e4304e78905210f67dd2af"),
}


@dataclass(frozen=True)
class NativeLibraryAsset:
    name: str
    sha256: str

    @property
    def url(self) -> str:
        return f"https://github.com/bogdanfinn/tls-client/releases/download/v{NATIVE_VERSION}/{self.name}"


def native_library_asset() -> NativeLibraryAsset:
    """Official binary for the current Python process's OS and architecture."""
    system, machine = platform.system(), platform.machine()
    if system == "Windows" and ctypes.sizeof(ctypes.c_void_p) == 4:
        machine = "x86"
    try:
        target, extension, digest = _ASSETS[system, machine]
    except KeyError:
        raise RuntimeError(f"uTLS native transport is not supported on {system}/{machine}") from None
    if system == "Linux" and platform.libc_ver()[0] == "musl":
        if machine != "x86_64":
            raise RuntimeError("uTLS native transport has no reviewed musl binary for this architecture")
        target, digest = "linux-alpine-amd64", "83c8702e8e8af2e5629277f422e77384a8780ac63c7f20988269a82d78e835ae"
    return NativeLibraryAsset(f"tls-client-{target}-{NATIVE_VERSION}.{extension}", digest)


def download_native_library(directory: str | Path) -> Path:
    """Explicitly install one verified binary; never called by Client."""
    asset = native_library_asset()
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / asset.name
    if target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest() == asset.sha256:
        return target
    temporary = None
    try:
        with get(asset.url, timeout=60) as response:
            response.raise_for_status()
            data = response.content
        if hashlib.sha256(data).hexdigest() != asset.sha256:
            raise RuntimeError("uTLS native library download checksum mismatch")
        descriptor, temporary = tempfile.mkstemp(dir=directory, prefix=".tls-client-")
        with os.fdopen(descriptor, "wb") as output:
            output.write(data)
        os.replace(temporary, target)
        return target
    finally:
        if temporary is not None:
            Path(temporary).unlink(missing_ok=True)


def load_library(path):
    if path is None:
        raise RuntimeError("utls requires utls_library_path; run python -m instagrapi.utls_native DIRECTORY")
    path = Path(path)
    asset = native_library_asset()
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != asset.sha256:
        raise RuntimeError(f"utls_library_path must contain the verified tls-client v{NATIVE_VERSION} platform binary")
    library = ctypes.CDLL(str(path.resolve()))
    for name in ("request", "destroySession"):
        function = getattr(library, name)
        function.argtypes = [ctypes.c_char_p]
        function.restype = ctypes.c_void_p
    library.freeMemory.argtypes = [ctypes.c_char_p]
    library.freeMemory.restype = None
    return library


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Install the verified tls-client native library for this platform")
    parser.add_argument("directory", type=Path)
    print(download_native_library(parser.parse_args().directory))
