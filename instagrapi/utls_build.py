"""Explicit source installer for the strict uTLS bridge; never invoked by Client."""

import hashlib
import io
import json
import os
import re
import shutil
import subprocess  # nosec B404
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from requests import get

from instagrapi.utls_native import (
    _BUILD_INPUTS,
    _NATIVE_SOURCE,
    _asset_for_digest,
    _atomic_write,
    _BuildMissing,
    _record_build,
    _source_fingerprint,
    _target,
    _verified_build,
)

_SOURCES = (
    {
        "name": "tls-client",
        "version": "v1.16.0",
        "sha256": "287e51a978eebcd384790f22e6c316a0a09133699637c6cd5cc53b3ace087508",
        "size": 189605,
    },
    {
        "name": "fhttp",
        "version": "v0.6.9",
        "sha256": "4b1ae2a1e06963a6e80cf82d5eb61233ece804f03dcfd111f67c677cfcca14fa",
        "size": 906480,
    },
)


def _fetch_source(source, destination):
    url = f"https://proxy.golang.org/github.com/bogdanfinn/{source['name']}/@v/{source['version']}.zip"
    data = bytearray()
    with get(url, timeout=(10, 60), stream=True) as response:
        response.raise_for_status()
        for chunk in response.iter_content(65536):
            data.extend(chunk)
            if len(data) > source["size"]:
                raise RuntimeError("uTLS source archive exceeds its pinned size")
    if hashlib.sha256(data).hexdigest() != source["sha256"]:
        raise RuntimeError("uTLS source archive checksum mismatch")
    prefix = f"github.com/bogdanfinn/{source['name']}@{source['version']}/"
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        selected = []
        for entry in archive.infolist():
            name = entry.filename
            relative = PurePosixPath(name.removeprefix(prefix))
            if (
                not name.startswith(prefix)
                or relative.is_absolute()
                or ".." in relative.parts
                or not relative.parts
                or "\\" in name
                or ":" in name
            ):
                raise RuntimeError("uTLS source archive contains an unsafe path")
            selected.append((entry, relative))
        for entry, relative in selected:
            target = destination.joinpath(*relative.parts)
            if entry.is_dir():
                target.mkdir(mode=0o700, parents=True, exist_ok=True)
            else:
                target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                target.write_bytes(archive.read(entry))


def _apply_patches(work):
    for patch in json.loads((_NATIVE_SOURCE / "patches.json").read_text()):
        target = work / patch["module"] / patch["path"]
        data = target.read_bytes()
        if hashlib.sha256(data).hexdigest() != patch["before_sha256"]:
            raise RuntimeError("uTLS patch does not match its pinned source")
        text = data.decode()
        for replacement in patch["replacements"]:
            if text.count(replacement["old"]) != 1:
                raise RuntimeError("uTLS patch context does not match its pinned source")
            text = text.replace(replacement["old"], replacement["new"])
        if hashlib.sha256(text.encode()).hexdigest() != patch["after_sha256"]:
            raise RuntimeError("uTLS patched source checksum mismatch")
        target.write_bytes(text.encode())


def _run(args, work, environment, stage):
    try:
        # Resolved local Go, fixed argument lists and pinned sources; no shell.
        result = subprocess.run(  # nosec B603
            args, cwd=work, env=environment, capture_output=True, text=True, timeout=300, shell=False
        )
    except (OSError, subprocess.TimeoutExpired):
        raise RuntimeError(f"uTLS native {stage} could not run; a working Go and C toolchain is required") from None
    if result.returncode:
        raise RuntimeError(f"uTLS native {stage} failed:\n{result.stderr[-4000:]}")
    return result.stdout


def _compile_native_library():
    go = shutil.which("go")
    if go is None:
        raise RuntimeError("Building uTLS requires Go >= 1.27.2 and a C compiler") from None
    fingerprint = _source_fingerprint()
    environment = {
        key: value
        for key, value in os.environ.items()
        if key
        in {
            "PATH",
            "HOME",
            "USERPROFILE",
            "LOCALAPPDATA",
            "APPDATA",
            "SYSTEMROOT",
            "WINDIR",
            "TEMP",
            "TMP",
            "TMPDIR",
            "XDG_CACHE_HOME",
            "SDKROOT",
            "CC",
            "CXX",
            "SSL_CERT_FILE",
            "SSL_CERT_DIR",
        }
        or key.lower() in {"http_proxy", "https_proxy", "all_proxy", "no_proxy"}
    }
    system, arch, extension = _target()
    environment.update(
        GOENV="off",
        GOWORK="off",
        GOTOOLCHAIN="local",
        GOFLAGS="-mod=readonly",
        GOPROXY="https://proxy.golang.org",
        GOSUMDB="sum.golang.org",
        CGO_ENABLED="1",
        GOOS=system,
        GOARCH=arch,
    )
    with tempfile.TemporaryDirectory(prefix="instagrapi-utls-") as temporary:
        work = Path(temporary)
        version = _run([go, "version"], work, environment, "toolchain check")
        match = re.search(r"\bgo(\d+)\.(\d+)\.(\d+)\b", version)
        if match is None or tuple(map(int, match.groups())) < (1, 27, 2):
            raise RuntimeError("Building uTLS requires Go >= 1.27.2 and a C compiler")
        for source in _SOURCES:
            _fetch_source(source, work / source["name"])
        _apply_patches(work)
        for name in _BUILD_INPUTS:
            if name in {"go.mod", "go.sum", "bridge.go"}:
                shutil.copyfile(_NATIVE_SOURCE / name, work / name)
        shutil.copyfile(
            _NATIVE_SOURCE / "contracts_test.go", work / "tls-client" / "cffi_src" / "instagrapi_contract_test.go"
        )
        shutil.copyfile(_NATIVE_SOURCE / "peer_contracts_test.go", work / "fhttp" / "http2" / "instagrapi_peer_test.go")
        _run([go, "mod", "verify"], work, environment, "module verification")
        # Select production files using Go's build constraints. The upstream
        # package tests predate the pinned cancellation patch's method signature.
        peer_package = json.loads(
            _run([go, "list", "-json", "github.com/bogdanfinn/fhttp/http2"], work, environment, "peer test selection")
        )
        peer_directory = Path(peer_package["Dir"])
        peer_files = [str(peer_directory / name) for name in peer_package["GoFiles"]]
        _run(
            [
                go,
                "test",
                *peer_files,
                str(peer_directory / "instagrapi_peer_test.go"),
                "-run",
                "TestInstagrapi",
                "-count=1",
                "-timeout=30s",
            ],
            work,
            environment,
            "peer protocol checks",
        )
        _run(
            [go, "test", "github.com/bogdanfinn/tls-client/cffi_src", "-run", "TestInstagrapi", "-count=1"],
            work,
            environment,
            "construction checks",
        )
        built = work / ("native" + extension)
        _run(
            [go, "build", "-trimpath", "-buildvcs=false", "-buildmode=c-shared", "-o", str(built), "."],
            work,
            environment,
            "compilation",
        )
        data = built.read_bytes()
    return data, fingerprint


def build_native_library(directory: str | Path, *, rebuild=False) -> Path:
    """Build explicitly, exporting the new file before replacing its registration."""
    cached = None
    if not rebuild:
        try:
            asset, cached = _verified_build()
        except _BuildMissing:
            pass
    fingerprint = None
    if cached is None:
        data, fingerprint = _compile_native_library()
        if fingerprint != _source_fingerprint():
            raise RuntimeError("uTLS sources changed during the build; run the installer again")
        asset = _asset_for_digest(hashlib.sha256(data).hexdigest())
    else:
        data = cached.read_bytes()
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    # Digest-named deployment files keep the previous working path intact if
    # either export or registration fails; the receipt is the final commit.
    target = directory / asset.name
    if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != asset.sha256:
        _atomic_write(target, data)
    if cached is None:
        _record_build(data, source_fingerprint=fingerprint)
    return target
