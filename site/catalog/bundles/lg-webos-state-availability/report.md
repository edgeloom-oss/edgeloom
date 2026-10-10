# LG webOS TV family: power, availability and screen state

Candidate · version 0\.1\.0

Bundle: lg\-webos\-state\-availability · schema 0\.2 · archive format 0.1

Device: LG webOS TVs \(integration family\)
Protocol: ip · Firmware: unknown

## Applicability

- Source\-only Home Assistant integration\-family case\. No physical TV was inspected, and no exact G2 or other model qualification is claimed\.
- Client fields, platform entity state, availability and screen state are separate layers\.
- No LG manufacturer manual, device telemetry, SDF mapping or independent review is included\.

## Declared integration context

- Identity scope: device\-family \(source\-declared, not proof of physical identity\)
- Category: media
- Home Assistant Core / webostv · platform version: 2026\.10\.0
- Transport: unknown · application protocol/API: LG webOS API via aiowebostv \(wire\-level behavior not traced\)
- Access: local · data updates: push · basis: source\-declared
- Evidence: ha\-webostv\-6a811d3/webostv\-manifest @ /iot\_class
- Evidence: ha\-webostv\-6a811d3/webostv\-manifest @ /requirements/0
- Evidence: ha\-webostv\-6a811d3/webostv\-coordinator @ WebOsTvDataUpdateCoordinator\.\_async\_update\_data; SCAN\_INTERVAL
- local\_push is the integration manifest&\#x27;s classification, not an observation of a household device or a claim that every path is event\-driven\. The coordinator also schedules connection recovery\.
- Transport is unknown for any physical instance\. No IP address, account, pairing or network discovery was used\.
- The pinned integration depends on aiowebostv 0\.10\.0; that dependency&\#x27;s state derivation and wire\-level protocol remain outside this source trace\.

## Power state is not screen state

The media\-player adapter derives an entity state from client fields; it does not measure electrical power or prove physical screen state\.

### Treat the media\-player value as an adapter\-produced state, not physical ground truth\.

At the pinned \_update\_states method \(media\_player\.py lines 115–181\), a false client tv\_state\.is\_on selects OFF and returns; otherwise ON is set initially and client media\_state entries can change it to PLAYING, PAUSED or IDLE\. This inspected source path distinguishes state construction from availability\. It does not establish how aiowebostv derived those fields from a device\.

Conditions:

- Home Assistant Core 2026\.10\.0 at the pinned commit only\.
- The upstream client was not imported, executed or independently validated\. Do not interpret source branches as successful hardware tests\.

Evidence references:

- supports: ha\-webostv\-6a811d3 \#/artifacts/1

No physical-device observations recorded for this feature.

Linked records: ha\-webostv\-6a811d3, lg\-webos\-tv\-family, ha\-webostv\-documentation\-20261010

### Open questions

- No physical\-device observation or independent review\.
- Exact regional model, firmware and installed integration are unknown; this is not a G2\-specific result\.

### Contribute to this feature

- [Add a source](<https://github.com/edgeloom-oss/edgeloom-catalog/issues/new?template=device-source.yml&bundle=lg-webos-state-availability&version=0.1.0&feature=power-state>)
- [Report an observation](<https://github.com/edgeloom-oss/edgeloom-catalog/issues/new?template=device-observation.yml&bundle=lg-webos-state-availability&version=0.1.0&feature=power-state>)
- [Suggest a correction](<https://github.com/edgeloom-oss/edgeloom-catalog/issues/new?template=correction.yml&bundle=lg-webos-state-availability&version=0.1.0&feature=power-state>)
- [Review this evidence](<https://github.com/edgeloom-oss/edgeloom-catalog/issues/new?template=independent-review.yml&bundle=lg-webos-state-availability&version=0.1.0&feature=power-state>)

## Unavailable is not a power measurement

Entity availability follows coordinator success and connection\-recovery conditions, separately from the media\-player state calculation\.

### Keep availability separate from a device&\#x27;s power value\.

WebOsTvEntity inherits CoordinatorEntity \(entity\.py lines 15–24\)\. CoordinatorEntity\.available returns coordinator\.last\_update\_success \(update\_coordinator\.py lines 724–728\)\. In the webOS coordinator&\#x27;s connection\-recovery path \(coordinator\.py lines 45–68\), an already\-connected client returns immediately; specified connection errors raise UpdateFailed when no turn\-on action exists and the config entry is LOADED\. Pairing errors follow a different authentication\-failure path\. This explains why configuration and connectivity affect availability; it is not an exhaustive proof of all runtime transitions\.

Conditions:

- Connection status, coordinator success and the client is\_on field are different predicates\.
- The manifest&\#x27;s local\_push classification coexists with a ten\-second coordinator recovery interval; do not infer the observed update latency from either declaration\.
- No recovery action, wake\-on\-LAN packet, new pairing or automation is performed by this bundle\.

Evidence references:

- supports: ha\-webostv\-6a811d3 \#/artifacts/2
- supports: ha\-webostv\-6a811d3 \#/artifacts/3
- supports: ha\-webostv\-6a811d3 \#/artifacts/4

No physical-device observations recorded for this feature.

Linked records: ha\-webostv\-6a811d3, lg\-webos\-tv\-family, ha\-webostv\-documentation\-20261010

### Open questions

- No physical\-device observation or independent review\.
- Exact regional model, firmware and installed integration are unknown; this is not a G2\-specific result\.
- Dependency\-level connection and state decoding, all exception paths and entity serialization have not been traced end\-to\-end\.

### Contribute to this feature

- [Add a source](<https://github.com/edgeloom-oss/edgeloom-catalog/issues/new?template=device-source.yml&bundle=lg-webos-state-availability&version=0.1.0&feature=availability>)
- [Report an observation](<https://github.com/edgeloom-oss/edgeloom-catalog/issues/new?template=device-observation.yml&bundle=lg-webos-state-availability&version=0.1.0&feature=availability>)
- [Suggest a correction](<https://github.com/edgeloom-oss/edgeloom-catalog/issues/new?template=correction.yml&bundle=lg-webos-state-availability&version=0.1.0&feature=availability>)
- [Review this evidence](<https://github.com/edgeloom-oss/edgeloom-catalog/issues/new?template=independent-review.yml&bundle=lg-webos-state-availability&version=0.1.0&feature=availability>)

## A separate, conditional screen entity

Screen state and availability have separate conditions; a declared switch does not establish support on every model\.

### Preserve the separate screen entity and its conditional applicability\.

The pinned switch\.py disables the screen entity by default, computes availability from inherited availability, client is\_on and a local unsupported flag, and returns client is\_screen\_on for screen state \(lines 28–52\)\. Its command path catches a service\-not\-found error and marks the entity unsupported \(lines 66–78\)\. These declarations must not be flattened into a universal power switch or a claim that every webOS TV supports screen control\.

Conditions:

- Source\-only inspection, not a control test or recommendation to enable the entity\.
- The exact TV model and firmware may change applicability\. Keep unsupported and unavailable distinct from screen\-off\.

Evidence references:

- supports: ha\-webostv\-6a811d3 \#/artifacts/5
- context: ha\-webostv\-documentation\-20261010 \#/locations/1

No physical-device observations recorded for this feature.

Linked records: ha\-webostv\-6a811d3, lg\-webos\-tv\-family, ha\-webostv\-documentation\-20261010

### Open questions

- No physical\-device observation or independent review\.
- Exact regional model, firmware and installed integration are unknown; this is not a G2\-specific result\.
- An exact\-model manufacturer manual is not yet linked; current document context comes from the integration publisher\.

### Proposed test: For one identified, already\-integrated TV, which state and availability fields are actually exposed?

Proposed procedure; no execution result is implied.

1. Confirm model, firmware, HA version, integration and whether relevant entities are already enabled; use research aliases\.
2. After separate agreement on a read\-only window, observe existing state fields during ordinary user activity without changing configuration or issuing commands\.
3. Record relative times and missing/unknown values; exclude account names, household identifiers, app/channel names and viewing history\.

Requested evidence:

- Sanitized model/version information and the selected implementation path\.
- A bounded, consented observation with actual versus expected values and explicit unobserved stages; no raw household export\.

### Contribute to this feature

- [Add a source](<https://github.com/edgeloom-oss/edgeloom-catalog/issues/new?template=device-source.yml&bundle=lg-webos-state-availability&version=0.1.0&feature=screen-state>)
- [Report an observation](<https://github.com/edgeloom-oss/edgeloom-catalog/issues/new?template=device-observation.yml&bundle=lg-webos-state-availability&version=0.1.0&feature=screen-state>)
- [Suggest a correction](<https://github.com/edgeloom-oss/edgeloom-catalog/issues/new?template=correction.yml&bundle=lg-webos-state-availability&version=0.1.0&feature=screen-state>)
- [Review this evidence](<https://github.com/edgeloom-oss/edgeloom-catalog/issues/new?template=independent-review.yml&bundle=lg-webos-state-availability&version=0.1.0&feature=screen-state>)

## Sources and evidence

### home\-assistant · source snapshot

Kind: source\-manifest

Record ID: ha\-webostv\-6a811d3 · Path: catalog/sources/ha\-webostv\-6a811d3\.json
Record SHA-256: 186e0d645a2e45c318e6a595b23ae0f1db66573226339752927302721ba0961f

[Upstream repository](<https://github.com/home-assistant/core>)

- [homeassistant/components/webostv/manifest\.json](<https://github.com/home-assistant/core/blob/6a811d3359c7b2076dc9e1cf900843a129c044af/homeassistant/components/webostv/manifest.json>)
- [homeassistant/components/webostv/media\_player\.py](<https://github.com/home-assistant/core/blob/6a811d3359c7b2076dc9e1cf900843a129c044af/homeassistant/components/webostv/media_player.py>)
- [homeassistant/components/webostv/entity\.py](<https://github.com/home-assistant/core/blob/6a811d3359c7b2076dc9e1cf900843a129c044af/homeassistant/components/webostv/entity.py>)
- [homeassistant/components/webostv/coordinator\.py](<https://github.com/home-assistant/core/blob/6a811d3359c7b2076dc9e1cf900843a129c044af/homeassistant/components/webostv/coordinator.py>)
- [homeassistant/helpers/update\_coordinator\.py](<https://github.com/home-assistant/core/blob/6a811d3359c7b2076dc9e1cf900843a129c044af/homeassistant/helpers/update_coordinator.py>)
- [homeassistant/components/webostv/switch\.py](<https://github.com/home-assistant/core/blob/6a811d3359c7b2076dc9e1cf900843a129c044af/homeassistant/components/webostv/switch.py>)
- [LICENSE\.md](<https://github.com/home-assistant/core/blob/6a811d3359c7b2076dc9e1cf900843a129c044af/LICENSE.md>)

Referenced driver code is not included or executed by this bundle.

Complete record:

    {
      "artifacts": [
        {
          "artifact_role": "evidence",
          "description": "Integration identity, local_push declaration and pinned dependency.",
          "id": "webostv-manifest",
          "layer": "platform-exposure",
          "license": {
            "evidence_path": "LICENSE.md",
            "expression": "Apache-2.0"
          },
          "media_type": "application/json",
          "path": "homeassistant/components/webostv/manifest.json",
          "sha256": "c2f4ea88a3508cc22568a7c6e3b427b4ec8c281653352eebc3f583111d93b78e",
          "source_maturity": "community"
        },
        {
          "artifact_role": "evidence",
          "description": "Entity state construction from the client's TV state.",
          "id": "webostv-media-player",
          "layer": "platform-exposure",
          "license": {
            "evidence_path": "LICENSE.md",
            "expression": "Apache-2.0"
          },
          "media_type": "text/x-python",
          "path": "homeassistant/components/webostv/media_player.py",
          "sha256": "25e4b06e61577dd5c896d163d4d8379c052c01a334e3638309e95a1ebe4edbe1",
          "source_maturity": "community"
        },
        {
          "artifact_role": "evidence",
          "description": "CoordinatorEntity inheritance and integration-level manufacturer identity.",
          "id": "webostv-entity",
          "layer": "platform-exposure",
          "license": {
            "evidence_path": "LICENSE.md",
            "expression": "Apache-2.0"
          },
          "media_type": "text/x-python",
          "path": "homeassistant/components/webostv/entity.py",
          "sha256": "cd3451b66ce5e14f73deca1ddce58d3908b96cd2d2fbf8d5c8582803a2416f27",
          "source_maturity": "community"
        },
        {
          "artifact_role": "evidence",
          "description": "Connection recovery and UpdateFailed conditions.",
          "id": "webostv-coordinator",
          "layer": "platform-exposure",
          "license": {
            "evidence_path": "LICENSE.md",
            "expression": "Apache-2.0"
          },
          "media_type": "text/x-python",
          "path": "homeassistant/components/webostv/coordinator.py",
          "sha256": "3788a885cb8dd0c71b877cc4cd5996634d695a834ed9be8bcad3110fa37ab4c6",
          "source_maturity": "community"
        },
        {
          "artifact_role": "evidence",
          "description": "Shared CoordinatorEntity availability property.",
          "id": "webostv-coordinator-base",
          "layer": "platform-exposure",
          "license": {
            "evidence_path": "LICENSE.md",
            "expression": "Apache-2.0"
          },
          "media_type": "text/x-python",
          "path": "homeassistant/helpers/update_coordinator.py",
          "sha256": "0af39b34a677ad53246333b80cbd0dfd73724af0a03d5cce39032640591b82ec",
          "source_maturity": "community"
        },
        {
          "artifact_role": "evidence",
          "description": "Separate screen switch state and availability conditions.",
          "id": "webostv-screen",
          "layer": "platform-exposure",
          "license": {
            "evidence_path": "LICENSE.md",
            "expression": "Apache-2.0"
          },
          "media_type": "text/x-python",
          "path": "homeassistant/components/webostv/switch.py",
          "sha256": "2ea11aa9442809ed132eb3c406b8cf6c29e80649ec524671b9e7fd47eef61f80",
          "source_maturity": "community"
        },
        {
          "artifact_role": "evidence",
          "description": "Pinned Home Assistant Core license.",
          "id": "webostv-license",
          "layer": "platform-exposure",
          "license": {
            "evidence_path": "LICENSE.md",
            "expression": "Apache-2.0"
          },
          "media_type": "text/plain",
          "path": "LICENSE.md",
          "sha256": "c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4",
          "source_maturity": "community"
        }
      ],
      "description": "Home Assistant 2026.10.0 webOS integration-family state paths. Not a model-specific driver match or physical result.",
      "ecosystem": "home-assistant",
      "id": "ha-webostv-6a811d3",
      "kind": "source-manifest",
      "repository": {
        "commit": "6a811d3359c7b2076dc9e1cf900843a129c044af",
        "url": "https://github.com/home-assistant/core"
      },
      "schema_version": "0.1"
    }

### LG webOS TVs \(integration family\) · device identity

Kind: catalog\-device

Record ID: lg\-webos\-tv\-family · Path: catalog/devices/lg\-webos\-tv\-family\.json
Record SHA-256: b79dfce17398eed231336600caacd2fa122436d042d4c764601ced5224116a35

Complete record:

    {
      "category": "media",
      "connections": [
        {
          "access": "local",
          "application_protocol": "LG webOS API via aiowebostv (wire-level behavior not traced)",
          "basis": "source-declared",
          "data_updates": "push",
          "id": "ha-webostv",
          "integration": "webostv",
          "limitations": [
            "local_push is the integration manifest's classification, not an observation of a household device or a claim that every path is event-driven. The coordinator also schedules connection recovery.",
            "Transport is unknown for any physical instance. No IP address, account, pairing or network discovery was used.",
            "The pinned integration depends on aiowebostv 0.10.0; that dependency's state derivation and wire-level protocol remain outside this source trace."
          ],
          "platform": "Home Assistant Core",
          "platform_version": "2026.10.0",
          "references": [
            {
              "artifact_id": "webostv-manifest",
              "locator": "/iot_class",
              "manifest_id": "ha-webostv-6a811d3"
            },
            {
              "artifact_id": "webostv-manifest",
              "locator": "/requirements/0",
              "manifest_id": "ha-webostv-6a811d3"
            },
            {
              "artifact_id": "webostv-coordinator",
              "locator": "WebOsTvDataUpdateCoordinator._async_update_data; SCAN_INTERVAL",
              "manifest_id": "ha-webostv-6a811d3"
            }
          ],
          "transports": [
            "unknown"
          ]
        }
      ],
      "features": [
        {
          "id": "power-state",
          "mapping_ids": [],
          "next_steps": [
            "Inspect the pinned adapter branches and separate reported state from physical state.",
            "Supply exact model, webOS and installed HA versions before a model-specific case."
          ],
          "source_references": [
            {
              "artifact_id": "webostv-media-player",
              "locator": "LgWebOSMediaPlayerEntity._update_states (lines 115-181)",
              "manifest_id": "ha-webostv-6a811d3"
            }
          ],
          "summary": "The media-player adapter derives an entity state from client fields; it does not measure electrical power or prove physical screen state.",
          "title": "Power state is not screen state"
        },
        {
          "id": "availability",
          "mapping_ids": [],
          "next_steps": [
            "Trace the availability chain before treating unavailable as off.",
            "Review current configuration without adding a turn-on automation or waking the TV."
          ],
          "source_references": [
            {
              "artifact_id": "webostv-entity",
              "locator": "WebOsTvEntity(CoordinatorEntity) (lines 15-24)",
              "manifest_id": "ha-webostv-6a811d3"
            },
            {
              "artifact_id": "webostv-coordinator",
              "locator": "WebOsTvDataUpdateCoordinator._async_update_data (lines 45-68)",
              "manifest_id": "ha-webostv-6a811d3"
            },
            {
              "artifact_id": "webostv-coordinator-base",
              "locator": "CoordinatorEntity.available (lines 724-728)",
              "manifest_id": "ha-webostv-6a811d3"
            }
          ],
          "summary": "Entity availability follows coordinator success and connection-recovery conditions, separately from the media-player state calculation.",
          "title": "Unavailable is not a power measurement"
        },
        {
          "id": "screen-state",
          "mapping_ids": [],
          "next_steps": [
            "Check source conditions; do not enable or exercise screen control solely for catalog intake.",
            "An exact-model manual and bounded read-only observation remain missing."
          ],
          "source_references": [
            {
              "artifact_id": "webostv-screen",
              "locator": "LgWebOSScreenSwitchEntity.available/is_on/_async_set_screen_state (lines 28-78)",
              "manifest_id": "ha-webostv-6a811d3"
            }
          ],
          "summary": "Screen state and availability have separate conditions; a declared switch does not establish support on every model.",
          "title": "A separate, conditional screen entity"
        }
      ],
      "firmware": "unknown",
      "hardware_evidence": [],
      "id": "lg-webos-tv-family",
      "identifiers": {
        "family": "webOS TV",
        "manufacturer": "LG"
      },
      "identity_evidence": {
        "artifact_id": "webostv-manifest",
        "locator": "/name",
        "manifest_id": "ha-webostv-6a811d3"
      },
      "identity_scope": "device-family",
      "kind": "catalog-device",
      "limitations": [
        "Integration-family source study only; no exact regional model, firmware, G2 compatibility or physical observation established.",
        "No independent review, SDF mapping, driver installation or control recommendation.",
        "Founder-directed, AI-assisted curation. Home Assistant contributors retain upstream credit; their authorship is not EdgeLoom review or endorsement."
      ],
      "manufacturer": "LG",
      "model": "webOS TVs (integration family)",
      "protocol": "ip",
      "schema_version": "0.2"
    }

### Home Assistant LG webOS TV integration documentation

Kind: document\-source

Record ID: ha\-webostv\-documentation\-20261010 · Path: catalog/documents/ha\-webostv\-documentation\-20261010\.json
Record SHA-256: 8176a1f20d46455c89880b26b148aba9f090c112dac77e493c95bfaec6cffd80

[Upstream document](<https://www.home-assistant.io/integrations/webostv/>)

Declared applicability: family\-context
Capture: link\-only; source bytes are not included.

Complete record:

    {
      "accessed_at": "2026-10-10",
      "applicability": {
        "manufacturer": "LG",
        "model": "webOS TV family",
        "notes": [
          "Official documentation of the integration, not an LG manufacturer manual or exact-model qualification."
        ],
        "scope": "family-context"
      },
      "capture": {
        "mode": "link-only"
      },
      "contributed_by": "github:@infinitywings",
      "document_version": "Mutable integration documentation inspected 2026-10-10 UTC",
      "id": "ha-webostv-documentation-20261010",
      "kind": "document-source",
      "limitations": [
        "Mutable page; no archived byte snapshot. Pinned code below is the reproducible implementation source.",
        "Official integration documentation is not independent EdgeLoom review. Exact-model LG manual remains missing."
      ],
      "locations": [
        {
          "description": "Integration-family context, not identification of a physical unit.",
          "id": "scope",
          "locator": "Supported devices"
        },
        {
          "description": "Separate screen entity and conditional availability.",
          "id": "screen",
          "locator": "Supported functionality / Switches"
        },
        {
          "description": "Configuration context for off versus unavailable.",
          "id": "availability",
          "locator": "Turning on the TV from Home Assistant"
        }
      ],
      "publisher": "Home Assistant",
      "rights": {
        "notice": "Link and original bounded paraphrases only. No upstream page, screenshots or manual redistributed; no rights determination inferred.",
        "redistribution": "not-granted"
      },
      "schema_version": "0.1",
      "source_maturity": "official",
      "title": "Home Assistant LG webOS TV integration documentation",
      "url": "https://www.home-assistant.io/integrations/webostv/"
    }

## Reviews

Review entries are scoped declarations, not authentication.

No scoped reviews recorded in this bundle.

## Credits

- github:@infinitywings: author, source\-research, maintenance; records: ha\-webostv\-6a811d3, lg\-webos\-tv\-family, ha\-webostv\-documentation\-20261010

## Version history

- 0\.1\.0: First source\-only family case under draft schema 0\.2\. Pin source declarations, explain three state layers, and preserve all hardware/model/review gaps\.

## Scope and limits

- Source\-only candidate under draft schema 0\.2\. Repository acceptance or snapshot publication does not confer independent review, hardware validation or a packaged software release\.
- Original metadata and explanations prepared with Codex assistance under the founder&\#x27;s direction; no independent community review\.
- Upstream Home Assistant contributors retain attribution through repository, commit, artifact and license links\. No upstream endorsement or additional contributor review credit is claimed\.
- Only metadata and original explanations are packaged; upstream source files and documentation are not redistributed\.
- This package never connects to a device, scans a network, executes an upstream driver or adds support to Home Assistant\.

## Package integrity

Record hashes and reference checks establish package consistency. They do not authenticate a publisher, establish independent review, or demonstrate device behavior.

Catalog revision: d4068dabf34f08a2ce35496203b232b8519fcc52
Declared core revision: d7e801d10f02b6effe4d8403ec997913bfd7bb2c
Input digest: e02434dd5b486a2770a6e0e735228c72a87aff2a6d760e3d08906c0146c467c6

License: Apache\-2\.0 for catalog-authored records; upstream terms remain separate.

See report.json for complete generator and package-check metadata.
