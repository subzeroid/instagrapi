# protects: Only pinned source builds and matching protected cache bytes can reach the native loader.
# fails_when: Unregistered/tampered code is loaded, extraction escapes, build policy changes, or failed rebuilds replace good code.
# why_new: The original official-asset checksum test cannot validate the dedicated local-build trust boundary.
# seam: none
"""Protect the explicit source-build and native-loader trust boundary."""

import hashlib
import importlib
import importlib.util
import io
import os
import stat
import sys
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

from instagrapi import utls_native


@pytest.fixture(autouse=True)
def private_cache(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))


def build_module():
    assert importlib.util.find_spec("instagrapi.utls_build") is not None, "Explicit source installer is missing"
    return importlib.import_module("instagrapi.utls_build")


def record_build(data):
    record = getattr(utls_native, "_record_build", None)
    assert callable(record), "Only an explicit source build may register a native checksum"
    return record(data)


def test_prebuilt_checksum_alone_cannot_authorize_unregistered_native_code(monkeypatch, tmp_path):
    payload = b"synthetic-prebuilt-code"
    path = tmp_path / "unregistered-library"
    path.write_bytes(payload)
    # Reproduce the old public prebuilt-asset approval seam. A source build
    # receipt must now be independently required before calling ctypes.
    monkeypatch.setattr(
        utls_native,
        "native_library_asset",
        lambda: utls_native.NativeLibraryAsset(path.name, hashlib.sha256(payload).hexdigest()),
    )
    loader = Mock()
    monkeypatch.setattr(utls_native.ctypes, "CDLL", loader)
    with pytest.raises(RuntimeError, match="build"):
        utls_native.load_library(path)
    loader.assert_not_called()


def test_registered_build_loads_only_protected_matching_cache_bytes(monkeypatch, tmp_path):
    payload = b"synthetic-locally-built-code"
    cached = record_build(payload)
    supplied = tmp_path / "user-copy"
    supplied.write_bytes(payload)
    library = Mock()
    library.instagrapiNativeABI.return_value = 1
    loader = Mock(return_value=library)
    monkeypatch.setattr(utls_native.ctypes, "CDLL", loader)
    assert utls_native.load_library(supplied) is library
    loader.assert_called_once_with(str(cached.resolve()))
    library.instagrapiNativeABI.assert_called_once_with()
    assert cached.read_bytes() == payload
    if os.name != "nt":
        assert stat.S_IMODE(cached.stat().st_mode) == 0o600


@pytest.mark.parametrize("tamper", ["supplied", "cached", "receipt"])
def test_tampered_build_material_is_rejected_before_native_load(monkeypatch, tmp_path, tamper):
    payload = b"synthetic-locally-built-code"
    cached = record_build(payload)
    supplied = tmp_path / "user-copy"
    supplied.write_bytes(payload)
    target = supplied if tamper == "supplied" else cached
    if tamper == "receipt":
        receipts = list((tmp_path / "cache").rglob("build.json"))
        assert len(receipts) == 1
        target = receipts[0]
    target.write_bytes(b"tampered")
    loader = Mock()
    monkeypatch.setattr(utls_native.ctypes, "CDLL", loader)
    with pytest.raises(RuntimeError):
        utls_native.load_library(supplied)
    loader.assert_not_called()


@pytest.mark.skipif(os.name == "nt", reason="POSIX mode contract; Windows uses the user profile ACL")
def test_group_writable_native_cache_is_rejected_before_load(monkeypatch):
    cached = record_build(b"synthetic-code")
    cached.parent.chmod(0o770)
    loader = Mock()
    monkeypatch.setattr(utls_native.ctypes, "CDLL", loader)
    with pytest.raises(RuntimeError, match="private"):
        utls_native.load_library(cached)
    loader.assert_not_called()


def test_wrong_native_abi_is_rejected_before_request_operations(monkeypatch):
    cached = record_build(b"synthetic-code")
    library = Mock()
    library.instagrapiNativeABI.return_value = 0
    monkeypatch.setattr(utls_native.ctypes, "CDLL", Mock(return_value=library))
    with pytest.raises(RuntimeError, match="ABI"):
        utls_native.load_library(cached)
    library.request.assert_not_called()


def downloaded(payload):
    response = MagicMock()
    response.__enter__.return_value = response
    response.iter_content.return_value = [payload]
    return response


def test_bad_source_checksum_is_rejected_before_extraction(monkeypatch, tmp_path):
    module = build_module()
    download = Mock(return_value=downloaded(b"untrusted-archive"))
    monkeypatch.setattr(module, "get", download)
    source = {"name": "fixture", "version": "v1", "sha256": "0" * 64, "size": 1024}
    with pytest.raises(RuntimeError, match="checksum"):
        module._fetch_source(source, tmp_path / "source")
    assert not (tmp_path / "source").exists()


def test_verified_archive_cannot_extract_outside_destination(monkeypatch, tmp_path):
    module = build_module()
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("github.com/bogdanfinn/fixture@v1/../escape", "fixture")
    payload = stream.getvalue()
    source = {"name": "fixture", "version": "v1", "sha256": hashlib.sha256(payload).hexdigest(), "size": len(payload)}
    monkeypatch.setattr(module, "get", Mock(return_value=downloaded(payload)))
    with pytest.raises(RuntimeError, match="archive"):
        module._fetch_source(source, tmp_path / "source")
    assert not (tmp_path / "escape").exists()


def test_valid_source_archive_is_extracted_after_checksum_verification(monkeypatch, tmp_path):
    module = build_module()
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("github.com/bogdanfinn/fixture@v1/source.go", "synthetic-source")
    payload = stream.getvalue()
    source = {"name": "fixture", "version": "v1", "sha256": hashlib.sha256(payload).hexdigest(), "size": len(payload)}
    monkeypatch.setattr(module, "get", Mock(return_value=downloaded(payload)))
    module._fetch_source(source, tmp_path / "source")
    assert (tmp_path / "source" / "source.go").read_text() == "synthetic-source"


def test_existing_verified_build_is_reused_without_network_or_compiler(monkeypatch, tmp_path):
    module = build_module()
    payload = b"synthetic-built-code"
    record_build(payload)
    network = Mock(side_effect=AssertionError("Unexpected source download"))
    compiler = Mock(side_effect=AssertionError("Unexpected compiler invocation"))
    monkeypatch.setattr(module, "get", network)
    monkeypatch.setattr(module.subprocess, "run", compiler)
    path = module.build_native_library(tmp_path / "installed")
    assert path.read_bytes() == payload
    network.assert_not_called()
    compiler.assert_not_called()


def test_missing_go_fails_before_download_or_registration(monkeypatch, tmp_path):
    module = build_module()
    network = Mock(side_effect=AssertionError("Unexpected source download"))
    monkeypatch.setattr(module, "get", network)
    monkeypatch.setattr(module.shutil, "which", Mock(return_value=None))
    with pytest.raises(RuntimeError, match="Go"):
        module.build_native_library(tmp_path / "installed")
    network.assert_not_called()
    assert not list((tmp_path / "cache").rglob("build.json"))


@pytest.mark.parametrize("version", ["1.26.9", "1.27.0", "1.27.1"])
def test_vulnerable_go_toolchain_is_rejected_before_source_download(monkeypatch, tmp_path, version):
    module = build_module()
    monkeypatch.setattr(module.shutil, "which", Mock(return_value="/synthetic/go"))
    monkeypatch.setattr(
        module.subprocess,
        "run",
        Mock(return_value=Mock(returncode=0, stdout=f"go version go{version} fixture/fixture", stderr="")),
    )
    network = Mock(side_effect=AssertionError("Unsupported compiler reached source download"))
    monkeypatch.setattr(module, "get", network)
    with pytest.raises(RuntimeError, match="Go >= 1.27.2"):
        module.build_native_library(tmp_path / "installed")
    network.assert_not_called()
    assert not list((tmp_path / "cache").rglob("build.json"))


def test_installer_preserves_network_policy_and_omits_account_secrets(monkeypatch, tmp_path):
    module = build_module()
    monkeypatch.setattr(module.shutil, "which", Mock(return_value="/synthetic/go"))
    compiler = Mock(return_value=Mock(returncode=0, stdout="go version go1.27.2 fixture/fixture", stderr=""))
    monkeypatch.setattr(module.subprocess, "run", compiler)
    monkeypatch.setattr(module, "get", Mock(return_value=downloaded(b"untrusted-archive")))
    monkeypatch.setenv("HTTPS_PROXY", "http://fixture.invalid:8080")
    monkeypatch.setenv("SSL_CERT_FILE", "/synthetic/ca.pem")
    monkeypatch.setenv("IG_PASSWORD", "synthetic-account-secret")
    monkeypatch.setenv("GOFLAGS", "-overlay=/synthetic/untrusted")
    with pytest.raises(RuntimeError, match="checksum"):
        module.build_native_library(tmp_path / "installed")
    environment = compiler.call_args.kwargs["env"]
    assert environment["HTTPS_PROXY"] == "http://fixture.invalid:8080"
    assert environment["SSL_CERT_FILE"] == "/synthetic/ca.pem"
    assert environment["GOFLAGS"] == "-mod=readonly"
    assert "IG_PASSWORD" not in environment


def test_android_runtime_is_rejected_before_native_build(monkeypatch):
    monkeypatch.setattr(sys, "getandroidapilevel", lambda: 35, raising=False)
    with pytest.raises(RuntimeError, match="not supported"):
        utls_native._target()


def test_explicit_rebuild_uses_toolchain_and_preserves_last_good_build_on_failure(monkeypatch, tmp_path):
    module = build_module()
    cached = record_build(b"synthetic-last-good-build")
    monkeypatch.setattr(module.shutil, "which", Mock(return_value="/synthetic/go"))
    compiler = Mock(return_value=Mock(returncode=0, stdout="go version go1.27.2 fixture/fixture", stderr=""))
    monkeypatch.setattr(module.subprocess, "run", compiler)
    monkeypatch.setattr(module, "get", Mock(return_value=downloaded(b"untrusted-archive")))
    with pytest.raises(RuntimeError, match="checksum"):
        module.build_native_library(tmp_path / "installed", rebuild=True)
    compiler.assert_called_once()
    assert cached.read_bytes() == b"synthetic-last-good-build"
    assert utls_native.native_library_asset().sha256 == hashlib.sha256(cached.read_bytes()).hexdigest()


@pytest.mark.parametrize("failure", ["export", "registration"])
def test_failed_export_preserves_last_registered_native_build(monkeypatch, tmp_path, failure):
    module = build_module()
    old = b"synthetic-last-good-code"
    record_build(old)
    installed = module.build_native_library(tmp_path / "installed")
    previous = utls_native.native_library_asset()

    def fetch(source, destination):
        (destination / "cffi_src").mkdir(parents=True)
        (destination / "http2").mkdir()

    def run(args, work, environment, stage):
        if stage == "toolchain check":
            return "go version go1.27.2 fixture/fixture"
        if stage == "peer test selection":
            return (
                '{"Dir": ' + __import__("json").dumps(str(work / "fhttp" / "http2")) + ', "GoFiles": ["transport.go"]}'
            )
        if stage == "compilation":
            Path(args[args.index("-o") + 1]).write_bytes(b"synthetic-new-valid-code")
        return ""

    monkeypatch.setattr(module.shutil, "which", Mock(return_value="/synthetic/go"))
    monkeypatch.setattr(module, "_fetch_source", fetch)
    monkeypatch.setattr(module, "_apply_patches", lambda work: None)
    monkeypatch.setattr(module, "_run", run)
    operation = "_atomic_write" if failure == "export" else "_record_build"
    monkeypatch.setattr(module, operation, Mock(side_effect=OSError("Synthetic failed deployment export")))
    with pytest.raises(OSError, match="export"):
        module.build_native_library(tmp_path / "installed", rebuild=True)
    assert utls_native.native_library_asset() == previous
    assert installed.read_bytes() == old
