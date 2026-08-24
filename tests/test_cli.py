"""Tests for the unified `edgeloom` entrypoint."""

from __future__ import annotations

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


@pytest.mark.parametrize("command", ["patch", "translate", "discover", "validate"])
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
    import json

    catalog = json.loads((tmp_path / "c.json").read_text())
    assert catalog["capability_cross_check"] == "skipped"
    assert catalog["unsupported_drivers"] == []


def test_translate_accepts_no_token_and_defaults_to_writing_it() -> None:
    from edgeloom.cli import build_parser

    base = ["translate", "--ha-url", "http://ha.local:8123", "--output", "out"]
    assert build_parser().parse_args(base).no_token is False
    assert build_parser().parse_args([*base, "--no-token"]).no_token is True


def test_no_token_keeps_the_credential_out_of_the_generated_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """--no-token must still require a token for the fetch, only stop persisting it."""
    from ha2st_edge import cli as translator_cli

    class StubClient:
        def __init__(self, **_kwargs: object) -> None:
            pass

        def get_states(self) -> list[dict]:
            return [{"entity_id": "switch.plug", "attributes": {}}]

    monkeypatch.setattr(translator_cli, "HomeAssistantClient", StubClient)
    monkeypatch.setenv("HA_TOKEN", "SECRET")

    argv = ["translate", "--ha-url", "http://ha.local:8123", "--output", str(tmp_path), "--no-token"]
    assert main(argv) == 0

    written = (tmp_path / "config" / "ha_devices.yaml").read_text(encoding="utf-8")
    assert "SECRET" not in written
    assert "ha_token" not in written
    assert "ha_base_url" in written
