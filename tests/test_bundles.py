"""Device Evidence Bundle integrity, scoped provenance, and hostile-input checks.

Every subject and observation below is synthetic test data, not a hardware result.
"""

from __future__ import annotations

import copy
import hashlib
import json
import socket
import stat
import struct
import zipfile
from pathlib import Path

import pytest

from edgeloom import bundles, catalog, schemas
from edgeloom.cli import main

ID = "synthetic-lock-battery"
MANIFEST = f"catalog/bundles/{ID}.json"
DOCUMENT = "catalog/documents/synthetic-manual.json"
OBSERVATION = "catalog/observations/synthetic-observation.json"


def encoded(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def write_record(root: Path, path: str, record: dict) -> dict:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = encoded(record)
    target.write_bytes(payload)
    return {"id": record["id"], "path": path, "sha256": digest(payload)}


def read_record(root: Path, path: str) -> dict:
    return json.loads((root / path).read_bytes())


def subject() -> dict:
    return {
        "manufacturer": "Synthetic Test Company",
        "model": "Synthetic Lock",
        "protocol": "zigbee",
        "identifiers": {"model_id": "synthetic-lock"},
        "firmware": "unknown",
        "scope_notes": ["Test fixture only; no physical device."],
    }


def document() -> dict:
    return {
        "kind": "document-source",
        "schema_version": "0.1",
        "id": "synthetic-manual",
        "title": "Synthetic fixture manual",
        "publisher": "Synthetic Test Company",
        "url": "https://example.invalid/synthetic-manual.pdf",
        "document_version": "fixture-1",
        "accessed_at": "2026-10-08",
        "source_maturity": "experimental",
        "applicability": {
            "manufacturer": "Synthetic Test Company",
            "model": "Synthetic Lock",
            "scope": "exact-model",
            "notes": ["Synthetic metadata, not a genuine manufacturer publication."],
        },
        "locations": [{"id": "battery", "locator": "Page 2", "description": "Synthetic battery claim"}],
        "capture": {"mode": "link-only"},
        "rights": {"redistribution": "not-granted", "notice": "Do not redistribute upstream bytes."},
        "contributed_by": "fixture-researcher",
        "limitations": ["This URL and document are synthetic; no upstream download was performed."],
    }


def observation() -> dict:
    return {
        "kind": "catalog-observation",
        "schema_version": "0.1",
        "id": "synthetic-observation",
        "subject": subject(),
        "feature_id": "battery",
        "method": "simulation",
        "data_origin": "synthetic-example",
        "environment": {
            "platform": "synthetic fixture",
            "platform_version": "1",
            "driver_revision": "synthetic, not a released driver",
            "setup": "In-memory example only; no connected equipment.",
        },
        "procedure": ["Supply a synthetic input to a fixture."],
        "expected": "A synthetic low-battery label.",
        "observed": "A synthetic low-battery label.",
        "outcome": "pass",
        "repetitions": 1,
        "observed_at": "2026-10-08T12:00:00Z",
        "reported_by": "fixture-observer",
        "evidence": [],
        "review": {"lifecycle": "candidate"},
        "limitations": ["Synthetic example only; no physical-device experiment."],
    }


@pytest.fixture
def bundle_root(tmp_path: Path) -> Path:
    root = tmp_path / "catalog-input"
    reference = write_record(root, DOCUMENT, document())
    manifest = {
        "kind": "device-evidence-bundle",
        "schema_version": "0.1",
        "id": ID,
        "version": "0.1.0",
        "title": "Synthetic lock battery explanation",
        "subject": subject(),
        "author": "fixture-author",
        "license": "Apache-2.0",
        "publication_status": "candidate",
        "records": [reference],
        "features": [
            {
                "id": "battery",
                "title": "Battery reporting",
                "summary": "A synthetic explanation with an explicit hardware evidence gap.",
                "record_ids": [reference["id"]],
                "implementation_notes": [
                    {
                        "id": "battery-explanation",
                        "decision": "Do not infer raw attribute scaling from a user manual.",
                        "rationale": "User-facing documentation does not establish wire-level behavior.",
                        "references": [
                            {
                                "record_id": reference["id"],
                                "locator": "#/locations/0",
                                "relationship": "context",
                            }
                        ],
                        "conditions": ["No raw device behavior was observed."],
                    }
                ],
                "test_plan": [
                    {
                        "id": "collect-hardware-evidence",
                        "question": "What does an actual device report?",
                        "procedure": ["A future contributor should record device identity and input/output."],
                        "requested_evidence": ["Redacted logs and firmware version."],
                    }
                ],
                "gaps": ["No physical-device observations or independent review."],
            }
        ],
        "reviews": [],
        "credits": [
            {"identity": "fixture-researcher", "roles": ["source-research"], "record_ids": [reference["id"]]}
        ],
        "history": [{"version": "0.1.0", "summary": "Synthetic draft fixture."}],
        "limitations": ["This fixture is not device compatibility evidence."],
    }
    write_record(root, MANIFEST, manifest)
    return root


def update_manifest(root: Path, mutate) -> None:
    manifest = read_record(root, MANIFEST)
    mutate(manifest)
    write_record(root, MANIFEST, manifest)


def update_document(root: Path, mutate) -> None:
    record = read_record(root, DOCUMENT)
    mutate(record)
    reference = write_record(root, DOCUMENT, record)
    update_manifest(root, lambda manifest: manifest["records"].__setitem__(0, reference))


def add_observation(root: Path, record: dict | None = None) -> None:
    reference = write_record(root, OBSERVATION, record or observation())
    manifest = read_record(root, MANIFEST)
    manifest["records"].append(reference)
    manifest["features"][0]["record_ids"].append(reference["id"])
    write_record(root, MANIFEST, manifest)


def review(root: Path, reviewer: str = "independent-fixture-reviewer") -> dict:
    reference = read_record(root, MANIFEST)["records"][0]
    return {
        "reviewer": reviewer,
        "reviewed_at": "2026-10-08T14:00:00Z",
        "decision": "commented",
        "scope": "Synthetic metadata review only; no physical device.",
        "url": "https://example.invalid/reviews/1",
        "record_refs": [{"record_id": reference["id"], "sha256": reference["sha256"]}],
    }


def write_zip(path: Path, files: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in files.items():
            archive.writestr(name, payload)


def reseal(files: dict[str, bytes]) -> None:
    """Recompute outer integrity without repairing semantic or inner-record faults."""
    lock = json.loads(files["package.json"])
    lock["files"] = {
        name: digest(payload)
        for name, payload in sorted(files.items())
        if name not in {"package.json", "checksums.txt"}
    }
    files["package.json"] = encoded(lock)
    files["checksums.txt"] = "".join(
        f"{digest(payload)}  {name}\n" for name, payload in sorted(files.items()) if name != "checksums.txt"
    ).encode()


def test_standalone_records_do_not_require_sdf() -> None:
    for record, kind in [(document(), schemas.DOCUMENT_SOURCE), (observation(), schemas.CATALOG_OBSERVATION)]:
        assert schemas.detect_kind(record) == kind
        assert not schemas.validation_errors(record, kind=kind)
        assert "sdf" not in json.dumps(record).lower()


def test_synthetic_observation_cannot_claim_physical_device() -> None:
    record = observation()
    record["method"] = "physical-device"
    assert schemas.validation_errors(record, kind=schemas.CATALOG_OBSERVATION)


@pytest.mark.parametrize(
    "bad_url", ["http://example.invalid/a", "https://user:secret@example.invalid/a", "javascript:alert(1)"]
)
def test_document_urls_are_safe_metadata(bad_url: str) -> None:
    record = document()
    record["url"] = bad_url
    assert schemas.validation_errors(record, kind=schemas.DOCUMENT_SOURCE)


def test_document_only_bundle_is_offline_deterministic_and_honest(
    bundle_root: Path, tmp_path: Path, monkeypatch
) -> None:
    def forbidden(*args, **kwargs):
        pytest.fail("Bundle check/build/export/verify must not fetch upstream content")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(catalog.requests.sessions.Session, "request", forbidden)
    bundle = bundles.load_bundle(bundle_root, ID)
    before = {path: payload for path, payload in bundle.payloads.items()}
    report = bundles.build_report(bundle)
    assert report["checks"]["upstream_bytes"] == "not-checked"
    assert report["checks"]["hardware"] == "not-tested-by-this-tool"
    assert report["checks"]["review_identity"] == "not-authenticated"
    assert report["bundle"]["reviews"] == []
    assert report["bundle"]["publication_status"] == "candidate"
    first, second = tmp_path / "first.zip", tmp_path / "second.zip"
    assert bundles.export_bundle(bundle, first) == first.stat().st_size
    bundles.export_bundle(bundle, second)
    assert first.read_bytes() == second.read_bytes()
    verified = bundles.verify_package(first)
    assert verified["id"] == ID
    assert verified["version"] == "0.1.0"
    assert verified["integrity"] == "passed"
    assert verified["authenticity"] == "not-established"
    assert verified["hardware"] == "not-tested-by-this-tool"
    with zipfile.ZipFile(first) as archive:
        names = archive.namelist()
        assert names == sorted(names)
        assert not any(name.endswith(".pdf") for name in names)
        assert "schema/document-source.schema.json" in names
        assert "schema/device-evidence-bundle.schema.json" in names
        assert all(item.date_time == (1980, 1, 1, 0, 0, 0) for item in archive.infolist())
    output = tmp_path / "site"
    assert bundles.build_bundle(bundle, output) == verified["files"] + 1
    assert (output / "bundle.zip").read_bytes() == first.read_bytes()
    for path, payload in before.items():
        assert (bundle_root / path).read_bytes() == payload


def test_observation_roundtrip_preserves_synthetic_and_candidate_labels(
    bundle_root: Path, tmp_path: Path
) -> None:
    add_observation(bundle_root)
    bundle = bundles.load_bundle(bundle_root, ID)
    target = tmp_path / "synthetic.zip"
    bundles.export_bundle(bundle, target)
    assert bundles.verify_package(target)["integrity"] == "passed"
    report = bundles.build_report(bundle)
    record = report["records"]["synthetic-observation"]
    assert record["method"] == "simulation"
    assert record["data_origin"] == "synthetic-example"
    assert record["review"]["lifecycle"] == "candidate"


def test_changed_raw_bytes_fail_even_if_parsed_document_unchanged(bundle_root: Path) -> None:
    path = bundle_root / DOCUMENT
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(bundles.BundleError, match="Record digest mismatch"):
        bundles.load_bundle(bundle_root, ID)


@pytest.mark.parametrize(
    "mutation, message",
    [
        (lambda m: m["features"][0]["record_ids"].append("missing-record"), "missing referenced record"),
        (lambda m: m["records"][0].update(id="wrong-id"), "Record identity mismatch"),
        (lambda m: m["features"][0]["record_ids"].clear(), "explanation must cite"),
        (
            lambda m: m["features"][0]["implementation_notes"][0]["references"][0].update(
                locator="#/locations/99"
            ),
            "JSON pointer not found",
        ),
        (
            lambda m: m["features"][0]["implementation_notes"][0]["references"][0].update(
                locator="#/locations/00"
            ),
            "JSON pointer not found",
        ),
        (
            lambda m: m["features"][0]["implementation_notes"][0]["references"][0].update(
                locator="#/locations/~9"
            ),
            "Invalid record JSON pointer",
        ),
        (lambda m: m["records"].append(copy.deepcopy(m["records"][0])), "duplicate"),
    ],
)
def test_invalid_record_relationships_fail(bundle_root: Path, mutation, message: str) -> None:
    update_manifest(bundle_root, mutation)
    with pytest.raises(bundles.BundleError, match=message):
        bundles.load_bundle(bundle_root, ID)


def test_json_pointer_escaped_tokens_and_root_are_resolved() -> None:
    record = {"a/b": {"~": ["value"]}}
    assert bundles._pointer(record, "#/a~1b/~0/0") == "value"
    assert bundles._pointer(record, "#") is record


def test_orphan_record_is_not_smuggled_into_package(bundle_root: Path) -> None:
    orphan = document()
    orphan["id"] = "orphan-manual"
    reference = write_record(bundle_root, "catalog/documents/orphan.json", orphan)
    update_manifest(bundle_root, lambda m: m["records"].append(reference))
    with pytest.raises(bundles.BundleError, match="outside its feature dependency closure"):
        bundles.load_bundle(bundle_root, ID)


def test_explicit_gap_is_required_for_an_empty_feature(bundle_root: Path) -> None:
    manifest = read_record(bundle_root, MANIFEST)
    empty = copy.deepcopy(manifest["features"][0])
    empty.update(id="not-yet-investigated", record_ids=[], implementation_notes=[], test_plan=[], gaps=[])
    manifest["features"].append(empty)
    write_record(bundle_root, MANIFEST, manifest)
    with pytest.raises(bundles.BundleError, match="empty feature needs an explicit gap"):
        bundles.load_bundle(bundle_root, ID)
    empty["gaps"] = ["No source or test evidence has been contributed."]
    write_record(bundle_root, MANIFEST, manifest)
    assert len(bundles.load_bundle(bundle_root, ID).manifest["features"]) == 2


def test_exact_document_applicability_must_match_subject(bundle_root: Path) -> None:
    update_document(bundle_root, lambda record: record["applicability"].update(model="Other Model"))
    with pytest.raises(bundles.BundleError, match="document applicability mismatch"):
        bundles.load_bundle(bundle_root, ID)
    update_document(bundle_root, lambda record: record["applicability"].update(scope="family-context"))
    assert (
        bundles.load_bundle(bundle_root, ID).records["synthetic-manual"]["applicability"]["scope"]
        == "family-context"
    )


@pytest.mark.parametrize(
    "change, message",
    [
        ("model", "subject model mismatch"),
        ("identifiers", "subject identifier mismatch"),
        ("feature_id", "observation feature mismatch"),
        ("firmware", "firmware mismatch"),
    ],
)
def test_observation_identity_and_feature_are_scoped(bundle_root: Path, change: str, message: str) -> None:
    record = observation()
    if change == "feature_id":
        record[change] = "other-feature"
    elif change == "identifiers":
        record["subject"][change]["model_id"] = "other-signature"
    elif change == "firmware":
        record["subject"][change] = "2.0"
        update_manifest(bundle_root, lambda m: m["subject"].update(firmware="1.0"))
    else:
        record["subject"][change] = "Other Model"
    add_observation(bundle_root, record)
    with pytest.raises(bundles.BundleError, match=message):
        bundles.load_bundle(bundle_root, ID)


@pytest.mark.parametrize(
    "reviewer, message",
    [
        ("fixture-author", "Bundle author cannot supply independent review"),
        ("fixture-researcher", "Record author cannot supply independent review"),
    ],
)
def test_self_review_cannot_supply_independent_review(bundle_root: Path, reviewer: str, message: str) -> None:
    row = review(bundle_root, reviewer)
    update_manifest(bundle_root, lambda m: m["reviews"].append(row))
    with pytest.raises(bundles.BundleError, match=message):
        bundles.load_bundle(bundle_root, ID)


def test_reviews_are_scoped_to_the_exact_record_digest(bundle_root: Path) -> None:
    row = review(bundle_root)
    update_manifest(bundle_root, lambda m: m["reviews"].append(row))
    assert len(bundles.load_bundle(bundle_root, ID).manifest["reviews"]) == 1
    update_document(bundle_root, lambda record: record.update(title="Updated synthetic manual metadata"))
    with pytest.raises(bundles.BundleError, match="Stale review"):
        bundles.load_bundle(bundle_root, ID)


def test_review_credit_requires_the_same_reviewer_and_scope(bundle_root: Path) -> None:
    credit = {
        "identity": "independent-fixture-reviewer",
        "roles": ["review"],
        "record_ids": ["synthetic-manual"],
    }
    update_manifest(bundle_root, lambda m: m["credits"].append(credit))
    with pytest.raises(bundles.BundleError, match="Review credit requires"):
        bundles.load_bundle(bundle_root, ID)
    row = review(bundle_root)
    update_manifest(bundle_root, lambda m: m["reviews"].append(row))
    assert bundles.load_bundle(bundle_root, ID).manifest["publication_status"] == "candidate"


@pytest.mark.parametrize(
    "bad_path",
    [
        "catalog/documents/../escape.json",
        "catalog/documents//manual.json",
        "/tmp/manual.json",
        "catalog/documents/./manual.json",
    ],
)
def test_manifest_paths_fail_closed(bundle_root: Path, bad_path: str) -> None:
    update_manifest(bundle_root, lambda m: m["records"][0].update(path=bad_path))
    with pytest.raises((bundles.BundleError, catalog.CatalogError)):
        bundles.load_bundle(bundle_root, ID)


def test_locked_record_symlink_is_rejected(bundle_root: Path, tmp_path: Path) -> None:
    target = bundle_root / DOCUMENT
    outside = tmp_path / "outside.json"
    outside.write_bytes(target.read_bytes())
    target.unlink()
    target.symlink_to(outside)
    with pytest.raises(catalog.CatalogError, match="symbolic link"):
        bundles.load_bundle(bundle_root, ID)


def test_existing_outputs_and_canonical_inputs_are_preserved(bundle_root: Path, tmp_path: Path) -> None:
    bundle = bundles.load_bundle(bundle_root, ID)
    protected = tmp_path / "existing.zip"
    protected.write_bytes(b"do not overwrite")
    with pytest.raises(FileExistsError):
        bundles.export_bundle(bundle, protected)
    assert protected.read_bytes() == b"do not overwrite"
    output = tmp_path / "existing-report"
    output.mkdir()
    (output / "note.txt").write_text("user-owned")
    with pytest.raises(bundles.BundleError, match="new or empty"):
        bundles.build_bundle(bundle, output)
    assert (output / "note.txt").read_text() == "user-owned"
    for target in [
        bundle_root,
        bundle_root / "catalog",
        bundle_root / "catalog/output.zip",
        bundle_root / "CORE_REVISION",
    ]:
        with pytest.raises(bundles.BundleError, match="overlaps"):
            bundles.export_bundle(bundle, target)


def test_package_tampering_is_detected(bundle_root: Path, tmp_path: Path) -> None:
    files = bundles.package_files(bundles.load_bundle(bundle_root, ID))
    files["report.md"] += b"Unexpected change\n"
    output = tmp_path / "tampered.zip"
    write_zip(output, files)
    with pytest.raises(bundles.BundleError, match="Package digest mismatch: report.md"):
        bundles.verify_package(output)


@pytest.mark.parametrize(
    "target, mutation, message",
    [
        (MANIFEST, lambda record: record["records"][0].update(sha256="0" * 64), "Record digest mismatch"),
        (
            MANIFEST,
            lambda record: record["features"][0]["record_ids"].append("missing-record"),
            "missing referenced record",
        ),
        (
            "report.json",
            lambda record: record["records"]["synthetic-manual"].update(title="Invented report title"),
            "Report and canonical records disagree",
        ),
        ("report.json", lambda record: record.update(input_digest="0" * 64), "Report input digest mismatch"),
    ],
)
def test_rehashed_outer_inventory_does_not_bypass_inner_checks(
    bundle_root: Path, tmp_path: Path, target: str, mutation, message: str
) -> None:
    files = bundles.package_files(bundles.load_bundle(bundle_root, ID))
    record = json.loads(files[target])
    mutation(record)
    files[target] = encoded(record)
    reseal(files)
    output = tmp_path / "rehashed.zip"
    write_zip(output, files)
    with pytest.raises(bundles.BundleError, match=message):
        bundles.verify_package(output)


def test_rehashed_package_cannot_replace_trusted_schema(bundle_root: Path, tmp_path: Path) -> None:
    files = bundles.package_files(bundles.load_bundle(bundle_root, ID))
    files["schema/document-source.schema.json"] = b"{}\n"
    reseal(files)
    output = tmp_path / "schema-swap.zip"
    write_zip(output, files)
    with pytest.raises(bundles.BundleError, match="Schema snapshot differs"):
        bundles.verify_package(output)


@pytest.mark.parametrize("resealed", [False, True])
def test_unexpected_package_members_are_rejected(bundle_root: Path, tmp_path: Path, resealed: bool) -> None:
    files = bundles.package_files(bundles.load_bundle(bundle_root, ID))
    files["unrequested-driver.py"] = b"raise RuntimeError('must never be executed')\n"
    if resealed:
        reseal(files)
    output = tmp_path / "extra.zip"
    write_zip(output, files)
    message = "record closure" if resealed else "unexpected package members"
    with pytest.raises(bundles.BundleError, match=message):
        bundles.verify_package(output)


@pytest.mark.parametrize(
    "name", ["../escape.txt", "/absolute.txt", "a//b.txt", "a/./b.txt", "a\\b.txt", "C:/escape.txt"]
)
def test_zip_paths_are_rejected_without_extraction(tmp_path: Path, name: str) -> None:
    output = tmp_path / "unsafe.zip"
    write_zip(output, {name: b"must not be extracted"})
    with pytest.raises((bundles.BundleError, catalog.CatalogError)):
        bundles.verify_package(output)
    assert list(tmp_path.iterdir()) == [output]


def test_zip_symlinks_and_duplicates_are_rejected(tmp_path: Path) -> None:
    output = tmp_path / "symlink.zip"
    with zipfile.ZipFile(output, "w") as archive:
        member = zipfile.ZipInfo("document.json")
        member.create_system = 3
        member.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(member, "../../outside")
    with pytest.raises(bundles.BundleError, match="Unsafe or duplicate"):
        bundles.verify_package(output)
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("same.json", b"first")
        with pytest.warns(UserWarning, match="Duplicate name"):
            archive.writestr("same.json", b"second")
    with pytest.raises(bundles.BundleError, match="Unsafe or duplicate"):
        bundles.verify_package(output)


def test_archive_limits_are_enforced_before_member_parsing(tmp_path: Path, monkeypatch) -> None:
    output = tmp_path / "limits.zip"
    write_zip(output, {"oversized.json": b"x" * 1024})
    monkeypatch.setattr(bundles, "MAX_MEMBER_BYTES", 100)
    with pytest.raises(bundles.BundleError, match="Unsafe or duplicate"):
        bundles.verify_package(output)
    monkeypatch.setattr(bundles, "MAX_MEMBER_BYTES", 2048)
    monkeypatch.setattr(bundles, "MAX_PACKAGE_BYTES", 512)
    with pytest.raises(bundles.BundleError, match="expanded-byte limit"):
        bundles.verify_package(output)
    monkeypatch.setattr(bundles, "MAX_PACKAGE_BYTES", 2048)
    monkeypatch.setattr(bundles, "MAX_MEMBERS", 0)
    with pytest.raises(bundles.BundleError, match="member/expanded-byte limit"):
        bundles.verify_package(output)


def test_corrupt_zip_fails_cleanly(tmp_path: Path) -> None:
    output = tmp_path / "not-a-zip.zip"
    output.write_bytes(b"not a zip archive")
    with pytest.raises(bundles.BundleError, match="Unreadable or corrupt"):
        bundles.verify_package(output)


def test_corrupt_deflate_stream_fails_without_traceback(tmp_path: Path, capsys) -> None:
    output = tmp_path / "invalid-deflate.zip"
    write_zip(output, {"document.json": b"synthetic document content"})
    raw = bytearray(output.read_bytes())
    filename_length, extra_length = struct.unpack_from("<HH", raw, 26)
    data_offset = 30 + filename_length + extra_length
    raw[data_offset] = 0x07  # DEFLATE's reserved block type, with BFINAL set.
    output.write_bytes(raw)
    with pytest.raises(bundles.BundleError, match="Unreadable or corrupt"):
        bundles.verify_package(output)
    assert main(["bundle", "verify", str(output)]) == 1
    captured = capsys.readouterr()
    assert "Traceback" not in captured.out + captured.err


def test_zip_embedded_nul_cannot_hide_filename_suffix(bundle_root: Path, tmp_path: Path) -> None:
    files = bundles.package_files(bundles.load_bundle(bundle_root, ID))
    files["index.htmlAAAAA"] = files.pop("index.html")
    output = tmp_path / "nul-name.zip"
    write_zip(output, files)
    raw = output.read_bytes()
    assert raw.count(b"index.htmlAAAAA") == 2  # Local header and central-directory entry.
    output.write_bytes(raw.replace(b"index.htmlAAAAA", b"index.html\x00evil"))
    with pytest.raises(bundles.BundleError, match="Unsafe or duplicate"):
        bundles.verify_package(output)


def test_locked_records_and_aggregate_inputs_are_bounded(bundle_root: Path, monkeypatch) -> None:
    monkeypatch.setattr(bundles, "MAX_INPUT_BYTES", 10)
    with pytest.raises(bundles.BundleError, match="aggregate byte limit"):
        bundles.load_bundle(bundle_root, ID)
    monkeypatch.setattr(bundles, "MAX_INPUT_BYTES", 16 * catalog.MAX_BYTES)
    (bundle_root / DOCUMENT).write_bytes(b" " * (catalog.MAX_BYTES + 1))
    with pytest.raises(catalog.CatalogError, match="exceeds"):
        bundles.load_bundle(bundle_root, ID)


def test_missing_record_is_an_error(bundle_root: Path) -> None:
    (bundle_root / DOCUMENT).unlink()
    with pytest.raises(catalog.CatalogError, match="Cannot read catalog/documents/synthetic-manual.json"):
        bundles.load_bundle(bundle_root, ID)


def test_bundle_discovery_rejects_ambiguous_manifests(bundle_root: Path, tmp_path: Path) -> None:
    assert bundles.load_all(tmp_path / "empty") == []
    assert [bundle.manifest["id"] for bundle in bundles.load_all(bundle_root)] == [ID]
    (bundle_root / MANIFEST).with_suffix(".yaml").write_bytes((bundle_root / MANIFEST).read_bytes())
    with pytest.raises(bundles.BundleError, match="Duplicate bundle ID"):
        bundles.load_all(bundle_root)
    with pytest.raises(bundles.BundleError, match="Expected one bundle manifest"):
        bundles.load_bundle(bundle_root, ID)


def test_core_pin_changes_input_digest_without_claiming_authentication(bundle_root: Path) -> None:
    bundle = bundles.load_bundle(bundle_root, ID)
    unpinned = bundles.build_report(bundle)
    assert unpinned["declared_core_revision"] is None
    pin = bundle_root / "CORE_REVISION"
    pin.write_text("1" * 40 + "\n")
    first = bundles.build_report(bundle)
    pin.write_text("2" * 40 + "\n")
    second = bundles.build_report(bundle)
    assert len({unpinned["input_digest"], first["input_digest"], second["input_digest"]}) == 3
    assert second["declared_core_revision"] == "2" * 40
    assert second["generator"]["version_label_is_not_release_attestation"] is True
    pin.write_text("main\n")
    with pytest.raises(bundles.BundleError, match="full commit ID"):
        bundles.build_report(bundle)


def add_mapping(root: Path, repo_root: Path) -> dict:
    fixtures = repo_root / "tests/fixtures/catalog"
    mapping = schemas.load_document(fixtures / "lock-mapping-set.yaml")
    manifest = read_record(root, MANIFEST)
    references = []
    for filename in ("smartthings-source.yaml", "onedm-source.yaml"):
        record = schemas.load_document(fixtures / filename)
        reference = write_record(root, f"catalog/sources/{record['id']}.json", record)
        references.append(reference)
        manifest["records"].append(reference)
    mapping["source_manifests"] = references
    mapping_ref = write_record(root, "catalog/mappings/synthetic-mapping.json", mapping)
    manifest["records"].append(mapping_ref)
    manifest["features"][0]["record_ids"].append(mapping["id"])
    manifest["subject"]["protocol"] = "zwave"
    write_record(root, MANIFEST, manifest)
    return mapping


def test_mapping_closure_retains_its_pinned_source_manifests(
    bundle_root: Path, repo_root: Path, tmp_path: Path
) -> None:
    mapping = add_mapping(bundle_root, repo_root)
    bundle = bundles.load_bundle(bundle_root, ID)
    assert set(bundle.records) == {
        "synthetic-manual",
        mapping["id"],
        "smartthings-lock-fixture",
        "onedm-lock-fixture",
    }
    output = tmp_path / "mapping.zip"
    bundles.export_bundle(bundle, output)
    assert bundles.verify_package(output)["integrity"] == "passed"


@pytest.mark.parametrize(
    "mutation, message",
    [
        (lambda m: m["nodes"][0]["artifact"].update(artifact_id="nonexistent-artifact"), "unknown artifact"),
        (lambda m: m["source_manifests"][0].update(sha256="0" * 64), "source manifest lock mismatch"),
        (
            lambda m: m["source_manifests"][0].update(path="catalog/sources/not-the-locked-file.json"),
            "source manifest lock mismatch",
        ),
        (lambda m: m["source_manifests"].pop(), "unknown source manifest|undeclared source manifest"),
        (lambda m: m["nodes"][1].update(layer="platform-exposure"), "evidence layer mismatch"),
    ],
)
def test_mapping_source_artifact_and_lock_scope_fail_closed(
    bundle_root: Path, repo_root: Path, mutation, message: str
) -> None:
    mapping = add_mapping(bundle_root, repo_root)
    mutation(mapping)
    reference = write_record(bundle_root, "catalog/mappings/synthetic-mapping.json", mapping)
    update_manifest(bundle_root, lambda m: m["records"].__setitem__(-1, reference))
    with pytest.raises(bundles.BundleError, match=message):
        bundles.load_bundle(bundle_root, ID)


def test_bundle_cli_offline_roundtrip_and_failure(bundle_root: Path, tmp_path: Path, capsys) -> None:
    assert main(["bundle", "check", str(bundle_root), ID]) == 0
    target = tmp_path / "cli.zip"
    assert main(["bundle", "export", str(bundle_root), ID, "--output", str(target)]) == 0
    assert main(["bundle", "verify", str(target)]) == 0
    site = tmp_path / "cli-site"
    assert main(["bundle", "build", str(bundle_root), ID, "--output", str(site)]) == 0
    assert (site / "index.html").is_file()
    target.write_bytes(b"broken archive")
    assert main(["bundle", "verify", str(target)]) == 1
    captured = capsys.readouterr()
    assert "Traceback" not in captured.out + captured.err


def test_committed_document_only_fixture_exports_and_verifies(repo_root: Path, tmp_path: Path) -> None:
    fixture = repo_root / "tests/fixtures/bundles"
    bundle = bundles.load_bundle(fixture, "demo")
    assert set(bundle.records) == {"synthetic-manual"}
    assert bundle.manifest["reviews"] == []
    archive = tmp_path / "demo.zip"
    bundles.export_bundle(bundle, archive)
    assert bundles.verify_package(archive)["id"] == "demo"
