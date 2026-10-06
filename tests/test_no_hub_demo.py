"""The documented source-only demo must restore the original fixture bytes."""

import subprocess
import sys
from pathlib import Path


def test_source_only_demo(repo_root: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(repo_root / "scripts/no_hub_demo.py")],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert "restore matched every original file" in result.stdout
    assert "No Lua executed, no hub contacted" in result.stdout
