"""The unified ``edgeloom`` command line interface."""

from __future__ import annotations

import argparse
import logging
import os
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from edgeloom import __version__, schemas
from edgeloom.argtypes import non_negative_int

LOGGER = logging.getLogger("edgeloom")


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="[%(levelname)s] %(message)s",
    )


# --------------------------------------------------------------------------- patch


def _cmd_patch(args: argparse.Namespace) -> int:
    from edgeloom.patching import PatchError, run_patch

    try:
        result = run_patch(
            driver=args.driver,
            model=args.model,
            manufacturer=args.manufacturer,
            attributes=args.attributes,
            dry_run=args.dry_run,
        )
    except PatchError as exc:
        LOGGER.error("%s", exc)
        return 1

    if result.dry_run:
        print(f"Dry run complete for {result.driver.name}; nothing was written.")
    else:
        print(f"Patched {result.driver.name} (profile '{result.profile_name}').")
        if result.backup is not None:
            print(f"Original preserved at {result.backup}")
    return 0


# ------------------------------------------------------------------------ restore


def _cmd_restore(args: argparse.Namespace) -> int:
    from auto_patch.restore_from_backup import restore_driver

    driver_dir = Path(args.driver).resolve()

    try:
        patched_dir = restore_driver(driver_dir, dry_run=args.dry_run)
    except FileNotFoundError as exc:
        LOGGER.error("%s", exc)
        return 1

    if args.dry_run:
        print(f"Dry run complete for {driver_dir.name}; nothing was written.")
    else:
        print(f"Restored {driver_dir.name} from its backup.")
        if patched_dir is not None:
            print(f"Patched tree preserved at {patched_dir}")
    return 0


# ----------------------------------------------------------------------- translate


def _cmd_translate(args: argparse.Namespace) -> int:
    from ha2st_edge.cli import translate

    token = args.token or os.environ.get("HA_TOKEN")
    if not token:
        LOGGER.error("A Home Assistant token is required; pass --token or set HA_TOKEN.")
        return 1
    return translate(
        ha_url=args.ha_url,
        token=token,
        output=args.output,
        domains=args.domains,
        persist_token=not args.no_token,
    )


# ------------------------------------------------------------------------ discover


def _cmd_discover(args: argparse.Namespace) -> int:
    from discovery.discover_drivers import (
        build_driver_catalog,
        detect_unsupported_drivers,
        summarize_fingerprints,
        write_output,
    )

    if args.source == "local" and args.local_dir is None:
        LOGGER.error("--local-dir is required when --source local is used.")
        return 1

    try:
        fingerprints = build_driver_catalog(
            source=args.source,
            repo=args.repo,
            branch=args.branch,
            local_dir=args.local_dir,
            driver_subpath=args.driver_subpath,
            token=args.token or os.environ.get("GITHUB_TOKEN"),
            limit=args.limit,
            timeout=args.timeout,
        )
    except (RuntimeError, FileNotFoundError, ValueError) as exc:
        LOGGER.error("Discovery failed: %s", exc)
        return 1

    drivers, stats = summarize_fingerprints(fingerprints)

    # detect_unsupported_drivers reads the capability config with configparser,
    # which returns silently on a missing file and would then report every
    # driver as unmapped. The default is a repo-relative path, so for anyone who
    # pip-installed EdgeLoom that silent-and-wrong answer is the default answer.
    if args.cap_config.is_file():
        unsupported = detect_unsupported_drivers(drivers, args.cap_config)
        cross_checked = True
    else:
        unsupported = []
        cross_checked = False
        LOGGER.warning(
            "Capability cross-check skipped: no config at %s. Pass --cap-config to enable it.",
            args.cap_config,
        )

    catalog = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source": args.source,
        "stats": stats,
        "capability_cross_check": "performed" if cross_checked else "skipped",
        "unsupported_drivers": unsupported,
        "drivers": drivers,
    }

    # Finding nothing is not success. `validate` already takes this position;
    # discover reporting "0 drivers" with exit 0 hid a wrong --driver-subpath.
    if stats["driver_count"] == 0:
        LOGGER.error(
            "No drivers found under %r in %s. Upstream nests by vendor, so a subpath "
            "of 'drivers' walks vendor directories that hold no fingerprints.yml; "
            "try 'drivers/SmartThings'.",
            args.driver_subpath,
            args.repo if args.source == "github" else args.local_dir,
        )
        return 1

    write_output(catalog, args.output, args.format)
    print(
        f"Discovered {stats['fingerprint_count']} fingerprints across "
        f"{stats['driver_count']} drivers -> {args.output}"
    )
    if not cross_checked:
        print("Capability cross-check skipped (no capability config found).")
    elif unsupported:
        print(f"{len(unsupported)} driver(s) have no capability mapping yet: {', '.join(unsupported)}")
    return 0


# --------------------------------------------------------------------------- audit


def _atomic_write(path: Path, content: str) -> None:
    """Write text beside the destination and replace it atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    except OSError:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise


def _cmd_audit(args: argparse.Namespace) -> int:
    from edgeloom import evidence

    if args.schema is None and args.schema_authority != "user-supplied":
        LOGGER.error("--schema-authority requires --schema")
        return 1

    output_path = None if args.output == "-" else Path(args.output)
    if output_path is not None:
        try:
            protected = {args.artifact.resolve()}
            if args.schema is not None:
                protected.add(args.schema.resolve())
            resolved_output = output_path.resolve()
        except (OSError, RuntimeError) as exc:
            LOGGER.error("Could not resolve audit paths: %s", exc)
            return 1
        if resolved_output in protected:
            LOGGER.error("Refusing to overwrite the audited artifact or its schema: %s", output_path)
            return 1

    try:
        result = evidence.audit_artifact(
            args.artifact,
            schema_path=args.schema,
            schema_authority=args.schema_authority,
            source_uri=args.source_uri,
            source_ref=args.source_ref,
            license_expression=args.license_expression,
            artifact_status=args.artifact_status,
            title=args.title,
        )
        rendered = (
            evidence.render_json(result.record)
            if args.format == "json"
            else evidence.render_markdown(result.record)
        )
        if output_path is None:
            sys.stdout.write(rendered)
        else:
            _atomic_write(output_path, rendered)
            print(f"Evidence record written to {output_path}")
    except (evidence.EvidenceError, OSError) as exc:
        LOGGER.error("Audit failed: %s", exc)
        return 1

    return 1 if result.failed else 0


# ------------------------------------------------------------------------ validate


def _cmd_validate(args: argparse.Namespace) -> int:
    try:
        documents = schemas.iter_documents(args.paths)
    except schemas.SchemaError as exc:
        LOGGER.error("%s", exc)
        return 1

    checked = 0
    skipped = 0
    failures: list[schemas.ValidationResult] = []

    for path in documents:
        try:
            result = schemas.validate_document(path, kind=args.kind)
        except schemas.SchemaError as exc:
            LOGGER.error("%s", exc)
            return 1
        if result.skipped:
            skipped += 1
            continue
        checked += 1
        if result.ok:
            if getattr(args, "verbose", False):
                print(f"ok       {path} ({result.kind})")
        else:
            failures.append(result)

    for failure in failures:
        print(f"FAIL     {failure.path} ({failure.kind})")
        for message in failure.errors:
            print(f"           {message}")

    if checked == 0:
        # Silence here would read as success. It is not: nothing was checked.
        LOGGER.error("No recognized EdgeLoom contract documents found in the given paths.")
        return 1

    summary = f"{checked} document(s) checked, {len(failures)} failed"
    if skipped:
        summary += f", {skipped} unrelated file(s) skipped"
    print(summary)
    return 1 if failures else 0


# ---------------------------------------------------------------------- entrypoint


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="edgeloom",
        description=(
            "An open toolchain for auditing, validating, patching, restoring, translating, "
            "and discovering smart-home edge-driver artifacts."
        ),
    )
    parser.add_argument("--version", action="version", version=f"edgeloom {__version__}")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")

    # Accept -v on either side of the subcommand. SUPPRESS keeps the subparser
    # from overwriting a global -v with its own default.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Enable debug logging",
    )

    subparsers = parser.add_subparsers(dest="command", metavar="<command>")

    patch = subparsers.add_parser(
        "patch",
        parents=[common],
        help="Patch a SmartThings Edge driver to expose hidden device attributes",
    )
    patch.add_argument("driver", help="Path to (or folder name of) the Edge driver to patch")
    patch.add_argument("model", help="Device model string as reported by SmartThings")
    patch.add_argument("manufacturer", help="Device manufacturer string as reported by SmartThings")
    patch.add_argument(
        "attributes",
        nargs="?",
        default="ALL",
        help="Colon-separated attribute list, or ALL (default: ALL)",
    )
    patch.add_argument("-n", "--dry-run", action="store_true", help="Preview every change without writing")
    patch.set_defaults(func=_cmd_patch)

    restore = subparsers.add_parser(
        "restore",
        parents=[common],
        help="Restore a patched Edge driver from its backup",
    )
    restore.add_argument("driver", help="Path to the Edge driver directory to restore")
    restore.add_argument("-n", "--dry-run", action="store_true", help="Preview every change without writing")
    restore.set_defaults(func=_cmd_restore)

    translate = subparsers.add_parser(
        "translate",
        parents=[common],
        help="Generate SmartThings Edge proxy artifacts from Home Assistant entities",
    )
    translate.add_argument("--ha-url", required=True, help="Home Assistant base URL")
    translate.add_argument("--token", help="Long-lived HA token (or set HA_TOKEN)")
    translate.add_argument(
        "--domains",
        default="light,switch,lock,binary_sensor",
        help="Comma-separated HA domains to include",
    )
    translate.add_argument("--output", required=True, help="Output directory for generated artifacts")
    translate.add_argument(
        "--no-token",
        action="store_true",
        help="Do not write the HA token into the generated config; set HA_EDGE_TOKEN on the hub instead",
    )
    translate.set_defaults(func=_cmd_translate)

    discover = subparsers.add_parser(
        "discover", parents=[common], help="Enumerate Edge drivers and their Zigbee fingerprints"
    )
    discover.add_argument("--source", choices=["github", "local"], default="github")
    discover.add_argument("--repo", default="SmartThingsCommunity/SmartThingsEdgeDrivers")
    discover.add_argument("--branch", default="main")
    discover.add_argument("--driver-subpath", default="drivers/SmartThings")
    discover.add_argument("--local-dir", type=Path, help="Local directory containing drivers")
    discover.add_argument("--output", type=Path, default=Path("discovery/catalog.json"))
    discover.add_argument("--format", choices=["json", "yaml"], default="json")
    discover.add_argument(
        "--limit",
        type=non_negative_int,
        help="Stop after this many drivers (0 processes none; omit for no limit)",
    )
    discover.add_argument("--timeout", type=float, default=15.0)
    discover.add_argument(
        "--cap-config",
        type=Path,
        default=Path("auto_patch/custom_capability_list.config"),
        help="Capability config used to flag drivers with no mapping",
    )
    discover.add_argument("--token", help="GitHub token (or set GITHUB_TOKEN)")
    discover.set_defaults(func=_cmd_discover)

    audit = subparsers.add_parser(
        "audit",
        parents=[common],
        help="Create a local evidence record for an artifact and optional pinned schema",
    )
    audit.add_argument("artifact", type=Path, help="Local artifact to hash and inspect")
    audit.add_argument("--schema", type=Path, help="Local Draft 2020-12 JSON Schema to apply")
    audit.add_argument(
        "--schema-authority",
        choices=["normative", "informative", "user-supplied"],
        default="user-supplied",
        help="How the supplied schema is governed (default: user-supplied)",
    )
    audit.add_argument("--source-uri", help="Asserted canonical or retrieval URI (not fetched)")
    audit.add_argument("--source-ref", help="Pinned commit, tag, version, or revision")
    audit.add_argument(
        "--license",
        dest="license_expression",
        help="Asserted SPDX expression or license label (not verified)",
    )
    audit.add_argument(
        "--artifact-status",
        choices=["experimental", "draft", "stable", "deprecated", "unknown"],
        default="unknown",
    )
    audit.add_argument("--title", help="Human-readable record title")
    audit.add_argument("--format", choices=["json", "markdown"], default="json")
    audit.add_argument("--output", default="-", help="Output file, or - for stdout (default)")
    audit.set_defaults(func=_cmd_audit)

    validate = subparsers.add_parser(
        "validate",
        parents=[common],
        help="Check toolchain and catalog artifacts against the EdgeLoom schemas",
    )
    validate.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[Path(".")],
        help="Files or directories to check (default: the current directory)",
    )
    validate.add_argument(
        "--kind",
        choices=list(schemas.KINDS),
        help="Force a schema instead of inferring it from each document",
    )
    validate.set_defaults(func=_cmd_validate)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "func", None) is None:
        parser.print_help()
        return 2
    _configure_logging(getattr(args, "verbose", False))
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
