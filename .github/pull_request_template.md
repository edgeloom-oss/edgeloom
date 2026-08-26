## Summary

<!-- High-level description of the change. -->

## User / Ecosystem Impact

<!-- Who benefits, what changes for them, and any compatibility or migration impact. -->

## Testing

- [ ] `make test` (or `python -m pytest tests/ translator/tests/`)
- [ ] `make lint` (`ruff check .`)
- [ ] `ruff format --check .`
- [ ] `edgeloom validate` passes on any profile, capability-map, or evidence-record change
- [ ] Other (describe):

## Checklist

- [ ] Added/updated documentation, or not applicable (explain)
- [ ] Added/updated tests, or not applicable (explain)
- [ ] Preserved compatibility, or documented the migration/breaking change
- [ ] Reviewed effects on credentials, untrusted inputs, generated code, and filesystem writes
- [ ] Updated `CHANGELOG.md` under Unreleased, or not user-facing
- [ ] Linked the design discussion for a substantial change, or not applicable

## Security and Trust Boundaries

<!-- Describe any effect on untrusted drivers or remote responses, credentials,
generated Lua/YAML, filesystem paths, schemas, GitHub workflows, or releases.
Write "No change" when none apply. Do not disclose an unpatched vulnerability. -->

## Screenshots / Demo (optional)

<!-- Attach any helpful output, logs, or screenshots. -->
