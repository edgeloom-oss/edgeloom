#!/usr/bin/env python3
"""Validate the exact EdgeLoom distribution set before PyPI publication."""

from __future__ import annotations

import argparse
import hashlib
import re
import stat
import tarfile
import zipfile
from email.parser import BytesParser
from pathlib import Path, PurePosixPath

PROJECT = "edgeloom"
MANIFEST_LINE = re.compile(r"^([0-9a-f]{64})  ([A-Za-z0-9_.+-]+)$")


class DistributionError(ValueError):
    """Raised when a release bundle is not the exact expected artifact set."""


def _safe_member_name(name: str) -> bool:
    path = PurePosixPath(name)
    return bool(name) and not path.is_absolute() and ".." not in path.parts


def _metadata_identity(payload: bytes, source: str) -> tuple[str, str]:
    metadata = BytesParser().parsebytes(payload)
    name = metadata.get("Name")
    version = metadata.get("Version")
    if not name or not version:
        raise DistributionError(f"{source} is missing Name or Version metadata")
    return name, version


def _validate_wheel(path: Path, version: str) -> None:
    metadata_name = f"{PROJECT}-{version}.dist-info/METADATA"
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        for entry in entries:
            if not _safe_member_name(entry.filename):
                raise DistributionError(f"unsafe wheel member: {entry.filename!r}")
            mode = entry.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise DistributionError(f"wheel contains a symlink: {entry.filename!r}")
        matches = [entry for entry in entries if entry.filename == metadata_name]
        if len(matches) != 1:
            raise DistributionError(f"wheel must contain exactly one {metadata_name}")
        identity = _metadata_identity(archive.read(matches[0]), f"{path.name} METADATA")
    if identity != (PROJECT, version):
        raise DistributionError(
            f"{path.name} metadata identifies {identity[0]} {identity[1]}, expected {PROJECT} {version}"
        )


def _validate_sdist(path: Path, version: str) -> None:
    metadata_name = f"{PROJECT}-{version}/PKG-INFO"
    with tarfile.open(path, mode="r:gz") as archive:
        members = archive.getmembers()
        for member in members:
            if not _safe_member_name(member.name):
                raise DistributionError(f"unsafe sdist member: {member.name!r}")
            if member.issym() or member.islnk() or member.isdev() or member.isfifo():
                raise DistributionError(f"sdist contains a special link/device: {member.name!r}")
        matches = [member for member in members if member.name == metadata_name]
        if len(matches) != 1:
            raise DistributionError(f"sdist must contain exactly one {metadata_name}")
        extracted = archive.extractfile(matches[0])
        if extracted is None:
            raise DistributionError(f"cannot read {metadata_name}")
        identity = _metadata_identity(extracted.read(), f"{path.name} PKG-INFO")
    if identity != (PROJECT, version):
        raise DistributionError(
            f"{path.name} metadata identifies {identity[0]} {identity[1]}, expected {PROJECT} {version}"
        )


def validate_distribution_set(dist_dir: Path, version: str) -> tuple[Path, Path]:
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
        raise DistributionError("version must be stable SemVer without a v prefix")
    if not dist_dir.is_dir():
        raise DistributionError(f"distribution directory does not exist: {dist_dir}")

    expected_names = {
        f"{PROJECT}-{version}-py3-none-any.whl",
        f"{PROJECT}-{version}.tar.gz",
    }
    entries = list(dist_dir.iterdir())
    actual_names = {entry.name for entry in entries}
    if len(entries) != 2 or actual_names != expected_names:
        raise DistributionError(f"expected exactly {sorted(expected_names)}, found {sorted(actual_names)}")
    for entry in entries:
        mode = entry.lstat().st_mode
        if not stat.S_ISREG(mode) or entry.is_symlink():
            raise DistributionError(f"distribution is not a regular file: {entry.name}")

    wheel = dist_dir / f"{PROJECT}-{version}-py3-none-any.whl"
    sdist = dist_dir / f"{PROJECT}-{version}.tar.gz"
    _validate_wheel(wheel, version)
    _validate_sdist(sdist, version)
    return wheel, sdist


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_manifest(manifest: Path, artifacts: tuple[Path, Path]) -> None:
    lines = [f"{_sha256(path)}  {path.name}\n" for path in sorted(artifacts)]
    manifest.write_text("".join(lines), encoding="ascii")


def check_manifest(manifest: Path, artifacts: tuple[Path, Path]) -> None:
    if not manifest.is_file() or manifest.is_symlink():
        raise DistributionError(f"manifest is not a regular file: {manifest}")
    observed: dict[str, str] = {}
    for raw_line in manifest.read_text(encoding="ascii").splitlines():
        match = MANIFEST_LINE.fullmatch(raw_line)
        if match is None or match.group(2) in observed:
            raise DistributionError("malformed or duplicate SHA256SUMS entry")
        observed[match.group(2)] = match.group(1)
    expected_names = {path.name for path in artifacts}
    if set(observed) != expected_names:
        raise DistributionError("SHA256SUMS does not name the exact distribution set")
    for path in artifacts:
        if _sha256(path) != observed[path.name]:
            raise DistributionError(f"SHA-256 mismatch for {path.name}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist-dir", required=True, type=Path)
    parser.add_argument("--version", required=True)
    manifest_mode = parser.add_mutually_exclusive_group(required=True)
    manifest_mode.add_argument("--write-manifest", type=Path)
    manifest_mode.add_argument("--check-manifest", type=Path)
    args = parser.parse_args()

    try:
        artifacts = validate_distribution_set(args.dist_dir, args.version)
        if args.write_manifest is not None:
            write_manifest(args.write_manifest, artifacts)
            print(f"validated distributions and wrote {args.write_manifest}")
        else:
            check_manifest(args.check_manifest, artifacts)
            print(f"validated distributions and {args.check_manifest}")
    except (DistributionError, OSError, tarfile.TarError, zipfile.BadZipFile) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
