# Development

Quality gates, container workflow, and how CI runs them.

## Testing & Validation

Run quality checks locally with:

```bash
make lint
make test
```

Validate both shipped toolchain artifacts and the synthetic catalog-contract
fixtures with:

```bash
make validate
```

Catalog validation in this first contract slice is intentionally offline. It
does not fetch a source repository or resolve artifact IDs across separate
manifest files; see [Catalog Contracts](catalog-contracts.md).

GitHub Actions (`.github/workflows/ci.yml`) runs the exact commands on every PR
and on the `main`/`master` branches.

## Containerized Development

Build the reusable image (installs all dev dependencies):

```bash
make docker-build
```

Drop into a shell with the repo bind-mounted, ready to run scripts:

```bash
make docker-shell
# inside container
make test
```

Or execute the QA suite headlessly:

```bash
make docker-test
```

You can also use `docker compose run --rm dev bash` directly if you prefer the
Compose workflow. The container automatically honors `GITHUB_TOKEN`, making it
easy to run the discovery pipeline against the public SmartThings repos without
throttling.
