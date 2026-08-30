from pathlib import Path

import pytest

from auto_patch import restore_from_backup
from auto_patch.paths import UnsafePathError


def test_successful_restore(monkeypatch, tmp_path: Path) -> None:
    tmp_root = tmp_path / "auto_patch"
    tmp_root.mkdir()

    active = tmp_root / "zigbee-lock"
    backup = tmp_root / "zigbee-lock-backup"
    active.mkdir()
    backup.mkdir()

    (active / "fingerprints.yml").write_text("patched\n", encoding="utf-8")
    (backup / "fingerprints.yml").write_text("original\n", encoding="utf-8")

    monkeypatch.setattr(restore_from_backup, "SCRIPT_ROOT", tmp_root)

    patched_dir = restore_from_backup.restore_driver("zigbee-lock", dry_run=False)

    restored_file = tmp_root / "zigbee-lock" / "fingerprints.yml"
    assert restored_file.read_text(encoding="utf-8") == "original\n"
    assert not backup.exists()

    assert patched_dir is not None
    assert patched_dir.exists()
    assert patched_dir.name.startswith("zigbee-lock-patched-")
    assert (patched_dir / "fingerprints.yml").read_text(encoding="utf-8") == "patched\n"


def test_missing_backup_raises(monkeypatch, tmp_path: Path) -> None:
    tmp_root = tmp_path / "auto_patch"
    tmp_root.mkdir()

    active = tmp_root / "zigbee-lock"
    active.mkdir()
    (active / "fingerprints.yml").write_text("patched\n", encoding="utf-8")

    monkeypatch.setattr(restore_from_backup, "SCRIPT_ROOT", tmp_root)

    with pytest.raises(FileNotFoundError):
        restore_from_backup.restore_driver("zigbee-lock", dry_run=False)


def test_dry_run_no_changes(monkeypatch, tmp_path: Path) -> None:
    tmp_root = tmp_path / "auto_patch"
    tmp_root.mkdir()

    active = tmp_root / "zigbee-lock"
    backup = tmp_root / "zigbee-lock-backup"
    active.mkdir()
    backup.mkdir()

    (active / "fingerprints.yml").write_text("patched\n", encoding="utf-8")
    (backup / "fingerprints.yml").write_text("original\n", encoding="utf-8")

    monkeypatch.setattr(restore_from_backup, "SCRIPT_ROOT", tmp_root)

    patched_dir = restore_from_backup.restore_driver("zigbee-lock", dry_run=True)

    assert patched_dir is not None
    assert not patched_dir.exists()
    assert (active / "fingerprints.yml").read_text(encoding="utf-8") == "patched\n"
    assert (backup / "fingerprints.yml").read_text(encoding="utf-8") == "original\n"
    patched_dirs = [path for path in tmp_root.iterdir() if path.name.startswith("zigbee-lock-patched-")]
    assert not patched_dirs


@pytest.mark.parametrize(
    "driver",
    ["../outside", "nested/driver", ".hidden", "/tmp/absolute", "~/external"],
)
def test_legacy_driver_must_be_a_bare_name(monkeypatch, tmp_path: Path, driver: str) -> None:
    """The legacy helper must not turn a path-like name into a move target."""
    monkeypatch.setattr(restore_from_backup, "SCRIPT_ROOT", tmp_path)

    with pytest.raises(UnsafePathError):
        restore_from_backup.restore_driver(driver)


def test_absolute_external_driver_requires_the_unified_cli(tmp_path: Path) -> None:
    """The safe helper rejects a path that the explicit public CLI accepts."""
    from edgeloom.cli import main as cli_main

    external = tmp_path / "external" / "zigbee-lock"
    external.mkdir(parents=True)
    backup = external.with_name("zigbee-lock-backup")
    backup.mkdir()
    (external / "fingerprints.yml").write_text("patched\n", encoding="utf-8")
    (backup / "fingerprints.yml").write_text("original\n", encoding="utf-8")

    with pytest.raises(UnsafePathError):
        restore_from_backup.restore_driver(external)

    assert cli_main(["restore", str(external)]) == 0
    assert (external / "fingerprints.yml").read_text(encoding="utf-8") == "original\n"


def test_legacy_main_rejects_a_path_like_driver(monkeypatch, tmp_path: Path) -> None:
    """Exercise the real legacy entry point, not only its resolver."""
    script_root = tmp_path / "auto_patch"
    script_root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    outside_backup = tmp_path / "outside-backup"
    outside_backup.mkdir()
    marker = outside_backup / "marker.txt"
    marker.write_text("untouched\n", encoding="utf-8")
    monkeypatch.setattr(restore_from_backup, "SCRIPT_ROOT", script_root)

    with pytest.raises(SystemExit) as exc:
        restore_from_backup.main(["--driver", "../outside"])

    assert exc.value.code == 1
    assert marker.read_text(encoding="utf-8") == "untouched\n"
    assert outside.is_dir()
    assert outside_backup.is_dir()


def test_legacy_restore_refuses_a_symlinked_driver(monkeypatch, tmp_path: Path) -> None:
    """A bare-name restore cannot follow a driver link outside SCRIPT_ROOT."""
    script_root = tmp_path / "auto_patch"
    script_root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (script_root / "zigbee-lock").symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr(restore_from_backup, "SCRIPT_ROOT", script_root)

    with pytest.raises(UnsafePathError):
        restore_from_backup.restore_driver("zigbee-lock")


def test_restore_refuses_a_symlinked_backup(monkeypatch, tmp_path: Path) -> None:
    """A backup link is not an acceptable source for a destructive restore."""
    script_root = tmp_path / "auto_patch"
    script_root.mkdir()
    active = script_root / "zigbee-lock"
    active.mkdir()
    outside = tmp_path / "outside-backup"
    outside.mkdir()
    (script_root / "zigbee-lock-backup").symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr(restore_from_backup, "SCRIPT_ROOT", script_root)

    with pytest.raises(UnsafePathError):
        restore_from_backup.restore_driver("zigbee-lock")


def test_identifier_guard_stops_escape_if_containment_is_neutered(monkeypatch, tmp_path: Path) -> None:
    """Mutation check: the allowlist independently blocks path-like input."""
    monkeypatch.setattr(restore_from_backup, "SCRIPT_ROOT", tmp_path)
    monkeypatch.setattr(
        restore_from_backup,
        "contained_path",
        lambda root, *parts: root.joinpath(*parts),
    )

    with pytest.raises(UnsafePathError):
        restore_from_backup.restore_driver("../outside")


def test_containment_guard_stops_escape_if_identifier_check_is_neutered(monkeypatch, tmp_path: Path) -> None:
    """Mutation check: the trusted-root boundary independently blocks escape."""
    monkeypatch.setattr(restore_from_backup, "SCRIPT_ROOT", tmp_path)
    monkeypatch.setattr(restore_from_backup, "safe_identifier", lambda value, **_: value)

    with pytest.raises(UnsafePathError):
        restore_from_backup.restore_driver("../outside")


def test_operator_path_entry_requires_an_absolute_path(tmp_path: Path) -> None:
    """The broad entry point cannot be selected with an accidental relative value."""
    with pytest.raises(UnsafePathError):
        restore_from_backup.restore_operator_selected_driver(Path("zigbee-lock"))
