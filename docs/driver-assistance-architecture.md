# Community driver assistance architecture and development plan

Status: design draft; integration baseline updated 10 October 2026. The PI approved a
SmartThings Edge-first workflow and the two-repository boundary. The new
contracts, modules, commands and milestones below are proposed, not implemented.

EdgeLoom should help a user find an existing implementation, explain what is
missing, and prepare or customize a candidate driver. A developer should be able
to start with a short explanation or source URL. Useful results return to the
catalog as reusable artifacts with provenance, applicability and credit.

The first usable workflow is **Find → Customize → Contribute**. AI coding is
optional. Finding evidence, checking records and preparing a development task
must work without an AI account. Native platform packaging and installation
remain separate from producing a candidate source tree.

## Current baseline and integration prerequisites

The following accepted development states anchor this plan. The
[construction schedule](driver-assistance-schedule.md) gives the ordered PR
queue, effort estimates, parallel lanes and acceptance gates.

| Repository state | Revision | Meaning for development |
| --- | --- | --- |
| Core bundle integration | `cd6f5cb3af7538fa08f23974ac67dc6f9aa83434` | PR 64 merged; bundle tooling and Yale snapshot |
| Core media integration | `5bd3c8a2d209799d183f7b95ad0653f169dd7e7b` | PR 65 merged; additive draft v0.2 contracts and family-scoped reports |
| Catalog media integration | `f246a43a37c7f9df74de661f7eb7ef16ba01d00d` | PR 6 merged; Yale and LG family candidate bundles |
| Catalog generator pin | `d7e801d10f02b6effe4d8403ec997913bfd7bb2c` | Preserved ancestor of core main, not a packaged release |

Recheck remote heads before implementation. The accepted dependency chain is
reachable; the proposed assistance contracts and commands remain unimplemented.
Documentation-only follow-ups do not by themselves require changing the
catalog's deliberately selected `CORE_REVISION`.

Existing components provide a starting point, not arbitrary driver generation:

- `discover` enumerates driver artifacts and selected Zigbee/Z-Wave fingerprints.
- `patch` uses a bounded set of SmartThings Zigbee handlers and templates;
  Z-Wave discovery does not imply Z-Wave patch support.
- `translate` produces a limited HA-to-SmartThings proxy scaffold. It is not a
  general native-driver porting engine; the existing Lua proxy has stubbed code.
- `catalog` and `bundle` provide source references, deterministic checks,
  reports and portable evidence packages at their respective development pins.
- Media device/bundle v0.2 does not add IP/Matter observation or mapping schemas.
  A future television test cannot be encoded as a legacy Zigbee observation.

Relevant code: [catalog.py](../edgeloom/catalog.py),
[bundles.py](../edgeloom/bundles.py), [schemas.py](../edgeloom/schemas.py),
[cli.py](../edgeloom/cli.py), [patching](patching.md),
[media contracts](media-device-contracts.md).

## Repository responsibilities

| Responsibility | EdgeLoom core | edgeloom-catalog |
| --- | --- | --- |
| Contracts | Versioned schemas, reference rules, migrations and compatibility tests | Records conforming to a selected contract version |
| Device knowledge | Parsers and resolution logic | Device identities, manuals, code references, feature explanations and conflicts |
| Reuse | Interpreter, reviewed generators and generic templates | Declarative implementation recipes, scoped bindings and template references |
| Customization | Request normalization, matching, task export and candidate checking | Evidence and recipes consumed by those operations |
| Validation | Deterministic checks, test harness and report generation | Test specifications, sanitized observations and scoped reviews |
| Presentation | Static renderer and browser behavior | Titles, explanations, contribution prompts and attribution |
| Release | Python package, schema/runtime versions, website generator | Versioned data snapshots and evidence bundle contents |

Do not duplicate schemas, generators or validators in the catalog. Do not embed
the production catalog as hard-coded cases in the Python package. Core tests use
small, clearly synthetic fixtures; paired integration tests use a pinned catalog.

**Canonical** means the project's maintained, versioned reference collection.
It does not mean a universal device registry, vendor approval or hardware
validation. An accepted catalog record may remain explicitly `candidate`.

## User and contributor workflow

```text
Desired behavior or a source URL
              ↓
Local draft request and explicit unknowns
              ↓
Pinned catalog search and applicability checks
        ┌─────────────┼────────────────┐
 Existing source   Scoped recipe    Missing evidence or binding
        │             │                │
 Explain/refer    Development pack   Research/contribution task
                      ↓
             Human or optional coding agent
                      ↓
              Candidate code and tests
                      ↓
       Core checks and scoped human review
                      ↓
          Catalog contribution or correction
```

The front door asks what the person wants to accomplish. Device/model, platform,
protocol and URLs are optional at intake and requested progressively when needed.
An unknown model should not prevent submitting a useful source; it can prevent
claiming applicability or generating a model-specific patch.

Search distinguishes:

- **Existing implementation reference:** source code describes the feature.
  Show a native installation/channel link only if it has separately been recorded;
  a GitHub source link does not establish an installable distribution.
- **Customization candidate:** a recipe is relevant and its stated preconditions
  can be checked. Show missing prerequisites before proposing changes.
- **Related research:** a family, another platform or an incomplete binding is
  useful context, but not an exact compatible driver.
- **No evidenced match:** show what was searched and how to contribute. Do not
  translate a search miss into a claim that the device lacks the feature.

Description/URL intake stays local or in a manually submitted issue until reviewed.
No website form silently creates public issues or uploads household information.
GitHub issues remain the contribution discussion channel; they are not automatically
canonical records.

## Data model and reusable artifacts

Reuse the existing source, document, device, mapping, corroboration, observation,
review and bundle records. Add three small contracts incrementally, rather than
another general-purpose knowledge graph or a universal device description language.

### Driver request

`driver-request` is a local work object. Required: contract version, local ID and
desired behavior. Optional: known device identity, platform, protocol, firmware,
current driver reference, feature selection, sources and user constraints.

Keep the user's words separate from normalized fields and machine suggestions.
For example, an extracted capability name is a proposed interpretation until
confirmed. Credentials, private addresses, serial numbers and household entity
names are not canonical request fields. Public sharing requires a redaction review.

### Implementation recipe

`implementation-recipe` is the new canonical reusable unit. One recipe explains
one bounded behavior or modification; several recipes can reference the same
device or be assembled into a bundle. Proposed fields:

| Group | Contents |
| --- | --- |
| Identity | Stable recipe ID, content version, title, author and credit |
| Applicability | Target platform/protocol, exact-model or family scope, firmware bounds or unknown, required base artifact revisions |
| Behavior | Baseline behavior, requested capability delta, inputs/outputs, units, ranges, sentinel/unknown handling and known semantic loss |
| Binding | Device attribute/command/API → handler or transform → SmartThings capability/profile; each edge cites evidence |
| Prerequisites | Device-side setup, service dependencies, SDK/capability namespace requirements and permissions by execution location |
| Evidence | Existing record references with exact hashes and locators; supporting and conflicting evidence retained |
| Generation | `reference-only` or a reviewed core generator/template ID and validated parameters; never an arbitrary shell hook |
| Checks | Preconditions, expected file changes, expected capability delta, test cases, postconditions and recovery limits |
| Rights and status | License/attribution basis, candidate/review state, limitations and exact-hash review references |

A recipe can be useful without being executable. A source-only webOS extension
has `reference-only` generation until a supported SmartThings binding, necessary
prerequisites and a reviewed generator exist. Do not fill an unknown API, payload
or permission with a plausible-looking AI guess.

Generic generator code and executable templates belong in core and receive code
review. Catalog recipes supply data and select approved generators. Upstream
drivers stay upstream by default. If later work needs catalog-hosted patches or
snippets, admit only rights-cleared bytes with a locked inventory and review;
never allow catalog content to become automatically executed plugin code.

### Development workpack

`driver-workpack` is a portable, local development task, not another canonical
evidence bundle. Its manifest locks:

- The normalized request, chosen recipe/version and relevant evidence closure.
- Catalog revision, core/generator/template/schema digests and policy version.
- Upstream or local driver base revision plus exact input file hashes.
- The allowed modification scope, expected outputs, unresolved questions and tests.
- Attribution and source-sharing restrictions.

Its human-readable brief explains the desired change and the cited rationale.
Machine-readable material enables later checking. Output may include a candidate
patch/source tree and a result descriptor identifying those exact bytes. The
candidate remains separate from the frozen inputs; new outputs get new digests.

Do not duplicate the bundle ZIP format blindly. Share bounded path, hashing and
archive utilities, but retain different meanings: a bundle publishes evidence;
a workpack commissions a change. Builds are deterministic for fixed inputs.
AI generation is not promised to be deterministic. Frozen accepted candidate
bytes can still be checked and repackaged reproducibly.

### Standards and platform boundaries

SDF references remain optional semantic anchors, not a prerequisite for every
contribution and not a complete code-generation specification. RFC 9880 separates
abstract affordances from protocol bindings and does not define a specific base
augmentation mechanism. EdgeLoom therefore needs explicit, evidenced protocol
and platform bindings alongside any SDF link. This is a design implication, not
a claim that SDF is defective. See [RFC 9880](https://www.rfc-editor.org/rfc/rfc9880.html).

SmartThings outputs must respect native package components: configuration, Lua
code, profiles, applicable fingerprints and optional LAN search parameters.
Do not force Zigbee fingerprint assumptions onto LAN recipes. See
[SmartThings driver structure](https://developer.smartthings.com/docs/devices/hub-connected/driver-components-and-structure).

## Core module structure

Keep the existing public CLI behavior compatible. Add a focused package rather
than appending all new behavior to `catalog.py` or `bundles.py`:

```text
edgeloom/
  assistance/
    requests.py           # normalize drafts without inventing unknown fields
    matching.py           # deterministic candidates with reason codes
    recipes.py            # resolution, preconditions, bindings and parameters
    workpacks.py          # locked inputs, brief and result-manifest handling
    proposals.py          # candidate inventory, scope and base-hash checks
    adapters/
      smartthings.py      # approved generation and native artifact checks
  catalog.py              # existing catalog entry points and index building
  bundles.py              # existing evidence bundle entry points
  schemas.py              # trusted schema/version dispatch
  catalog_assets/         # static browser UI
schema/                   # authoritative contracts
tests/                    # synthetic fixtures and regression cases
```

These names are proposed. Extract common record resolution only when a second
consumer requires it; avoid a broad refactor before the first vertical slice.
The current bundle folder allowlist and catalog script need explicit additions
for recipes. Simply adding a JSON file will not make it resolvable or packageable.

Candidate CLI surface, also proposed:

```text
edgeloom assist init
edgeloom assist find REQUEST --catalog CATALOG_ROOT
edgeloom assist prepare REQUEST --recipe RECIPE_ID --catalog CATALOG_ROOT --output DIR
edgeloom assist check WORKPACK --candidate CANDIDATE_DIR
edgeloom assist contribute WORKPACK --candidate CANDIDATE_DIR --output DRAFT_DIR
```

`contribute` prepares local files and a PR description; it does not push or open
a PR. The first version need not implement all five commands. Start with request
loading, `find` and `prepare`; introduce candidate checking when candidate output
is delivered. Keep source acquisition explicit and separate from offline commands.

## Matching and customization policy

Use ordinary structured filtering and text search first. A small catalog does
not need a vector database or a hosted retrieval service. Preserve requested
behavior in natural language, but require explicit feature/platform selection
where ambiguous wording would change a generated implementation.

Matching should report identity strength, feature evidence, platform suitability,
version/prerequisite gaps and the next available action separately. Exact
fingerprint matching is not proof of feature behavior. Family or other-platform
sources appear as related evidence, not verified alternatives. Hard protocol,
model or firmware contradictions exclude automatic customization even when text
similarity is high. Do not collapse these dimensions into a compatibility score.

Feature identifiers retain their namespace and version. Similar labels such as
availability, power and screen state are not interchangeable. Aliases improve
discovery but cannot establish a semantic mapping. The first customization pack
selects one recipe and one driver base; automatic multi-recipe composition waits
for conflict, dependency and combined-test rules.

Initially, only known generators may produce candidate code. Generate in a fresh
workspace from a pinned base; do not modify the user's active driver tree. Refuse
base-hash mismatch, unapproved paths, unsafe parameters, unknown capability
namespaces and unrecognized template IDs. Candidate checking must compare actual
files against the manifest, not trust AI-reported test success or allowed changes.

Trusted generators come from the installed, selected core runtime, not from a
workpack's declaration of its own trust. A digest proves byte consistency, not
publisher identity. Display the catalog origin and acceptance provenance; an
external catalog or modified workpack cannot self-assign official review status.

Tests may run only through a separate explicit local execution step in an isolated
workspace with no device credentials and network disabled. Offline `check`,
`build` and `verify` continue to parse data without executing upstream drivers,
test hooks or arbitrary catalog commands. Existing `patch`/`restore` can support
bounded local artifact workflows; restoration does not undo device configuration,
firmware, calibration, remote writes or hardware side effects.

## Optional AI coding handoff

The MVP exports a provider-neutral brief and pinned local inputs. A human or the
user's chosen coding agent can return a candidate. EdgeLoom does not initially
need to host an agent, acquire an API key, run a model or manage an agent session.

Keep authored instructions separate from quoted source material. A reverse-
engineering page can supply a claim or code reference; instructions embedded in
that page cannot change task scope, execute code, access secrets or promote data.
Upstream skills are references, not automatically installed or trusted programs.

The official [SmartThings Developer AI Skills](https://github.com/SmartThingsCommunity/wwst-skills)
already offer integration/code-generation guidance, including hub-connected
development. Evaluate and pin relevant guidance instead of copying a generic
SmartThings coding tutorial. EdgeLoom's added value is the device-specific
evidence, exact task inputs, applicability checks and result review. Upstream
guidance does not establish an endorsement or integration that EdgeLoom already has.

Record AI assistance and human review, and record model/tool identity when known.
Do not require publishing full conversations, private prompts or credentials.
Sending source contents to an external agent must respect user choice and rights.
Reference-only documents stay references unless reuse and sharing are permitted.

## Catalog structure and publication states

Preserve existing directories and add `catalog/recipes/`. Link recipes into
device feature navigation and versioned bundles through an explicitly versioned
contract change. A recipe can reference a family context without turning the
subject into an exact-model qualification. Do not duplicate feature explanations
in a new independent registry.

Use local `requests/`, `workpacks/` and `candidates/` directories for work in
progress; these are ignored working directories, not automatically committed
catalog data. Public issue submissions may remain lightweight. Maintainer-assisted
normalization adds source hashes, rights, applicability and credit before a PR.

Display independent axes: provenance/reuse rights, record review state, source
applicability, candidate build/static checks, simulation, and physical observation.
Missing, failed and inconclusive checks remain visible. One reporter's hardware
test does not automatically become independent review or support for all firmware.

Old versions remain addressable by exact catalog commit and record digest. A
changed recipe/base/source invalidates reuse of the corresponding old review
for new bytes. Scheduled drift detection can later prepare impact reports; it
must not rewrite accepted records or silently carry tests/reviews forward.

## Website design

Retain a buildless, responsive static catalog. Add three clear actions: Find an
implementation, Prepare a customization, and Contribute a source/result. Explain
prerequisites and the proposed change before offering a development-pack download.

Core generates the index and schema-versioned metadata. Browser matching uses
the same published rules and golden cases as CLI matching; test parity to avoid
contradictory recommendations. Python and agent execution remain local. The
website does not contain API keys, fetch arbitrary URLs, control devices or imply
that clicking a button installs a driver. Allow downloads without a GitHub account;
an issue submission can use GitHub separately with a public-sharing preview.

Do not add a backend, accounts, marketplace, vector store or second Pages site
for the MVP. Generated website files are views, never another editable canonical
catalog. Core's existing main-triggered Pages workflow means a later core merge
can be a publication event; review its generated snapshot accordingly.

## Development sequence and acceptance gates

| Slice | Core deliverable | Catalog deliverable | Exit criterion |
| --- | --- | --- | --- |
| P0 Baseline and design | Merged dependency baseline; focused design proposal; version matrix | Matching baseline/pin and provenance audit | Reachable pair is established; freeze the new contract and first bounded customization case before implementation |
| P1 Contracts and vertical fixture | Request and recipe validators, resolution, negative fixtures; workpack contract only as needed by P2 | Two small candidate recipes, one source-only and one bounded SmartThings customization case | Legacy records unchanged; exact joins, rights/status, unknowns and forbidden hooks tested |
| P2 Find and prepare | Explainable matching and deterministic workpack/brief export | Feature aliases, prerequisites and precise references for selected recipes | A request resolves to an existing reference, a customization task or an explicit research gap; no AI service required |
| P3 Candidate implementation | One approved Zigbee generation path or template, candidate inventory checks and isolated tests | Reusable binding, test specification and result-linked bundle updates | One pinned example yields actual reviewable code/diff and check output; wrong base and out-of-scope output fail; no hardware claim |
| P4 Community flow | Static UI, CLI/browser parity, contributor draft export | Short request/source forms, walkthrough, role-specific credit and review checklist | A newcomer completes a source contribution or development-pack download without hand-writing the full schema |
| P5 Real-device and release readiness | Scoped observation support where needed; paired build and clean-install checks | Sanitized physical observations if available; accepted versioned snapshot | Source/static/simulation/hardware states remain distinct; publication and device-operation approvals stay explicit |

Use focused PRs per slice and repository, not one large cross-repository change.
P1 can begin with synthetic core fixtures; real catalog curation can proceed
against the frozen draft contract. P2 consumes that contract. P3 and P4 can
progress in parallel after P2 output is fixed. P5 depends on their integration.
Higher-privilege webOS references can be curated alongside P1/P2 without blocking
the first Zigbee workflow or being presented as generated SmartThings drivers.

Suggested implementation branches are `codex/driver-assistance-contracts`,
`codex/driver-assistance-find`, and `codex/driver-assistance-candidates` in core,
with paired `codex/reusable-driver-recipes` and contributor-flow branches in
catalog. These branches have not been created by this plan. Rebase or restack
only after inspecting current remote bases; never overwrite the media work.

## Initial examples and validation matrix

1. **Yale battery explanation:** reuse existing evidence for search, units and
   gaps. Do not infer a ready-made battery fix or firmware qualification.
2. **Bounded SmartThings Zigbee customization:** use a clearly synthetic fixture
   plus a pinned, rights-reviewed native source for candidate generation. Select
   an exact real device separately; existing fixture success is not hardware support.
3. **webOS extension references:** curate bscpylgtv, Homebrew Channel and
   PicCap/hyperion-webos as source-only extension recipes after source/license
   checks. Distinguish ordinary API access, developer mode, privileged TV services
   and root prerequisites. No automatic rooting or TV changes.
4. **One-link contribution:** a public source URL becomes a draft with credit,
   locators and unresolved applicability, then a reviewed catalog PR proposal.

Required regression groups:

- Schema/version dispatch, dependency closure, identifier collisions, stale hashes,
  family/exact-model mismatches, firmware contradictions and unresolved bindings.
- Matching positives and counterexamples: same marketing name/different protocol,
  other-platform reference, missing firmware, no results and conflicting sources.
- Generation: parameter limits, namespace gaps, wrong input base, no writes to the
  original tree, unexpected files, safe failures and input/output digest binding.
- Reproducibility: repeat exports, offline verification, installed-wheel contents,
  legacy bundle retention and a clear failure for unsupported contract versions.
- Security: traversal/symlinks/archive limits, untrusted HTML and prompt text,
  absent secrets, no network/code execution during deterministic checks.
- Experience: CLI help, clear unknown/error states, keyboard and mobile flows,
  accessible status labels, links and CLI/browser golden-case agreement.

The MVP accepts public URLs as references, not an arbitrary web crawler. Git
retrieval reuses the explicit bounded pinned-source mechanism. General page
acquisition, if later approved, needs its own SSRF/redirect/private-address policy,
content/size/time bounds, non-executing parser, rights review and cache separation.

Core CI runs unit/regression tests and installed-package checks; catalog CI pins
core and checks every record and bundle, including repeated deterministic builds.
Update today's Yale-specific export checks to enumerate supported bundles. PR
validation must have no deployment credentials, no device access and no automatic
execution of submitted recipe code. Exact-pin integration is the MVP guarantee;
broader version compatibility requires an explicit tested matrix.

## Hardware needs and release boundaries

P0 through P4 do not require a physical device. Before P5, choose one low-risk
sensor or read-only state case and obtain exact public model, firmware, platform
and driver versions. The PI has described Home Assistant equipment; availability
of a SmartThings hub has not been established. HA observations can support a
source-side claim, not substitute for SmartThings runtime validation.

Privileged TV modifications are not the first hardware pilot. Where a recipe
requires an external service or device configuration, the workpack describes
the prerequisite and recovery uncertainty without performing it. No LAN scan,
pairing, firmware change or physical actuation is authorized by this design.

Release order: validate core and catalog candidate pins together; obtain required
design/code review; make the chosen core revision reachable through the approved
integration path; re-pin and validate catalog; then explicitly approve the public
website snapshot and any software/data release. Neither this plan nor passing CI
authorizes merge, deployment, release, public outreach or contacting contributors.

Success is a completed, reproducible user task and a reusable contribution—not
the count of URLs, generated drivers or AI calls. Capture task completion,
unresolved assumptions, reviewer corrections and reuse across a second request
in an opt-in evaluation; no background household telemetry is needed.
