# RP-007 — Reference Level Rejection, Absorption and Reversal
## Data inventory and Stage 1A proposal. **Stage 1A is not run.**

No level was tested, no interaction was counted, no outcome was measured. Every
number below is a property of the recorded files, of arithmetic declared in
advance, or of results already on this project's record.

---

# 1. Data inventory

## 1.1 Resolution, measured from actual prices

Resolution was measured as the **minimum non-zero gap between distinct traded
prices in the file**, per date, per stream — not from the file format. The
correction ledger already records that format and resolution are independent
(`TAPE_NQ_20260820.csv.gz` is plain gzip and true 0.25; its `_run2` twin is
5.00), so the format was ignored entirely.

**This inventory corrects `reports/resolution_audit.md`, which is stale.** That
document concluded "61 of 63 unique dates need re-recording" and "none at 0.25
after 2026-08-20". A re-recording campaign ran on 16–17 September (file mtimes
`Sep 16 18:39` → `Sep 17 14:00`) in the compact `#fmt=1` format and lifted the
count from 31 to **46**. The campaign worked forward from 18 June and **stopped
at 20 August**; it never reached the 21 August – 11 September block.

| | dates |
|---|---|
| distinct NQ session dates on disk | **64** |
| **tape at true 0.25** | **46** |
| tape at 5.00 | 18 |
| **all four streams at true 0.25** | **46** |
| of those, full cash sessions | **44** |

**0.25 block: 2026-06-18 → 2026-08-20, contiguous, no missing trading day.**

**5.00 block, excluded entirely from RP-007:** `20260617 20260712 20260821
20260824 20260825 20260826 20260827 20260828 20260831 20260901 20260902 20260903
20260904 20260907 20260908 20260909 20260910 20260911`.

Two anomalies inside the coarse block, recorded and not used: 20260901 has 0.25
depth and cumulative files but a 5.00 tape, and 20260821's depth measures a
1.00 step. Neither date has a usable tape, so neither enters any sample.

## 1.2 File selected for each date

The loader keeps **resolution first, then row count** when a date was recorded
more than once. The selected file for every 0.25 date:

| date | file | date | file |
|---|---|---|---|
| 20260618 | `TAPE_NQ_20260618_part3.csv.gz` | 20260722 | `TAPE_NQ_20260722.csv.br` |
| 20260619 | `TAPE_NQ_20260619.csv.gz` | 20260723 | `TAPE_NQ_20260723.csv.br` |
| 20260622 | `TAPE_NQ_20260622.csv.gz` | 20260724 | `TAPE_NQ_20260724.csv.br` |
| 20260623 | `TAPE_NQ_20260623.csv.gz` | 20260727 | `TAPE_NQ_20260727.csv.gz` |
| 20260624 | `TAPE_NQ_20260624.csv.gz` | 20260728 | `TAPE_NQ_20260728.csv.br` |
| 20260625 | `TAPE_NQ_20260625.csv.br` | 20260729 | `TAPE_NQ_20260729.csv.br` |
| 20260626 | `TAPE_NQ_20260626.csv.br` | 20260730 | `TAPE_NQ_20260730.csv.br` |
| 20260629 | `TAPE_NQ_20260629.csv.br` | 20260731 | `TAPE_NQ_20260731.csv.br` |
| 20260630 | `TAPE_NQ_20260630.csv.br` | 20260803 | `TAPE_NQ_20260803.csv.br` |
| 20260701 | `TAPE_NQ_20260701.csv.gz` | 20260804 | `TAPE_NQ_20260804.csv.br` |
| 20260702 | `TAPE_NQ_20260702.csv.gz` | 20260805 | `TAPE_NQ_20260805.csv.br` |
| 20260703 | `TAPE_NQ_20260703.csv.br` | 20260806 | `TAPE_NQ_20260806.csv.br` |
| 20260706 | `TAPE_NQ_20260706.csv.br` | 20260807 | `TAPE_NQ_20260807.csv.br` |
| 20260707 | `TAPE_NQ_20260707.csv.br` | 20260810 | `TAPE_NQ_20260810.csv.br` |
| 20260708 | `TAPE_NQ_20260708.csv.br` | 20260811 | `TAPE_NQ_20260811.csv.br` |
| 20260709 | `TAPE_NQ_20260709.csv.br` | 20260812 | `TAPE_NQ_20260812.csv.br` |
| 20260710 | `TAPE_NQ_20260710.csv.br` | 20260813 | `TAPE_NQ_20260813.csv.br` |
| 20260713 | `TAPE_NQ_20260713.csv.gz` | 20260814 | `TAPE_NQ_20260814.csv.br` |
| 20260714 | `TAPE_NQ_20260714.csv.br` | 20260817 | `TAPE_NQ_20260817.csv.br` |
| 20260715 | `TAPE_NQ_20260715.csv.br` | 20260818 | `TAPE_NQ_20260818.csv.br` |
| 20260716 | `TAPE_NQ_20260716.csv.br` | 20260819 | `TAPE_NQ_20260819.csv.br` |
| 20260717 | `TAPE_NQ_20260717.csv.br` | 20260820 | `TAPE_NQ_20260820.csv.br` |
| 20260720 | `TAPE_NQ_20260720.csv.gz` | | |
| 20260721 | `TAPE_NQ_20260721.csv.br` | | |

Depth, cumulative and BBO files follow the same date and the same selection
rule (`L2_NQ_*`, `CUM_NQ_*`, `BBO_NQ_*`).

## 1.3 Measured minimum non-zero price gap

| stream | 0.25 | 5.00 | other | files |
|---|---|---|---|---|
| tape | 46 dates | 18 dates | — | 104 |
| depth | 50 files | 53 files | 1.00 × 2, unreadable × 2 | 107 |
| cumulative | 48 files | 53 files | — | 101 |
| **BBO** | **46 files** | 0 | — | **46** |

BBO exists **only** for the 46 fine dates and is 0.25 on every one. The compact
`#fmt=1` header declares `tick=0.25` and integer offsets; a 5.00 recording
encoded in that format still shows offsets in multiples of 20, so the measured
gap and not the header tick is what is reported here.

## 1.4 Session coverage

Recorder clock is **UTC** (the CME maintenance halt sits at 21:00–22:00 UTC =
17:00–18:00 ET). Every fine recording runs the **full 24-hour cycle**
(00:00:00.0x → 23:59:5x), except four early-close days that end at 20:59.

| | dates |
|---|---|
| fine dates | 46 |
| **full cash sessions** (≥ 0.97 × 390 min, ≥ 40,000 RTH prints) | **44** |
| not a full session | **20260619**, **20260703** — both CME 13:00 ET early closes |

Median RTH prints per fine full session **≈ 355,000**; mean RTH range **282
points**.

## 1.5 Streams available on the 46 fine dates

| item | available | source |
|---|---|---|
| **Tape trades** | **yes**, ~360k RTH prints/session | `TAPE_NQ_*`: `time, price, volume, aggressor` |
| **Aggressor side** | **yes**, `B`/`S` on every print, no nulls | same |
| **Bid-traded volume by price** | **yes** — exact, by summing `volume` where `aggressor = S` per 0.25 price | derived from tape |
| **Ask-traded volume by price** | **yes** — same with `aggressor = B` | derived from tape |
| **Cumulative order and fill data** | **yes** on 47 files: `aggressor, first_price, last_price, volume, fills` per aggressive order | `CUM_NQ_*` |
| **Depth snapshots** | **yes**, 50 levels per side (0–49), 0.25 grid = **12.25 points of visible ladder per side** | `L2_NQ_*` |
| **BBO** | **yes**, 46 dates, 0.25, one-minute resync | `BBO_NQ_*` |
| **MBO** | **no** — `data/mbo/` is empty | — |

**Stage 1B is feasible on these 46 dates and on no others.** Exact footprint
reconstruction needs price + aggressor + volume at 0.25, which the fine tape
gives directly; the cumulative stream additionally gives per-order fill counts
and sweep spans, which the resolution audit showed were 94–97% censored on the
coarse grid and are 82% zero-span at 0.25.

## 1.6 Contract rolls — checked, none present

NQ June 2026 expired 2026-06-19 and September 2026 expires 2026-09-18, so a roll
could sit inside the fine block. It does not.

* Largest single-print jump anywhere in the 46-date 0.25 block: **65.00 points**
  (20260722), against a ~900-point roll basis.
* The one candidate — a **−936 point** gap between the 22 June RTH close
  (30654.25) and the 23 June RTH open (29718.25) — is **not a roll**. The
  continuous 24-hour tape for 23 June opens at 30574.25 and closes at 29748.25
  with a maximum consecutive-print jump of 22.00 points. Price *walked* the
  distance. It is a violent session, not a contract change.

**The tape follows one contract continuously across the whole fine block. No
roll adjustment is required, and this is measured rather than assumed.**

## 1.7 Dates previously examined

The roster (`scripts/orderflow/roster.py`) pins **discovery = 2026-07-01 →
2026-09-08**. Every one of the 36 open fine dates falls inside it.

Explicitly documented prior use:

* **16 sessions**, order-flow batch: `0701 0702 0706 0707 0708 0709 0710 0713
  0714 0715 0716 0717 0720 0721 0812 0820`.
* **20 discovery sessions at 0.25**, pullback batch.
* **20 discovery sessions**, bar-resolution gate.
* **21 sessions**, European session profile (the 16 above plus `0703 0722 0724
  0727 0728`).

Provenance was not pinned by every script. **I am therefore treating all 36 open
fine dates as previously examined**, not only the ones a report happens to name.
Under the standing rule they may be used for discovery and may not be presented
as untouched validation.

## 1.8 Sealed dates

`SEALED_PREFIX, SEALED_DATES = "202606", {"20260723"}` — **the whole of June
2026 plus 23 July 2026.**

Sealed dates at 0.25: `20260618 20260619 20260622 20260623 20260624 20260625
20260626 20260629 20260630 20260723` — **10 dates, 9 of them full sessions**
(20260619 is an early close).

**They remain unread.** Nothing in this proposal opens them.

## 1.9 Non-NQ price history on disk

| file | span | sessions | resolution | overnight |
|---|---|---|---|---|
| `QQQ_1m.parquet` | 2021-01-04 → 2026-08-31 | **1,421** | $0.01 | RTH only, 09:30–15:59 |
| `QQQ_1m_eth.parquet` | 2021-01-04 → 2026-08-31 | 1,399 | $0.01 | **04:00–19:59 only** |
| `QQQ_1m_holdout.parquet` | 2016-01-04 → 2020-12-31 | 1,259 | $0.01 | RTH only |
| `data/parquet/NQ_5min.parquet` | 2026-06-17 → 2026-07-06 | ~14 | 5-minute bars | — |
| `nq_30min_eth.json` / `nq_1h_eth.json` | 2026-05-12 → 2026-08-18 | 54–78 | 30-min / 1-hour | — |

**There is no long NQ one-minute history anywhere in this project.** The only
NQ price data is the 64 recorded dates plus a handful of 5-minute and 30-minute
bar files, all too coarse or too short to matter.

`QQQ_1m_eth` covers **04:00–19:59 US pre/post market, not a Globex overnight**.
An "overnight high" computed on it is a *pre-market* high, a materially
different object from NQ's 22:00–13:30 UTC overnight auction. Three of the
fifteen proposed level families are therefore not portable to QQQ.

**2016–2020 is spent.** The FOMC ruling states that after that test no future
family uses 2016–2020 as out-of-sample. `QQQ_1m_holdout.parquet` is not
available to RP-007.

## 1.10 Forward collection path

* Replay reach is **three months**. Today is 2026-09-23, so the earliest
  re-recordable date is roughly **2026-06-23**. 17 June and everything older is
  permanently out of reach at 0.25.
* **The 16 coarse dates 2026-08-21 → 2026-09-11 are inside replay reach and can
  be re-recorded at 0.25 now.** This is the single cheapest data action
  available to this project and it is expiring at one date per day. It would
  lift the fine block from 46 to 62 dates and, critically, extend it into a
  third calendar month.
* Beyond that, **live forward recording only**, at ≈21 sessions per month.
* Storage: ≈2.6× for depth, ≈1.2× for tape and cumulative at 0.25.

---

# 2. Prior evidence on this exact question — stated before Stage 1A, not after

This desk has **already tested five of the fifteen proposed level families**, on
a sample 40× larger than the NQ block, and the answer was no.

`reports/levels_predictive_result.md`, 1,414 QQQ sessions, 2021–2026:

| level | touches | reaction at 30 min | at 60 min |
|---|---|---|---|
| PDH | 545 | **44.8%** | 46.7% |
| PDL | 468 | 48.1% | 49.6% |
| VAH | 644 | 47.2% | 48.8% |
| VAL | 586 | 51.5% | 49.9% |
| POC | 661 | 49.0% | 52.4% |

Null 50%, pre-registered bar 55%. **0 of 8 cleared.** The one directional lean —
PDH at 44.8% — points *against* the folk belief: price reaching yesterday's high
is slightly more likely to carry through than to reject.

The turning-point test found prior-day levels genuinely closer to the session's
own extremes than a stranger's level set (0 of 200 shuffles beat them) and the
size of that effect was **3.4 bps** — detectable and immaterial.

**Three things follow, and they belong in the design rather than in the
discussion of the result.**

1. RP-007 is **not** a fresh question for PDH, PDL, VAH, VAL and POC. It is a
   re-test of a null, on a different instrument, with a shifted-price control
   the earlier study did not have and a reclaim-plus-rotation outcome the
   earlier study did not measure. Those are real differences and they justify
   re-asking — they do not make the prior null disappear.
2. A positive Stage 1A result for any of those five families on 35 NQ sessions
   **must be reconciled with 1,414 QQQ sessions of null**, and the default
   reading of a conflict that size is that the small sample is wrong.
3. The genuinely untested families are the ten the earlier study never touched:
   prior RTH close, prior RTH VWAP, overnight high/low/midpoint, IB
   high/low/midpoint, current-session VWAP, and round prices.

My prior, stated now: **the ten untested families will behave like the five
tested ones.** I expect Stage 1A to fail, most likely on the shifted-control
comparison and on starting geometry.

---

# 3. Data roles — proposed and frozen

| role | dates | n | status |
|---|---|---|---|
| **Discovery** | 2026-07-01 → 2026-08-20, full sessions, 0.25 | **35** | previously examined; usable for discovery, **never presentable as validation** |
| **Internal validation** | sealed: 2026-06-18 → 2026-06-30 + 2026-07-23, full sessions, 0.25 | **9** | **sealed, unread.** Opened only if Stage 1A passes on discovery |
| **Final out-of-sample** | forward collection only | **0 today** | does not exist |
| **Excluded — coarse** | 18 dates at 5.00 | 18 | not used at any stage |
| **Excluded — part session** | 20260619, 20260703 | 2 | rejection and rotation windows are undefined on a 13:00 ET close |

Discovery months: **July 21 sessions, August 14 sessions.** Two calendar months,
one of them partial.

**Intended deployment instrument: MNQ** (micro NQ), with NQ as the scaled
equivalent. Micro is what a $50,000 prop evaluation can actually size, and every
cost figure below is quoted for it.

## 3.1 The out-of-sample requirement, answered before any performance test

> *"If no credible path exists to at least 150 final out-of-sample trades over
> at least 12 months, state this before performance testing."*

**No such path exists today, and none can be manufactured from stored data.**

* Total NQ data at usable resolution: **46 dates ≈ 2 calendar months.** Not 12.
* The entire fine block is already either examined (36) or sealed (10). There is
  no third pile.
* Replay reach caps historical recovery at three months. Even a complete
  re-recording campaign starting today reaches back only to ~23 June 2026 and
  adds the 16 coarse August–September dates — **62 dates ≈ 3 months.** Still not
  12.
* There is no long NQ one-minute history on disk and no vendor source in this
  project has been shown to supply one.

**The only path to 12 months of final out-of-sample NQ data is to record forward
for 12 months**, ≈252 sessions, reaching September 2027.

The trade-count arithmetic is worse than the calendar arithmetic. Stage 1A
counts *interactions*; a trade survives Stage 1A **and** an absorption condition
**and** a reclaim condition. If those two gates retain even a generous one third
between them, 150 trades needs ~450 qualifying interactions in the
out-of-sample block — and the deployment standard's own minimum of four trades
per month over 12 months is 48, not 150.

**I am stating this now, as instructed, rather than discovering it after Stage
1A passes.** RP-007 can be explored, but it cannot be validated to the declared
standard within any horizon shorter than a year, and the decision to spend a
year of forward recording on it should be taken deliberately and before the work
rather than as a consequence of an encouraging Stage 1A table.

## 3.2 Statistical power — the constraint that shapes Stage 1A

This belongs before the design, because it determines what the design can
legitimately ask.

With 35 discovery sessions and an expected ~6 first interactions per session
(§8), Stage 1A has roughly **210 first interactions in total, ~14 per level
family**. For a difference in reclaim *rates* between a genuine level and its
shifted control, at 80% power and 5% two-sided:

| comparison | n per arm | **minimum detectable difference** |
|---|---|---|
| **pooled across all 15 families** | ~210 | **±13.7 percentage points** |
| **one level family** | ~14 | **±53 percentage points** |

**A 53-point minimum detectable effect is not a test.** Stage 1A as specified
asks for per-family verdicts, both sides separately, across multiple months, and
isolated versus confluence — four splits of a sample that cannot support one.

Two further constraints from the same arithmetic:

* **"present across multiple months"** — discovery is July plus two-thirds of
  August. That is two months, one partial. The condition is satisfiable only in
  the weakest possible sense.
* **"support and resistance both"** halves every cell again.

### Recommendation, and it is a real choice for you

**Run Stage 1A on QQQ one-minute, 2021-01-04 → 2026-08-31, 1,421 sessions, and
use the 35 NQ sessions as an instrument-native consistency check rather than as
the test.** QQQ one-minute is $0.01 resolution — it is not a 5-point recording
and it satisfies your own §3 ruling that one-minute price data is sufficient for
Stage 1A. It gives ~8,500 first interactions instead of ~210, which moves the
per-family minimum detectable effect from 53 points to about 5.

The costs of that choice, stated plainly:

1. **QQQ 2021–2026 is partly spent** — `levels_predictive` consumed it for PDH,
   PDL, VAH, VAL and POC. Those five families would be re-tested on data that
   has already answered a closely related question, and the result cannot be
   presented as untouched.
2. **Three families are not portable**: overnight high, low and midpoint become
   pre-market objects on QQQ.
3. **QQQ is not the deployment instrument.** A level effect that survives on a
   cash ETF still has to survive on a 24-hour futures contract with a different
   participant mix.

The alternative — NQ only — is honest about the instrument and cannot answer the
question. **I recommend QQQ-primary with NQ confirmation, and I am flagging it
rather than deciding it, because it changes what Stage 1A is.**

Everything below is specified so that it runs unchanged on either instrument,
with the two instrument-specific quantities (tick size, zone width) declared for
each.

---

# 4. Exact computation for every proposed level

All fifteen are computed **only from data timestamped before the level's first
interaction**. No level uses same-session data except current-session VWAP,
which is causal at every timestamp by construction.

## 4.1 Session definitions

| window | UTC | New York |
|---|---|---|
| **Regular session (RTH)** | 13:30:00 → 20:00:00 | 09:30 → 16:00 |
| **Overnight session** | 22:00:00 (D−1) → 13:30:00 (D) | 18:00 (D−1) → 09:30 (D) |
| **Initial Balance** | 13:30:00 → 14:30:00 | 09:30 → 10:30 |

The overnight window starts at the **end of the CME maintenance halt**
(21:00–22:00 UTC), which is the true start of the next trading day's auction,
not at midnight. RTH is a half-open interval `[13:30, 20:00)` throughout.

All recorded dates fall in US Eastern Daylight Time. A DST transition changes
the UTC constants and must be handled by a calendar, not by a fixed offset, the
moment the sample extends past 2026-11-01.

On QQQ the RTH window is 09:30–15:59 inclusive of the 15:59 bar; "overnight"
becomes pre-market 04:00–09:29 and is **labelled as such**, never as overnight.

## 4.2 The fifteen levels

| # | level | computation |
|---|---|---|
| 1 | **Prior RTH high** | `max(price)` over the previous full RTH session |
| 2 | **Prior RTH low** | `min(price)` over the previous full RTH session |
| 3 | **Prior RTH close** | last traded price strictly before 20:00:00 UTC on the previous full RTH session |
| 4 | **Prior RTH VWAP** | `Σ(price × volume) / Σ(volume)` over the previous full RTH session, all prints, tape volume |
| 5 | **Prior VAH** | see §4.3 |
| 6 | **Prior VAL** | see §4.3 |
| 7 | **Prior POC** | see §4.3 |
| 8 | **Overnight high** | `max(price)` over 22:00 (D−1) → 13:30 (D) |
| 9 | **Overnight low** | `min(price)` over the same window |
| 10 | **Overnight midpoint** | `(overnight high + overnight low) / 2` |
| 11 | **IB high** | `max(price)` over 13:30 → 14:30 |
| 12 | **IB low** | `min(price)` over 13:30 → 14:30 |
| 13 | **IB midpoint** | `(IB high + IB low) / 2` |
| 14 | **Current-session VWAP** | causal: at time *t*, `Σ(price × volume) / Σ(volume)` over `[13:30, t]` only |
| 15 | **Round prices** | every multiple of **100 NQ points** (see §4.5) |

**"Previous full RTH session"** means the most recent date in the sample that
passes the full-session test. It **skips** early closes and non-sessions rather
than using them, and the skip is recorded per date. When the previous full
session is not in the sample at all — which is true of the first date of any
block — levels 1–7 are undefined and that date contributes no interaction for
those families. It is reported as an exclusion, not silently dropped.

**Levels 1–10 are known before the cash open. Levels 11–13 are known at 14:30
UTC and are not eligible for interaction before that instant. Level 14 updates
continuously.**

## 4.3 Value area methodology

* **Histogram:** prior RTH session only, tape volume summed per traded price on
  the instrument's native grid (0.25 NQ ticks; $0.01 on QQQ).
* **Point of control:** the price with the **highest** total volume. Ties are
  broken by taking the price **closest to the session's volume-weighted mean**;
  if still tied, the **lower** price. The rule is declared here so it cannot be
  chosen later.
* **Value area percentage: 70%**, the standard.
* **Expansion rule:** start at the POC. Repeatedly compare the summed volume of
  the **two** prices above the current region against the **two** below, and
  annex whichever pair is larger; if equal, annex the upper pair. Stop when the
  region holds ≥ 70% of session volume. **VAH** and **VAL** are the region's
  extremes.

This is the conventional two-tick-pair expansion. It is stated in full because
"standard value area" has three common variants that give different boundaries.

**Value area and POC use prior-session data only. Nothing in levels 1–13 reads a
single print from the session being tested.**

## 4.4 Current-session VWAP causality

At every timestamp *t*, VWAP is computed from prints in `[13:30, t]` **strictly
inclusive of t and nothing after**. The interaction test at time *t* compares
price at *t* against VWAP computed at *t*. No session-complete VWAP is ever used
as a level. This is the one level that moves, and it is the one most likely to
produce a geometric identity, because price and its own VWAP are mechanically
close — §7 and §12 exist largely for it.

## 4.5 Round price interval

**100 NQ points**, fixed, declared now, not swept.

Rationale, stated before testing: mean RTH range is **282 points**, so a
100-point grid puts **two to three** round levels inside a typical session — a
comparable density to the other families. A 50-point grid would give five or
six and a 25-point grid eleven, which would dominate the confluence counts by
construction and make every other family look isolated by comparison.

On QQQ the equivalent is **$1.00** (QQQ ≈ $712 against NQ ≈ 29,500; one QQQ
dollar ≈ 41 NQ points, so $1.00 is finer than 100 NQ points — declared as the
natural round number a participant would actually watch rather than as a
conversion).

## 4.6 Contract rolls

Verified absent from the 0.25 block (§1.6). The rule, declared for forward data:
**a session whose prior session is on a different contract contributes no
prior-session level** (families 1–7). Overnight and IB levels are unaffected
because they are computed within one contract. Roll detection is by the measured
test used in §1.6 — a consecutive-print jump exceeding 100 points, which is
above the observed maximum of 65 and far below a roll basis.

## 4.7 Duplicate and overlapping levels

* **Exact duplicates** — two families computing the identical price, e.g.
  overnight high equal to prior RTH high — are collapsed to **one price**
  carrying **both family labels**. They are not counted twice.
* **Overlapping zones** that are not identical form a **confluence cluster**
  (§6) and are counted once as a cluster, with every contributing family named.
* A level whose zone falls **outside the session's traded range** is never
  interacted with and is reported in the denominator of "levels available" but
  never in "interactions".

---

# 5. One fixed zone width

**Zone width = 12 NQ ticks = 3.00 NQ points, applied as level ± 6 ticks
(± 1.50 points).**

Declared now. **One width. No sweep.**

| expression | value |
|---|---|
| NQ ticks (full width) | **12 ticks** |
| NQ points (full width) | **3.00** |
| half-width | ± 6 ticks, ± 1.50 points |
| as a fraction of mean 1-minute ATR | **0.14** |
| as a fraction of median 1-minute ATR | **0.18** |
| QQQ equivalent | **± $0.036**, full width $0.072 |

## 5.1 How the ATR fraction was calibrated, and why not on the discovery block

A 1-minute ATR cannot be measured on the 5.00 recordings — the minimum
resolvable bar range is 5 points, which quantises the statistic beyond use (it
returns a median true range of exactly 10.00, i.e. two rungs). And measuring it
on the discovery block would be calibrating a design constant on the data the
design is about.

Calibrated instead on **QQQ one-minute over the matching calendar window**
(2026-06-18 → 2026-08-20, 44 sessions, 17,114 bars) and converted by price ratio:

| | |
|---|---|
| QQQ mean 1-minute true range | $0.5037 = **7.07 bps** |
| QQQ median 1-minute true range | $0.4100 = **5.76 bps** |
| implied NQ mean 1-minute ATR at 29,500 | **20.9 points** |
| implied NQ median 1-minute ATR | **17.0 points** |
| coarse-block NQ measurement (quantisation-biased, for reference only) | 15.1 mean |

The two independent estimates bracket 15–21 points. **12 ticks is 0.14 of the
mean and 0.18 of the median**, and the stated fraction is a description of the
declared width rather than the way it was chosen.

## 5.2 Why 12 ticks and not something else — three binding constraints

1. **The control shifts force an upper bound.** Your §11 specifies controls at
   ±10 points. A zone half-width of ≥ 5 points would make the ±10 control's zone
   touch the genuine zone, and the control would no longer be an arbitrary
   price. At ±1.5 points there is a **8.5-point gap** between the genuine zone
   and the nearest control zone — 34 ticks of clean separation.
2. **A lower bound from the instrument.** NQ's spread is one tick and a 1-minute
   bar spans 60–80 ticks. A zone of 2–4 ticks would be indistinguishable from
   the spread and from a single print's noise.
3. **An economic bound.** MNQ round-turn cost is ~2.0 points (1 tick spread each
   way plus commission), so a 3× hurdle is **6 points of required rotation**. A
   zone of 3 points is half the minimum rotation that could ever pay — narrow
   enough that "inside the zone" and "rotated away" are distinguishable events.

If Stage 1A is run QQQ-primary, the QQQ width is the price-ratio equivalent
above and is likewise fixed before running.

---

# 6. Confluence definition

A **confluence cluster** is a set of **two or more declared levels whose zones
overlap**, where zones `[a−1.5, a+1.5]` and `[b−1.5, b+1.5]` overlap when
`|a − b| ≤ 3.00 points`.

* Clustering is by **transitive closure**: if A overlaps B and B overlaps C, all
  three are one cluster, even when A and C do not overlap each other.
* A cluster's **reference price** is the **unweighted mean** of its member
  levels. Its zone is that mean ± 1.50 points — the zone does **not** widen with
  membership, because a wider zone would mechanically produce more interactions
  and confound cluster size with interaction frequency.
* Each cluster carries the **list of contributing families**. No family is
  weighted above another, and no subjective weights are assigned anywhere.
* An **isolated level** is a cluster of size one.

Reported as a descriptive split, **never as a filter**:

| bucket | definition |
|---|---|
| isolated | 1 level |
| two-level cluster | exactly 2 |
| three-or-more cluster | ≥ 3 |

**Confluence is a split of the same sample, not a selection applied to it.** The
isolated arm is reported with the same completeness as the cluster arms.

---

# 7. First and repeated interaction definitions

## 7.1 Interaction

An **interaction** occurs at the first timestamp *t* at which the traded price
enters the zone `[L − 1.5, L + 1.5]`, having been **outside** it at the
immediately preceding print.

* **Approach side** is the side price occupied on the last print strictly
  outside the zone before *t*. Approach from **below** makes the level a
  **resistance** test; from **above**, a **support** test. The label comes from
  the approach, not from the family's name — a prior-day high approached from
  above is a support test, and it is counted as one.
* A level is **not eligible** before it exists: IB levels not before 14:30 UTC,
  prior-session levels not before 13:30 UTC on the test date, current VWAP from
  the first print of the session.
* **Stage 1A counts the RTH session only.** The overnight auction is a different
  animal with different participants, it is excluded here, and that exclusion is
  a declared limit rather than a finding.

## 7.2 The four ambiguous cases, resolved in advance

| case | rule |
|---|---|
| **Price opens inside the zone** | **No interaction is recorded on that approach.** There is no approach side, so support and resistance are undefined, and assigning one would be a coin flip that the outcome statistics would then inherit. The level becomes eligible again once price leaves the zone by ≥ one full zone width (3.00 points) and later returns; that return is the **first** interaction. Sessions where this happens are counted and reported. |
| **Price gaps across the zone** | Two consecutive prints straddle the zone without trading inside it. **This is recorded as a `CROSSED` event, not an interaction**, and is reported separately with its own count. It is not evidence for or against the level — the level was never tested. The level is then eligible for a genuine interaction on any subsequent return. |
| **Several levels overlap** | They are **one cluster** (§6) and generate **one** interaction against the cluster's mean price. They never generate one interaction each. |
| **Price touches multiple zones in the same bar** | Interactions are timestamped from the **tape**, not from a bar, so the ordering is the tape's ordering and ties are essentially impossible at 0.25 with microsecond stamps. If two distinct clusters are entered on the **same print**, both are recorded, each against its own cluster, and the pair is flagged. On one-minute QQQ data, where genuine intra-bar ties do occur, the order within the bar is **undefined** and both interactions are recorded and flagged as simultaneous. |

## 7.3 First versus repeated

**At most one counted interaction per cluster until price moves at least one
full zone width (3.00 points) away from the zone boundary and later returns.**

* **First interaction** = the first qualifying interaction with that cluster in
  that RTH session.
* **Repeated interaction** = the second and subsequent qualifying interactions
  with the same cluster in the same session, each numbered (2nd, 3rd, …).
* Interaction counts **reset at each RTH session boundary**. A cluster touched
  yesterday is first-interaction again today — with the caveat that most level
  families are recomputed daily anyway.

Stage 1A's primary sample is **first interactions**. Repeated interactions are
measured with identical definitions and **reported separately**, never pooled,
because repeated testing is expected to weaken a level and pooling would hide
exactly the gradient the family predicts.

---

# 8. Matched control construction

Every genuine interaction generates **five** controls, all following the
identical interaction, reclaim and rotation definitions.

## 8.1 The four shifted controls

`L + 10`, `L − 10`, `L + 20`, `L − 20` points (NQ; price-ratio equivalents on
QQQ). Each is a synthetic level with the same 3.00-point zone, tested for
interaction over the **same session** with the same rules.

**Contamination rule — declared before running:** a shifted price whose zone
overlaps **any** genuine declared level's zone, or any other cluster's zone, is
**excluded from the control arm and labelled**, not treated as arbitrary. Both
counts are reported: how many shifted controls were generated and how many
survived. If a large fraction is excluded — which is likely for the ±10 shifts,
because 15 families across a 282-point range put levels roughly every 19 points
on average — that fraction is itself a reportable finding about how crowded the
level universe is, and it will be reported before any outcome.

This is the point at which the round-price interval matters: a 100-point grid
contributes ~3 levels per session, and a 25-point grid would have made a ±20
shift land on a round number with high probability.

## 8.2 The matched random control

For each genuine interaction, draw a random price from the **same session**,
matched on four axes simultaneously:

| axis | matching rule |
|---|---|
| **interaction time** | within ±30 minutes of the genuine interaction's timestamp |
| **realised volatility** | trailing 30-minute realised volatility at the candidate time within **±10%** of its value at the genuine interaction |
| **distance from the session open** | `|candidate − RTH open|` within **±10%** of `|L − RTH open|` |
| **relative location in the session range so far** | candidate's percentile within `[low, high]` observed up to that instant within **±0.05** of the genuine level's |

The fourth axis is not in your §11 list; it is added because §12 requires
matching on relative location inside the session range, and a control that is
not matched on it cannot support the §12 test. **It is declared here, before
running.** A genuine interaction for which no candidate satisfies all four
constraints is reported as **unmatched** and is excluded from the random-control
comparison only — it remains in every other table.

Controls are drawn **with a fixed seed**, and **200 draws** per genuine
interaction, reported as a distribution with mean, sd, p5 and p95 rather than as
a single draw. The RP-006 halt is the reason this is specified now: a single
random draw is not a control, and a control whose construction makes it
mechanically similar to the true arm is worse than none.

## 8.3 The geometric-identity test (your §12), specified as an analysis, not a caveat

Four mechanical explanations must be excluded **before** any level effect is
interpreted:

1. price already close to the reclaim boundary;
2. the level lying near the middle of the current range;
3. the shifted control lying closer to a session extreme;
4. the target rotation being easier from one starting location.

The test: for every genuine interaction and every control, record
`(relative location in range, distance from price at interaction, time of day,
trailing 30-minute volatility)`. Then compare genuine against control **within
matched strata** of those four, and report the genuine-minus-control difference
**per stratum** as well as pooled.

**If the pooled advantage disappears inside strata, the level is reported as
explained by starting geometry and the family fails**, regardless of the pooled
number. This is written down now so that a pooled positive cannot later be
defended as "directionally right".

---

# 9. Expected interaction frequency

**Design estimates. Not pass conditions. Not measured — no interaction has been
counted.**

Derived from the QQQ touch rates already on record (33–47% per prior-day level
per session) applied to fifteen families, with overlap collapsing:

| quantity | estimate |
|---|---|
| declared levels per session, before collapsing | 15 |
| distinct clusters after overlap collapse | **10–12** |
| clusters inside the session's traded range | **7–9** |
| **first interactions per session** | **5–7** |
| **first interactions per session per family** | **0.35–0.5** |
| repeated interactions per session | 3–6 |
| **first interactions, 35 discovery sessions** | **~210** |
| **first interactions per family, discovery** | **~14** |
| first interactions per month (21 sessions) | **~125 across all families** |

**I have under-estimated frequency before.** RP-003 declared 15–25 signals per
month and realised 44.30 — a 2× miss, caused by fat tails and clustering at the
open. The same failure mode applies here: levels cluster near the open and near
the prior close, so the realised count may be materially higher than this
estimate. It is declared as an estimate, it is not a gate, and it will not be
moved after the count is seen.

**The number that matters is not the total but the per-family total of ~14**,
and §3.2 has already stated what that implies: on 35 NQ sessions Stage 1A can
report per-family counts but cannot test per-family effects.

Against the commercial requirement: ~125 first interactions per month is
comfortably above the four-trades-per-month floor **before** any absorption or
reclaim condition. Whether it survives two further gates is precisely what
Stages 1B and 1C exist to find out, and it is the reason the frequency
requirement belongs at Stage 1A rather than later.

---

# 10. Validation path

| stage | sample | opens only if |
|---|---|---|
| **Stage 1A discovery** | 35 NQ sessions (or 1,421 QQQ sessions with NQ confirmation, if you take the §3.2 recommendation) | approved |
| **Stage 1A internal validation** | **9 sealed dates** — 2026-06-18 → 06-30 + 07-23 | discovery passes all seven §14 conditions |
| **Stage 1B** | surviving families only, on the 46 fine dates | Stage 1A passes on **both** discovery and the sealed block |
| **Stage 1C** | surviving families only | Stage 1B passes |
| **Final out-of-sample** | **forward recording only, ≥12 months** | all three gates pass |

**The sealed block is nine sessions.** It is enough to detect a gross failure
and nowhere near enough to confirm a modest effect: at ~6 first interactions per
session it holds ~54 interactions, about 3–4 per family. It should be understood
as a **falsification check, not a confirmation**, and I would rather say so now
than present nine sessions as validation later.

Immediate, cheap and expiring, recommended independently of everything above:
**re-record 2026-08-21 → 2026-09-11 at 0.25 while replay reach still covers
them.** Sixteen sessions, currently unusable, inside reach today and leaving at
one per day. They are not examined at 0.25 and could serve as a second
validation block rather than as discovery. This is a data action, and I am not
taking it without approval.

---

## Declared before approval

* **No level was computed and no interaction was counted.** Every figure in this
  document is a file property, a declared constant, an arithmetic estimate, or a
  result already on this project's record.
* **Sealed dates were not opened.** 2016–2020 was not opened and remains spent.
* **No data was acquired.**
* **No absorption, delta, volume or footprint threshold is defined anywhere in
  this document**, as instructed. Stage 1B remains unauthorised and unspecified.
* My prior is **against**: five of the fifteen families already returned a null
  on a sample 40× larger, and the NQ block cannot test the other ten
  individually.
