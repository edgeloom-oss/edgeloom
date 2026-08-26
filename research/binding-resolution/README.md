# Binding resolution: can a device capability be described once and bound twice?

EdgeLoom's schema is deliberately platform-scoped, because capability namespaces
do not port between ecosystems. That raises an obvious question: is there a layer
*underneath* the platform binding — a neutral description of what a device
actually does — that a driver for any platform could be generated from or checked
against?

This is the measurement that answers it, for door locks. It exists because the
answer decides what EdgeLoom builds next, and because reasoning about it produced
the wrong answer twice before the data was consulted.

## The result

**Build a lexicon, not a format.** Concepts port; encodings do not.

| | cells | share of bound cells |
| --- | ---: | ---: |
| `RESOLVED-1:1` | 95 | **59.4%** |
| `RESOLVED-LOSSY` | 65 | 40.6% |
| `AMBIGUOUS-1:N` | 0 | **0.0%** |
| `UNBOUND` | 236 | (device lacks the feature) |

44 Z-Wave lock products × 9 capabilities = 396 cells, of which 160 have a binding
on both protocols. Full output in [`results/summary.txt`](results/summary.txt);
every scored cell in [`results/cells.json`](results/cells.json).

The accompanying
[`results/cells.evidence.json`](results/cells.evidence.json) pins the exact
committed bytes, source revision, asserted licence, and deterministic parse
result using EdgeLoom's v0.1 evidence-record contract. It is an identity and
check record, not independent validation of the experiment's conclusions.

## What is being measured

Not "does this capability exist on both protocols" — that question cannot fail.
All nine capabilities exist in both the Zigbee Cluster Library and Z-Wave
Configuration CC, and none of them is surfaced by any of the 42 SmartThings lock
profiles across three protocols. An agreement rate would come out near 100% for
reasons unrelated to the hypothesis.

What is measured is whether a neutral record **round-trips**: can a single
description resolve to a correct, unambiguous, type-faithful binding on each
protocol?

Each `(device, capability)` cell scores as:

- `RESOLVED-1:1` — exactly one binding, type and unit faithful
- `RESOLVED-LOSSY` — exactly one binding, but the encoding differs
- `AMBIGUOUS-1:N` — several candidates that are not the same concept
- `UNBOUND` — the device does not implement it

## The decision rule, stated before the run

- ≥60% `RESOLVED-1:1` and <10% `AMBIGUOUS` → build the format
- >40% `AMBIGUOUS`, or <25% `RESOLVED-1:1` → stop
- otherwise → build a lexicon plus an index

At 59.4% / 0.0% the middle branch fires. The concepts map cleanly; the encodings
need a lexicon entry to survive the trip.

## The control

The lexicon is hand-authored, so the obvious objection is that it is a wrapper
over work anyone could do with string matching. Re-scoring with naive CamelCase
keyword matching prices it:

| | ambiguous cells |
| --- | ---: |
| naive keyword matching | 100 of 228 (**43.9%**) |
| curated lexicon | 0 of 160 (**0.0%**) |

That gap is the content.

## What the losses actually are

Five capabilities round-trip perfectly: `Language`, `SoundVolume`,
`OperatingMode`, `WrongCodeEntryLimit`, `UserCodeTemporaryDisableTime`.

Four are uniformly lossy, and every loss is enumerable:

- `AutoRelockTime` — ZCL types it `uint32`; Z-Wave devices cap the range at 180
  or 127 seconds.
- `EnableOneTouchLocking`, `EnableInsideStatusLED`, `EnablePrivacyModeButton` —
  ZCL booleans are `0`/`1`; Z-Wave encodes true as `255`.

Losses being *recordable* is the whole argument for a lexicon. A bare format
would have to pick one encoding and silently corrupt the other.

## Something the corpus disproved

Counting parameter labels across the Z-Wave lock corpus suggests severe
ambiguity: eleven distinct labels can be read as "auto relock", and they are not
synonyms — some are boolean enables, some the auto delay, some the manual delay,
some the remote delay.

Per *device* that collapses. Measured co-occurrence across the 34 relock-bearing
products:

| combination | products |
| --- | ---: |
| `Auto Relock` + `Auto Relock Time` | 20 |
| `Dipswitch setting: Autolock` (Kwikset, read-only) | 6 |
| `Auto Lock` + `Lock & Leave` (Schlage) | 6 |
| singletons | 3 |

Twenty of thirty-four carry exactly the enable-plus-duration pair, which is an
idiom, not an ambiguity. Corpus-level label counting and per-device binding are
different questions, and only the second one matters here.

## Reproducing it

```bash
pip install -r research/binding-resolution/requirements.txt
python research/binding-resolution/fetch_data.py     # corpora, ~1 minute
python research/binding-resolution/build_index.py    # join, writes results/
python research/binding-resolution/measure.py        # score and report

# Record the exact committed result bytes after reproducing the run.
edgeloom audit research/binding-resolution/results/cells.json \
  --source-uri https://github.com/edgeloom-oss/edgeloom/blob/784718c/research/binding-resolution/results/cells.json \
  --source-ref 784718c --license Apache-2.0 \
  --artifact-status experimental \
  --output research/binding-resolution/results/cells.evidence.json
```

Deliberately not part of `make check`: it needs network access and a 2,384-file
clone, neither of which belongs in a test suite. `results/cells.json` and `results/summary.txt` are committed so the numbers can be
read without running anything; the 926K device index is regenerated, not stored.

## Sources and licences

- SmartThings lock fingerprints — [SmartThingsEdgeDrivers](https://github.com/SmartThingsCommunity/SmartThingsEdgeDrivers), Apache-2.0
- Z-Wave device configs and parameter labels — [zwave-js](https://github.com/zwave-js/zwave-js), MIT
- ZCL/Matter attribute identities — Matter data model, Apache-2.0

`zigpy` is the other obvious source of ZCL attribute definitions and is **GPL-3.0**,
so it cannot be vendored into this Apache-2.0 project. Nothing here depends on it.

## Limits worth stating

- **Locks only.** Whether this generalises to sensors is untested, and there is
  reason to doubt it: the four attributes EdgeLoom maps for battery sensors
  (`IdentifyTime`, `DeviceEnabled`, `CheckInInterval`, `FastPollTimeout`) are
  Zigbee mechanisms — Poll Control has no Z-Wave counterpart, which uses Wake Up
  Command Class — so a neutral layer has nothing to say about them.
- **The corpus is small.** 44 products, and 8 of 61 SmartThings fingerprints do
  not resolve at all.
- **No hardware.** Every binding is reasoned from published definitions. That a
  device *specifies* an optional attribute does not mean any given unit
  implements it.
- **The lexicon is one author's judgement.** Two contributors handed Yale's
  parameter set might disagree about whether `Manual Relock Time` is the same
  neutral term as `Auto Relock Time`. Reproducibility across annotators is the
  obvious next test and has not been run.
