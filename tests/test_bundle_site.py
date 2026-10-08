"""Presentation must preserve evidence boundaries and treat submitted text as data."""

from copy import deepcopy
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlsplit

import pytest

from edgeloom.bundle_site import generated_files


class Page(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.ids = []
        self.links = []
        self.tags = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        values = dict(attrs)
        if "id" in values:
            self.ids.append(values["id"])
        if tag == "a":
            self.links.append(values.get("href", ""))


def test_source_comparisons_preserve_heading_hierarchy(report):
    report["records"]["comparison"] = {
        "kind": "catalog-corroboration",
        "id": "comparison",
        "summary": "Synthetic comparison.",
        "observations": [
            {
                "platform": "Fixture platform",
                "evidence_kind": "source-code",
                "relationship": "context",
                "claim": "Synthetic source context.",
                "conditions": [],
                "references": [],
            }
        ],
        "limitations": ["Not a device result."],
    }
    report["bundle"]["records"].append(
        {
            "id": "comparison",
            "path": "catalog/corroboration/example.json",
            "sha256": "c" * 64,
        }
    )
    page = Page(generated_files(report)["index.html"])
    levels = [int(tag[1]) for tag in page.tags if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}]
    assert all(current <= previous + 1 for previous, current in zip(levels, levels[1:]))


@pytest.fixture
def report():
    subject = {
        "manufacturer": "Example",
        "model": "Lock",
        "protocol": "zigbee",
        "identifiers": {"model": "Lock"},
        "firmware": "Unknown",
        "scope_notes": ["Model family only."],
    }
    observation = {
        "id": "main",
        "kind": "catalog-observation",
        "subject": subject,
        "feature_id": "main",
        "method": "simulation",
        "data_origin": "synthetic-example",
        "environment": {
            "platform": "Fixture",
            "platform_version": "1",
            "driver_revision": "none",
            "setup": "Documentation example only.",
        },
        "procedure": ["Supply synthetic input."],
        "expected": "Input is retained.",
        "observed": "Input is retained.",
        "outcome": "pass",
        "repetitions": 1,
        "observed_at": "2026-10-08T00:00:00Z",
        "reported_by": "Example contributor",
        "evidence": [],
        "limitations": ["No physical device involved."],
    }
    document = {
        "id": "sources",
        "kind": "document-source",
        "title": "Family manual",
        "publisher": "Example manufacturer",
        "url": "https://example.org/manual.pdf",
        "document_version": "1",
        "accessed_at": "2026-10-08",
        "source_maturity": "official",
        "applicability": {
            "manufacturer": "Example",
            "model": "Lock family",
            "scope": "family-context",
            "notes": ["Exact firmware is not specified."],
        },
        "locations": [{"id": "battery", "locator": "Page 3", "description": "Battery guidance."}],
        "capture": {"mode": "link-only"},
        "rights": {"redistribution": "not-granted", "notice": "Reference only."},
        "limitations": ["Not a protocol specification."],
    }
    feature = {
        "id": "main",
        "title": "Battery",
        "summary": "Explain battery conversion.",
        "record_ids": ["main", "sources"],
        "implementation_notes": [
            {
                "id": "sources",
                "decision": "Preserve the raw value.",
                "rationale": "Final normalization is unresolved.",
                "references": [
                    {"record_id": "sources", "locator": "#/locations/0", "relationship": "context"}
                ],
                "conditions": ["Exact model match is required."],
            }
        ],
        "test_plan": [
            {
                "id": "plan",
                "question": "What is the final value?",
                "procedure": ["Read it."],
                "requested_evidence": ["Firmware and sanitized values."],
            }
        ],
        "gaps": ["Hardware result missing."],
    }
    bundle = {
        "id": "test-bundle",
        "version": "0.1.0",
        "title": "Lock battery",
        "subject": subject,
        "author": "Example contributor",
        "license": "Apache-2.0",
        "features": [feature],
        "records": [
            {"id": "main", "path": "catalog/observations/example.json", "sha256": "a" * 64},
            {"id": "sources", "path": "catalog/documents/example.json", "sha256": "b" * 64},
        ],
        "reviews": [],
        "credits": [{"identity": "Example contributor", "roles": ["author"], "record_ids": []}],
        "history": [{"version": "0.1.0", "summary": "Initial candidate."}],
        "limitations": ["No hardware validation."],
    }
    return {
        "bundle": bundle,
        "records": {"main": observation, "sources": document},
        "catalog_revision": "working-tree",
        "declared_core_revision": "a" * 40,
        "input_digest": "b" * 64,
        "generator": {"implementation_digest": "c" * 64},
        "checks": {"record_hashes": "matched"},
    }


def test_report_navigation_and_prefilled_contributions(report):
    before = deepcopy(report)
    files = generated_files(report)
    assert set(files) == {"index.html", "report.md", "bundle.css"}
    assert report == before
    page = Page(files["index.html"])
    assert len(page.ids) == len(set(page.ids))
    assert all(link[1:] in page.ids for link in page.links if link.startswith("#"))
    assert {"bundle.zip", "report.md", "report.json", "checksums.txt"} <= set(page.links)
    contributions = [parse_qs(urlsplit(link).query) for link in page.links if "/issues/new?" in link]
    assert len(contributions) == 4
    for query in contributions:
        assert query["bundle"] == ["test-bundle"]
        assert query["version"] == ["0.1.0"]
        assert query["feature"] == ["main"]
        assert set(query) == {"template", "bundle", "version", "feature"}
    assert {q["template"][0] for q in contributions} == {
        "device-source.yml",
        "device-observation.yml",
        "correction.yml",
        "independent-review.yml",
    }
    assert "The ZIP link is available in the hosted or built report." in files["index.html"]
    assert "does not include another copy of itself" in files["index.html"]


def test_synthetic_pass_never_becomes_hardware_result(report):
    files = generated_files(report)
    for name in ("index.html", "report.md"):
        assert "Synthetic example · simulation · not a device result" in files[name]
        assert "No physical-device observations recorded for this feature." in files[name]
        assert "Proposed procedure; no execution result is implied." in files[name]
        assert "No scoped reviews recorded in this bundle." in files[name]
    assert "family-context" in files["index.html"]
    assert "Link only; document bytes are not pinned or included." in files["index.html"]


def test_physical_report_is_labeled_reported_not_verified(report):
    report["records"]["main"].update(method="physical-device", data_origin="community-report")
    files = generated_files(report)
    assert "Reported physical-device observation · not independently authenticated" in files["index.html"]
    assert "No physical-device observations recorded for this feature." not in files["index.html"]
    assert "No physical-device observations recorded for this feature." not in files["report.md"]


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "https://example.org\n/evil",
        "https://user@example.org/",
        "https://example.org:bad",
        "https://example.org\\@evil.org/",
    ],
)
def test_submitted_markup_and_unsafe_urls_are_inert(report, url):
    injection = '<script>alert("bad")</script> [link](javascript:alert(1)) ```'
    report["bundle"]["title"] = injection
    report["bundle"]["features"][0]["summary"] = injection
    report["records"]["sources"]["url"] = url
    files = generated_files(report)
    page = Page(files["index.html"])
    assert "script" not in page.tags
    assert url not in page.links
    assert all(not link.startswith("javascript:") for link in page.links)
    assert "&lt;script&gt;" in files["index.html"]
    assert "\\[link\\]" in files["report.md"]
    assert "<script>" not in files["report.md"]
