"""Locate, load, and apply the published EdgeLoom JSON Schemas."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from edgeloom.boundedyaml import DocumentTooLargeError, check_bounds

SCHEMA_VERSION = "0.1"

PROFILE = "profile"
CAPABILITY_MAP = "capability-map"
EVIDENCE_RECORD = "evidence-record"
KINDS = (PROFILE, CAPABILITY_MAP, EVIDENCE_RECORD)

_YAML_SUFFIXES = {".yaml", ".yml"}
_JSON_SUFFIXES = {".json"}
DOCUMENT_SUFFIXES = _YAML_SUFFIXES | _JSON_SUFFIXES


class SchemaError(RuntimeError):
    """Raised when a schema cannot be located or a document cannot be read."""


def schema_dir() -> Path:
    """Return the directory holding the shipped schemas.

    Installed wheels carry the schemas inside the package; a source checkout
    keeps the canonical copy at the repository root so it stays browsable and
    citable. Prefer the packaged copy, fall back to the checkout.
    """
    packaged = Path(__file__).resolve().parent / "schema"
    if packaged.is_dir():
        return packaged
    checkout = Path(__file__).resolve().parents[1] / "schema"
    if checkout.is_dir():
        return checkout
    raise SchemaError("EdgeLoom schemas not found; the installation looks incomplete")


def schema_path(kind: str) -> Path:
    if kind not in KINDS:
        raise SchemaError(f"Unknown schema kind {kind!r}; expected one of {', '.join(KINDS)}")
    path = schema_dir() / f"{kind}.schema.json"
    if not path.is_file():
        raise SchemaError(f"Schema file missing: {path}")
    return path


def load_schema(kind: str) -> dict[str, Any]:
    return json.loads(schema_path(kind).read_text(encoding="utf-8"))


def load_document(path: Path) -> Any:
    """Read a YAML or JSON document from disk."""
    if path.suffix.lower() not in DOCUMENT_SUFFIXES:
        raise SchemaError(f"Unsupported document type {path.suffix!r}: {path}")
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise SchemaError(f"{path}: is not valid UTF-8: {exc}") from exc
    try:
        if path.suffix.lower() in _JSON_SUFFIXES:
            document = json.loads(text)
        else:
            document = yaml.safe_load(text)
    except (json.JSONDecodeError, yaml.YAMLError) as exc:
        raise SchemaError(f"{path}: could not be parsed: {exc}") from exc
    except RecursionError as exc:
        # Both parsers recurse; a deeply nested document exhausts the stack
        # before the bounds check below can see it.
        raise SchemaError(f"{path}: nests too deeply to parse") from exc
    try:
        return check_bounds(document)
    except DocumentTooLargeError as exc:
        raise SchemaError(f"{path}: {exc}") from exc


def detect_kind(document: Any) -> str | None:
    """Infer which schema a document is meant to satisfy.

    Returns ``None`` when the document matches neither shape, so callers can
    skip unrelated YAML rather than reporting spurious failures.
    """
    if not isinstance(document, dict):
        return None
    if isinstance(document.get("drivers"), dict):
        return CAPABILITY_MAP
    if isinstance(document.get("components"), list):
        return PROFILE
    if (
        document.get("record_version") == "0.1"
        and isinstance(document.get("subject"), dict)
        and isinstance(document.get("checks"), list)
    ):
        return EVIDENCE_RECORD
    return None


@dataclass(frozen=True)
class ValidationResult:
    path: Path
    kind: str | None
    errors: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return self.kind is not None and not self.errors

    @property
    def skipped(self) -> bool:
        return self.kind is None


def validation_errors(document: Any, *, kind: str) -> tuple[str, ...]:
    """Return stable, path-qualified validation errors for an in-memory document."""
    import jsonschema

    validator = jsonschema.Draft202012Validator(load_schema(kind))
    errors = []
    for error in sorted(validator.iter_errors(document), key=lambda e: list(e.absolute_path)):
        location = "/".join(str(part) for part in error.absolute_path) or "<document root>"
        errors.append(f"{location}: {error.message}")
    return tuple(errors)


def validate_document(path: Path, kind: str | None = None) -> ValidationResult:
    """Validate one document. ``kind`` forces a schema instead of inferring one."""
    document = load_document(path)
    resolved = kind or detect_kind(document)
    if resolved is None:
        return ValidationResult(path=path, kind=None, errors=())

    return ValidationResult(path=path, kind=resolved, errors=validation_errors(document, kind=resolved))


# Directories that hold other people's files. Walking into them produces
# findings about vendored artifacts rather than about this project. pip, for
# one, ships CycloneDX SBOMs under .dist-info/sboms/ whose top-level
# "components" is a list, which is shape-identical to a device profile.
VENDOR_DIRS = frozenset(
    {
        "node_modules",
        "site-packages",
        "venv",
        "build",
        "dist",
        "__pycache__",
    }
)


def _is_vendored(path: Path, root: Path) -> bool:
    """True if any directory between root and path is vendored or hidden."""
    try:
        parts = path.relative_to(root).parts[:-1]
    except ValueError:
        return False
    return any(part in VENDOR_DIRS or part.startswith(".") for part in parts)


def iter_documents(targets: list[Path]) -> list[Path]:
    """Expand files and directories into a sorted list of candidate documents.

    Hidden and vendored directories are not descended into. A file named
    explicitly is always honoured, so `edgeloom validate .venv/thing.yaml`
    still works; only the recursive walk prunes.
    """
    found: set[Path] = set()
    for target in targets:
        if target.is_dir():
            for suffix in sorted(DOCUMENT_SUFFIXES):
                found.update(
                    p for p in target.rglob(f"*{suffix}") if p.is_file() and not _is_vendored(p, target)
                )
        elif target.is_file():
            found.add(target)
        else:
            raise SchemaError(f"No such file or directory: {target}")
    return sorted(found)
