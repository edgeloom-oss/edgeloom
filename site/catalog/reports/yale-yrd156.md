# Yale YRD156

Source-level evidence, not a compatibility or installation recommendation.

- Protocol: zwave
- Identifiers: \{   "manufacturer\_id": "0x0129",   "product\_id": "0x0508",   "product\_type": "0x803A" \}
- Firmware: Unknown; no real\-unit firmware or SLGA\_MIGRATED state recorded
- Catalog revision: 140d146f81913c213574702810098ae7a4f5f4cc
- Input digest: 3b8ce4d6d019462230dd70781bf1de1919da83ffa7ce32e9dfa3ae7333e502a9
- Source byte check: matched
- Hardware evidence: none recorded

## Auto\-relock duration

The pinned community configuration describes a duration parameter\. It is absent from the examined base\-lock capability list and the selected lock\-status SDF object\. This does not establish that the whole driver or SmartThings UI lacks a setting, or that SDF cannot express one\.

### Yale YRD156 auto\-relock exposure and neutral\-model gaps

Review lifecycle: candidate (declared).

- map\.yrd156\-auto\-relock\-to\-smartthings: unbound / platform-not-exposed
  - Limit: Absence is established only for the pinned base\-lock profile; another profile, custom capability, or later commit could expose this setting\.
- map\.yrd156\-auto\-relock\-to\-sdf: unbound / neutral-model-missing
  - Limit: The finding is bounded to the pinned OCF\-derived lock\-status model and does not assert that no other SDF model can describe auto relock\.

- Limit: The zwave\-js configuration is community evidence, not Yale authority\.
- Limit: No physical YRD156 or SmartThings hub was tested for this candidate\.
- Limit: The current schema requires a neutral\-layer context node even when the mapping conclusion is neutral\-model\-missing; that context is the bounded lock\-status property set examined for this record\.

- Evidence: The community configuration identifies the YRD156 with product tuple 0x0129/0x803A/0x0508\.
  - [Pinned source](https://github.com/zwave-js/zwave-js/blob/c4c599e1e6a0f6fab1f356f92307b8f94e895e60/packages/config/config/devices/0x0129/yrd156.json); locator: /manufacturerId\|/devices/0/productType\|/devices/0/productId; check: manual-review
- Evidence: The SmartThings fingerprint uses the same product tuple and assigns it to the base\-lock profile examined for the platform\-exposure gap\.
  - [Pinned source](https://github.com/SmartThingsCommunity/SmartThingsEdgeDrivers/blob/6b8a9cf69462d314a7c81b7a709037744d7d788d/drivers/SmartThings/zwave-lock/fingerprints.yml); locator: zwaveManufacturer\[id=Yale/YRD156\]; check: manual-review
- Evidence: The pinned community YRD156 config imports auto\_relock\_time\_180 for configuration parameter 3\.
  - [Pinned source](https://github.com/zwave-js/zwave-js/blob/c4c599e1e6a0f6fab1f356f92307b8f94e895e60/packages/config/config/devices/0x0129/yrd156.json); locator: /paramInformation/\[\#=3\]; check: manual-review
- Evidence: The imported template describes Auto Relock Time in seconds with a default value of 30 and imports the named base\_0\-180\_nounit definition\.
  - [Pinned source](https://github.com/zwave-js/zwave-js/blob/c4c599e1e6a0f6fab1f356f92307b8f94e895e60/packages/config/config/devices/0x0129/templates/yale_template.json); locator: /auto\_relock\_time\_180; check: manual-review
- Evidence: The pinned shared base definition supplies an unsigned minimum of 0 and maximum of 180 for the imported duration field\.
  - [Pinned source](https://github.com/zwave-js/zwave-js/blob/c4c599e1e6a0f6fab1f356f92307b8f94e895e60/packages/config/config/devices/templates/master_template.json); locator: /base\_0\-180\_nounit; check: manual-review
- Evidence: The complete pinned base\-lock capability list has lock, lockCodes, lockCredentials, lockUsers, battery, and refresh, but no auto\-relock field\.
  - [Pinned source](https://github.com/SmartThingsCommunity/SmartThingsEdgeDrivers/blob/6b8a9cf69462d314a7c81b7a709037744d7d788d/drivers/SmartThings/zwave-lock/profiles/base-lock.yml); locator: /components/0/capabilities; check: resolved
- Evidence: The complete pinned lock\-status property set contains lockState only and does not contain an auto\-relock enable or duration property\.
  - [Pinned source](https://github.com/one-data-model/ocf-models/blob/c97d095c239539b8242ceb4f12cf6deaeedb16e2/sdfObject/sdfobject-lock_status.sdf.json); locator: /sdfObject/lock\.status/sdfProperty; check: resolved

Next steps:

- Compare your exact driver version and assigned profile with these pinned files\.
- Inspect preferences, handlers and subdrivers before concluding the setting is unavailable\.
- Report a difference without including private device identifiers or access codes\.

## Lock\-state events

A strict locked/unlocked subset has a candidate correspondence with the selected SDF property\. Unknown state and method/user metadata are not preserved\. The examined handler path requires a true migration flag; that state has not been established for a real YRD156\.

### Yale YRD156 migrated\-path SmartThings lock\-state mapping candidate

Review lifecycle: candidate (declared).

- map\.smartthings\-binary\-state\-to\-sdf: one-to-one
  - Limit: This classification covers only the strict locked/unlocked subset and does not claim a complete SmartThings lock\-state translation\.
  - Limit: Enum spelling conversion is not represented by contract version 0\.1\.
- map\.smartthings\-extended\-event\-to\-sdf: lossy
  - Limit: The SDF property has no value corresponding to SmartThings unknown\.
  - Limit: Method, user index, user name, and user type metadata are not preserved\.

- Limit: The analysis is based on pinned published artifacts, not physical\-device tests\.
- Limit: No pinned record establishes the SLGA\_MIGRATED state of a real YRD156\. Devices without a true migration flag use legacy/default handlers whose behavior is outside this mapping set\.
- Limit: The OCF\-derived SDF repository location is not evidence of OneDM adoption, endorsement, active maintenance, or interoperability\.
- Limit: Contract version 0\.1 lacks a driver\-source artifact role; the pinned Lua source is transparently recorded under the generic evidence role\.

- Evidence: The pinned fingerprint identifies product tuple 0x0129/0x803A/0x0508 and assigns the YRD156 to the base\-lock profile\.
  - [Pinned source](https://github.com/SmartThingsCommunity/SmartThingsEdgeDrivers/blob/6b8a9cf69462d314a7c81b7a709037744d7d788d/drivers/SmartThings/zwave-lock/fingerprints.yml); locator: zwaveManufacturer\[id=Yale/YRD156\]; check: manual-review
- Evidence: On the current handler path, the pinned function maps a strict operation subset to locked or unlocked, maps other outcomes to unknown, and can attach method and user data\.
  - [Pinned source](https://github.com/SmartThingsCommunity/SmartThingsEdgeDrivers/blob/6b8a9cf69462d314a7c81b7a709037744d7d788d/drivers/SmartThings/zwave-lock/src/lock_handlers/zwave_responses.lua); locator: lua:function ZwaveHandlers\.door\_operation\_event\_handler; check: manual-review
- Evidence: The main driver template registers the pinned current Z\-Wave response functions for notification and user\-code reports\.
  - [Pinned source](https://github.com/SmartThingsCommunity/SmartThingsEdgeDrivers/blob/6b8a9cf69462d314a7c81b7a709037744d7d788d/drivers/SmartThings/zwave-lock/src/init.lua); locator: lua:driver\_template\.zwave\_handlers; check: manual-review
- Evidence: When the persisted SLGA\_MIGRATED field is unset or false, the pinned can\-handle function selects the legacy subdriver instead of this path\.
  - [Pinned source](https://github.com/SmartThingsCommunity/SmartThingsEdgeDrivers/blob/6b8a9cf69462d314a7c81b7a709037744d7d788d/drivers/SmartThings/zwave-lock/src/legacy-handlers/can_handle.lua); locator: lua:return function\(opts, driver, device, \.\.\.\); check: manual-review
- Evidence: The base\-lock profile exposes the native SmartThings lock capability\.
  - [Pinned source](https://github.com/SmartThingsCommunity/SmartThingsEdgeDrivers/blob/6b8a9cf69462d314a7c81b7a709037744d7d788d/drivers/SmartThings/zwave-lock/profiles/base-lock.yml); locator: /components/0/capabilities\[id=lock\]; check: manual-review
- Evidence: The pinned SDF property allows exactly Locked and Unlocked strings\.
  - [Pinned source](https://github.com/one-data-model/ocf-models/blob/c97d095c239539b8242ceb4f12cf6deaeedb16e2/sdfObject/sdfobject-lock_status.sdf.json); locator: /sdfObject/lock\.status/sdfProperty/lockState; check: resolved

Next steps:

- Establish the active handler path and migration condition before applying this finding\.
- Keep unknown state and event metadata explicit rather than reducing them to a binary value\.
- Request review of this bounded correspondence; no complete translator is provided here\.

## Access identity and lock codes

The examined migrated path carries user and credential metadata absent from the selected lock\-code SDF object\. A PIN write payload and the reported identity records do not establish a reversible value mapping\.

### Yale YRD156 migrated\-path access identity and lock\-code candidate

Review lifecycle: candidate (declared).

- map\.smartthings\-access\-identities\-to\-sdf: unbound / neutral-model-missing
  - Limit: The conclusion is bounded to the pinned lock\-code SDF object; other SDF objects or future extensions might represent identity metadata\.
- map\.smartthings\-credential\-payload\-to\-sdf\-list: ambiguous
  - Limit: The write path accepts credentialData as a PIN payload, while the report path represents slot occupancy and identity metadata; the files do not establish one reversible value\-level representation\.
  - Limit: No transformation is proposed for security\-sensitive credential values\.

- Limit: No real PIN, lock code, user identifier, or device credential is stored here\.
- Limit: The analysis is based on pinned source artifacts, not device or account tests\.
- Limit: No pinned record establishes the SLGA\_MIGRATED state of a real YRD156\. Devices without a true migration flag use legacy/default handlers whose user\-code behavior is outside this mapping set\.
- Limit: The SDF object is a neutral data model, not an authorization or credential management specification\.
- Limit: Contract version 0\.1 lacks a driver\-source artifact role; the pinned Lua source is transparently recorded under the generic evidence role\.

- Evidence: The pinned fingerprint identifies product tuple 0x0129/0x803A/0x0508 and assigns the YRD156 to the base\-lock profile used by this record\.
  - [Pinned source](https://github.com/SmartThingsCommunity/SmartThingsEdgeDrivers/blob/6b8a9cf69462d314a7c81b7a709037744d7d788d/drivers/SmartThings/zwave-lock/fingerprints.yml); locator: zwaveManufacturer\[id=Yale/YRD156\]; check: manual-review
- Evidence: On the current handler path, the function derives userIndex, userName, userType, credentialIndex, credentialType, and credentialName records from Z\-Wave user\-code reports\.
  - [Pinned source](https://github.com/SmartThingsCommunity/SmartThingsEdgeDrivers/blob/6b8a9cf69462d314a7c81b7a709037744d7d788d/drivers/SmartThings/zwave-lock/src/lock_handlers/zwave_responses.lua); locator: lua:function ZwaveHandlers\.user\_code\_report; check: manual-review
- Evidence: The base\-lock profile separately exposes lockCodes, lockCredentials, and lockUsers capabilities\.
  - [Pinned source](https://github.com/SmartThingsCommunity/SmartThingsEdgeDrivers/blob/6b8a9cf69462d314a7c81b7a709037744d7d788d/drivers/SmartThings/zwave-lock/profiles/base-lock.yml); locator: /components/0/capabilities; check: resolved
- Evidence: Credential data is accepted as a write\-time UserCode payload\. The pinned response path records slot occupancy and identity metadata rather than returning or caching the PIN value\.
  - [Pinned source](https://github.com/SmartThingsCommunity/SmartThingsEdgeDrivers/blob/6b8a9cf69462d314a7c81b7a709037744d7d788d/drivers/SmartThings/zwave-lock/src/lock_handlers/capabilities.lua); locator: lua:function CapabilityHandlers\.add\_credential\|update\_credential; check: manual-review
- Evidence: The main driver template registers the current lockUsers, lockCredentials, and user\-code report handlers; migrated marker state is emitted only when the persisted migration flag is true\.
  - [Pinned source](https://github.com/SmartThingsCommunity/SmartThingsEdgeDrivers/blob/6b8a9cf69462d314a7c81b7a709037744d7d788d/drivers/SmartThings/zwave-lock/src/init.lua); locator: lua:driver\_template\.capability\_handlers\|driver\_template\.zwave\_handlers; check: manual-review
- Evidence: When SLGA\_MIGRATED is unset or false, the pinned can\-handle function routes the device to the legacy subdriver\.
  - [Pinned source](https://github.com/SmartThingsCommunity/SmartThingsEdgeDrivers/blob/6b8a9cf69462d314a7c81b7a709037744d7d788d/drivers/SmartThings/zwave-lock/src/legacy-handlers/can_handle.lua); locator: lua:return function\(opts, driver, device, \.\.\.\); check: manual-review
- Evidence: The explicit legacy migration command emits lockUsers and lockCredentials state and then persists SLGA\_MIGRATED as true\.
  - [Pinned source](https://github.com/SmartThingsCommunity/SmartThingsEdgeDrivers/blob/6b8a9cf69462d314a7c81b7a709037744d7d788d/drivers/SmartThings/zwave-lock/src/legacy-handlers/init.lua); locator: lua:function migrate; check: manual-review
- Evidence: The SDF model defines an array of string lock\-code values but no user or credential identity, type, lifecycle, authorization, or privacy metadata\.
  - [Pinned source](https://github.com/one-data-model/ocf-models/blob/c97d095c239539b8242ceb4f12cf6deaeedb16e2/sdfObject/sdfobject-lock_code.sdf.json); locator: /sdfObject/lock\.code/sdfProperty/lockCodeList; check: resolved

Next steps:

- Review identity, authorization and privacy requirements before proposing a mapping\.
- Treat write payloads and read/event metadata as different interfaces\.
- Never submit real PINs, lock codes, credential values or household identifiers\.

## Boundaries

- One device model is indexed; the three feature records are not three supported devices\.
- All associated mappings are founder\-authored candidates without independent review\.
- No physical YRD156 or SmartThings hub has been tested for these records\.
- Published source artifacts do not prove behavior of your installed driver or firmware\.
- No installation instruction or automated Z\-Wave patch is offered for this case\.
- Community configuration is not manufacturer authority; hosted SDF models are not adoption evidence\.
- Device associations, classifications, license labels, and review states are catalog\-author declarations, not independently authenticated by this build\.
- Resolved locators establish field existence only, not the interpretation, completeness, runtime behavior, SDF conformance, or interoperability of an artifact\.
- Selectors, JSON5 and Lua locators need manual review\. No upstream Lua is executed\.
- Profile absence is not whole\-driver or UI absence\. A missing property in a particular SDF model is not a limitation of SDF itself\.
- Hardware\-evidence links are reported observations, not tests performed by this tool\. No patch availability is inferred\.
