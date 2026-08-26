# Patching SmartThings Edge drivers

Retrofit a stock SmartThings Edge driver so it exposes Zigbee attributes the
shipped distribution hides. This is the `auto_patch` component, reachable as
`edgeloom patch`.

> Every mutating run backs the driver up first and rolls the backup back if any
> step fails. See [SECURITY.md](../SECURITY.md) for the safety and disclosure
> model.

## Requirements

- Python 3.11+
- `pip`
- Any platform supported by Python. The alternative `auto_patch.sh` entrypoint
  requires bash (Linux, macOS, or Windows with Git Bash/WSL).
- SmartThings Edge driver source available as a local directory

### Prefer Containers?

A ready-to-use Docker image is provided for contributors who would rather not
install Python locally. See
[Containerized Development](development.md#containerized-development) for details.

Install the package and development dependencies from the repository root:

```bash
python -m pip install -e ".[dev]"
```

## Quickstart

1. Clone this repository and `cd` into it.
2. Copy the Edge driver you want to patch inside the `auto_patch/` directory.
3. Run the patcher:

   ```bash
   # From the repository root:
   edgeloom patch auto_patch/zigbee-lock "YRD226 TSDB" Yale ALL
   ```

4. The patched driver replaces the original folder, while a
   `zigbee-lock-backup` directory preserves the stock bits.

Use `--dry-run` when trying a new driver or attribute list:

```bash
# From the repository root:
edgeloom patch auto_patch/zigbee-lock "YRD226 TSDB" Yale Language --dry-run
```

Nothing is written to disk; you simply see the steps that would run.

## Usage Details

```text
edgeloom patch [-n|--dry-run] DRIVER MODEL MANUFACTURER [ATTRIBUTES]
```

- `DRIVER`: path to the driver directory, resolved relative to the current
  working directory.
- `MODEL`: model string from SmartThings Advanced Web App.
- `MANUFACTURER`: manufacturer string from the same page.
- `ATTRIBUTES`: optional colon (`:`) separated list (for example,
  `Language:AutoRelockTime`); defaults to `ALL`.

The bash entrypoint remains available as an alternative:

```bash
# From the repository root:
cd auto_patch
./auto_patch.sh [-n|--dry-run] [-v|--verbose] DriverName DeviceModel Manufacturer AttributeList
```

The two entrypoints resolve driver paths differently. `edgeloom patch` uses the
directory where you run the command, while `auto_patch.sh` changes into its own
`auto_patch/` directory before resolving `DriverName`. Consequently,
`auto_patch/zigbee-lock` is the unambiguous path from the repository root for
the Python CLI, while the shell command uses `zigbee-lock`.

### Workflow Overview

1. **Profiles & fingerprints** – `patch_profiles.py`
   - Backs up `fingerprints.yml`
   - Points the requested model at a new `*-patch` profile
   - Clones the original profile and appends the desired capabilities
2. **Capability handlers** – `patch_handlers.py`
   - Copies the appropriate Lua handler from `cap-patches/`
   - Skips copies when you rerun the script
3. **Subdriver wiring** – `patch_subdriver.py`
   - Copies a subdriver template from `subdrivers/`
   - Adds the manufacturer/model to `PATCHED_DEVICE_MODELS`
   - Injects the new subdriver into the parent driver’s `sub_drivers` table

## Restoring to Stock Drivers

Every non-dry-run patch preserves the original driver in a sibling directory
named `<driver>-backup` (for example `zigbee-lock-backup`). Undo a patch and
bring the stock driver back with the CLI:

```bash
edgeloom restore /path/to/zigbee-lock
```

`DRIVER` is a path to the driver directory, resolved relative to the current
working directory just like `edgeloom patch`. The command parks the patched
tree in a timestamped folder such as `zigbee-lock-patched-YYYYMMDD-HHMMSS` and
moves the backup back to `zigbee-lock`. Pass `--dry-run` to preview the moves
without writing anything.

The original helper script remains available as an alternative:

```bash
# From the repository root:
cd auto_patch
python restore_from_backup.py --driver zigbee-lock
```

`--verbose` there enables debug output, and `--dry-run` logs the moves without
changing the filesystem.

## Configuration Files

- `custom_capability_list.config` – maps human-friendly attribute names to
  custom capability IDs. Extend this file when a driver learns new attributes.
- `driver2patch.config` – links drivers to their handler file name and
  subdriver directory. Add entries here when supporting new drivers.

## Find Device Model and Manufacturer

Use the [SmartThings web app](https://my.smartthings.com) and navigate to
**Advanced Users** to read the device’s model and manufacturer strings. These
values must match the inputs passed to the patcher.

![mysmartthings](../assets/mysmartthings.png)

## Currently Supported Drivers and Attributes

<table>
  <tr>
    <th> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; SmartThings Edge Drivers &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</th>
    <th> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Attributes &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</th>
  </tr>
  <tr>
    <td rowspan="9">zigbee-lock</td>
    <td>Language</td>
  </tr>
  <tr><td>AutoRelockTime</td></tr>
  <tr><td>SoundVolume</td></tr>
  <tr><td>OperatingMode</td></tr>
  <tr><td>EnableOneTouchLocking</td></tr>
  <tr><td>EnableInsideStatusLED</td></tr>
  <tr><td>EnablePrivacyModeButton</td></tr>
  <tr><td>WrongCodeEntryLimit</td></tr>
  <tr><td>UserCodeTemporaryDisableTime &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td></tr>

  <tr>
    <td>zigbee-siren</td>
    <td>MaxDuration</td>
  </tr>

  <tr>
    <td rowspan="2">hue-motion</td>
    <td>PIROccupiedToUnoccupiedDelay</td>
  </tr>
  <tr><td>MotionSensitivity</td></tr>

  <tr>
    <td rowspan="8">zigbee-switch</td>
    <td>IdentifyTime</td>
  </tr>
  <tr><td>DeviceEnabled</td></tr>
  <tr><td>OnOffTransitionTime</td></tr>
  <tr><td>OnLevel</td></tr>
  <tr><td>OnTime</td></tr>
  <tr><td>OffWaitTime</td></tr>
  <tr><td>StartUpOnOff</td></tr>
  <tr><td>StartUpColorTemperatureMireds</td></tr>

  <tr>
    <td rowspan="2">zigbee-dimmer-switch</td>
    <td>CheckInInterval</td>
  </tr>
  <tr><td>FastPollTimeout</td></tr>

  <tr>
    <td rowspan="4">zigbee-contact</td>
    <td>IdentifyTime</td>
  </tr>
  <tr><td>DeviceEnabled</td></tr>
  <tr><td>CheckInInterval</td></tr>
  <tr><td>FastPollTimeout</td></tr>

  <tr>
    <td rowspan="4">zigbee-water-leak-sensor</td>
    <td>IdentifyTime</td>
  </tr>
  <tr><td>DeviceEnabled</td></tr>
  <tr><td>CheckInInterval</td></tr>
  <tr><td>FastPollTimeout</td></tr>

  <tr>
    <td rowspan="4">zigbee-button</td>
    <td>IdentifyTime</td>
  </tr>
  <tr><td>DeviceEnabled</td></tr>
  <tr><td>CheckInInterval</td></tr>
  <tr><td>FastPollTimeout</td></tr>

  <tr>
    <td rowspan="4">zigbee-motion-sensor</td>
    <td>IdentifyTime</td>
  </tr>
  <tr><td>DeviceEnabled</td></tr>
  <tr><td>CheckInInterval</td></tr>
  <tr><td>FastPollTimeout</td></tr>

  <tr>
    <td rowspan="3">zigbee-presence-sensor</td>
    <td>IdentifyTime</td>
  </tr>
  <tr><td>CheckInInterval</td></tr>
  <tr><td>FastPollTimeout</td></tr>
</table>
