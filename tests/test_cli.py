"""Tests for the unified `edgeloom` entrypoint."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from edgeloom import __version__
from edgeloom.cli import main


def test_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_bare_invocation_prints_help(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 2
    assert "usage: edgeloom" in capsys.readouterr().out


@pytest.mark.parametrize("command", ["patch", "restore", "translate", "discover", "audit", "validate"])
def test_every_subcommand_is_registered(command: str, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main([command, "--help"])
    assert exc.value.code == 0
    assert command in capsys.readouterr().out


def test_validate_accepts_verbose_on_either_side(repo_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    target = str(repo_root / "auto_patch" / "capability-map.yaml")
    assert main(["validate", target, "-v"]) == 0
    after = capsys.readouterr().out
    assert main(["-v", "validate", target]) == 0
    before = capsys.readouterr().out
    assert "capability-map" in after and "capability-map" in before


def test_validate_reports_failures_and_exits_nonzero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("components: []\n", encoding="utf-8")

    assert main(["validate", str(bad)]) == 1
    out = capsys.readouterr().out
    assert "FAIL" in out
    assert "1 failed" in out


def test_validate_errors_when_nothing_was_checked(tmp_path: Path) -> None:
    """An empty run must not be reported as success."""
    (tmp_path / "unrelated.yaml").write_text("hello: world\n", encoding="utf-8")
    assert main(["validate", str(tmp_path)]) == 1


def test_validate_rejects_a_missing_path(tmp_path: Path) -> None:
    assert main(["validate", str(tmp_path / "nope")]) == 1


def test_patch_reports_failure_cleanly(tmp_path: Path) -> None:
    assert main(["patch", str(tmp_path / "absent"), "M", "Mfg"]) == 1


def test_translate_requires_a_token(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("HA_TOKEN", raising=False)
    assert main(["translate", "--ha-url", "http://ha.local", "--output", str(tmp_path)]) == 1


def test_translate_no_token_is_accepted_and_not_persisted(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """`--no-token` still requires a token for the fetch, but must not write
    it into the generated config (issue #33)."""
    from edgeloom.cli import build_parser

    args = build_parser().parse_args(
        ["translate", "--ha-url", "http://ha.local", "--output", "/dev/null", "--no-token"]
    )
    assert args.no_token is True

    captured = {}

    def fake_translate(**kwargs):
        captured.update(kwargs)
        return 0

    monkeypatch.setattr("ha2st_edge.cli.translate", fake_translate)
    exit_code = main(
        ["translate", "--ha-url", "http://ha.local", "--token", "T", "--output", str(tmp_path), "--no-token"]
    )
    assert exit_code == 0
    assert captured["persist_token"] is False


def test_discover_requires_local_dir_for_local_source(tmp_path: Path) -> None:
    assert main(["discover", "--source", "local", "--output", str(tmp_path / "c.json")]) == 1


def test_discover_defaults_point_at_a_repo_that_exists() -> None:
    """The shipped defaults have to resolve; they previously 404'd.

    `--repo` defaulted to SmartThingsCommunity/edge-drivers, which does not
    exist, and `--driver-subpath` to "drivers", which upstream nests by vendor
    so it contains no fingerprints.yml at that level.
    """
    from edgeloom.cli import build_parser

    args = build_parser().parse_args(["discover", "--output", "/dev/null"])

    assert args.repo == "SmartThingsCommunity/SmartThingsEdgeDrivers"
    assert args.driver_subpath == "drivers/SmartThings"


def test_discover_reports_zero_results_as_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Finding nothing is not success; it used to exit 0 and hide a bad subpath."""
    from discovery import discover_drivers

    monkeypatch.setattr(discover_drivers, "discover_from_local", lambda *a, **k: [])
    empty = tmp_path / "drivers"
    empty.mkdir()

    assert (
        main(
            [
                "discover",
                "--source",
                "local",
                "--local-dir",
                str(empty),
                "--output",
                str(tmp_path / "c.json"),
            ]
        )
        == 1
    )


def test_discover_says_so_when_the_capability_cross_check_is_skipped(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A missing capability config used to report every driver as unmapped.

    configparser returns silently on a missing file, and the default path is
    repo-relative, so for a pip-installed user the wrong answer was the default.
    """
    driver = tmp_path / "drivers" / "zigbee-lock"
    driver.mkdir(parents=True)
    (driver / "fingerprints.yml").write_text(
        "zigbeeManufacturer:\n- id: x\n  manufacturer: Yale\n  model: M\n", encoding="utf-8"
    )

    code = main(
        [
            "discover",
            "--source",
            "local",
            "--local-dir",
            str(tmp_path),
            "--driver-subpath",
            "drivers",
            "--cap-config",
            str(tmp_path / "absent.config"),
            "--output",
            str(tmp_path / "c.json"),
        ]
    )

    assert code == 0
    out = capsys.readouterr().out
    assert "cross-check skipped" in out

    catalog = json.loads((tmp_path / "c.json").read_text())
    assert catalog["capability_cross_check"] == "skipped"
    assert catalog["unsupported_drivers"] == []


def test_discover_rejects_a_negative_limit(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["discover", "--limit", "-1"])
    assert exc.value.code == 2
    assert "--limit" in capsys.readouterr().err


def test_discover_accepts_zero_as_a_real_limit() -> None:
    from edgeloom.cli import build_parser

    assert build_parser().parse_args(["discover", "--limit", "0"]).limit == 0
    assert build_parser().parse_args(["discover"]).limit is None


def test_restore_missing_driver_exits_nonzero(tmp_path: Path) -> None:
    """A driver with no backup must be a clean error, not a traceback."""
    assert main(["restore", str(tmp_path / "external" / "zigbee-lock")]) == 1


def test_restore_dry_run_moves_nothing(tmp_path: Path) -> None:
    tmp_root = tmp_path / "external"
    tmp_root.mkdir()
    active = tmp_root / "zigbee-lock"
    backup = tmp_root / "zigbee-lock-backup"
    active.mkdir()
    backup.mkdir()
    (active / "fingerprints.yml").write_text("patched\n", encoding="utf-8")
    (backup / "fingerprints.yml").write_text("original\n", encoding="utf-8")

    assert main(["restore", str(active), "--dry-run"]) == 0

    assert (active / "fingerprints.yml").read_text(encoding="utf-8") == "patched\n"
    assert (backup / "fingerprints.yml").read_text(encoding="utf-8") == "original\n"
    patched_dirs = [p for p in tmp_root.iterdir() if p.name.startswith("zigbee-lock-patched-")]
    assert not patched_dirs


def test_restore_restores_an_external_driver(tmp_path: Path) -> None:
    """The CLI restores a driver outside the installed package tree."""
    tmp_root = tmp_path / "external"
    tmp_root.mkdir()
    active = tmp_root / "zigbee-lock"
    backup = tmp_root / "zigbee-lock-backup"
    active.mkdir()
    backup.mkdir()
    (active / "fingerprints.yml").write_text("patched\n", encoding="utf-8")
    (backup / "fingerprints.yml").write_text("original\n", encoding="utf-8")

    assert main(["restore", str(active)]) == 0

    assert (active / "fingerprints.yml").read_text(encoding="utf-8") == "original\n"
    assert not backup.exists()
    patched_dirs = [p for p in tmp_root.iterdir() if p.name.startswith("zigbee-lock-patched-")]
    assert len(patched_dirs) == 1
    assert (patched_dirs[0] / "fingerprints.yml").read_text(encoding="utf-8") == "patched\n"


def test_audit_prints_a_clean_json_record(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    artifact = tmp_path / "model.json"
    artifact.write_text('{"x": 1}', encoding="utf-8")

    assert main(["audit", str(artifact)]) == 0

    record = json.loads(capsys.readouterr().out)
    assert record["record_version"] == "0.1"
    assert record["subject"]["digest"]["algorithm"] == "sha256"


def test_audit_schema_failure_returns_nonzero_with_record(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    artifact = tmp_path / "model.json"
    artifact.write_text('{"x": 1}', encoding="utf-8")
    schema = tmp_path / "schema.json"
    schema.write_text('{"type":"object","required":["missing"]}', encoding="utf-8")

    assert main(["audit", str(artifact), "--schema", str(schema)]) == 1

    record = json.loads(capsys.readouterr().out)
    assert record["checks"][-1]["status"] == "fail"


def test_audit_refuses_to_overwrite_its_input(tmp_path: Path) -> None:
    artifact = tmp_path / "model.json"
    original = '{"x": 1}'
    artifact.write_text(original, encoding="utf-8")

    assert main(["audit", str(artifact), "--output", str(artifact)]) == 1
    assert artifact.read_text(encoding="utf-8") == original


def test_audit_refuses_to_overwrite_its_schema(tmp_path: Path) -> None:
    artifact = tmp_path / "model.json"
    artifact.write_text('{"x": 1}', encoding="utf-8")
    schema = tmp_path / "schema.json"
    original = '{"type":"object"}'
    schema.write_text(original, encoding="utf-8")

    assert (
        main(
            [
                "audit",
                str(artifact),
                "--schema",
                str(schema),
                "--output",
                str(schema),
            ]
        )
        == 1
    )
    assert schema.read_text(encoding="utf-8") == original


def test_audit_writes_markdown_atomically(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    artifact = tmp_path / "model.json"
    artifact.write_text('{"x": 1}', encoding="utf-8")
    output = tmp_path / "reports" / "model.md"

    assert main(["audit", str(artifact), "--format", "markdown", "--output", str(output)]) == 0

    assert output.read_text(encoding="utf-8").startswith("# EdgeLoom evidence record")
    assert "Evidence record written" in capsys.readouterr().out
    assert not list(output.parent.glob(f".{output.name}.*.tmp"))


def test_atomic_write_cleans_temporary_file_when_replace_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from edgeloom import cli

    output = tmp_path / "record.json"

    def fail_replace(self: Path, _target: Path) -> None:
        raise OSError("simulated replace failure")

    monkeypatch.setattr(Path, "replace", fail_replace)

    with pytest.raises(OSError, match="simulated"):
        cli._atomic_write(output, "{}\n")

    assert not output.exists()
    assert not list(tmp_path.glob(f".{output.name}.*.tmp"))


def test_audit_rejects_schema_authority_without_schema(tmp_path: Path) -> None:
    artifact = tmp_path / "model.json"
    artifact.write_text('{"x": 1}', encoding="utf-8")

    assert main(["audit", str(artifact), "--schema-authority", "normative"]) == 1


@pytest.mark.parametrize("flag", ["--source-uri", "--source-ref", "--license", "--title"])
def test_audit_rejects_empty_optional_metadata_without_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    flag: str,
) -> None:
    artifact = tmp_path / "model.json"
    artifact.write_text('{"x": 1}', encoding="utf-8")
    output = tmp_path / "record.json"

    assert main(["audit", str(artifact), flag, "  ", "--output", str(output)]) == 1

    captured = capsys.readouterr()
    assert not output.exists()
    assert "Traceback" not in captured.out + captured.err


def test_audit_rejects_non_string_yaml_mapping_keys_without_traceback(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    artifact = tmp_path / "model.yaml"
    artifact.write_text("1: value\n", encoding="utf-8")
    schema = tmp_path / "schema.json"
    schema.write_text(
        '{"type":"object","patternProperties":{".*":{"type":"string"}}}',
        encoding="utf-8",
    )

    assert main(["audit", str(artifact), "--schema", str(schema)]) == 1

    captured = capsys.readouterr()
    record = json.loads(captured.out)
    assert record["checks"][1]["status"] == "fail"
    assert record["checks"][1]["details"]["error_type"] == "NonStringMappingKeyError"
    assert "Traceback" not in captured.out + captured.err


def test_validate_rejects_non_string_yaml_mapping_keys_without_traceback(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    artifact = tmp_path / "model.yaml"
    artifact.write_text("outer:\n  1: value\n", encoding="utf-8")

    assert main(["validate", str(artifact), "--kind", "profile"]) == 1

    captured = capsys.readouterr()
    assert "Traceback" not in captured.out + captured.err


def test_patch_then_restore_an_external_driver(driver_copy: Path) -> None:
    """The public patch and restore commands share one sibling-backup contract."""

    def tree_contents(root: Path) -> dict[str, bytes]:
        return {str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*") if path.is_file()}

    stock = tree_contents(driver_copy)

    assert main(["patch", str(driver_copy), "YRD226 TSDB", "Yale"]) == 0
    assert driver_copy.with_name(f"{driver_copy.name}-backup").is_dir()
    assert (driver_copy / "profiles" / "base-lock-patch.yml").is_file()

    assert main(["restore", str(driver_copy)]) == 0
    assert tree_contents(driver_copy) == stock

    patched_dirs = list(driver_copy.parent.glob(f"{driver_copy.name}-patched-*"))
    assert len(patched_dirs) == 1
    assert (patched_dirs[0] / "profiles" / "base-lock-patch.yml").is_file()
