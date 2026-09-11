"""Locate, load, and apply the published EdgeLoom JSON Schemas."""

from __future__ import annotations

import ipaddress
import json
import re
from collections.abc import Iterator
from dataclasses import dataclass
from itertools import islice
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml

from edgeloom.boundedyaml import DocumentTooLargeError, check_bounds

SCHEMA_VERSION = "0.1"

PROFILE = "profile"
CAPABILITY_MAP = "capability-map"
EVIDENCE_RECORD = "evidence-record"
SOURCE_MANIFEST = "source-manifest"
CATALOG_MAPPING_SET = "catalog-mapping-set"
KINDS = (PROFILE, CAPABILITY_MAP, EVIDENCE_RECORD, SOURCE_MANIFEST, CATALOG_MAPPING_SET)

_YAML_SUFFIXES = {".yaml", ".yml"}
_JSON_SUFFIXES = {".json"}
DOCUMENT_SUFFIXES = _YAML_SUFFIXES | _JSON_SUFFIXES

_WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:")

# Bundled schemas are trusted, but the documents they validate are not. Keep a
# single command from flooding a terminal or retaining an unbounded list of
# jsonschema diagnostics. The audit command has a separate, evidence-record
# budget because it serializes a different, deliberately redacted structure.
MAX_VALIDATION_ERRORS = 50
VALIDATION_TRUNCATION_MARKER = (
    f"<document root>: validation diagnostics truncated after {MAX_VALIDATION_ERRORS} errors"
)


class SchemaError(RuntimeError):
    """Raised when a schema cannot be located or a document cannot be read."""


class NonStringMappingKeyError(SchemaError):
    """A YAML mapping cannot be represented as a JSON Schema object."""


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


def _require_string_mapping_keys(document: Any, *, path: Path) -> None:
    """Reject YAML mappings that cannot enter the JSON data model safely.

    PyYAML permits integer, boolean, and other hashable keys. JSON Schema object
    member names are strings, and validators may otherwise raise while applying
    keywords such as ``patternProperties``. The document has already passed the
    shared depth and expanded-node bounds, but aliases can still share objects,
    so this walk remains identity-memoised.
    """
    pending = [document]
    seen: set[int] = set()
    while pending:
        node = pending.pop()
        if not isinstance(node, (dict, list, tuple)):
            continue
        identity = id(node)
        if identity in seen:
            continue
        seen.add(identity)
        if isinstance(node, dict):
            for key, value in node.items():
                if not isinstance(key, str):
                    raise NonStringMappingKeyError(
                        f"{path}: contains a non-string YAML mapping key; "
                        "JSON Schema object member names must be strings",
                    )
                pending.append(value)
        else:
            pending.extend(node)


def parse_document_bytes(content: bytes, *, path: Path) -> Any:
    """Parse already-snapshotted YAML or JSON bytes within shared bounds.

    Keeping parsing separate from file I/O lets evidence generation hash and
    validate the same byte snapshot instead of reopening a mutable artifact.
    ``path`` supplies only the format hint and diagnostic label.
    """
    if path.suffix.lower() not in DOCUMENT_SUFFIXES:
        raise SchemaError(f"Unsupported document type {path.suffix!r}: {path}")
    try:
        text = content.decode("utf-8")
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
        bounded = check_bounds(document)
    except DocumentTooLargeError as exc:
        raise SchemaError(f"{path}: {exc}") from exc
    _require_string_mapping_keys(bounded, path=path)
    return bounded


def load_document(path: Path) -> Any:
    """Read a YAML or JSON document from disk."""
    try:
        content = path.read_bytes()
    except OSError as exc:
        raise SchemaError(f"Could not read {path}: {exc}") from exc
    return parse_document_bytes(content, path=path)


def detect_kind(document: Any) -> str | None:
    """Infer which schema a document is meant to satisfy.

    Returns ``None`` when the document matches neither shape, so callers can
    skip unrelated YAML rather than reporting spurious failures.
    """
    if not isinstance(document, dict):
        return None
    tagged_kind = document.get("kind")
    if tagged_kind in {SOURCE_MANIFEST, CATALOG_MAPPING_SET}:
        return tagged_kind
    if (
        document.get("record_version") == "0.1"
        and isinstance(document.get("subject"), dict)
        and isinstance(document.get("checks"), list)
    ):
        return EVIDENCE_RECORD
    # A missing or misspelled catalog kind must fail its intended schema rather
    # than disappear as "unrelated" beside another valid document. These
    # structural hints are deliberately specific to the two catalog contracts;
    # generic YAML with a Kubernetes-style ``kind`` remains unrelated.
    if "repository" in document and ("artifacts" in document or "ecosystem" in document):
        return SOURCE_MANIFEST
    if "source_manifests" in document or ("nodes" in document and "mappings" in document):
        return CATALOG_MAPPING_SET
    if isinstance(document.get("drivers"), dict):
        return CAPABILITY_MAP
    if isinstance(document.get("components"), list):
        return PROFILE
    return None


def _duplicate_id_errors(items: Any, location: str) -> list[str]:
    """Report duplicate object IDs that JSON Schema cannot express.

    ``uniqueItems`` only rejects byte-for-byte-equivalent objects. Two records
    may carry the same ID and differ elsewhere, so identifier uniqueness is a
    semantic contract enforced by ``edgeloom validate``.
    """
    if not isinstance(items, list):
        return []

    seen: set[str] = set()
    duplicates: set[str] = set()
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            continue
        identifier = item["id"]
        if identifier in seen:
            duplicates.add(identifier)
        seen.add(identifier)
    return [f"{location}: duplicate id {identifier!r}" for identifier in sorted(duplicates)]


def _profile_duplicate_id_errors(document: dict[str, Any]) -> Iterator[str]:
    """Reject reused component and capability IDs that ``uniqueItems`` cannot see.

    ``uniqueItems`` compares whole objects, so ``{id: lock, version: 1}`` next
    to ``{id: lock, version: 2}`` is accepted. The schema says IDs are unique
    within the profile / component; this pass enforces that in document order.
    """
    components = document.get("components")
    if not isinstance(components, list):
        return

    seen_component_ids: set[str] = set()
    for component_index, component in enumerate(components):
        if not isinstance(component, dict):
            continue
        capabilities = component.get("capabilities")
        if isinstance(capabilities, list):
            seen_capability_ids: set[str] = set()
            for capability_index, capability in enumerate(capabilities):
                if not isinstance(capability, dict) or not isinstance(capability.get("id"), str):
                    continue
                capability_id = capability["id"]
                if capability_id in seen_capability_ids:
                    yield (
                        f"components/{component_index}/capabilities/{capability_index}: "
                        f"duplicate capability id {capability_id!r}"
                    )
                seen_capability_ids.add(capability_id)
        component_id = component.get("id")
        if isinstance(component_id, str):
            if component_id in seen_component_ids:
                yield f"components/{component_index}: duplicate component id {component_id!r}"
            seen_component_ids.add(component_id)


def _artifact_manifest_reference_errors(
    item: Any,
    location: str,
    manifest_ids: set[str],
) -> list[str]:
    """Check the manifest half of an artifact reference within a mapping set.

    Artifact IDs live in separate source-manifest documents. Resolving those
    files and checking their content digests belongs to a future directory-level
    catalog validator; this single-document validator can still reject a
    manifest ID that the mapping set never declares.
    """
    if not isinstance(item, dict):
        return []
    artifact = item.get("artifact")
    if not isinstance(artifact, dict):
        return []
    manifest_id = artifact.get("manifest_id")
    if isinstance(manifest_id, str) and manifest_id not in manifest_ids:
        return [f"{location}/artifact/manifest_id: unknown source manifest {manifest_id!r}"]
    return []


def _catalog_items(value: Any) -> list[Any]:
    """Return catalog collection items without trusting a schema-invalid type."""
    return value if isinstance(value, list) else []


def _posix_contract_path_errors(value: Any, location: str) -> list[str]:
    """Validate a path before any future catalog resolver treats it as a file.

    Contract paths are portable POSIX paths. They name either a Git-tree entry
    or a file below a catalog root; they are never host filesystem paths.
    JSON Schema carries the same constraints for non-Python consumers, while
    this check gives the CLI a stable and explicit diagnostic.
    """
    if not isinstance(value, str):
        return []

    problems: list[str] = []
    segments = value.split("/")
    if not value or value.startswith("/") or _WINDOWS_DRIVE.match(value):
        problems.append("must be a relative POSIX path without a drive prefix")
    if "\\" in value:
        problems.append("must use POSIX '/' separators")
    if value.endswith("/") or "" in segments:
        problems.append("must not contain empty segments or a trailing slash")
    if any(segment in {".", ".."} for segment in segments):
        problems.append("must not contain '.' or '..' segments")
    if any(segment.casefold() == ".git" for segment in segments):
        problems.append("must not address Git administrative data")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        problems.append("must not contain control characters")
    return [f"{location}: {problem}" for problem in problems]


def _repository_url_errors(repository: Any) -> list[str]:
    """Validate a declared Git HTTPS URL without performing network access."""
    if not isinstance(repository, dict):
        return []
    value = repository.get("url")
    if not isinstance(value, str):
        return []

    errors: list[str] = []
    if any(character.isspace() or ord(character) == 127 for character in value):
        errors.append("repository/url: must not contain whitespace or control characters")
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        # Accessing ``port`` also rejects malformed or out-of-range ports.
        _ = parsed.port
    except ValueError:
        errors.append("repository/url: must be a well-formed HTTPS repository URL")
        return errors

    if parsed.scheme != "https" or not hostname:
        errors.append("repository/url: must use HTTPS and include a hostname")
    elif not _valid_repository_hostname(hostname):
        errors.append("repository/url: hostname is not valid")
    if parsed.username is not None or parsed.password is not None:
        errors.append("repository/url: credentials are not allowed")
    if "?" in value or "#" in value:
        errors.append("repository/url: query strings and fragments are not allowed")
    return errors


def _valid_repository_hostname(hostname: str) -> bool:
    """Validate an IP literal or canonical DNS/IDNA hostname locally."""
    if hostname.endswith(".") or "%" in hostname:
        return False
    try:
        ipaddress.ip_address(hostname)
        return True
    except ValueError:
        # A dotted numeric token is intended as an IP address, not a DNS name.
        if ":" in hostname or re.fullmatch(r"[0-9.]+", hostname):
            return False

    try:
        ascii_hostname = hostname.encode("idna").decode("ascii")
    except UnicodeError:
        return False
    if len(ascii_hostname) > 253:
        return False
    labels = ascii_hostname.split(".")
    return all(
        1 <= len(label) <= 63 and re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", label)
        for label in labels
    )


def _iter_semantic_errors(document: Any, kind: str) -> Iterator[str]:
    """Yield public-contract invariants beyond JSON Schema's vocabulary."""
    if not isinstance(document, dict):
        return

    if kind == SOURCE_MANIFEST:
        artifacts = _catalog_items(document.get("artifacts"))
        yield from _duplicate_id_errors(artifacts, "artifacts")
        yield from _repository_url_errors(document.get("repository"))
        for index, artifact in enumerate(artifacts):
            if not isinstance(artifact, dict):
                continue
            yield from _posix_contract_path_errors(
                artifact.get("path"),
                f"artifacts/{index}/path",
            )
            license_record = artifact.get("license")
            if isinstance(license_record, dict):
                yield from _posix_contract_path_errors(
                    license_record.get("evidence_path"),
                    f"artifacts/{index}/license/evidence_path",
                )
        return

    if kind == PROFILE:
        yield from _profile_duplicate_id_errors(document)
        return

    if kind != CATALOG_MAPPING_SET:
        return

    manifests = _catalog_items(document.get("source_manifests"))
    nodes = _catalog_items(document.get("nodes"))
    evidence = _catalog_items(document.get("evidence"))
    mappings = _catalog_items(document.get("mappings"))

    yield from _duplicate_id_errors(manifests, "source_manifests")
    yield from _duplicate_id_errors(nodes, "nodes")
    yield from _duplicate_id_errors(evidence, "evidence")
    yield from _duplicate_id_errors(mappings, "mappings")

    manifest_ids = {
        item["id"] for item in manifests if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    node_ids = {item["id"] for item in nodes if isinstance(item, dict) and isinstance(item.get("id"), str)}
    evidence_ids = {
        item["id"] for item in evidence if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    present_layers = {
        item["layer"] for item in nodes if isinstance(item, dict) and isinstance(item.get("layer"), str)
    }
    node_layers = {
        item["id"]: item["layer"]
        for item in nodes
        if isinstance(item, dict) and isinstance(item.get("id"), str) and isinstance(item.get("layer"), str)
    }
    for required_layer in (
        "device-protocol-support",
        "platform-exposure",
        "neutral-sdf-representation",
    ):
        if required_layer not in present_layers:
            yield f"nodes: missing required layer {required_layer!r}"

    for index, reference in enumerate(manifests):
        if isinstance(reference, dict):
            yield from _posix_contract_path_errors(
                reference.get("path"),
                f"source_manifests/{index}/path",
            )
    for index, node in enumerate(nodes):
        yield from _artifact_manifest_reference_errors(node, f"nodes/{index}", manifest_ids)
    for index, record in enumerate(evidence):
        yield from _artifact_manifest_reference_errors(record, f"evidence/{index}", manifest_ids)

    for index, mapping in enumerate(mappings):
        if not isinstance(mapping, dict):
            continue
        classification = mapping.get("classification")
        if classification == "unbound":
            if "unbound_reason" not in mapping:
                yield f"mappings/{index}: unbound mapping requires unbound_reason"
            if "to" in mapping:
                yield f"mappings/{index}: unbound mapping must not declare a target node"
        elif isinstance(classification, str):
            if "to" not in mapping:
                yield f"mappings/{index}: bound mapping requires a target node"
            if "unbound_reason" in mapping:
                yield f"mappings/{index}: bound mapping must not declare unbound_reason"
        for endpoint in ("from", "to"):
            node_id = mapping.get(endpoint)
            if isinstance(node_id, str) and node_id not in node_ids:
                yield f"mappings/{index}/{endpoint}: unknown node {node_id!r}"
        source_id = mapping.get("from")
        target_id = mapping.get("to")
        if (
            classification != "unbound"
            and isinstance(source_id, str)
            and isinstance(target_id, str)
            and source_id in node_layers
            and target_id in node_layers
        ):
            if source_id == target_id:
                yield f"mappings/{index}: bound mapping must not target its source node"
            elif node_layers[source_id] == node_layers[target_id]:
                yield f"mappings/{index}: bound mapping must connect different evidence layers"
        refs = mapping.get("evidence_refs")
        if isinstance(refs, list):
            for ref_index, evidence_id in enumerate(refs):
                if isinstance(evidence_id, str) and evidence_id not in evidence_ids:
                    yield (f"mappings/{index}/evidence_refs/{ref_index}: unknown evidence {evidence_id!r}")

    review = document.get("review")
    if isinstance(review, dict) and review.get("lifecycle") != "candidate":
        author = review.get("author")
        reviewers = review.get("reviewers")
        if isinstance(author, str) and isinstance(reviewers, list) and author in reviewers:
            yield "review/reviewers: record author is not an independent reviewer"


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
    """Return bounded, stable diagnostics for one in-memory document."""
    import jsonschema

    validator = jsonschema.Draft202012Validator(
        load_schema(kind),
        format_checker=jsonschema.FormatChecker(),
    )
    sampled = list(islice(validator.iter_errors(document), MAX_VALIDATION_ERRORS + 1))
    schema_truncated = len(sampled) > MAX_VALIDATION_ERRORS
    schema_errors = sorted(
        sampled[:MAX_VALIDATION_ERRORS],
        key=lambda error: (
            tuple(str(part) for part in error.absolute_path),
            tuple(str(part) for part in error.absolute_schema_path),
            error.message,
        ),
    )
    errors: list[str] = []
    for error in schema_errors:
        location = "/".join(str(part) for part in error.absolute_path) or "<document root>"
        errors.append(f"{location}: {error.message}")

    if schema_truncated:
        errors.append(VALIDATION_TRUNCATION_MARKER)
        return tuple(errors)

    remaining = MAX_VALIDATION_ERRORS - len(errors)
    semantic_sample = list(islice(_iter_semantic_errors(document, kind), remaining + 1))
    errors.extend(semantic_sample[:remaining])
    if len(semantic_sample) > remaining:
        errors.append(VALIDATION_TRUNCATION_MARKER)
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
