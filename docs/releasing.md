# Releasing EdgeLoom

Releases are prepared in a pull request and published only after that exact
commit has passed review and CI. Merging a release-preparation pull request and
publishing a GitHub Release do not publish a package: PyPI publication starts
only when a maintainer separately dispatches the gated workflow.

## 1. Prepare the release pull request

1. Start from current `main` on a dedicated branch.
2. Update the distribution version in `edgeloom/__init__.py` and the translator
   component version in `translator/ha2st_edge/__init__.py`.
3. Move the release notes out of `Unreleased`, use the intended publication
   date, and update the comparison links at the end of `CHANGELOG.md`.
4. Update `CITATION.cff`, supported versions in `SECURITY.md`, and version
   examples that users will copy.
5. Run the release gates below and open a pull request with the exact commands,
   results, and any expected pre-tag link failures.

If publication moves to another date, update both `CHANGELOG.md` and
`CITATION.cff` before merging.

## 2. Run the release gates

```bash
make check
make site-check
make site-links
python -m pip install --require-hashes -r requirements-release.txt
python -m build --no-isolation --outdir release-bundle/dist
python -m twine check release-bundle/dist/*
python scripts/verify_release_dist.py --dist-dir release-bundle/dist \
  --version X.Y.Z --write-manifest release-bundle/SHA256SUMS
uvx zizmor --min-severity medium .github/workflows
```

Install the wheel into a newly created virtual environment outside the checkout
and verify at least:

```bash
python -m venv /tmp/edgeloom-release-check
/tmp/edgeloom-release-check/bin/python -m pip install --upgrade pip
/tmp/edgeloom-release-check/bin/python -m pip install release-bundle/dist/*.whl
/tmp/edgeloom-release-check/bin/edgeloom --version
```

From that environment, run `audit` and `validate` against an evidence record and
the catalog fixtures. Confirm that all ten bundled schema kinds resolve without
the checkout. Run the synthetic document-only bundle through `bundle check`,
`build`, two byte-identical `export` calls and `verify`. Confirm that the wheel
ships `bundle.css` and that verification rejects a tampered package. A local
build's package-version label is not evidence that this code was published on
PyPI: update the software version only in the approved release preparation.
Run a dependency audit against the resolved runtime environment.
The pull request CI must pass Python 3.11 and 3.12, package, and site jobs.

The two changelog comparison links for the new version will return 404 until the
tag exists. Record those as expected rather than weakening the link checker, and
check them again after publication.

## 3. Publish the gated release

After the release pull request is merged and tag/release creation is approved:

1. Confirm the intended commit is still the tip of `main` and all required
   checks passed for that exact commit.
2. Create the stable `vX.Y.Z` tag at that commit.
3. Publish a GitHub Release for the tag.
4. After a separate publication approval, dispatch the protected default-branch
   workflow with the stable release tag as data:

   ```bash
   gh api --method POST repos/edgeloom-oss/edgeloom/dispatches \
     -f event_type=publish_release \
     -F 'client_payload[tag]=vX.Y.Z'
   ```

   The `Publish to PyPI` workflow builds from that tag, verifies both
   distributions against it, and publishes with PyPI Trusted Publishing.

The workflow fails closed unless the tag, checkout, and current `main` tip
resolve to the same commit; the GitHub Release is published and is not a
prerelease; and the latest successful `ci.yml` push run for that exact commit
contains passing Python 3.11, Python 3.12, packaging, and site jobs. It also
requires exactly one wheel and one source distribution, checks both packages'
embedded name/version metadata, and verifies their SHA-256 manifest again
immediately before publication.

Do not point the workflow at a branch or a moving reference. Both `release` and
`workflow_dispatch` triggers are intentionally disabled: `repository_dispatch`
loads the workflow definition from the default branch, so a tag or feature
branch cannot substitute a weaker publishing workflow. For a transient failure,
use **Re-run failed jobs** on the original dispatch run; its tag payload and
event context retain the same release-state and exact-commit check gates. Build,
Twine, Hatchling, pip, and their transitive dependencies are installed from the
reviewed SHA-256 lock in `requirements-release.txt`; the PEP 517 build runs
without a second unverified dependency resolution. A repository tag ruleset
that blocks `v*` updates and deletions remains
recommended; until that setting is approved, the workflow independently
re-fetches and compares the live tag in both the build and publish jobs.

## 4. Read back the public state

Treat the release as complete only after independently checking:

- the GitHub Release tag, target commit, notes, and attached source archives;
- the successful `Publish to PyPI` run for the same tag;
- the PyPI version, wheel and source distribution, and provenance attestation;
- a fresh `pip install edgeloom==X.Y.Z` followed by `edgeloom --version` and a
  small installed-wheel smoke test; and
- the changelog comparison links and public site/package metadata.

Record the tag, commit, workflow run, artifact hashes, and read-back evidence in
the project journal before starting any downstream re-pin or announcement.
