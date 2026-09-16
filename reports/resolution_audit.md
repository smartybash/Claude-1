# Price resolution audit

No strategy test was run for this document and no performance number appears in
it. Every figure below is a property of the recorded files.

---

## Part 0 — the premise, corrected

The audit was requested on the basis that the 5-point grid is a defect. It is
not: the Step is set to 20, deliberately, and 20 × 0.25 = 5.00 exactly. That is
the cause, and it was stated in this conversation before the audit was asked
for.

That correction narrows Part 1 and changes nothing in Parts 2 to 5. A grid
chosen on purpose still determines what every depth feature physically
measured, and still leaves a set of ideas that were never measured at all.

---

## Part 1 — the cause, from the files alone

### Measured

| quantity | value |
|---|---|
| smallest non-zero gap, tape | **5.00** on 64 of 66 files; **0.25** on 2 |
| smallest gap, depth | **5.00** on 64 of 67 files; **0.25** on 3 |
| smallest gap, cumulative | **5.00** on every file checked |
| adjacent depth levels, coarse | min 5.00, median 5.00 |
| adjacent depth levels, fine | min 0.25, median 0.25 |
| distinct prices per session | median **103** |
| implied by session range at 0.25 | median **2,021** |
| ratio | **19.8×**, i.e. 20 |

### The decisive evidence

Two dates exist recorded **twice**, once each way:

| file | distinct prices | min gap | session range |
|---|---|---|---|
| `TAPE_NQ_20260812` | 1,510 | **0.25** | 377.25 |
| `TAPE_NQ_20260812_run2` | 77 | 5.00 | 380.00 |
| `TAPE_NQ_20260820` | 1,936 | **0.25** | 483.75 |
| `TAPE_NQ_20260820_run2` | 98 | 5.00 | 485.00 |

Same instrument, same replay source, same recorder binary, same dates, two
resolutions. That rules out instrument selection and feed limitation by
construction — a feed cannot deliver 0.25 and 5.00 for the same session — and
rules out chart type, since the recorder reads market-data events, not candles.

**It is a platform step setting, and it is correctable.** Confirmed by
experiment, not inferred.

### The setting

ATAS expresses this as a **price step / tick-size multiplier on the
instrument**, not on the indicator. Current value **20**; it must be **1** to
record a true 0.25 ladder. Check, in order:

1. **Instrument settings → Tick size / Price step** (chart → instrument
   properties). This is the one that governs the data objects the recorder
   reads, so it is almost certainly the one set to 20.
2. **Cluster/footprint chart settings → "Step"** if the recorder's chart is a
   cluster chart — it can override the instrument step for that chart.
3. **Chart → Price scale / "Grid step"** — cosmetic in most builds, but worth
   eliminating.

The arithmetic identifies the right field without guesswork: the field
currently reading **20** is the one, and setting it to **1** gives 0.25.

### Depth stream: 49 levels per side (0–49), both eras.

| | fine | coarse |
|---|---|---|
| ladder span, bid side | **12.25 pts** | **245.00 pts** |
| spread, median | 0.50 | **5.00** |
| spread, minimum | 0.25 | **5.00** |

---

## Part 2 — what the DoM features actually measured

### The one thing that is NOT broken

The coarse book **aggregates**; it does not sample. Reconstructed books from
the same date, same clock, matched 12.5-point window:

| | contracts | levels |
|---|---|---|
| 0.25 recording | 271 | 50 |
| 5.00 recording | 270 | 3 |

**Ratio 1.00.** No resting size is lost — the twenty ticks inside a rung are
summed into it. Tape row counts confirm the same for trades: 367,002 vs
366,593 rows for 12 August, 505,997 vs 505,560 for 20 August. **Every trade and
every contract is recorded. Only the price coordinate is quantised.**

That is why volume, delta and CVD survive intact, and it is the reason most of
the project is not invalidated.

### Feature by feature

| feature | intended | actually measured on coarse data |
|---|---|---|
| **best bid / offer** | the true inside quote | the top *populated 5-point bucket*; the true BBO is somewhere inside it, up to **4.75 pts** away |
| **spread** | 0.25 or 0.50, varying | **constant 5.00.** Zero variance, therefore zero information. Any spread feature measured nothing |
| **book imbalance over N levels** | size within N × 0.25 | size within **N × 5.00**. At 50 levels: intended 12.5 pts, actual **250 pts** — the whole visible book, not the inside |
| **volume within N levels** | as above | as above. The *total* is correct (aggregation is exact); the *price distance* is 20× wider than the name implies |
| **sweep depth** | ticks crossed by an aggressive order | **censored, not scaled.** 94–97% of multi-fill orders report span 0 because their fills fell inside one bucket. Only sweeps crossing a 5-point boundary registered at all |
| **liquidity pulling / stacking** | size appearing or leaving at a price | size appearing or leaving in a **5-point bucket**. A pull at one tick and a refill one tick away are the same event here and cancel out |
| **any threshold in "levels"** | N × 0.25 | **N × 5.00** |

**Explicitly measuring something other than their names imply:** spread (a
constant), book imbalance over N levels (a 250-point span, not an inside-book
measure), volume-within-N-levels (right total, wrong distance), sweep depth
(a censored near-binary), and pull/stack detection (blind within 5 points).

### Which era each depth study used

`imbalance.py` states in its own docstring that it ran on *"four clean sessions
at a 0.25 tick"* over *"the ten levels the feed provides"*. So the early
order-book work was done at correct resolution — but only 10 levels, which is
**2.5 points of visibility**, and on four sessions. Only three fine depth files
survive on disk today (`20260812`, `20260820`, `20260901_run2`); the rest were
overwritten by coarse re-recordings.

**Provenance was never recorded.** No script pins the dates it ran on, so for
studies other than `imbalance.py` the era has to be inferred. That is its own
audit finding and is why several rows below say "never tested" rather than
"wrong".

---

## Part 3 — classification of every result

Verdicts: **U** unaffected · **M** magnitude affected, ordering preserved ·
**I** invalid, must be retested at 0.25 · **N** never actually tested.

| hypothesis / feature | verdict | why |
|---|---|---|
| **Footprint diagonal imbalance** | **N** | The diagonal compares a price to the one *one tick* below. At 5.00 it compared aggregates 5 points apart, which is not the auction mechanic. The 3:1 test never ran on the quantity it names |
| **Stacked imbalance** | **N** | Could not physically form: 0.00% of bars showed a 3-run. Absence of the pattern was an artifact of the grid, not a property of the market |
| **Absorption at a level** (footprint extremes) | **I** | "At the bar's extreme" meant "within a 5-point bucket of the extreme". It measured *something*, but not the trader's concept, and the bucket mixes absorption with continuation |
| **Heavy level revisits** | **U** | The conclusion rests on a *placebo comparison* — real level vs a price shifted 25 points. Both arms are equally quantised, so the comparison is resolution-independent. The verdict survives |
| **Pullback continuation** | **M** | Departure threshold is 15 pts = 3 rungs, comfortably resolvable. Level location carries ±2.5 pts of noise, which widens the entry but cannot create the effect |
| **Order-size gating** (25/50-lot net delta) | **U** | Uses order volume and aggressor only. No price distance anywhere in it. Fully valid |
| **Sweep depth gating** | **N** | 94–97% censoring. The arm was near-always zero. It was never tested |
| **DoM / book imbalance** | **N** on coarse, **U-but-thin** on fine | On coarse data it measured a 250-point span under an inside-book name. On the 3 fine sessions it was correct but only 2.5 points deep and far too few sessions to conclude from |
| **Spread features** | **N** | Constant on coarse data |
| **Liquidity pull vs fill** | **I** | Needs tick-level book changes; 5-point buckets hide the pull-and-refill that defines it |
| **VWAP stretch** | **U** | Built from price, volume and a rolling standard deviation measured in points. Quantisation adds at most ±2.5 pts of rounding to a feature whose scale is tens of points, and volume is exact |
| **CVD level and CVD change** | **U** | Volume and aggressor only |
| **Structure / BOS timeframe** | **M** | Pivots are quantised to 5 pts, which blurs pivot *location* but not pivot *ordering* |
| **Level fades, gap fill** (long history) | **U** | Sourced from Alpha Vantage bars, never from the ATAS tape. Untouched by this issue |

---

## Part 4 — corrections to the record

The distinction being drawn: **killed** means measured and found wanting;
**never measured** means the instrument could not see it.

Three conclusions must be restated.

**1. Sweep depth**

- Previously: *"no order-flow gate separates the structure trade — sweep delta
  included."*
- **Corrected: sweep depth was never tested.** 94–97% of multi-fill aggressive
  orders reported zero price span because their fills fell inside a single
  5-point bucket. The gate was almost always off for mechanical reasons, so its
  failure carries no information about sweeps.

**2. Footprint imbalance and stacked imbalance**

- Previously: *"footprint is dead on this data"* — accurate as stated, but it
  has been read as *footprint is dead*.
- **Corrected: diagonal and stacked imbalance were never tested.** They are
  defined one tick apart and the data is twenty ticks coarse. The observation
  that stacks never occurred is a fact about the grid. Absorption and level
  revisits *were* tested and did fail, and the placebo result stands.

**3. Order-book imbalance**

- Previously: *"book imbalance does not predict."*
- **Corrected: not tested at the depth the name implies.** On coarse data it
  measured a 250-point span; on the three fine sessions it measured 2.5 points,
  which is too shallow to see a level before price reaches it — `depth_audit.py`
  flagged exactly this risk when it was written and the flag was not acted on.

**Not corrected — these stand as killed:** level fades, gap fill, CVD level,
CVD change, order-size gating, heavy-level revisits, the footprint bar-shape
study, and the lookahead and overlap errors. None depended on price resolution.

---

## Part 5 — cost of fixing

### Can it be fixed

Yes. Proven by the two dates already recorded both ways with the same binary.

### Replay reach

Three months, so today it starts around **16 June**. The pool runs 17 June to
11 September, and the earliest dates fall out of reach one per day. **Every
session currently held is still re-recordable, but not for long** — 17 June
expires within days.

### How many sessions

**61 of 63** unique dates need re-recording. Two are already fine (12 and 20
August), though their coarse `_run2` twins currently shadow them in the loader,
which keys on the date and takes the later file.

### File sizes, measured

| stream | coarse | fine | ratio |
|---|---|---|---|
| depth | 5.0 MB/session | 12.8 MB/session | **2.6×** |
| tape | 2.1–2.8 MB | 2.5–3.5 MB | **~1.2×** |
| cumulative | — | — | ~1.2× expected |

Current totals: tape 159 MB, cum 100 MB, depth 343 MB = **602 MB**.
Projected at 0.25: **≈1.2 GB**. Tape row counts are unchanged, so the growth is
digits and depth rows, not events.

### What can be reused

**Reusable without regeneration** — anything whose inputs are volume, time or
aggressor:

- bar aggregates, session VWAP, CVD and all delta series
- session-level bookkeeping: rosters, coverage, full-session classification
- the discovery/holdout split, which is by date and is unaffected

**Must be regenerated** — anything measuring price distance at fine scale:

- all footprint ladders and every shape built from them
- every depth feature, all thresholds expressed in levels
- sweep depth

**Housekeeping:** the parquet cache keys on source size and mtime, so it
invalidates itself on re-record — no manual clearing. The loader's date keying
must be fixed before any re-record, or a coarse `_run2` will keep shadowing a
fine original, which is exactly what is happening to 12 and 20 August today.

### Recommendation on sequencing

Re-recording is only worth its cost for the ideas in the **N** rows — the ones
never measured. The **U** rows gain nothing. If the step is corrected, the
cheapest informative move is a small number of fresh sessions at 0.25 to
establish whether the untested ideas show anything at all, before committing to
61 re-recordings.
