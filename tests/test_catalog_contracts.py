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


@pytest.mark.parametrize("kind_value", [None, "source_manifest"])
def test_cli_does_not_silently_skip_a_mistagged_catalog_document_in_a_mixed_directory(
    tmp_path: Path,
    source_manifest: dict,
    capsys: pytest.CaptureFixture[str],
    kind_value: str | None,
) -> None:
    _write(tmp_path, "valid.yaml", source_manifest)
    invalid = copy.deepcopy(source_manifest)
    if kind_value is None:
        invalid.pop("kind")
    else:
        invalid["kind"] = kind_value
    _write(tmp_path, "invalid.yaml", invalid)

    assert main(["validate", str(tmp_path)]) == 1
    output = capsys.readouterr().out
    assert "invalid.yaml" in output
    assert "kind" in output
    assert "unrelated file(s) skipped" not in output


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


@pytest.mark.parametrize(
    "bad_url",
    [
        "http://example.invalid/repository.git",
        "https://",
        "https://exa mple.invalid/repository.git",
        "https://[invalid/repository.git",
        "https://bad_host.invalid/repository.git",
        "https://-bad.invalid/repository.git",
        "https://999.999.999.999/repository.git",
        "https://user:password@example.invalid/repository.git",
        "https://example.invalid/repository.git?ref=main",
        "https://example.invalid/repository.git#main",
    ],
)
def test_source_manifest_rejects_noncanonical_repository_urls(
    tmp_path: Path,
    source_manifest: dict,
    bad_url: str,
) -> None:
    source_manifest["repository"]["url"] = bad_url

    result = _validate(tmp_path, source_manifest)

    assert not result.ok
    assert any("repository/url" in error or "url" in error for error in result.errors)


def test_repository_url_shape_is_enforced_without_optional_jsonschema_format_extras(
    source_manifest: dict,
) -> None:
    import jsonschema

    source_manifest["repository"]["url"] = "https://exa mple.invalid/repository.git"
    validator = jsonschema.Draft202012Validator(schemas.load_schema(schemas.SOURCE_MANIFEST))
    assert list(validator.iter_errors(source_manifest))


@pytest.mark.parametrize(
    "bad_path",
    [
        "/absolute/profile.yml",
        "../profile.yml",
        "a/../profile.yml",
        "a/./profile.yml",
        "a//b.yml",
        "a/",
        ".",
        ".git/config",
        "a/.GIT/config",
        "C:/outside/profile.yml",
        r"a\b.yml",
        "a\x00b.yml",
        "a\nb.yml",
    ],
)
def test_source_manifest_rejects_unsafe_repository_paths(
    tmp_path: Path,
    source_manifest: dict,
    bad_path: str,
) -> None:
    source_manifest["artifacts"][0]["path"] = bad_path
    result = _validate(tmp_path, source_manifest)
    assert not result.ok
    assert any("artifacts/0/path" in error for error in result.errors)


def test_source_manifest_rejects_unsafe_license_evidence_path(
    tmp_path: Path,
    source_manifest: dict,
) -> None:
    source_manifest["artifacts"][0]["license"]["evidence_path"] = ".git/config"
    result = _validate(tmp_path, source_manifest)
    assert not result.ok
    assert any("license/evidence_path" in error for error in result.errors)


def test_mapping_set_manifest_paths_are_catalog_root_relative_and_safe(
    tmp_path: Path,
    mapping_set: dict,
) -> None:
    mapping_set["source_manifests"][0]["path"] = "C:/catalog/source.yaml"
    result = _validate(tmp_path, mapping_set)
    assert not result.ok
    assert any("source_manifests/0/path" in error for error in result.errors)


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


def test_source_manifest_requires_an_artifact_role(
    tmp_path: Path,
    source_manifest: dict,
) -> None:
    source_manifest["artifacts"][0].pop("artifact_role")
    result = _validate(tmp_path, source_manifest)
    assert not result.ok
    assert any("artifact_role" in error for error in result.errors)


@pytest.mark.parametrize(
    "role",
    ["driver-config", "fingerprints", "platform-profile", "sdf-model", "evidence"],
)
def test_source_manifest_accepts_every_versioned_artifact_role(
    tmp_path: Path,
    source_manifest: dict,
    role: str,
) -> None:
    source_manifest["artifacts"][0]["artifact_role"] = role
    assert _validate(tmp_path, source_manifest).ok


@pytest.mark.parametrize(
    ("target", "value"),
    [
        ("ecosystem", "SmartThings"),
        ("domain", "Door Lock"),
        ("platform", "SmartThings"),
        ("protocol", "Z-Wave"),
    ],
)
def test_aggregation_identifiers_are_stable_lowercase_tokens(
    tmp_path: Path,
    source_manifest: dict,
    mapping_set: dict,
    target: str,
    value: str,
) -> None:
    document = source_manifest if target == "ecosystem" else mapping_set
    if target == "ecosystem":
        document["ecosystem"] = value
    elif target == "protocol":
        document["scope"]["protocols"] = [value]
    else:
        document["scope"][target] = value
    result = _validate(tmp_path, document)
    assert not result.ok
    assert any(target in error or "protocols" in error for error in result.errors)


def test_source_maturity_rejects_review_lifecycle_terms(
    tmp_path: Path,
    source_manifest: dict,
) -> None:
    source_manifest["artifacts"][0]["source_maturity"] = "verified"
    result = _validate(tmp_path, source_manifest)
    assert not result.ok
    assert any("source_maturity" in error for error in result.errors)


def test_source_maturity_preserves_insufficient_status_evidence_as_unknown(
    tmp_path: Path,
    source_manifest: dict,
) -> None:
    source_manifest["artifacts"][0]["source_maturity"] = "unknown"
    assert _validate(tmp_path, source_manifest).ok


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


@pytest.mark.parametrize("field", ["source_manifests", "nodes", "evidence", "mappings"])
@pytest.mark.parametrize("bad_value", [1, {"not": "a-list"}, None])
def test_malformed_catalog_collections_report_validation_errors_instead_of_crashing(
    tmp_path: Path,
    mapping_set: dict,
    field: str,
    bad_value: object,
) -> None:
    mapping_set[field] = bad_value
    result = _validate(tmp_path, mapping_set)
    assert not result.ok
    assert any(field in error for error in result.errors)


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


def test_record_author_is_not_an_independent_reviewer(
    tmp_path: Path,
    mapping_set: dict,
) -> None:
    mapping_set["review"] = {
        "author": "fixture-author",
        "lifecycle": "reviewed",
        "reviewers": ["fixture-author"],
        "reviewed_at": "2026-08-30T12:00:00Z",
    }
    result = _validate(tmp_path, mapping_set)
    assert not result.ok
    assert "review/reviewers: record author is not an independent reviewer" in result.errors


def test_verified_review_requires_a_governed_decision_reference(
    tmp_path: Path,
    mapping_set: dict,
) -> None:
    mapping_set["review"] = {
        "author": "fixture-author",
        "lifecycle": "verified",
        "reviewers": ["fixture-reviewer"],
        "reviewed_at": "2026-08-30T12:00:00Z",
    }
    result = _validate(tmp_path, mapping_set)
    assert not result.ok
    assert any("decision_ref" in error for error in result.errors)


def test_verified_review_with_independent_decision_reference_is_structurally_valid(
    tmp_path: Path,
    mapping_set: dict,
) -> None:
    mapping_set["review"] = {
        "author": "fixture-author",
        "lifecycle": "verified",
        "reviewers": ["fixture-reviewer"],
        "reviewed_at": "2026-08-30T12:00:00Z",
        "decision_ref": "catalog-review-1",
    }
    assert _validate(tmp_path, mapping_set).ok


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


def test_mapping_set_rejects_a_self_mapping(tmp_path: Path, mapping_set: dict) -> None:
    mapping_set["mappings"][0]["to"] = mapping_set["mappings"][0]["from"]
    result = _validate(tmp_path, mapping_set)
    assert not result.ok
    assert any("must not target its source" in error for error in result.errors)


def test_mapping_set_rejects_a_same_layer_mapping(tmp_path: Path, mapping_set: dict) -> None:
    mapping_set["mappings"][0]["to"] = "device.auto-relock"
    result = _validate(tmp_path, mapping_set)
    assert not result.ok
    assert any("different evidence layers" in error for error in result.errors)


def test_mapping_set_allows_a_direct_cross_layer_mapping(tmp_path: Path, mapping_set: dict) -> None:
    mapping_set["mappings"][0]["to"] = "sdf.lock-state"
    result = _validate(tmp_path, mapping_set)
    assert result.ok, result.errors


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
