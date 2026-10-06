# External evidence without borrowed authority

This development increment is not in PyPI 0.2.0. Use the catalog's exact core
pin and [local walkthrough](catalog-quickstart.md). Sources are references and
hashes, not vendored upstream code. The original mapping contracts and review
lifecycle are unchanged; the new sidecar is deliberately candidate-only.

## Contribute one bounded comparison

1. Select an exact protocol identity. Treat nearby names, hardware variants and
   firmware as separate or unresolved until source evidence establishes a join.
2. Pin each upstream's full commit, selected paths, SHA-256 and license evidence.
   Prefer merged source, not an unmerged PR presented as shipped behavior.
3. Inspect only relevant declarations and their helper definitions. Do not run
   an upstream Python quirk, JavaScript converter or arbitrary driver to extract
   metadata. Dynamic factories and runtime results remain unresolved.
4. Write a `catalog-corroboration` record for one device feature. Cite exact
   artifacts/locators, explicit conditions and `identity_match` fields. A Z2M
   `zigbeeModel` entry does not assert a manufacturer filter merely because
   its descriptive vendor field says Yale. A ZHA signature also needs endpoint
   and cluster matching. Generic HA code is not a model-specific observation.
5. Record source lineage. HA's Z-Wave JS path and Z-Wave JS configuration share
   stack ancestry; a Homebridge Z2M bridge inherits Z2M facts. An empty dependency
   list means none declared *within that record*, not proven independence.
6. Preserve disagreements and distinguish code declarations from simulated
   test fixtures. `conflicts` is a curator interpretation; no majority rule
   silently removes it. This contract does not ingest hardware reports or
   confer credit for an independent EdgeLoom review.
7. Join the record to its matching `catalog-device` feature and run offline
   `catalog check`, explicit optional `fetch`, then two deterministic builds.
   Review the generated source links, conditions and device page on mobile.

## The first comparisons

- **YRD156 / auto-relock:** HA's generic `set_config_parameter` entry point
  provides context for a community parameter declaration. Door Lock CC
  `auto_relock_time` is a different interface, not an established equivalent.
- **YRD156 / unknown state:** the HA entity returns an unknown result for a
  missing value. A Schlage simulation fixture is identified as such; it does
  not validate a Yale unit or resolve the SmartThings migration condition.
- **Yale / YRD210 PB DB / battery:** ZHA doubles the raw cluster attribute;
  Z2M skips default halving for this model. Different adaptation layers are not
  contradictory final percentages. The downstream ZHA entity path and real
  raw/final values still need examination.
- **YRD210 / lock state:** ZHA cluster presence and Z2M's command/actual-state
  exposes are different scopes. No new SDF mapping or UI equivalence is claimed.

## What remains a separate gate

Independent review requires a human other than the record author to assess a
specific EdgeLoom claim through the governed process. Repo existence, CI,
upstream code review and multiple source families do not satisfy it. Hardware
claims require traceable, privacy-safe real-unit evidence. No lock settings,
credential operations or repairs should be recommended from source-only data.

Homebridge extraction, additional models, drift alerts and AI-assisted triage
are later increments. AI could suggest source candidates and flag potential
conflicts, but must cite pinned evidence, abstain on unresolved identity and
leave every semantic/lifecycle decision to a human. No AI service is added here.
