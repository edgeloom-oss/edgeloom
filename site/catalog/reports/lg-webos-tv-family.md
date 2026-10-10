# LG webOS TVs \(integration family\)

Source-level evidence, not a compatibility or installation recommendation.

- Protocol: ip
- Identifiers: \{   "family": "webOS TV",   "manufacturer": "LG" \}
- Firmware: unknown
- Catalog revision: d4068dabf34f08a2ce35496203b232b8519fcc52
- Input digest: 26c0d572d3e7e04ec9ba3d7bdabd4439feadca81902c8a5a8381bb7aaa3e4b1e
- Source byte check: not-checked
- Hardware evidence: none recorded

## Declared integration context

- Identity scope: device\-family \(source\-declared, not proof of physical identity\)
- Category: media
- Home Assistant Core / webostv · platform version: 2026\.10\.0
- Transport: unknown · application protocol/API: LG webOS API via aiowebostv \(wire\-level behavior not traced\)
- Access: local · data updates: push · basis: source\-declared
- Evidence: ha\-webostv\-6a811d3/webostv\-manifest @ /iot\_class
- Evidence: ha\-webostv\-6a811d3/webostv\-manifest @ /requirements/0
- Evidence: ha\-webostv\-6a811d3/webostv\-coordinator @ WebOsTvDataUpdateCoordinator\.\_async\_update\_data; SCAN\_INTERVAL
- local\_push is the integration manifest's classification, not an observation of a household device or a claim that every path is event\-driven\. The coordinator also schedules connection recovery\.
- Transport is unknown for any physical instance\. No IP address, account, pairing or network discovery was used\.
- The pinned integration depends on aiowebostv 0\.10\.0; that dependency's state derivation and wire\-level protocol remain outside this source trace\.

## Power state is not screen state

The media\-player adapter derives an entity state from client fields; it does not measure electrical power or prove physical screen state\.

- Source-only declaration: https://github.com/home-assistant/core/blob/6a811d3359c7b2076dc9e1cf900843a129c044af/homeassistant/components/webostv/media_player.py · LgWebOSMediaPlayerEntity\.\_update\_states \(lines 115\-181\)

Next steps:

- Inspect the pinned adapter branches and separate reported state from physical state\.
- Supply exact model, webOS and installed HA versions before a model\-specific case\.

## Unavailable is not a power measurement

Entity availability follows coordinator success and connection\-recovery conditions, separately from the media\-player state calculation\.

- Source-only declaration: https://github.com/home-assistant/core/blob/6a811d3359c7b2076dc9e1cf900843a129c044af/homeassistant/components/webostv/entity.py · WebOsTvEntity\(CoordinatorEntity\) \(lines 15\-24\)

- Source-only declaration: https://github.com/home-assistant/core/blob/6a811d3359c7b2076dc9e1cf900843a129c044af/homeassistant/components/webostv/coordinator.py · WebOsTvDataUpdateCoordinator\.\_async\_update\_data \(lines 45\-68\)

- Source-only declaration: https://github.com/home-assistant/core/blob/6a811d3359c7b2076dc9e1cf900843a129c044af/homeassistant/helpers/update_coordinator.py · CoordinatorEntity\.available \(lines 724\-728\)

Next steps:

- Trace the availability chain before treating unavailable as off\.
- Review current configuration without adding a turn\-on automation or waking the TV\.

## A separate, conditional screen entity

Screen state and availability have separate conditions; a declared switch does not establish support on every model\.

- Source-only declaration: https://github.com/home-assistant/core/blob/6a811d3359c7b2076dc9e1cf900843a129c044af/homeassistant/components/webostv/switch.py · LgWebOSScreenSwitchEntity\.available/is\_on/\_async\_set\_screen\_state \(lines 28\-78\)

Next steps:

- Check source conditions; do not enable or exercise screen control solely for catalog intake\.
- An exact\-model manual and bounded read\-only observation remain missing\.

## Boundaries

- Integration\-family source study only; no exact regional model, firmware, G2 compatibility or physical observation established\.
- No independent review, SDF mapping, driver installation or control recommendation\.
- Founder\-directed, AI\-assisted curation\. Home Assistant contributors retain upstream credit; their authorship is not EdgeLoom review or endorsement\.
- Device associations, classifications, license labels, and review states are catalog\-author declarations, not independently authenticated by this build\.
- Resolved locators establish field existence only, not the interpretation, completeness, runtime behavior, SDF conformance, or interoperability of an artifact\.
- Selectors, JSON5 and Lua locators need manual review\. No upstream Lua is executed\.
- Profile absence is not whole\-driver or UI absence\. A missing property in a particular SDF model is not a limitation of SDF itself\.
- Hardware\-evidence links are reported observations, not tests performed by this tool\. No patch availability is inferred\.
- Cross\-source observations and lineage are curator declarations\. Shared backends are not independent evidence; upstream test fixtures are not physical\-device tests or independent EdgeLoom review\. No source count promotes a candidate\.
