"""Catalog joins, explicit fetch policy, output ownership and report boundaries."""

from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from edgeloom import catalog, schemas
from edgeloom.cli import main


def write_document(path: Path, document: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")


@pytest.fixture
def dataset(tmp_path: Path, repo_root: Path) -> Path:
    root = tmp_path / "dataset"
    fixtures = repo_root / "tests/fixtures/catalog"
    mapping = schemas.load_document(fixtures / "lock-mapping-set.yaml")
    for reference, filename in zip(
        mapping["source_manifests"], ["smartthings-source.yaml", "onedm-source.yaml"], strict=True
    ):
        reference["path"] = f"catalog/sources/{filename}"
        target = root / reference["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(fixtures / filename, target)
        reference["sha256"] = catalog.digest(target.read_bytes())
    write_document(root / "catalog/mappings/lock.yaml", mapping)
    device = {
        "kind": "catalog-device",
        "schema_version": "0.1",
        "id": "acme-lock",
        "manufacturer": "Acme",
        "model": "Synthetic Lock",
        "protocol": "zwave",
        "identifiers": {"manufacturer_id": "0x0001", "product_type": "0x0002", "product_id": "0x0003"},
        "identity_evidence": {
            "manifest_id": "smartthings-lock-fixture",
            "artifact_id": "zwave-lock-fingerprints",
            "locator": "/zwaveManufacturer/0",
        },
        "firmware": "Unknown; synthetic fixture",
        "hardware_evidence": [],
        "features": [
            {
                "id": "state",
                "title": "Lock-state events",
                "summary": "Synthetic bounded evidence, not hardware behavior.",
                "mapping_ids": [mapping["id"]],
                "next_steps": ["Inspect the pinned sources."],
            }
        ],
        "limitations": ["Synthetic data only; no hardware or independent review."],
    }
    write_document(root / "catalog/devices/acme.yaml", device)
    return root


def repin(root: Path) -> None:
    mapping_path = root / "catalog/mappings/lock.yaml"
    mapping = schemas.load_document(mapping_path)
    for reference in mapping["source_manifests"]:
        reference["sha256"] = catalog.digest((root / reference["path"]).read_bytes())
    write_document(mapping_path, mapping)


def prepare_fetch(root: Path) -> bytes:
    payload = b'{"components":[{"capabilities":[]}],"zwaveManufacturer":[]}\n'
    for path in (root / "catalog/sources").glob("*.yaml"):
        source = schemas.load_document(path)
        source["repository"]["url"] = f"https://github.com/acme/{source['id']}"
        for artifact in source["artifacts"]:
            artifact["sha256"] = catalog.digest(payload)
        write_document(path, source)
    repin(root)
    return payload


def test_offline_check_and_build_never_fetch(dataset: Path, tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        catalog.requests, "get", lambda *args, **kwargs: pytest.fail("Implicit network access")
    )
    assert main(["catalog", "check", str(dataset)]) == 0
    first, second = tmp_path / "first", tmp_path / "second"
    assert main(["catalog", "build", str(dataset), "--output", str(first)]) == 0
    assert main(["catalog", "build", str(dataset), "--output", str(second)]) == 0
    for path in first.rglob("*"):
        if path.is_file():
            assert path.read_bytes() == (second / path.relative_to(first)).read_bytes()
    index = json.loads((first / "catalog.json").read_text())
    assert index["counts"]["devices"] == 1
    assert index["checks"]["source_bytes"] == "not-checked"
    assert all(item["review"]["lifecycle"] == "candidate" for item in index["mapping_sets"])
    assert index["devices"][0]["hardware_evidence"] == []
    assert "Source bytes: not-checked" in capsys.readouterr().out
    assert "not a compatibility" in (first / "reports/acme-lock.md").read_text()


def test_manifest_bytes_are_recomputed(dataset: Path) -> None:
    source = dataset / "catalog/sources/smartthings-source.yaml"
    source.write_text(source.read_text() + "\n# changed\n")
    with pytest.raises(catalog.CatalogError, match="digest mismatch"):
        catalog.load_catalog(dataset)


@pytest.mark.parametrize(
    "change, message",
    [
        ("artifact", "Unknown artifact"),
        ("source-path", "not indexed"),
        ("source-id", "identity mismatch"),
        ("layer", "layer mismatch"),
    ],
)
def test_cross_record_errors(dataset: Path, change: str, message: str) -> None:
    path = dataset / "catalog/mappings/lock.yaml"
    mapping = schemas.load_document(path)
    if change == "artifact":
        mapping["nodes"][0]["artifact"]["artifact_id"] = "does-not-exist"
    elif change == "source-path":
        mapping["source_manifests"][0]["path"] = "catalog/sources/missing.yaml"
    elif change == "source-id":
        source_path = dataset / mapping["source_manifests"][0]["path"]
        source = schemas.load_document(source_path)
        source["id"] = "different-id"
        write_document(source_path, source)
        mapping["source_manifests"][0]["sha256"] = catalog.digest(source_path.read_bytes())
    else:
        source_path = dataset / mapping["source_manifests"][0]["path"]
        source = schemas.load_document(source_path)
        source["artifacts"][0]["layer"] = "platform-exposure"
        write_document(source_path, source)
        mapping["source_manifests"][0]["sha256"] = catalog.digest(source_path.read_bytes())
    write_document(path, mapping)
    with pytest.raises(catalog.CatalogError, match=message):
        catalog.load_catalog(dataset)


def test_device_mapping_and_feature_identity(dataset: Path) -> None:
    path = dataset / "catalog/devices/acme.yaml"
    device = schemas.load_document(path)
    device["features"][0]["mapping_ids"] = ["missing-mapping"]
    write_document(path, device)
    with pytest.raises(catalog.CatalogError, match="unknown mapping"):
        catalog.load_catalog(dataset)
    device["features"].append(copy.deepcopy(device["features"][0]))
    write_document(path, device)
    with pytest.raises(catalog.CatalogError, match="duplicate id"):
        catalog.load_catalog(dataset)


def test_unknown_device_is_not_inferred(dataset: Path, tmp_path: Path) -> None:
    (dataset / "catalog/devices/acme.yaml").unlink()
    assert main(["catalog", "check", str(dataset)]) == 0
    assert main(["catalog", "build", str(dataset), "--output", str(tmp_path / "view")]) == 1


@pytest.mark.parametrize("bad_id", ["../escape", "UPPERCASE", "a/b", "a#fragment"])
def test_device_ids_cannot_escape_output(dataset: Path, bad_id: str) -> None:
    path = dataset / "catalog/devices/acme.yaml"
    device = schemas.load_document(path)
    device["id"] = bad_id
    write_document(path, device)
    assert main(["catalog", "check", str(dataset)]) == 1


def test_symlinks_and_size_are_rejected(dataset: Path) -> None:
    target = dataset / "catalog/devices/link.yaml"
    target.symlink_to(dataset / "catalog/devices/acme.yaml")
    with pytest.raises(catalog.CatalogError, match="symbolic link"):
        catalog.load_catalog(dataset)
    target.unlink()
    target.write_bytes(b"x" * (catalog.MAX_BYTES + 1))
    with pytest.raises(catalog.CatalogError, match="exceeds"):
        catalog.load_catalog(dataset)


@pytest.mark.parametrize("relative", ["../x", "/x", "a//b", "a/./b", "a/.git/x", "C:/x", "a\\b"])
def test_paths_fail_closed(tmp_path: Path, relative: str) -> None:
    with pytest.raises(catalog.CatalogError):
        catalog.read_bytes(tmp_path, relative)


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="Named pipes are unavailable on this platform")
def test_cache_reader_rejects_a_fifo_without_blocking(tmp_path: Path) -> None:
    os.mkfifo(tmp_path / "pipe")
    with pytest.raises(catalog.CatalogError, match="regular file"):
        catalog.read_bytes(tmp_path, "pipe")


def test_changed_core_pin_cannot_claim_clean_catalog_revision(tmp_path: Path) -> None:
    for arguments in (
        ("init", str(tmp_path)),
        ("-C", str(tmp_path), "config", "user.name", "Catalog test"),
        ("-C", str(tmp_path), "config", "user.email", "test@example.invalid"),
    ):
        subprocess.run(["git", *arguments], check=True, capture_output=True)
    pin = tmp_path / "CORE_REVISION"
    pin.write_text("a" * 40 + "\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "CORE_REVISION"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-m", "Fixture"], check=True, capture_output=True)
    assert catalog.catalog_revision(tmp_path) != "working-tree"
    pin.write_text("b" * 40 + "\n")
    assert catalog.catalog_revision(tmp_path) == "working-tree"


def test_output_ownership_and_idempotence(dataset: Path, tmp_path: Path) -> None:
    loaded = catalog.load_catalog(dataset)
    index = catalog.build_index(loaded)
    output = tmp_path / "view"
    catalog.write_site(loaded, index, output)
    original = (output / "catalog.json").read_bytes()
    catalog.write_site(loaded, index, output)
    assert (output / "catalog.json").read_bytes() == original
    (output / "user-file.txt").write_text("Preserve me")
    with pytest.raises(catalog.CatalogError, match="unrelated file"):
        catalog.write_site(loaded, index, output)
    assert (output / "user-file.txt").read_text() == "Preserve me"
    with pytest.raises(catalog.CatalogError, match="overwrite catalog"):
        catalog.write_site(loaded, index, dataset)


def test_nonempty_output_is_not_adopted(dataset: Path, tmp_path: Path) -> None:
    output = tmp_path / "user-output"
    output.mkdir()
    (output / "index.html").write_text("User page")
    assert main(["catalog", "build", str(dataset), "--output", str(output)]) == 1
    assert (output / "index.html").read_text() == "User page"


class Response:
    def __init__(self, payload: bytes, status: int = 200):
        self.payload = payload
        self.status_code = status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def iter_content(self, chunk_size):
        yield self.payload


def test_explicit_fetch_digest_cache_and_corruption(dataset: Path, tmp_path: Path, monkeypatch) -> None:
    payload = prepare_fetch(dataset)
    calls = []

    def get(url, **kwargs):
        calls.append(url)
        assert kwargs["allow_redirects"] is False
        assert (
            "/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/" in url
            or "/dddddddddddddddddddddddddddddddddddddddd/" in url
        )
        return Response(payload)

    monkeypatch.setattr(catalog.requests, "get", get)
    cache = tmp_path / "cache"
    loaded = catalog.load_catalog(dataset)
    catalog.fetch_sources(loaded, cache)
    assert calls
    assert catalog.build_index(loaded, cache)["checks"]["source_bytes"] == "matched"
    cached = cache / catalog.digest(payload)
    assert cached.read_bytes() == payload
    calls.clear()
    catalog.fetch_sources(loaded, cache)
    assert not calls
    cached.write_bytes(b"tampered")
    with pytest.raises(catalog.CatalogError, match="digest mismatch"):
        catalog.build_index(loaded, cache)


@pytest.mark.parametrize(
    "payload,status,message",
    [
        (b"wrong", 200, "digest mismatch"),
        (b"", 302, "HTTP 302"),
        (b"x" * (catalog.MAX_BYTES + 1), 200, "exceeds"),
    ],
)
def test_fetch_rejects_bad_bytes_and_redirects(
    dataset: Path, tmp_path: Path, monkeypatch, payload, status, message
) -> None:
    prepare_fetch(dataset)
    monkeypatch.setattr(catalog.requests, "get", lambda *args, **kwargs: Response(payload, status))
    cache = tmp_path / "cache"
    with pytest.raises(catalog.CatalogError, match=message):
        catalog.fetch_sources(catalog.load_catalog(dataset), cache)
    assert not list(cache.iterdir())


def test_fetch_rejects_non_github_before_network(dataset: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(catalog.requests, "get", lambda *args, **kwargs: pytest.fail("Network called"))
    with pytest.raises(catalog.CatalogError, match="public github.com"):
        catalog.fetch_sources(catalog.load_catalog(dataset), tmp_path / "cache")


def test_locator_checks_do_not_verify_semantics() -> None:
    artifact = {"path": "artifact.json", "media_type": "application/json"}
    payload = b'{"a/b": {"~key": [null]}, "enum": ["Locked", "Unlocked"]}'
    assert catalog._locator_status(payload, artifact, "/a~1b/~0key/0") == "resolved"
    assert catalog._locator_status(payload, artifact, "/missing") == "not-found"
    assert catalog._locator_status(payload, artifact, "/enum/[id=lock]") == "manual-review"
    assert catalog._locator_status(payload, artifact, "lua:function migrate") == "manual-review"
    assert catalog._locator_status(None, artifact, "/enum") == "not-checked"


def test_author_text_is_escaped_in_html_and_markdown(dataset: Path, tmp_path: Path) -> None:
    path = dataset / "catalog/devices/acme.yaml"
    device = schemas.load_document(path)
    device["model"] = '<script>alert("x")</script>'
    device["features"][0]["summary"] = "[unsafe](javascript:alert(1)) <img src=x>"
    write_document(path, device)
    assert main(["catalog", "build", str(dataset), "--output", str(tmp_path / "view")]) == 0
    html = (tmp_path / "view/devices/acme-lock/index.html").read_text()
    assert '<script>alert("x")</script>' not in html
    assert "&lt;script&gt;" in html
    markdown = (tmp_path / "view/reports/acme-lock.md").read_text()
    assert "[unsafe](javascript:" not in markdown


@pytest.fixture
def corroborated(dataset: Path) -> Path:
    loaded = catalog.load_catalog(dataset)
    sources = list(loaded.sources.values())
    first = sources[0]
    reference = {"manifest_id": first["id"], "artifact_id": first["artifacts"][0]["id"], "locator": "/value"}
    record = {
        "kind": schemas.CATALOG_CORROBORATION,
        "schema_version": "0.1",
        "id": "acme-comparison",
        "device_id": "acme-lock",
        "feature_id": "state",
        "title": "Synthetic comparison",
        "summary": "Keep competing declarations visible.",
        "source_manifests": [{"id": source["id"], **loaded.records[source["id"]]} for source in sources],
        "lineage": [
            {
                "manifest_id": source["id"],
                "family": "shared-backend",
                "depends_on": [sources[0]["id"]] if index else [],
            }
            for index, source in enumerate(sources)
        ],
        "observations": [
            {
                "id": "generic",
                "platform": "Synthetic platform",
                "scope": "platform-generic",
                "evidence_kind": "code-declaration",
                "relationship": "context",
                "claim": "Generic code is not device validation.",
                "references": [reference],
                "conditions": ["No real device observation."],
            }
        ],
        "review": {"lifecycle": "candidate", "author": "synthetic-author", "reviewers": []},
        "limitations": ["Synthetic comparison; no independent review."],
    }
    write_document(dataset / "catalog/corroboration/comparison.yaml", record)
    path = dataset / "catalog/devices/acme.yaml"
    device = schemas.load_document(path)
    device["features"][0]["corroboration_ids"] = [record["id"]]
    write_document(path, device)
    return dataset


@pytest.mark.parametrize(
    "mutation, message",
    [
        ("missing-source", "not indexed"),
        ("manifest-digest", "digest mismatch"),
        ("manifest-id", "identity mismatch"),
        ("undeclared-artifact", "undeclared source"),
        ("unknown-artifact", "Unknown artifact"),
        ("feature", "association mismatch"),
        ("orphan", "unknown corroboration"),
        ("cycle", "cyclic source"),
        ("missing-lineage", "cover exactly"),
        ("unknown-dependency", "cover exactly"),
        ("duplicate-lineage", "duplicate id"),
        ("duplicate-observation", "duplicate id"),
        ("identity", "identity match differs"),
        ("unknown-identity-key", "identity match differs"),
        ("review-upgrade", "candidate"),
        ("path-traversal", "segments"),
    ],
)
def test_corroboration_integrity(corroborated: Path, mutation: str, message: str) -> None:
    path = corroborated / "catalog/corroboration/comparison.yaml"
    record = schemas.load_document(path)
    if mutation == "missing-source":
        record["source_manifests"][0]["path"] = "catalog/sources/missing.yaml"
    elif mutation == "manifest-digest":
        record["source_manifests"][0]["sha256"] = "0" * 64
    elif mutation == "manifest-id":
        record["source_manifests"][0]["id"] = "wrong-source"
    elif mutation == "undeclared-artifact":
        record["observations"][0]["references"][0]["manifest_id"] = "not-declared"
    elif mutation == "unknown-artifact":
        record["observations"][0]["references"][0]["artifact_id"] = "not-present"
    elif mutation == "feature":
        record["feature_id"] = "different-feature"
    elif mutation == "orphan":
        record["id"] = "different-record"
    elif mutation == "cycle":
        record["lineage"][0]["depends_on"] = [record["lineage"][1]["manifest_id"]]
    elif mutation == "missing-lineage":
        record["lineage"].pop()
    elif mutation == "unknown-dependency":
        record["lineage"][0]["depends_on"] = ["unknown-source"]
    elif mutation == "duplicate-lineage":
        record["lineage"].append(copy.deepcopy(record["lineage"][0]))
    elif mutation == "duplicate-observation":
        record["observations"].append(copy.deepcopy(record["observations"][0]))
    elif mutation in {"identity", "unknown-identity-key"}:
        observation = record["observations"][0]
        observation["scope"] = "device-model"
        observation["identity_evidence"] = copy.deepcopy(observation["references"][0])
        observation["identity_match"] = (
            {"product_id": "0x9999"} if mutation == "identity" else {"model": "Synthetic Lock"}
        )
    elif mutation == "review-upgrade":
        record["review"]["lifecycle"] = "verified"
    else:
        record["source_manifests"][0]["path"] = "catalog/sources/../sources/file.yaml"
    write_document(path, record)
    with pytest.raises(catalog.CatalogError, match=message):
        catalog.load_catalog(corroborated)


def test_corroboration_only_feature_and_conflicts_survive(
    corroborated: Path, tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(catalog.requests, "get", lambda *args, **kwargs: pytest.fail("Implicit network"))
    path = corroborated / "catalog/devices/acme.yaml"
    device = schemas.load_document(path)
    device["features"][0]["mapping_ids"] = []
    write_document(path, device)
    path = corroborated / "catalog/corroboration/comparison.yaml"
    record = schemas.load_document(path)
    conflicting = copy.deepcopy(record["observations"][0])
    conflicting.update(id="conflicting", relationship="conflicts", claim="A contrary source declaration.")
    record["observations"].append(conflicting)
    write_document(path, record)
    original = path.read_bytes()
    loaded = catalog.load_catalog(corroborated)
    index = catalog.build_index(loaded)
    assert index == catalog.build_index(loaded)
    assert index["counts"]["corroboration_records"] == 1
    assert index["counts"]["source_observations"] == 2
    assert index["corroborations"][0]["review"]["lifecycle"] == "candidate"
    assert index["corroborations"][0]["lineage"] == record["lineage"]
    assert all(item["review"]["lifecycle"] == "candidate" for item in index["mapping_sets"])
    assert index["devices"][0]["hardware_evidence"] == []
    assert "independent_sources" not in index["counts"]
    catalog.write_site(loaded, index, tmp_path / "view")
    html = (tmp_path / "view/devices/acme-lock/index.html").read_text()
    report = (tmp_path / "view/reports/acme-lock.md").read_text()
    for text in (html, report):
        text = text.replace("\\", "")
        assert "A contrary source declaration." in text
        assert "conflicts" in text
        assert "not an independence score" in text
        assert "shared-backend" in text
    assert path.read_bytes() == original


def test_corroboration_identity_and_generic_scope(corroborated: Path) -> None:
    path = corroborated / "catalog/corroboration/comparison.yaml"
    record = schemas.load_document(path)
    observation = record["observations"][0]
    observation["identity_match"] = {"product_id": "0x0003"}
    write_document(path, record)
    with pytest.raises(catalog.CatalogError):
        catalog.load_catalog(corroborated)  # Generic paths must not claim a device match.
    observation["scope"] = "device-model"
    observation["identity_evidence"] = copy.deepcopy(observation["references"][0])
    write_document(path, record)
    catalog.load_catalog(corroborated)
    assert schemas.detect_kind({**record, "kind": "misspelled"}) == schemas.CATALOG_CORROBORATION


def test_corroboration_escapes_author_content(corroborated: Path, tmp_path: Path) -> None:
    path = corroborated / "catalog/corroboration/comparison.yaml"
    record = schemas.load_document(path)
    record["observations"][0]["claim"] = '<img src=x onerror="alert(1)"> [x](javascript:alert(1))'
    write_document(path, record)
    loaded = catalog.load_catalog(corroborated)
    catalog.write_site(loaded, catalog.build_index(loaded), tmp_path / "view")
    html = (tmp_path / "view/devices/acme-lock/index.html").read_text()
    assert '<img src=x onerror="alert(1)">' not in html
    assert "&lt;img" in html
    assert "[x](javascript:" not in (tmp_path / "view/reports/acme-lock.md").read_text()


def test_feature_needs_evidence_reference(dataset: Path) -> None:
    path = dataset / "catalog/devices/acme.yaml"
    device = schemas.load_document(path)
    device["features"][0]["mapping_ids"] = []
    write_document(path, device)
    with pytest.raises(catalog.CatalogError, match="needs a mapping or corroboration"):
        catalog.load_catalog(dataset)
