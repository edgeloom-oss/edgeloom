# Catalog Contracts

EdgeLoom's catalog contracts describe evidence-backed relationships among
device behavior, native edge-driver artifacts, and protocol-independent SDF
models. They are assurance records, not an authoritative device registry,
driver store, certification, or claim of standards adoption.

Version 0.1 publishes two JSON Schema Draft 2020-12 contracts:

- [`source-manifest.schema.json`](../schema/source-manifest.schema.json) pins one
  upstream Git repository to a full 40-character commit ID. Every artifact has
  a Git-tree-relative POSIX path, SHA-256 digest, media type, artifact role,
  license evidence, and upstream source maturity.
- [`catalog-mapping-set.schema.json`](../schema/catalog-mapping-set.schema.json)
  records the evidence nodes and mappings built from those pinned artifacts.
  It keeps EdgeLoom's review lifecycle separate from upstream source maturity.

The synthetic lock records in [`tests/fixtures/catalog/`](../tests/fixtures/catalog/)
exercise both contracts without creating a real catalog entry.

## Stable identifiers and paths

`ecosystem`, `scope.domain`, `scope.platform`, and every value in
`scope.protocols` are lowercase aggregation identifiers, such as
`smartthings`, `door-lock`, and `zwave`. They are stable machine keys, not
display names. Titles, descriptions, and node labels carry human-readable text.
This avoids splitting deterministic indexes across spellings such as
`SmartThings`, `smartthings`, and `Samsung SmartThings`.

An artifact's `artifact_role` is separate from its evidence `layer`. Version
0.1 recognizes `driver-config`, `fingerprints`, `platform-profile`, `sdf-model`,
and `evidence`, allowing readers to select a parser without guessing from a
filename or media type.

Two path namespaces are explicit:

- artifact and license-evidence paths are POSIX paths within the pinned Git
  tree; and
- `source_manifests[].path` is a POSIX path resolved from the catalog repository
  root, not from the mapping-set file's directory.

Neither path is a host filesystem path. Absolute and Windows-drive paths, dot
segments, control characters, empty segments, trailing slashes, backslashes,
and `.git` administrative paths are invalid.

## Three evidence layers

A mapping set must represent all three layers explicitly:

1. `device-protocol-support`: what the pinned device or protocol artifact says
   the device can do.
2. `platform-exposure`: what the pinned native driver/profile exposes.
3. `neutral-sdf-representation`: what the pinned SDF artifact can represent.

Keeping these layers separate prevents an unexposed platform feature from
being mistaken for an absent device feature or a missing neutral model.

A bound mapping must connect two different evidence layers. Direct mappings
between any two different layers, including device-to-SDF mappings, are allowed
when the cited evidence supports them; self-edges and same-layer edges are not.

Mappings are classified as `one-to-one`, `lossy`, `ambiguous`, or `unbound`.
A lossy mapping must name at least one loss dimension. An unbound mapping has no
target and must distinguish among `device-feature-absent`,
`platform-not-exposed`, `neutral-model-missing`, `insufficient-evidence`, and
`out-of-scope`. Every mapping cites evidence and carries an explicit limitations
list, which may be empty only when there are no known qualifications.

## Status is two-dimensional

`source_maturity` declares the status attributed to upstream material:

- `official`
- `community`
- `experimental`
- `draft`
- `deprecated`
- `unknown`

Use `unknown` when the pinned source does not provide enough evidence for a
more specific status. Validators must not force a stronger upstream claim merely
to satisfy the contract.

`review.lifecycle` declares the treatment proposed for a mapping set:

- `candidate`
- `reviewed`
- `verified`
- `deprecated`

An experimental SDF model therefore remains experimental even when an
EdgeLoom mapping has been reviewed. Likewise, an official upstream artifact
does not make an EdgeLoom mapping verified.

Both axes are **untrusted declarations inside a file**. `edgeloom validate`
checks their structure; it does not authenticate the author, reviewers, source
owner, or decision. A non-candidate record must name at least one reviewer other
than its explicit `review.author`. A `verified` declaration must also cite a
`review.decision_ref`, but neither field becomes authoritative merely by passing
validation. Project-trusted status comes only from acceptance through the
governed history and review controls of an official catalog repository. A
renderer or downstream consumer must preserve that distinction.

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

Repository URL checks are implemented explicitly by EdgeLoom rather than
depending only on optional `jsonschema` URI-format extras: a URL must use HTTPS,
include a hostname, and contain no embedded credentials, query, or fragment.
Future fetch code still needs its own explicit network/SSRF policy.

## Shared validation dependency

Catalog validation uses the same bounded loader and diagnostic path as
EdgeLoom's evidence-record validation. When the catalog work is stacked with
the audit/evidence foundation, integration must retain all five schema kinds
(`profile`, `capability-map`, `evidence-record`, `source-manifest`, and
`catalog-mapping-set`) and cap the combined JSON-Schema and semantic diagnostic
stream. The catalog contracts do not replace evidence records.
