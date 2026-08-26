"""Lint the EdgeLoom static site and check its internal or public links."""

from __future__ import annotations

import argparse
import json
import ssl
import sys
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urljoin, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
INDEX = SITE / "index.html"
USER_AGENT = "EdgeLoom site link checker/1.0"


class SiteParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: set[str] = set()
        self.references: list[tuple[str, str]] = []
        self.meta: set[tuple[str, str]] = set()
        self.h1_count = 0
        self.main_count = 0
        self.images_without_alt: list[str] = []
        self.heading_levels: list[int] = []
        self.json_ld: list[str] = []
        self._json_buffer: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if element_id := values.get("id"):
            if element_id in self.ids:
                raise ValueError(f"duplicate id: {element_id}")
            self.ids.add(element_id)
        if tag == "a" and values.get("href"):
            self.references.append(("href", values["href"] or ""))
        if tag in {"img", "script"}:
            if values.get("src"):
                self.references.append(("src", values["src"] or ""))
        if tag == "link" and values.get("rel") in {"stylesheet", "icon"} and values.get("href"):
            self.references.append(("href", values["href"] or ""))
        if tag == "img" and "alt" not in values:
            self.images_without_alt.append(values.get("src", "<unknown>"))
        if tag == "meta":
            key = values.get("name") or values.get("property")
            if key and values.get("content"):
                self.meta.add((key, values["content"] or ""))
        if tag == "h1":
            self.h1_count += 1
        if len(tag) == 2 and tag[0] == "h" and tag[1].isdigit():
            self.heading_levels.append(int(tag[1]))
        if tag == "main":
            self.main_count += 1
        if tag == "script" and values.get("type") == "application/ld+json":
            self._json_buffer = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._json_buffer is not None:
            self.json_ld.append("".join(self._json_buffer))
            self._json_buffer = None

    def handle_data(self, data: str) -> None:
        if self._json_buffer is not None:
            self._json_buffer.append(data)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lint", action="store_true", help="Check document, CSS, and metadata quality")
    parser.add_argument("--links", action="store_true", help="Check internal links and fragments")
    parser.add_argument("--external", action="store_true", help="Also request public HTTP(S) links")
    return parser.parse_args()


def parse_site() -> SiteParser:
    parser = SiteParser()
    parser.feed(INDEX.read_text(encoding="utf-8"))
    parser.close()
    return parser


def lint(parser: SiteParser) -> list[str]:
    errors: list[str] = []
    html = INDEX.read_text(encoding="utf-8")
    css = (SITE / "styles.css").read_text(encoding="utf-8")
    required_meta = {
        "description",
        "og:title",
        "og:description",
        "og:url",
        "og:image",
        "twitter:card",
        "twitter:title",
        "twitter:description",
        "twitter:image",
    }
    present_meta = {name for name, _ in parser.meta}

    if not html.lower().startswith("<!doctype html>"):
        errors.append("index.html must start with the HTML5 doctype")
    if '<html lang="en">' not in html:
        errors.append("index.html must declare lang=en")
    if parser.h1_count != 1:
        errors.append(f"expected exactly one h1, found {parser.h1_count}")
    if parser.main_count != 1:
        errors.append(f"expected exactly one main landmark, found {parser.main_count}")
    if parser.images_without_alt:
        errors.append(f"images missing alt: {', '.join(parser.images_without_alt)}")
    if missing := sorted(required_meta - present_meta):
        errors.append(f"missing metadata: {', '.join(missing)}")
    for previous, current in zip(parser.heading_levels, parser.heading_levels[1:]):
        if current > previous + 1:
            errors.append(f"heading level jumps from h{previous} to h{current}")
    for payload in parser.json_ld:
        try:
            json.loads(payload)
        except json.JSONDecodeError as exc:
            errors.append(f"invalid JSON-LD: {exc}")
    if css.count("{") != css.count("}"):
        errors.append("styles.css has unbalanced braces")
    for path in SITE.rglob("*"):
        if path.is_file() and path.suffix in {".html", ".css", ".js", ".txt", ".xml"}:
            for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if line.rstrip() != line:
                    errors.append(f"{path.relative_to(ROOT)}:{line_number} has trailing whitespace")
    return errors


def local_target(reference: str) -> tuple[Path | None, str | None]:
    parsed = urlparse(reference)
    if parsed.scheme or reference.startswith("//"):
        return None, None
    path_text = unquote(parsed.path)
    target = INDEX if path_text in {"", ".", "./"} else (SITE / path_text).resolve()
    if target.is_dir():
        target /= "index.html"
    return target, parsed.fragment or None


def check_local_links(parser: SiteParser) -> tuple[list[str], set[str]]:
    errors: list[str] = []
    external: set[str] = set()
    site_root = SITE.resolve()
    for _, reference in parser.references:
        if reference.startswith(("mailto:", "tel:", "data:")):
            continue
        parsed = urlparse(reference)
        if parsed.scheme in {"http", "https"}:
            external.add(reference)
            continue
        target, fragment = local_target(reference)
        if target is None:
            continue
        try:
            target.relative_to(site_root)
        except ValueError:
            errors.append(f"local reference escapes site/: {reference}")
            continue
        if not target.is_file():
            errors.append(f"missing local target: {reference}")
        if fragment and target == INDEX and fragment not in parser.ids:
            errors.append(f"missing fragment #{fragment}")
    return errors, external


def request_url(url: str) -> tuple[str, str | None]:
    request = Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
    context = ssl.create_default_context()
    try:
        with urlopen(request, timeout=15, context=context) as response:
            if response.status >= 400:
                return url, f"HTTP {response.status}"
    except HTTPError as exc:
        if exc.code in {401, 403, 405, 429}:
            return url, None
        return url, f"HTTP {exc.code}"
    except (URLError, TimeoutError) as exc:
        return url, str(exc.reason if isinstance(exc, URLError) else exc)
    return url, None


def check_external_links(urls: set[str]) -> list[str]:
    canonical = sorted({urljoin(url, "") for url in urls})
    errors: list[str] = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        for url, error in executor.map(request_url, canonical):
            if error:
                errors.append(f"{url}: {error}")
    return errors


def main() -> None:
    args = parse_args()
    if not args.lint and not args.links:
        args.lint = args.links = True
    parser = parse_site()
    errors: list[str] = []
    if args.lint:
        errors.extend(lint(parser))
    if args.links:
        local_errors, external = check_local_links(parser)
        errors.extend(local_errors)
        if args.external:
            errors.extend(check_external_links(external))
            print(f"Checked {len(external)} public links")
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
    print("Site checks passed")


if __name__ == "__main__":
    main()
