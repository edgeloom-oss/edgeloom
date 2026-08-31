"""Tests for schema discovery, kind inference, and validation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from edgeloom import schemas


def _write(path: Path, payload: dict) -> Path:
    if path.suffix == ".json":
        path.write_text(json.dumps(payload), encoding="utf-8")
    else:
        path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    return path


VALID_PROFILE = {
    "name": "base-lock",
    "components": [
        {
            "id": "main",
            "label": "Main",
            "capabilities": [{"id": "lock", "version": 1}],
            "categories": [{"name": "SmartLock"}],
        }
    ],
}

VALID_MAP = {
    "version": "0.1",
    "platform": "smartthings",
    "drivers": {"zigbee-lock": {"attributes": {"Language": "adminmusic34435.language"}}},
}

VALID_EVIDENCE_RECORD = {
    "record_version": "0.1",
    "record_id": "elr-0123456789abcdef01234567",
    "created_at": "2026-08-26T20:00:00+00:00",
    "tool": {"name": "edgeloom", "version": "0.1.1", "policy_version": "audit-0.1"},
    "subject": {
        "path": "model.sdf.json",
        "status": "experimental",
        "size_bytes": 2,
        "digest": {"algorithm": "sha256", "value": "0" * 64},
    },
    "checks": [
        {
            "id": "content-digest",
            "status": "pass",
            "authority": "deterministic",
            "summary": "Digest computed.",
        }
    ],
    "limitations": ["A digest is not proof of provenance."],
}


def test_all_schemas_are_shipped_and_valid_draft_2020_12() -> None:
    import jsonschema

    assert schemas.KINDS == (
        schemas.PROFILE,
        schemas.CAPABILITY_MAP,
        schemas.EVIDENCE_RECORD,
        schemas.SOURCE_MANIFEST,
        schemas.CATALOG_MAPPING_SET,
    )
    for kind in schemas.KINDS:
        schema = schemas.load_schema(kind)
        assert schema["$schema"].startswith("https://json-schema.org/draft/2020-12")
        assert schema["title"].startswith("EdgeLoom")
        jsonschema.Draft202012Validator.check_schema(schema)


def test_unknown_schema_kind_is_rejected() -> None:
    with pytest.raises(schemas.SchemaError):
        schemas.load_schema("not-a-schema")


@pytest.mark.parametrize(
    "document,expected",
    [
        (VALID_PROFILE, schemas.PROFILE),
        (VALID_MAP, schemas.CAPABILITY_MAP),
        (VALID_EVIDENCE_RECORD, schemas.EVIDENCE_RECORD),
        (
            {"kind": "source-manifest", "repository": {}, "artifacts": []},
            schemas.SOURCE_MANIFEST,
        ),
        (
            {"kind": "catalog-mapping-set", "nodes": [], "mappings": []},
            schemas.CATALOG_MAPPING_SET,
        ),
        (
            {"schema_version": "0.1", "repository": {}, "artifacts": []},
            schemas.SOURCE_MANIFEST,
        ),
        (
            {
                "kind": "catalog_mapping_set",
                "source_manifests": [],
                "nodes": [],
                "mappings": [],
            },
            schemas.CATALOG_MAPPING_SET,
        ),
        ({"components": []}, schemas.PROFILE),
        ({"drivers": {}}, schemas.CAPABILITY_MAP),
        (
            {
                "generated_at": "2026-08-23T00:00:00+00:00",
                "source": "local",
                "stats": {},
                "unsupported_drivers": [],
                "drivers": [],
            },
            None,
        ),
        ({"unrelated": True}, None),
        ("not a mapping", None),
        (None, None),
    ],
)
def test_detect_kind(document: object, expected: str | None) -> None:
    assert schemas.detect_kind(document) == expected


@pytest.mark.parametrize(
    "payload,expected_kind,missing_key",
    [
        ({"components": []}, schemas.PROFILE, "name"),
        ({"drivers": {}}, schemas.CAPABILITY_MAP, "version"),
    ],
)
def test_missing_required_identity_key_fails_validation(
    tmp_path: Path, payload: dict, expected_kind: str, missing_key: str
) -> None:
    result = schemas.validate_document(_write(tmp_path / "invalid.yaml", payload))

    assert result.kind == expected_kind
    assert not result.ok
    assert any(missing_key in message for message in result.errors)


def test_valid_profile_passes(tmp_path: Path) -> None:
    result = schemas.validate_document(_write(tmp_path / "p.yaml", VALID_PROFILE))
    assert result.ok
    assert result.kind == schemas.PROFILE


def test_valid_capability_map_passes(tmp_path: Path) -> None:
    result = schemas.validate_document(_write(tmp_path / "m.yaml", VALID_MAP))
    assert result.ok
    assert result.kind == schemas.CAPABILITY_MAP


def test_valid_evidence_record_passes(tmp_path: Path) -> None:
    result = schemas.validate_document(_write(tmp_path / "record.json", VALID_EVIDENCE_RECORD))
    assert result.ok
    assert result.kind == schemas.EVIDENCE_RECORD


def test_evidence_record_active_review_requires_reviewer_and_time(tmp_path: Path) -> None:
    for disposition in ("accepted", "rejected", "needs-work"):
        incomplete = {**VALID_EVIDENCE_RECORD, "review": {"disposition": disposition}}

        result = schemas.validate_document(_write(tmp_path / f"{disposition}.json", incomplete))

        assert not result.ok
        assert any("reviewer" in message for message in result.errors)
        assert any("reviewed_at" in message for message in result.errors)


def test_evidence_record_accepts_complete_human_review(tmp_path: Path) -> None:
    reviewed = {
        **VALID_EVIDENCE_RECORD,
        "review": {
            "disposition": "accepted",
            "reviewer": "operator@example.test",
            "reviewed_at": "2026-08-30T20:00:00+00:00",
        },
    }

    result = schemas.validate_document(_write(tmp_path / "reviewed.json", reviewed))

    assert result.ok


@pytest.mark.parametrize("field", ["mappings", "transformation"])
def test_evidence_record_defers_unproduced_contracts(tmp_path: Path, field: str) -> None:
    unsupported = {**VALID_EVIDENCE_RECORD, field: [] if field == "mappings" else {}}

    result = schemas.validate_document(_write(tmp_path / f"{field}.json", unsupported))

    assert not result.ok
    assert any("Additional properties" in message for message in result.errors)


def test_evidence_record_date_time_format_is_enforced(tmp_path: Path) -> None:
    invalid = {**VALID_EVIDENCE_RECORD, "created_at": "not-a-date"}

    result = schemas.validate_document(_write(tmp_path / "record.json", invalid))

    assert not result.ok
    assert any("date-time" in message for message in result.errors)


def test_bundled_schema_errors_are_bounded_with_stable_marker(tmp_path: Path) -> None:
    invalid = {
        "name": "many-invalid-components",
        "components": [{"id": f"component-{index}"} for index in range(75)],
    }

    first = schemas.validate_document(_write(tmp_path / "many.yaml", invalid))
    second = schemas.validation_errors(invalid, kind=schemas.PROFILE)

    assert first.errors == second
    assert len(first.errors) == schemas.MAX_VALIDATION_ERRORS + 1
    assert first.errors[-1] == schemas.VALIDATION_TRUNCATION_MARKER


def test_profile_missing_components_fails(tmp_path: Path) -> None:
    result = schemas.validate_document(_write(tmp_path / "p.yaml", {"name": "x"}), kind=schemas.PROFILE)
    assert not result.ok
    assert any("components" in message for message in result.errors)


def test_profile_with_empty_capabilities_fails(tmp_path: Path) -> None:
    bad = {"name": "x", "components": [{"id": "main", "capabilities": []}]}
    result = schemas.validate_document(_write(tmp_path / "p.yaml", bad))
    assert not result.ok


def test_profile_rejects_exact_duplicate_components(tmp_path: Path) -> None:
    bad = {
        "name": "x",
        "components": [
            {"id": "main", "capabilities": [{"id": "lock", "version": 1}]},
            {"id": "main", "capabilities": [{"id": "lock", "version": 1}]},
        ],
    }
    result = schemas.validate_document(_write(tmp_path / "p.yaml", bad))

    assert not result.ok


def test_profile_rejects_exact_duplicate_capabilities(tmp_path: Path) -> None:
    bad = {
        "name": "x",
        "components": [
            {
                "id": "main",
                "capabilities": [
                    {"id": "lock", "version": 1},
                    {"id": "lock", "version": 1},
                ],
            }
        ],
    }
    result = schemas.validate_document(_write(tmp_path / "p.yaml", bad))

    assert not result.ok


def test_capability_map_rejects_unnamespaced_capability(tmp_path: Path) -> None:
    """A bare id like 'language' would collide with the standard namespace."""
    bad = {"version": "0.1", "drivers": {"zigbee-lock": {"attributes": {"Language": "language"}}}}
    result = schemas.validate_document(_write(tmp_path / "m.yaml", bad))
    assert not result.ok


def test_capability_map_rejects_unknown_key(tmp_path: Path) -> None:
    bad = {"version": "0.1", "drivers": {"zigbee-lock": {"attributes": {"A": "ns.a"}, "oops": 1}}}
    result = schemas.validate_document(_write(tmp_path / "m.yaml", bad))
    assert not result.ok


def test_unrelated_yaml_is_skipped_not_failed(tmp_path: Path) -> None:
    result = schemas.validate_document(_write(tmp_path / "other.yaml", {"hello": "world"}))
    assert result.skipped
    assert result.errors == ()


def test_unparseable_document_raises(tmp_path: Path) -> None:
    path = tmp_path / "broken.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(schemas.SchemaError):
        schemas.validate_document(path)


def test_iter_documents_walks_directories(tmp_path: Path) -> None:
    _write(tmp_path / "a.yaml", VALID_PROFILE)
    (tmp_path / "nested").mkdir()
    _write(tmp_path / "nested" / "b.json", VALID_PROFILE)
    (tmp_path / "ignored.txt").write_text("not a document", encoding="utf-8")

    found = schemas.iter_documents([tmp_path])

    assert found == [tmp_path / "a.yaml", tmp_path / "nested" / "b.json"]


def test_iter_documents_rejects_missing_path(tmp_path: Path) -> None:
    with pytest.raises(schemas.SchemaError):
        schemas.iter_documents([tmp_path / "nope"])


def test_repo_capability_map_conforms(repo_root: Path) -> None:
    """The map generated from the legacy INI files must satisfy the schema."""
    result = schemas.validate_document(repo_root / "auto_patch" / "capability-map.yaml")
    assert result.ok, result.errors


def test_humidity_sensor_is_mapped(repo_root: Path) -> None:
    """The INI and its schema-checked mirror must agree for every driver."""
    import configparser

    ini = configparser.ConfigParser()
    ini.optionxform = str
    ini.read(repo_root / "auto_patch" / "custom_capability_list.config")

    document = schemas.load_document(repo_root / "auto_patch" / "capability-map.yaml")
    mapped = document["drivers"]["zigbee-humidity-sensor"]["attributes"]

    assert dict(ini["zigbee-humidity-sensor"]) == mapped


def test_every_shipped_profile_conforms(repo_root: Path) -> None:
    """Both toolchain paths must emit profiles that satisfy one contract."""
    targets = [
        repo_root / "auto_patch" / "zigbee-lock" / "profiles",
        repo_root / "translator" / "ha_proxy_edge_driver" / "profiles",
    ]
    results = [schemas.validate_document(p) for p in schemas.iter_documents(targets)]
    assert results, "expected profiles to validate"
    assert all(r.ok for r in results), [r.errors for r in results if not r.ok]


def test_repo_document_census_recognizes_only_schema_artifacts(repo_root: Path) -> None:
    """Repository-wide inference must find every schema artifact and skip support YAML."""
    expected = {
        Path("auto_patch/capability-map.yaml"),
        # Vendored upstream corpus; see tests/fixtures/upstream_profiles/README.md.
        Path("tests/fixtures/upstream_profiles/base-lock.yml"),
        Path("tests/fixtures/upstream_profiles/color-temp-bulb.yml"),
        Path("tests/fixtures/upstream_profiles/frient-switch-power-energy-voltage.yml"),
        Path("auto_patch/zigbee-lock/profiles/base-lock.yml"),
        Path("auto_patch/zigbee-lock/profiles/lock-battery.yml"),
        Path("auto_patch/zigbee-lock/profiles/lock-without-codes.yml"),
        Path("translator/ha_proxy_edge_driver/profiles/ha_contact_sensor.yaml"),
        Path("translator/ha_proxy_edge_driver/profiles/ha_light_color.yaml"),
        Path("translator/ha_proxy_edge_driver/profiles/ha_light_dimmable.yaml"),
        Path("translator/ha_proxy_edge_driver/profiles/ha_lock_basic.yaml"),
        Path("translator/ha_proxy_edge_driver/profiles/ha_motion_sensor.yaml"),
        Path("translator/ha_proxy_edge_driver/profiles/ha_switch_basic.yaml"),
        Path("tests/fixtures/catalog/smartthings-source.yaml"),
        Path("tests/fixtures/catalog/onedm-source.yaml"),
        Path("tests/fixtures/catalog/lock-mapping-set.yaml"),
    }
    recognized = {
        result.path.relative_to(repo_root)
        for result in (schemas.validate_document(path) for path in schemas.iter_documents([repo_root]))
        if not result.skipped
    }

    assert recognized == expected


def test_iter_documents_skips_hidden_and_vendored_directories(tmp_path: Path) -> None:
    """A .venv in the tree must not turn third-party files into findings.

    pip ships CycloneDX SBOMs under .dist-info/sboms/ whose top-level
    "components" is a list, which detect_kind would otherwise read as a device
    profile and report as invalid.
    """
    _write(tmp_path / "real.yaml", VALID_PROFILE)

    sbom = tmp_path / ".venv" / "lib" / "site-packages" / "ruff.dist-info" / "sboms"
    sbom.mkdir(parents=True)
    _write(sbom / "ruff.cyclonedx.json", {"bomFormat": "CycloneDX", "components": [{"type": "library"}]})
    for vendored in ("node_modules", "build", "dist"):
        (tmp_path / vendored).mkdir()
        _write(tmp_path / vendored / "stray.yaml", VALID_PROFILE)

    assert schemas.iter_documents([tmp_path]) == [tmp_path / "real.yaml"]


def test_explicitly_named_vendored_file_is_still_honoured(tmp_path: Path) -> None:
    """Pruning applies to the recursive walk, not to a path the user named."""
    hidden = tmp_path / ".venv"
    hidden.mkdir()
    target = _write(hidden / "profile.yaml", VALID_PROFILE)

    assert schemas.iter_documents([target]) == [target]


def test_real_upstream_profiles_are_accepted(repo_root: Path) -> None:
    """The schema is only an assurance layer if it accepts what the platform ships.

    An earlier revision declared additionalProperties: false on capability
    entries without checking against real data, and rejected 13 of 38 upstream
    SmartThings profiles over the `config` key. See the corpus README.
    """
    corpus = repo_root / "tests" / "fixtures" / "upstream_profiles"
    profiles = sorted(corpus.glob("*.yml"))
    assert profiles, "upstream corpus is missing"

    failures = {
        path.name: result.errors
        for path in profiles
        for result in [schemas.validate_document(path)]
        if not result.ok
    }
    assert not failures, f"schema rejects real upstream profiles: {failures}"


def test_capability_config_is_accepted_and_opaque(tmp_path: Path) -> None:
    """`config` carries platform presentation data EdgeLoom does not model."""
    profile = {
        "name": "x",
        "components": [
            {
                "id": "main",
                "capabilities": [
                    {
                        "id": "colorTemperature",
                        "version": 1,
                        "config": {"values": [{"key": "colorTemperature.value", "range": [2700, 6500]}]},
                    }
                ],
            }
        ],
    }
    assert schemas.validate_document(_write(tmp_path / "p.yaml", profile)).ok


def test_unknown_capability_key_is_still_rejected(tmp_path: Path) -> None:
    """Accepting `config` must not turn the capability object into a free-for-all."""
    profile = {
        "name": "x",
        "components": [{"id": "main", "capabilities": [{"id": "switch", "verison": 1}]}],
    }
    assert not schemas.validate_document(_write(tmp_path / "p.yaml", profile)).ok
