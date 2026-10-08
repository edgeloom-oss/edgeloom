# Device Evidence Bundle — draft v0.1

Status: proposed implementation for public review. This format is an EdgeLoom
contribution and publication convention, not an IETF standard or certification.
Public design discussion: [issue #63](https://github.com/edgeloom-oss/edgeloom/issues/63).

## Problem and intended result

Driver behavior is explained across manuals, implementation code, observations,
and reviews. A device evidence bundle preserves those relationships in a
versioned, portable report. A contributor can add one source or observation;
a maintainer assembles a scoped package without inventing missing experiments
or an SDF mapping. The first example follows Yale YRD210 battery normalization.

## Additive records

The existing source-manifest and mapping-set v0.1 contracts remain unchanged.
Three new **draft** contracts belong to core:

- `document-source`: publisher, document version, URL, access date, explicit
  applicability, citation locations and rights. `link-only` is distinct from
  a recorded content digest; neither implies included or archived source bytes.
- `catalog-observation`: one reported execution with subject, feature, method
  (`physical-device` or `simulation`), environment, procedure, expected/observed
  result, outcome, reporter and evidence links. Synthetic examples are labeled.
  A proposed test belongs in a bundle's test plan, not in an observation.
- `device-evidence-bundle`: subject and version, a closed list of exact record
  paths and SHA-256 digests, feature explanations and cited implementation
  decisions, test plans, gaps, scoped review references, history and credits.

New contributions need no fabricated mapping. Bundle validation is independent
of the legacy catalog's minimum source/mapping inventory. Existing records are
referenced by their current IDs and included as catalog-authored metadata.
Device associations and feature associations must agree when declared.

## Boundaries and compatibility

New bundles and observations are candidate by default. Publication does not
change the review lifecycle of a constituent record. Reviews identify exact
record hashes and an external decision URL; stale hashes fail validation.
Review fields remain declarations, with trust established through governed
repository history. Independent reviewers cannot be the relevant record author.

Manuals and drivers remain at their upstream locations. The package contains
catalog-authored records and generated reports, not third-party source bytes.
No build, validation, or verification step downloads a manual, executes an
upstream driver, calls an AI service or operates hardware. Existing explicit
Git-source fetching retains its current limits.

The package records its catalog revision, core pin, schema and generator
digests. A modified checkout is labeled `working-tree`. Its integrity checks
cover package consistency; they do not authenticate a publisher or prove a
device claim. Package format, package content version and driver revision are
separate identifiers. Missing firmware or evidence stays explicit.

## Try the review branch

The commands below are implemented on `codex/device-evidence-bundles`, not in
PyPI 0.2.0. Use a new directory for this preview. Python 3.11+ and Git are needed;
installation needs network access. After installation these commands are offline.

```bash
git clone --branch codex/device-evidence-bundles https://github.com/edgeloom-oss/edgeloom-catalog.git
cd edgeloom-catalog
git clone https://github.com/edgeloom-oss/edgeloom.git .edgeloom-core
git -C .edgeloom-core checkout "$(tr -d '[:space:]' < CORE_REVISION)"
python3 -m venv .venv
. .venv/bin/activate
python -m pip install ./.edgeloom-core
edgeloom bundle check . yale-yrd210-battery
edgeloom bundle build . yale-yrd210-battery --output _bundle
edgeloom bundle verify _bundle/bundle.zip
python -m http.server 4178 --bind 127.0.0.1 --directory _bundle
```

Open `http://127.0.0.1:4178/`. The report shows two feature contexts, six locked
records, official manual references, implementation explanations and specific
requests for contributions. **There is no physical-device result or independent
review in this sample.** A source digest was recorded for the manual; bundle
verification does not retrieve or authenticate its upstream bytes.

## Command surface

```text
edgeloom bundle check CATALOG_ROOT BUNDLE_ID
edgeloom bundle build CATALOG_ROOT BUNDLE_ID --output REPORT_DIRECTORY
edgeloom bundle export CATALOG_ROOT BUNDLE_ID --output BUNDLE.zip
edgeloom bundle verify BUNDLE.zip
```

Exports sort paths and normalize ZIP metadata so the same inputs and tool
produce identical bytes. Verification rejects unsafe/duplicate paths, missing
or unexpected members, invalid records, broken references and digest mismatch.
Output does not overwrite unrelated files. Reports work offline.
`build` requires a new or empty output directory; `export` requires a new file.
`catalog build` also links and includes the optional bundles in its static view.

## Portable package

Each ZIP includes its original bundle manifest and locked catalog records,
the relevant schema snapshots, `report.json`, `report.md`, `index.html`,
`bundle.css`, `package.json` (inventory hashes) and `checksums.txt`.
The build directory additionally contains the downloadable ZIP. An extracted
archive has no nested copy of itself; its other report links remain local.
Verification reads the ZIP without extracting it and uses the installed
validator's trusted schemas, not arbitrary schema code from the archive. It
re-derives the report checks and HTML/Markdown/CSS from the packaged canonical
records. Use the declared core pin if a later verifier reports a policy/schema
mismatch; this draft does not promise cross-version verifier compatibility.

Bounds: 1 MiB per canonical record, 16 MiB of input records, 200 records per
bundle, 512 ZIP members, 8 MiB per generated member and 32 MiB total expanded
package. ZIP paths, duplicate entries, special files and encrypted members are
rejected. A valid hash inventory establishes internal consistency, **not a
signature, author authentication, semantic correctness or hardware safety**.

The catalog's `CORE_REVISION` is a declared reproducibility pin; the report also
records the actual generator and schema digests. The package version label is
not a software release attestation. A future release will assign a new software
version after approval; this work does not republish 0.2.0.

## Contribution and display

Each feature shows the current explanation, implementation decisions, document
citations, code comparisons, observations, proposed tests and open questions.
Links invite a source, observation, correction or scoped review, prefilled with
the bundle, version and feature. Credits identify the work contributed.
The catalog repository owns these records and submission templates; core owns
schemas, tools, rendering and software releases.

## Alternatives and rollout

A README-only dossier is easy to author but cannot reliably check exact
references or carry structured observations. Extending every existing mapping
record would couple community participation to SDF authoring. The proposed
additive package reuses those records while allowing earlier contribution stages.

Keep this design open under the project's substantial-change process while
preparing review branches. Deliver contracts and synthetic fixtures, tools and
reports, then the real catalog sample and contributor workflow. Acceptance of
this draft does not promote existing candidate mappings. A new software release
and publication of a website snapshot remain explicit release activities.

## Validation

- Standalone document/observation and partial bundles need no SDF mapping.
- Record closure, exact digests, subject/feature joins and review scope are checked.
- Wrong hashes, missing references, stale reviews and unsafe archives fail.
- Simulated/synthetic observations cannot become hardware evidence in reports.
- Repeated exports are byte-identical and verify without network access.
- A clean installed wheel contains the schemas, templates and CLI.
- The real sample retains absent hardware results as gaps; desktop/mobile
  reports show sources, explanations, versions, downloads and contribution links.

AI extraction, automated upstream drift fetching, additional devices and
automatic driver generation are follow-on work.
