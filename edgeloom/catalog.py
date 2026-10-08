"""Offline catalog joins and deterministic reports; network use is opt-in.

Upstream files are untrusted bytes. No driver is imported or executed. A
matching digest or an existing JSON pointer is not semantic verification.
"""

from __future__ import annotations

import hashlib
import json
import re
import stat
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import quote

import requests

from edgeloom import __version__, schemas

MAX_BYTES = 1024 * 1024
MAX_DOCUMENTS = 500
MAX_FETCH_ARTIFACTS = 100
CATALOG_REPOSITORY = "https://github.com/edgeloom-oss/edgeloom-catalog"


class CatalogError(ValueError):
    """Unsafe, malformed, or inconsistent catalog inputs."""


def _child(root: Path, relative: str) -> Path:
    parts = PurePosixPath(relative).parts
    if (
        not parts
        or relative.startswith("/")
        or "\\" in relative
        or ":" in relative
        or any(part in {".", "..", ".git"} for part in relative.split("/"))
        or any(not part for part in relative.split("/"))
        or any(ord(char) < 32 for char in relative)
    ):
        raise CatalogError(f"Unsafe relative path: {relative!r}")
    target = root
    for part in parts:
        target /= part
        if target.is_symlink():
            raise CatalogError(f"Refusing symbolic link: {relative}")
    if not target.resolve().is_relative_to(root.resolve()):
        raise CatalogError(f"Path escapes selected root: {relative}")
    return target


def read_bytes(root: Path, relative: str) -> bytes:
    target = _child(root, relative)
    try:
        if not stat.S_ISREG(target.stat().st_mode):
            raise CatalogError(f"Expected a regular file: {relative}")
        with target.open("rb") as stream:
            payload = stream.read(MAX_BYTES + 1)
    except OSError as exc:
        raise CatalogError(f"Cannot read {relative}: {exc}") from exc
    if len(payload) > MAX_BYTES:
        raise CatalogError(f"Document exceeds {MAX_BYTES} bytes: {relative}")
    return payload


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def render_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


@dataclass
class Catalog:
    root: Path
    sources: dict[str, dict]
    mappings: dict[str, dict]
    devices: dict[str, dict]
    corroborations: dict[str, dict]
    records: dict[str, dict]

    def artifact(self, reference: dict) -> tuple[dict, dict]:
        source = self.sources.get(reference["manifest_id"])
        if source is None:
            raise CatalogError(f"Unknown source manifest: {reference['manifest_id']}")
        artifact = next(
            (item for item in source["artifacts"] if item["id"] == reference["artifact_id"]),
            None,
        )
        if artifact is None:
            raise CatalogError(f"Unknown artifact: {reference['manifest_id']}/{reference['artifact_id']}")
        return source, artifact


def _check_lineage(record: dict, declared: set[str]) -> None:
    graph = {row["manifest_id"]: row["depends_on"] for row in record["lineage"]}
    if set(graph) != declared or any(set(deps) - declared for deps in graph.values()):
        raise CatalogError(f"{record['id']}: lineage must cover exactly the declared sources")
    visited, pending = set(), set()

    def visit(identifier: str) -> None:
        if identifier in pending:
            raise CatalogError(f"{record['id']}: cyclic source lineage")
        if identifier in visited:
            return
        pending.add(identifier)
        for dependency in graph[identifier]:
            visit(dependency)
        pending.remove(identifier)
        visited.add(identifier)

    for identifier in graph:
        visit(identifier)


def load_catalog(root: Path) -> Catalog:
    root = root.resolve()
    catalog = Catalog(root, {}, {}, {}, {}, {})
    documents: dict[str, tuple[dict, bytes]] = {}
    total_bytes = 0
    for folder, kind, target in (
        ("sources", schemas.SOURCE_MANIFEST, catalog.sources),
        ("mappings", schemas.CATALOG_MAPPING_SET, catalog.mappings),
        ("devices", schemas.CATALOG_DEVICE, catalog.devices),
        ("corroboration", schemas.CATALOG_CORROBORATION, catalog.corroborations),
    ):
        directory = _child(root, f"catalog/{folder}")
        if not directory.is_dir():
            if folder in {"devices", "corroboration"}:
                continue
            raise CatalogError(f"Missing catalog/{folder} directory")
        for path in sorted(directory.rglob("*")):
            relative = path.relative_to(root).as_posix()
            _child(root, relative)
            if not path.is_file() or path.suffix.lower() not in schemas.DOCUMENT_SUFFIXES:
                continue
            if len(documents) >= MAX_DOCUMENTS:
                raise CatalogError(f"Catalog exceeds {MAX_DOCUMENTS} documents")
            payload = read_bytes(root, relative)
            total_bytes += len(payload)
            if total_bytes > 16 * MAX_BYTES:
                raise CatalogError("Catalog input exceeds the 16 MiB aggregate budget")
            document = schemas.parse_document_bytes(payload, path=path)
            errors = schemas.validation_errors(document, kind=kind)
            if errors:
                raise CatalogError(f"{relative}: " + "; ".join(errors))
            identifier = document["id"]
            if identifier in catalog.records:
                raise CatalogError(f"Duplicate catalog record ID: {identifier}")
            target[identifier] = document
            catalog.records[identifier] = {"path": relative, "sha256": digest(payload)}
            documents[relative] = (document, payload)
    if not catalog.sources or not catalog.mappings:
        raise CatalogError("Expected at least one source and one mapping set")
    for mapping in catalog.mappings.values():
        referenced = {item["id"] for item in mapping["source_manifests"]}
        for reference in mapping["source_manifests"]:
            relative = reference["path"]
            if relative not in documents:
                raise CatalogError(f"{mapping['id']}: source path not indexed: {relative}")
            source, payload = documents[relative]
            if source.get("kind") != schemas.SOURCE_MANIFEST or source["id"] != reference["id"]:
                raise CatalogError(f"{mapping['id']}: source identity mismatch: {relative}")
            if digest(payload) != reference["sha256"]:
                raise CatalogError(f"{mapping['id']}: source manifest digest mismatch: {relative}")
        for item in mapping["nodes"] + mapping["evidence"]:
            if item["artifact"]["manifest_id"] not in referenced:
                raise CatalogError(f"{mapping['id']}: undeclared source reference")
            _, artifact = catalog.artifact(item["artifact"])
            if "layer" in item and item["layer"] != artifact["layer"]:
                raise CatalogError(f"{mapping['id']}/{item['id']}: artifact layer mismatch")
    for device in catalog.devices.values():
        catalog.artifact(device["identity_evidence"])
        if (
            sum(
                len(feature["mapping_ids"]) + len(feature.get("corroboration_ids", []))
                for feature in device["features"]
            )
            > 100
        ):
            raise CatalogError(f"{device['id']}: too many feature associations")
        for feature in device["features"]:
            for identifier in feature["mapping_ids"]:
                mapping = catalog.mappings.get(identifier)
                if mapping is None:
                    raise CatalogError(f"{device['id']}: unknown mapping set: {identifier}")
                if device["protocol"] not in mapping["scope"]["protocols"]:
                    raise CatalogError(f"{device['id']}: protocol does not match {identifier}")
            for identifier in feature.get("corroboration_ids", []):
                record = catalog.corroborations.get(identifier)
                if record is None:
                    raise CatalogError(f"{device['id']}: unknown corroboration: {identifier}")
                if record["device_id"] != device["id"] or record["feature_id"] != feature["id"]:
                    raise CatalogError(f"{identifier}: device/feature association mismatch")
    associated = {
        identifier
        for device in catalog.devices.values()
        for feature in device["features"]
        for identifier in feature.get("corroboration_ids", [])
    }
    for record in catalog.corroborations.values():
        if record["id"] not in associated:
            raise CatalogError(f"{record['id']}: orphan corroboration record")
        declared = {reference["id"] for reference in record["source_manifests"]}
        for reference in record["source_manifests"]:
            relative = reference["path"]
            if relative not in documents:
                raise CatalogError(f"{record['id']}: source path not indexed: {relative}")
            source, payload = documents[relative]
            if source.get("kind") != schemas.SOURCE_MANIFEST or source["id"] != reference["id"]:
                raise CatalogError(f"{record['id']}: source identity mismatch: {relative}")
            if digest(payload) != reference["sha256"]:
                raise CatalogError(f"{record['id']}: source manifest digest mismatch: {relative}")
        _check_lineage(record, declared)
        device = catalog.devices[record["device_id"]]
        for observation in record["observations"]:
            references = observation["references"] + (
                [observation["identity_evidence"]] if "identity_evidence" in observation else []
            )
            for reference in references:
                if reference["manifest_id"] not in declared:
                    raise CatalogError(f"{record['id']}: undeclared source reference")
                catalog.artifact(reference)
            # This checks the curator's declared match, not the source interpretation.
            for key, value in observation.get("identity_match", {}).items():
                expected = device["identifiers"].get(key)
                if key in {"manufacturer_id", "product_type", "product_id"}:
                    matches = (
                        expected is not None
                        and re.fullmatch(r"0x[0-9a-fA-F]{4}", value)
                        and int(value, 16) == int(expected, 16)
                    )
                else:
                    matches = value == expected
                if not matches:
                    raise CatalogError(f"{record['id']}: declared identity match differs from device")
    return catalog


def _atomic_bytes(target: Path, payload: bytes) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
        temporary.replace(target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def write_site(catalog: Catalog, index: dict, output: Path) -> int:
    """Replace only known generated files in a dedicated, marked output directory."""
    from edgeloom.catalog_site import generated_files

    output = output.resolve()
    if (
        output == catalog.root
        or catalog.root.is_relative_to(output)
        or output.is_relative_to(catalog.root / "catalog")
    ):
        raise CatalogError("Output must not overwrite catalog inputs or a parent directory")
    marker = ".edgeloom-catalog-output.json"
    files = generated_files(index)
    allowed = re.compile(
        r"(?:index\.html|catalog\.json|styles\.css|script\.js|devices/[a-z0-9-]+/index\.html|reports/[a-z0-9-]+\.md)"
    )
    previous: list[str] = []
    if output.exists() and any(output.iterdir()):
        try:
            previous = json.loads(read_bytes(output, marker))["files"]
        except (CatalogError, json.JSONDecodeError, KeyError, TypeError) as exc:
            raise CatalogError("Refusing nonempty output without a valid generated-output marker") from exc
        if (
            not isinstance(previous, list)
            or len(previous) > 2000
            or any(not isinstance(path, str) or not allowed.fullmatch(path) for path in previous)
        ):
            raise CatalogError("Invalid generated-output file list")
        for path in output.rglob("*"):
            relative = path.relative_to(output).as_posix()
            _child(output, relative)
            if path.is_file() and relative not in {*previous, marker}:
                raise CatalogError(f"Output contains an unrelated file: {relative}")
    if sum(len(value.encode()) for value in files.values()) > 32 * MAX_BYTES:
        raise CatalogError("Generated view exceeds the 32 MiB output budget")
    for relative in {*previous, *files, marker}:
        _child(output, relative)
    output.mkdir(parents=True, exist_ok=True)
    for relative, value in files.items():
        _atomic_bytes(_child(output, relative), value.encode("utf-8"))
    for relative in set(previous) - files.keys():
        _child(output, relative).unlink(missing_ok=True)
    _atomic_bytes(_child(output, marker), render_json({"files": sorted(files)}).encode())
    return len(files)


def artifact_url(source: dict, artifact: dict, *, raw: bool = False) -> str:
    repository = source["repository"]["url"]
    match = re.fullmatch(r"https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?", repository)
    if match is None:
        if raw:
            raise CatalogError("Pinned fetch currently supports public github.com repositories only")
        return repository
    owner, repo = match.groups()
    host = "https://raw.githubusercontent.com" if raw else "https://github.com"
    separator = "" if raw else "/blob"
    path = quote(artifact["path"], safe="/")
    return f"{host}/{owner}/{repo}{separator}/{source['repository']['commit']}/{path}"


def _cached(cache: Path, artifact: dict) -> bytes:
    payload = read_bytes(cache.resolve(), artifact["sha256"])
    if digest(payload) != artifact["sha256"]:
        raise CatalogError(f"Cached source digest mismatch: {artifact['id']}")
    return payload


def fetch_sources(catalog: Catalog, cache: Path) -> int:
    """Explicit bounded download. Only digest-matched bytes enter a local cache."""
    artifacts = [(source, item) for source in catalog.sources.values() for item in source["artifacts"]]
    if len(artifacts) > MAX_FETCH_ARTIFACTS:
        raise CatalogError(f"Fetch exceeds {MAX_FETCH_ARTIFACTS} artifacts; narrow the catalog")
    # Validate every destination URL before making any request.
    urls = [artifact_url(source, item, raw=True) for source, item in artifacts]
    cache = cache.resolve()
    if cache == catalog.root or cache.is_relative_to(catalog.root / "catalog"):
        raise CatalogError("Cache must be outside catalog input directories")
    cache.mkdir(parents=True, exist_ok=True)
    for (_, artifact), url in zip(artifacts, urls, strict=True):
        target = _child(cache, artifact["sha256"])
        if target.exists():
            _cached(cache, artifact)
            continue
        try:
            with requests.get(url, timeout=(5, 20), stream=True, allow_redirects=False) as response:
                if response.status_code != 200:
                    raise CatalogError(f"Fetch failed for {artifact['id']}: HTTP {response.status_code}")
                payload = bytearray()
                for chunk in response.iter_content(chunk_size=65536):
                    payload.extend(chunk)
                    if len(payload) > MAX_BYTES:
                        raise CatalogError(f"Fetched artifact exceeds {MAX_BYTES} bytes: {artifact['id']}")
        except requests.RequestException as exc:
            raise CatalogError(f"Fetch failed for {artifact['id']}: {exc}") from exc
        if digest(payload) != artifact["sha256"]:
            raise CatalogError(f"Upstream digest mismatch: {artifact['id']}; no cache entry written")
        # Preserve original UTF-8 bytes (including newlines), never normalize before hashing.
        try:
            bytes(payload).decode("utf-8")
        except UnicodeDecodeError as exc:
            raise CatalogError(f"Non-UTF-8 artifact: {artifact['id']}") from exc
        _atomic_bytes(target, bytes(payload))
        _cached(cache, artifact)
    return len(artifacts)


def _locator_status(payload: bytes | None, artifact: dict, locator: str) -> str:
    if payload is None:
        return "not-checked"
    if not locator.startswith("/") or any(char in locator for char in "[]|"):
        return "manual-review"
    if artifact["media_type"] in {"application/json5", "text/x-lua"}:
        return "manual-review"
    try:
        value = schemas.parse_document_bytes(payload, path=Path(artifact["path"]))
    except schemas.SchemaError:
        return "manual-review"
    for component in locator[1:].split("/"):
        if re.search(r"~(?![01])", component):
            return "manual-review"
        key = component.replace("~1", "/").replace("~0", "~")
        if isinstance(value, dict) and key in value:
            value = value[key]
        elif isinstance(value, list) and re.fullmatch(r"0|[1-9][0-9]*", key) and int(key) < len(value):
            value = value[int(key)]
        else:
            return "not-found"
    return "resolved"


def catalog_revision(root: Path) -> str:
    try:

        def git(*arguments: str) -> str:
            return subprocess.check_output(
                ["git", "-C", str(root), *arguments], stderr=subprocess.DEVNULL, timeout=5, text=True
            ).strip()

        if Path(git("rev-parse", "--show-toplevel")).resolve() != root.resolve():
            return "working-tree"
        if git("status", "--porcelain", "--", "catalog", "CORE_REVISION"):
            return "working-tree"
        return git("rev-parse", "HEAD")
    except (OSError, subprocess.SubprocessError):
        return "working-tree"


def build_index(catalog: Catalog, cache: Path | None = None) -> dict:
    revision = catalog_revision(catalog.root)
    records = catalog.records
    core_pin = None
    if (catalog.root / "CORE_REVISION").exists():
        core_pin = read_bytes(catalog.root, "CORE_REVISION").decode().strip()
        if not re.fullmatch(r"[0-9a-f]{40}", core_pin):
            raise CatalogError("CORE_REVISION must be a full lowercase commit ID")
    implementation = Path(__file__).parent
    policy_files = {
        name: digest(read_bytes(implementation, name))
        for name in ("catalog.py", "catalog_site.py", "schemas.py", "boundedyaml.py")
    }
    for name in ("page.html", "index.html", "device.html", "styles.css", "script.js"):
        policy_files[f"catalog_assets/{name}"] = digest(read_bytes(implementation / "catalog_assets", name))
    for kind in (
        schemas.SOURCE_MANIFEST,
        schemas.CATALOG_MAPPING_SET,
        schemas.CATALOG_DEVICE,
        schemas.CATALOG_CORROBORATION,
    ):
        policy_files[f"schema/{kind}"] = digest(schemas.schema_path(kind).read_bytes())
    sources = []
    for source in sorted(catalog.sources.values(), key=lambda item: item["id"]):
        artifacts = []
        for artifact in source["artifacts"]:
            if cache is not None:
                _cached(cache, artifact)
            artifacts.append(
                {
                    **artifact,
                    "url": artifact_url(source, artifact),
                    "byte_check": "matched" if cache else "not-checked",
                }
            )
        sources.append({**source, **records[source["id"]], "artifacts": artifacts})
    mapping_sets = []
    for mapping in sorted(catalog.mappings.values(), key=lambda item: item["id"]):
        locators = []
        for item in mapping["nodes"] + mapping["evidence"]:
            source, artifact = catalog.artifact(item["artifact"])
            status = _locator_status(_cached(cache, artifact) if cache else None, artifact, item["locator"])
            locators.append(
                {
                    "id": item["id"],
                    "url": artifact_url(source, artifact),
                    "locator": item["locator"],
                    "status": status,
                }
            )
        mapping_sets.append({**mapping, **records[mapping["id"]], "locator_checks": locators})
    devices = [
        {**device, **records[device["id"]]}
        for device in sorted(catalog.devices.values(), key=lambda item: item["id"])
    ]
    corroborations = []
    for record in sorted(catalog.corroborations.values(), key=lambda item: item["id"]):
        observations = []
        for observation in record["observations"]:
            checks = []
            for reference in observation["references"] + (
                [observation["identity_evidence"]] if "identity_evidence" in observation else []
            ):
                source, artifact = catalog.artifact(reference)
                checks.append(
                    {
                        **reference,
                        "url": artifact_url(source, artifact),
                        "status": _locator_status(
                            _cached(cache, artifact) if cache else None, artifact, reference["locator"]
                        ),
                    }
                )
            observations.append({**observation, "locator_checks": checks})
        corroborations.append({**record, **records[record["id"]], "observations": observations})
    return {
        "report_version": "0.1",
        "catalog_repository": CATALOG_REPOSITORY,
        "catalog_revision": revision,
        "input_digest": digest(
            render_json({"records": records, "declared_core_revision": core_pin}).encode()
        ),
        "generator": {
            "policy": "catalog/v0.1",
            "package_version_label": __version__,
            "version_label_is_not_release_attestation": True,
            "implementation_digest": digest(render_json(policy_files).encode()),
            "declared_core_revision": core_pin,
        },
        "checks": {
            "contracts": "passed",
            "cross_record_references": "passed",
            "manifest_digests": "matched",
            "source_bytes": "matched" if cache else "not-checked",
        },
        "counts": {
            "devices": len(devices),
            "mapping_sets": len(mapping_sets),
            "assertions": sum(len(item["mappings"]) for item in mapping_sets),
            "corroboration_records": len(corroborations),
            "source_observations": sum(len(item["observations"]) for item in corroborations),
        },
        "devices": devices,
        "mapping_sets": mapping_sets,
        "sources": sources,
        "corroborations": corroborations,
        "limitations": [
            "Device associations, classifications, license labels, and review states are "
            "catalog-author declarations, not independently authenticated by this build.",
            "Resolved locators establish field existence only, not the interpretation, completeness, "
            "runtime behavior, SDF conformance, or interoperability of an artifact.",
            "Selectors, JSON5 and Lua locators need manual review. No upstream Lua is executed.",
            "Profile absence is not whole-driver or UI absence. A missing property in a particular "
            "SDF model is not a limitation of SDF itself.",
            "Hardware-evidence links are reported observations, not tests performed by this tool. "
            "No patch availability is inferred.",
            "Cross-source observations and lineage are curator declarations. Shared backends are "
            "not independent evidence; upstream test fixtures are not physical-device tests or "
            "independent EdgeLoom review. No source count promotes a candidate.",
        ],
    }


def device_markdown(index: dict, device: dict) -> str:
    def plain(text: str) -> str:
        # Prevent author text from injecting links, HTML, or tables into a generated report.
        return re.sub(r"([\\`*_{}\[\]()<>#+.!|~-])", r"\\\1", text.replace("\n", " "))

    mappings = {item["id"]: item for item in index["mapping_sets"]}
    corroborations = {item["id"]: item for item in index["corroborations"]}
    hardware = "reported links; not authenticated" if device["hardware_evidence"] else "none recorded"
    lines = [
        f"# {plain(device['manufacturer'])} {plain(device['model'])}",
        "",
        "Source-level evidence, not a compatibility or installation recommendation.",
        "",
        f"- Protocol: {device['protocol']}",
        f"- Identifiers: {plain(render_json(device['identifiers']).strip())}",
        f"- Firmware: {plain(device['firmware'])}",
        f"- Catalog revision: {index['catalog_revision']}",
        f"- Input digest: {index['input_digest']}",
        f"- Source byte check: {index['checks']['source_bytes']}",
        f"- Hardware evidence: {hardware}",
        "",
    ]
    for feature in device["features"]:
        lines += [f"## {plain(feature['title'])}", "", plain(feature["summary"]), ""]
        for identifier in feature["mapping_ids"]:
            mapping = mappings[identifier]
            lines += [
                f"### {plain(mapping['title'])}",
                "",
                f"Review lifecycle: {mapping['review']['lifecycle']} (declared).",
                "",
            ]
            for assertion in mapping["mappings"]:
                lines += [
                    f"- {plain(assertion['id'])}: {assertion['classification']}"
                    + (f" / {assertion['unbound_reason']}" if "unbound_reason" in assertion else "")
                ]
                lines += [f"  - Limit: {plain(limit)}" for limit in assertion.get("limitations", [])]
            lines += [""] + [f"- Limit: {plain(limit)}" for limit in mapping.get("limitations", [])] + [""]
            for evidence in mapping["evidence"]:
                locator = next(item for item in mapping["locator_checks"] if item["id"] == evidence["id"])
                lines += [
                    f"- Evidence: {plain(evidence['summary'])}",
                    f"  - [Pinned source]({locator['url']}); "
                    f"locator: {plain(locator['locator'])}; check: {locator['status']}",
                ]
            lines += [""]
        for identifier in feature.get("corroboration_ids", []):
            record = corroborations[identifier]
            lines += [
                f"### {plain(record['title'])}",
                "",
                plain(record["summary"]),
                "",
                "Candidate external corroboration; not independent EdgeLoom review.",
                "",
            ]
            for observation in record["observations"]:
                lines += [
                    f"- {plain(observation['platform'])}: {observation['relationship']} / "
                    f"{observation['scope']} / {observation['evidence_kind']}",
                    f"  - {plain(observation['claim'])}",
                    "  - Declared identity match: "
                    + plain(render_json(observation.get("identity_match", {})).strip()),
                ]
                lines += [f"  - Condition: {plain(value)}" for value in observation["conditions"]]
                for check in observation["locator_checks"]:
                    lines += [
                        f"  - [Pinned source]({check['url']}): {plain(check['locator'])}; {check['status']}"
                    ]
            lines += ["", "Declared lineage (not an independence score):", ""]
            lines += [
                f"- {plain(row['manifest_id'])}: family {plain(row['family'])}; "
                f"depends on {plain(', '.join(row['depends_on']) or 'none declared in this record')}"
                for row in record["lineage"]
            ]
            lines += [""] + [f"- Limit: {plain(value)}" for value in record["limitations"]] + [""]
        lines += ["Next steps:", ""] + [f"- {plain(step)}" for step in feature["next_steps"]] + [""]
    lines += ["## Boundaries", ""] + [
        f"- {plain(limit)}" for limit in device["limitations"] + index["limitations"]
    ]
    return "\n".join(lines) + "\n"
