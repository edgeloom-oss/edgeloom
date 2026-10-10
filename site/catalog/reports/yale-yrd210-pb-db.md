# Yale YRD210 PB DB \(Zigbee\)

Source-level evidence, not a compatibility or installation recommendation.

- Protocol: zigbee
- Identifiers: \{   "manufacturer": "Yale",   "model": "YRD210 PB DB" \}
- Firmware: Unknown; exact endpoint/cluster signature and installed platform versions unconfirmed
- Catalog revision: d4068dabf34f08a2ce35496203b232b8519fcc52
- Input digest: 26c0d572d3e7e04ec9ba3d7bdabd4439feadca81902c8a5a8381bb7aaa3e4b1e
- Source byte check: not-checked
- Hardware evidence: none recorded

## Battery normalization

Two upstream adaptations for the same model string, at different layers\. Raw cluster values and final entity percentages are not interchangeable\.

### Same battery intent, different adaptation

Both snapshots account for nonstandard battery reporting, but at different layers\. Compare the raw attribute and the final entity value before proposing a numeric binding; do not copy either adjustment twice\.

Candidate external corroboration; not independent EdgeLoom review.

- ZHA quirk: supports / device-model / code-declaration
  - The Yale YRD210 PB DB signature selects a replacement DoublingPowerConfigurationCluster\. That cluster multiplies battery\_percentage\_remaining \(0x0021\) by two\.
  - Declared identity match: \{   "manufacturer": "Yale",   "model": "YRD210 PB DB" \}
  - Condition: The full endpoint/cluster signature must also match; manufacturer/model alone is insufficient for quirk selection\.
  - Condition: This is a cluster\-attribute adjustment, not a claim that the final HA entity shows twice the battery percentage\.
  - Condition: Firmware and downstream ZHA entity normalization are not inspected in this record\.
  - [Pinned source](https://github.com/zigpy/zha-device-handlers/blob/d6fcec59eff9f63f154723500be9378be926d927/zhaquirks/yale/realliving.py): YRD210PBDB220TSLL\.signature and replacement; not-checked
  - [Pinned source](https://github.com/zigpy/zha-device-handlers/blob/d6fcec59eff9f63f154723500be9378be926d927/zhaquirks/__init__.py): DoublingPowerConfigurationCluster\.\_update\_attribute; not-checked
  - [Pinned source](https://github.com/zigpy/zha-device-handlers/blob/d6fcec59eff9f63f154723500be9378be926d927/zhaquirks/yale/realliving.py): YRD210PBDB220TSLL\.signature\.MODELS\_INFO; not-checked
- Zigbee2MQTT converter: supports / device-model / code-declaration
  - The YRD210 PB DB entry uses dontDividePercentage: true\. The battery converter therefore skips its default divide\-by\-two step, when the reported percentage exists and is below 255\.
  - Declared identity match: \{   "model": "YRD210 PB DB" \}
  - Condition: This definition matches zigbeeModel, without an explicit manufacturer constraint; vendor is descriptive metadata\.
  - Condition: voltageToPercentage must be absent for the selected percentage branch\.
  - Condition: Static source inspection only; no converter or upstream driver is executed\.
  - [Pinned source](https://github.com/Koenkk/zigbee-herdsman-converters/blob/5750b44559405203b202e0f5539dc0d6f46f1c8d/src/devices/yale.ts): YRD210\-HA\-605; lockExtend\(\{battery: \{dontDividePercentage: true\}\}\); not-checked
  - [Pinned source](https://github.com/Koenkk/zigbee-herdsman-converters/blob/5750b44559405203b202e0f5539dc0d6f46f1c8d/src/converters/fromZigbee.ts): battery\.convert; batteryPercentageRemaining; dontDividePercentage; not-checked
  - [Pinned source](https://github.com/Koenkk/zigbee-herdsman-converters/blob/5750b44559405203b202e0f5539dc0d6f46f1c8d/src/devices/yale.ts): definitions\[zigbeeModel includes YRD210 PB DB\]; not-checked

Declared lineage (not an independence score):

- zha\-yale\-d6fcec5: family zha\-quirks; depends on none declared in this record
- z2m\-yale\-5750b44: family zigbee\-herdsman\-converters; depends on none declared in this record

- Limit: Human\-authored candidate observations; no independent EdgeLoom review or physical\-device test\.
- Limit: Sources are pinned snapshots, not a claim about the currently installed integration, coordinator or firmware\.
- Limit: Relationship labels are curator interpretations, not computed semantic equivalence\. Conflicting observations must remain visible\.
- Limit: Different declared source families are not proof of independence: shared specs, authors or copied knowledge may exist\.
- Limit: No raw device report, final\-entity comparison, unit\-test result or SDF binding is established\.

Next steps:

- Compare the exact manufacturer/model and full endpoint/cluster signature\.
- Report a sanitized raw battery attribute and final entity value, including firmware and platform versions\.
- Do not apply either adjustment twice or treat this report as a patch recommendation\.

## Lock control and observed state

A cluster declaration and a richer exposes declaration are different evidence scopes\. No complete cross\-platform or SDF mapping has been established\.

### Cluster declaration versus exposed state

The matching ZHA quirk retains a DoorLock cluster\. Zigbee2MQTT declares separate command/state and actual\-state fields\. These artifacts alone do not establish equal UI behavior or a complete cross\-platform mapping\.

Candidate external corroboration; not independent EdgeLoom review.

- ZHA quirk: context / device-model / code-declaration
  - YRD210PBDB220TSLL includes DoorLock in its signature and replacement input clusters\. The quirk itself does not define the downstream HA lock entity's states\.
  - Declared identity match: \{   "manufacturer": "Yale",   "model": "YRD210 PB DB" \}
  - Condition: Endpoint and complete cluster signature must match\.
  - Condition: Cluster presence is not whole\-platform exposure or hardware success\.
  - [Pinned source](https://github.com/zigpy/zha-device-handlers/blob/d6fcec59eff9f63f154723500be9378be926d927/zhaquirks/yale/realliving.py): YRD210PBDB220TSLL\.signature and replacement; DoorLock\.cluster\_id; not-checked
  - [Pinned source](https://github.com/zigpy/zha-device-handlers/blob/d6fcec59eff9f63f154723500be9378be926d927/zhaquirks/yale/realliving.py): YRD210PBDB220TSLL\.signature\.MODELS\_INFO; not-checked
- Zigbee2MQTT exposes: context / device-model / code-declaration
  - The shared e\.lock\(\) constructor declares state as LOCK/UNLOCK with state/set/get access, and lock\_state as not\_fully\_locked/locked/unlocked with state\-only access\.
  - Declared identity match: \{   "model": "YRD210 PB DB" \}
  - Condition: Model\-only matcher; no explicit manufacturer constraint in this definition\.
  - Condition: Exposed metadata is not a firmware capability test or confirmation that all state values occur\.
  - [Pinned source](https://github.com/Koenkk/zigbee-herdsman-converters/blob/5750b44559405203b202e0f5539dc0d6f46f1c8d/src/devices/yale.ts): YRD210\-HA\-605; lockExtend; exposes e\.lock\(\); not-checked
  - [Pinned source](https://github.com/Koenkk/zigbee-herdsman-converters/blob/5750b44559405203b202e0f5539dc0d6f46f1c8d/src/lib/exposes.ts): presets\.lock; Lock\.withState; Lock\.withLockState; access; not-checked
  - [Pinned source](https://github.com/Koenkk/zigbee-herdsman-converters/blob/5750b44559405203b202e0f5539dc0d6f46f1c8d/src/devices/yale.ts): definitions\[zigbeeModel includes YRD210 PB DB\]; not-checked

Declared lineage (not an independence score):

- zha\-yale\-d6fcec5: family zha\-quirks; depends on none declared in this record
- z2m\-yale\-5750b44: family zigbee\-herdsman\-converters; depends on none declared in this record

- Limit: Human\-authored candidate observations; no independent EdgeLoom review or physical\-device test\.
- Limit: Sources are pinned snapshots, not a claim about the currently installed integration, coordinator or firmware\.
- Limit: Relationship labels are curator interpretations, not computed semantic equivalence\. Conflicting observations must remain visible\.
- Limit: No SDF correspondence is added for this Zigbee case; lack of a catalog binding is not a limitation of SDF\.
- Limit: Commands, observations and partially locked state must not be collapsed into a single binary semantic binding\.

Next steps:

- Distinguish a requested lock command from the reported actual lock state\.
- Retain partially locked and unknown values when investigating a correspondence\.
- Contribute a source correction or sanitized observation; never include real PINs or user identifiers\.

## Boundaries

- Founder\-authored candidate corroboration only; no independent review or hardware testing\.
- Not the YRD156 Z\-Wave case; protocol variants and nearby marketing models are not interchangeable\.
- ZHA requires the full device signature; Zigbee2MQTT's selected entry uses a weaker model\-only matcher\.
- No SDF binding, safe installation recipe or automatic repair is provided for this case\.
- Source lineage is declared and incomplete; no independent\-source or adoption score is inferred\.
- Device associations, classifications, license labels, and review states are catalog\-author declarations, not independently authenticated by this build\.
- Resolved locators establish field existence only, not the interpretation, completeness, runtime behavior, SDF conformance, or interoperability of an artifact\.
- Selectors, JSON5 and Lua locators need manual review\. No upstream Lua is executed\.
- Profile absence is not whole\-driver or UI absence\. A missing property in a particular SDF model is not a limitation of SDF itself\.
- Hardware\-evidence links are reported observations, not tests performed by this tool\. No patch availability is inferred\.
- Cross\-source observations and lineage are curator declarations\. Shared backends are not independent evidence; upstream test fixtures are not physical\-device tests or independent EdgeLoom review\. No source count promotes a candidate\.
