"""Build the dependency-free EdgeLoom project site into a clean directory."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "site"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "_site")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output = output.resolve()

    if output in {ROOT.resolve(), SOURCE.resolve()}:
        raise SystemExit(f"Refusing unsafe output directory: {output}")
    if not (SOURCE / "index.html").is_file():
        raise SystemExit("site/index.html is missing")

    if output.exists():
        shutil.rmtree(output)
    shutil.copytree(SOURCE, output)

    files = [path for path in output.rglob("*") if path.is_file()]
    size = sum(path.stat().st_size for path in files)
    print(f"Built {len(files)} files ({size:,} bytes) -> {output}")


if __name__ == "__main__":
    main()
