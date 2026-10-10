"""Synthetic media fixtures: declarations only, never a physical device test."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import jsonschema
import pytest
from test_bundles import reseal, write_zip
from test_catalog_bundles import bundled as bundled
from test_catalog_bundles import file_bytes, write_json
from test_catalog_pipeline import dataset as dataset

from edgeloom import bundles, catalog, schemas


@pytest.fixture
def media(bundled: Path) -> Path:
    loaded = catalog.load_catalog(bundled)
    device = copy.deepcopy(loaded.devices["acme-lock"])
    device.update(
        id="acme-tv",
        model="Synthetic TV family",
        protocol="ip",
        schema_version="0.2",
        identity_scope="device-family",
        category="media",
        identifiers={"family": "Synthetic TV"},
    )
    device["features"][0]["mapping_ids"] = []
    device["features"][0]["source_references"] = [device["identity_evidence"]]
    device["connections"] = [
        {
            "id": "adapter",
            "transports": ["unknown"],
            "application_protocol": "synthetic-api",
            "platform": "Synthetic platform",
            "integration": "fixture",
            "platform_version": "1",
            "access": "local",
            "data_updates": "push",
            "basis": "source-declared",
            "references": [device["identity_evidence"]],
            "limitations": ["Synthetic declarations only."],
        }
    ]
    path = bundled / "catalog/devices/tv.json"
    write_json(path, device)
    manifest = json.loads((bundled / "catalog/bundles/acme-state.json").read_text())
    manifest.update(id="acme-tv-state", schema_version="0.2", device_record_id="acme-tv")
    manifest["subject"] = {
        key: device[key]
        for key in ("manufacturer", "model", "protocol", "identity_scope", "identifiers", "firmware")
    }
    manifest["subject"]["scope_notes"] = ["Synthetic family only, no exact model."]
    source_id = device["identity_evidence"]["manifest_id"]
    manifest["records"] = [
        {"id": source_id, **loaded.records[source_id]},
        {"id": device["id"], "path": "catalog/devices/tv.json", "sha256": catalog.digest(path.read_bytes())},
    ]
    manifest["features"][0]["record_ids"] = [source_id, device["id"]]
    manifest["credits"][0]["record_ids"] = [device["id"]]
    write_json(bundled / "catalog/bundles/acme-tv-state.json", manifest)
    return bundled


def update_device(root: Path, device: dict) -> None:
    path = root / "catalog/devices/tv.json"
    write_json(path, device)
    bundle_path = root / "catalog/bundles/acme-tv-state.json"
    manifest = json.loads(bundle_path.read_text())
    manifest["records"][1]["sha256"] = catalog.digest(path.read_bytes())
    write_json(bundle_path, manifest)


def test_versioned_schemas_are_valid_and_legacy_remains_separate() -> None:
    for kind in schemas.VERSIONED_KINDS:
        jsonschema.Draft202012Validator.check_schema(schemas.load_schema(kind, "0.2"))
        assert schemas.load_schema(kind)["properties"]["schema_version"] == {"const": "0.1"}
        assert schemas.schema_path(kind) != schemas.schema_path(kind, "0.2")


@pytest.mark.parametrize("version", ["0.3", "../../profile", None, {}, []])
def test_unknown_version_fails_closed(media: Path, version) -> None:
    doc = schemas.load_document(media / "catalog/devices/tv.json")
    doc["schema_version"] = version
    assert "schema_version" in schemas.validation_errors(doc, kind=schemas.CATALOG_DEVICE)[0]


@pytest.mark.parametrize(
    "field,value",
    [
        ("basis", "hardware-tested"),
        ("transports", ["unknown", "wifi"]),
        ("references", []),
        ("access", "certified"),
    ],
)
def test_connection_boundaries(media: Path, field: str, value) -> None:
    doc = schemas.load_document(media / "catalog/devices/tv.json")
    doc["connections"][0][field] = value
    assert schemas.validation_errors(doc, kind=schemas.CATALOG_DEVICE)


def test_private_identifiers_and_unscoped_family_are_rejected(media: Path) -> None:
    doc = schemas.load_document(media / "catalog/devices/tv.json")
    for identifiers in ({"ip": "192.0.2.1"}, {"serial": "private"}, {"model": "unknown"}):
        doc["identifiers"] = identifiers
        assert schemas.validation_errors(doc, kind=schemas.CATALOG_DEVICE)


@pytest.mark.parametrize("missing", ["manifest_id", "artifact_id"])
def test_connection_references_checked_in_both_loaders(media: Path, missing: str) -> None:
    doc = schemas.load_document(media / "catalog/devices/tv.json")
    doc["connections"][0]["references"][0][missing] = "missing"
    update_device(media, doc)
    with pytest.raises(catalog.CatalogError):
        catalog.load_catalog(media)
    with pytest.raises(bundles.BundleError):
        bundles.load_bundle(media, "acme-tv-state")


def test_family_cannot_be_presented_as_exact_model(media: Path) -> None:
    path = media / "catalog/bundles/acme-tv-state.json"
    doc = json.loads(path.read_text())
    doc["subject"]["identity_scope"] = "exact-model"
    write_json(path, doc)
    with pytest.raises(bundles.BundleError, match="identity scope mismatch"):
        bundles.load_bundle(media, "acme-tv-state")


def test_duplicate_connection_ids_rejected(media: Path) -> None:
    doc = schemas.load_document(media / "catalog/devices/tv.json")
    doc["connections"].append(copy.deepcopy(doc["connections"][0]))
    update_device(media, doc)
    with pytest.raises(catalog.CatalogError, match="duplicate connection"):
        catalog.load_catalog(media)
    with pytest.raises(bundles.BundleError, match="duplicate connection"):
        bundles.load_bundle(media, "acme-tv-state")


def test_mixed_versions_render_and_package_offline(media: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(catalog.requests, "get", lambda *a, **k: pytest.fail("Unexpected network"))
    loaded = catalog.load_catalog(media)
    index = catalog.build_index(loaded)
    first, second = tmp_path / "first", tmp_path / "second"
    catalog.write_site(loaded, index, first)
    catalog.write_site(loaded, index, second)
    assert file_bytes(first) == file_bytes(second)
    home = (first / "index.html").read_text()
    assert '<option value="ip">IP / API</option>' in home
    assert "Device-family scope" in home
    for identifier in ("acme-state", "acme-tv-state"):
        assert bundles.verify_package(first / f"bundles/{identifier}/bundle.zip")
    package = first / "bundles/acme-tv-state"
    assert (package / "schema/catalog-device.v0.2.schema.json").is_file()
    assert (package / "schema/device-evidence-bundle.v0.2.schema.json").is_file()
    assert not (package / "schema/catalog-device.schema.json").exists()
    for name in ("index.html", "report.md"):
        content = (package / name).read_text()
        assert "Declared integration context" in content
        assert "source-declared" in content
    assert "source-declared" in (first / "devices/acme-tv/index.html").read_text()


def test_connection_text_escaped(media: Path, tmp_path: Path) -> None:
    doc = schemas.load_document(media / "catalog/devices/tv.json")
    doc["connections"][0]["application_protocol"] = '<script>alert("x")</script>'
    update_device(media, doc)
    loaded = catalog.load_catalog(media)
    output = tmp_path / "escaped"
    catalog.write_site(loaded, catalog.build_index(loaded), output)
    for path in (output / "devices/acme-tv/index.html", output / "bundles/acme-tv-state/index.html"):
        assert '<script>alert("x")</script>' not in path.read_text()
        assert "&lt;script&gt;" in path.read_text()


@pytest.mark.parametrize("protocol", ["zigbee", "zwave", "ip", "matter", "other", "unknown"])
def test_family_and_exact_model_identifier_boundaries(media: Path, protocol: str) -> None:
    doc = schemas.load_document(media / "catalog/devices/tv.json")
    doc["protocol"] = protocol
    assert not schemas.validation_errors(doc, kind=schemas.CATALOG_DEVICE)
    doc["identity_scope"] = "exact-model"
    assert schemas.validation_errors(doc, kind=schemas.CATALOG_DEVICE)


def test_source_only_feature_cannot_drop_or_forge_references(media: Path) -> None:
    doc = schemas.load_document(media / "catalog/devices/tv.json")
    doc["features"][0]["source_references"] = []
    assert schemas.validation_errors(doc, kind=schemas.CATALOG_DEVICE)
    doc["features"][0]["source_references"] = [dict(doc["identity_evidence"], artifact_id="missing")]
    update_device(media, doc)
    with pytest.raises(catalog.CatalogError):
        catalog.load_catalog(media)
    with pytest.raises(bundles.BundleError):
        bundles.load_bundle(media, "acme-tv-state")


@pytest.mark.parametrize("target", ["catalog-device", "device-evidence-bundle"])
def test_resealed_v02_schema_swap_rejected(media: Path, tmp_path: Path, target: str) -> None:
    files = bundles.package_files(bundles.load_bundle(media, "acme-tv-state"))
    files[f"schema/{target}.v0.2.schema.json"] = b"{}\n"
    reseal(files)
    output = tmp_path / "forged.zip"
    write_zip(output, files)
    with pytest.raises(bundles.BundleError, match="Schema snapshot differs"):
        bundles.verify_package(output)
