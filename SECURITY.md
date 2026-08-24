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
  By default the generator writes the token into the produced
  `config/ha_devices.yaml` so the Edge driver can authenticate. That file is
  created mode `0600`, readable only by its owner, and the generated output
  directory is gitignored — but it is still a secret, so keep it out of version
  control. Pass `--no-token` to leave the token out of the file entirely and
  supply `HA_EDGE_TOKEN` on the hub instead; the Edge driver prefers that
  environment variable over the file either way.
- **Discovery talks to the GitHub API.** Supply `GITHUB_TOKEN` for rate limits
  only; it needs no write scope.

Findings about *these* documented behaviours are welcome as regular issues.
Report privately anything that goes further — credential leakage beyond the
above, code execution, or a patch path that escapes the target driver directory.

## Research disclosure

The hidden-attribute vulnerability class this tooling accompanies was disclosed
to affected vendors and published at ACM CCS 2025. See
[How to Cite](README.md#how-to-cite).
