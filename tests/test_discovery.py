import sys
from pathlib import Path

import pytest

from discovery.discover_drivers import (
    build_driver_catalog,
    detect_unsupported_drivers,
    discover_from_local,
    parse_args,
    parse_fingerprints,
    summarize_fingerprints,
)


def test_local_discovery(driver_copy: Path) -> None:
    fingerprints = build_driver_catalog(
        source="local",
        repo="",
        branch="",
        local_dir=driver_copy.parent,
        driver_subpath=".",
        token=None,
        limit=None,
        timeout=1,
    )

    drivers, stats = summarize_fingerprints(fingerprints)
    assert stats["driver_count"] == 1
    assert stats["fingerprint_count"] > 0
    assert drivers[0]["driver"] == "zigbee-lock"


def test_detects_unsupported_driver(driver_copy: Path, tmp_path) -> None:
    fingerprints = build_driver_catalog(
        source="local",
        repo="",
        branch="",
        local_dir=driver_copy.parent,
        driver_subpath=".",
        token=None,
        limit=None,
        timeout=1,
    )
    drivers, _ = summarize_fingerprints(fingerprints)

    fake_config = tmp_path / "caps.config"
    fake_config.write_text("[other-driver]\nattr=value\n", encoding="utf-8")

    unsupported = detect_unsupported_drivers(drivers, fake_config)
    assert "zigbee-lock" in unsupported


def _driver_tree(root: Path, names: list[str]) -> Path:
    """Build a local driver directory holding one fingerprints.yml per name."""
    for name in names:
        driver = root / name
        driver.mkdir(parents=True)
        (driver / "fingerprints.yml").write_text(
            "zigbeeManufacturer:\n"
            f"  - id: Acme/{name}\n"
            "    deviceLabel: Acme Device\n"
            "    manufacturer: Acme\n"
            f"    model: {name.upper()}\n"
            "    deviceProfileName: base\n",
            encoding="utf-8",
        )
    return root


def test_local_zero_limit_processes_nothing(tmp_path: Path) -> None:
    tree = _driver_tree(tmp_path / "drivers", ["alpha", "beta", "gamma"])

    assert discover_from_local(tree.parent, "drivers", 0) == []


def test_local_positive_limit_stops_after_that_many_drivers(tmp_path: Path) -> None:
    tree = _driver_tree(tmp_path / "drivers", ["alpha", "beta", "gamma"])

    result = discover_from_local(tree.parent, "drivers", 2)

    assert sorted({fp.driver for fp in result}) == ["alpha", "beta"]


def test_local_omitted_limit_is_unlimited(tmp_path: Path) -> None:
    tree = _driver_tree(tmp_path / "drivers", ["alpha", "beta", "gamma"])

    result = discover_from_local(tree.parent, "drivers", None)

    assert sorted({fp.driver for fp in result}) == ["alpha", "beta", "gamma"]


def test_discovery_script_rejects_a_negative_limit(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "argv", ["discover_drivers.py", "--limit", "-1"])
    with pytest.raises(SystemExit) as exc:
        parse_args()
    assert exc.value.code == 2
    assert "--limit" in capsys.readouterr().err


def test_discovery_script_accepts_zero_as_a_real_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["discover_drivers.py", "--limit", "0"])
    assert parse_args().limit == 0

    monkeypatch.setattr(sys, "argv", ["discover_drivers.py"])
    assert parse_args().limit is None


def test_zwave_identity_is_normalized_without_inventing_a_model() -> None:
    result = parse_fingerprints(
        "zwave-lock",
        {
            "zwaveManufacturer": [
                {
                    "id": "Yale/YRD156",
                    "manufacturerId": 0x0129,
                    "productType": "0x803a",
                    "productId": 0x0508,
                    "deviceProfileName": "base-lock",
                }
            ]
        },
    )
    assert len(result) == 1
    fingerprint = result[0]
    assert fingerprint.protocol == "zwave"
    assert fingerprint.manufacturer_id == "0x0129"
    assert fingerprint.product_type == "0x803A"
    assert fingerprint.product_id == "0x0508"
    assert fingerprint.model is None
    assert fingerprint.device_id == "Yale/YRD156"


@pytest.mark.parametrize("identifier", [True, -1, 65536, None, "not-hex"])
def test_invalid_zwave_identifiers_fail_cleanly(identifier) -> None:
    with pytest.raises(ValueError, match="Z-Wave identifier"):
        parse_fingerprints(
            "lock", {"zwaveManufacturer": [{"manufacturerId": identifier, "productType": 2, "productId": 3}]}
        )
