# Evidence records

An evidence record answers a narrow question: **what exact bytes were checked,
with which local policy and schema, and what did those checks establish or
leave unresolved?** It is designed for audit trails and review, not for
certification.

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

Use `--format markdown` for a compact human-review view. JSON is the canonical
machine-readable form and validates against
[`schema/evidence-record.schema.json`](../schema/evidence-record.schema.json).

The command exits nonzero when parsing or the supplied schema check fails. It
still emits a valid evidence record for those expected check failures, so a
corpus run can preserve negative results. Setup errors such as a missing
artifact or invalid schema produce no record.

Schema failures record the failed keyword plus bounded instance and schema
paths; they do not copy the rejected artifact value into the record. Syntax
errors are bounded diagnostic text. Review evidence records before publishing
them because file paths and operator-supplied metadata may still be sensitive.

## Authority labels

The label describes the supplied check, not the artifact:

| Label | Use |
| --- | --- |
| `normative` | The supplied schema is the governing specification for this exact check. Record the governing version and source. |
| `informative` | The schema is a non-normative rendition or diagnostic aid. RFC 9880 Appendix B belongs here. |
| `user-supplied` | The operator supplied a project, vendor, or experimental schema with no broader authority claim. |

EdgeLoom's built-in digest and syntax checks use `deterministic` automatically.

## What a pass means

- `content-digest: pass` means EdgeLoom read the bytes and computed the recorded
  SHA-256 value.
- `document-syntax: pass` means bounded parsing succeeded as JSON or YAML.
- `json-schema: pass` means the parsed document satisfied the exact supplied
  Draft 2020-12 schema whose digest appears in the record.

None of those establish origin, authenticity, ownership, licensing,
applicability to a particular device, semantic consistency, secure behavior,
or standards conformance. The limitations are embedded in every generated
record so they are not separated from exported results.

Schema evaluation runs in the EdgeLoom process. File-size, document-depth, and
node-count limits reduce resource risk, but they do not provide a hard runtime
bound for adversarial schema expressions. Use a disposable environment for a
third-party schema you do not trust.

## Building a reviewable corpus

For a public SDF/OneDM corpus, keep upstream material outside EdgeLoom or in a
disposable pinned checkout. Maintain a small source manifest containing the
repository URL, exact commit, file path, declared license, and maturity label.
Generate one evidence record per artifact and publish the manifest plus compact
records—not a mutable mirror presented as an authoritative registry.

A review workflow can then add, without changing the source model:

- reference-resolution results;
- mapping classifications (`one-to-one`, `lossy`, `ambiguous`, `unbound`);
- transformation and recovery digests;
- reviewer identity, disposition, and notes;
- explicit unresolved questions and upstream issue links.

The v0.1 CLI fills the identity and deterministic-check portion. The richer
fields are present in the schema for reviewed tools and experiments to populate
without inventing a second device-description format.
