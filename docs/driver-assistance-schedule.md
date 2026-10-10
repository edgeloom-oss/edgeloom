# Driver assistance construction schedule

Planning baseline: 10 October 2026. This schedule covers the first
**Find → Customize → Contribute** workflow, not arbitrary driver generation.
The [architecture](driver-assistance-architecture.md) defines the contracts and
trust boundaries; the [catalog plan](https://github.com/edgeloom-oss/edgeloom-catalog/blob/main/docs/driver-assistance-implementation.md)
defines the canonical records. The new workflow is not implemented yet.

## First usable outcome

A person describes a desired feature or supplies a public source URL. EdgeLoom
finds relevant evidence, explains applicability and missing information, and
prepares a local development pack. For one supported SmartThings Zigbee change,
the pack leads to actual candidate code and checks. Useful explanations and
recipes can then be proposed back to the catalog with credit.

The first increment needs no hosted AI, account, physical device or new backend.
An optional coding agent consumes the same bounded task as a human developer.
The output is a candidate source tree, not an installed or certified driver.

## Integrated starting point

Core [PR 64](https://github.com/edgeloom-oss/edgeloom/pull/64) and
[PR 65](https://github.com/edgeloom-oss/edgeloom/pull/65), and catalog
[PR 6](https://github.com/edgeloom-oss/edgeloom-catalog/pull/6), are merged.
The development baseline contains bundle tooling, additive media contracts and
two candidate bundles: Yale YRD210 battery evidence and LG webOS family state
evidence. It does not establish exact LG G2 compatibility or hardware behavior.

- Core integration revision: `5bd3c8a2d209799d183f7b95ad0653f169dd7e7b`.
- Catalog data revision: `f246a43a37c7f9df74de661f7eb7ef16ba01d00d`.
- Catalog generator pin: `d7e801d10f02b6effe4d8403ec997913bfd7bb2c`, preserved in
  core main's history. Documentation-only follow-ups need not change this pin.
- Existing checks at integration: 512 core tests, 23 typed catalog documents,
  repeatable catalog builds and offline verification of both bundle exports.
- These development capabilities are not a new PyPI release. Candidate status,
  independent review, software publication and hardware observations stay separate.

## Schedule and dependencies

The week labels start when focused implementation begins. If work begins on
12 October, Week 1 is 12–16 October and Week 6 is 16–20 November. This is an
initial six-week planning envelope, not a delivery promise. Estimates below are
engineering effort; review queues and device availability can extend elapsed time.
Re-estimate at each gate instead of accepting incomplete work to meet a date.

| Stage | Indicative window | Effort estimate | Deliverable and exit gate |
| --- | --- | --- | --- |
| P0 Design freeze | Week 1 | 1–2 days, plus public review | Focused design proposal; choose one Zigbee behavior/base; resolve fields, rights and matching reason codes |
| P1 Contracts and seeds | Weeks 1–2 | 4–6 days | Core validators and synthetic fixtures; two catalog recipes; unchanged legacy contracts and strict reference checks |
| P2 Find and prepare | Week 3 | 4–6 days | Explainable offline matching and deterministic workpack export; a useful no-AI task reproduced from pinned inputs |
| P3 One candidate generator | Weeks 4–5 | 4–6 days | Actual code/diff and scoped tests; wrong bases and unexpected outputs fail safely |
| P4 Community workflow | Weeks 4–5, parallel with P3 where staffed | 3–5 days | Static search/task download, one-link contribution draft, credit and newcomer walkthrough |
| P5 Integration and pilot gate | Week 6 or later | 2–4 days, excluding physical testing | Clean-install and paired snapshot checks; decision on a scoped device pilot and separately approved release |

Total planning estimate: **18–29 engineering days**. Parallel tasks need distinct
available capacity; assigning several lanes to one executor does not shorten
the total effort. Physical testing has no promised completion date yet.

```text
P0 scope and interfaces
          ↓
P1 core contracts ──→ catalog recipe seeds and source review
          └──────────────────────┬────────────────────────┘
                         P2 find/workpack interface
                           ┌────┴────┐
                      P3 code    P4 UI/contribution
                           └────┬────┘
                       P5 paired acceptance
```

Draft source research and UI sketches can begin earlier. Canonical recipes must
not merge against an unsupported core pin, and UI downloads must not advertise
a workpack format that the released or explicitly pinned tool cannot read.

## Ordered implementation queue

### 1. Freeze the smallest useful contract

Open a public design proposal under [GOVERNANCE.md](../GOVERNANCE.md), with one
positive and one unsupported example. Follow the normal discussion window;
the early-merge authorization for the preceding integration does not waive
future review requirements.

Specify `driver-request`, `implementation-recipe` and the minimum workpack
manifest together, but implement only what the first vertical example needs.
Keep the original request beside normalized fields, preserve unknown firmware,
and separate source excerpts from instructions. Choose one bounded Zigbee change
after inspecting existing patch templates and a pinned native driver base.
If no rights-cleared, supported change fits, narrow the example before coding.

Core PR: versioned schemas, reference resolution and synthetic tests under the
proposed `edgeloom/assistance/` package, without changing existing CLI behavior.
Catalog PR: two recipes after the core contract is reachable—one supported
customization candidate and one `reference-only` extension. Catalog supplies
data and approved template IDs, never executable hooks.

Gate: reject stale hashes, incompatible scope, unsupported versions, missing
rights information and arbitrary commands. Tests do not confer independent
review or physical validation.

### 2. Make finding and task preparation useful without AI

Core PRs: deterministic matching first, then workpack export using the frozen
match/result interface. Distinguish existing source references, customization
candidates, related research and evidence gaps. Include reason codes and unmet
prerequisites; a search miss does not mean a device lacks a feature.

Lock the request, recipe, source closure, driver base, tool/template versions,
allowed changes and tests. Export a concise human brief and machine manifest.
Keep candidate outputs outside frozen inputs. A URL-only submission becomes a
local draft with unknowns, not a canonical record or silent download.

Catalog PR: refine feature terms, binding explanations, prerequisites and credit.
Use existing Yale evidence for explanation/search; do not advertise a ready-made
battery fix without an implementation.

Gate: repeated exports agree; offline verification works; wrong protocol,
uncertain firmware, other-platform references and conflicting evidence remain
visible. The task is understandable without an AI subscription.

### 3. Produce one real, reviewable candidate change

Core PR: connect one reviewed generator/template to a synthetic fixture and a
rights-reviewed pinned base. Use a fresh output tree, produce candidate code and
diff, and bind the result manifest to input/output hashes. A prompt, TODO scaffold
or copied upstream URL is not a generated driver.

Structural checking never executes upstream code. Executable tests require a
separate explicit local action in isolation, without network, secrets or device
access. Label static checks and simulated behavior separately.

Catalog follow-up: record the reusable rationale, test specification and scoped
result references. A recipe/base change invalidates the old review for changed
bytes. One recipe applies to one base in the MVP; composition waits.

Gate: preserve the original tree; reject a wrong base, unsupported parameters,
path escapes and out-of-scope files. Recovery claims cover local artifacts only.

### 4. Build the low-friction community path

This lane can run beside P3 after P2 is stable. Core owns static UI and matching
parity tests. Catalog owns short request/source forms, explanations, credit and
review prompts. A contributor can start with a URL and two sentences;
maintainers enrich the draft before canonical acceptance.

Show download contents, evidence limits and the next action. Source URLs are
not installation channels. Public sharing requires explicit review; exclude
household names, serial numbers, credentials and raw telemetry. Browsing or
downloading a workpack requires no account.

Gate: keyboard/mobile walkthroughs pass, CLI/browser golden cases agree, and a
newcomer completes a download or source draft without writing the schema.
Update case-study/demo drafts after this gate; posting and contacting contributors
still require separate approval.

### 5. Reconcile release and hardware gates

Generalize catalog CI from a Yale-specific export to all supported bundles.
Run regression tests, installed-wheel checks, deterministic exports, offline
verification, negative fixtures and website checks against an exact core/catalog
pair. Generate snapshots reproducibly; never edit generated pages by hand.

Before a physical pilot, ask for exact model/firmware and confirm an available
SmartThings hub/setup. HA observations do not establish SmartThings behavior.
Start with a low-risk sensor or read-only state case. Media/IP observations need
a supported contract; do not encode a TV result as a Zigbee observation.

Gate: the demonstrated user task is complete and its limits are intelligible.
Version/tag, GitHub Release, PyPI, Pages snapshot and outreach follow their
applicable approval paths. A hardware delay can leave a bounded source/static-check
workflow ready; it cannot be hidden as validation.

## Working rules and progress records

Use small PRs per repository and dependency, with exact tested heads and a gate
checklist. Preserve accepted pins through merge history; re-pin deliberately
when behavior or schema support changes. Inspect active branches before creating
or restacking work, and never overwrite user changes.

Parallel lanes are core contracts/tests, catalog source curation, and later the
static community UI. Assign non-overlapping files and one integration owner
before parallel editing. Core is the sole owner of shared contracts.

After each gate, record exact revisions, tests, changed assumptions, unresolved
evidence gaps, next dependency and updated effort. Keep RKA aligned with PRs.
Measure useful task completion and reusable contributions, not URL counts or
AI output volume as adoption.

The immediate next engineering action is **P0: a focused design proposal and one
supported Zigbee customization example**. LAN scanning, device modifications,
automatic rooting, hosted AI and mass source ingestion are outside this schedule.
