# Evidence records

An evidence record answers a narrow question: **what exact local byte snapshot
was checked, with which local policy and schema, and what did those checks
establish or leave unresolved?** It is designed for audit trails and review,
not for provenance authentication, standards conformance, or certification.

## Create a record

Hash and parse a local JSON/YAML artifact:

```bash
edgeloom audit ./model.sdf.json --output ./reports/model.evidence.json
```

Add source assertions and a pinned local schema:

```bash
edgeloom audit ./model.sdf.json \
  --schema ./pinned/sdf.schema.json \
  --schema-authority informative \
  --source-uri https://github.com/example/models/blob/0123456/model.sdf.json \
  --source-ref 0123456 \
  --license BSD-3-Clause \
  --artifact-status experimental \
  --title "Example model at 0123456" \
  --output ./reports/model.evidence.json
```

Surrounding whitespace is removed from optional source, revision, license, and
title assertions; values that become empty are rejected rather than silently
changing record identity.

Use `--format markdown` for a compact human-review view. JSON is the canonical
machine-readable form and validates against
[`schema/evidence-record.schema.json`](../schema/evidence-record.schema.json).
Every JSON record is checked against that bundled schema before EdgeLoom emits
it.

The command exits nonzero when parsing or the supplied schema check fails. It
still emits a valid evidence record for those expected check failures, so a
corpus run can preserve negative results. Setup errors such as a missing
artifact, invalid schema, unresolved local reference, or non-local `$ref`
produce no record.

Output files are written beside their destination and atomically replaced only
after the complete record is ready. EdgeLoom refuses to use the artifact or its
schema as the output path.

## Snapshot and bounds

EdgeLoom reads each local file through one open file handle. For an artifact at
or below the 8 MiB parse limit, the digest and parser consume the same byte
snapshot; larger files are streamed through SHA-256 and are not parsed. A file
that changes while it is read is rejected rather than recorded.

JSON and YAML then use the same depth and expanded-node bounds as `edgeloom
validate`. The size check occurs before decoding. YAML aliases are counted as
their expanded shape before a schema walks them.

Schema failures record only a bounded number of failed keywords plus bounded
instance and schema paths; rejected artifact values are not copied into the
record. Syntax diagnostics contain only a bounded error type and safe position
metadata; source snippets and values are omitted. Review evidence records
before publishing them because local paths and operator-supplied metadata may
still be sensitive.

## Authority labels

The label describes the supplied check, not the artifact:

| Label | Use |
| --- | --- |
| `normative` | The supplied schema is the governing specification for this exact check. Record the governing version and source. |
| `informative` | The schema is a non-normative rendition or diagnostic aid. |
| `user-supplied` | The operator supplied a project, vendor, or experimental schema with no broader authority claim. |

EdgeLoom's built-in digest and syntax checks use `deterministic` automatically.
The authority value is still an operator assertion: EdgeLoom does not establish
that a schema is truly normative.

## What a pass means

- `content-digest: pass` means EdgeLoom read the local bytes and computed the
  recorded SHA-256 value.
- `document-syntax: pass` means the same bounded byte snapshot parsed as JSON
  or YAML.
- `json-schema: pass` means the parsed document satisfied the exact supplied
  Draft 2020-12 schema whose digest appears in the record. JSON Schema format
  checks are enabled.

None of those establish origin, authenticity, ownership, licensing,
applicability to a particular device, semantic consistency, secure behavior,
or standards conformance. `--source-uri`, `--source-ref`, `--license`,
`--artifact-status`, and `--schema-authority` are recorded assertions, not
facts EdgeLoom fetches or authenticates. These limitations are embedded in
every generated record so they are not separated from exported results.

Schema evaluation runs in the EdgeLoom process. File-size, document-depth,
expanded-node, and reported-error limits reduce resource risk, but they do not
provide a hard runtime bound for every adversarial schema expression. Use a
disposable environment for a third-party schema you do not trust.

## References stay local

The v0.1 command does not fetch anything. A supplied schema may use local JSON
Pointer references beginning with `#`; non-local `$ref` and `$dynamicRef`
values are rejected. A broken local reference is a setup error. Pin and bundle
every required schema before running an audit.

The v0.1 schema permits an optional human `review` disposition. Active
dispositions (`accepted`, `rejected`, or `needs-work`) require a reviewer and
review time, but all three values remain operator assertions: EdgeLoom does not
authenticate the reviewer or turn the value into certification or governance
approval. The current CLI does not invent a review decision.

Mapping, transformation, and recovery contracts are intentionally deferred
until EdgeLoom has real producers and lifecycle semantics for them. They do not
belong in a byte-snapshot record merely because a schema can reserve fields.
