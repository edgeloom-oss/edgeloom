from __future__ import annotations

import io
import tarfile
import zipfile
from pathlib import Path

import pytest

from scripts.verify_release_dist import (
    DistributionError,
    check_manifest,
    validate_distribution_set,
    write_manifest,
)

VERSION = "0.2.0"


def _metadata(version: str) -> bytes:
    return f"Metadata-Version: 2.4\nName: edgeloom\nVersion: {version}\n".encode()


def _make_distributions(directory: Path, metadata_version: str = VERSION) -> tuple[Path, Path]:
    wheel = directory / f"edgeloom-{VERSION}-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(f"edgeloom-{VERSION}.dist-info/METADATA", _metadata(metadata_version))

    sdist = directory / f"edgeloom-{VERSION}.tar.gz"
    payload = _metadata(metadata_version)
    info = tarfile.TarInfo(f"edgeloom-{VERSION}/PKG-INFO")
    info.size = len(payload)
    with tarfile.open(sdist, "w:gz") as archive:
        archive.addfile(info, io.BytesIO(payload))
    return wheel, sdist


def test_release_distribution_set_and_manifest_round_trip(tmp_path: Path) -> None:
    expected = _make_distributions(tmp_path)

    artifacts = validate_distribution_set(tmp_path, VERSION)
    manifest = tmp_path.parent / "SHA256SUMS"
    write_manifest(manifest, artifacts)
    check_manifest(manifest, artifacts)

    assert artifacts == expected


def test_release_distribution_set_rejects_an_extra_file(tmp_path: Path) -> None:
    _make_distributions(tmp_path)
    (tmp_path / "unexpected.txt").write_text("not publishable", encoding="utf-8")

    with pytest.raises(DistributionError, match="expected exactly"):
        validate_distribution_set(tmp_path, VERSION)


def test_release_distribution_set_checks_embedded_metadata(tmp_path: Path) -> None:
    _make_distributions(tmp_path, metadata_version="9.9.9")

    with pytest.raises(DistributionError, match="metadata identifies"):
        validate_distribution_set(tmp_path, VERSION)


def test_release_manifest_detects_artifact_tampering(tmp_path: Path) -> None:
    _make_distributions(tmp_path)
    artifacts = validate_distribution_set(tmp_path, VERSION)
    manifest = tmp_path.parent / "SHA256SUMS"
    write_manifest(manifest, artifacts)
    artifacts[0].write_bytes(artifacts[0].read_bytes() + b"tampered")

    with pytest.raises(DistributionError, match="SHA-256 mismatch"):
        check_manifest(manifest, artifacts)
