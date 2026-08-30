"""Evidence-record generation stays local, bounded, and explicit about authority."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from edgeloom import evidence, schemas


def _write_json(path: Path, payload: object) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _write_schema(path: Path, *, required: list[str]) -> Path:
    return _write_json(
        path,
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "https://example.test/pinned.schema.json",
            "type": "object",
            "required": required,
        },
    )


def test_audit_records_digest_source_and_informative_schema(tmp_path: Path) -> None:
    artifact = _write_json(tmp_path / "switch.sdf.json", {"info": {"title": "Switch"}})
    schema = _write_schema(tmp_path / "sdf-rendition.schema.json", required=["info"])
    now = datetime(2026, 8, 26, 20, 0, tzinfo=UTC)

    result = evidence.audit_artifact(
        artifact,
        schema_path=schema,
        schema_authority="informative",
        source_uri="https://example.test/models/switch.sdf.json",
        source_ref="0123456789abcdef",
        license_expression="BSD-3-Clause",
        artifact_status="experimental",
        title="Pinned switch model",
        now=now,
    )

    assert not result.failed
    record = result.record
    assert record["record_version"] == "0.1"
    assert record["created_at"] == "2026-08-26T20:00:00+00:00"
    assert record["subject"]["media_type"] == "application/sdf+json"
    assert record["subject"]["digest"]["value"] == hashlib.sha256(artifact.read_bytes()).hexdigest()
    assert record["subject"]["uri"] == "https://example.test/models/switch.sdf.json"
    assert record["subject"]["ref"] == "0123456789abcdef"
    assert record["subject"]["license"] == "BSD-3-Clause"
    assert [check["status"] for check in record["checks"]] == ["pass", "pass", "pass"]
    assert record["checks"][-1]["authority"] == "informative"
    assert not schemas.validation_errors(record, kind=schemas.EVIDENCE_RECORD)


def test_record_id_is_stable_across_audit_times(tmp_path: Path) -> None:
    artifact = _write_json(tmp_path / "model.json", {"x": 1})
    first = evidence.audit_artifact(artifact, now=datetime(2026, 8, 26, tzinfo=UTC))
    second = evidence.audit_artifact(artifact, now=datetime(2026, 8, 27, tzinfo=UTC))

    assert first.record["record_id"] == second.record["record_id"]
    assert first.record["created_at"] != second.record["created_at"]


def test_record_id_captures_media_and_syntax_policy(tmp_path: Path) -> None:
    json_artifact = _write_json(tmp_path / "model.json", {"x": 1})
    opaque_artifact = tmp_path / "model.txt"
    opaque_artifact.write_bytes(json_artifact.read_bytes())

    parsed = evidence.audit_artifact(json_artifact)
    opaque = evidence.audit_artifact(opaque_artifact)

    assert parsed.record["subject"]["digest"] == opaque.record["subject"]["digest"]
    assert parsed.record["record_id"] != opaque.record["record_id"]
    assert parsed.record["checks"][1]["status"] == "pass"
    assert opaque.record["checks"][1]["status"] == "skipped"


def test_optional_metadata_is_normalized_once_for_record_identity(tmp_path: Path) -> None:
    artifact = _write_json(tmp_path / "model.json", {"x": 1})
    now = datetime(2026, 8, 26, tzinfo=UTC)
    clean = evidence.audit_artifact(
        artifact,
        source_uri="https://example.test/model.json",
        source_ref="0123456",
        license_expression="Apache-2.0",
        title="Example model",
        now=now,
    )
    padded = evidence.audit_artifact(
        artifact,
        source_uri="  https://example.test/model.json  ",
        source_ref="  0123456  ",
        license_expression="  Apache-2.0  ",
        title="  Example model  ",
        now=now,
    )

    assert padded.record == clean.record


@pytest.mark.parametrize(
    "argument",
    ["source_uri", "source_ref", "license_expression", "title"],
)
def test_empty_optional_metadata_is_rejected(tmp_path: Path, argument: str) -> None:
    artifact = _write_json(tmp_path / "model.json", {"x": 1})

    with pytest.raises(evidence.EvidenceError, match="must not be empty"):
        evidence.audit_artifact(artifact, **{argument: " \t "})


def test_hash_and_parse_use_one_byte_snapshot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    artifact = _write_json(tmp_path / "model.json", {"original": True})
    schema = _write_schema(tmp_path / "schema.json", required=["original"])
    original_bytes = artifact.read_bytes()
    parse_document_bytes = schemas.parse_document_bytes

    def mutate_after_snapshot(content: bytes, *, path: Path) -> object:
        if path == artifact:
            artifact.write_text('{"changed": true}', encoding="utf-8")
        return parse_document_bytes(content, path=path)

    monkeypatch.setattr(schemas, "parse_document_bytes", mutate_after_snapshot)

    result = evidence.audit_artifact(artifact, schema_path=schema)

    assert not result.failed
    assert result.record["subject"]["digest"]["value"] == hashlib.sha256(original_bytes).hexdigest()
    assert artifact.read_bytes() != original_bytes


def test_invalid_json_still_produces_a_failing_evidence_record(tmp_path: Path) -> None:
    artifact = tmp_path / "broken.json"
    artifact.write_text("{not json", encoding="utf-8")

    result = evidence.audit_artifact(artifact)

    assert result.failed
    syntax = next(check for check in result.record["checks"] if check["id"] == "document-syntax")
    assert syntax["status"] == "fail"
    assert len(syntax["details"]["message"]) <= 2000
    assert not schemas.validation_errors(result.record, kind=schemas.EVIDENCE_RECORD)


@pytest.mark.parametrize(
    ("suffix", "content", "marker"),
    [
        (".json", '{"token":"JSON_SECRET",}', "JSON_SECRET"),
        (".yaml", "token: [YAML_SECRET\nbad: value\n", "YAML_SECRET"),
    ],
)
def test_syntax_diagnostics_do_not_copy_artifact_text(
    tmp_path: Path,
    suffix: str,
    content: str,
    marker: str,
) -> None:
    artifact = tmp_path / f"malformed{suffix}"
    artifact.write_text(content, encoding="utf-8")

    result = evidence.audit_artifact(artifact)

    assert result.failed
    assert marker not in evidence.render_json(result.record)
    assert marker not in evidence.render_markdown(result.record)


def test_schema_failure_is_recorded_not_promoted_to_conformance(tmp_path: Path) -> None:
    artifact = _write_json(tmp_path / "model.json", {"x": 1})
    schema = _write_schema(tmp_path / "schema.json", required=["missing"])

    result = evidence.audit_artifact(artifact, schema_path=schema, schema_authority="user-supplied")

    assert result.failed
    check = next(check for check in result.record["checks"] if check["id"] == "json-schema")
    assert check["status"] == "fail"
    assert check["details"]["error_count"] == 1
    assert check["details"]["reported_error_count"] == 1
    assert check["details"]["errors"][0]["keyword"] == "required"
    assert any("does not establish" in item for item in result.record["limitations"])


def test_schema_error_record_does_not_copy_artifact_values(tmp_path: Path) -> None:
    artifact = _write_json(tmp_path / "model.json", {"x": "DO_NOT_COPY_THIS_VALUE"})
    schema = _write_json(
        tmp_path / "schema.json",
        {"type": "object", "properties": {"x": {"type": "integer"}}},
    )

    result = evidence.audit_artifact(artifact, schema_path=schema)
    rendered = evidence.render_json(result.record)

    assert result.failed
    assert "DO_NOT_COPY_THIS_VALUE" not in rendered
    assert result.record["checks"][-1]["details"]["errors"][0]["keyword"] == "type"


def test_schema_error_collection_is_bounded(tmp_path: Path) -> None:
    artifact = _write_json(tmp_path / "model.json", ["wrong"] * 75)
    schema = _write_json(tmp_path / "schema.json", {"type": "array", "items": {"type": "integer"}})

    result = evidence.audit_artifact(artifact, schema_path=schema)
    details = result.record["checks"][-1]["details"]

    assert result.failed
    assert details["reported_error_count"] == evidence.MAX_RECORDED_ERRORS
    assert len(details["errors"]) == evidence.MAX_RECORDED_ERRORS
    assert details["errors_truncated"] is True
    assert "error_count" not in details
    assert f"more than {evidence.MAX_RECORDED_ERRORS}" in result.record["checks"][-1]["summary"]


def test_recorded_schema_identifier_is_bounded(tmp_path: Path) -> None:
    artifact = _write_json(tmp_path / "model.json", {"x": 1})
    schema = _write_json(
        tmp_path / "schema.json",
        {"$id": "https://example.test/" + "x" * 3000, "type": "object"},
    )

    result = evidence.audit_artifact(artifact, schema_path=schema)
    recorded_schema = result.record["checks"][-1]["details"]["schema"]

    assert not result.failed
    assert len(recorded_schema["id"]) == 2000
    assert recorded_schema["id_truncated"] is True


def test_schema_format_checks_are_enforced(tmp_path: Path) -> None:
    artifact = _write_json(tmp_path / "model.json", {"when": "not-a-date"})
    schema = _write_json(
        tmp_path / "schema.json",
        {
            "type": "object",
            "properties": {"when": {"type": "string", "format": "date-time"}},
        },
    )

    result = evidence.audit_artifact(artifact, schema_path=schema)

    assert result.failed
    assert result.record["checks"][-1]["details"]["errors"][0]["keyword"] == "format"


def test_required_schema_format_checkers_are_installed() -> None:
    import jsonschema

    checker = jsonschema.FormatChecker()

    assert "date-time" in checker.checkers
    assert "uri" in checker.checkers


def test_user_schema_rejects_invalid_uri_format(tmp_path: Path) -> None:
    artifact = _write_json(tmp_path / "model.json", {"source": "not a uri"})
    schema = _write_json(
        tmp_path / "schema.json",
        {
            "type": "object",
            "properties": {"source": {"type": "string", "format": "uri"}},
        },
    )

    result = evidence.audit_artifact(artifact, schema_path=schema)

    assert result.failed
    assert result.record["checks"][-1]["details"]["errors"][0]["keyword"] == "format"


def test_oversized_document_is_hashed_but_not_parsed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    artifact = _write_json(tmp_path / "large.json", {"x": 1})
    monkeypatch.setattr(evidence, "MAX_PARSE_BYTES", 1)

    def unexpected_parse(*_args: object, **_kwargs: object) -> object:
        pytest.fail("oversized input reached the decoder")

    monkeypatch.setattr(schemas, "parse_document_bytes", unexpected_parse)

    result = evidence.audit_artifact(artifact)

    assert not result.failed
    syntax = next(check for check in result.record["checks"] if check["id"] == "document-syntax")
    assert syntax["status"] == "skipped"
    assert syntax["details"]["limit_bytes"] == 1


def test_invalid_user_schema_is_rejected(tmp_path: Path) -> None:
    artifact = _write_json(tmp_path / "model.json", {"x": 1})
    schema = _write_json(tmp_path / "schema.json", {"type": "definitely-not-a-json-schema-type"})

    with pytest.raises(evidence.EvidenceError, match="Invalid Draft 2020-12"):
        evidence.audit_artifact(artifact, schema_path=schema)


def test_invalid_schema_setup_error_omits_source_text(tmp_path: Path) -> None:
    artifact = _write_json(tmp_path / "model.json", {"x": 1})
    schema = tmp_path / "schema.yaml"
    schema.write_text("type: [SCHEMA_SECRET\nbad: value\n", encoding="utf-8")

    with pytest.raises(evidence.EvidenceError) as captured:
        evidence.audit_artifact(artifact, schema_path=schema)

    message = str(captured.value)
    assert "SCHEMA_SECRET" not in message
    assert "source text omitted" in message
    assert len(message) < 1000


def test_oversized_user_schema_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    artifact = _write_json(tmp_path / "model.json", {"x": 1})
    schema = _write_schema(tmp_path / "schema.json", required=["x"])
    monkeypatch.setattr(evidence, "MAX_PARSE_BYTES", 1)

    with pytest.raises(evidence.EvidenceError, match="Schema .* exceeds"):
        evidence.audit_artifact(artifact, schema_path=schema)


@pytest.mark.parametrize("keyword", ["$ref", "$dynamicRef"])
def test_schema_cannot_trigger_remote_resolution(tmp_path: Path, keyword: str) -> None:
    artifact = _write_json(tmp_path / "model.json", {"x": 1})
    schema = _write_json(
        tmp_path / "schema.json",
        {"type": "object", "properties": {"x": {keyword: "https://example.test/remote.json"}}},
    )

    with pytest.raises(evidence.EvidenceError, match="non-local"):
        evidence.audit_artifact(artifact, schema_path=schema)


def test_remote_reference_setup_error_is_bounded(tmp_path: Path) -> None:
    artifact = _write_json(tmp_path / "model.json", {"x": 1})
    schema = _write_json(tmp_path / "schema.json", {"$ref": "https://example.test/" + "x" * 5000})

    with pytest.raises(evidence.EvidenceError) as captured:
        evidence.audit_artifact(artifact, schema_path=schema)

    assert "non-local" in str(captured.value)
    assert "..." in str(captured.value)
    assert len(str(captured.value)) < 1000


def test_unresolved_local_schema_reference_is_a_bounded_setup_error(tmp_path: Path) -> None:
    artifact = _write_json(tmp_path / "model.json", {"x": 1})
    schema = _write_json(
        tmp_path / "schema.json",
        {"type": "object", "properties": {"x": {"$ref": "#/$defs/missing"}}},
    )

    with pytest.raises(evidence.EvidenceError, match="only local references"):
        evidence.audit_artifact(artifact, schema_path=schema)


def test_requested_schema_that_cannot_run_returns_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact = _write_json(tmp_path / "large.json", {"x": "a" * 500})
    schema = _write_schema(tmp_path / "schema.json", required=["x"])
    schema_bytes = schema.read_bytes()
    monkeypatch.setattr(evidence, "MAX_PARSE_BYTES", len(schema_bytes))

    result = evidence.audit_artifact(artifact, schema_path=schema)

    assert result.failed
    assert result.record["checks"][-1]["status"] == "skipped"


def test_direct_api_rejects_unknown_operator_labels(tmp_path: Path) -> None:
    artifact = _write_json(tmp_path / "model.json", {"x": 1})

    with pytest.raises(evidence.EvidenceError, match="schema authority"):
        evidence.audit_artifact(artifact, schema_authority="official")
    with pytest.raises(evidence.EvidenceError, match="artifact status"):
        evidence.audit_artifact(artifact, artifact_status="adopted")


def test_markdown_renderer_neutralizes_table_breaks_and_newlines(tmp_path: Path) -> None:
    artifact = _write_json(tmp_path / "model.json", {"x": 1})
    result = evidence.audit_artifact(
        artifact,
        title="Line one\nLine | two",
        source_uri="https://example.test/a|b",
    )

    rendered = evidence.render_markdown(result.record)

    assert "Line one Line \\| two" in rendered
    assert "https://example.test/a\\|b" in rendered


def test_markdown_renderer_neutralizes_html_links_and_code_breaks(tmp_path: Path) -> None:
    artifact = _write_json(tmp_path / "model.json", {"x": 1})
    result = evidence.audit_artifact(
        artifact,
        title="<img src=x onerror=alert(1)> [link](javascript:alert(1))",
        source_uri="https://example.test/`break`",
    )

    rendered = evidence.render_markdown(result.record)

    assert "<img" not in rendered
    assert "&lt;img" in rendered
    assert "\\[link\\]" in rendered
    assert "\\`break\\`" in rendered


def test_naive_datetime_is_recorded_as_utc(tmp_path: Path) -> None:
    artifact = _write_json(tmp_path / "model.json", {"x": 1})

    result = evidence.audit_artifact(artifact, now=datetime(2026, 8, 26) + timedelta(hours=1))

    assert result.record["created_at"].endswith("+00:00")
