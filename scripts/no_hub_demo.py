"""Exercise Zigbee patch/validate/restore on a disposable source fixture, not a hub."""

from __future__ import annotations

import hashlib
import shutil
import tempfile
from pathlib import Path

from edgeloom import schemas
from edgeloom.cli import main

ROOT = Path(__file__).resolve().parents[1]


def snapshot(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*")
        if path.is_file()
    }


def run() -> None:
    with tempfile.TemporaryDirectory(prefix="edgeloom-no-hub-demo-") as temporary:
        driver = Path(temporary) / "zigbee-lock"
        shutil.copytree(ROOT / "auto_patch/zigbee-lock", driver)
        original = snapshot(driver)
        arguments = ["patch", str(driver), "YRD226 TSDB", "Yale", "Language"]
        if main([*arguments, "--dry-run"]) or snapshot(driver) != original:
            raise SystemExit("Dry-run failed or changed the source copy")
        if main(arguments):
            raise SystemExit("Patch failed")
        patched = snapshot(driver)
        changed = sorted(name for name in patched if original.get(name) != patched[name])
        print("Changed/new source files:", ", ".join(changed))
        for profile in sorted((driver / "profiles").glob("*.yml")):
            result = schemas.validate_document(profile, kind=schemas.PROFILE)
            if not result.ok:
                raise SystemExit(f"Profile validation failed: {result.errors}")
        if main(["restore", str(driver), "--dry-run"]) or main(["restore", str(driver)]):
            raise SystemExit("Restore failed")
        if snapshot(driver) != original:
            raise SystemExit("Restored source bytes differ from the original")
        print("PASS: dry-run left bytes unchanged; profiles validated; restore matched every original file.")
        print(
            "Source-only Zigbee exercise. No Lua executed, no hub contacted, no YRD156 Z-Wave patch claimed."
        )


if __name__ == "__main__":
    run()
