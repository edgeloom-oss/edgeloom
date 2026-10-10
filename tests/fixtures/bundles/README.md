# Synthetic Device Evidence Bundle fixture

This **document-only** fixture exercises offline validation, rendering, export,
and verification from an installed wheel. It needs no SDF model, hub, device,
account, or network connection. The manufacturer, model, manual, and URL are
synthetic. It is not compatibility evidence or a physical-device observation.

From the repository root, with the current development version installed:

```sh
edgeloom bundle check tests/fixtures/bundles demo
edgeloom bundle export tests/fixtures/bundles demo --output /tmp/edgeloom-demo.zip
edgeloom bundle verify /tmp/edgeloom-demo.zip
```

Choose a new output filename if that archive already exists. Export refuses to
overwrite files. The manifest pins the document metadata bytes, not an actual
manual or evidence of its authenticity. A future hardware test is explicitly a
plan, not a completed experiment.
