"""Load only explicit, locally verified builds of the strict uTLS bridge."""

import ctypes
import hashlib
import json
import os
import platform
import re
import stat
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

NATIVE_ABI = 1
_NATIVE_SOURCE = Path(__file__).with_name("native")
_BUILD_INPUTS = ("bridge.go", "go.mod", "go.sum", "patches.json", "contracts_test.go", "peer_contracts_test.go")


class _BuildMissing(RuntimeError):
    pass


@dataclass(frozen=True)
class NativeLibraryAsset:
    name: str
    sha256: str


def _target():
    system, machine = platform.system(), platform.machine()
    if sys.platform == "android" or hasattr(sys, "getandroidapilevel"):
        raise RuntimeError("uTLS native transport is not supported on Android/Termux")
    architectures = {
        "arm64": "arm64",
        "aarch64": "arm64",
        "x86_64": "amd64",
        "AMD64": "amd64",
        "x86": "386",
        "i386": "386",
        "armv7l": "arm",
    }
    if system not in {"Darwin", "Linux", "Windows"} or machine not in architectures:
        raise RuntimeError(f"uTLS native transport is not supported on {system}/{machine}")
    arch = "386" if system == "Windows" and ctypes.sizeof(ctypes.c_void_p) == 4 else architectures[machine]
    extension = {"Darwin": ".dylib", "Linux": ".so", "Windows": ".dll"}[system]
    return system.lower(), arch, extension


def _source_fingerprint():
    digest = hashlib.sha256()
    inputs = [Path(__file__), Path(__file__).with_name("utls_build.py")]
    inputs.extend(_NATIVE_SOURCE / name for name in _BUILD_INPUTS)
    try:
        for path in inputs:
            digest.update(path.name.encode() + b"\0" + path.read_bytes() + b"\0")
    except OSError:
        raise RuntimeError("uTLS build sources are missing; reinstall the package") from None
    return digest.hexdigest()


def _private_directory(path, *, create=False):
    if path.is_symlink():
        raise RuntimeError("uTLS build cache must be a private directory, not a symlink")
    if create:
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not path.is_dir():
        raise _BuildMissing("No verified local uTLS build; run python -m instagrapi.utls_native DIRECTORY")
    resolved = path.resolve()
    if os.name == "nt":
        if not resolved.is_relative_to(Path.home().resolve()):
            raise RuntimeError("uTLS build cache must be inside the private Windows user profile")
    else:
        info = resolved.stat()
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
            raise RuntimeError("uTLS build cache must be private to its owner (mode 0700)")
        for parent in resolved.parents:
            info = parent.stat()
            if info.st_uid not in {0, os.getuid()} or (info.st_mode & 0o022 and not info.st_mode & stat.S_ISVTX):
                raise RuntimeError("uTLS build cache ancestors must not permit untrusted writes")
    return resolved


def _build_directory(*, create=False):
    system, arch, _ = _target()
    base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "instagrapi" / "utls-native"
    base = _private_directory(base, create=create)
    source = _private_directory(base / _source_fingerprint(), create=create)
    return _private_directory(source / f"{system}-{arch}", create=create)


def _private_file(path):
    try:
        info = path.lstat()
    except OSError:
        raise RuntimeError("uTLS verified build cache is incomplete; rebuild the native library") from None
    if not stat.S_ISREG(info.st_mode):
        raise RuntimeError("uTLS verified build cache contains an unsafe file")
    if os.name != "nt" and (info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077):
        raise RuntimeError("uTLS verified build files must be private to their owner (mode 0600)")


def _asset_for_digest(digest):
    system, arch, extension = _target()
    return NativeLibraryAsset(f"instagrapi-utls-{system}-{arch}-abi{NATIVE_ABI}-{digest}{extension}", digest)


def _verified_build():
    directory = _build_directory()
    receipt = directory / "build.json"
    if not receipt.exists():
        raise _BuildMissing("No verified local uTLS build; run python -m instagrapi.utls_native DIRECTORY")
    _private_file(receipt)
    try:
        metadata = json.loads(receipt.read_text())
    except (OSError, ValueError):
        raise RuntimeError("uTLS verified build receipt is invalid; rebuild the native library") from None
    system, arch, extension = _target()
    if (
        not isinstance(metadata, dict)
        or set(metadata) != {"schema", "source", "target", "sha256"}
        or metadata["schema"] != 1
        or metadata["source"] != _source_fingerprint()
        or metadata["target"] != f"{system}-{arch}"
        or not isinstance(metadata["sha256"], str)
        or re.fullmatch(r"[0-9a-f]{64}", metadata["sha256"]) is None
    ):
        raise RuntimeError("uTLS verified build receipt does not match this installation")
    blob = directory / (metadata["sha256"] + extension)
    _private_file(blob)
    if hashlib.sha256(blob.read_bytes()).hexdigest() != metadata["sha256"]:
        raise RuntimeError("uTLS verified build cache checksum mismatch")
    return _asset_for_digest(metadata["sha256"]), blob


def _atomic_write(path, data):
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".utls-")
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(data)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _record_build(data, *, source_fingerprint=None):
    current = _source_fingerprint()
    if source_fingerprint is not None and source_fingerprint != current:
        raise RuntimeError("uTLS sources changed during the build; run the installer again")
    directory = _build_directory(create=True)
    system, arch, extension = _target()
    digest = hashlib.sha256(data).hexdigest()
    blob = directory / (digest + extension)
    if blob.exists():
        _private_file(blob)
        if hashlib.sha256(blob.read_bytes()).hexdigest() != digest:
            raise RuntimeError("uTLS verified build cache checksum mismatch")
    else:
        _atomic_write(blob, data)
    receipt = {"schema": 1, "source": current, "target": f"{system}-{arch}", "sha256": digest}
    _atomic_write(directory / "build.json", json.dumps(receipt, sort_keys=True).encode())
    return blob


def native_library_asset() -> NativeLibraryAsset:
    """Name and checksum of this user's explicit, source-matching local build."""
    return _verified_build()[0]


def load_library(path):
    if path is None:
        raise RuntimeError("utls requires utls_library_path; run python -m instagrapi.utls_native DIRECTORY")
    asset, cached = _verified_build()
    path = Path(path)
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != asset.sha256:
        raise RuntimeError("utls_library_path must contain the verified locally built native library")
    # Adjacent manifests are never approval. Load the protected cache copy so a
    # caller-supplied deployment directory cannot swap code after the hash check.
    library = ctypes.CDLL(str(cached.resolve()))
    try:
        library.instagrapiNativeABI.argtypes = []
        library.instagrapiNativeABI.restype = ctypes.c_int
        if library.instagrapiNativeABI() != NATIVE_ABI:
            raise AttributeError
    except AttributeError:
        raise RuntimeError("uTLS native ABI does not match this installation") from None
    for name in ("request", "destroySession"):
        function = getattr(library, name)
        function.argtypes = [ctypes.c_char_p]
        function.restype = ctypes.c_void_p
    library.freeMemory.argtypes = [ctypes.c_char_p]
    library.freeMemory.restype = None
    return library


if __name__ == "__main__":
    import argparse

    from instagrapi.utls_build import build_native_library

    parser = argparse.ArgumentParser(
        description="Build the verified strict uTLS library explicitly (requires Go and a C compiler)"
    )
    parser.add_argument("directory", type=Path)
    parser.add_argument("--rebuild", action="store_true", help="recompile with the current Go/C toolchain")
    args = parser.parse_args()
    print(build_native_library(args.directory, rebuild=args.rebuild))
