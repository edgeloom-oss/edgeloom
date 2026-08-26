# Project homepage

The EdgeLoom homepage is a dependency-free static site under `site/`. Keeping it
separate from the Python package makes the publishing boundary explicit and
lets GitHub Pages serve the files without introducing a JavaScript framework or
runtime dependency.

## Work locally

```bash
make site-check
python3 -m http.server 4173 --directory site
```

Open `http://127.0.0.1:4173/`. To check public links as well as local assets and
fragments, run `make site-links`. The public-link check requires network access
and is intentionally kept out of CI to avoid third-party availability causing a
project build failure.

The generated output goes to `_site/` by default and is ignored by Git. Override
it when needed with `make site-build SITE_OUTPUT=/path/to/output`.

## Maintain factual claims

The homepage intentionally links each project-health claim to GitHub, PyPI, or
the public security advisory. Before changing the release count, version,
verification date, CI status, contributor wording, or security wording, check
the current public source. Do not add adoption, partnership, certification, or
user-scale claims without public evidence.

The research figure is reproduced from the CCS 2025 paper under CC BY 4.0. Its
caption distinguishes research results from EdgeLoom's current implementation
coverage. Preserve that distinction when editing the research section.

## Preview metadata

Canonical, Open Graph, X card, JSON-LD, `robots.txt`, and `sitemap.xml` values
assume the standard project Pages URL:

`https://edgeloom-oss.github.io/edgeloom/`

If the project adopts a custom domain, update all of those values together. The
social card lives at `site/assets/og-card.png` and is 1200 by 630 pixels.

## Publish with GitHub Pages

The workflow in `.github/workflows/pages.yml` is manual-only. Adding the file
does not enable Pages and does not deploy the site.

After the homepage branch is reviewed and merged:

1. In repository settings, open **Pages** and select **GitHub Actions** as the
   source.
2. Open **Actions**, choose **Build and deploy project site**, and run the
   workflow from `main`.
3. Verify the reported Pages URL, navigation, social metadata, and both desktop
   and mobile layouts.

Keep the workflow manual until the maintainers explicitly decide that merges to
`main` should publish automatically.
