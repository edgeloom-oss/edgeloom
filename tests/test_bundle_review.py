"""Regressions from independent review of bundle consistency and portable paths."""

from __future__ import annotations

import copy
import io
import json
from pathlib import Path

import pytest
from test_bundles import ID, MANIFEST, encoded, reseal
from test_bundles import bundle_root as bundle_root
from test_catalog_pipeline import corroborated as corroborated
from test_catalog_pipeline import dataset as dataset

from edgeloom import bundles, catalog, schemas


class MemoryArchive:
    """Exercise archive verification without creating colliding filesystem entries."""

    def __init__(self, files: dict[str, bytes]):
        self.payload = bundles._zip_bytes(files)

    def open(self, mode: str) -> io.BytesIO:
        assert mode == "rb"
        return io.BytesIO(self.payload)


@pytest.mark.parametrize(
    "member, replacement",
    [
        ("index.html", b'<script>alert("unexpected script")</script><p>Hardware verified</p>'),
        ("report.md", b"# Replaced report\nAll devices passed physical tests.\n"),
        ("bundle.css", b"body::before { content: 'Hardware verified'; }"),
    ],
)
def test_resealed_rendered_files_must_still_match_canonical_records(
    bundle_root: Path, member: str, replacement: bytes
) -> None:
    files = bundles.package_files(bundles.load_bundle(bundle_root, ID))
    files[member] = replacement
    reseal(files)
    with pytest.raises(bundles.BundleError):
        bundles.verify_package(MemoryArchive(files))


@pytest.mark.parametrize("field", ["checks", "generator", "catalog_revision", "declared_core_revision"])
def test_resealed_report_provenance_cannot_bypass_consistency(bundle_root: Path, field: str) -> None:
    files = bundles.package_files(bundles.load_bundle(bundle_root, ID))
    report = json.loads(files["report.json"])
    if field == "checks":
        report[field]["hardware"] = "verified-on-hardware"
    elif field == "generator":
        report[field]["implementation_digest"] = "0" * 64
    else:
        report[field] = ["not a revision string"]
    files["report.json"] = encoded(report)
    reseal(files)
    with pytest.raises(bundles.BundleError):
        bundles.verify_package(MemoryArchive(files))


def _colliding_inputs(bundle: bundles.Bundle) -> dict[str, bytes]:
    manifest = copy.deepcopy(bundle.manifest)
    payloads = dict(bundle.payloads)
    row = manifest["records"][0]
    document = json.loads(payloads.pop(row["path"]))
    row["path"] = "catalog/documents/Manual.json"
    payloads[row["path"]] = encoded(document)
    row["sha256"] = catalog.digest(payloads[row["path"]])
    alternate = dict(document, id="alternate-manual")
    alternate_path = "catalog/documents/manual.json"
    payloads[alternate_path] = encoded(alternate)
    manifest["records"].append(
        {"id": alternate["id"], "path": alternate_path, "sha256": catalog.digest(payloads[alternate_path])}
    )
    manifest["features"][0]["record_ids"].append(alternate["id"])
    payloads[bundle.manifest_path] = encoded(manifest)
    return payloads


def test_case_colliding_input_paths_cannot_form_a_portable_bundle(bundle_root: Path) -> None:
    bundle = bundles.load_bundle(bundle_root, ID)
    with pytest.raises(bundles.BundleError, match="(?i)case|duplicate|collision"):
        bundles._assemble(None, bundle.manifest_path, _colliding_inputs(bundle))


def test_case_colliding_archive_members_are_rejected_before_extraction(bundle_root: Path) -> None:
    bundle = bundles.load_bundle(bundle_root, ID)
    files = bundles.package_files(bundle)
    # Keep every member/digest correct while introducing two names that a default
    # macOS/Windows filesystem treats as one. No real colliding paths are written.
    files["catalog/documents/Manual.json"] = files["catalog/documents/synthetic-manual.json"]
    files["catalog/documents/manual.json"] = files["catalog/documents/synthetic-manual.json"]
    reseal(files)
    with pytest.raises(bundles.BundleError, match="(?i)case|duplicate|collision"):
        bundles.verify_package(MemoryArchive(files))


def test_device_corroboration_join_is_checked_in_both_directions(
    bundle_root: Path, corroborated: Path
) -> None:
    base = bundles.load_bundle(bundle_root, ID)
    source_catalog = catalog.load_catalog(corroborated)
    device = source_catalog.devices["acme-lock"]
    manifest = copy.deepcopy(base.manifest)
    manifest["subject"] = {
        **{key: device[key] for key in ("manufacturer", "model", "protocol", "identifiers", "firmware")},
        "scope_notes": ["Synthetic fixture only."],
    }
    manifest["records"] = [
        {"id": identifier, **metadata} for identifier, metadata in source_catalog.records.items()
    ]
    manifest["features"] = [
        {
            "id": "state",
            "title": "State",
            "summary": "Synthetic evidence.",
            "record_ids": [row["id"] for row in manifest["records"]],
            "implementation_notes": [],
            "test_plan": [],
            "gaps": ["No actual device involved."],
        }
    ]
    manifest["credits"] = [{"identity": "fixture-author", "roles": ["author"], "record_ids": []}]
    payloads = {row["path"]: catalog.read_bytes(corroborated, row["path"]) for row in manifest["records"]}
    payloads[MANIFEST] = encoded(manifest)
    bundles._assemble(None, MANIFEST, payloads)

    row = next(row for row in manifest["records"] if row["id"] == device["id"])
    changed = copy.deepcopy(device)
    changed["features"].append({**copy.deepcopy(device["features"][0]), "id": "other-feature"})
    # The corroboration still points to state and is correctly linked there, but
    # the new feature improperly reuses it. The reverse direction must reject it.
    assert not schemas.validation_errors(changed, kind=schemas.CATALOG_DEVICE)
    payloads[row["path"]] = encoded(changed)
    row["sha256"] = catalog.digest(payloads[row["path"]])
    payloads[MANIFEST] = encoded(manifest)
    with pytest.raises(bundles.BundleError, match="association"):
        bundles._assemble(None, MANIFEST, payloads)
