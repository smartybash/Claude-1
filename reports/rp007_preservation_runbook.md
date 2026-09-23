# RP-007 data preservation — the sixteen expiring sessions

**Authorised as data preservation only.** No outcome is calculated, no level
reaction is inspected, no sealed date is opened.

---

## 0. I cannot execute this step, and here is the proof rather than the excuse

The recording is done by ATAS Market Replay on a Windows machine. This session
runs in a Linux container. Checked, not assumed:

| check | result |
|---|---|
| `which dotnet` / `which mono` | **nothing** |
| `find / -iname "ATAS*.dll" -o -iname "OFT*.dll"` | **nothing** |
| Desktop / ATAS export folder | **does not exist** |
| `uname -s` | `Linux` |

This is the same wall `reports/recorder_completeness_audit.md` hit: *"The ATAS
assemblies are not in the repository… no NuGet cache, no .NET SDK."* Nothing has
changed.

**So this document is the runbook, and `scripts/orderflow/verify_preservation.py`
is the verification that runs the moment the bundles land.** The harness is
written, committed and already executed against today's files to establish the
baseline (§4). The step that needs a Windows machine is the only step I am
handing back.

**The clock is the reason this is urgent.** Replay reach is three months. On
2026-09-23 the earliest reachable date is ≈2026-06-23, and one more date falls
out of reach every day. The sixteen targets are all inside reach today. They
will not be later.

---

## 1. The sixteen target dates

```
20260821 20260824 20260825 20260826 20260827 20260828 20260831 20260901
20260902 20260903 20260904 20260907 20260908 20260909 20260910 20260911
```

**Not targets, and why:**

| date | reason |
|---|---|
| `20260617` | outside replay reach — three months from 2026-09-23 stops at ≈2026-06-23 |
| `20260712` | a Sunday. No cash session exists |
| June 2026, `20260723` | **sealed.** Not re-recorded, not read, not touched |

`20260907` is a CME early close (13:00 ET, ~23,000 RTH prints against a median
of ~330,000). It is re-recorded for completeness and will correctly fail the
full-session test. That is a calendar fact, not a defect.

---

## 2. The settings that matter

The recorder binary is **not** the problem. Its `BuildTag` is `2026-09-17.z`,
the same build that produced all 46 existing 0.25 recordings. The defect was
always a **platform instrument setting**, established by experiment: two dates
exist recorded twice by the same binary, once at 0.25 and once at 5.00.

| setting | where | required value |
|---|---|---|
| **Price step / Tick size** | ATAS **instrument settings** (chart → instrument properties) | **1**, not 20. `20 × 0.25 = 5.00` is the whole cause |
| **Cluster/footprint `Step`** | chart settings, if the recorder's chart is a cluster chart | **1** — it can override the instrument step for that chart |
| **Replay mode** | Market Replay | **Ticks + DOM.** The recorder's own status text says the other modes carry no tick or depth data |
| Record tape | recorder settings | on |
| Record depth | recorder settings | on |
| Record individual fills | recorder settings | on — this is the `CUM_` stream |
| BBO throttle ms | recorder settings | as configured for the July–August campaign; BBO exists for all 46 fine dates and none of the coarse ones |
| Compress output | recorder settings | on (`.csv.gz`) |
| Record tape around the clock | recorder settings | on — overnight levels need the 22:00–13:30 UTC window |

**Verify the step before recording sixteen sessions, not after.** The platform's
own `TickSize` is printed into `_status.txt`; on a correct run it reads
`TickSize = 0.25`. One session recorded and checked first costs one session; the
wrong setting discovered at the end costs sixteen and the replay window.

---

## 3. Delivery

The recorder folds each day into one `NQ_<date>.zip` containing the gzipped
`TAPE_`, `L2_`, `CUM_`, `BBO_` files and `_status.txt`. Drop the zips anywhere
under `data/`; `tape.unpack_bundles()` routes each part to its folder and
`_status.txt` to `data/status/`, and the verification harness calls it first.

**`_status.txt` must be included.** It is the only provenance record of what the
platform's step actually was, and the existing coarse dates have none — §4 shows
sixteen `MISSING` rows, which is precisely the gap this fixes.

Where a new fine recording lands beside an existing coarse one, **nothing needs
deleting**. The loader's rule is resolution first, then row count, so a 0.25
file automatically supersedes its 5.00 twin.

---

## 4. Baseline, measured today

`scripts/orderflow/verify_preservation.py` was run against the current files.
This is the "before" state and the thing the re-recording must change:

| check | now |
|---|---|
| verified at 0.25 on tape + depth + cum | **0 of 16** |
| with BBO as well | **0 of 16** |
| tape present, aggressor side `B`/`S` | 16 of 16 |
| cumulative fills present | 16 of 16 |
| depth present | 16 of 16 |
| **BBO present** | **0 of 16** |
| **`_status.txt` present** | **0 of 16** — no provenance exists for any of them |
| full cash sessions | 15 of 16 (`20260907` is the early close) |

Measured minimum non-zero price gap, today: **5.00 on tape, depth and cumulative
for all sixteen**, except `20260901` (depth and cumulative already 0.25, tape
5.00) and `20260821` (depth 1.00). Those two are anomalies of the original
capture and are not usable while their tape is coarse.

The harness passes a date only when tape, depth and cumulative all measure
**0.25**, from the decoded prices themselves — the compact `#fmt=1` header
declares `tick=0.25` even for a coarse recording, because a 5.00 file simply has
every offset on a multiple of 20. The declared tick is never trusted.

The harness also refuses to run at all if a sealed date appears in the target
list. That is a guard in code, not a promise in prose.

---

## 5. Classification of the recovered dates

**All sixteen are additional discovery data. None is validation.**

Per the standing rule: previously examined dates do not become pristine
validation merely because they are re-recorded at finer resolution, and
provenance must *prove* otherwise before any other classification is allowed.

It does not prove otherwise for any of the sixteen. Every one lies inside the
period this project has been working in; `scripts/orderflow/roster.py` pins the
discovery window as 2026-07-01 → 2026-09-08, which covers thirteen of them
outright; and per-script date provenance was never pinned, which is a finding
the roster's own header records.

One asymmetry, recorded rather than exploited: **`20260909`, `20260910` and
`20260911` fall outside the roster's discovery window** and would be holdout
under that rule. No provenance proves they were never read, and the roster
itself warns that a count is not a roster. They go to discovery with the rest.
Shrinking the validation pile is the only direction a reclassification is
allowed to move once it is ambiguous.

**Effect on the RP-007 data roles:**

| role | before | after preservation |
|---|---|---|
| NQ discovery, 0.25, full sessions | 35 | **50** (35 + 15 new full sessions) |
| NQ internal validation (sealed) | 9 | **9, unchanged and unread** |
| NQ final out-of-sample | 0 | **0** |
| total 0.25 dates | 46 | **62** |
| calendar span at 0.25 | 2 months | **~3 months** |

Fifty discovery sessions raises the pooled minimum detectable effect from about
±13.7 points to about ±11.5, and the per-family figure from ±53 to ±44.
**Preservation does not fix the power problem** — it was never going to, which
is why Stage 1A1 moves to QQQ. It preserves optionality that expires this week,
and it is worth doing for that reason alone.

---

## 6. What happens next, in order

1. Re-record the sixteen dates at Step 1. **Verify the first one before
   recording the other fifteen.**
2. Deliver the bundles, including `_status.txt`.
3. Run `python3 scripts/orderflow/verify_preservation.py`. It writes
   `reports/rp007_preservation_verification.csv` and prints the funnel.
4. Any date failing the 0.25 check is re-recorded or dropped. **No coarse date
   enters RP-007 at any stage.**
5. Stage 1A2 does not open until the QQQ screen has frozen no more than three
   level families.

**No outcome is calculated at any point in this document. No level reaction is
inspected. Sealed dates remain unread.**
