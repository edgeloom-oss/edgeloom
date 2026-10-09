# Device Evidence Bundle review and publication checklist

This is an execution checklist for the [draft bundle format](device-evidence-bundles.md),
not approval to adopt it, merge either repository, deploy a snapshot, or release
software. Keep technical review, publication permission and evidence status
separate. Record completed checks against exact commits in the pull requests.

## 1. Review the draft, not just the generated page

Use [issue #63](https://github.com/edgeloom-oss/edgeloom/issues/63) for the format
discussion, [core PR #64](https://github.com/edgeloom-oss/edgeloom/pull/64) for
contracts/tooling, and [catalog PR #5](https://github.com/edgeloom-oss/edgeloom-catalog/pull/5)
for the initial records and contribution forms. Follow the substantial-change
window and review requirements in [GOVERNANCE.md](../GOVERNANCE.md). Elapsed time
and green CI alone do not constitute approval.

Reviewers can take one bounded question:

- **Contribution burden:** can a person contribute one manual reference or
  executed observation without inventing an SDF mapping or unknown firmware?
- **Explanation traceability:** do the cited records and JSON pointers support
  each feature explanation, and are contrary evidence and applicability limits
  visible? A resolved pointer only establishes that the location exists.
- **Package trust boundary:** are record closure, digests, safe paths, bounded
  inputs and re-derived reports checked without fetching or executing upstream
  content? Hash agreement is not publisher authentication.
- **Review and credit:** does a review identify exact record hashes and its
  actual scope? Are authoring, source research, observations and independent
  review kept distinct when assigning credit?
- **Usability:** can a reader inspect, download and verify a package, then find
  a small contribution to make? The first Yale sample has no physical-device
  observations or independent reviews; a review must not silently change that.

Record findings, tested commits, method and limitations in the relevant issue
or PR. An agent's code review or a green CI run is not an independent community
review of the device evidence and must not be recorded as such in the bundle.

## 2. Freeze the paired inputs

Before requesting merge approval, capture:

- The exact core and catalog PR heads and successful CI runs for those heads.
- The catalog's full `CORE_REVISION`, bundle ID/content version, and locked
  record hashes. Verify the pin is reachable from the intended accepted core
  history, not merely temporarily downloadable from an unmerged branch.
- The catalog source commit embedded in the prepared site snapshot, generator
  digest, ZIP SHA-256 and repeated-build comparison. The snapshot commit may
  precede a merge commit if its catalog inputs and core pin are unchanged;
  record that relationship rather than relabeling the generated provenance.
- The clean installed-wheel roundtrip, regression results, site/link checks,
  and desktop/mobile inspection for the prepared snapshot.

At initial review, catalog PR #5 pins core commit
`0c86fea045972458dc1e60eb435ced95036f04fe`, which is part of core PR #64's history.
A merge commit preserves that dependency. Squashing or rebasing core PR #64
requires a deliberate re-pin to an accepted commit, repeated validation and
snapshot regeneration; do not delete the only branch retaining the pin and
assume the dependency remains supported. Recheck these facts if either head
changes. A documentation-only core follow-up does not itself require changing
the catalog's generator pin.

Use fresh output paths and the pinned-core installation in the draft walkthrough
for local checks. Do not overwrite canonical records, alter hashes to hide a
failure, or advance a candidate lifecycle to make a gate pass.

## 3. Coordinate merges with the existing Pages trigger

**Core pushes to `main` trigger the existing [Pages workflow](../.github/workflows/pages.yml).**
Core PR #64 includes the prepared static snapshot. Approving that PR's merge
therefore also needs approval to publish that snapshot; merge and website
deployment are not independent controls in the current workflow. This checklist
does not change that workflow or repository settings.

For the current paired PRs, the coordinated path after review and explicit
approval is:

1. Re-read both live heads, checks, comments and the format decision. Obtain
   approval for the exact catalog merge and core merge/Pages publication.
2. Merge the accepted catalog records and issue templates before exposing their
   links on Pages. Re-read catalog `main` and verify its inputs and pin still
   match the reviewed snapshot. The pin is already available in the reviewed
   core branch; this ordering does not make it an accepted software release.
3. Merge the exact approved core head with its pinned history preserved. If
   the core merge cannot proceed, report the partial state; do not describe the
   candidate catalog merge alone as a complete release or trigger deployment.
4. Check the `main` CI run and Pages deployment for the resulting core commit.
   Read back the public bundle page, downloaded ZIP hash, and contribution
   forms, including prefilled bundle/version/feature values. Verify the public
   ZIP with its declared generator and confirm candidate/limitations labels.

If only a code merge is approved, first prepare a separately reviewed split
that excludes the new static snapshot from the merge. Do not silently disable
Pages, change its environment protections, or merge the snapshot while promising
that deployment can be deferred.

On failure, preserve the workflow logs and exact source/package hashes. A
rollback or workflow-setting change needs a scoped maintainer decision; failed
publication is not permission to weaken integrity or release gates.

## 4. Keep software publication and community evidence separate

Bundle commands are not in the public PyPI 0.2.0 distribution. Until a new
software release is approved and read back, share the pinned development
installation rather than instructing users to obtain these commands from
`pip install edgeloom==0.2.0`.

Prepare a distinct versioned software release using [RELEASING.md](RELEASING.md).
Select and approve the new version; update metadata; validate the final wheel
and sdist; then separately approve the tag, GitHub Release and gated PyPI
publication. A version change changes generator provenance. If re-pinning the
catalog to that release, regenerate and verify its snapshot in a follow-up PR;
do not rewrite an older download's declared provenance.

After public readback, a small community invitation can ask for one source
correction, one scoped review, or one sanitized observation on an already
configured device. Announcements remain a separate action. Track actual
responses and accepted contributions, not source counts, CI passes or package
downloads as evidence of adoption or hardware compatibility.
