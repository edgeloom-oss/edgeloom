"""Optional bundle publishing within the owned, deterministic catalog output."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_catalog_pipeline import dataset as dataset

from edgeloom import bundles, catalog


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(catalog.render_json(value), encoding="utf-8")


@pytest.fixture
def bundled(dataset: Path) -> Path:
    loaded = catalog.load_catalog(dataset)
    device = loaded.devices["acme-lock"]
    document = {
        "kind": "document-source",
        "schema_version": "0.1",
        "id": "synthetic-manual",
        "title": "Synthetic fixture manual",
        "publisher": "Fixture publisher",
        "url": "https://example.invalid/manual.pdf",
        "document_version": "Synthetic revision",
        "accessed_at": "2026-10-08",
        "source_maturity": "unknown",
        "applicability": {
            "manufacturer": "Acme",
            "model": "Synthetic Lock",
            "scope": "family-context",
            "notes": ["Synthetic test data; no real device or document."],
        },
        "locations": [],
        "capture": {"mode": "link-only"},
        "rights": {"redistribution": "unknown", "notice": "No document included."},
        "contributed_by": "synthetic-author",
        "limitations": ["Synthetic fixture only."],
    }
    document_path = "catalog/documents/synthetic-manual.json"
    write_json(dataset / document_path, document)
    records = [{"id": identifier, **metadata} for identifier, metadata in sorted(loaded.records.items())]
    records.append(
        {
            "id": document["id"],
            "path": document_path,
            "sha256": catalog.digest((dataset / document_path).read_bytes()),
        }
    )
    manifest = {
        "kind": "device-evidence-bundle",
        "schema_version": "0.1",
        "id": "acme-state",
        "version": "0.1.0",
        "title": "Synthetic state evidence",
        "subject": {
            **{key: device[key] for key in ("manufacturer", "model", "protocol", "identifiers")},
            "firmware": "unknown",
            "scope_notes": ["Synthetic fixture; no device execution."],
        },
        "device_record_id": device["id"],
        "author": "synthetic-author",
        "license": "Apache-2.0",
        "publication_status": "candidate",
        "records": records,
        "features": [
            {
                "id": "state",
                "title": "State",
                "summary": "Synthetic evidence only.",
                "record_ids": [row["id"] for row in records],
                "implementation_notes": [],
                "test_plan": [],
                "gaps": ["No reported execution."],
            }
        ],
        "reviews": [],
        "credits": [{"identity": "synthetic-author", "roles": ["author"], "record_ids": [document["id"]]}],
        "history": [{"version": "0.1.0", "summary": "Synthetic fixture."}],
        "limitations": ["No actual document or physical device."],
    }
    write_json(dataset / "catalog/bundles/acme-state.json", manifest)
    return dataset


def file_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file()
    }


def test_no_bundle_catalog_still_builds(dataset: Path, tmp_path: Path) -> None:
    loaded = catalog.load_catalog(dataset)
    index = catalog.build_index(loaded)
    assert index["bundles"] == []
    output = tmp_path / "without-bundles"
    catalog.write_site(loaded, index, output)
    assert not (output / "bundles").exists()
    assert "Versioned evidence packages" not in (output / "index.html").read_text()


def test_catalog_emits_linked_bundle_and_verifiable_deterministic_archive(
    bundled: Path, tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(catalog.requests, "get", lambda *a, **kw: pytest.fail("Implicit network request"))
    loaded = catalog.load_catalog(bundled)
    index = catalog.build_index(loaded)
    summary = index["bundles"][0]
    assert summary["id"] == "acme-state"
    assert summary["version"] == "0.1.0"
    assert summary["device_record_id"] == "acme-lock"
    assert summary["publication_status"] == "candidate"
    first, second = tmp_path / "first", tmp_path / "second"
    catalog.write_site(loaded, index, first)
    catalog.write_site(loaded, index, second)
    assert file_bytes(first) == file_bytes(second)
    archive = first / "bundles/acme-state/bundle.zip"
    assert bundles.verify_package(archive)
    assert 'href="bundles/acme-state/"' in (first / "index.html").read_text()
    assert 'href="../../bundles/acme-state/"' in (first / "devices/acme-lock/index.html").read_text()
    assert (first / "bundles/acme-state/catalog/documents/synthetic-manual.json").is_file()
    assert not list(first.rglob("*.pdf"))


def test_bundle_manifest_affects_catalog_digest_and_rejects_stale_index(
    bundled: Path, tmp_path: Path
) -> None:
    loaded = catalog.load_catalog(bundled)
    original = catalog.build_index(loaded)
    path = bundled / "catalog/bundles/acme-state.json"
    manifest = json.loads(path.read_text())
    manifest["title"] = "A changed explanation"
    write_json(path, manifest)
    changed = catalog.build_index(loaded)
    assert original["input_digest"] != changed["input_digest"]
    assert original["bundles"][0]["input_digest"] != changed["bundles"][0]["input_digest"]
    output = tmp_path / "stale"
    with pytest.raises(catalog.CatalogError, match="changed since"):
        catalog.write_site(loaded, original, output)
    assert not output.exists()


def test_bundle_record_corruption_blocks_catalog_build(bundled: Path) -> None:
    loaded = catalog.load_catalog(bundled)
    path = bundled / "catalog/documents/synthetic-manual.json"
    path.write_text(path.read_text() + "\n")
    with pytest.raises(catalog.CatalogError, match="digest mismatch"):
        catalog.build_index(loaded)


def test_bundle_input_changes_update_catalog_digest(bundled: Path) -> None:
    loaded = catalog.load_catalog(bundled)
    original = catalog.build_index(loaded)
    document = bundled / "catalog/documents/synthetic-manual.json"
    document.write_text(document.read_text() + "\n")
    manifest_path = bundled / "catalog/bundles/acme-state.json"
    manifest = json.loads(manifest_path.read_text())
    next(row for row in manifest["records"] if row["id"] == "synthetic-manual")["sha256"] = catalog.digest(
        document.read_bytes()
    )
    write_json(manifest_path, manifest)
    assert catalog.build_index(loaded)["input_digest"] != original["input_digest"]


def test_bundle_titles_are_escaped_on_catalog_pages(bundled: Path, tmp_path: Path) -> None:
    path = bundled / "catalog/bundles/acme-state.json"
    manifest = json.loads(path.read_text())
    manifest["title"] = '<img src="x" onerror="alert(1)">'
    write_json(path, manifest)
    loaded = catalog.load_catalog(bundled)
    output = tmp_path / "escaped"
    catalog.write_site(loaded, catalog.build_index(loaded), output)
    for relative in ("index.html", "devices/acme-lock/index.html"):
        html = (output / relative).read_text()
        assert manifest["title"] not in html
        assert "&lt;img" in html


def test_generated_bundle_files_are_owned_but_nearby_user_files_are_preserved(
    bundled: Path, tmp_path: Path
) -> None:
    loaded = catalog.load_catalog(bundled)
    index = catalog.build_index(loaded)
    output = tmp_path / "owned"
    catalog.write_site(loaded, index, output)
    catalog.write_site(loaded, index, output)
    user_file = output / "bundles/acme-state/user-notes.txt"
    user_file.write_text("Preserve me")
    with pytest.raises(catalog.CatalogError, match="unrelated file"):
        catalog.write_site(loaded, index, output)
    assert user_file.read_text() == "Preserve me"


def test_removed_bundle_removes_only_previously_generated_files(bundled: Path, tmp_path: Path) -> None:
    loaded = catalog.load_catalog(bundled)
    output = tmp_path / "owned"
    catalog.write_site(loaded, catalog.build_index(loaded), output)
    (bundled / "catalog/bundles/acme-state.json").unlink()
    catalog.write_site(loaded, catalog.build_index(loaded), output)
    assert not list((output / "bundles").rglob("*.*"))
    assert (output / "devices/acme-lock/index.html").is_file()


def test_bundle_output_symlink_is_rejected(bundled: Path, tmp_path: Path) -> None:
    loaded = catalog.load_catalog(bundled)
    target = tmp_path / "target"
    target.mkdir()
    output = tmp_path / "link"
    output.symlink_to(target, target_is_directory=True)
    with pytest.raises(catalog.CatalogError, match="symbolic link"):
        catalog.write_site(loaded, catalog.build_index(loaded), output)
    assert not list(target.iterdir())


def test_bundle_site_respects_combined_output_budget(bundled: Path, tmp_path: Path, monkeypatch) -> None:
    loaded = catalog.load_catalog(bundled)
    index = catalog.build_index(loaded)
    monkeypatch.setattr(
        bundles, "package_files", lambda bundle: {"report.md": b"x" * (32 * catalog.MAX_BYTES + 1)}
    )
    output = tmp_path / "too-large"
    with pytest.raises(catalog.CatalogError, match="32 MiB output budget"):
        catalog.write_site(loaded, index, output)
    assert not output.exists()


@pytest.mark.parametrize(
    "relative",
    [
        "bundles/acme-state/custom.js",
        "bundles/acme-state/schema/arbitrary.schema.json",
        "bundles/acme-state/catalog/documents/../../kept.json",
    ],
)
def test_forged_bundle_output_marker_cannot_expand_ownership(
    bundled: Path, tmp_path: Path, relative: str
) -> None:
    loaded = catalog.load_catalog(bundled)
    index = catalog.build_index(loaded)
    output = tmp_path / "forged"
    output.mkdir()
    write_json(output / ".edgeloom-catalog-output.json", {"files": [relative]})
    with pytest.raises(catalog.CatalogError):
        catalog.write_site(loaded, index, output)
    assert not (output / "index.html").exists()
