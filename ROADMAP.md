# EdgeLoom roadmap

EdgeLoom is an active open-source toolchain for validating, patching,
restoring, translating, and discovering smart-home edge-driver artifacts. The
next product step is to make the evidence around those artifacts reusable:
what exact source was inspected, what a platform exposes or hides, where a
mapping loses meaning, and whether a transformation can be reviewed and
recovered.

This roadmap records direction, sequencing, and acceptance gates. It is not a
promise of dates, adoption, standards endorsement, or support for a particular
vendor. Substantial CLI, schema, security-boundary, and governance changes use
the public design process in [GOVERNANCE.md](GOVERNANCE.md).

## Product boundary

EdgeLoom will provide an assurance lifecycle around native platform artifacts:

1. **Identify** exact driver, profile, model, and schema bytes.
2. **Validate** bounded machine-readable contracts.
3. **Map** device/protocol behavior, platform exposure, and neutral concepts
   without hiding semantic loss.
4. **Transform** artifacts through previewable patch or translation steps.
5. **Recover** through explicit restore and round-trip evidence.
6. **Review** provenance, checks, limitations, and human disposition.

[RFC 9880](https://datatracker.ietf.org/doc/html/rfc9880) supplies a
protocol-independent Semantic Definition Format (SDF). EdgeLoom does not
replace SDF or native platform formats. It focuses on the evidence required to
use models and drivers safely across real ecosystems.

EdgeLoom is **not** planned as:

- a new universal device-description language;
- an authoritative model or driver registry;
- a certification authority or conformance badge;
- a replacement for native packaging, signing, distribution, or installation;
- a service that executes untrusted upstream driver code; or
- a source of automatically verified AI mappings.

## Status vocabulary

- **Shipped** — available on `main` and covered by the normal CI/release path.
- **Next** — the current implementation gate; work should land before later
  phases depend on it.
- **Planned** — accepted direction whose detailed design still receives public
  review.
- **Exploratory** — a bounded experiment, not a product or compatibility
  commitment.

## Shipped foundation

- One CLI for profile validation, driver patch/restore, Home Assistant to
  SmartThings translation, and driver discovery.
- Versioned profile and capability-map JSON Schemas shipped in the Python
  package.
- Backup-first patching and explicit restoration.
- CI across supported Python versions, package installation checks, static-site
  checks, public security reporting, governance, and contribution processes.
- A reproducible 44-lock binding-resolution study showing that concepts often
  port while encodings do not: 95 one-to-one and 65 lossy bindings among 160
  bound cells. The measured direction is a lexicon plus an index, not another
  format.

## Phase 0 — safety and evidence foundation

**Status: Shipped**

These foundations landed as independent, reviewable changes rather than one
cross-cutting feature branch:

1. Resolved [restore path containment issue #40](https://github.com/edgeloom-oss/edgeloom/issues/40)
   with symlink, traversal, and mutation-style regression tests.
2. Added a bounded local `edgeloom audit` command and versioned evidence-record
   schema. A record identifies exact bytes, deterministic checks,
   operator-supplied source assertions, limitations, and review disposition;
   it is not certification or proof of provenance.
3. Published the standards boundary, including normative RFC 9880 CDDL versus
   informative JSON-Schema checks and the moving status of SDF protocol
   mappings.
4. Kept security fixes, public schemas, research evidence, and website copy in
   focused pull requests with independent test evidence.

**Exit gate (met)**

- Restore containment tests pass on supported Python versions.
- Evidence records are deterministic with respect to artifact and policy
  identity, validate against their shipped schema, and never follow remote
  references implicitly.
- Lint, tests, artifact validation, package build/install, and site checks pass.

## Phase 1 — federated catalog contracts

**Status: Next (contract foundation shipped)**

The first contract slice is shipped in the core `edgeloom` package:

- a source manifest containing repository, full commit, path, SHA-256 digest,
  declared license, source role, and upstream maturity;
- a mapping-set contract that keeps mapping classification separate from
  review status;
- offline structural and single-document semantic validation with bounded
  diagnostics, safe catalog-relative paths, and synthetic contract fixtures.

The next increments are:

- bounded readers for SmartThings `config.yml`, `fingerprints.yml`, and
  profiles, plus SDF JSON models;
- explicit commands to validate, fetch pinned inputs, build deterministic
  indexes/reports, and detect upstream drift;
- local-only reference resolution by default, with network access limited to
  an explicit fetch or drift operation;
- machine-readable and human-readable reports from the same canonical data.

Catalog records must distinguish three layers:

1. behavior implemented by a device or protocol;
2. behavior exposed by a platform driver and profile; and
3. behavior represented by a neutral SDF model.

Mappings use `one-to-one`, `lossy`, `ambiguous`, or `unbound`. An unbound record
also explains whether the device lacks the feature, the platform hides it, the
neutral model lacks it, or the available evidence is insufficient.

**Exit gate**

- Every source is pinned by immutable revision and digest.
- Catalog builds are byte-for-byte reproducible after the explicit fetch step.
- Malformed, oversized, deeply nested, duplicate, path-escaping, or remotely
  referencing inputs have regression tests.
- No imported Lua is executed during inspection or CI.

## Phase 2 — SmartThings lock pilot

**Status: Device browser and external corroboration merged; evidence bundles in draft review**

The separate catalog contains Yale YRD156 and YRD210 device cases, three mapping
sets, six mapping assertions and four corroboration records. These are
founder-authored candidates, not supported-device certifications.
No independent review or physical-device test is recorded.
Sources are referenced at fixed commits with digests rather than redistributed.

### Current construction milestone — Catalog v0.1: usable device evidence

1. Reconcile public status and introduce typed device identities and feature
   associations without changing existing mapping assertions or review state.
2. Add offline cross-record/digest checks, an explicit bounded pinned-source
   fetch, and deterministic JSON/Markdown reports with separate source-byte,
   locator, review, and hardware-evidence states.
3. Generate a small searchable static browser and shareable device pages from
   the same data. Embed a commit-pinned snapshot in the existing project site;
   no new service, login, upstream mirror, or automatic deployment is required.
4. Add Z-Wave manufacturer fingerprints to discovery and a five-minute,
   no-account walkthrough. A source-level gap is not a patch-availability claim.
5. After this vertical slice is accepted, add 3–5 distinct lock models and invite
   targeted external review. Do not fabricate review or hardware evidence to
   satisfy this follow-on gate. AI triage remains a later optional increment.

Acceptance: a reader can understand one case in 30 seconds, reproduce a local
report in approximately five minutes, share a source-linked finding, and report
a mismatch without authoring a mapping. Automated checks must not promote
candidate records or equate profile absence with complete driver/UI absence.

Steps 1–4 are merged into the development tree; they are not included in the
PyPI 0.2.0 package. Step 5 and independent review remain
open; this slice does not satisfy the full pilot exit gate below.

### Merged increment — external corroboration, not borrowed review

Merged into the development tree: a draft candidate-only
corroboration contract, exact manifest joins, scoped identity matches, declared
acyclic source lineage, and side-by-side observations in JSON/Markdown/HTML.
The populated first slice adds HA Z-Wave JS configuration/unknown-state context
to YRD156 and a Yale `YRD210 PB DB` Zigbee battery/lock-exposure case from merged
ZHA and Zigbee2MQTT snapshots. No existing mapping is promoted or rewritten.

Remaining sequence:

1. Validate the next installable package and reconcile its release notes before
   requesting software release approval.
2. Trace the complete downstream ZHA battery entity path and request sanitized
   raw/final-value observations; neither is evidenced by a cluster quirk alone.
3. Add further distinct lock identities only with pinned overlap and explicit
   variant/firmware boundaries. Do not inflate model counts from aliases.
4. Explore Homebridge bridging loss using a bounded overlapping device case.
   A bridge inheriting Zigbee2MQTT facts is not an independent device source;
   its config UI schema is not a device capability description.
5. Invite independent review of a specific candidate finding. Upstream code,
   test fixtures, CI and source counts do not meet this human-review gate.

No bulk ingestion, upstream execution, hardware-validity badge, majority-vote
conflict resolution or AI-generated verification is included. AI-assisted
candidate extraction remains exploratory and must preserve human disposition.

### Current construction milestone — Device Evidence Bundle draft v0.1

The [public design discussion](https://github.com/edgeloom-oss/edgeloom/issues/63)
precedes adoption. Core owns contracts, validation and reporting; the companion
catalog owns versioned records and the contribution workflow.

1. Add document-source, reported-observation and bundle contracts without
   changing existing source/mapping contracts. Accept partial knowledge without
   requiring an SDF mapping or fabricating a completed experiment.
2. Check exact record closure, digest/identity/feature joins and scoped review
   references. Export deterministic bounded ZIPs and independently verify their
   consistency without downloading or executing upstream content.
3. Present explanations by feature with concise summaries, expandable evidence,
   versions/downloads and contribution links for a source, observation,
   correction or review. Integrate these reports into the existing browser.
4. Seed a Yale YRD210 battery bundle with official manual metadata and existing
   pinned code comparisons. Keep manual applicability, upstream byte verification,
   independent review and physical-device observations distinct.
5. Run regression, clean-wheel, deterministic-package, desktop/mobile and link
   checks; submit reviewable core/catalog PRs with exact pins. Software release
   remains a separate approval. A core merge that contains the prepared snapshot
   also needs Pages publication approval because `main` auto-deploys; follow the
   [paired review/publication checklist](docs/bundle-release-readiness.md).

Acceptance: a contributor can inspect one explanation, trace its sources,
download and verify the scoped package, and propose one bounded correction
without writing a driver or SDF mapping. Independent community review and real
hardware observations remain subsequent evidence gates, not CI outcomes.

Create 3–5 manually reviewed records before attempting broad ingestion. The
pilot will connect pinned SmartThings Z-Wave and Zigbee lock artifacts with
relevant experimental OneDM Door, Lock Status, and Lock Code models and with
the existing 44-lock lexicon.

Before expanding population, maintainers must resolve attribution and
redistribution handling for any additional OneDM files and distinguish official
platform evidence, community configuration evidence, manufacturer evidence,
and standards context. A reference-and-hash-only pilot remains the conservative
fallback when redistribution authority is incomplete.

The pilot should deliberately include:

- a candidate one-to-one mapping;
- a range, type, enum, unit, or direction loss;
- behavior supported by a protocol but not exposed by a platform profile;
- a concept supported by the measured lock corpus but missing from the neutral
  model; and
- an unresolved or disputed mapping whose uncertainty remains visible.

Expected outputs are a provenance inventory, coverage matrix, semantic-loss
report, platform-exposure report, SDF gap report, machine-readable index, and a
small searchable static view.

**Exit gate**

- All records cite pinned inputs and carry explicit source/model maturity.
- A contributor other than the record author reviews the evidence or the
  record remains `candidate`/`reviewed`, never `verified`.
- Disagreement and limitations remain in the record instead of being resolved
  by silent normalization.

## Phase 3 — open catalog and community review

**Status: Repository and contribution processes established; external review pending**

The public
[`edgeloom-oss/edgeloom-catalog`](https://github.com/edgeloom-oss/edgeloom-catalog)
repository contains the candidate pilot and its governance, licensing, source
update, correction, submission, and independent-review processes. It has no
independent Pages deployment. Broader population and external review remain
future work. The core repository continues to own schemas, validators,
adapters, and renderers. The catalog repository owns pinned manifests,
original mapping assertions, review records, evidence outputs, and the
generated static catalog.

The catalog will reference upstream projects rather than present a mutable
mirror as authoritative. Contributions will include mapping proposals, source
updates, corrections, independent reviews, and reproducible device reports.

Expansion beyond locks is evidence-driven. Candidate classes include sensors,
switches, and energy devices, but each needs a measured interoperability case
and named reviewer capacity before becoming a milestone.

## Phase 4 — optional AI-assisted triage

**Status: Exploratory**

AI may rank candidate mappings, retrieve similar reviewed records, or summarize
drift only after the lock pilot provides a human-reviewed evaluation set.

Every AI suggestion must retain pinned input citations, model/provider/version,
prompt or policy version, uncertainty, deterministic validation results, and a
human disposition. AI output is never accepted evidence and cannot promote a
record to `verified`.

Evaluation will measure candidate precision/recall, citation correctness,
false-positive rate, reviewer time, and agreement with independent reviewers.
The catalog remains usable without an AI provider or network credential.

## Continuing product work

The catalog does not replace the existing product path. In parallel, EdgeLoom
will continue to:

- expand tested subdrivers and handler templates;
- broaden capability coverage beyond the current device classes;
- improve Windows-native validation and patching;
- collect reproducible reports from real hardware;
- harden patch, translation, discovery, credential, and filesystem boundaries;
  and
- improve installation, examples, documentation, and contributor onboarding.

## How priorities change

A roadmap item advances when its prerequisites and review capacity exist, not
because a date arrived. Maintainers may narrow or stop a phase when evidence
shows that mappings are mostly unsupported judgment, source licensing is
unclear, reproducibility fails, maintenance cost exceeds demonstrated value, or
security requires a different boundary.

Propose a substantial change through the
[design-proposal issue template](https://github.com/edgeloom-oss/edgeloom/issues/new?template=design_proposal.yml).
Small corrections and reproducible findings can use a focused issue or pull
request.
