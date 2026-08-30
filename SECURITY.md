# Security Policy

## Supported versions

EdgeLoom is pre-1.0. Security fixes land on `main` and ship in the next release;
older releases are not backported.

| Version | Supported |
| --- | --- |
| 0.1.x | Yes |
| < 0.1 | No |

## Reporting a vulnerability

**Please do not open a public issue for a security problem.**

Report privately through
[GitHub Security Advisories](https://github.com/edgeloom-oss/edgeloom/security/advisories/new),
or by email to Chenglong Fu at `chenglong.fu@charlotte.edu` with `EdgeLoom
security` in the subject.

Please include the affected version or commit, what an attacker gains, the steps
or input needed to reproduce it, and any hub, driver, or device involved.

You can expect acknowledgement within 5 working days and an initial assessment
within 10. We will keep you updated at least every two weeks until the report is
closed, and will credit you in the advisory and CHANGELOG unless you ask us not
to. We ask that you give us 90 days before public disclosure, and we will tell
you if a fix will take longer.

## Scope

In scope: the `edgeloom` package and CLI, the patching, translation, discovery,
and validation logic, the published schemas, and the packaging and release
pipeline.

Out of scope: vulnerabilities in SmartThings, Home Assistant, or vendor
firmware, which should go to those vendors; and the intended behaviour described
below.

## What EdgeLoom trusts

This section exists because an outside reporter found that it was missing, and
because getting it wrong produced a real vulnerability (GHSA-4f7m-wgh7-46xf).

**A driver you point EdgeLoom at is untrusted input.** Its `fingerprints.yml`,
its `profiles/*.yml`, its `src/*.lua`, and its directory structure — including
whether any of those are symlinks — are authored by whoever published that
driver. EdgeLoom's whole premise is patching a driver obtained from elsewhere,
so this is the primary path, not an unusual one. Values read out of a driver
never become filesystem paths, generated code, or unbounded work without a
check. Findings here are in scope and should be reported privately.

**A driver's own Lua is not vetted.** EdgeLoom copies `src/*.lua` through
byte-identical and the hub executes it. A malicious driver already runs
arbitrary Lua on your hub whether or not you patch it; EdgeLoom neither adds to
nor mitigates that. Review a driver before installing it, exactly as you would
without this tool. This is a limit of the tool, not a vulnerability in it.

**Remote responses are untrusted.** `discover` reads whatever repository you
point it at, and the translator reads whatever your Home Assistant instance
returns. Neither is assumed well-formed or well-intentioned.

**Audited documents and schemas are untrusted.** `audit` hashes arbitrary local
regular files and parses JSON/YAML only after an 8 MiB size gate, then applies
the shared depth and expanded-node bounds. For parsed artifacts, hashing and
parsing use one byte snapshot; a file that changes during the read is rejected.
A schema supplied with `--schema` is validated as Draft 2020-12 before use. The
command never follows schema URLs, resolves non-local references, or sends the
artifact elsewhere. Its source URI, revision, license, maturity, and schema
authority fields are operator assertions rather than authenticated facts.
Schema checks run in-process: size, depth, node, and reported-error bounds
reduce resource risk but do not impose a hard time limit on every adversarial
schema expression. Evaluate an untrusted third-party schema in a disposable
environment.

**The operator is trusted.** Command-line arguments, `--config` files, and the
`--output` path are the operator's own. A finding whose only attacker is the
person running the tool on their own machine is a robustness bug, not a
vulnerability — they can edit the driver directly.

**The hub and the SmartThings account are out of scope.** EdgeLoom never
packages or installs anything; you do that separately.

## What this tool does by design

EdgeLoom exists to make device attributes visible that a stock driver hides.
That is the point of the research it accompanies, not a flaw in the tool:

- **Patching rewrites a driver you install on your own hub.** It changes what
  the device exposes to your account. Review the diff before installing on a hub
  you depend on. Every run backs the driver up first and restores that backup if
  a step fails.
- **The translator handles Home Assistant credentials.** A long-lived access
  token is a bearer credential for your entire HA instance. Pass it via
  `HA_TOKEN` rather than on the command line, where it lands in shell history.
  The generator writes the token into the produced `config/ha_devices.yaml` so
  the Edge driver can authenticate; that file is written with owner-only
  permissions (`0600`). Prefer keeping the token out of the file entirely with
  `translate --no-token` and supplying `HA_EDGE_TOKEN` on the hub instead —
  treat any copy of `ha_devices.yaml` as a secret and keep it out of version
  control.
- **Discovery talks to the GitHub API.** Supply `GITHUB_TOKEN` for rate limits
  only; it needs no write scope.

Findings about *these* documented behaviours are welcome as regular issues.
Report privately anything that goes further — credential leakage beyond the
above, code execution, or a patch path that escapes the target driver directory.

## Research disclosure

The hidden-attribute vulnerability class this tooling accompanies was disclosed
to affected vendors and published at ACM CCS 2025. See
[How to Cite](README.md#how-to-cite).
