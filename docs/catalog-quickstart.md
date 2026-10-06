# A five-minute device-evidence walkthrough

Requires Git, Python 3.11+ and internet for installation. No SmartThings account,
hub, Home Assistant token, AI key or physical lock is needed. The new commands
are a development increment, **not included in PyPI 0.2.0**.

Until these stacked PRs merge, clone the catalog's `codex/catalog-external-evidence`
branch. After merge, use its default branch instead. The core checkout below
always uses the exact `CORE_REVISION`, not an unpinned software branch.

```bash
git clone --branch codex/catalog-external-evidence \
  https://github.com/edgeloom-oss/edgeloom-catalog.git
cd edgeloom-catalog
git clone https://github.com/edgeloom-oss/edgeloom.git .edgeloom-core
git -C .edgeloom-core checkout "$(tr -d '[:space:]' < CORE_REVISION)"
python3 -m venv .venv
. .venv/bin/activate
python -m pip install ./.edgeloom-core
edgeloom catalog check .
edgeloom catalog build . --output _site
python -m http.server 4178 --bind 127.0.0.1 --directory _site
```

Open `http://127.0.0.1:4178/`. Search **YRD156**, **YRD210**, **battery**, or **0x0508**.
Open the report, then expand its evidence panel. Download Markdown if you want
to share a readable finding. Choosing Zigbee shows the new YRD210 comparison;
searching an absent model shows **Not indexed**, not an incompatibility verdict. Reports also work
with JavaScript disabled; only search requires it.

On Windows PowerShell, read the core pin with
`git -C .edgeloom-core checkout (Get-Content CORE_REVISION).Trim()`, create the
environment with `py -3 -m venv .venv`, and use
`.venv\Scripts\python.exe` instead of the activated `python`/`edgeloom` commands
(`python -m edgeloom.cli ...` is equivalent). Windows execution is not claimed
tested by this walkthrough's macOS/Ubuntu checks.

## Optional: reproduce source-byte checks

Stop the server with Ctrl-C first. This is the only catalog command that
downloads upstream files:

```bash
edgeloom catalog fetch . --cache .cache/source-bytes
edgeloom catalog build . --cache .cache/source-bytes --output _site
python -m http.server 4178 --bind 127.0.0.1 --directory _site
```

The source-byte state changes from `not-checked` to `matched` only after every
declared artifact digest matches. Selectors and Lua/JSON5 locations may still
need manual review. No mapping lifecycle or hardware-evidence state changes.

## What to look for

- **Auto-relock duration:** a gap in the examined profile/model, not proof
  that SmartThings settings or the full driver lack the feature.
- **Lock state:** a bounded binary correspondence, with information loss and
  an unresolved real-unit migration condition.
- **Access identity:** an unresolved representation problem; no PIN conversion
  or credential values are provided.
- **YRD210 battery:** distinct upstream adaptations at different layers;
  the raw-to-final entity mapping and physical-device behavior remain untested.
- **HA context:** generic actions and a simulated Schlage test are not model-
  specific Yale validation or independent EdgeLoom review.

Use **Report a mismatch** to contribute a version-specific observation. Remove
PINs, lock codes, tokens, private device/household identifiers and private logs.
No automatic Z-Wave patch is offered for this pilot. To see the separate
Zigbee patch/restore path on a disposable source copy, run
`python .edgeloom-core/scripts/no_hub_demo.py` from this directory. That is a
source-file exercise, not an installation or hardware test.
