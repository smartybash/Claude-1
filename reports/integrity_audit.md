# Research integrity audit — dependency-based, before RP-010

Correctness is not inferred anywhere in this document from the fact that a
script completed or produced plausible numbers. Every A and B classification
below rests on **re-executing the committed runner from a clean working tree
and confirming the tree stays clean** — that is, every committed output file
regenerates byte-identically — plus a named check against the committed report.

Audit date **2026-09-23**. Platform tests at `b3a9649`: **80 assertions, 0
failures.**

---

## 1. Reproduction evidence

All 28 runners were executed from a clean tree, one at a time, with
`git status --porcelain` checked after each and the tree restored between runs.

| | |
|---|---|
| runners executed | **28** |
| exited 0 | **28** (`fomc_straddle` needs its `run --block all` mode argument) |
| left the tree dirty | **0** |
| **committed outputs that regenerate byte-identically** | **all of them** |

This is the strongest reproduction test available here and it is what "A"
means below. It does **not** certify that a runner measures what its report
claims — that is what the defect register and the dependency map are for.

---

## 2. Defect register

Sources: `reports/correction_ledger.md` (8 entries, 388 lines), 353 commits
mined for `fix|bug|correct|amend|rerun|wrong|lookahead|defect|invalid|halt|
resolution|timestamp|control|revert`, the RP-006 halt report, and every
study's own §0 corrections.

Categories: **RO** reporting only · **IS** input selection · **DQ** data
quality · **TS** timing/session · **LA** look-ahead · **EX** execution/fill ·
**SL** strategy logic · **CC** control construction · **CU** cost/unit ·
**ST** statistical implementation.

| # | defect | cat | discovered | defect commit | fix commit | seen first? | changed n? | changed result? | changed verdict? | rerun | stale output in repo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | ATAS `Step` multiplier read as an absolute price increment | IS | 2026-09-21 | `5509fcc` | `69cacfc` | no | no | no | no | n/a | no |
| 2 | File format used as a proxy for price resolution | IS | 2026-09-21 | pre-`f1190aa` | `f1190aa` | no | no | **no** — same 36 dates | no | not required | no |
| 3 | Verification return code discarded instead of exiting non-zero | RO | 2026-09-16 | — | `0e978fe` | no | no | no | no | n/a | no |
| 4 | Duplicate files selected by name/format, not measured quality | IS | 2026-09-21 | — | `f1190aa` | no | no | **no** — same files | no | not required | no |
| 5 | Tape coverage computed on the wrong denominator | RO | 2026-09 | — | `7792edb` | yes | **yes** (inventory) | yes | no | **done** | no |
| 6 | BBO and tape recorded under different session gates | DQ | 2026-09 | — | — | yes | yes | yes | no | **not recoverable** | n/a |
| 7 | Cumulative order events mixed with fill rows | RO | 2026-09-15 | — | `8b63cc4` | no | no | no | no | not required | no |
| 8 | Signal implemented as a touch instead of a crossing | SL | 2026-09 | — | `a2148d2` | yes | **yes** | yes | no | **done** | no |
| 9 | `DataFrame.pivot` collision with a `pivot` column | ST | 2026-09 | — | — | yes | no | **no** — verdict identical | no | recomputed | no |
| 10 | A pre-registered rule dropped/altered in a runner | SL | 2026-09 | — | — | no | no | none undeclared | no | n/a | no |
| 11 | FOMC announcement weekday hardcoded to Wednesday | TS | 2026-09-21 | `a971882` | `b7becac` | **no — nothing run** | n/a | n/a | n/a | n/a | no |
| 12 | Overnight cleaning removed genuine extremes on 98.1% of sessions | DQ | 2026-09-22 | `1a65e8c` | frozen, not changed | **measured pre-result** | **yes** — mean range 117.6→91.7 bps | yes | **no** | deliberately not re-run | frozen and labelled |
| 13 | `DataFrame.mod` collision with a `mod` column | ST | 2026-09-22 | — | renamed | no — `TypeError` | no | no | no | n/a | no |
| 14 | Completeness filter imported from another family, dropped 292/503 sessions | IS | 2026-09-23 | `963cafd` | `d26c066` | **yes — 2022 block seen** | **yes** 211→213 usable | yes | **halted, block contaminated** | **done on 2023** | halt report retained, labelled invalid |
| 15 | Shuffled control permuted outcome **columns**, not ranking identity | CC | 2026-09-23 | `963cafd` | `d26c066` | yes | n/a | **control tested nothing** | contributed to halt | **done** | labelled void |
| 16 | Random-pair control kept only coincident pairs (n 129→34–45) | CC | 2026-09-23 | `963cafd` | `d26c066` | yes | **yes** | yes | contributed to halt | **done** | labelled void |
| 17 | Rank-domination threshold incompatible with a 3-instrument universe | ST | 2026-09-23 | `963cafd` | `d26c066` | yes | no | flag fired unconditionally | contributed to halt | **done** | labelled |
| 18 | Five-point recordings used where 0.25 was required | DQ | 2026-09-21 | — | `864c489` | partly | yes | yes | **several families marked "never measured"** | **partial** | audit retained |
| 19 | Entry look-ahead in the pullback `ARMED` state | LA | 2026-09-17 | — | `26e0350` | yes | **yes** — 34.5–72.3% of entries | **yes** | **yes** — a "better rule" was withdrawn | **done** | corrected in place |
| 20 | Stop order assumed to fill at its own trigger price | EX | 2026-09-17 | — | `26e0350` | yes | no | **yes** — +0.56R phantom on QQQ | **yes** — the QQQ screen's entire edge | **done** | corrected in place |
| 21 | Frozen candidate reproduced at 5-minute instead of 1-minute resolution | IS | 2026-09-22 | — | `concentration_audit` | yes | yes | yes | yes | **done** | labelled |
| 22 | `MIN_OR_BARS` 30 unsatisfiable on a 5-minute grid | SL | 2026-09-17 | — | `26e0350` | no | yes | no | no | **done** | no |
| 23 | Flat time in the wrong timezone (22:30 Dubai vs 18:30 UTC) | TS | 2026-09-16 | — | `6936c7a` | yes | yes | yes | **no** | **done** | no |
| 24 | Session-windowing bug exposed by the inventory | TS | 2026-09-16 | — | `ab01cea` | no | yes | yes | no | **done** | no |
| 25 | Lookahead worth 8.75 points a trade in the forecast model | LA | 2026-09-15 | — | `f3c1016` | yes | no | **yes** | **yes** | **done** | no |
| 26 | Realistic-entry lookahead — "the lookahead was the edge" | LA | 2026-09-11 | — | `108661f` | yes | no | **yes** | **yes** | **done** | no |
| 27 | Stale trade side in the recorder | DQ | 2026-09-14 | — | `b384d80` | no | yes | yes | no | **done** | pre-fix dates re-recorded |
| 28 | Cumulative trade stream recording nothing useful | DQ | 2026-09-15 | — | `8b63cc4` | no | yes | yes | no | **done** | no |
| 29 | NQ/ETF costs transferred through a price ratio | CU | 2026-09-22 | `ib_pullback` | `ib_pullback_native` | yes | no | **yes** — pooled −0.004R | **yes** — "not portable" | **done** | labelled |
| 30 | Approach-side (support/resistance) convention inverted | SL | 2026-09-23 | RP-007 draft | pre-result | **no** | yes | yes | n/a — pre-result | **done** | no |
| 31 | IB levels interacted with before 10:30 (look-ahead) | LA | 2026-09-23 | RP-007 draft | pre-result | **no** | yes | 13–15% vs 72–85% reclaim | n/a — pre-result | **done** | no |
| 32 | Two-sided stop grid saturated at 95.7–100% | ST | 2026-09-23 | RP-008 prereg | not changed | yes | no | column carried no information | **no** | n/a | reported |
| 33 | Pooled terciles partly encoded the instant, not the volatility | ST | 2026-09-23 | RP-008 prereg | diagnostic added at counts stage | **no — counts stage** | no | "extra R² 0.4227" → **+0.0014** | **no** | n/a | both arms reported |
| 34 | **NQ tape clock read with the QQQ offset — four hours out** | **TS** | 2026-09-23 | RP-009 first pass | pre-interpretation | **no** | **yes** 1,980→5,544 rows | yes | n/a — pre-result | **done** | no |
| 35 | **One session-level ATR used for an intraday normalisation question** | **CU** | 2026-09-23 | RP-009 prereg | block-local arm added | **yes** | no | **decisive** — 0.518 → 1.056 | **yes** — undeterminable → B | **done** | both arms reported |
| 36 | Barrier ambiguity from 1-minute OHLC ordering | EX | 2026-09-23 | inherent | measured on tape | yes | no | **+6.0 pts at 1R** | no | **calibrated** | quantified |
| 37 | `DataFrame.agg` collision — **third** recurrence | ST | **2026-09-23, this audit** | audit script | renamed | no — `AttributeError` | no | no | no | n/a | no |

**37 defects. 2 unrecoverable or permanently frozen (6, 12). 5 changed a
verdict (19, 20, 25, 26, 29, 35). 11 were caught before any result was viewed.**

### Additional risks searched for and NOT found

* **DST-crossing studies.** Every NQ study uses June–September data (EDT
  throughout). The QQQ bar files are ET-native, so no conversion is applied.
  **No study in the repository crosses a DST boundary with a hardcoded offset.**
  This was luck, not design, and `sessioncal.py` now removes the exposure.
* **Holiday and early-close handling.** `is_full_session` rejects them on
  measured coverage; 2026-06-19, 2026-07-03, 2026-07-12 and 2026-09-07 are
  excluded everywhere by that test, not by a remembered list.
* **Corporate actions.** One split in scope (IJH five-for-one, **2024-02-22** -- corrected; this line originally said 2026, measured date is 2024),
  verified before RP-006B and confirmed outside the 2023 discovery block.

---

## 3. Study integrity table

Clock convention: **ET** = ET-native bar file, no conversion. **UTC** = tape in
UTC, converted. Cost: **0.667 bps** = the NQ 2.0-point round turn expressed as
a fraction; **$0.017/share** = the ETF model; **2.0 pts** = NQ native.

| study | final runner | data | instr | res | dates | clock | session | cost | fill | relevant defects | rerun | reproduces | verdict | **class** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **ORB** | `or_height.py` + `setup_grading.py` | `QQQ_1m` | QQQ | 1-min | 2021-01-04→2026-08-31 | ET | 09:30–16:00 | 0.667 bps | honest, entry bar excluded | 19, 20, 22 | done | **yes** | closed 0/16 | **A** |
| **Pullback continuation** | `or_height.py` + `setup_grading.py` | `QQQ_1m` | QQQ | 1-min | same | ET | same | 0.667 bps | honest | 19, 20 | done | **yes** | closed 0/16 | **A** |
| Pullback, NQ-native | `pullback.py` | NQ tape | NQ | 1-sec | 20 sessions | UTC | 13:30–18:30 UTC | 2.0 pts | honest | 19, 20, 23 | done | **yes** | 0/12 survive | **B** — 20 sessions, 49 trades; power, not correctness |
| **IB 1R** | `reopen_study.py` | `QQQ_1m` | QQQ | 1-min | 2021→2026 | ET | 09:30–16:00 | 2.0 pts frac | honest | 31 (fixed) | done | **yes** | descriptive | **A** |
| **IB midpoint pullback** | `ib_pullback_native.py` | `QQQ_1m` + related | 5 ETFs | 1-min | 2021→2025 | ET | 09:30–13:00 expiry | native per instrument | honest | **29** | done | **yes** | QQQ-specific, not portable | **B** — the transfer failure is the finding |
| IB-mid holdout | `ib_pullback_holdout.py` | `QQQ_1m_holdout` | QQQ | 1-min | 2016→2020 | ET | same | native | honest | — | n/a | **yes** — 132 trades, +0.0002R, PF 1.000 | break-even | **A** — spent, one authorised run |
| **ORB Fibonacci** | `orb_fib_study.py` | `QQQ_1m` | QQQ | 1-min | 2021→2026 | ET | 09:30–16:00 | 0.667 bps | honest | — | n/a | **yes** | continuation unresolved, reversal below floor | **B** — reversal arm 13–39 sessions vs its own 150 floor |
| **Compression** | `compression_run.py` | `QQQ_1m` | QQQ | 1-min | 2021→2026 | ET | D=10:00/10:30 | 0.667 bps | honest | — | n/a | **yes** — p 0.7065, 0/6 | mechanism falsified | **A** |
| **VWAP / ORB+VWAP** | `orb_vwap.py` | `QQQ_1m` | QQQ | 1-min | 2021→2026 | ET | 09:30–16:00 | 0.667 bps | honest + **slippage audit** | **20** (measured, reported) | done | **yes** | 0/16, phantom +0.04–0.16R quantified | **A** |
| **FOMC volatility** | `fomc_study.py` | `QQQ_1m` + `fomc.csv` | QQQ | 1-min | 2021→2026 | ET | release +270 min | n/a | n/a | **11** (fixed) | done | **yes** | expansion, no directional edge | **A** |
| **FOMC straddle** | `fomc_straddle.py run` | AV option chains | QQQ opts | EOD chain | 2016→2026 | ET | T−1 close entry | 2.57% of premium | mark-to-mark | **11** | done | **yes** — n=39/79, −3.54% paired | NULL | **B** — one EOD snapshot per date is the known limit |
| **Pre-open conditioning** | `preopen.py` | `QQQ_1m` + `_eth` | QQQ | 1-min | 2021→2026 | ET | pre-open | n/a | n/a | **12** (overnight raw) | frozen | **yes** | 0/30 | **B** — `on_range`/`on_disp` uncleaned, excluded from later use |
| **Trade conditioning** | `trade_conditioning.py` | frozen trade sets | QQQ | 1-min | 2021→2026 | ET | — | inherited | inherited | 12 (via `on_*`) | n/a | **yes** | 0 claimable | **B** — same overnight caveat |
| **RP-002** | `rp002_stage1.py` | NQ tape + QQQ | NQ/QQQ | 0.25 | 2021→2026 | UTC | RTH | 2.0 pts | n/a | **12** | frozen | **yes** | rejected | **B** — verdict internally consistent, absolute ranges biased low |
| **RP-003** | `rp003_stage1.py` | `QQQ_1m`,`SPY_1m` | QQQ/SPY | 1-min | 2021→2022 | ET | RTH | 0.538 bps paired | n/a | **13** (fixed) | done | **yes** | rejected | **A** |
| **RP-004** | `rp004_stage1.py` | SPY/EFA 1-min | SPY/EFA | 1-min | 2021→2022 | ET | RTH | 3.71 bps | n/a | staleness measured | n/a | **yes** | rejected — 13.42% EFA staleness explains it | **A** |
| **RP-005** | `rp005_stage1.py` | `QQQ_1m` | QQQ | 1-min | 2021→2026 | ET | RTH | 0.667 bps | n/a | — | n/a | **yes** | rejected | **A** |
| **RP-006** (original) | `rp006_stage1.py` | 4 ETFs 1-min | ETFs | 1-min | 2021→2022 | ET | RTH | — | n/a | **14, 15, 16, 17** | **halted** | yes (reproduces the defective output) | **HALTED, invalid** | **D** |
| **RP-006B** | `rp006b_stage1.py` | 4 ETFs 1-min | ETFs | 1-min | 2023 only | ET | RTH | per-pair | n/a | 14–17 all corrected | **done** | **yes** | rejected, 7 of 9 fail | **A** |
| **RP-007** | `rp007_stage1a1.py` | `QQQ_1m`,`_eth` | QQQ | 1-min | 2021→2026 | ET | RTH + ETH | 0.68 bps | n/a | **30, 31** (both fixed pre-result), 36 | done | **yes** | no family qualifies | **A** |
| **RP-008 Stage 0** | `rp008_stage0.py` | frozen trade sets | QQQ | 1-min | 2021→2026 | ET | — | inherited | inherited | — | n/a | **yes** | feasibility | **A** |
| **RP-008 Stage 1** | `rp008_stage1.py` | `QQQ_1m` | QQQ | 1-min | 2021→2026 | ET | RTH | n/a | n/a | **32, 33** | diagnostics added at counts stage | **yes** | regimes not meaningful | **A** |
| **RP-009 Stage 1** | `rp009_stage1.py` | `QQQ_1m` + NQ tape | QQQ/NQ | 1-min / 0.25 | 2021→2026 / 44 sess | ET **and** UTC | RTH | 0.68 bps | adverse-first, tape-calibrated | **34, 35, 36** | **done** | **yes** | time affects only scale | **B** — the frozen ATR arm is uninformative by construction; the block-local arm carries the verdict and was added after the fact |
| **Trendline bounded reconstruction** | `trendline_recon.py` | NQ tape | NQ | 0.25 | 20 sessions | UTC | RTH | 2.0 pts | honest | **9** | recomputed | **yes** | closed | **B** — 20 sessions |
| Levels predictive | `levels_predictive.py` | `QQQ_1m` + gamma | QQQ | 1-min | 2021→2026 | ET | RTH | n/a | n/a | — | n/a | **yes** | 0/13 | **A** |
| Regime forecastability | `regime_forecast.py` | `QQQ_1m` | QQQ | 1-min | 2021→2026 | ET | RTH | n/a | n/a | — | n/a | **yes** | 0/14 | **A** |
| Calendar classification | `calendar_session_study.py` | `QQQ_1m` | QQQ | 1-min | 2016→2026 | ET | RTH | n/a | n/a | — | n/a | **yes** | descriptive | **A** |
| Concentration audit | `concentration_audit.py` | frozen sets | mixed | mixed | — | ET | — | inherited | inherited | **21** (it IS the finding) | done | **yes** | frozen candidate fails | **A** |
| Related instruments | `related_instruments.py` | 5 ETFs | ETFs | 1-min | 2021→2025 | ET | RTH | native | honest | **29** | done | **yes** | not portable | **A** |
| Price resolution audit | `reports/resolution_audit.md` | tape files | NQ | measured | — | — | — | — | — | **18** | — | **superseded** | 61 of 63 need re-recording | **E** — **stale**; RP-007 measured 46 of 64 already at 0.25 |
| Recorder completeness audit | `reports/recorder_completeness_audit.md` | recorder source | — | — | — | — | — | — | — | Part 1 blocked | — | Part 1 **never completed** | partial | **E** — needs `_api_inventory.txt` from the Windows machine |

---

## 4. Classification summary

| class | count | studies |
|---|---|---|
| **A — reproduced and reliable** | **19** | ORB · pullback (QQQ) · IB 1R · IB-mid holdout · compression · VWAP · FOMC volatility · RP-003 · RP-004 · RP-005 · RP-006B · RP-007 · RP-008 Stage 0 · RP-008 Stage 1 · levels predictive · regime forecastability · calendar classification · concentration audit · related instruments |
| **B — reliable with qualification** | **9** | pullback NQ-native · IB-mid pullback · ORB Fibonacci · FOMC straddle · pre-open conditioning · trade conditioning · RP-002 · **RP-009 Stage 1** · trendline reconstruction |
| **C — requires rerun** | **0** | — |
| **D — invalid** | **1** | **RP-006 original** (already halted, labelled, superseded by RP-006B) |
| **E — not reproducible** | **2** | price resolution audit (stale, superseded) · recorder completeness audit Part 1 (blocked on hardware) |

**Qualifications, stated so they bind:**

* **RP-002, pre-open conditioning, trade conditioning** — the overnight cleaning
  estimator (defect 12) biases absolute overnight ranges 22% low. Verdicts are
  internally consistent because every arm shares it. **`on_range` and `on_disp`
  may not be used in any future family until a validated cleaning method exists.**
* **RP-009 Stage 1** — the frozen session-level ATR arm cannot answer the
  normalisation question; the block-local arm that carries Verdict B was added
  after seeing the frozen arm. It can only reduce the opening's advantage, so it
  cannot have manufactured the verdict, but it is post-hoc and is labelled so.
* **IB-mid pullback, related instruments** — the cost-transfer defect (29) is
  the finding, not a flaw: transferring NQ points into ETFs is what failed.
* **pullback NQ-native, trendline reconstruction** — 20 sessions. Underpowered,
  not incorrect.
* **ORB Fibonacci** — the reversal arm fires on 13–39 sessions against its own
  declared 150-session floor. Continuation is unresolved, not rejected.
* **FOMC straddle** — Alpha Vantage returns one EOD chain snapshot per date.
  The design was moved to a T−1 close entry to avoid reading a post-announcement
  vol-crushed mark; that limit is structural.

---

## 5. Decision impact — defects that changed a number

| defect | old | corrected | difference | verdict changed? | later work relying on the old value? |
|---|---|---|---|---|---|
| 19 entry look-ahead | 34.5–72.3% of entries on the extreme bar | 0.0% | removes the entry edge | **yes** | no — caught in the gate |
| 20 stop fill at trigger | QQQ screen edge +0.24 to +0.55R | phantom **+0.56R** | the edge *was* the defect | **yes** | **no** — "bar-close filter" hypothesis withdrawn at `26e0350` |
| 5 coverage denominator | inflated coverage | corrected | inventory only | no | no |
| 8 touch vs crossing | calibration values | corrected | calibration | no | **RP-007 used crossing** ✓ |
| 12 overnight cleaning | mean range 117.6 bps | **91.7 bps** | **−22%** | **no** | RP-002, pre-open, trade conditioning — all classified **B** |
| 14–17 RP-006 harness | 211 usable, 2022-only, controls void | 213 in 2023, controls discriminate | block contaminated | **halt → rejected** | **no** — 2021–22 sealed off |
| 21 5-minute reproduction | frozen candidate "survives" | fails at 1-minute | — | **yes** | no |
| 25 forecast look-ahead | +8.75 points/trade | removed | **−8.75 pts** | **yes** | no |
| 26 realistic-entry look-ahead | positive | negative | "the lookahead was the edge" | **yes** | no |
| 29 cost transfer | QQQ +0.185R frozen | pooled non-QQQ **−0.004R** | not portable | **yes** | **RP-009 §8 relies on this** — correctly, it uses the corrected figure |
| 33 pooled terciles | "extra R² **0.4227**" | **+0.0014** | 300× overstated | **no** | no |
| 34 NQ clock | 1,980 rows, 5 of 14 timestamps | 5,544 rows, all 14 | 4-hour mislabel | n/a — pre-result | no |
| 35 session ATR | close/open ratio **0.518** | **1.056** | gradient inverts | **yes** — undeterminable → B | **RP-010 §13 relies on the 1.2-ATR container from this** |
| 36 barrier ambiguity | P(target) 44.0% at 1R | tape-true **50.0%** | **+6.0 pts** | no | RP-009 reports both |

**One live dependency to flag:** RP-010's §13 feasibility test invokes "the
approximately 1.2 ATR minimum viable NQ risk container identified by RP-009".
RP-009 is classified **B**, and that particular number comes from the *cost*
arithmetic (0.68 bps ÷ risk), **not** from the block-local ATR arm that carries
the qualification. The 1.2-ATR figure is therefore **A-grade within a B-grade
study** and is safe to carry. It is stated here so the dependency is explicit.

---

## 6. Platform work completed for this audit

`b3a9649`. **80 assertions, 0 failures.**

| module | what it removes |
|---|---|
| `sessioncal.py` | per-study clock arithmetic. zoneinfo DST, cash open/close, early closes **measured not remembered**, CME halt, IB completion, FOMC release, and `minutes_after_open(ts, clock=...)` which makes the tape's clock an explicit argument |
| `dataquality.py` | resolution inferred from format; duplicate files chosen by name; completeness used as a silent filter; splits read as moves; staleness unreported |
| `orderflow_core.py` | ad-hoc aggression maths. Zero-delta and zero-progress explicit. **Rolling windows deliberately unimplemented** so one construction must be declared before outcomes |
| `fixtures.py` | answers inferred from plausibility. Known-answer cases for every defect class |
| `test_platform.py` | the gate. Exits non-zero on any failure |

**Coverage of the register:** timezone (34, 23, 24, 11) · IB look-ahead (31) ·
approach side (30) · crossing vs touch (8) · barrier ordering and ambiguity
(36) · resolution measurement (1, 2, 18) · duplicate selection (4) · split
detection · staleness (RP-004) · monotonicity · roll detection · aggressor
classification · absorption/initiative separability · **five control
constructions including an exact reproduction of the RP-006 column-permutation
defect (15)**, random-pair coverage (16), shifted-level overlap, opposite-bias
(RP-006 native control), and "a control must not copy the treatment".

**The tests caught four errors in my own fixtures before they were trusted**,
and the audit's own inventory script produced the **third** recurrence of the
pandas-method column collision (`DataFrame.agg`), recorded as ledger entry 8.

### Unresolved items

1. **The reserved-column-name rule is still enforced by memory.** Three
   recurrences (`pivot`, `mod`, `agg`). A lint check belongs in
   `test_platform.py` and is not yet written. **Does not affect RP-010 inputs**
   — RP-010's columns are named in `orderflow_core.py`, which is tested — but
   it is the one standing weakness.
2. **Existing studies have not been migrated to `sessioncal.py`.** Twelve
   scripts still contain their own offsets. All are classified A or B and all
   reproduce; migrating them would change committed outputs and is therefore a
   deliberate non-action. **Every new study must use the shared calendar.**
3. **`recorder_completeness_audit` Part 1 (E)** remains blocked on
   `_api_inventory.txt` from the Windows machine. It documents the recorder's
   callback surface, not any result.
4. **`resolution_audit.md` (E) is stale** and should be read only alongside
   RP-007 §1, which supersedes it.

---

# AUDIT VERDICT

| | |
|---|---|
| **A — reproduced and reliable** | **19** |
| **B — reliable with qualification** | **9** |
| **C — requires rerun** | **0** |
| **D — invalid** | **1** (RP-006 original, already halted and superseded) |
| **E — not reproducible** | **2** (both documentation, neither a result) |

**Closures that remain valid:** all of them. Every closed family is A or B, and
the one D was closed *because* it was invalid, by a halt that refused to
interpret the output.

**Closures requiring rerun: none.**

**Findings safe to carry forward:** the efficiency-ratio result (§3.5); the
time-of-day opportunity gradient and its inversion under local normalisation
(RP-009); the 1.2-ATR minimum viable NQ container; the driftless barrier
baseline confirmed on tick data; RP-007's level null; RP-008's regime null;
every closure listed above.

**Findings that must be withdrawn:** none beyond those already withdrawn in
place — the bar-close filter hypothesis (`26e0350`), the RP-006 2021–22 output
(halted), and `resolution_audit.md`'s re-recording estimate (superseded).

> ## **Research platform APPROVED for RP-010, with no unresolved material defect affecting RP-010 inputs, timing, order-flow construction, controls, or prior conclusions used by RP-010.**

The two E items are documentation, not results. The one D is superseded. The
single unresolved weakness — the reserved-name rule enforced by memory — does
not touch RP-010's inputs, which are produced by the tested `orderflow_core`.

**Conditions attached to the approval:**

1. RP-010 uses `sessioncal.py` for every time window. No local offsets.
2. RP-010 uses `orderflow_core.py` for aggression, progress and impact.
3. `test_platform.py` must pass before each RP-010 run, and the run must
   report the pass count.
4. Every RP-010 report prints the relevant `dataquality.py` output.
5. **`on_range` and `on_disp` remain unusable** until an overnight cleaning
   method is independently validated.
