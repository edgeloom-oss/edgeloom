"""Nested static report links and fragments must be checked, not just the homepage."""

from pathlib import Path

from scripts import site_check


def test_nested_relative_links_and_cross_page_fragments(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "site"
    page = root / "catalog/devices/acme/index.html"
    page.parent.mkdir(parents=True)
    page.write_text('<main id="main"><a href="../../#browser">Browse</a><a href="#main">Skip</a></main>')
    index = root / "catalog/index.html"
    index.write_text('<main id="browser"></main>')
    monkeypatch.setattr(site_check, "SITE", root)
    errors, _ = site_check.check_local_links(site_check.parse_site(page), page)
    assert not errors
    index.write_text('<main id="different"></main>')
    errors, _ = site_check.check_local_links(site_check.parse_site(page), page)
    assert any("missing fragment #browser" in error for error in errors)


def test_nested_link_cannot_escape_site(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "site"
    root.mkdir()
    page = root / "index.html"
    page.write_text('<a href="../outside.html">Escape</a>')
    monkeypatch.setattr(site_check, "SITE", root)
    errors, _ = site_check.check_local_links(site_check.parse_site(page), page)
    assert any("escapes site" in error for error in errors)
