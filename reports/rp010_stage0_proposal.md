# RP-010 Stage 0 — order-flow impact, absorption and exhaustion

**Stage 0 only: data, event construction, thresholds, controls, frequency,
feasibility.** No outcomes, no expectancy, no strategy performance. No entries,
stops or targets are defined. Stage 1 does not run until separately approved.

Prerequisite met: the integrity audit approves the platform, and
`test_platform.py` passes **80 assertions, 0 failures** at `b3a9649`.

The primary object is **signed price progress per unit of aggressive volume**,
not chart location. RP-007 established that named reference levels do not
outperform nearby arbitrary prices, so RP-010 is independent of them by
construction; levels appear only as a diagnostic split in §7.

---

## 1. Data inventory

Resolution **measured from actual prices** by `dataquality.min_increment`, per
date, never inferred from a filename or a header.

| | |
|---|---|
| NQ dates on disk | 64 |
| **at measured 0.25** | **46** |
| **full cash sessions at 0.25** | **44** (2026-06-18 → 2026-08-20, contiguous) |
| at 5.00 — **excluded entirely** | 18 |
| tick size measured on all 44 | **0.25 on 44 of 44** |
| **aggressor labels** | **`B`/`S` on 44 of 44, zero nulls** |
| bid/ask traded volume by price | derivable exactly from price + aggressor + volume |
| cumulative fills (`CUM_`) | present, 47 files |
| BBO | present, 46 files, 0.25 on all |
| depth snapshots (`L2_`) | present, 50 levels/side = 12.25 points |
| MBO | **absent** — `data/mbo/` is empty |
| timestamp resolution | microsecond; monotonic on all 44 |
| median RTH prints/session | **321,470** (min 244,199, max 504,296) |

**Previously examined:** 36 of the 46 fine dates lie inside the roster's
discovery window, and per-script provenance was never pinned, so **all 36 are
treated as examined**.

**Sealed:** June 2026 plus 2026-07-23 — **10 dates, 9 full sessions. Unread.**

**Forward collection:** replay reach is three months. The 16 dates
2026-08-21 → 2026-09-11 are still 5.00 and **have not been delivered** —
`data/tape/` holds 104 files, `data/bbo/` 46, `data/status/` 41, unchanged.
Nothing is claimed for them.

### Selected source file per date

Selection is **resolution first, then row count** — never by extension. The
ledger records `TAPE_NQ_20260820.csv.gz` at true 0.25 and its `_run2` twin at
5.00, so format proves nothing. Full 44-row mapping is in
`reports/rp009_stage1_result.md` §1 and reproduced by
`rp010_stage0_inventory.py`.

---

## 2. Data roles

| role | dates | n | status |
|---|---|---|---|
| **Discovery** | 35 examined full sessions, 2026-07-01 → 2026-08-20 | **35** | examined; discovery only, never validation |
| **Internal falsification** | sealed June 2026 + 2026-07-23, full sessions | **9** | **unread. A falsification check, not confirmation.** |
| **Final out-of-sample** | forward collection under a frozen rule | **0 today** | does not exist |

**Intended deployment instrument: MNQ**, NQ scaled.

### Calendar time to 150 final trades

| | |
|---|---|
| untouched NQ at usable resolution today | **none** |
| forward collection rate | ≈21 sessions/month |
| 12 untouched months | ≈252 sessions |
| at **4 trades/month** (the floor) | 150 trades needs **≈37 months** |
| at **13 trades/month** | 150 trades needs **≈12 months** |

**Stated plainly: 12 months of forward collection reaches 150 trades only if
the frozen rule fires at least ~13 times a month.** §10 shows the raw event
rate is far above that; whether it survives Stage 2's confirmation gates is
exactly what would determine the calendar. Earliest realistic completion is
**late 2027**, and the clock cannot start until a rule is frozen.

---

## 3. Event window — one construction, declared

**30-second NON-OVERLAPPING windows, anchored to the session start, cash
session only, excluding the first and last five minutes.**

`orderflow_core.windows()` **raises `NotImplementedError` on `overlap=True`**.
Rolling windows are deliberately unavailable so that trying both after seeing
results is not possible.

### The overlap quantification the brief asked for, before choosing

| construction | windows/session | windows across 44 sessions | effective independence |
|---|---|---|---|
| **non-overlapping 30 s** | **760** | **33,437** | one window per 30 s of tape |
| rolling 30 s, 1 s step | 22,800 | 1,003,200 | **30× inflation**; adjacent windows share 29/30 of their trades |

A rolling construction would report 30 times the observations for the same
tape, with a 96.7% overlap between neighbours. **Non-overlapping is chosen and
frozen**, and §5's cooldown reduces the count further.

Measured, 09:35–15:55, 44 sessions:

| per 30-second window | median | min | max |
|---|---|---|---|
| windows per session | **760** | 758 | 760 |
| aggressive volume | **353** contracts | 251 | 657 |
| trades | **328** | 236 | 615 |
| zero-volume windows | **0.0%** | 0 | 0 |

---

## 4. Aggression calculation

`orderflow_core.aggression()`, tested against `fixtures.tape_fixture` with
hand-checked answers (buys 8, sells 5, total 13, delta +3, terminal 100.75 with
5 contracts and 3 buys there). A test asserts the aggressor label is
**load-bearing**: flipping `B`↔`S` must negate delta and leave total unchanged.

Per window: aggressive buy volume · aggressive sell volume · **net delta =
buy − sell** · total aggressive volume · **imbalance = |delta| / total** ·
number of trades · number of unique prices · volume at the terminal price ·
buy and sell volume at the terminal price · trades at the terminal price.

Aggressor side comes from the recorder's own field and is **never inferred from
a tick rule**. Zero nulls across 44 sessions.

Measured imbalance: **median 0.106, p90 0.245**. Aggression at 30 seconds is
much more balanced than the folk account assumes — a useful thing to know
before a threshold is set.

---

## 5. Price-progress calculation

`orderflow_core.progress()` and `.impact()`, tested on
`fixtures.absorption_fixture` (200 buys, 10 sells, **1 tick**) and
`fixtures.initiative_fixture` (60 buys, 5 sells, **12 ticks**), with an
assertion that the two are separable by impact by more than 5×.

Per window: signed first-to-last price change · ticks progressed · maximum
progress in the aggression direction · maximum movement against it · **price
progress per 1,000 aggressive contracts** · progress ÷ local ATR · progress ÷
|delta| · progress relative to the 0.25 tick.

**Zero cases, declared:** zero total volume → imbalance **0.0**; zero delta →
`ticks_per_delta` **0.0**; zero progress → impact **0.0**. Never NaN, never a
division by zero. Both are asserted in the test suite.

Measured impact, ticks per 1,000 aggressive contracts:

| | median | p10 | p90 |
|---|---|---|---|
| across 44 sessions | **58.3** | **11.0** | **137.4** |

A 12.5× spread between the tenth and ninetieth percentile. **The variable has
range**, which is the minimum precondition for the hypothesis.

---

## 6. Causal thresholds — three, and no more

All from **trailing completed discovery sessions only**, never from the current
session and never from the forward window.

| threshold | definition | rolling basis |
|---|---|---|
| **aggression** | imbalance ≥ the **90th percentile** of the trailing 10 completed discovery sessions | ~7,600 windows |
| **high impact** | `ticks_per_1k` ≥ the **80th percentile** of the same trailing window, among windows already clearing the aggression threshold | conditional |
| **low impact** | `ticks_per_1k` ≤ the **20th percentile** of the same, same conditioning | conditional |

Three thresholds, one per the brief's maximum. **No grid is swept.**
Percentiles are causal and symmetric: a buy-side and a sell-side window with
mirrored statistics receive the same label, because imbalance uses |delta| and
impact uses |ticks|.

**State A (effective initiative)** = aggression ∧ high impact ∧ progress
aligned with delta. **State B (absorbed)** = aggression ∧ low impact.
**State C (ordinary control)** = neither threshold met.

A window with high imbalance, high impact, but progress **opposed** to delta is
neither A nor B; it is counted and reported separately rather than forced into
a state.

---

## 7. Cooldown and overlap

| rule | value |
|---|---|
| windows overlap | **no** |
| minimum time between events | **5 minutes** |
| consecutive initiative windows | the **first** is the event; the rest are suppressed by the cooldown and counted as `extended` |
| consecutive absorption windows | same |
| **event that changes direction inside the cooldown** | the cooldown is **not** reset; the new-direction window is recorded as `flipped` and **excluded from the primary sample** |
| maximum events per session | **6**, whichever side; beyond that the session is flagged `saturated` and its extra events are excluded |
| independence unit | **the session**, not the window |

Both the event count and the **independent session count** are reported, and
every inference is session-clustered. **Thousands of nearby windows are not
treated as independent observations** — that is the §12 requirement and it is
built into the reporting unit, not applied afterwards.

---

## 8. Controls — declared before any outcome

| # | control | what it isolates |
|---|---|---|
| 1 | same aggression state, **price-progress labels shuffled across events** | whether the impact label is load-bearing |
| 2 | same price progress, **without unusual aggression** | whether progress alone suffices |
| 3 | same \|delta\| at **random times matched on volatility and time of day** | whether the state is a volatility/clock artefact |
| 4 | **high volume with balanced delta** | whether volume alone suffices |
| 5 | **opposite direction** | sign symmetry |
| 6 | events **near vs away from named levels** | **diagnostic only.** Named levels cannot be required for the primary effect |

Every control is unit-tested on synthetic data before use. The suite already
asserts: shuffling changes what it claims to shuffle; **column-permutation
reproduces the treatment exactly (the RP-006 defect, as a failing case)**;
random pairing observes every eligible date; shifted levels that overlap
genuine ones are excluded; opposite-bias returns observations and is the exact
negation; and **a control must not copy the treatment**.

---

## 9. Session-level inference, declared now

Event-level results · session-clustered results · sessions supporting the
effect · **leave-one-session-out** · contribution of the best three sessions ·
results by week · **buy and sell separately, never pooled to conceal a
one-sided result**.

With 35 discovery sessions, a leave-one-out that moves the conclusion means the
conclusion was one session. That is the intended reading.

---

## 10. Expected event frequency

Raw window counts, before thresholds:

| | |
|---|---|
| windows per session | 760 |
| windows, 35 discovery sessions | **26,600** |
| windows, 9 sealed sessions | 6,840 |

Threshold arithmetic. Aggression at p90 keeps ~10% of windows; the impact
condition keeps ~20% of those at each end:

| stage | per session | 35 sessions |
|---|---|---|
| windows | 760 | 26,600 |
| aggression ≥ p90 | ~76 | ~2,660 |
| **A: ∧ high impact** | **~15** | **~530** |
| **B: ∧ low impact** | **~15** | **~530** |
| after the 5-minute cooldown and the 6-per-session cap | **≤6** | **≤210 per state** |

**Design estimate: 4–6 events per state per session, capped at 6.** Roughly
**85–125 events per state per month**, far above the four-trades-a-month floor
even after two Stage 2 confirmation gates.

**I have under-estimated frequency before** — RP-003 declared 15–25/month and
realised 44.30, a 2× miss. This is a design estimate, it is not a pass
condition, and it will not be moved once counted.

---

## 11. Cost and risk feasibility

| | |
|---|---|
| NQ round turn | **2.0 points** = 0.68 bps at 29,460 |
| measured NQ 1-minute ATR (44 sessions) | **21.55 points** |
| **minimum viable container (RP-009)** | **≈1.2 × ATR₁ₘ ≈ 25.9 NQ points**, cost **7.7%** of risk |
| 1.0 × ATR₁ₘ = 21.6 pts | cost **9.3%** — inside the gate on the NQ-measured ATR, **fails at 11.0% on the QQQ-measured unit** |
| 0.5 × ATR₁ₘ, 10 NQ points | **18.6% / 20.0%** — dead |

A container of ~26 NQ points is **~104 ticks**. For a post-event move to cover
3× cost it must travel **≥ 6 NQ points ≈ 24 ticks**.

**The feasibility question Stage 1 must answer, stated now:** the median
30-second window moves ~2 ticks. An event must be followed by a move an order
of magnitude larger than the window that identified it. Measured median impact
is 58 ticks per 1,000 contracts, so a 1,000-contract initiative burst moves
~14 ticks — **below the 24-tick hurdle**. That is not fatal, because the
hypothesis is about what happens *after* the window, but **it is the number the
family most plausibly dies on**, and it is on the record before any outcome.

Time remaining before the close is reported per event; RP-009 established the
closing block cannot supply a 120-minute horizon, and RP-010's horizons top out
at 15 minutes, so truncation should bind only in the final minutes — which the
last-five-minute exclusion already removes.

---

## 12. Stage sequence and what is not defined here

Stage 0 — this document. Stage 1 — descriptive forward behaviour at 30 s,
1, 3, 5, 10, 15 minutes, **with the event window excluded from every forward
outcome**. Stage 2 — authorised only if Stage 1 passes, and limited to **one**
continuation confirmation for initiative and **one** reclaim confirmation for
absorption.

**No entries, stops or targets are defined in this document.**

---

## 13. Declared

The event window is excluded from every forward outcome. Aggressor
classification is validated on synthetic fixtures with known answers before any
discovery outcome is read. Five-point recordings are excluded entirely.
Resolution is measured from prices. Sealed dates remain unread. `on_range` and
`on_disp` are not used. Every time window comes from `sessioncal.py`; no local
offset is computed. `test_platform.py` must pass before each run and its pass
count must appear in the report.

**My prior: against, on §11.** The impact variable has genuine range and the
states are cleanly separable by construction, so I expect Stage 1 to find
*different* forward paths. I doubt the difference will be large enough to clear
a 24-tick hurdle on a 26-point container. Stated now so a statistically
detectable but economically inert result is not read as a pass.

**RP-010 Stage 1 will not run until separately approved.**
