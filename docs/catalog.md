# Device evidence catalog (development increment)

The `catalog` commands and draft `catalog-device` / `catalog-corroboration` schemas are **not in
PyPI 0.2.0**. Use the exact core commit pinned by the catalog checkout. Existing
source-manifest and mapping-set v0.1 contracts are unchanged.

See the [five-minute walkthrough](catalog-quickstart.md). Data belongs in
[`edgeloom-catalog`](https://github.com/edgeloom-oss/edgeloom-catalog); tools,
schemas, templates and tests belong here. Device entries provide explicit
protocol identity and feature-to-mapping associations; names are never inferred
from record titles. Associations are declarations, not device compatibility.

## Three explicit operations

```bash
# Offline contracts, manifest byte digests, artifact IDs and device associations
edgeloom catalog check /path/to/edgeloom-catalog

# Optional network operation: fixed commits, digest match, no redirects/execution
edgeloom catalog fetch /path/to/edgeloom-catalog --cache /path/to/source-cache

# Offline JSON + Markdown + buildless HTML from the same canonical records
edgeloom catalog build /path/to/edgeloom-catalog --output /path/to/new-view

# Optional recheck of already-fetched source bytes and bounded locators
edgeloom catalog build /path/to/edgeloom-catalog \
  --cache /path/to/source-cache --output /path/to/new-view
```

Neither `check` nor `build` makes network requests. Fetch supports public GitHub
repositories only, uses full commits, reads at most 1 MiB per artifact and 100
artifacts per run, and writes only digest-matched UTF-8 bytes to a local cache.
The cache is not redistributed and is separate from report output. License
fields remain assertions; downloading bytes does not establish legal authority.

Catalog input is limited to 500 structured source/mapping/device/corroboration documents,
1 MiB each and 16 MiB total. Unsafe paths, symlinks, duplicate IDs, broken
references, mismatching manifest hashes and protocol inconsistencies fail.
Existing nonempty output is refused unless it carries the generated-file
ownership marker. Unrelated files are never silently adopted or removed.

## Reading checks correctly

| Check | Establishes | Does not establish |
| --- | --- | --- |
| Contract / cross-record check | Shape and reference integrity | Correct interpretation |
| Manifest digest match | Mapping cites these manifest bytes | Authentic author or trusted lifecycle |
| Source byte match | Retrieved bytes match the declared digest | Correctness, currentness, or license authority |
| Locator `resolved` | A strict JSON pointer exists in the parsed snapshot | Completeness or semantic correspondence |
| Locator `manual-review` | Automated resolution is not implemented | Failure or success of the claim |
| Locator `not-found` | That exact pointer was not located | Whole-driver absence or device incompatibility |
| Review lifecycle | Catalog-declared state, governed through repository history | A status authenticated by this tool |
| Hardware links | Reported observations linked by a contributor | Hardware testing performed by this build |

Lua functions, selectors and JSON5 locators remain manual-review. No imported
Lua runs. A missing profile field is not whole-driver/UI absence, and a missing
property in one SDF model is not a limitation of SDF. Existing mapping
limitations, handler-path conditions and source maturity are retained in JSON
and the expanded HTML evidence panels. No patch availability is inferred.

## External corroboration

Candidate-only sidecars in `catalog/corroboration/` add parallel observations,
not same-layer semantic mapping edges or reviewer credits. They cite manifest
bytes, source locators, conditions, and a declared source-family dependency DAG.
Each device feature must reference a mapping or corroboration record. Orphan
records, wrong device/feature joins, mismatching declared identity fields,
unindexed sources, bad digests and cyclic/unknown lineage fail closed.

Model-specific observations declare only fields the upstream matcher actually
uses. A model-only matcher remains visibly weaker than a manufacturer/model
signature. Generic platform paths cannot carry a device identity match.
Neither check authenticates the interpretation of the upstream code. Python
and TypeScript selectors remain manual-review; no imports or execution occur.

`supports`, `conflicts`, `context` and `unresolved` are human-authored labels,
not inferred outcomes. All observations survive the build: no voting,
independence score or automatic review promotion. A simulated upstream test is
identified as `test-fixture`, not a hardware test or a test run performed here.
See [the evidence workflow](catalog-external-evidence.md).

## Static publication and reproducibility

`catalog.json`, device Markdown, HTML, CSS and JavaScript are generated together.
Reports have no wall-clock timestamp or local absolute paths. Their input digest
identifies canonical record paths, byte hashes and the declared core pin.
Generator policy, implementation digest and the core pin are recorded
separately; the package version label is not a release attestation.
A clean catalog Git checkout records its exact HEAD; changed catalog inputs
or `CORE_REVISION` produce a clearly labeled
`working-tree` export instead of a false commit pin.

The core website embeds a generated, commit-pinned snapshot in `site/catalog/`.
It is derived output, not another editable source of truth. Rebuild from the
same catalog commit and source cache to compare bytes. Updates are reviewed
commits, not browser-time API calls or automatic upstream ingestion. Do not
edit generated reports manually. The current Pages workflow still publishes
only approved `main` changes; a feature branch does not deploy.

Follow-on work: drift detection with affected-record reports, reviewed
expansion to 3–5 distinct lock models, external observations, and optional
human-supervised AI triage. These are not implemented or evidenced by this
first vertical slice.
