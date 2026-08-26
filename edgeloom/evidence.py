"""Create bounded, reviewable evidence records for local artifacts.

The audit command is deliberately local and read-only. It hashes the exact
bytes the operator named, records asserted source metadata, parses bounded
JSON/YAML documents, and can apply a pinned JSON Schema supplied as a local
file. It does not fetch remote resources, resolve references, authenticate a
source, or turn a structural check into a conformance or certification claim.
"""

from __future__ import annotations

import hashlib
import html
import json
import mimetypes
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from edgeloom import __version__, schemas

AUDIT_POLICY_VERSION = "audit-0.1"
MAX_PARSE_BYTES = 8 * 1024 * 1024
MAX_RECORDED_ERRORS = 50
_DOCUMENT_SUFFIXES = {".json", ".yaml", ".yml"}


class EvidenceError(RuntimeError):
    """The requested audit could not produce a trustworthy record."""


@dataclass(frozen=True)
class AuditResult:
    record: dict[str, Any]
    failed: bool


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise EvidenceError(f"Could not read {path}: {exc}") from exc
    return digest.hexdigest()


def _media_type(path: Path) -> str:
    if path.name.endswith(".sdf.json"):
        return "application/sdf+json"
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed or "application/octet-stream"


def _parse_document(path: Path, size_bytes: int) -> tuple[Any | None, dict[str, Any]]:
    if path.suffix.lower() not in _DOCUMENT_SUFFIXES:
        return None, {
            "id": "document-syntax",
            "status": "skipped",
            "authority": "deterministic",
            "summary": "No JSON/YAML parser is registered for this file type.",
        }
    if size_bytes > MAX_PARSE_BYTES:
        return None, {
            "id": "document-syntax",
            "status": "skipped",
            "authority": "deterministic",
            "summary": f"Document exceeds the {MAX_PARSE_BYTES}-byte parsing limit; digest only.",
            "details": {"limit_bytes": MAX_PARSE_BYTES},
        }
    try:
        document = schemas.load_document(path)
    except schemas.SchemaError as exc:
        return None, {
            "id": "document-syntax",
            "status": "fail",
            "authority": "deterministic",
            "summary": "Document could not be parsed within EdgeLoom's safety bounds.",
            "details": {"error": str(exc)[:2000]},
        }
    return document, {
        "id": "document-syntax",
        "status": "pass",
        "authority": "deterministic",
        "summary": "Document parsed as bounded JSON/YAML.",
    }


def _load_user_schema(path: Path) -> tuple[dict[str, Any], str]:
    if not path.is_file():
        raise EvidenceError(f"Schema file not found: {path}")
    try:
        schema_size = path.stat().st_size
    except OSError as exc:
        raise EvidenceError(f"Could not stat schema {path}: {exc}") from exc
    if schema_size > MAX_PARSE_BYTES:
        raise EvidenceError(
            f"Schema {path} exceeds the {MAX_PARSE_BYTES}-byte parsing limit; "
            "pin a smaller local schema before auditing",
        )
    try:
        document = schemas.load_document(path)
    except schemas.SchemaError as exc:
        raise EvidenceError(f"Could not load schema {path}: {exc}") from exc
    if not isinstance(document, dict):
        raise EvidenceError(f"Schema must be a JSON/YAML object: {path}")

    def reject_remote_references(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in {"$ref", "$dynamicRef"} and isinstance(value, str) and not value.startswith("#"):
                    raise EvidenceError(
                        f"Schema {path} contains non-local {key} {value!r}; "
                        "pin and bundle referenced schemas before auditing",
                    )
                reject_remote_references(value)
        elif isinstance(node, list):
            for value in node:
                reject_remote_references(value)

    reject_remote_references(document)

    import jsonschema

    try:
        jsonschema.Draft202012Validator.check_schema(document)
    except jsonschema.exceptions.SchemaError as exc:
        raise EvidenceError(f"Invalid Draft 2020-12 JSON Schema {path}: {exc.message}") from exc
    return document, _sha256_file(path)


def _schema_check(
    document: Any | None,
    schema_path: Path,
    authority: str,
) -> tuple[dict[str, Any], str]:
    schema_document, schema_digest = _load_user_schema(schema_path)
    details: dict[str, Any] = {
        "schema": {
            "path": str(schema_path),
            "digest": {"algorithm": "sha256", "value": schema_digest},
        }
    }
    if isinstance(schema_document.get("$id"), str):
        details["schema"]["id"] = schema_document["$id"]

    if document is None:
        return (
            {
                "id": "json-schema",
                "status": "skipped",
                "authority": authority,
                "summary": "Schema check was not run because no bounded JSON/YAML document was available.",
                "details": details,
            },
            schema_digest,
        )

    import jsonschema

    validator = jsonschema.Draft202012Validator(schema_document)
    validation_errors = sorted(validator.iter_errors(document), key=lambda error: list(error.absolute_path))
    if not validation_errors:
        return (
            {
                "id": "json-schema",
                "status": "pass",
                "authority": authority,
                "summary": "Document satisfies the supplied Draft 2020-12 JSON Schema.",
                "details": details,
            },
            schema_digest,
        )

    reported_errors = []
    for error in validation_errors[:MAX_RECORDED_ERRORS]:
        location = "/".join(str(part) for part in error.absolute_path) or "<document root>"
        schema_location = "/".join(str(part) for part in error.absolute_schema_path) or "<schema root>"
        reported_errors.append(
            {
                "instance_path": location[:1000],
                "schema_path": schema_location[:1000],
                "keyword": str(error.validator or "unknown")[:100],
            }
        )
    details["error_count"] = len(validation_errors)
    details["errors"] = reported_errors
    details["errors_truncated"] = len(validation_errors) > len(reported_errors)
    return (
        {
            "id": "json-schema",
            "status": "fail",
            "authority": authority,
            "summary": f"Document has {len(validation_errors)} JSON-Schema validation error(s).",
            "details": details,
        },
        schema_digest,
    )


def _record_id(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return f"elr-{hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:24]}"


def audit_artifact(
    artifact: Path,
    *,
    schema_path: Path | None = None,
    schema_authority: str = "user-supplied",
    source_uri: str | None = None,
    source_ref: str | None = None,
    license_expression: str | None = None,
    artifact_status: str = "unknown",
    title: str | None = None,
    now: datetime | None = None,
) -> AuditResult:
    """Audit one local artifact and return a self-validating evidence record."""
    if not artifact.is_file():
        raise EvidenceError(f"Artifact file not found: {artifact}")
    try:
        size_bytes = artifact.stat().st_size
    except OSError as exc:
        raise EvidenceError(f"Could not stat {artifact}: {exc}") from exc

    artifact_digest = _sha256_file(artifact)
    document, syntax_check = _parse_document(artifact, size_bytes)
    checks: list[dict[str, Any]] = [
        {
            "id": "content-digest",
            "status": "pass",
            "authority": "deterministic",
            "summary": "SHA-256 digest computed over the exact local bytes.",
        },
        syntax_check,
    ]

    schema_digest = None
    if schema_path is not None:
        check, schema_digest = _schema_check(document, schema_path, schema_authority)
        checks.append(check)

    subject: dict[str, Any] = {
        "path": str(artifact),
        "status": artifact_status,
        "media_type": _media_type(artifact),
        "size_bytes": size_bytes,
        "digest": {"algorithm": "sha256", "value": artifact_digest},
    }
    if source_uri:
        subject["uri"] = source_uri
    if source_ref:
        subject["ref"] = source_ref
    if license_expression:
        subject["license"] = license_expression

    identity = {
        "policy_version": AUDIT_POLICY_VERSION,
        "artifact_digest": artifact_digest,
        "schema_digest": schema_digest,
        "schema_authority": schema_authority if schema_path else None,
        "source_uri": source_uri,
        "source_ref": source_ref,
        "license": license_expression,
        "status": artifact_status,
    }
    created_at = now or datetime.now(UTC)
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)

    record: dict[str, Any] = {
        "record_version": "0.1",
        "record_id": _record_id(identity),
        "created_at": created_at.astimezone(UTC).isoformat(),
        "tool": {
            "name": "edgeloom",
            "version": __version__,
            "policy_version": AUDIT_POLICY_VERSION,
        },
        "subject": subject,
        "checks": checks,
        "limitations": [
            "A digest establishes byte identity, not provenance, authenticity, ownership, or license.",
            (
                "Source URI, revision, license, and status are operator assertions; "
                "this command does not fetch or authenticate them."
            ),
            (
                "Structural validation does not establish semantic correctness, "
                "applicability, security, or standards conformance."
            ),
            (
                "Check authority labels are operator assertions about the supplied policy; "
                "EdgeLoom does not establish their governance status."
            ),
            (
                "Schema evaluation runs in-process; size, depth, and node bounds do not "
                "guarantee a time bound for adversarial schema expressions."
            ),
            "This local audit does not resolve remote references or imported model components.",
        ],
    }
    if title:
        record["title"] = title

    record_errors = schemas.validation_errors(record, kind=schemas.EVIDENCE_RECORD)
    if record_errors:
        raise EvidenceError(f"Generated evidence record violates its own schema: {'; '.join(record_errors)}")

    failed = any(check["status"] in {"fail", "error"} for check in checks)
    if schema_path is not None:
        schema_status = next(check["status"] for check in checks if check["id"] == "json-schema")
        failed = failed or schema_status != "pass"
    return AuditResult(record=record, failed=failed)


def render_json(record: dict[str, Any]) -> str:
    return json.dumps(record, indent=2, sort_keys=False, ensure_ascii=False) + "\n"


def _markdown_text(value: object) -> str:
    text = html.escape(" ".join(str(value).split()), quote=False)
    for character in ("\\", "`", "|", "[", "]", "*", "_"):
        text = text.replace(character, f"\\{character}")
    return text


def render_markdown(record: dict[str, Any]) -> str:
    """Render a compact human-review view without embedding artifact content."""
    subject = record["subject"]
    lines = [
        f"# {_markdown_text(record.get('title', 'EdgeLoom evidence record'))}",
        "",
        f"- Record: `{_markdown_text(record['record_id'])}`",
        f"- Created: `{_markdown_text(record['created_at'])}`",
        f"- Subject: `{_markdown_text(subject['path'])}`",
        f"- SHA-256: `{_markdown_text(subject['digest']['value'])}`",
        f"- Status: `{_markdown_text(subject['status'])}`",
    ]
    for label, key in (("Source", "uri"), ("Revision", "ref"), ("License", "license")):
        if key in subject:
            lines.append(f"- {label}: `{_markdown_text(subject[key])}`")

    lines.extend(
        ["", "## Checks", "", "| Check | Status | Authority | Summary |", "| --- | --- | --- | --- |"]
    )
    for check in record["checks"]:
        lines.append(
            "| "
            + " | ".join(_markdown_text(check[key]) for key in ("id", "status", "authority", "summary"))
            + " |"
        )

    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {_markdown_text(item)}" for item in record["limitations"])
    return "\n".join(lines) + "\n"
