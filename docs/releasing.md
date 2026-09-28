# Releasing EdgeLoom

Releases are prepared in a pull request and published only after that exact
commit has passed review and CI. Merging a release-preparation pull request does
not publish a package: publication starts when a maintainer publishes a GitHub
Release for the matching tag.

## 1. Prepare the release pull request

1. Start from current `main` on a dedicated branch.
2. Update the distribution version in `edgeloom/__init__.py` and the translator
   component version in `translator/ha2st_edge/__init__.py`.
3. Move the release notes out of `Unreleased`, use the intended publication
   date, and update the comparison links at the end of `CHANGELOG.md`.
4. Update `CITATION.cff`, the manual tag default in
   `.github/workflows/release.yml`, supported versions in `SECURITY.md`, and
   version examples that users will copy.
5. Run the release gates below and open a pull request with the exact commands,
   results, and any expected pre-tag link failures.

If publication moves to another date, update both `CHANGELOG.md` and
`CITATION.cff` before merging.

## 2. Run the release gates

```bash
make check
make site-check
make site-links
python -m build
python -m twine check dist/*
uvx zizmor --min-severity medium .github/workflows
```

Install the wheel into a newly created virtual environment outside the checkout
and verify at least:

```bash
python -m venv /tmp/edgeloom-release-check
/tmp/edgeloom-release-check/bin/python -m pip install --upgrade pip
/tmp/edgeloom-release-check/bin/python -m pip install dist/*.whl
/tmp/edgeloom-release-check/bin/edgeloom --version
```

From that environment, run `audit` and `validate` against an evidence record and
the catalog fixtures. Confirm that all five bundled schema kinds resolve without
the checkout. Run a dependency audit against the resolved runtime environment.
The pull request CI must pass Python 3.11 and 3.12, package, and site jobs.

The two changelog comparison links for the new version will return 404 until the
tag exists. Record those as expected rather than weakening the link checker, and
check them again after publication.

## 3. Publish the immutable release

After the release pull request is merged and publication is approved:

1. Confirm the intended commit is still the tip of `main` and all required
   checks passed for that exact commit.
2. Create the stable `vX.Y.Z` tag at that commit.
3. Publish a GitHub Release for the tag. The `Publish to PyPI` workflow builds
   from the tag, verifies that the wheel version matches it, and publishes with
   PyPI Trusted Publishing.

Do not point the workflow at a branch or a moving reference. The manual workflow
is only for retrying an existing immutable release tag.

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
