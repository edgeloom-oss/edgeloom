# Catalog Contracts

EdgeLoom's catalog contracts describe evidence-backed relationships among
device behavior, native edge-driver artifacts, and protocol-independent SDF
models. They are assurance records, not an authoritative device registry,
driver store, certification, or claim of standards adoption.

Version 0.1 publishes two JSON Schema Draft 2020-12 contracts:

- [`source-manifest.schema.json`](../schema/source-manifest.schema.json) pins one
  upstream Git repository to a full 40-character commit ID. Every artifact has
  a repository-relative path, SHA-256 digest, media type, license evidence, and
  upstream source maturity.
- [`catalog-mapping-set.schema.json`](../schema/catalog-mapping-set.schema.json)
  records the evidence nodes and mappings built from those pinned artifacts.
  It keeps EdgeLoom's review lifecycle separate from upstream source maturity.

The synthetic lock records in [`tests/fixtures/catalog/`](../tests/fixtures/catalog/)
exercise both contracts without creating a real catalog entry.

## Three evidence layers

A mapping set must represent all three layers explicitly:

1. `device-protocol-support`: what the pinned device or protocol artifact says
   the device can do.
2. `platform-exposure`: what the pinned native driver/profile exposes.
3. `neutral-sdf-representation`: what the pinned SDF artifact can represent.

Keeping these layers separate prevents an unexposed platform feature from
being mistaken for an absent device feature or a missing neutral model.

Mappings are classified as `one-to-one`, `lossy`, `ambiguous`, or `unbound`.
A lossy mapping must name at least one loss dimension. An unbound mapping has no
target and must distinguish among `device-feature-absent`,
`platform-not-exposed`, `neutral-model-missing`, `insufficient-evidence`, and
`out-of-scope`. Every mapping cites evidence and carries an explicit limitations
list, which may be empty only when there are no known qualifications.

## Status is two-dimensional

`source_maturity` describes upstream material:

- `official`
- `community`
- `experimental`
- `draft`
- `deprecated`

`review.lifecycle` describes EdgeLoom's treatment of a mapping:

- `candidate`
- `reviewed`
- `verified`
- `deprecated`

An experimental SDF model therefore remains experimental even when an
EdgeLoom mapping has been reviewed. Likewise, an official upstream artifact
does not make an EdgeLoom mapping verified.

## Validate locally

```bash
edgeloom validate tests/fixtures/catalog -v
edgeloom validate --kind source-manifest path/to/source.yaml
edgeloom validate --kind catalog-mapping-set path/to/mappings.yaml
```

`edgeloom validate` checks the JSON Schema, duplicate stable IDs, required
three-layer coverage, and references among manifests, nodes, evidence, and
mappings declared inside one mapping-set document.

This first contract slice deliberately does **not** fetch remote content,
recalculate a source digest, or resolve an `artifact_id` against a separate
manifest file. Those operations require an explicit, bounded catalog-directory
validator. Until that exists, a schema-valid record means the declaration is
well formed, not that its upstream bytes, semantics, or provenance have been
independently verified.
