# Discovering drivers

Enumerate Edge drivers and Zigbee/Z-Wave manufacturer fingerprints from GitHub or a local
clone, and flag drivers that have no capability mapping yet. This is the
`discovery` component, reachable as `edgeloom discover`.

## Driver Discovery Pipeline

Use the discovery CLI to scan either the public SmartThings Edge repository
directly from GitHub or any local clone that contains official drivers. The
tool aggregates every `fingerprints.yml`, summarizes the devices they target,
and highlights drivers that still lack capability mappings in
`custom_capability_list.config`.

Discover via GitHub (requires internet; optional `GITHUB_TOKEN` for higher
rate limits):

```bash
edgeloom discover \
  --source github \
  --repo SmartThingsCommunity/SmartThingsEdgeDrivers \
  --branch main \
  --output discovery/catalog.json
```

Work offline against a local clone (or any folder that holds driver
directories with `fingerprints.yml`):

```bash
edgeloom discover \
  --source local \
  --local-dir ~/edge-drivers \
  --driver-subpath drivers/SmartThings \
  --output discovery/catalog-local.yaml \
  --format yaml
```

`unsupported_drivers` means no entry in the selected capability config, not
that the device is incompatible or an automatic patch is available. Z-Wave
manufacturer fingerprints retain `manufacturer_id`, `product_type`,
`product_id` (normalized `0x0000` values), profile assignment, ID and label.
Marketing model/manufacturer names are not inferred from protocol identifiers.
Generic Z-Wave and Matter fingerprints are not parsed by this increment.

This driver inventory is distinct from the source-linked device evidence
[catalog](catalog.md). Discovery does not execute drivers or establish their
behavior on a real device. Z-Wave discovery does not add Z-Wave patch support.
