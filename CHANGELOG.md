# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.1] - 2026-08-24

### Security

- **Path containment for driver-supplied profile names.** A driver's
  `fingerprints.yml` is authored by whoever published that driver, and
  `patch_profiles.py` used its `deviceProfileName` to build filesystem paths
  without validating it. A name carrying parent components or an absolute path
  caused the generated profile to be written outside the driver directory, and
  could silently overwrite an existing file whose name ended in `-patch.yml`.
  The value is now required to be a bare identifier, and the resolved
  destination is re-checked against the driver's `profiles/` directory at the
  write boundary. Reported by Marcos Maia Jr. through the process in
  `SECURITY.md`, answering question 3 of #31.

### Fixed

- `edgeloom validate` now reports profiles and capability maps that omit their
  required `name` or `version` key instead of silently skipping them.

## [0.1.0] - 2026-08-23

First release under the EdgeLoom name. Unifies the SmartThings Edge driver
patcher and the Home Assistant translator into one installable toolchain with a
published schema between them.

### Added

- **Unified `edgeloom` CLI** with four subcommands: `patch`, `translate`,
  `discover`, and `validate`.
- **Schema v0.1** — two JSON Schemas (draft 2020-12) published under `schema/`:
  `profile.schema.json` for device profiles and `capability-map.schema.json` for
  attribute-to-capability bindings. Both ship inside the installed package.
- **`edgeloom validate`** as a CI-ready assurance gate. It checks profiles
  emitted by either toolchain path against one contract, and exits non-zero both
  on a violation and on finding nothing to check.
- **`auto_patch/capability-map.yaml`**, generated from the legacy INI pair and
  validated in CI, so the schema is grounded in the mapping actually in use.
- **Python packaging** via hatchling. `pip install edgeloom` provides the CLI;
  the distribution spans `edgeloom`, `auto_patch`, `discovery`, and
  `ha2st_edge`.
- **Home Assistant translator** merged from
  [HA2ST-Translator](https://github.com/edgeloom-oss/HA2ST-Translator) with its
  commit history preserved, now at `translator/` and reachable as
  `edgeloom translate`.
- **`SECURITY.md`** with a private disclosure path and an explicit statement of
  the tool's by-design behaviour.
- **First tests for the shell entrypoint**, covering backup creation, reuse,
  dry-run, and argument rejection.

### Fixed

- **`auto_patch.sh` never created the driver backup.** The guard used `else:`
  rather than the bash reserved word `else`, so it parsed as a command inside
  the then-list and the if-statement had no else-branch. On a first run the
  backup step was skipped entirely and the driver was patched destructively,
  contradicting the documented safety guarantee; when a backup did exist the
  stray command aborted the run at exit 127. `bash -n` reports the file clean,
  and CI linted only Python, so nothing caught it.
- **A failed patch could delete the driver.** `restore_backup` ran
  `rm -rf "$DRIVER"` before moving the backup into place, without checking the
  backup existed — which, given the bug above, it never did. Restore now refuses
  to remove anything when no backup is present.
- **`auto_patch.sh` failed on macOS.** The three step invocations expanded
  `"${COMMON_ARGS[@]}"` directly, and bash 3.2 treats expansion of an empty
  array under `set -u` as an unbound variable error, so every run without an
  optional flag — including the documented Quickstart command — died at step 1.
- **`auto_patch.sh` was not executable** (mode 644), so the documented
  `./auto_patch.sh` failed on a fresh clone.
- **Two wrong assertions** in the translator's `test_generate_profiles_and_config`,
  which expected device entries to be de-duplicated the way profiles are.

### Changed

- Minimum Python is now **3.11**. `discovery` imports `datetime.UTC`, which does
  not exist earlier, so the previously documented "Python 3.10+" was inaccurate.
- `edgeloom patch` orchestrates the three patch steps in Python rather than
  through bash, so patching runs on native Windows and is directly testable.
  `auto_patch/auto_patch.sh` remains available.
- The README is now an umbrella; component detail moved to `docs/`.
- The merged translator is covered by the repository's `ruff` and pytest gates.

[Unreleased]: https://github.com/edgeloom-oss/edgeloom/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/edgeloom-oss/edgeloom/releases/tag/v0.1.0
