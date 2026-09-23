# RP-012A Stage 0 — intraday relative volume and price-impact persistence

**Stage 0 only: data, contamination, construction, counts, feasibility.** No
forward return has been computed on any block. No entry, stop, target or
strategy is defined. Stage 1 requires separate approval.

| script | what it does | reads an outcome? |
|---|---|---|
| `scripts/orderflow/rp012a_common.py` | the one loader, window builder, feature builder, labeller and cooldown | **no** |
| `scripts/orderflow/rp012a_stage0_inventory.py` | per-instrument data quality, splits, costs — all periods | **no** |
| `scripts/orderflow/rp012a_stage0_counts.py` | event counts — **discovery only** | **no**; asserts no outcome-like column exists |

Platform suite: **PASS 139, FAIL 0.**

---

## 1. Contamination inventory — every instrument, every period

**No ETF one-minute period on disk is untouched.** A search of every script that
loads these files:

| period | QQQ | SPY | IWM | IJH | EFA |
|---|---|---|---|---|---|
| 2016–2020 | **spent as OOS** (`ib_pullback_holdout`) — barred by standing rule | — | — | — | — |
| 2021–2022 | examined: RP-002/003/005/006 + ~30 QQQ-wide scripts with no date filter | examined: RP-003, RP-004, RP-006 + the instrument extensions below | examined | examined | examined: RP-004 |
| 2023 | examined: RP-005 discovery, RP-006B, QQQ-wide scripts | examined: RP-006B factor, instrument extensions | examined: RP-006B | examined: RP-006B | examined |
| 2024–2025 | examined: **RP-005 internal validation**, RP-002 discovery (2024), QQQ-wide scripts | examined: IB 1R (`related_instruments`), ORB-Fib and IB-pullback instrument extensions, all over 2021-01-04 → 2025-12-31 | same | same | same |
| 2026-01 → 08 | **on disk, examined** by QQQ-wide scripts | not on disk | not on disk | not on disk | not on disk |

**No RP-012A outcome has been inspected on any of it**, and no earlier family
tested relative volume as its hypothesis. The only earlier use of a
relative-volume idea is an archived ORB filter (`scripts/archive/backtest_orb_strict.py`:
opening-range-bar volume against its trailing average), which is a single opening
bar, not a 5-minute state, and never became a result. It is declared here as
adjacent, not as contamination of this hypothesis.

Per your instruction, **nothing below is described as pristine final
out-of-sample data**.

---

## 2. Data-quality inventory

Measured by `rp012a_stage0_inventory.py`. Timestamps are naive ET, microsecond
units, first bar 09:30.

### Coverage and half days

| instr | on-disk span | sessions 2021–25 | half days |
|---|---|---|---|
| QQQ | 2021-01-04 → 2026-08-31 | 1,255 (+166 in 2026) | 10 |
| SPY / IWM / IJH / EFA | 2021-01-04 → 2025-12-31 | 1,255 | 10 |

**A platform defect found here.** `sessioncal.early_closes` identified half days
by the time of the last bar. The QQQ and SPY "RTH" files carry after-hours
prints every minute to 15:59 on half days, so it found **zero half days in five
years** — and on illiquid instruments it would have flagged normal days whose
last print came early. Replaced by two measured signals: afternoon bar coverage,
and median afternoon-to-morning minute volume. On all five files it now returns
**the same ten dates**, which are exactly the NYSE half days 2021–2025; half days
score 0.002–0.061, the lowest normal day 0.301. Five new platform tests. Half
days are **excluded from events and from every lookback.** (Ledger §13: RP-008 and
RP-009 contain no half-day handling, so they **may** have read up to 10 of
~1,420 QQQ sessions as full sessions — bounded at 0.7%, not verified, not rerun.)

### Missing bars, staleness, activity

| instr | period | missing % | 0-chg 1m % | flat 1m % | 0-chg 5m % | < 4 bars 5m % | median 1m vol | 0-vol 1m % |
|---|---|---|---|---|---|---|---|---|
| QQQ | discovery | 0.02 | 1.68 | 0.00 | 0.65 | 0.02 | 74,720 | 0.00 |
| QQQ | int. val. | 0.00 | 1.55 | 0.00 | 0.67 | 0.00 | 66,757 | 0.00 |
| SPY | discovery | 0.02 | 1.77 | 0.00 | 0.78 | 0.02 | 109,417 | 0.00 |
| SPY | int. val. | 0.00 | 1.73 | 0.00 | 0.74 | 0.00 | 91,722 | 0.00 |
| IWM | discovery | 0.02 | 3.35 | 0.00 | 1.39 | 0.02 | 37,514 | 0.00 |
| IWM | int. val. | 0.00 | 3.11 | 0.00 | 1.31 | 0.00 | 48,643 | 0.00 |
| IJH | discovery | **3.80** | 2.48 | **8.91** | 1.08 | **2.84** | 6,500 | 0.00 |
| IJH | int. val. | 0.19 | 7.25 | 0.68 | 3.26 | 0.09 | 10,841 | 0.00 |
| EFA | discovery | 0.06 | **13.15** | 0.65 | **5.85** | 0.03 | 25,927 | 0.00 |
| EFA | int. val. | 0.07 | **11.67** | 1.04 | **5.01** | 0.01 | 15,344 | 0.00 |

No NaN volumes on any instrument. IJH's volumes are split-adjusted (×5 before
2024-02-22), so its discovery 6,500 is in post-split shares.

### Split and corporate actions — the IJH five-for-one, resolved

Measured from the session-close series, never remembered:

> **IJH 5-for-1, effective 2024-02-22: 280.84 → 56.99** (ratio 4.928).
> No split on QQQ, SPY, IWM or EFA.

Its effect on relative volume, measured on volume alone:

| | median RV, 20 sessions before | median RV, 20 sessions after | post-split windows with RV ≥ 2 |
|---|---|---|---|
| unadjusted | 0.88 | **2.20** | **54.7%** |
| adjusted | 0.88 | 0.96 | 11.3% |

Unadjusted, the month after the split reads as ~5× normal volume throughout — a
month of spurious "abnormal activity". **Resolved: pre-split prices ÷ 5 and
volumes × 5.** Cost is charged on the price actually traded, not the adjusted
one. Dividends are unadjusted, but a dividend moves only the overnight price and
every RP-012A quantity lies inside one cash session.

### Costs

No ETF quote data exists on disk, so the spread is an **assumption**: one tick
($0.01). Commission $0.0035/share each way. **Round trip $0.017/share**, the
project convention. Optimistic for EFA and post-split IJH, where one cent is a
larger fraction of price and is less often the touch.

| instr | period | traded px | spread bps | comm bps | **RT bps** | ATR₁ₘ bps | **RT / 1.2 ATR₁ₘ** | **3× RT hurdle bps** |
|---|---|---|---|---|---|---|---|---|
| QQQ | discovery | 336.63 | 0.297 | 0.208 | **0.505** | 6.96 | **6.0%** | **1.515** |
| QQQ | int. val. | 495.99 | 0.202 | 0.141 | 0.343 | 5.41 | 5.3% | 1.028 |
| SPY | discovery | 420.28 | 0.238 | 0.167 | **0.404** | 5.06 | **6.7%** | **1.213** |
| SPY | int. val. | 579.30 | 0.173 | 0.121 | 0.293 | 3.89 | 6.3% | 0.880 |
| IWM | discovery | 192.25 | 0.520 | 0.364 | **0.884** | 7.27 | **10.1%** | **2.653** |
| IWM | int. val. | 216.93 | 0.461 | 0.323 | 0.784 | 6.26 | 10.4% | 2.351 |
| IJH | discovery | 257.57 | 0.388 | 0.272 | 0.660 | 4.77 | 11.5% | 1.980 |
| IJH | int. val. | 62.24 | 1.607 | 1.125 | 2.731 | 4.46 | 51.1% | 8.194 |
| EFA | discovery | 72.59 | 1.378 | 0.964 | 2.342 | 3.56 | **54.9%** | 7.026 |
| EFA | int. val. | 81.40 | 1.229 | 0.860 | 2.088 | 2.77 | **62.7%** | 6.265 |

### Instrument suitability — the exclusion rule, declared before measuring

An instrument is excluded from the **primary** screen if, on discovery: **C1**
more than 5% of valid 5-minute windows show zero change; **C2** more than 2% of
5-minute windows have fewer than 4 of 5 bars; **C3** more than 1% of 1-minute
bars carry zero volume. An excluded instrument may serve as the lower-liquidity
control only if it passes C2 and C3.

| instr | C1 zero-change | C2 short windows | C3 zero volume | role |
|---|---|---|---|---|
| **QQQ** | 0.65% ✓ | 0.02% ✓ | 0.00% ✓ | **PRIMARY** |
| **SPY** | 0.78% ✓ | 0.02% ✓ | 0.00% ✓ | **PRIMARY** |
| **IWM** | 1.39% ✓ | 0.02% ✓ | 0.00% ✓ | **PRIMARY** — cost at the 10% gate |
| IJH | 1.08% ✓ | **2.84% ✗** | 0.00% ✓ | **EXCLUDED** — the minute series is too gappy before the split |
| EFA | **5.85% ✗** | 0.03% ✓ | 0.00% ✓ | **LOWER-LIQUIDITY CONTROL ONLY** — stale, and cost is 55% of the container |

**EFA is excluded from the primary screen**, as your brief anticipated, and is
kept as the "same construction on a lower-liquidity instrument" control that
Stage 1 requires. **IJH is excluded entirely.** Its split is resolved regardless.

---

## 3. Exact relative-volume construction

| element | frozen value |
|---|---|
| unit | 5-minute non-overlapping window *k* (§4) |
| window volume | Σ one-minute volume over the window's present bars |
| **bucket** | **the window itself** — bucket width 5 minutes, 75 buckets per session |
| denominator | **median** volume of the **same bucket** over the **prior 20 eligible sessions** |
| minimum history | ≥ 15 valid same-bucket observations, else the window has no RV |
| **RV** | window volume ÷ that median |
| eligible session | full cash session; **half days excluded** from events and from every lookback |
| holidays | absent sessions are simply absent; the lookback counts **sessions**, not calendar days |
| missing bars | a window needs **≥ 4 of its 5** one-minute bars; otherwise it is invalid — never an event, never a control, never in any median |
| splits | measured and adjusted as §2 |
| winsorisation | **none.** The median denominator is robust and every threshold is a percentile, so scale is irrelevant |
| pooling | **never.** Raw volume is never compared across buckets |

---

## 4. Exact event-window construction

| element | frozen value |
|---|---|
| windows | 5-minute, **non-overlapping**, aligned to the open |
| first window | 09:35–09:40 (the first five minutes excluded) |
| last window | 15:45–15:50 (the final ten minutes excluded) |
| windows per session | **75** |
| **displacement** | **ln(C_k / C_{k−1})**, close-to-close; C₋₁ is the close of the 09:34 bar. Causal, and robust to a missing first bar |
| **RD** | \|displacement\| ÷ median \|displacement\| of the **same bucket** over the prior 20 eligible sessions |
| direction | sign of the displacement. **Zero-displacement windows have no direction and are never events** |
| observable at | the close of the window's last bar |
| execution model (Stage 1) | entry at the **open of the next one-minute bar**; exit at the close of the bar at the horizon |
| horizons | **5, 15, 30 minutes** after the window; **primary 15** |
| horizon eligibility | an event is measured at horizon *h* only if the whole horizon ends by 16:00; nothing is truncated |

Bars carry no aggressor label, so direction is **price** direction, not flow
direction. That is a real limitation for state B and is stated rather than worked
around.

---

## 5. State definitions — three, no grid

Thresholds are **percentiles over the prior 20 eligible sessions, computed
separately within each time block** (opening 09:35–10:00, morning 10:00–11:30,
midday 11:30–14:00, closing 14:00–15:50).

| state | definition | reading |
|---|---|---|
| **A** | RV ≥ block p90 **and** RD ≥ block p80 | abnormal volume **with** material displacement — incomplete flow; the hypothesis says it continues |
| **B** | RV ≥ block p90 **and** RD ≤ block p50 | abnormal volume **without** displacement — completed or absorbed flow |
| **C** | block p25 ≤ RV ≤ block p75 | ordinary volume — the control pool, matched in Stage 1 |

Abnormal-volume windows with RD between p50 and p80 belong to **no state** and
are counted, not analysed. RD's thresholds are **unconditional**, not taken
within the abnormal set, so that "the same displacement at ordinary volume" —
the control that decides the family — always exists at the same RD level. That
is also the lesson of RP-010, where the ratio built inside the aggressive set
destroyed the information the scale variables carried.

### Revised before any outcome: thresholds became block-specific

The first construction **pooled** the percentiles across all 75 buckets, arguing
that RV and RD were already bucket-normalised. The counts refuted that.
Normalising by the same-bucket **median** fixes each bucket's level but not its
**spread**: opening volume is high every day, so opening RV varies less, and a
pooled p90 caught only **0.47–0.71×** the average abnormal rate in the opening
block. This is RP-011's pooled-threshold defect one step removed.

| abnormal-volume rate, relative to the instrument's overall rate | opening | morning | midday | closing |
|---|---|---|---|---|
| QQQ, pooled (rejected) | **0.47×** | 0.86× | 1.06× | 1.15× |
| QQQ, block-specific (frozen) | **1.08×** | 0.99× | 1.00× | 0.99× |

Median block-specific thresholds on discovery:

| instr | block | RV p90 | RV p25 | RV p75 | RD p80 | RD p50 |
|---|---|---|---|---|---|---|
| QQQ | opening | 1.551 | 0.801 | 1.247 | 1.969 | 0.992 |
| QQQ | midday | 1.916 | 0.727 | 1.398 | 2.077 | 0.972 |
| SPY | opening | 1.570 | 0.777 | 1.283 | 2.057 | 0.978 |
| SPY | midday | 1.895 | 0.747 | 1.387 | 2.074 | 0.968 |
| IWM | opening | 1.661 | 0.764 | 1.321 | 1.942 | 1.009 |
| IWM | midday | 2.108 | 0.682 | 1.456 | 2.022 | 0.973 |

Full table in `reports/rp012a_stage0_counts.txt`. The opening p90 is ~1.55 and
midday ~1.9: the opening really is less variable, which is exactly why pooling
failed.

---

## 6. Cooldown and overlap rules

| rule | frozen value | why |
|---|---|---|
| cooldown | **15 minutes** after every retained A or B event, **per instrument** | **equal to the primary horizon**, so primary forward paths of successive events on one instrument **never overlap** |
| session cap | **none** | RP-010's cap was a first-come filter. The cooldown is the only thinning, and its effect by block is reported below |
| window overlap | impossible — windows are non-overlapping by construction | |
| cross-instrument | each instrument labelled independently. **38.6%** of primary events share a (date, window) with another instrument (1,125 slots shared by two, 266 by all three) | pooled inference **clusters by date, never by event** |
| A then B | a B event inside another event's cooldown is discarded like any other | the cooldown is state-blind |

Cooldown as a sampling filter, via `dataquality.cap_diagnostics`:

| instr | candidates | retained | discarded | blocks emptied | opening before → after | closing before → after |
|---|---|---|---|---|---|---|
| QQQ | 5,021 | 2,675 | 46.7% | **none** | 343 → 208 | 1,488 → 722 |
| SPY | 5,008 | 2,602 | 48.0% | **none** | 344 → 213 | 1,502 → 728 |
| IWM | 4,675 | 2,619 | 44.0% | **none** | 323 → 213 | 1,391 → 722 |

The cooldown discards roughly half the candidates, **evenly across blocks**
(opening retains 61–66%, closing 48–52%). It clusters rather than biases; no
block is emptied and no block's share moves outside 0.92–1.23× its share of the
session's windows.

---

## 7. Expected event frequency — discovery counts only

Discovery 2021-01-04 → 2023-12-29: 749 full sessions per instrument (4 half days
excluded), 35 warm-up, **714 labelled**. Internal validation was **not counted**.

| instr | A events | B events | events/session | A sessions | B sessions | buy % A | buy % B |
|---|---|---|---|---|---|---|---|
| QQQ | 1,830 | 845 | **3.75** | 491 | 405 | 46.2% | 50.1% |
| SPY | 1,830 | 772 | **3.64** | 494 | 380 | 47.2% | 50.3% |
| IWM | 1,568 | 1,051 | **3.67** | 483 | 448 | 47.4% | 49.7% |
| EFA (control) | 1,430 | 1,293 | 3.81 | 471 | 541 | 48.3% | 49.3% |

By block (QQQ): A 114 / 443 / 775 / 498 and B 94 / 209 / 318 / 224 across
opening / morning / midday / closing. By year (QQQ A): 571 / 693 / 566 across
2021 / 2022 / 2023. Every instrument × state × year cell and every instrument ×
state × block cell is populated.

### Pre-outcome count conditions — all six pass

| # | condition | result |
|---|---|---|
| 1 | A and B each in ≥ 30 independent sessions per primary instrument | **PASS** — minimum 380 |
| 2 | block event share within 0.5–2.0× its share of windows | **PASS** — 0.92–1.23× |
| 3 | every block produces both A and B | **PASS** |
| 4 | buy share within 40–60% in every cell | **PASS** — 46.2–50.3% |
| 5 | abnormal-volume rate per block within 0.5–2.0× | **PASS** — 0.97–1.08× |
| 6 | every discovery year contributes to every cell | **PASS** |

**Condition 2 was revised before any outcome.** As first written — no block
above 40% of events — it was imported from RP-011 without being re-derived.
Midday **is** 30 of the 75 windows, 40.0% of the session, so a flat ceiling would
bind on it under perfectly uniform rates. It now compares each block's event
share with its share of windows, using the 0.5–2.0× band already declared for
condition 5. No new number was chosen. Ledger §14.

### Frequency against the requirement

| | events/session | per month | after one confirmation filter (⅓) | 150 trades in |
|---|---|---|---|---|
| QQQ | 3.75 | 79 | 26 | 5.7 months |
| SPY | 3.64 | 77 | 26 | 5.9 months |
| IWM | 3.67 | 77 | 26 | 5.8 months |
| **NQ proxy — QQQ, state A only** | 2.56 | 54 | **17.9** | **8.4 months** |

**Four trades per month is not in doubt**, and frequency was not manufactured:
the percentiles were declared before counting and not moved. The binding
constraint on any deployment is the **12-month forward-data requirement**, not
the 150-trade count.

---

## 8. Cost and risk feasibility

**Commercial hurdle, frozen now: gross mean forward movement at the primary
15-minute horizon of at least 3 × the instrument's round-trip cost, at that
period's actual traded price.** For NQ: **3 × 2.0 = 6.0 points.**

| instr | discovery RT | **3× hurdle** | 1.2 × ATR₁ₘ container | cost / container | median \|15-min move\| | hurdle / median 15-min move |
|---|---|---|---|---|---|---|
| QQQ | 0.505 bps | **1.515 bps** | 8.35 bps | **6.0%** | 10.35 bps | 14.6% |
| SPY | 0.404 bps | **1.213 bps** | 6.07 bps | **6.7%** | 7.55 bps | 16.1% |
| IWM | 0.884 bps | **2.653 bps** | 8.72 bps | **10.1%** | 11.70 bps | 22.7% |
| NQ (deployment) | 2.0 pts ≈ 0.68 bps | **6.0 pts** | 1.2 × 21.55 = 25.86 pts | **7.7%** | — | — |

**A correction to my own proposal.** It said Proposal A carried "a 10.8% cost
burden and fails the 10% gate at 1 ATR₁ₘ". That figure applied the NQ-derived
cost fraction (0.667 bps) to QQQ against a 1.0 × ATR₁ₘ container. At QQQ's own
measured cost against the 1.2 × ATR₁ₘ container used throughout this project it
is **6.0%**, and on the deployment instrument it is **7.7%**. The cost problem is
smaller than I reported. **IWM is the one instrument at the 10% gate**, and it is
flagged as such.

A Stage 1 pass would require, in addition to the hurdle: both buy and sell
correct, the effect present in each of 2021, 2022 and 2023, no dependence on a
few dates (best-three-date removal and the 40% consistency rule of the
prop-evaluation standard), and relative volume adding information beyond
displacement and volatility. **Statistical strength without economic movement
does not pass.**

### Future Stage 1 controls — designed, not run

| control | construction |
|---|---|
| displacement without abnormal volume | state-C windows with RD ≥ block p80, matched on bucket and RD decile |
| abnormal volume without displacement | state B itself, and abnormal-volume windows at RD p50–p80 |
| matched ordinary windows | state C matched on bucket, trailing realised volatility decile, and RD decile |
| randomised event direction | A and B with the sign drawn at random, 1,000 draws |
| time of day only | the same buckets on randomly drawn sessions |
| absolute rather than relative volume | top decile of **raw** window volume, pooled — the construction this study rejects |
| lower-liquidity instrument | the identical construction on **EFA** |

**The primary state passes only if A beats the displacement-without-volume
control at the same RD.** That is the one comparison that separates "volume adds
information" from "big moves continue".

---

## 9. Discovery and validation path

| role | block | sessions | status | opened when |
|---|---|---|---|---|
| **discovery** | 2021-01-04 → 2023-12-29 | 749 per instrument | examined by other families; no RP-012A outcome | Stage 1, on approval |
| **internal validation** | 2024-01-02 → 2025-12-31 | 502 | examined by other families (RP-005 validation, IB 1R, ORB-Fib, IB pullback); **no RP-012A outcome inspected — preserved** | only if discovery passes every condition; one run |
| **secondary validation** | 2026-01 onward | ~180 to date | **SPY and IWM: not on disk — to be newly acquired, never read.** QQQ 2026-01 → 08 is on disk and examined, and is labelled so | only if internal validation passes |
| **final untouched OOS** | **NQ, forward-recorded after the full freeze** | ≥ 12 months | untouched by construction | §10 |

2016–2020 is not used anywhere. Internal validation's event frequency was **not
even counted**, so nothing about it is known before discovery is judged.

---

## 10. NQ transfer path

**Frozen before any NQ data is acquired, and never re-tuned on NQ:**

| element | frozen value |
|---|---|
| event window | 5-minute non-overlapping, 09:35–15:50 ET, first 5 and last 10 minutes excluded, 75 per session, from `sessioncal` |
| relative-volume method | same-bucket median over the prior 20 eligible sessions, ≥ 15 observations |
| state thresholds | block-specific **p90** RV; **p80 / p50** RD; **p25–p75** ordinary |
| cooldown | 15 minutes per instrument |
| horizons | 5, 15, 30 minutes; primary 15 |
| execution model | next one-minute bar open → bar close at the horizon |
| cost model | **2.0 NQ points round trip**; hurdle **6.0 points** |
| half days | `sessioncal.early_closes`, two-signal |

**What transfers is the rule, not the numbers.** On NQ the percentile *values*
are re-estimated causally from NQ's own trailing 20 sessions — that is the same
rule, not a tuning. The percentile *levels*, windows, cooldown, horizons and cost
model may not change after any NQ outcome is viewed.

**One NQ-specific rule, declared now because it is the futures analogue of the
IJH split: contract rolls.** Volume migrates between contracts over the roll
week, so the front-month series shows a volume discontinuity just as IJH did.
Frozen: the front contract is selected by **prior-session volume**, and the
**five sessions ending on each roll switch** are excluded from events and from
every lookback median.

**Two NQ data sets play two different roles:**

1. **Historical NQ 1-minute, 2021–2026 (to be acquired)** — an **instrument-native
   confirmation** that the frozen rule produces the same event structure, the
   same counts-gate results and cost-adjusted behaviour on the deployment
   instrument. **It is not out-of-sample**: those are the same trading days as
   the ETF blocks, in a different wrapper.
2. **Forward NQ from the freeze date** — the **final untouched OOS**. At the
   17.9 state-A trades/month proxy, 150 trades take ~8.4 months, so the
   **12-month requirement binds**.

---

## Separate items, as instructed

- **Proposal B** (macro calendar) remains pending. A verified release calendar
  may be commissioned independently. No event study runs until release
  timestamps are verified, revisions are distinguished from releases, surprise
  data is available without look-ahead, and ≥ 150 final-validation events exist.
- **Proposal C** (multi-day) remains pending your explicit ruling, and will not
  run until its compatibility with the prop program's overnight-hold
  restrictions and trailing drawdown is established.
- **RP-011** remains frozen and separate. RP-012A touches no NQ tape.
