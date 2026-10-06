# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Development-only `catalog check/fetch/build` commands join source manifests,
  mapping sets and explicitly identified device entries, check cross-record
  references and manifest digests, explicitly fetch bounded commit-pinned
  source bytes, and generate deterministic JSON/Markdown/static HTML reports.
  Source-byte checks, bounded JSON-pointer resolution, declared review states,
  hardware evidence and semantic limitations remain separate. No imported Lua
  is executed and no record is automatically promoted.
- Draft v0.1 `catalog-device` navigation contract, a searchable candidate
  catalog view, a no-account walkthrough and a disposable Zigbee
  patch/validate/restore demonstration. Catalog tooling is not in PyPI 0.2.0.
- Z-Wave manufacturer fingerprint discovery preserves normalized 16-bit
  identifiers without guessing a manufacturer name or device model. Generic
  Z-Wave/Matter fingerprints and automatic Z-Wave patching remain out of scope.

### Changed

- Reconcile catalog roadmap status with the populated founder-seeded pilot;
  distinguish one indexed model from three mapping sets and six assertions.
- Site link/lint checks now cover nested HTML and cross-page fragments.

## [0.2.0] - 2026-09-27

This release makes the six-workflow toolchain and its evidence/catalog
contracts available from one installable distribution. It contains every
change merged after the `v0.1.1` tag. The Home Assistant token-permission and
`--no-token` entries had appeared in the 0.1.1 changelog before their code was
merged; they are correctly attributed to 0.2.0 below.

### Added

- `edgeloom restore` is now a first-class CLI workflow, with dry-run support
  and explicit handling for drivers selected outside the repository checkout.
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
  references without fetching or executing upstream content. Portable source
  paths, explicit artifact roles, stable aggregation identifiers, independent
  reviewer checks, and an `unknown` maturity state preserve the boundary between
  a well-formed declaration and governed project trust.
- Public governance, maintainer, support, and code-ownership documents now
  define decision records, contribution roles, support channels, and review
  responsibility.
- A federated driver–SDF evidence-catalog roadmap defines the two-repository
  boundary, candidate-only ingestion gate, provenance requirements, semantic
  loss taxonomy, human-review roles, and staged sustainability plan.
- A lightweight project homepage, social-preview metadata, link checks, and a
  GitHub Pages workflow publish the project's verified public evidence from
  `main`.
- The patcher's capability map now includes the four hidden-attribute mappings
  used by the `zigbee-humidity-sensor` driver.

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
- **Restore paths and filesystem moves are contained.** The legacy helper now
  accepts only a bare driver name below its trusted root, while the unified CLI
  has a separate absolute operator-path entry point. Restore refuses symlinked
  backups and colliding destinations, and uses sibling filesystem renames so a
  destination link cannot redirect a move outside the selected parent.
- The translator writes `config/ha_devices.yaml` with owner-only permissions
  (`0600`) when it contains a Home Assistant token, and tightens a previously
  broader mode on overwrite. `translate --no-token`, available from both CLIs,
  omits the credential so `HA_EDGE_TOKEN` can be supplied on the hub instead.
- CI, Pages, and release workflows now use least-privilege tokens, non-persistent
  checkout credentials, and immutable action revisions. Release tags enter the
  shell through an environment boundary and must match stable `vX.Y.Z` SemVer.
- PyPI publication now loads its workflow only from the default branch, requires
  the tag and checkout to equal the current `main` tip, binds the gate to the
  exact successful `ci.yml` push run, and rechecks GitHub Release state before
  the OIDC-backed upload. The build toolchain is SHA-256 locked; exactly one
  wheel and one source distribution must pass embedded-metadata and digest
  verification before publication.

### Changed

- Contribution and pull-request guidance now asks for explicit compatibility,
  security-boundary, documentation, and test evidence.
- The Code of Conduct now names a working private reporting address instead of
  a placeholder.
- `SECURITY.md` now states what EdgeLoom trusts. The absence of that section is
  what made GHSA-4f7m-wgh7-46xf possible to misjudge: a driver's own files are
  attacker-controlled on the primary path, and the document did not say so.
- A maintainer release checklist now makes exact-commit review, clean-wheel
  smoke tests, workflow security checks, Trusted Publishing, and public-state
  read-back explicit gates.
- Runtime installations now include JSON Schema's non-GPL format checkers, so
  URI and date-time checks behave consistently in development and from wheels.

### Fixed

- `edgeloom validate` now rejects a profile that reuses a component id or a
  capability id even when the objects are not byte-identical. Completes #8.
- The profile schema now rejects exact duplicate component and capability entries.
- `discover --limit N` now counts drivers that actually yield fingerprints.
  A `fingerprints.yml` without a `zigbeeManufacturer` key (e.g. Matter
  drivers) no longer consumes the limit, which made small limits return
  nothing even though Zigbee drivers followed.
- `discover --limit 0` now processes zero drivers instead of treating zero as
  an omitted, unlimited value; negative limits are rejected at the CLI boundary.

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

[Unreleased]: https://github.com/edgeloom-oss/edgeloom/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/edgeloom-oss/edgeloom/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/edgeloom-oss/edgeloom/releases/tag/v0.1.1
[0.1.0]: https://github.com/edgeloom-oss/edgeloom/releases/tag/v0.1.0
