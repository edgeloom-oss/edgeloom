from pathlib import Path

import yaml
from ha2st_edge import __version__ as translator_version

from edgeloom import __version__

ROOT = Path(__file__).resolve().parents[1]


def test_release_metadata_uses_one_distribution_version() -> None:
    citation = yaml.safe_load((ROOT / "CITATION.cff").read_text(encoding="utf-8"))
    workflow = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")

    assert translator_version == __version__
    assert citation["version"] == __version__
    assert "TAG: ${{ github.event.client_payload.tag }}" in workflow
    assert '--version "${TAG#v}"' in workflow


def test_changelog_links_span_the_release_boundary() -> None:
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    assert f"## [{__version__}]" in changelog
    assert (
        f"[Unreleased]: https://github.com/edgeloom-oss/edgeloom/compare/v{__version__}...HEAD"
    ) in changelog
    assert (
        f"[{__version__}]: https://github.com/edgeloom-oss/edgeloom/compare/v0.1.1...v{__version__}"
    ) in changelog


def test_release_workflow_gates_publishing_on_main_and_exact_commit_checks() -> None:
    workflow = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")

    assert workflow.count("actions: read") == 2
    assert "workflow_dispatch" not in workflow
    assert "types: [publish_release]" in workflow
    assert "github.event.client_payload.tag" in workflow
    assert "fetch-depth: 0" in workflow
    assert "releases/tags/${TAG}" in workflow
    assert "actions/workflows/ci.yml/runs" in workflow
    assert 'head_sha="$commit"' in workflow
    assert 'required_checks=("build (3.11)" "build (3.12)" "package" "site")' in workflow
    assert "refs/remotes/origin/release-tag^{commit}" in workflow
    assert "must identify a published, non-prerelease GitHub Release" in workflow
    assert "EXPECTED_RELEASE_ID" in workflow
    assert "GitHub Release state changed before publication" in workflow
    assert workflow.count("actions/workflows/ci.yml/runs") == 2
    assert "latest ci.yml push run for $commit changed or is not successful" in workflow
    assert "--require-hashes -r requirements-release.txt" in workflow
    assert "python -m build --no-isolation" in workflow
    assert "scripts/verify_release_dist.py" in workflow
    assert "packages-dir: release-bundle/dist/" in workflow


def test_package_ci_exercises_the_hash_locked_release_toolchain() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "--require-hashes -r requirements-release.txt" in workflow
    assert "python -m build --no-isolation" in workflow
    assert "scripts/verify_release_dist.py" in workflow
