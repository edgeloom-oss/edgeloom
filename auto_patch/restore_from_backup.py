"""Restore patched SmartThings Edge drivers from backups."""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

LOGGER = logging.getLogger("edge_patcher.restore")
SCRIPT_ROOT = Path(__file__).resolve().parent


def configure_logging(verbose: bool = False) -> None:
    """Configure root logging level and format."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="[%(levelname)s] %(message)s")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Restore a patched SmartThings Edge driver from its backup.")
    parser.add_argument(
        "--driver",
        required=True,
        help="Driver folder name under auto_patch/ (e.g., zigbee-lock).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log intended actions without moving any files.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging for troubleshooting.",
    )
    return parser.parse_args(argv)


def timestamped_backup_name(active_dir: Path) -> Path:
    """Return a unique timestamped path to park the patched driver."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    parent = active_dir.parent
    base_name = f"{active_dir.name}-patched-{timestamp}"
    candidate = parent / base_name
    suffix = 1
    while candidate.exists():
        candidate = parent / f"{base_name}-{suffix}"
        suffix += 1
    return candidate


def _driver_path(driver: str | Path) -> Path:
    """Resolve a CLI path while preserving the helper's bare-name shorthand."""
    candidate = Path(driver).expanduser()
    if not candidate.is_absolute() and candidate.parent == Path("."):
        candidate = SCRIPT_ROOT / candidate
    return candidate.resolve()


def restore_driver(driver: str | Path, dry_run: bool = False) -> Path | None:
    """Restore a driver from its sibling backup, parking the patched copy first."""
    active_dir = _driver_path(driver)
    backup_dir = active_dir.with_name(f"{active_dir.name}-backup")

    LOGGER.debug("Active driver directory: %s", active_dir)
    LOGGER.debug("Backup driver directory: %s", backup_dir)

    if not backup_dir.is_dir():
        raise FileNotFoundError(f"Backup directory not found: {backup_dir}")

    patched_dir: Path | None = None
    if active_dir.exists():
        patched_dir = timestamped_backup_name(active_dir)
        LOGGER.info("Moving patched driver from %s to %s", active_dir, patched_dir)
        if dry_run:
            LOGGER.debug("Dry-run enabled; skipping move of patched driver.")
        else:
            shutil.move(str(active_dir), patched_dir)
    else:
        LOGGER.info("No active driver found at %s; skipping patched move.", active_dir)

    LOGGER.info("Restoring backup from %s to %s", backup_dir, active_dir)
    if dry_run:
        LOGGER.debug("Dry-run enabled; skipping restore move.")
    else:
        shutil.move(str(backup_dir), active_dir)

    return patched_dir


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    configure_logging(args.verbose)

    try:
        restore_driver(args.driver, dry_run=args.dry_run)
    except FileNotFoundError as exc:
        LOGGER.error("%s", exc)
        sys.exit(1)
    except Exception:  # noqa: BLE001 - propagate unexpected failure
        LOGGER.exception("Restore failed due to an unexpected error.")
        sys.exit(1)

    if args.dry_run:
        LOGGER.info("Dry-run completed; no filesystem changes were made.")
    else:
        LOGGER.info("Restore complete.")


if __name__ == "__main__":
    main()
