"""Small, accessible, buildless views derived from the canonical report index."""

from __future__ import annotations

from html import escape
from pathlib import Path
from string import Template
from urllib.parse import quote

from edgeloom.catalog import device_markdown, read_bytes, render_json

ASSETS = Path(__file__).parent / "catalog_assets"
CATALOG_URL = "https://edgeloom-oss.github.io/edgeloom/catalog/"


def _e(value: object) -> str:
    return escape(str(value), quote=True)


def _list(items: list[str]) -> str:
    return "<ul>" + "".join(f"<li>{_e(item)}</li>" for item in items) + "</ul>"


def _template(template_name: str, **values: object) -> str:
    return Template(read_bytes(ASSETS, template_name).decode()).substitute(values)


def _bundle_links(bundles: list[dict], prefix: str = "") -> str:
    if not bundles:
        return ""
    links = "".join(
        f'<li><a href="{prefix}bundles/{_e(bundle["id"])}/">{_e(bundle["title"])}</a> '
        f'<span class="state">v{_e(bundle["version"])} · {_e(bundle["publication_status"])}</span> '
        f'<a href="{prefix}bundles/{_e(bundle["id"])}/bundle.zip" download>Download package</a></li>'
        for bundle in bundles
    )
    return (
        '<section class="feature" aria-label="Device evidence bundles">'
        '<p class="eyebrow">Versioned evidence packages</p><h2>Follow the implementation decisions</h2>'
        "<p>Read document citations, implementation explanations, reported observations and open "
        "questions. A candidate package records available evidence and its limits.</p>"
        f'<ul class="feature-links">{links}</ul></section>'
    )


def _layout(title: str, description: str, content: str, index: dict, prefix="./", path="") -> str:
    revision = index["catalog_revision"]
    revision_link = (
        f'<a href="{_e(index["catalog_repository"])}/tree/{revision}">{revision[:12]}</a>'
        if revision != "working-tree"
        else "working-tree export (not commit-pinned)"
    )
    return _template(
        "page.html",
        title=_e(title),
        description=_e(description),
        canonical=CATALOG_URL + path,
        prefix=prefix,
        content=content,
        revision=revision_link,
        input_digest=index["input_digest"],
        generator_digest=index["generator"]["implementation_digest"],
        core_pin=index["generator"]["declared_core_revision"] or "not recorded",
        source_bytes=_e(index["checks"]["source_bytes"]),
        limitations=_list(index["limitations"]),
    )


def index_html(index: dict) -> str:
    cards = []
    mappings = {item["id"]: item for item in index["mapping_sets"]}
    corroborations = {item["id"]: item for item in index["corroborations"]}
    for device in index["devices"]:
        name = f"{device['manufacturer']} {device['model']}"
        statuses = sorted(
            {
                mappings[mid]["review"]["lifecycle"]
                for feature in device["features"]
                for mid in feature["mapping_ids"]
            }
            | {
                corroborations[cid]["review"]["lifecycle"]
                for feature in device["features"]
                for cid in feature.get("corroboration_ids", [])
            }
        )
        keywords = " ".join(
            [
                name,
                device["protocol"],
                "Z-Wave" if device["protocol"] == "zwave" else "Zigbee",
                *device["identifiers"].values(),
                *[feature["title"] + " " + feature["summary"] for feature in device["features"]],
                *[
                    observation["platform"] + " " + observation["claim"]
                    for feature in device["features"]
                    for cid in feature.get("corroboration_ids", [])
                    for observation in corroborations[cid]["observations"]
                ],
            ]
        )
        features = "".join(
            f'<li><a href="devices/{device["id"]}/#{feature["id"]}">{_e(feature["title"])} '
            '<span aria-hidden="true">↗</span></a></li>'
            for feature in device["features"]
        )
        features += "".join(
            f'<li><a href="bundles/{_e(bundle["id"])}/">Evidence bundle '
            f'v{_e(bundle["version"])} <span aria-hidden="true">↗</span></a></li>'
            for bundle in index.get("bundles", [])
            if bundle["device_record_id"] == device["id"]
        )
        hardware = (
            "Hardware observations linked; not authenticated"
            if device["hardware_evidence"]
            else "No hardware evidence recorded"
        )
        cards.append(f'''<article class="device-card" data-device data-search="{_e(keywords.casefold())}"
data-protocol="{device["protocol"]}" data-status="{" ".join(statuses)}">
<div class="card-top"><span class="eyebrow">{device["protocol"]} · device evidence</span>
<span class="badge">{_e(", ".join(statuses))}</span></div>
<h2><a href="devices/{device["id"]}/">{_e(name)}</a></h2>
<p>Inspect what the published artifacts describe, expose, and leave unresolved.</p>
<ul class="feature-links">{features}</ul>
<div class="card-bottom"><span>{hardware}</span>
<a href="devices/{device["id"]}/">Open report <span aria-hidden="true">→</span></a></div></article>''')
    content = _template("index.html", **index["counts"], cards="\n".join(cards))
    content += _bundle_links(index.get("bundles", []))
    return _layout(
        "Device evidence",
        "Inspect source-linked smart-home driver features, mapping gaps, and evidence limits. "
        "An early candidate catalog, not a compatibility guarantee.",
        content,
        index,
    )


def device_html(index: dict, device: dict) -> str:
    name = f"{device['manufacturer']} {device['model']}"
    mappings = {item["id"]: item for item in index["mapping_sets"]}
    corroborations = {item["id"]: item for item in index["corroborations"]}
    identity = device["identity_evidence"]
    source = next(item for item in index["sources"] if item["id"] == identity["manifest_id"])
    artifact = next(item for item in source["artifacts"] if item["id"] == identity["artifact_id"])
    sections = [
        _bundle_links(
            [bundle for bundle in index.get("bundles", []) if bundle["device_record_id"] == device["id"]],
            "../../",
        )
    ]
    for feature in device["features"]:
        conclusions, details = [], []
        for mid in feature["mapping_ids"]:
            mapping = mappings[mid]
            assertion_details = []
            for assertion in mapping["mappings"]:
                label = {
                    "one-to-one": "Bounded match",
                    "lossy": "Information loss",
                    "ambiguous": "Unresolved correspondence",
                    "unbound": "No binding established",
                }[assertion["classification"]]
                label = {
                    "platform-not-exposed": "Not in the examined profile",
                    "neutral-model-missing": "Not in the examined SDF model",
                }.get(assertion.get("unbound_reason"), label)
                state = _e(mapping["review"]["lifecycle"])
                directions = _e(", ".join(assertion["directions"]))
                limits = _list(assertion.get("limitations", []))
                conclusions.append(f"""<div class="finding"><span class="badge">{_e(label)}</span>
<span class="state">{state} · {directions}</span></div>""")
                assertion_details.append(
                    f"<p><strong>{_e(assertion['id'])}</strong>: "
                    f"{_e(assertion['classification'])} · {directions}</p>{limits}"
                )
            evidence = []
            for item in mapping["evidence"]:
                check = next(row for row in mapping["locator_checks"] if row["id"] == item["id"])
                evidence.append(f'''<li><p>{_e(item["summary"])}</p>
<a href="{_e(check["url"])}">Pinned source ↗</a> <code>{_e(check["locator"])}</code>
<span class="locator-state">Locator: {_e(check["status"])}</span></li>''')
            revision = index["catalog_revision"]
            ref = revision if revision != "working-tree" else "main"
            url = f"{index['catalog_repository']}/blob/{ref}/{quote(mapping['path'], safe='/')}"
            review = mapping["review"]
            details.append(f'''<div class="mapping-detail"><h3>{_e(mapping["title"])}</h3>
<p>Declared lifecycle: {_e(review["lifecycle"])}. Author: {_e(review["author"])}.
{_e(review.get("notes", ""))}</p><p><a href="{_e(url)}">Mapping record ↗</a> ·
SHA-256: <code>{mapping["sha256"]}</code></p>{_list(mapping.get("limitations", []))}
{"".join(assertion_details)}
<ul class="evidence-list">{"".join(evidence)}</ul></div>''')
        comparisons = []
        for cid in feature.get("corroboration_ids", []):
            record = corroborations[cid]
            observations, evidence = [], []
            for observation in record["observations"]:
                match = (
                    "; ".join(
                        f"{key}: {value}" for key, value in observation.get("identity_match", {}).items()
                    )
                    or "Generic platform path; not a model-specific result"
                )
                observations.append(f"""<article class="observation">
<h3>{_e(observation["platform"])}</h3>
<p class="state">{_e(observation["relationship"])} · {_e(observation["evidence_kind"])}</p>
<p>{_e(observation["claim"])}</p>
<p class="identity-match">Declared match: {_e(match)}</p></article>""")
                links = "".join(
                    f'<li><a href="{_e(check["url"])}">Pinned source ↗</a> '
                    f"<code>{_e(check['locator'])}</code> "
                    f'<span class="locator-state">Locator: {_e(check["status"])}</span></li>'
                    for check in observation["locator_checks"]
                )
                evidence.append(
                    f"<h4>{_e(observation['platform'])}</h4>"
                    f"{_list(observation['conditions'])}<ul>{links}</ul>"
                )
            lineage = _list(
                [
                    f"{row['manifest_id']} · family: {row['family']} · depends on: "
                    + (", ".join(row["depends_on"]) or "none declared in this record")
                    for row in record["lineage"]
                ]
            )
            ref = index["catalog_revision"]
            ref = ref if ref != "working-tree" else "main"
            url = f"{index['catalog_repository']}/blob/{ref}/{quote(record['path'], safe='/')}"
            comparisons.append(f'''<div class="comparison">
<p class="eyebrow">External corroboration · candidate</p><h3>{_e(record["title"])}</h3>
<p>{_e(record["summary"])}</p>
<div class="comparison-grid">{"".join(observations)}</div>
<details><summary>Pinned sources, conditions &amp; declared lineage</summary>
<p>Curator: {_e(record["review"]["author"])}. No independent EdgeLoom reviewer recorded.
<a href="{_e(url)}">Canonical record ↗</a></p>
{"".join(evidence)}<h4>Source lineage — not an independence score</h4>{lineage}
{_list(record["limitations"])}</details></div>''')
        mapping_panel = (
            "<details><summary>Mapping evidence, source links &amp; scope boundaries</summary>"
            + "".join(details)
            + "</details>"
            if details
            else ""
        )
        sections.append(f'''<section id="{feature["id"]}" class="feature">
<p class="eyebrow">Feature evidence</p><h2>{_e(feature["title"])}</h2>
<p class="feature-summary">{_e(feature["summary"])}</p>{"".join(conclusions)}
{"".join(comparisons)}
<div class="next"><h3>What you can do next</h3>{_list(feature["next_steps"])}</div>
{mapping_panel}</section>''')
    navigation = "".join(
        f'<a href="#{feature["id"]}">{_e(feature["title"])}</a>' for feature in device["features"]
    )
    title = quote(f"[Device observation] {name}")
    feedback = (
        "https://github.com/edgeloom-oss/edgeloom-catalog/issues/new"
        f"?template=device-observation.yml&title={title}"
    )
    hardware = "Reported links; not authenticated" if device["hardware_evidence"] else "None recorded"
    content = _template(
        "device.html",
        protocol=device["protocol"],
        name=_e(name),
        id=device["id"],
        identifiers=_e(" / ".join(device["identifiers"].values())),
        identity_url=_e(artifact["url"]),
        firmware=_e(device["firmware"]),
        hardware=hardware,
        source_bytes=_e(index["checks"]["source_bytes"]),
        feedback=_e(feedback),
        navigation=navigation,
        sections="\n".join(sections),
        limitations=_list(device["limitations"]),
        hardware_links=_list(device["hardware_evidence"]),
    )
    return _layout(
        name,
        f"Source-linked feature evidence for {name}. Read findings, limits, and pinned sources; "
        "no hardware test or automatic patch is implied.",
        content,
        index,
        "../../",
        f"devices/{device['id']}/",
    )


def generated_files(index: dict) -> dict[str, str]:
    files = {
        "catalog.json": render_json(index),
        "index.html": index_html(index),
        "styles.css": read_bytes(ASSETS, "styles.css").decode(),
        "script.js": read_bytes(ASSETS, "script.js").decode(),
    }
    for device in index["devices"]:
        files[f"devices/{device['id']}/index.html"] = device_html(index, device)
        files[f"reports/{device['id']}.md"] = device_markdown(index, device)
    return files
