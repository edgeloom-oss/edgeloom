import logging
import os
from pathlib import Path
from typing import Any

import yaml

from .mapping import DeviceProfileSpec

LOG = logging.getLogger("ha2st_edge.generator")


def _write_secret_yaml(path: Path, payload: dict[str, Any]) -> None:
    """Write YAML containing a credential, readable only by its owner.

    The mode goes to os.open rather than a chmod after the write, so the file is
    never briefly world-readable. os.open's mode is ignored for a file that
    already exists, so fchmod covers the upgrade case where an earlier run left
    it at the umask default.
    """
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        if hasattr(os, "fchmod"):  # POSIX only; Windows has no mode bits here
            os.fchmod(handle.fileno(), 0o600)
        yaml.safe_dump(payload, handle, sort_keys=False)


def _profile_filename(profile_name: str) -> str:
    return f"{profile_name}.yaml"


def _render_profile_yaml(spec: DeviceProfileSpec) -> dict[str, Any]:
    return {
        "name": spec.profile_name,
        "components": [
            {
                "id": "main",
                "label": "Main",
                "capabilities": [{"id": cap, "version": 1} for cap in spec.capabilities],
                "categories": [{"name": spec.category}],
            }
        ],
        "metadata": {"vid": f"vid-{spec.profile_name}", "mnmn": "ha2st-edge"},
    }


def generate_profiles_and_config(
    mapped: list[dict[str, Any]], output_dir: Path, ha_base_url: str, ha_token: str | None = None
) -> None:
    profiles_dir = output_dir / "profiles"
    config_dir = output_dir / "config"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    config_dir.mkdir(parents=True, exist_ok=True)

    seen_profiles: dict[str, DeviceProfileSpec] = {}
    for item in mapped:
        spec: DeviceProfileSpec = item["profile"]
        if spec.profile_name not in seen_profiles:
            seen_profiles[spec.profile_name] = spec

    for spec in seen_profiles.values():
        profile_path = profiles_dir / _profile_filename(spec.profile_name)
        with profile_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(_render_profile_yaml(spec), f, sort_keys=False)

    devices_payload = []
    for item in mapped:
        state = item["state"]
        spec = item["profile"]
        label = state.get("attributes", {}).get("friendly_name") or state.get("entity_id")
        devices_payload.append(
            {
                "st_label": f"{label} (HA)",
                "ha_entity_id": state.get("entity_id"),
                "profile": spec.profile_name,
            }
        )

    config_payload = {"ha_base_url": ha_base_url, "devices": devices_payload}
    config_path = config_dir / "ha_devices.yaml"
    if ha_token:
        config_payload["ha_token"] = ha_token
        _write_secret_yaml(config_path, config_payload)
        LOG.warning(
            "%s contains your Home Assistant token. It is written owner-readable "
            "only; keep it out of version control. Pass --no-token to omit it and "
            "supply HA_EDGE_TOKEN on the hub instead.",
            config_path,
        )
    else:
        with config_path.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(config_payload, handle, sort_keys=False)
