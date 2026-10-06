from __future__ import annotations

import argparse
import configparser
import json
import logging
import os
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import requests
import yaml

from edgeloom.argtypes import non_negative_int
from edgeloom.boundedyaml import check_bounds

LOGGER = logging.getLogger("edge_patcher.discovery")
GITHUB_API_URL = "https://api.github.com"
# Upstream nests by vendor: drivers/{ABB,Aqara,DeepSmart,SinuxSoft,SmartThings,
# Unofficial}. Pointing at "drivers" alone walks vendor directories, which hold
# no fingerprints.yml, and finds nothing.
DEFAULT_DRIVER_SUBPATH = "drivers/SmartThings"


@dataclass
class DriverFingerprint:
    driver: str
    manufacturer: str | None
    model: str | None
    profile: str | None
    device_id: str | None
    label: str | None
    protocol: str = "zigbee"
    manufacturer_id: str | None = None
    product_type: str | None = None
    product_id: str | None = None


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="[%(levelname)s] %(message)s")


def parse_fingerprints(driver_name: str, fingerprint_data: dict) -> list[DriverFingerprint]:
    if not isinstance(fingerprint_data, dict):
        raise ValueError("fingerprints must be an object")
    for key in ("zigbeeManufacturer", "zwaveManufacturer"):
        if key in fingerprint_data and not isinstance(fingerprint_data[key], list):
            raise ValueError(f"{key} must be a list")
    devices = []
    for device in fingerprint_data.get("zigbeeManufacturer", []):
        if not isinstance(device, dict):
            raise ValueError("zigbeeManufacturer entries must be objects")
        devices.append(
            DriverFingerprint(
                driver=driver_name,
                manufacturer=device.get("manufacturer"),
                model=device.get("model"),
                profile=device.get("deviceProfileName"),
                device_id=device.get("id"),
                label=device.get("deviceLabel"),
            )
        )
    for device in fingerprint_data.get("zwaveManufacturer", []):
        if not isinstance(device, dict):
            raise ValueError("zwaveManufacturer entries must be objects")
        devices.append(
            DriverFingerprint(
                driver=driver_name,
                manufacturer=None,
                model=None,
                profile=device.get("deviceProfileName"),
                device_id=device.get("id"),
                label=device.get("deviceLabel"),
                protocol="zwave",
                manufacturer_id=_zwave_identifier(device.get("manufacturerId")),
                product_type=_zwave_identifier(device.get("productType")),
                product_id=_zwave_identifier(device.get("productId")),
            )
        )
    return devices


def _zwave_identifier(value: object) -> str:
    """Normalize 16-bit numeric protocol IDs; do not infer a marketing model."""
    if isinstance(value, str):
        try:
            value = int(value, 16 if value.lower().startswith("0x") else 10)
        except ValueError as exc:
            raise ValueError(f"Invalid Z-Wave identifier {value!r}") from exc
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 0xFFFF:
        raise ValueError(f"Invalid Z-Wave identifier {value!r}")
    return f"0x{value:04X}"


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return check_bounds(yaml.safe_load(handle) or {})


def fetch_remote_directory(
    repo: str,
    branch: str,
    subpath: str,
    token: str | None,
    timeout: float,
) -> list[str]:
    url = f"{GITHUB_API_URL}/repos/{repo}/contents/{subpath.strip('/')}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "edge-driver-auto-patching",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    params = {"ref": branch}
    response = requests.get(url, headers=headers, params=params, timeout=timeout)
    if response.status_code != 200:
        raise RuntimeError(f"Failed to list {repo}/{subpath}: {response.status_code} {response.text}")
    entries = response.json()
    return [entry["name"] for entry in entries if entry.get("type") == "dir"]


def fetch_remote_yaml(repo: str, branch: str, path: str, timeout: float) -> dict | None:
    url = f"https://raw.githubusercontent.com/{repo}/{branch}/{path.strip('/')}"
    response = requests.get(url, timeout=timeout)
    if response.status_code != 200:
        LOGGER.debug("Skipping %s (HTTP %s)", path, response.status_code)
        return None
    return check_bounds(yaml.safe_load(response.text) or {})


def discover_from_github(
    repo: str,
    branch: str,
    subpath: str,
    token: str | None,
    limit: int | None,
    timeout: float,
) -> list[DriverFingerprint]:
    driver_names = fetch_remote_directory(repo, branch, subpath, token, timeout)
    fingerprints: list[DriverFingerprint] = []
    processed = 0
    for driver_name in driver_names:
        if limit is not None and processed >= limit:
            break
        fp_path = f"{subpath.strip('/')}/{driver_name}/fingerprints.yml"
        data = fetch_remote_yaml(repo, branch, fp_path, timeout)
        if not data:
            continue
        driver_fps = parse_fingerprints(driver_name, data)
        if not driver_fps:
            # The limit counts drivers that actually yield fingerprints: a
            # Matter-shaped fingerprints.yml (no zigbeeManufacturer key)
            # contributes nothing, and counting it against the limit makes a
            # small --limit return nothing even though Zigbee drivers follow.
            continue
        fingerprints.extend(driver_fps)
        processed += 1
    return fingerprints


def discover_from_local(base_dir: Path, subpath: str, limit: int | None) -> list[DriverFingerprint]:
    target_dir = (base_dir / subpath).resolve()
    if not target_dir.exists():
        raise FileNotFoundError(f"Local driver path not found: {target_dir}")
    fingerprints: list[DriverFingerprint] = []
    processed = 0
    for driver_dir in sorted(target_dir.iterdir()):
        # Checked before any work, matching discover_from_github, so that a
        # limit of 0 processes nothing instead of the first driver.
        if limit is not None and processed >= limit:
            break
        if driver_dir.is_dir():
            fp_file = driver_dir / "fingerprints.yml"
            if not fp_file.exists():
                continue
            data = load_yaml(fp_file)
            driver_fps = parse_fingerprints(driver_dir.name, data)
            if not driver_fps:
                # Same accounting as discover_from_github: only drivers that
                # yield fingerprints count against the limit.
                continue
            fingerprints.extend(driver_fps)
            processed += 1
    return fingerprints


def summarize_fingerprints(fingerprints: Iterable[DriverFingerprint]) -> tuple[list[dict], dict]:
    drivers: dict[str, list[DriverFingerprint]] = {}
    for fp in fingerprints:
        drivers.setdefault(fp.driver, []).append(fp)

    driver_entries = []
    total = 0
    for driver_name, entries in sorted(drivers.items()):
        driver_entries.append(
            {
                "driver": driver_name,
                "fingerprints": [fp.__dict__ for fp in entries],
            }
        )
        total += len(entries)

    stats = {"driver_count": len(driver_entries), "fingerprint_count": total}
    return driver_entries, stats


def detect_unsupported_drivers(drivers: list[dict], capability_config: Path | None) -> list[str]:
    if capability_config is None:
        return []
    config = configparser.ConfigParser()
    config.read(capability_config)
    known_drivers = set(config.sections())
    missing = []
    for driver in drivers:
        if driver["driver"] not in known_drivers:
            missing.append(driver["driver"])
    return sorted(missing)


def build_driver_catalog(
    source: str,
    repo: str,
    branch: str,
    local_dir: Path | None,
    driver_subpath: str,
    token: str | None,
    limit: int | None,
    timeout: float,
) -> list[DriverFingerprint]:
    if source == "github":
        return discover_from_github(repo, branch, driver_subpath, token, limit, timeout)
    if source == "local":
        if local_dir is None:
            raise ValueError("local_dir is required when source='local'")
        return discover_from_local(local_dir, driver_subpath, limit)
    raise ValueError(f"Unknown source '{source}'")


def write_output(data: dict, output: Path, fmt: str) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "json":
        output.write_text(json.dumps(data, indent=2), encoding="utf-8")
    else:
        output.write_text(yaml.dump(data, sort_keys=False), encoding="utf-8")
    LOGGER.info("Catalog written to %s", output)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Discover SmartThings Edge drivers")
    parser.add_argument(
        "--source",
        choices=["github", "local"],
        default="github",
        help="Where to discover drivers from",
    )
    parser.add_argument(
        "--repo", default="SmartThingsCommunity/SmartThingsEdgeDrivers", help="GitHub repo to query"
    )
    parser.add_argument("--branch", default="main", help="Git branch to use")
    parser.add_argument("--driver-subpath", default=DEFAULT_DRIVER_SUBPATH, help="Driver subdirectory")
    parser.add_argument("--local-dir", type=Path, help="Local directory containing drivers")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("discovery/catalog.json"),
        help="Catalog output path",
    )
    parser.add_argument("--format", choices=["json", "yaml"], default="json", help="Output format")
    parser.add_argument(
        "--limit",
        type=non_negative_int,
        help="Stop after this many drivers (0 processes none; omit for no limit)",
    )
    parser.add_argument("--timeout", type=float, default=15.0, help="Request timeout in seconds")
    parser.add_argument(
        "--cap-config",
        type=Path,
        default=Path("auto_patch/custom_capability_list.config"),
        help="Capability config to compare against",
    )
    parser.add_argument("--token", help="GitHub token (defaults to GITHUB_TOKEN env var)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configure_logging(args.verbose)
    token = args.token or os.getenv("GITHUB_TOKEN")
    try:
        fingerprints = build_driver_catalog(
            source=args.source,
            repo=args.repo,
            branch=args.branch,
            local_dir=args.local_dir,
            driver_subpath=args.driver_subpath,
            token=token,
            limit=args.limit,
            timeout=args.timeout,
        )
    except Exception as exc:  # noqa: BLE001
        LOGGER.error("Failed to build catalog: %s", exc)
        raise SystemExit(1) from exc

    drivers, stats = summarize_fingerprints(fingerprints)
    unsupported = detect_unsupported_drivers(drivers, args.cap_config)

    catalog = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source": {
            "type": args.source,
            "repo": args.repo if args.source == "github" else None,
            "branch": args.branch if args.source == "github" else None,
            "local_dir": str(args.local_dir) if args.source == "local" else None,
            "driver_subpath": args.driver_subpath,
        },
        "stats": stats,
        "drivers": drivers,
        "unsupported_drivers": unsupported,
    }

    write_output(catalog, args.output, args.format)


if __name__ == "__main__":
    main()
