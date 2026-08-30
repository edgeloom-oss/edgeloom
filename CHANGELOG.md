# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `edgeloom audit` and the v0.1 evidence-record schema capture one local
  artifact byte snapshot, asserted source metadata, bounded syntax results,
  optional pinned JSON-Schema checks with explicit authority labels, and
  limitations. Generated JSON records validate against their bundled contract;
  output replacement is atomic, non-local schema references are rejected, and
  recorded validation diagnostics are bounded.
- Draft 2020-12 contracts for immutable upstream source manifests and catalog
  mapping sets. They model device/protocol support, native platform exposure,
  and neutral SDF representation as separate evidence layers; preserve
  one-to-one, lossy, ambiguous, and unbound outcomes; and keep upstream source
  maturity distinct from EdgeLoom review lifecycle. `edgeloom validate` ships
  and autodetects both contracts and checks duplicate IDs and internal
  references without fetching or executing upstream content.
- Public governance, maintainer, support, and code-ownership documents now
  define decision records, contribution roles, support channels, and review
  responsibility.

### Security

- **Bounded documents parsed from untrusted sources.** `yaml.safe_load` stores
  aliases as shared references, so a driver file with nested anchors parsed
  cheaply and only became expensive in whatever walked it — `jsonschema` in
  `edgeloom validate`, `json.dumps` in `edgeloom discover`. A 420-byte profile
  drove validate to multi-gigabyte RSS, and a 483-byte `fingerprints.yml`
  produced a 200 MB catalog. Both now measure the expansion before walking it,
  memoised per object identity so the check costs the document's distinct nodes
  rather than the expansion it describes, and report a diagnostic instead.
  Closes #44 and #45. `load_document` also reports non-UTF-8 and
  over-deep documents instead of raising a traceback.

### Changed

- Contribution and pull-request guidance now asks for explicit compatibility,
  security-boundary, documentation, and test evidence.
- The Code of Conduct now names a working private reporting address instead of
  a placeholder.
- `SECURITY.md` now states what EdgeLoom trusts. The absence of that section is
  what made GHSA-4f7m-wgh7-46xf possible to misjudge: a driver's own files are
  attacker-controlled on the primary path, and the document did not say so.

### Fixed

- The profile schema now rejects exact duplicate component and capability entries.
- `discover --limit N` now counts drivers that actually yield fingerprints.
  A `fingerprints.yml` without a `zigbeeManufacturer` key (e.g. Matter
  drivers) no longer consumes the limit, which made small limits return
  nothing even though Zigbee drivers followed.

## [0.1.1] - 2026-08-24

### Security

- **Symlinks in a driver defeated path containment.** Two defects, both
  reachable from a driver the operator downloaded. `contained_path` resolved
  its own base, and `patch_profiles` passed `driver_dir/profiles` as that base,
  so a driver shipping `profiles` as a symlink relocated the containment anchor
  itself and every write under it was judged contained — reopening the escape
  the guard was added to close. Separately, `patch_handlers` and
  `patch_subdriver` applied no containment at all, so a symlinked `src/`, or a
  single symlinked `src/init.lua`, redirected the code-generation writes and an
  in-place Lua rewrite onto a file outside the driver. Containment now anchors
  on the driver directory the operator named, refuses symlinked components
  outright rather than following them, and is applied at every write site in
  all three patch steps.

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

- **Unescaped model and manufacturer names corrupted generated Lua.**
  `patch_subdriver.py` interpolated both into a driver's `PATCHED_DEVICE_MODELS`
  table without escaping, so any legitimate value containing a double quote or
  backslash silently produced broken Lua while the patch reported success. All
  three sites that emit Lua now go through `auto_patch/luagen.lua_string`, which
  escapes backslash before quote and refuses control characters.

  This was investigated as a possible injection vulnerability and is not one:
  the only party who can meet the preconditions is the driver publisher, who
  already ships the `src/*.lua` that EdgeLoom copies through byte-identical and
  that the hub executes at the driver's main entry point. The escaping is a
  correctness fix.

- `edgeloom validate` now reports profiles and capability maps that omit their
  required `name` or `version` key instead of silently skipping them.
- The translator now writes `config/ha_devices.yaml` with owner-only
  permissions (`0600`) when it contains the Home Assistant token, and a
  previously world-readable file is tightened on overwrite.

### Added

- `translate --no-token` (both the `edgeloom` and `ha2st_edge` CLIs) keeps the
  Home Assistant token out of the generated config; supply `HA_EDGE_TOKEN` on
  the hub instead.

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
