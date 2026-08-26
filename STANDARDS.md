# Standards and interoperability

EdgeLoom is an assurance toolchain around smart-home artifacts. It is not a
device-description standard, a registry, a certification authority, or a
replacement for platform-native packaging and distribution.

## Relationship to SDF

[RFC 9880](https://datatracker.ietf.org/doc/html/rfc9880) defines the Semantic
Definition Format (SDF), an ecosystem- and protocol-independent format for
modeling Things, Objects, Properties, Actions, Events, and their data. Its
normative syntax is the CDDL in Appendix A. The JSON-Schema rendition in
Appendix B is informative.

RFC 9880 also makes the operational boundary explicit: implementations using
models for validation or augmentation need to establish their provenance,
authenticity, integrity, and applicability, including for imported components.
It treats model composition with the same supply-chain care as source code.
Those requirements motivate EdgeLoom's evidence work; they do not make
EdgeLoom an SDF implementation.

Current status:

| Area | EdgeLoom status |
| --- | --- |
| RFC 9880 SDF parsing or normative CDDL validation | Not implemented |
| RFC 9880 Appendix B JSON-Schema checks | Supported only when the operator supplies a pinned local rendition and labels it `informative` |
| SDF reference resolution and composition | Not implemented |
| [SDF Protocol Mapping](https://datatracker.ietf.org/doc/draft-ietf-asdf-sdf-protocol-mapping/) | Active Internet-Draft; not implemented |
| [SDF Supplements](https://datatracker.ietf.org/doc/draft-ietf-asdf-sdf-mapping/) | Active Internet-Draft; not implemented |
| EdgeLoom profile and capability-map schemas | Implemented product contracts, not SDF replacements |
| Local provenance and check evidence | Initial `evidence-record` schema and `edgeloom audit` support |

The Internet-Draft rows are moving work. The table was checked on 26 August
2026, when Protocol Mapping was at revision `-09` and Supplements at `-01`.
Always follow the version-agnostic Datatracker links above for current status.

## Evidence records, not conformance badges

`edgeloom audit` creates a local, versioned record containing:

- the exact artifact path, byte count, media type, and SHA-256 digest;
- operator-supplied source URI, revision, license, and maturity status;
- bounded JSON/YAML parse results;
- an optional check against a pinned local Draft 2020-12 JSON Schema, including
  that schema's digest and an explicit authority label;
- extension points for one-to-one, lossy, ambiguous, and unbound semantic
  mappings; transformation before/after digests; recovery results; and human
  disposition;
- limitations that travel with the record.

The command never fetches a remote model or schema. It does not authenticate
source metadata, resolve SDF references, infer license rights, establish
semantic correctness, declare security, or certify standards conformance.

For example, an operator who has independently pinned the RFC 9880 Appendix B
rendition can record an informative structural check:

```bash
edgeloom audit model.sdf.json \
  --schema ./pinned/rfc9880-appendix-b.schema.json \
  --schema-authority informative \
  --source-uri https://example.org/models/model.sdf.json \
  --source-ref 0123456789abcdef \
  --license BSD-3-Clause \
  --artifact-status experimental \
  --output reports/model.evidence.json
```

See [Evidence records](docs/evidence-records.md) for interpretation and a
corpus workflow.

## Planned standards-facing work

Future work should remain incremental and reviewable:

1. pin public SDF/OneDM sources in a manifest with exact revisions, licenses,
   digests, and experimental/stable labels;
2. distinguish normative CDDL results from informative JSON-Schema checks;
3. resolve references without silently fetching mutable content;
4. record protocol/platform mappings with explicit semantic-loss classes;
5. record patch, restore, diff, and round-trip evidence;
6. return reproducible implementation findings to the relevant standards
   communities rather than maintaining a competing format.

AI may later rank candidate mappings or summarize diffs, but it must remain
optional and human-supervised. AI output is a suggestion, never accepted
evidence: it must cite pinned inputs, carry uncertainty, pass deterministic
checks, and receive an explicit human disposition before publication.

## Feedback

Use [GitHub Discussions](https://github.com/edgeloom-oss/edgeloom/discussions)
for design questions. File reproducible implementation findings in the
upstream standards project when appropriate; do not imply IETF, OneDM, W3C,
CSA, a platform, or a manufacturer endorses EdgeLoom.
