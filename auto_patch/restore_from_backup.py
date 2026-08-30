"""Restore patched SmartThings Edge drivers from backups."""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from auto_patch.paths import UnsafePathError, contained_path, safe_identifier

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
    candidate = contained_path(parent, base_name)
    suffix = 1
    while candidate.exists():
        candidate = contained_path(parent, f"{base_name}-{suffix}")
        suffix += 1
    return candidate


def _rename_sibling(source: Path, destination: Path) -> None:
    """Rename one sibling to another without following the destination.

    ``shutil.move`` treats an existing symlink to a directory as a directory
    destination and moves ``source`` *through* that link.  A plain filesystem
    rename either replaces the link itself or fails; it never descends into
    the link target.  Requiring siblings also makes the same-filesystem
    assumption explicit and prevents a copy-and-delete fallback.
    """
    if source.parent != destination.parent:
        raise UnsafePathError(
            f"restore moves must stay within one parent: {source} -> {destination}",
        )

    if destination.exists() or destination.is_symlink():
        raise UnsafePathError(f"restore destination already exists: {destination}")

    try:
        source.rename(destination)
    except OSError as exc:
        # A destination may appear after the check above.  Some platforms
        # replace a file or symlink atomically; others reject a directory over
        # that entry.  Turn the latter into the same clean containment error.
        if destination.exists() or destination.is_symlink():
            raise UnsafePathError(
                f"restore destination appeared during the move: {destination}",
            ) from exc
        raise


def _restore_driver_at(active_dir: Path, *, dry_run: bool) -> Path | None:
    """Restore an already-authorized driver path from its sibling backup."""
    backup_dir = contained_path(active_dir.parent, f"{active_dir.name}-backup")

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
            _rename_sibling(active_dir, patched_dir)
    else:
        LOGGER.info("No active driver found at %s; skipping patched move.", active_dir)

    LOGGER.info("Restoring backup from %s to %s", backup_dir, active_dir)
    if dry_run:
        LOGGER.debug("Dry-run enabled; skipping restore move.")
    else:
        _rename_sibling(backup_dir, active_dir)

    return patched_dir


def restore_driver(driver: str | Path, dry_run: bool = False) -> Path | None:
    """Restore a bare-name driver from beneath the trusted ``auto_patch`` root.

    This is the legacy helper's safe-by-default entry point. Paths, including
    absolute paths, are deliberately rejected here. The unified CLI has a
    separate operator-path entry point so its broader contract cannot be
    enabled accidentally by changing the shape of this argument.
    """
    driver_name = safe_identifier(str(driver), field="driver")
    active_dir = contained_path(SCRIPT_ROOT, driver_name)
    return _restore_driver_at(active_dir, dry_run=dry_run)


def restore_operator_selected_driver(driver: str | Path, dry_run: bool = False) -> Path | None:
    """Restore an absolute path explicitly selected through the unified CLI."""
    candidate = Path(driver).expanduser()
    if not candidate.is_absolute():
        raise UnsafePathError(
            "operator-selected driver path must be absolute; resolve it at the CLI boundary",
        )
    return _restore_driver_at(candidate.resolve(), dry_run=dry_run)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    configure_logging(args.verbose)

    try:
        restore_driver(args.driver, dry_run=args.dry_run)
    except (FileNotFoundError, UnsafePathError) as exc:
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
