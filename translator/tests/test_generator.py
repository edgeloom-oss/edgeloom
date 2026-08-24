import stat
import sys
from pathlib import Path

import pytest
import yaml
from ha2st_edge.generator import generate_profiles_and_config
from ha2st_edge.mapping import DeviceProfileSpec

posix_only = pytest.mark.skipif(sys.platform == "win32", reason="POSIX mode bits")


def _mapped() -> list[dict]:
    return [
        {
            "state": {"entity_id": "light.lamp", "attributes": {"friendly_name": "Lamp", "brightness": 50}},
            "profile": DeviceProfileSpec("ha_light_dimmable", ["switch", "switchLevel"], "Light"),
        },
        {
            "state": {"entity_id": "light.rgb", "attributes": {"friendly_name": "RGB", "hs_color": [1, 2]}},
            "profile": DeviceProfileSpec(
                "ha_light_color", ["switch", "switchLevel", "colorControl"], "Light"
            ),
        },
        {
            "state": {"entity_id": "switch.plug", "attributes": {"friendly_name": "Plug"}},
            "profile": DeviceProfileSpec("ha_switch_basic", ["switch"], "Switch"),
        },
    ]


def test_generate_profiles_and_config(tmp_path: Path):
    generate_profiles_and_config(
        _mapped(), tmp_path, ha_base_url="http://ha.local:8123", ha_token="TEST_TOKEN"
    )

    profiles_dir = tmp_path / "profiles"
    config_dir = tmp_path / "config"
    assert (profiles_dir / "ha_light_dimmable.yaml").exists()
    assert (profiles_dir / "ha_light_color.yaml").exists()
    assert (profiles_dir / "ha_switch_basic.yaml").exists()
    cfg_path = config_dir / "ha_devices.yaml"
    assert cfg_path.exists()

    cfg = yaml.safe_load(cfg_path.read_text())
    assert cfg["ha_base_url"] == "http://ha.local:8123"
    assert cfg["ha_token"] == "TEST_TOKEN"
    # One device entry per mapped HA entity. Profiles are de-duplicated (three
    # entities, three distinct profiles here), but devices are not: each HA
    # entity has to surface as its own SmartThings device.
    assert len(cfg["devices"]) == 3
    assert [d["profile"] for d in cfg["devices"]] == [
        "ha_light_dimmable",
        "ha_light_color",
        "ha_switch_basic",
    ]
    assert [d["ha_entity_id"] for d in cfg["devices"]] == ["light.lamp", "light.rgb", "switch.plug"]


@posix_only
def test_config_containing_a_token_is_owner_readable_only(tmp_path: Path):
    generate_profiles_and_config(_mapped(), tmp_path, ha_base_url="http://ha.local", ha_token="SECRET")

    mode = stat.S_IMODE((tmp_path / "config" / "ha_devices.yaml").stat().st_mode)

    assert mode == 0o600, f"credential file is {oct(mode)}, expected 0o600"


@posix_only
def test_a_previously_world_readable_config_is_tightened(tmp_path: Path):
    """An earlier run may have left the file at the umask default."""
    config = tmp_path / "config"
    config.mkdir()
    stale = config / "ha_devices.yaml"
    stale.write_text("ha_token: OLD\n", encoding="utf-8")
    stale.chmod(0o644)

    generate_profiles_and_config(_mapped(), tmp_path, ha_base_url="http://ha.local", ha_token="SECRET")

    assert stat.S_IMODE(stale.stat().st_mode) == 0o600


def test_no_token_omits_the_credential(tmp_path: Path):
    generate_profiles_and_config(_mapped(), tmp_path, ha_base_url="http://ha.local", ha_token=None)

    written = (tmp_path / "config" / "ha_devices.yaml").read_text(encoding="utf-8")

    assert "ha_token" not in written
    assert "ha_base_url" in written
