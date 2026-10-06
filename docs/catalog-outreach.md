# Catalog pilot outreach — draft, not posted

Use only after the browser snapshot and feedback form are merged and their
public links read back. Start with SmartThings driver developers/maintainers;
this pilot is not a driver-installation solution for general smart-home users.
Check the target forum's current rules before posting. No outreach, endorsement
or independent use is evidenced by this draft.

## Suggested first post

**Can we make missing SmartThings driver features easier to inspect?**

We're building EdgeLoom, an open-source toolchain for inspecting smart-home
driver artifacts. Its new evidence catalog starts with one Yale YRD156 case:
auto-relock duration, lock-state events, and access identity.

Each report links fixed source versions, shows what we checked, and keeps
uncertainty visible. For example, an auto-relock parameter is described in a
community configuration but absent from the particular profile/model we
examined. That does **not** prove the complete driver or SmartThings UI lacks
the setting.

These are founder-authored candidate findings, not independently reviewed or
hardware-validated results. The catalog does not install or automatically patch
this Z-Wave lock. A separate disposable Zigbee source demo exercises
patch/validate/restore without a hub.

Does the finding match your driver version or device? We would value a
correction or review of one specific assertion. No mapping authoring is needed;
please remove access codes, credentials and private identifiers from feedback.

- Device report (planned URL): https://edgeloom-oss.github.io/edgeloom/catalog/devices/yale-yrd156/#auto-relock
- Dataset: https://github.com/edgeloom-oss/edgeloom-catalog
- Toolchain: https://github.com/edgeloom-oss/edgeloom

Disclose that the poster is a project founder/maintainer. For broader Reddit
outreach, first obtain real external feedback, expand the distinct-device
inventory and publish/install-test the new tooling. Stars or page views are
not adoption evidence. Standards outreach should use the bounded model gap
and evidence report, not a claim that RFC 9880/SDF is defective.
