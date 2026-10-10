"""Offline, feature-centered views for validated Device Evidence Bundle reports."""

from __future__ import annotations

import json
import re
from html import escape
from pathlib import Path
from urllib.parse import quote, urlencode, urlsplit

CATALOG_URL = "https://edgeloom-oss.github.io/edgeloom/catalog/"
ISSUES_URL = "https://github.com/edgeloom-oss/edgeloom-catalog/issues/new"
INTEGRITY_NOTE = (
    "Record hashes and reference checks establish package consistency. They do not authenticate "
    "a publisher, establish independent review, or demonstrate device behavior."
)
CONTRIBUTIONS = (
    ("device-source.yml", "Add a source"),
    ("device-observation.yml", "Report an observation"),
    ("correction.yml", "Suggest a correction"),
    ("independent-review.yml", "Review this evidence"),
)


def _e(value: object) -> str:
    return escape(str(value), quote=True)


def _md(value: object) -> str:
    """Keep contributed text inert in Markdown, including raw HTML and autolinks."""
    text = escape(str(value), quote=True)
    return re.sub(r"([\\`*_{}\[\]()#+.!|>~-])", r"\\\1", text).replace("\n", " ")


def _https(value: object) -> str | None:
    """Defense in depth: reports can also be rendered outside schema validation."""
    text = str(value)
    if any(ord(char) < 33 or ord(char) == 127 for char in text) or "\\" in text:
        return None
    try:
        parts = urlsplit(text)
        if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
            return None
        _ = parts.port  # Reject malformed ports rather than letting a browser reinterpret them.
    except ValueError:
        return None
    return quote(text, safe="/:?#[]@!$&'()*+,;=%-._~")


def _link(url: object, label: object) -> str:
    target = _https(url)
    return f'<a href="{_e(target)}" rel="noreferrer">{_e(label)}</a>' if target else _e(label)


def _md_link(url: object, label: object) -> str:
    target = _https(url)
    return f"[{_md(label)}](<{target}>)" if target else _md(label)


def _list(items: list, *, ordered: bool = False) -> str:
    if not items:
        return ""
    tag = "ol" if ordered else "ul"
    return f"<{tag}>" + "".join(f"<li>{_e(item)}</li>" for item in items) + f"</{tag}>"


def _facts(values: dict) -> str:
    return (
        '<dl class="facts">'
        + "".join(f"<div><dt>{_e(key)}</dt><dd>{_e(value)}</dd></div>" for key, value in values.items())
        + "</dl>"
    )


def _json_details(record: dict, label: str = "Complete record") -> str:
    return (
        f"<details><summary>{_e(label)}</summary><pre>"
        f"{_e(json.dumps(record, indent=2, ensure_ascii=False, sort_keys=True))}</pre></details>"
    )


def _contribution_url(bundle: dict, feature: dict, template: str) -> str:
    return (
        ISSUES_URL
        + "?"
        + urlencode(
            {
                "template": template,
                "bundle": bundle["id"],
                "version": bundle["version"],
                "feature": feature["id"],
            }
        )
    )


def _record_label(record: dict) -> str:
    if record["kind"] == "source-manifest":
        return f"{record['ecosystem']} · source snapshot"
    if record["kind"] == "catalog-device":
        return f"{record['manufacturer']} {record['model']} · device identity"
    return record.get("title") or record["id"]


def _observation_label(record: dict) -> str:
    if record["data_origin"] == "synthetic-example":
        return "Synthetic example · simulation · not a device result"
    if record["method"] == "physical-device":
        return "Reported physical-device observation · not independently authenticated"
    return "Reported simulation · not a physical-device test"


def _record_kind(record: dict) -> str:
    return _observation_label(record) if record["kind"] == "catalog-observation" else record["kind"]


def _observation_html(record: dict) -> str:
    environment = record["environment"]
    return (
        f'<p class="badge">{_e(_observation_label(record))}</p>'
        f"<p><strong>Reported outcome:</strong> {_e(record['outcome'])}</p>"
        f"<p><strong>Expected:</strong> {_e(record['expected'])}</p>"
        f"<p><strong>Observed:</strong> {_e(record['observed'])}</p>"
        + _facts(
            {
                "Reporter": record["reported_by"],
                "Observed at": record["observed_at"],
                "Repetitions": record["repetitions"],
                "Platform": environment["platform"],
                "Platform version": environment["platform_version"],
                "Driver revision": environment["driver_revision"],
                "Firmware": record["subject"]["firmware"],
            }
        )
        + "<details><summary>Setup, procedure &amp; supporting material</summary>"
        + f"<p>{_e(environment['setup'])}</p>"
        + _list(record["procedure"], ordered=True)
        + "".join(f"<p>{_link(item['url'], item['description'])}</p>" for item in record["evidence"])
        + _list(record["limitations"])
        + "</details>"
    )


def _document_html(record: dict) -> str:
    applicability, capture = record["applicability"], record["capture"]
    capture_label = (
        "Link only; document bytes are not pinned or included."
        if capture["mode"] == "link-only"
        else "Content digest declared; document bytes are not included or checked by this report."
    )
    locations = "".join(
        f"<li><strong>{_e(item['locator'])}</strong> — {_e(item['description'])}</li>"
        for item in record["locations"]
    )
    return (
        f'<p class="badge">{_e(record["source_maturity"])} source declaration · '
        f"{_e(applicability['scope'])}</p>"
        f"<p>{_link(record['url'], 'Open upstream document ↗')}</p>"
        + _facts(
            {
                "Publisher": record["publisher"],
                "Document version": record["document_version"],
                "Accessed": record["accessed_at"],
                "Applies to": f"{applicability['manufacturer']} {applicability['model']}",
            }
        )
        + _list(applicability["notes"])
        + (f"<ul>{locations}</ul>" if locations else "<p>No page or section citations recorded.</p>")
        + f'<p class="muted">{capture_label}</p>'
        + (
            f"<p>Declared document SHA-256: <code>{_e(capture['sha256'])}</code></p>"
            if capture["mode"] == "digest-recorded"
            else ""
        )
        + f"<p>Redistribution: {_e(record['rights']['redistribution'])}. "
        f"{_e(record['rights']['notice'])}</p>" + _list(record["limitations"])
    )


def _artifact_link(source: dict, artifact: dict) -> str:
    repository = source["repository"]
    return (
        repository["url"].rstrip("/")
        + "/blob/"
        + quote(repository["commit"], safe="")
        + "/"
        + quote(artifact["path"], safe="/")
    )


def _source_html(record: dict) -> str:
    repository = record["repository"]
    artifacts = "".join(
        f"<li>{_link(_artifact_link(record, item), item['path'])}"
        f"<p>{_e(item['description'])}</p><small>Declared source SHA-256: "
        f"<code>{_e(item['sha256'])}</code></small></li>"
        for item in record["artifacts"]
    )
    return (
        f"<p>{_e(record.get('description', ''))}</p>"
        f"<p>{_link(repository['url'], 'Upstream repository ↗')} · commit "
        f"<code>{_e(repository['commit'])}</code></p><ul>{artifacts}</ul>"
        '<p class="muted">Source references describe pinned implementation snapshots. '
        "Upstream code is not included or executed by this bundle.</p>"
    )


def _corroboration_html(record: dict, records: dict) -> str:
    rows = []
    for item in record["observations"]:
        references = []
        for reference in item["references"]:
            source = records.get(reference["manifest_id"], {})
            artifact = next(
                (a for a in source.get("artifacts", []) if a["id"] == reference["artifact_id"]), None
            )
            label = reference["artifact_id"] + " · " + reference["locator"]
            references.append(_link(_artifact_link(source, artifact), label) if artifact else _e(label))
        rows.append(
            f'<article class="comparison"><h3>{_e(item["platform"])}</h3>'
            f'<p class="meta">{_e(item["evidence_kind"])} · {_e(item["relationship"])}</p>'
            f"<p>{_e(item['claim'])}</p>"
            + _list(item["conditions"])
            + "<ul>"
            + "".join(f"<li>{link}</li>" for link in references)
            + "</ul></article>"
        )
    return (
        f'<p>{_e(record["summary"])}</p><p class="muted">Code declarations and upstream '
        "test fixtures describe source evidence; they are not physical-device results.</p>"
        '<div class="comparison-grid">' + "".join(rows) + "</div>" + _list(record["limitations"])
    )


def _record_html(record: dict, records: dict) -> str:
    kind = record["kind"]
    if kind == "document-source":
        content = _document_html(record)
    elif kind == "catalog-observation":
        content = _observation_html(record)
    elif kind == "source-manifest":
        content = _source_html(record)
    elif kind == "catalog-corroboration":
        content = _corroboration_html(record, records)
    else:
        content = f"<p>{_e(record.get('summary', ''))}</p>" + _list(record.get("limitations", []))
    return content + _json_details(record)


def _feature_html(bundle: dict, feature: dict, index: int, records: dict, anchors: dict) -> str:
    notes = []
    for note in feature["implementation_notes"]:
        references = "".join(
            f'<li><span class="badge">{_e(ref["relationship"])}</span> '
            f'<a href="#{anchors[ref["record_id"]]}">{_e(ref["record_id"])}</a> '
            f"<code>{_e(ref['locator'])}</code></li>"
            for ref in note["references"]
        )
        notes.append(
            '<details class="decision"><summary>'
            + _e(note["decision"])
            + "</summary>"
            + f"<p>{_e(note['rationale'])}</p><h4>Applies under these conditions</h4>"
            + _list(note["conditions"])
            + f"<h4>Evidence references</h4><ul>{references}</ul></details>"
        )
    linked = [records[rid] for rid in feature["record_ids"]]
    observations = [record for record in linked if record["kind"] == "catalog-observation"]
    physical = [
        record
        for record in observations
        if record["method"] == "physical-device" and record["data_origin"] != "synthetic-example"
    ]
    physical_note = (
        f"{len(physical)} reported physical-device observation(s); authenticity and review remain scoped."
        if physical
        else "No physical-device observations recorded for this feature."
    )
    evidence = "".join(
        f'<li><a href="#{anchors[record["id"]]}">{_e(_record_label(record))}</a>'
        f'<span class="meta">{_e(_record_kind(record))}</span></li>'
        for record in linked
    )
    plans = "".join(
        f"<details><summary>{_e(plan['question'])}</summary>"
        '<p class="muted">Proposed procedure; no execution result is implied.</p>'
        + _list(plan["procedure"], ordered=True)
        + "<h4>Requested evidence</h4>"
        + _list(plan["requested_evidence"])
        + "</details>"
        for plan in feature["test_plan"]
    )
    actions = "".join(
        f'<a href="{_e(_contribution_url(bundle, feature, template))}">{_e(label)} ↗</a>'
        for template, label in CONTRIBUTIONS
    )
    return (
        f'<section class="feature" id="feature-{index}" aria-labelledby="feature-title-{index}">'
        f'<p class="eyebrow">Feature · {_e(feature["id"])}</p>'
        f'<h2 id="feature-title-{index}">{_e(feature["title"])}</h2>'
        f'<p class="lede">{_e(feature["summary"])}</p>'
        f'<p class="notice">{physical_note}</p><h3>Implementation reasoning</h3>'
        + ("".join(notes) or "<p>No implementation decisions recorded yet.</p>")
        + '<details class="evidence"><summary>Sources &amp; reported observations '
        f"({len(linked)})</summary><ul>{evidence}</ul></details>"
        + ("<h3>Open questions</h3>" + _list(feature["gaps"]) if feature["gaps"] else "")
        + ("<h3>Help test this feature</h3>" + plans if plans else "")
        + '<div class="contribute"><h3>Contribute to this feature</h3>'
        "<p>One source, observation, correction or scoped review is a useful contribution.</p>"
        f'<div class="actions">{actions}</div></div></section>'
    )


def _html(report: dict) -> str:
    bundle, records = report["bundle"], report["records"]
    subject = bundle["subject"]
    anchors = {item["id"]: f"record-{index}" for index, item in enumerate(bundle["records"], 1)}
    navigation = "".join(
        f'<a href="#feature-{index}">{_e(feature["title"])}</a>'
        for index, feature in enumerate(bundle["features"], 1)
    )
    features = "".join(
        _feature_html(bundle, feature, index, records, anchors)
        for index, feature in enumerate(bundle["features"], 1)
    )
    record_details = "".join(
        f'<details class="record" id="{anchors[item["id"]]}"><summary>'
        f'{_e(_record_label(records[item["id"]]))}</summary><p class="meta">'
        f"{_e(records[item['id']]['kind'])} · {_e(item['id'])}</p>"
        + _record_html(records[item["id"]], records)
        + f'<p class="meta">Packaged record: <code>{_e(item["path"])}</code><br>'
        f"Record SHA-256: <code>{_e(item['sha256'])}</code></p></details>"
        for item in bundle["records"]
    )
    reviews = (
        "".join(
            f'<article class="review"><h3>{_e(item["reviewer"])}</h3>'
            f"<p>Declared decision: {_e(item['decision'])} · {_e(item['reviewed_at'])}</p>"
            f"<p>{_e(item['scope'])}</p><p>{_link(item['url'], 'Review discussion ↗')}</p>"
            "<details><summary>Exact records covered by this review</summary><ul>"
            + "".join(
                f"<li>{_e(ref['record_id'])}: <code>{_e(ref['sha256'])}</code></li>"
                for ref in item["record_refs"]
            )
            + "</ul></details></article>"
            for item in bundle["reviews"]
        )
        or "<p>No scoped reviews recorded in this bundle.</p>"
    )
    credits = "".join(
        f'<li><strong>{_e(item["identity"])}</strong><span class="meta">'
        f"{_e(', '.join(item['roles']))}</span><small>Records: "
        f"{_e(', '.join(item['record_ids']) or 'Bundle-level contribution')}</small></li>"
        for item in bundle["credits"]
    )
    history = "".join(
        f"<li><strong>{_e(item['version'])}</strong> · {_e(item['summary'])}</li>"
        for item in bundle["history"]
    )
    provenance = (
        _facts(
            {
                "Catalog revision": report["catalog_revision"],
                "Declared core revision": report.get("declared_core_revision") or "Not recorded",
                "Input digest": report["input_digest"],
            }
        )
        + _json_details(report["generator"], "Generator provenance")
        + _json_details(report["checks"], "Package checks")
    )
    citation = f"{bundle['author']}. {bundle['title']}. {bundle['id']}, version {bundle['version']}."
    identity = _facts(
        {
            "Device": f"{subject['manufacturer']} {subject['model']}",
            "Protocol": subject["protocol"],
            "Firmware": subject["firmware"],
            "Bundle version": bundle["version"],
        }
    )
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_e(bundle["title"])} · EdgeLoom evidence bundle</title>
<meta name="description"
content="Versioned device evidence, implementation reasoning, sources and open tests.">
<meta property="og:type" content="website">
<meta property="og:title" content="{_e(bundle["title"])} · EdgeLoom evidence bundle">
<meta property="og:description"
content="Versioned candidate evidence, implementation reasoning and open tests.">
<meta property="og:url" content="{CATALOG_URL}bundles/{_e(bundle["id"])}/">
<meta property="og:image" content="https://edgeloom-oss.github.io/edgeloom/assets/og-card.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{_e(bundle["title"])} · EdgeLoom evidence bundle">
<meta name="twitter:description"
content="Versioned candidate evidence, implementation reasoning and open tests.">
<meta name="twitter:image" content="https://edgeloom-oss.github.io/edgeloom/assets/og-card.png">
<link rel="stylesheet" href="bundle.css"></head><body>
<a class="skip" href="#main">Skip to evidence</a>
<header><a class="brand" href="{CATALOG_URL}"><span aria-hidden="true">▦</span> EdgeLoom
<span class="brand-label"> / evidence bundle</span></a>
<nav aria-label="Primary"><a href="#sources">Sources</a>
<a href="#participate">Credits &amp; review</a></nav></header>
<main id="main" tabindex="-1"><section class="intro" aria-labelledby="title">
<p class="eyebrow">Device Evidence Bundle · draft format 0.1</p>
<h1 id="title">{_e(bundle["title"])}</h1>
<p class="lede">Follow the evidence behind a device capability, and help fill the gaps.</p>
<p class="badge">Candidate · version {_e(bundle["version"])}</p>{identity}
<details><summary>Identity &amp; applicability</summary>{_facts(subject["identifiers"])}
{_list(subject["scope_notes"])}</details>
<div class="actions downloads" aria-label="Download this version">
<a class="button" href="bundle.zip" download>Download bundle ZIP</a>
<a href="report.md" download>Markdown</a><a href="report.json" download>JSON</a>
<a href="checksums.txt" download>Checksums</a></div>
<p class="muted download-note">The ZIP link is available in the hosted or built report.
An extracted archive already contains these files and does not include another copy of itself.</p></section>
<nav class="feature-nav" aria-label="Capabilities">{navigation}</nav>
<div class="layout"><div>{features}</div><aside aria-labelledby="about-bundle">
<p class="eyebrow">About this version</p><h2 id="about-bundle">An inspectable snapshot</h2>
<p>Read the explanation, inspect its sources, and contribute evidence for a specific feature.</p>
<p class="muted">Candidate publication does not change the review status of any record.</p>
<details><summary>Scope &amp; limits</summary>{_list(bundle["limitations"])}</details>
<details><summary>Cite this bundle</summary><p>{_e(citation)}</p>
<p>Catalog revision: <code>{_e(report["catalog_revision"])}</code></p></details></aside></div>
<section id="sources" class="section" aria-labelledby="sources-title"><p class="eyebrow">Traceable records</p>
<h2 id="sources-title">Sources &amp; evidence</h2>
<p>Expand a record for its scope, citations and complete metadata. Record hashes pin the packaged metadata;
upstream documents and driver code remain at their referenced locations.</p>{record_details}</section>
<section id="participate" class="section" aria-labelledby="participate-title">
<p class="eyebrow">People &amp; progress</p><h2 id="participate-title">Review &amp; contributions</h2>
<div class="comparison-grid"><div><h3>Scoped reviews</h3>{reviews}</div>
<div><h3>Contribution credits</h3><ul class="credits">{credits}</ul></div></div>
<details><summary>Version history</summary><ul>{history}</ul></details></section>
<section class="section" aria-labelledby="integrity-title"><h2 id="integrity-title">Package integrity</h2>
<p>{INTEGRITY_NOTE}</p><details><summary>Build provenance &amp; checks</summary>
{provenance}</details></section>
</main><footer>EdgeLoom · Device Evidence Bundle draft v0.1 · {_e(bundle["license"])}
catalog-authored records.
Third-party sources retain their own terms. This portable report works without network access;
upstream and contribution links require a connection.</footer></body></html>
'''


def _markdown(report: dict) -> str:
    bundle, records = report["bundle"], report["records"]
    subject = bundle["subject"]
    lines = [
        f"# {_md(bundle['title'])}",
        "",
        f"Candidate · version {_md(bundle['version'])}",
        "",
        f"Bundle: {_md(bundle['id'])} · draft format 0.1",
        "",
        f"Device: {_md(subject['manufacturer'])} {_md(subject['model'])}",
        f"Protocol: {_md(subject['protocol'])} · Firmware: {_md(subject['firmware'])}",
        "",
        "## Applicability",
        "",
        *[f"- {_md(v)}" for v in subject["scope_notes"]],
        "",
    ]
    for feature in bundle["features"]:
        lines += [f"## {_md(feature['title'])}", "", _md(feature["summary"]), ""]
        for note in feature["implementation_notes"]:
            lines += [f"### {_md(note['decision'])}", "", _md(note["rationale"]), "", "Conditions:", ""]
            lines += [f"- {_md(value)}" for value in note["conditions"]]
            lines += ["", "Evidence references:", ""]
            lines += [
                f"- {_md(ref['relationship'])}: {_md(ref['record_id'])} {_md(ref['locator'])}"
                for ref in note["references"]
            ]
            lines += [""]
        observations = [
            records[rid] for rid in feature["record_ids"] if records[rid]["kind"] == "catalog-observation"
        ]
        if not any(
            o["method"] == "physical-device" and o["data_origin"] != "synthetic-example" for o in observations
        ):
            lines += ["No physical-device observations recorded for this feature.", ""]
        lines += ["Linked records: " + _md(", ".join(feature["record_ids"])), "", "### Open questions", ""]
        lines += [f"- {_md(value)}" for value in feature["gaps"]] or ["None listed."]
        for plan in feature["test_plan"]:
            lines += [
                "",
                f"### Proposed test: {_md(plan['question'])}",
                "",
                "Proposed procedure; no execution result is implied.",
                "",
            ]
            lines += [f"{i}. {_md(value)}" for i, value in enumerate(plan["procedure"], 1)]
            lines += ["", "Requested evidence:", ""]
            lines += [f"- {_md(value)}" for value in plan["requested_evidence"]]
        lines += ["", "### Contribute to this feature", ""]
        lines += [
            f"- {_md_link(_contribution_url(bundle, feature, template), label)}"
            for template, label in CONTRIBUTIONS
        ]
        lines += [""]
    lines += ["## Sources and evidence", ""]
    for item in bundle["records"]:
        record = records[item["id"]]
        lines += [
            f"### {_md(_record_label(record))}",
            "",
            f"Kind: {_md(record['kind'])}",
            "",
            f"Record ID: {_md(item['id'])} · Path: {_md(item['path'])}",
            f"Record SHA-256: {_md(item['sha256'])}",
            "",
        ]
        if record["kind"] == "catalog-observation":
            lines += [
                _observation_label(record),
                "",
                f"Reported outcome: {_md(record['outcome'])}",
                f"Expected: {_md(record['expected'])}",
                f"Observed: {_md(record['observed'])}",
                "",
            ]
        elif record["kind"] == "document-source":
            lines += [
                _md_link(record["url"], "Upstream document"),
                "",
                f"Declared applicability: {_md(record['applicability']['scope'])}",
                f"Capture: {_md(record['capture']['mode'])}; source bytes are not included.",
                "",
            ]
        elif record["kind"] == "source-manifest":
            lines += [_md_link(record["repository"]["url"], "Upstream repository"), ""]
            lines += [
                f"- {_md_link(_artifact_link(record, artifact), artifact['path'])}"
                for artifact in record["artifacts"]
            ]
            lines += ["", "Referenced driver code is not included or executed by this bundle.", ""]
        # Indented code is inert even when a contributed string contains fence markers or HTML.
        lines += (
            ["Complete record:", ""]
            + [
                "    " + line
                for line in json.dumps(record, indent=2, ensure_ascii=False, sort_keys=True).splitlines()
            ]
            + [""]
        )
    lines += ["## Reviews", "", "Review entries are scoped declarations, not authentication.", ""]
    if not bundle["reviews"]:
        lines += ["No scoped reviews recorded in this bundle.", ""]
    for review in bundle["reviews"]:
        lines += [
            f"- {_md(review['reviewer'])}: {_md(review['decision'])} · {_md(review['reviewed_at'])}",
            "",
            _md(review["scope"]),
            "",
            _md_link(review["url"], "Review discussion"),
            "",
        ]
        lines += [f"  - {_md(ref['record_id'])}: {_md(ref['sha256'])}" for ref in review["record_refs"]]
        lines += [""]
    lines += ["## Credits", ""]
    lines += [
        f"- {_md(credit['identity'])}: {_md(', '.join(credit['roles']))}; "
        f"records: {_md(', '.join(credit['record_ids']) or 'Bundle-level contribution')}"
        for credit in bundle["credits"]
    ]
    lines += ["", "## Version history", ""]
    lines += [f"- {_md(item['version'])}: {_md(item['summary'])}" for item in bundle["history"]]
    lines += ["", "## Scope and limits", ""] + [f"- {_md(value)}" for value in bundle["limitations"]]
    lines += [
        "",
        "## Package integrity",
        "",
        INTEGRITY_NOTE,
        "",
        f"Catalog revision: {_md(report['catalog_revision'])}",
        f"Declared core revision: {_md(report.get('declared_core_revision') or 'Not recorded')}",
        f"Input digest: {_md(report['input_digest'])}",
        "",
        f"License: {_md(bundle['license'])} for catalog-authored records; upstream terms remain separate.",
        "",
        "See report.json for complete generator and package-check metadata.",
        "",
    ]
    return "\n".join(lines)


def generated_files(report: dict) -> dict[str, str]:
    """Render a validated report without fetching sources or executing driver code."""
    return {
        "index.html": _html(report),
        "report.md": _markdown(report),
        "bundle.css": (Path(__file__).parent / "catalog_assets" / "bundle.css").read_text(encoding="utf-8"),
    }
