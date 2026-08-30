"""Public-contract tests for federated catalog source and mapping records."""

from __future__ import annotations

import copy
import hashlib
from pathlib import Path

import pytest
import yaml

from edgeloom import schemas
from edgeloom.cli import main


@pytest.fixture
def catalog_fixtures(repo_root: Path) -> Path:
    return repo_root / "tests" / "fixtures" / "catalog"


@pytest.fixture
def source_manifest(catalog_fixtures: Path) -> dict:
    return schemas.load_document(catalog_fixtures / "smartthings-source.yaml")


@pytest.fixture
def mapping_set(catalog_fixtures: Path) -> dict:
    return schemas.load_document(catalog_fixtures / "lock-mapping-set.yaml")


def _write(tmp_path: Path, name: str, document: dict) -> Path:
    path = tmp_path / name
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    return path


def _validate(tmp_path: Path, document: dict) -> schemas.ValidationResult:
    return schemas.validate_document(_write(tmp_path, "contract.yaml", document))


def test_catalog_fixtures_are_valid_and_autodetected(catalog_fixtures: Path) -> None:
    expected = {
        "smartthings-source.yaml": schemas.SOURCE_MANIFEST,
        "onedm-source.yaml": schemas.SOURCE_MANIFEST,
        "lock-mapping-set.yaml": schemas.CATALOG_MAPPING_SET,
    }

    for name, kind in expected.items():
        result = schemas.validate_document(catalog_fixtures / name)
        assert result.kind == kind
        assert result.ok, result.errors


def test_cli_validates_catalog_contracts(
    catalog_fixtures: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["validate", str(catalog_fixtures), "-v"]) == 0
    output = capsys.readouterr().out
    assert "source-manifest" in output
    assert "catalog-mapping-set" in output
    assert "3 document(s) checked, 0 failed" in output


def test_fixture_manifest_references_pin_the_fixture_bytes(repo_root: Path, mapping_set: dict) -> None:
    """Keep the illustrative lockfile internally reproducible as it evolves."""
    for reference in mapping_set["source_manifests"]:
        payload = (repo_root / reference["path"]).read_bytes()
        assert hashlib.sha256(payload).hexdigest() == reference["sha256"]


@pytest.mark.parametrize(
    "mutable_ref",
    [
        "main",
        "v0.1.0",
        "abc1234",
        "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
    ],
)
def test_source_manifest_rejects_mutable_or_noncanonical_git_refs(
    tmp_path: Path,
    source_manifest: dict,
    mutable_ref: str,
) -> None:
    source_manifest["repository"]["commit"] = mutable_ref

    result = _validate(tmp_path, source_manifest)

    assert not result.ok
    assert any("commit" in error for error in result.errors)


@pytest.mark.parametrize("bad_path", ["/absolute/profile.yml", "../profile.yml", "a//b.yml", r"a\b.yml"])
def test_source_manifest_rejects_unsafe_repository_paths(
    tmp_path: Path,
    source_manifest: dict,
    bad_path: str,
) -> None:
    source_manifest["artifacts"][0]["path"] = bad_path
    assert not _validate(tmp_path, source_manifest).ok


def test_source_manifest_requires_sha256_and_license_provenance(
    tmp_path: Path,
    source_manifest: dict,
) -> None:
    source_manifest["artifacts"][0]["sha256"] = "short"
    source_manifest["artifacts"][1]["license"].pop("evidence_path")

    result = _validate(tmp_path, source_manifest)

    assert not result.ok
    assert any("sha256" in error for error in result.errors)
    assert any("evidence_path" in error for error in result.errors)


def test_source_maturity_rejects_review_lifecycle_terms(
    tmp_path: Path,
    source_manifest: dict,
) -> None:
    source_manifest["artifacts"][0]["source_maturity"] = "verified"
    result = _validate(tmp_path, source_manifest)
    assert not result.ok
    assert any("source_maturity" in error for error in result.errors)


def test_source_manifest_rejects_duplicate_artifact_ids(
    tmp_path: Path,
    source_manifest: dict,
) -> None:
    duplicate = copy.deepcopy(source_manifest["artifacts"][0])
    duplicate["description"] = "Different content, same stable ID."
    source_manifest["artifacts"].append(duplicate)

    result = _validate(tmp_path, source_manifest)

    assert not result.ok
    assert "artifacts: duplicate id 'zwave-lock-fingerprints'" in result.errors


def test_mapping_set_requires_all_three_layers(tmp_path: Path, mapping_set: dict) -> None:
    mapping_set["nodes"] = [
        node for node in mapping_set["nodes"] if node["layer"] != "neutral-sdf-representation"
    ]
    result = _validate(tmp_path, mapping_set)
    assert not result.ok
    assert "nodes: missing required layer 'neutral-sdf-representation'" in result.errors


def test_review_lifecycle_rejects_source_maturity_terms(tmp_path: Path, mapping_set: dict) -> None:
    mapping_set["review"]["lifecycle"] = "experimental"
    result = _validate(tmp_path, mapping_set)
    assert not result.ok
    assert any("lifecycle" in error for error in result.errors)


@pytest.mark.parametrize("lifecycle", ["reviewed", "verified", "deprecated"])
def test_non_candidate_review_requires_reviewer_and_timestamp(
    tmp_path: Path,
    mapping_set: dict,
    lifecycle: str,
) -> None:
    mapping_set["review"]["lifecycle"] = lifecycle
    result = _validate(tmp_path, mapping_set)
    assert not result.ok
    assert any("reviewers" in error or "reviewed_at" in error for error in result.errors)


def test_mapping_set_rejects_duplicate_node_ids(tmp_path: Path, mapping_set: dict) -> None:
    duplicate = copy.deepcopy(mapping_set["nodes"][0])
    duplicate["label"] = "Different assertion, same stable ID"
    mapping_set["nodes"].append(duplicate)

    result = _validate(tmp_path, mapping_set)

    assert not result.ok
    assert "nodes: duplicate id 'device.lock-state'" in result.errors


def test_mapping_set_rejects_unknown_internal_references(tmp_path: Path, mapping_set: dict) -> None:
    mapping_set["nodes"][0]["artifact"]["manifest_id"] = "missing-manifest"
    mapping_set["mappings"][0]["to"] = "missing-node"
    mapping_set["mappings"][0]["evidence_refs"] = ["missing-evidence"]

    result = _validate(tmp_path, mapping_set)

    assert not result.ok
    assert any("unknown source manifest" in error for error in result.errors)
    assert any("unknown node" in error for error in result.errors)
    assert any("unknown evidence" in error for error in result.errors)


def test_unbound_mapping_requires_reason_and_forbids_target(tmp_path: Path, mapping_set: dict) -> None:
    unbound = mapping_set["mappings"][2]
    unbound.pop("unbound_reason")
    unbound["to"] = "platform.lock-state"

    result = _validate(tmp_path, mapping_set)

    assert not result.ok
    assert any("unbound_reason" in error for error in result.errors)
    assert any("unbound mapping must not declare a target node" in error for error in result.errors)


def test_bound_mapping_requires_target_and_forbids_unbound_reason(
    tmp_path: Path,
    mapping_set: dict,
) -> None:
    bound = mapping_set["mappings"][0]
    bound.pop("to")
    bound["unbound_reason"] = "insufficient-evidence"

    result = _validate(tmp_path, mapping_set)

    assert not result.ok
    assert any("'to' is a required property" in error for error in result.errors)
    assert any("unbound_reason" in error for error in result.errors)


def test_lossy_mapping_requires_explicit_loss_dimensions(tmp_path: Path, mapping_set: dict) -> None:
    mapping_set["mappings"][0]["classification"] = "lossy"
    result = _validate(tmp_path, mapping_set)
    assert not result.ok
    assert any("loss_dimensions" in error for error in result.errors)


def test_one_to_one_mapping_rejects_loss_dimensions(tmp_path: Path, mapping_set: dict) -> None:
    mapping_set["mappings"][0]["loss_dimensions"] = ["range"]
    result = _validate(tmp_path, mapping_set)
    assert not result.ok
    assert any("loss_dimensions" in error for error in result.errors)
