"""Bounded, offline Device Evidence Bundle assembly and integrity checking."""

from __future__ import annotations

import io
import re
import stat
import zipfile
import zlib
from dataclasses import dataclass
from pathlib import Path

from edgeloom import __version__, catalog, schemas

FORMAT = "device-evidence-bundle/0.1"
MAX_INPUT_BYTES = 16 * catalog.MAX_BYTES
MAX_PACKAGE_BYTES = 32 * catalog.MAX_BYTES
MAX_MEMBER_BYTES = 8 * catalog.MAX_BYTES
MAX_MEMBERS = 512
FOLDERS = {
    "sources": schemas.SOURCE_MANIFEST,
    "mappings": schemas.CATALOG_MAPPING_SET,
    "devices": schemas.CATALOG_DEVICE,
    "corroboration": schemas.CATALOG_CORROBORATION,
    "documents": schemas.DOCUMENT_SOURCE,
    "observations": schemas.CATALOG_OBSERVATION,
}


class BundleError(ValueError):
    """An invalid record, reference, output path or package."""


@dataclass
class Bundle:
    root: Path | None
    manifest_path: str
    manifest: dict
    records: dict[str, dict]
    payloads: dict[str, bytes]


def _validate(payload: bytes, path: str, kind: str) -> dict:
    if len(payload) > catalog.MAX_BYTES:
        raise BundleError(f"Record exceeds {catalog.MAX_BYTES} bytes: {path}")
    document = schemas.parse_document_bytes(payload, path=Path(path))
    errors = schemas.validation_errors(document, kind=kind)
    if errors:
        raise BundleError(f"{path}: " + "; ".join(errors))
    return document


def _record_kind(path: str) -> str:
    catalog._child(Path("/bundle"), path)
    parts = path.split("/")
    if len(parts) < 3 or parts[0] != "catalog" or parts[1] not in FOLDERS:
        raise BundleError(f"Unsupported record location: {path}")
    if Path(path).suffix not in schemas.DOCUMENT_SUFFIXES:
        raise BundleError(f"Unsupported record suffix: {path}")
    return FOLDERS[parts[1]]


def _pointer(document: object, locator: str) -> object:
    if locator == "#":
        return document
    if not locator.startswith("#/") or re.search(r"~(?![01])", locator):
        raise BundleError(f"Invalid record JSON pointer: {locator}")
    try:
        for token in locator[2:].split("/"):
            token = token.replace("~1", "/").replace("~0", "~")
            if isinstance(document, list):
                if not re.fullmatch(r"0|[1-9][0-9]*", token):
                    raise KeyError(token)
                document = document[int(token)]
            elif isinstance(document, dict):
                document = document[token]
            else:
                raise KeyError(token)
    except (KeyError, IndexError, ValueError) as exc:
        raise BundleError(f"Record JSON pointer not found: {locator}") from exc
    return document


def _same_subject(subject: dict, other: dict, context: str) -> None:
    if subject.get("identity_scope", "exact-model") != other.get("identity_scope", "exact-model"):
        raise BundleError(f"{context}: subject identity scope mismatch")
    for key in ("manufacturer", "model", "protocol"):
        if subject[key] != other[key]:
            raise BundleError(f"{context}: subject {key} mismatch")
    for key, value in other.get("identifiers", {}).items():
        if subject["identifiers"].get(key) != value:
            raise BundleError(f"{context}: subject identifier mismatch: {key}")
    if "firmware" in other and (
        subject["firmware"] != "unknown"
        and other["firmware"] != "unknown"
        and subject["firmware"] != other["firmware"]
    ):
        raise BundleError(f"{context}: firmware mismatch")


def _check_records(bundle: Bundle) -> None:
    manifest, records = bundle.manifest, bundle.records
    locked = {row["id"]: row for row in manifest["records"]}
    dependencies: dict[str, set[str]] = {identifier: set() for identifier in records}

    def need(identifier: str, owner: str) -> dict:
        if identifier not in records:
            raise BundleError(f"{owner}: missing referenced record {identifier}")
        return records[identifier]

    def artifact(reference: dict, owner: str) -> dict:
        identifier = reference["manifest_id"]
        if "source_manifests" in records[owner] and identifier not in {
            row["id"] for row in records[owner]["source_manifests"]
        }:
            raise BundleError(f"{owner}: artifact source is not declared")
        source = need(identifier, owner)
        dependencies[owner].add(identifier)
        if source["kind"] != schemas.SOURCE_MANIFEST:
            raise BundleError(f"{owner}: reference is not a source manifest")
        for item in source["artifacts"]:
            if item["id"] == reference["artifact_id"]:
                return item
        raise BundleError(f"{owner}: unknown artifact {reference['artifact_id']}")

    for identifier, record in records.items():
        kind = record["kind"]
        if kind in {schemas.CATALOG_MAPPING_SET, schemas.CATALOG_CORROBORATION}:
            for ref in record["source_manifests"]:
                source = need(ref["id"], identifier)
                dependencies[identifier].add(ref["id"])
                if (
                    source["kind"] != schemas.SOURCE_MANIFEST
                    or locked[ref["id"]]["path"] != ref["path"]
                    or locked[ref["id"]]["sha256"] != ref["sha256"]
                ):
                    raise BundleError(f"{identifier}: source manifest lock mismatch")
            if kind == schemas.CATALOG_MAPPING_SET:
                if manifest["subject"]["protocol"] not in record["scope"]["protocols"]:
                    raise BundleError(f"{identifier}: mapping protocol mismatch")
                for node in record["nodes"] + record["evidence"]:
                    item = artifact(node["artifact"], identifier)
                    if "layer" in node and node["layer"] != item["layer"]:
                        raise BundleError(f"{identifier}: evidence layer mismatch")
            else:
                catalog._check_lineage(record, {row["id"] for row in record["source_manifests"]})
                device = need(record["device_id"], identifier)
                dependencies[identifier].add(record["device_id"])
                if device["kind"] != schemas.CATALOG_DEVICE:
                    raise BundleError(f"{identifier}: device reference has wrong kind")
                _same_subject(manifest["subject"], device, identifier)
                feature = next((f for f in device["features"] if f["id"] == record["feature_id"]), None)
                if feature is None or identifier not in feature.get("corroboration_ids", []):
                    raise BundleError(f"{identifier}: device feature association mismatch")
                for observation in record["observations"]:
                    for ref in observation["references"]:
                        artifact(ref, identifier)
                    if "identity_evidence" in observation:
                        artifact(observation["identity_evidence"], identifier)
                    for key, value in observation.get("identity_match", {}).items():
                        if device["identifiers"].get(key) != value:
                            raise BundleError(f"{identifier}: declared identity mismatch")
        elif kind == schemas.CATALOG_DEVICE:
            _same_subject(manifest["subject"], record, identifier)
            artifact(record["identity_evidence"], identifier)
            connection_ids = [row["id"] for row in record.get("connections", [])]
            if len(connection_ids) != len(set(connection_ids)):
                raise BundleError(f"{identifier}: duplicate connection id")
            for connection in record.get("connections", []):
                for reference in connection["references"]:
                    artifact(reference, identifier)
            for feature in record["features"]:
                for reference in feature.get("source_references", []):
                    artifact(reference, identifier)
                for target in feature["mapping_ids"] + feature.get("corroboration_ids", []):
                    dependency = need(target, identifier)
                    expected = (
                        schemas.CATALOG_MAPPING_SET
                        if target in feature["mapping_ids"]
                        else schemas.CATALOG_CORROBORATION
                    )
                    if dependency["kind"] != expected:
                        raise BundleError(f"{identifier}: feature reference kind mismatch")
                    if expected == schemas.CATALOG_CORROBORATION and (
                        dependency["device_id"] != identifier or dependency["feature_id"] != feature["id"]
                    ):
                        raise BundleError(f"{identifier}: corroboration feature association mismatch")
                    dependencies[identifier].add(target)
        elif kind == schemas.CATALOG_OBSERVATION:
            _same_subject(manifest["subject"], record["subject"], identifier)
            if record["feature_id"] not in {f["id"] for f in manifest["features"]}:
                raise BundleError(f"{identifier}: observation feature mismatch")
        elif kind == schemas.DOCUMENT_SOURCE and record["applicability"]["scope"] == "exact-model":
            for key in ("manufacturer", "model"):
                if record["applicability"][key] != manifest["subject"][key]:
                    raise BundleError(f"{identifier}: document applicability mismatch")

    direct: set[str] = set()
    device_id = manifest.get("device_record_id")
    if device_id:
        if need(device_id, "bundle")["kind"] != schemas.CATALOG_DEVICE:
            raise BundleError("device_record_id must refer to a catalog-device")
        direct.add(device_id)
    for feature in manifest["features"]:
        for identifier in feature["record_ids"]:
            record = need(identifier, feature["id"])
            if record["kind"] in {schemas.CATALOG_OBSERVATION, schemas.CATALOG_CORROBORATION}:
                if record["feature_id"] != feature["id"]:
                    raise BundleError(f"{identifier}: bundle feature association mismatch")
            direct.add(identifier)
        if not feature["record_ids"] and not feature["gaps"]:
            raise BundleError(f"{feature['id']}: empty feature needs an explicit gap")
        for note in feature["implementation_notes"]:
            for ref in note["references"]:
                if ref["record_id"] not in feature["record_ids"]:
                    raise BundleError(f"{note['id']}: explanation must cite a feature record")
                _pointer(records[ref["record_id"]], ref["locator"])

    reached: set[str] = set()
    pending = list(direct)
    while pending:
        identifier = pending.pop()
        if identifier not in reached:
            reached.add(identifier)
            pending.extend(dependencies[identifier] - reached)
    if reached != set(records):
        raise BundleError("Package includes records outside its feature dependency closure")

    for review in manifest["reviews"]:
        if review["reviewer"] == manifest["author"]:
            raise BundleError("Bundle author cannot supply independent review")
        for ref in review["record_refs"]:
            record = need(ref["record_id"], "review")
            if ref["sha256"] != locked[ref["record_id"]]["sha256"]:
                raise BundleError("Stale review: record digest changed")
            author = record.get("reported_by", record.get("contributed_by"))
            author = record.get("review", {}).get("author", author)
            if author == review["reviewer"]:
                raise BundleError("Record author cannot supply independent review")
    for credit in manifest["credits"]:
        for identifier in credit["record_ids"]:
            need(identifier, "credit")
        if "review" in credit["roles"] and not any(
            row["reviewer"] == credit["identity"]
            and set(credit["record_ids"]).issubset({r["record_id"] for r in row["record_refs"]})
            for row in manifest["reviews"]
        ):
            raise BundleError("Review credit requires a matching scoped review reference")


def _assemble(root: Path | None, manifest_path: str, payloads: dict[str, bytes]) -> Bundle:
    if len({name.casefold() for name in payloads}) != len(payloads):
        raise BundleError("Case-colliding record paths are not portable")
    if sum(map(len, payloads.values())) > MAX_INPUT_BYTES:
        raise BundleError("Bundle records exceed the aggregate byte limit")
    manifest = _validate(payloads[manifest_path], manifest_path, schemas.DEVICE_EVIDENCE_BUNDLE)
    records = {}
    for entry in manifest["records"]:
        path = entry["path"]
        if path not in payloads:
            raise BundleError(f"Missing locked record: {path}")
        if catalog.digest(payloads[path]) != entry["sha256"]:
            raise BundleError(f"Record digest mismatch: {path}")
        record = _validate(payloads[path], path, _record_kind(path))
        if record["id"] != entry["id"]:
            raise BundleError(f"Record identity mismatch: {path}")
        records[entry["id"]] = record
    bundle = Bundle(root, manifest_path, manifest, records, payloads)
    _check_records(bundle)
    return bundle


def load_bundle(root: Path, identifier: str) -> Bundle:
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,119}", identifier):
        raise BundleError("Invalid bundle identifier")
    root = root.resolve()
    candidates = [f"catalog/bundles/{identifier}{suffix}" for suffix in (".json", ".yaml", ".yml")]
    candidates = [path for path in candidates if catalog._child(root, path).exists()]
    if len(candidates) != 1:
        raise BundleError("Expected one bundle manifest with that ID")
    path = candidates[0]
    payloads = {path: catalog.read_bytes(root, path)}
    manifest = _validate(payloads[path], path, schemas.DEVICE_EVIDENCE_BUNDLE)
    if manifest["id"] != identifier:
        raise BundleError("Bundle filename and identifier disagree")
    for entry in manifest["records"]:
        _record_kind(entry["path"])
        payloads[entry["path"]] = catalog.read_bytes(root, entry["path"])
        if sum(map(len, payloads.values())) > MAX_INPUT_BYTES:
            raise BundleError("Bundle records exceed the aggregate byte limit")
    return _assemble(root, path, payloads)


def _core_pin(root: Path | None) -> str | None:
    if root is None or not (root / "CORE_REVISION").exists():
        return None
    pin = catalog.read_bytes(root, "CORE_REVISION").decode("ascii").strip()
    if not re.fullmatch(r"[0-9a-f]{40}", pin):
        raise BundleError("CORE_REVISION must contain a full commit ID")
    return pin


def load_all(root: Path) -> list[Bundle]:
    """Load optional bundles; reject ambiguous IDs and unsafe input directories."""
    folder = catalog._child(root.resolve(), "catalog/bundles")
    if not folder.exists():
        return []
    identifiers = []
    for path in sorted(folder.iterdir()):
        if path.suffix in schemas.DOCUMENT_SUFFIXES:
            if path.stem in identifiers:
                raise BundleError(f"Duplicate bundle ID: {path.stem}")
            identifiers.append(path.stem)
        if len(identifiers) > 100:
            raise BundleError("Catalog exceeds 100 bundles")
    loaded = []
    total_bytes = 0
    for identifier in identifiers:
        bundle = load_bundle(root, identifier)
        total_bytes += sum(map(len, bundle.payloads.values()))
        if total_bytes > MAX_INPUT_BYTES:
            raise BundleError("Catalog bundle inputs exceed aggregate byte limit")
        loaded.append(bundle)
    return loaded


def _schema_files(bundle: Bundle) -> dict[str, bytes]:
    files = {}
    for record in [bundle.manifest, *bundle.records.values()]:
        path = schemas.document_schema_path(record)
        files[f"schema/{path.name}"] = path.read_bytes()
    return files


def build_report(bundle: Bundle) -> dict:
    root = Path(__file__).parent
    generator_files = ["bundles.py", "bundle_site.py", "schemas.py", "boundedyaml.py", "catalog.py"]
    generator_files.append("catalog_assets/bundle.css")
    generator = {name: catalog.digest(catalog.read_bytes(root, name)) for name in generator_files}
    for name, payload in _schema_files(bundle).items():
        generator[name] = catalog.digest(payload)
    input_hashes = {path: catalog.digest(payload) for path, payload in sorted(bundle.payloads.items())}
    core_pin = _core_pin(bundle.root)
    return {
        "format": FORMAT,
        "bundle": bundle.manifest,
        "records": bundle.records,
        "catalog_revision": catalog.catalog_revision(bundle.root) if bundle.root else "working-tree",
        "declared_core_revision": core_pin,
        "input_digest": catalog.digest(
            catalog.render_json({"records": input_hashes, "core_pin": core_pin}).encode()
        ),
        "generator": {
            "package_version_label": __version__,
            "version_label_is_not_release_attestation": True,
            "implementation_digest": catalog.digest(catalog.render_json(generator).encode()),
        },
        "checks": {
            "contracts": "passed",
            "record_digests": "matched",
            "references": "passed",
            "upstream_bytes": "not-checked",
            "review_identity": "not-authenticated",
            "hardware": "not-tested-by-this-tool",
        },
    }


def _checksums(files: dict[str, bytes]) -> bytes:
    return "".join(f"{catalog.digest(payload)}  {name}\n" for name, payload in sorted(files.items())).encode()


def package_files(bundle: Bundle) -> dict[str, bytes]:
    from edgeloom.bundle_site import generated_files

    report = build_report(bundle)
    files = dict(bundle.payloads)
    files["report.json"] = catalog.render_json(report).encode()
    for name, text in generated_files(report).items():
        if name not in {"index.html", "report.md", "bundle.css"}:
            raise BundleError(f"Unexpected renderer file: {name}")
        files[name] = text.encode()
    files.update(_schema_files(bundle))
    if sum(map(len, files.values())) > MAX_PACKAGE_BYTES or any(
        len(p) > MAX_MEMBER_BYTES for p in files.values()
    ):
        raise BundleError("Generated package exceeds byte limit")
    lock = {
        "format": FORMAT,
        "bundle_path": bundle.manifest_path,
        "files": {name: catalog.digest(payload) for name, payload in sorted(files.items())},
    }
    files["package.json"] = catalog.render_json(lock).encode()
    files["checksums.txt"] = _checksums(files)
    return files


def _zip_bytes(files: dict[str, bytes]) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, payload in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, payload, compresslevel=9)
    payload = stream.getvalue()
    if len(payload) > MAX_PACKAGE_BYTES:
        raise BundleError("Archive exceeds byte limit")
    return payload


def _output_target(bundle: Bundle, target: Path) -> Path:
    if target.is_symlink():
        raise BundleError("Output must not be a symbolic link")
    target = target.resolve()
    if bundle.root:
        inputs = bundle.root / "catalog"
        if target.is_relative_to(inputs) or inputs.is_relative_to(target):
            raise BundleError("Output overlaps canonical catalog inputs")
        if target == bundle.root / "CORE_REVISION":
            raise BundleError("Output overlaps core pin")
    return target


def export_bundle(bundle: Bundle, output: Path) -> int:
    output = _output_target(bundle, output)
    payload = _zip_bytes(package_files(bundle))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as stream:
        stream.write(payload)
    return len(payload)


def build_bundle(bundle: Bundle, output: Path) -> int:
    output = _output_target(bundle, output)
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise BundleError("Report output must be a new or empty directory")
    files = package_files(bundle)
    files["bundle.zip"] = _zip_bytes(files)
    output.mkdir(parents=True, exist_ok=True)
    for name, payload in sorted(files.items()):
        target = catalog._child(output, name)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(payload)
    return len(files)


def verify_package(path: Path) -> dict:
    """Verify bounded package integrity and record semantics without extraction."""
    with path.open("rb") as stream:
        raw = stream.read(MAX_PACKAGE_BYTES + 1)
    if len(raw) > MAX_PACKAGE_BYTES:
        raise BundleError("Archive exceeds byte limit")
    files: dict[str, bytes] = {}
    folded_names: set[str] = set()
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            members = archive.infolist()
            if len(members) > MAX_MEMBERS or sum(i.file_size for i in members) > MAX_PACKAGE_BYTES:
                raise BundleError("Archive exceeds member/expanded-byte limit")
            for member in members:
                name = member.filename
                catalog._child(Path("/bundle"), name)
                mode = member.external_attr >> 16
                if (
                    name.casefold() in folded_names
                    or name != member.orig_filename
                    or member.is_dir()
                    or member.flag_bits & 1
                    or member.file_size > MAX_MEMBER_BYTES
                    or (stat.S_IFMT(mode) not in {0, stat.S_IFREG})
                    or member.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}
                ):
                    raise BundleError(f"Unsafe or duplicate archive member: {name}")
                with archive.open(member) as stream:
                    payload = stream.read(MAX_MEMBER_BYTES + 1)
                if len(payload) != member.file_size:
                    raise BundleError(f"Archive member size mismatch: {name}")
                files[name] = payload
                folded_names.add(name.casefold())
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError, zlib.error, EOFError) as exc:
        raise BundleError("Unreadable or corrupt ZIP package") from exc
    try:
        lock = schemas.parse_document_bytes(files["package.json"], path=Path("package.json"))
        if (
            not isinstance(lock, dict)
            or set(lock) != {"format", "bundle_path", "files"}
            or lock["format"] != FORMAT
        ):
            raise BundleError("Unknown package format or lock structure")
        expected = lock["files"]
        if not isinstance(expected, dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in expected.items()
        ):
            raise BundleError("Invalid package file inventory")
        if set(files) != set(expected) | {"package.json", "checksums.txt"} or {
            "package.json",
            "checksums.txt",
        } & set(expected):
            raise BundleError("Missing or unexpected package members")
        for name, digest in expected.items():
            if catalog.digest(files[name]) != digest:
                raise BundleError(f"Package digest mismatch: {name}")
        if files["checksums.txt"] != _checksums({n: p for n, p in files.items() if n != "checksums.txt"}):
            raise BundleError("Package checksum list mismatch")
        manifest_path = lock["bundle_path"]
        if not isinstance(manifest_path, str) or not re.fullmatch(
            r"catalog/bundles/[a-z0-9][a-z0-9._-]*\.(json|yaml|yml)", manifest_path
        ):
            raise BundleError("Invalid bundle manifest path")
        manifest = _validate(files[manifest_path], manifest_path, schemas.DEVICE_EVIDENCE_BUNDLE)
        paths = {manifest_path} | {r["path"] for r in manifest["records"]}
        bundle = _assemble(None, manifest_path, {n: files[n] for n in paths})
        if Path(manifest_path).stem != manifest["id"]:
            raise BundleError("Bundle filename and identifier disagree")
        schema_files = _schema_files(bundle)
        schema_paths = set(schema_files)
        if set(expected) != paths | schema_paths | {"index.html", "report.md", "report.json", "bundle.css"}:
            raise BundleError("Package inventory does not match its record closure")
        for name, payload in schema_files.items():
            if files[name] != payload:
                raise BundleError("Schema snapshot differs from this verifier; use the declared core pin")
        report = schemas.parse_document_bytes(files["report.json"], path=Path("report.json"))
        if (
            not isinstance(report, dict)
            or report.get("format") != FORMAT
            or report.get("bundle") != manifest
            or report.get("records") != bundle.records
        ):
            raise BundleError("Report and canonical records disagree")
        hashes = {n: catalog.digest(p) for n, p in sorted(bundle.payloads.items())}
        actual_input = catalog.digest(
            catalog.render_json(
                {"records": hashes, "core_pin": report.get("declared_core_revision")}
            ).encode()
        )
        if report.get("input_digest") != actual_input:
            raise BundleError("Report input digest mismatch")
        pin = report.get("declared_core_revision")
        revision = report.get("catalog_revision")
        if (pin is not None and (not isinstance(pin, str) or not re.fullmatch(r"[0-9a-f]{40}", pin))) or (
            revision != "working-tree"
            and (not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision))
        ):
            raise BundleError("Invalid declared revision in report")
        # Re-derive all claims and rendered files from trusted local policy and
        # the original canonical bytes, not the report's asserted checks.
        expected_report = build_report(bundle)
        expected_report.update(
            catalog_revision=revision, declared_core_revision=pin, input_digest=actual_input
        )
        if report != expected_report:
            raise BundleError("Report policy or checks differ from this verifier; use the declared core pin")
        from edgeloom.bundle_site import generated_files

        for name, rendered in generated_files(expected_report).items():
            if files[name] != rendered.encode():
                raise BundleError(f"Rendered report differs from canonical records: {name}")
    except (KeyError, TypeError) as exc:
        raise BundleError("Package is missing required structured content") from exc
    return {
        "id": manifest["id"],
        "version": manifest["version"],
        "files": len(files),
        "integrity": "passed",
        "authenticity": "not-established",
        "hardware": "not-tested-by-this-tool",
    }
