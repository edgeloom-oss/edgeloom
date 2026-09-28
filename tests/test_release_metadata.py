import re
from pathlib import Path

import yaml
from ha2st_edge import __version__ as translator_version

from edgeloom import __version__

ROOT = Path(__file__).resolve().parents[1]


def test_release_metadata_uses_one_distribution_version() -> None:
    citation = yaml.safe_load((ROOT / "CITATION.cff").read_text(encoding="utf-8"))
    workflow = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
    match = re.search(r'^\s+default: "v([^"]+)"$', workflow, re.MULTILINE)

    assert translator_version == __version__
    assert citation["version"] == __version__
    assert match is not None
    assert match.group(1) == __version__


def test_changelog_links_span_the_release_boundary() -> None:
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    assert f"## [{__version__}]" in changelog
    assert (
        f"[Unreleased]: https://github.com/edgeloom-oss/edgeloom/compare/v{__version__}...HEAD"
    ) in changelog
    assert (
        f"[{__version__}]: https://github.com/edgeloom-oss/edgeloom/compare/v0.1.1...v{__version__}"
    ) in changelog
