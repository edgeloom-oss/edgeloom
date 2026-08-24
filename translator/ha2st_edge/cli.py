import argparse
import logging
from pathlib import Path
from typing import Any

from .generator import generate_profiles_and_config
from .ha_client import HomeAssistantClient, HomeAssistantError
from .mapping import DeviceProfileSpec, infer_profile

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
LOG = logging.getLogger("ha2st_edge")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate SmartThings Edge proxy artifacts from Home Assistant."
    )
    parser.add_argument(
        "--ha-url",
        required=True,
        help="Base URL of Home Assistant (e.g., http://192.168.1.10:8123)",
    )
    parser.add_argument("--token", required=True, help="Long-lived Home Assistant token")
    parser.add_argument(
        "--domains",
        default="light,switch,lock,binary_sensor",
        help="Comma-separated HA domains to include (default: light,switch,lock,binary_sensor)",
    )
    parser.add_argument("--output", required=True, help="Output directory for generated Edge artifacts")
    parser.add_argument(
        "--no-token",
        action="store_true",
        help="Do not write the HA token into the generated config; set HA_EDGE_TOKEN on the hub instead",
    )
    return parser.parse_args()


def filter_entities(states: list[dict[str, Any]], domains: list[str]) -> list[dict[str, Any]]:
    filtered = []
    for state in states:
        entity_id = state.get("entity_id", "")
        domain = entity_id.split(".", 1)[0] if "." in entity_id else ""
        if domain in domains:
            filtered.append(state)
    return filtered


def translate(
    ha_url: str,
    token: str,
    output: str | Path,
    domains: str | list[str] = "light,switch,lock,binary_sensor",
    write_token: bool = True,
) -> int:
    """Fetch HA states, map them to Edge profiles, and write the artifacts.

    Extracted from main() so `edgeloom translate` and `python -m ha2st_edge.cli`
    drive exactly the same code path. Returns a process exit code.
    """
    if isinstance(domains, str):
        domains = [d.strip() for d in domains.split(",") if d.strip()]
    output_dir = Path(output)

    client = HomeAssistantClient(base_url=ha_url, token=token)
    try:
        states = client.get_states()
    except HomeAssistantError as exc:
        LOG.error("Failed to fetch states: %s", exc)
        return 1

    LOG.info("Fetched %d states from Home Assistant", len(states))
    entities = filter_entities(states, domains)
    LOG.info("Filtered to %d entities matching domains %s", len(entities), domains)

    mapped: list[dict[str, Any]] = []
    skipped: list[str] = []
    for state in entities:
        spec: DeviceProfileSpec | None = infer_profile(state)
        if spec is None:
            skipped.append(state.get("entity_id", "unknown"))
            continue
        mapped.append({"state": state, "profile": spec})

    if skipped:
        LOG.warning("Skipped %d entities with no mapping: %s", len(skipped), ", ".join(skipped))

    if not mapped:
        LOG.error("No entities were mapped; nothing to generate.")
        return 1

    # The token is always needed for the fetch above; write_token only decides
    # whether it is persisted into the generated config.
    generate_profiles_and_config(
        mapped, output_dir, ha_base_url=ha_url, ha_token=token if write_token else None
    )
    LOG.info("Generation complete at %s", output_dir)
    return 0


def main() -> int:
    args = parse_args()
    return translate(
        ha_url=args.ha_url,
        token=args.token,
        output=args.output,
        domains=args.domains,
        write_token=not args.no_token,
    )


if __name__ == "__main__":
    raise SystemExit(main())
