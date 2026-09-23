# RP-009 Stage 1 — time-of-day opportunity and risk design

Pre-registered at `04d8d4b`. **Barrier geometry only.** No strategy P&L,
expectancy, profit factor, win rate, drawdown, allocator, entry pattern,
directional rule or prop-evaluation simulation. No strategy module is imported
by the map; the one strategy table is architecture only.

* **QQQ provides the primary long-sample evidence.**
* **NQ provides exploratory instrument-native confirmation only.**
* **44 NQ sessions cannot support a standalone commercial verdict.**
* **QQQ results cannot validate an MNQ strategy.**

---

## 0. A defect in my own frozen definition, found before reading the NQ arm and before interpreting section 3

Two corrections, both mine, both recorded because the second changes what the
study can conclude.

**0a. The NQ clock was four hours out.** The recorder writes the ATAS platform
clock, which is UTC; the cash open is 13:30 UTC, not 09:30. The first NQ pass
computed minutes-after-open as `(h×60+m) − 570` instead of `− 810`, so every NQ
timestamp was labelled four hours late and only five of fourteen matched
anything. Caught in the block counts (only "midday" and "close" appeared),
fixed, re-run. The NQ arm below is the corrected one — 5,544 excursion rows
against 1,980 before.

**0b. The frozen ATR unit cannot answer the question it was frozen for.**
ATR₁ₘ as pre-registered is the **prior session's mean 1-minute true range — one
number per session**. Dividing all fourteen timestamps by the same constant
cannot flatten an intraday gradient; it rescales every timestamp identically.
The frozen unit is therefore **mathematically incapable** of answering §12's
first question, *"does ATR normalisation remove the opening's advantage?"*

That is a logical fact about the definition, not something the data revealed,
and I should have seen it when I froze it. §3 below reports the frozen arm as
specified **and** adds a **block-local ATR** arm — the prior session's ATR
measured over the same clock block, causal, the construction RP-008 already
used. It is a diagnostic added after the fact, and it can only **reduce** the
opening's apparent advantage, never inflate it, because the open is the block
with the largest local ATR. It changes the verdict from *undeterminable* to
**B**.

---

## 1. Data and sample counts

| | |
|---|---|
| QQQ calendar sessions | 1,421 |
| excluded: fewer than 300 bars / no prior session | 1 / 1 |
| **QQQ sessions used** | **1,419** |
| observations | 14 timestamps × 1,419 = **19,866** |
| QQQ excursion rows / barrier rows | 178,749 / **714,996** |
| **NQ full 0.25 sessions** | **44** (2026-06-18 → 2026-08-20) |
| NQ excursion / barrier / tick-calibration rows | 5,544 / 22,176 / **22,176** |

**Horizon availability — horizons past the cash close are marked unavailable,
never substituted with a shorter window:**

| timestamp | available min | h15 | h30 | h60 | h120 | to close |
|---|---|---|---|---|---|---|
| 09:30 | 389 | 1418 | 1418 | 1418 | 1418 | 1418 |
| 13:30 | 149 | 1419 | 1419 | 1419 | **1418** | 1419 |
| **14:00** | 119 | 1418 | 1418 | 1418 | **0** | 1418 |
| **14:30** | 89 | 1419 | 1419 | 1418 | **0** | 1419 |
| **15:00** | 59 | 1418 | 1418 | **0** | **0** | 1418 |
| **15:30** | 29 | 1419 | **0** | **0** | **0** | 1419 |

The closing block loses the 120-minute horizon entirely and loses the
60-minute horizon at half its timestamps. **That is a structural fact about the
block, not a measurement failure**, and it is one of the two things that decide
Verdict C.

---

## 2. Absolute excursion gradient — bps, medians [p25, p75]

**60-minute horizon:**

| timestamp | n | MFE med | [p25 | p75] | MAE med | range |
|---|---|---|---|---|---|---|
| **09:30** | 1418 | **33.44** | 15.10 | 59.92 | 35.56 | 80.30 |
| 09:45 | 1418 | 29.21 | 13.75 | 53.33 | 31.02 | 71.59 |
| 10:00 | 1418 | 27.68 | 13.33 | 49.55 | 28.25 | 64.59 |
| 10:30 | 1419 | 22.56 | 10.60 | 40.48 | 23.50 | 54.95 |
| 11:30 | 1419 | 18.40 | — | — | 18.42 | 44.48 |
| 13:30 | 1419 | 15.46 | — | — | 17.62 | 39.22 |
| **14:30** | 1418 | **15.40** | — | — | 15.51 | 38.01 |

**Block summary, 60-minute horizon:**

| block | n | MFE bps | MAE bps | **ratio vs open** |
|---|---|---|---|---|
| open | 2,836 | **31.44** | 33.15 | **1.000** |
| morning | 4,256 | 23.61 | 23.71 | 0.751 |
| midday | 7,095 | 16.99 | 17.45 | 0.540 |
| close | 2,836 | 15.52 | 15.73 | **0.494** |

**The open offers almost exactly twice the absolute excursion of the close.**
Long MFE equals short MAE to machine precision (appendix), so this is one
symmetric distribution seen twice, not a directional statement.

---

## 3. ATR-normalised excursion gradient

**Frozen arm — session-level ATR₁ₘ (median 6.19 bps, constant within a day):**

| block | MFE ATR | MAE ATR | ratio vs open |
|---|---|---|---|
| open | 4.974 | 5.170 | 1.000 |
| morning | 3.804 | 3.752 | 0.765 |
| midday | 2.738 | 2.713 | 0.550 |
| close | 2.577 | 2.506 | **0.518** |

The ratio is 0.518 against the bps ratio of 0.494 — **essentially unchanged**,
because the divisor is the same number at every timestamp. This arm is reported
as specified and carries no information about normalisation, for the reason in
§0b.

**Block-local ATR arm — the prior session's ATR over the same clock block:**

| block | n | local ATR (bps) | MFE / local ATR | MAE / local ATR | **ratio vs open** |
|---|---|---|---|---|---|
| open | 2,836 | **10.510** | 2.901 | 3.064 | **1.000** |
| morning | 4,256 | 7.676 | 3.112 | 3.122 | **1.073** |
| midday | 7,095 | 5.108 | **3.321** | 3.346 | **1.145** |
| close | 2,836 | 5.180 | 3.063 | 2.988 | **1.056** |

**The gradient does not merely flatten — it inverts slightly.** Measured against
the volatility unit of its own time of day, the open offers the *least*
excursion per unit of risk (2.901) and midday the most (3.321), a spread of
14.5%. The open's two-to-one advantage in basis points is **entirely a scale
effect**: the open is twice as volatile and therefore requires twice the stop.

This is the same result RP-008 reached from the other direction — *the day gets
quieter, not straighter* — and it is the core finding of RP-009.

---

## 4. Barrier geometry

Driftless baseline **P(+MR before −1R) = 1/(1+M)**: 50.0% at 1R, 40.0% at 1.5R,
33.3% at 2R. **Matching or beating the baseline is not evidence of directional
edge. It is geometry, and a directional entry rule would still be required.**

**Excluding ambiguous bars**, in every block and every container:

| target | baseline | open | morning | midday | close |
|---|---|---|---|---|---|
| 1.0R | 50.0% | **50.0** | **50.0** | **50.0** | **50.0** |
| 1.5R | 40.0% | 39.7–40.9 | 39.8–40.9 | 39.7–40.9 | 39.0–41.2 |
| 2.0R | 33.3% | 33.2–34.7 | 33.1–34.4 | 33.0–34.5 | 31.4–34.6 |

**The market is a driftless barrier process at this resolution, in every block,
at every container size, to within a point.** Nothing in the clock changes it.

Including ambiguous bars the figures fall — 33.4% at 1R for the 10-point
container at the open — but that is the adverse-first convention, not the
market. §7 measures exactly what that convention costs.

**Median resolution time (minutes):**

| block | 1.0ATR 1R | 1.5ATR 1.5R | 30NQpt 2R |
|---|---|---|---|
| open | 1 | 2 | 3 |
| morning | 2 | 4 | 6 |
| midday | 3 | 9 | 12 |
| close | 3 | 10 | 12 |

Resolution is fast everywhere — a container of one to one-and-a-half ATR
resolves in single-digit minutes. The mapped containers are small relative to
the excursion budget at every hour.

---

## 5. Cost viability — NQ cost 0.68 bps, 2.0 NQ points

| container | risk (bps) | **cost / risk** | | cost / median 60-min MFE by block |
|---|---|---|---|---|
| 10 NQ points | 3.39 | **20.0%** | **FAIL** | open 2.2% · morning 2.9% · midday 4.0% · close 4.4% |
| 0.5 × ATR₁ₘ | 3.10 | **21.9%** | **FAIL** | " |
| 20 NQ points | 6.79 | **10.0%** | at the limit | " |
| 1.0 × ATR₁ₘ | 6.19 | **11.0%** | **marginal FAIL** | " |
| 30 NQ points | 10.18 | 6.7% | pass | " |
| 1.5 × ATR₁ₘ | 9.29 | 7.3% | pass | " |

The pre-declared arithmetic holds, with one correction: **1.0 × ATR₁ₘ measures
6.19 bps, not the 7.32 bps the proposal estimated from the 44-session NQ ATR**,
so it costs **11.0% of risk and fails the 10% gate**, where the proposal had it
passing narrowly at 9.3%. The estimate came from NQ's ATR; the realised figure
is QQQ's, and the two differ by 15%. **On the QQQ-measured unit the smallest
container that clears the gate is about 1.2 ATR₁ₘ.**

Cost as a share of *available movement* rises through the day — 2.2% of the
open's median 60-minute MFE, 4.4% of the close's — but at no hour is it the
binding constraint. **Cost binds on the container, not on the clock.**

Minimum gross edge to recover a round turn is **0.68 bps everywhere by
construction**; what changes is the fraction of the excursion budget it eats.

---

## 6. Holding-time truncation

% unresolved at the cash close:

| block | 1.0ATR 1R | 1.0ATR 2R | 1.5ATR 1.5R | **1.5ATR 2R** | **30NQpt 2R** |
|---|---|---|---|---|---|
| open | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| morning | 0.0 | 0.0 | 0.0 | 0.0 | 0.1 |
| midday | 0.0 | 0.1 | 0.2 | 0.4 | 1.3 |
| **close** | 0.3 | 1.1 | 3.1 | **5.8** | **10.2** |

**Truncation is real, confined to the closing block, and modest** — the worst
mapped cell is a 30-point container at a 2R target, unresolved on 10.2% of
paths. At one ATR it is 1.1%.

The larger truncation fact is in §1: **the closing block cannot offer a
120-minute horizon at all, and cannot offer 60 minutes after 14:30.** An
architecture needing two hours of runway does not exist after 14:00, regardless
of what the excursion distribution says.

---

## 7. Tick-order calibration — 44 NQ sessions, exploratory

The same dates resolved two ways: true tick order from the tape, and the
one-minute adverse-first convention.

| target | n | bar P(target) | **tick P(target)** | difference | ambiguous % | disagree % |
|---|---|---|---|---|---|---|
| 1.0R | 2,640 | 44.0 | **50.0** | **+6.0** | 12.0 | 6.0 |
| 1.5R | 2,640 | 37.4 | **40.2** | +2.8 | 7.7 | 2.8 |
| 2.0R | 2,640 | 31.7 | **32.8** | +1.1 | 4.9 | 1.1 |

**Tick-resolved probabilities are 50.0 / 40.2 / 32.8 against geometric
baselines of 50.0 / 40.0 / 33.3.** The tape independently confirms the driftless
result on a different instrument.

**On the 652 ambiguous bars — where the convention actually binds — it calls
100% adverse and the tape says 40.2% were in fact the target.** The convention
is conservative by roughly the amount the baseline predicts, which is the
reassuring answer: it is not introducing a bias of its own, it is applying the
geometric split pessimistically.

**Consequence for reading §4:** the adverse-first columns understate P(target)
by about 6.0 points at 1R with a small container, 1.1 points at 2R. The
"excluding ambiguous" columns are the better estimate and they sit on the
baseline. No cell is labelled unresolved, because the ambiguity moves the
figures toward the baseline rather than across a decision boundary.

These 44 sessions do **not** overturn the QQQ map. They calibrate the
convention, and they agree with it.

**NQ native excursion, 60-minute horizon, exploratory:**

| block | n | MFE (NQ pts) | MAE (NQ pts) |
|---|---|---|---|
| open | 88 | **92.7** | **130.4** |
| morning | 132 | 68.3 | 106.6 |
| midday | 220 | 45.5 | 51.1 |
| close | 88 | 32.4 | 47.2 |

Same shape as QQQ — monotone, roughly halving — but steeper: open-to-close
ratio **0.349** against QQQ's 0.494.

**Two cautions on this table, both about 44 sessions.** The steeper ratio is
within the year-to-year range QQQ itself shows (0.33 in 2026, and these dates
are 2026). And **MAE exceeds MFE at every block** — 130.4 against 92.7 at the
open — which is a directional skew in a two-month sample, not a property of the
market. QQQ's 1,419-session equivalent is symmetric to within 1.7 bps (appendix).
**Not a finding. Not promoted.**

---

## 8. Strategy compatibility — architecture only, no P&L

Median risk converted to ATR₁ₘ and to NQ points at the measured 29,460; cost
gate at the NQ round turn. Attainability comes from the **opportunity map's own
excursion distribution at each strategy's median entry timestamp** — no trade
outcome is read.

| strategy | window | med entry | **risk (ATR)** | **risk (NQ pts)** | cost/risk | target | need (ATR) | **% reach target** | % reach stop | **% neither** | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ORB OR15 R3 | 09:45+ | 10:00 | 1.70 | 31 | 6.4% | 3R | 5.11 | 68.8 | 87.4 | 0.1 | **compatible** |
| ORB OR15 R4 | 09:45+ | 10:00 | 1.68 | 31 | 6.5% | 4R | 6.72 | 58.8 | 87.6 | 0.4 | **compatible** |
| ORB OR30 R3 | 10:00+ | 10:00 | 1.46 | 27 | 7.4% | 3R | 4.38 | 72.3 | 89.1 | 0.0 | **compatible** |
| ORB OR30 R4 | 10:00+ | 10:00 | 1.45 | 27 | 7.5% | 4R | 5.79 | 65.3 | 89.1 | 0.1 | **compatible** |
| pullback OR15 R3 | 09:45+ | 10:30 | 1.74 | 32 | 6.2% | 3R | 5.23 | 62.3 | 85.9 | 0.1 | **compatible** |
| pullback OR30 R3 | 10:00+ | 11:00 | 1.52 | 30 | 6.7% | 3R | 4.57 | 66.5 | 85.7 | 0.4 | **compatible** |
| IB-mid pullback R2 | 10:30–13:00 | 11:00 | 2.65 | 52 | 3.8% | 1.5R | 3.98 | 71.0 | 76.5 | 0.5 | **compatible** |
| ORB-Fib cont ORB15 | 09:45+ | 10:00 | 5.55 | **99** | 2.0% | 1R | 5.55 | 66.8 | 63.5 | 1.8 | **marginal** |
| ORB-Fib cont ORB30 | 10:00+ | 10:30 | 6.07 | **102** | 2.0% | 1R | 6.07 | 57.7 | 56.2 | 5.4 | **marginal** |
| **IB 1R single** | 10:30+ | 10:30 | **13.45** | **259** | 0.8% | 1R | 13.45 | **21.4** | 27.7 | **52.2** | **structurally incompatible** |
| **IB 1R re-entry** | 10:30+ | 10:30 | **13.29** | **256** | 0.8% | 1R | 13.29 | **22.0** | 28.1 | **51.3** | **structurally incompatible** |
| **Compression D=10:00** | 10:01 only | 10:00 | **49.04** | **848** | 0.2% | none | — | — | **1.1** | — | **structurally incompatible** |
| **Compression D=10:30** | 10:31 only | 10:30 | **48.22** | **880** | 0.2% | none | — | — | **0.7** | — | **structurally incompatible** |

**The library splits on container size, not on time of day.** Every strategy
sits in the 09:45–11:00 window, so the clock cannot separate them — which is
what RP-008 Stage 0 found, restated in architectural terms.

**IB 1R** needs a 13.4-ATR favourable move against a median 7.2-ATR
excursion-to-close from its own entry timestamp. **Half its setups reach neither
barrier before the cash close.** Its nominal risk is ~258 NQ points ≈ $516 per
MNQ contract, which on a $50,000 evaluation is a single micro per trade.

**Compression** carries a 48-ATR nominal stop that is reached on **0.7–1.1%** of
paths. It is not a stop-based architecture at all — it is a hold-to-close delta
position with a notional stop that never engages, at ~850 NQ points ≈ $1,700 per
MNQ contract. It cannot be sized in a $50,000 evaluation.

**No expectancy, profit factor or trade outcome appears in this table**, and
none was computed to build it.

---

## 9. Yearly stability

Median MFE, 60-minute horizon:

| block | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | |
|---|---|---|---|---|---|---|---|
| open | 28.21 | 49.36 | 32.79 | 23.89 | 28.08 | 34.04 | bps |
| | 5.150 | 4.793 | 5.174 | 4.567 | 4.845 | 5.314 | ATR |
| close | 13.56 | 30.63 | 18.19 | 13.45 | 13.66 | 11.28 | bps |
| | 2.819 | 2.923 | 2.870 | 2.596 | 2.362 | 1.800 | ATR |

**Close-to-open ratio by year:** bps 0.481 / 0.621 / 0.555 / 0.563 / 0.487 /
0.331; ATR 0.547 / 0.610 / 0.555 / 0.568 / 0.488 / 0.339.

**The gradient is present in all six years and is stable at roughly 0.5**,
loosening to 0.62 in 2022 and tightening to 0.33 in 2026. The session-level ATR
row tracks the bps row almost exactly, which is §0b's point seen year by year.

---

## 10. Desk interpretation — the seven questions, answered directly

**1. Is the opening genuinely capable of supporting wider targets, or does ATR
normalisation remove the advantage?** *Normalisation removes it entirely.* The
open offers 2.0× the absolute excursion and requires 2.0× the stop; measured
against its own local volatility it offers **less** excursion per unit of risk
than midday (2.901 vs 3.321). Wider targets at the open are wider in points, not
in R.

**2. Does midday support smaller absolute targets but similar ATR multiples?**
*Yes, and slightly better ATR multiples.* Midday absolute excursion is 54% of
the open's; in local-ATR units it is 114%.

**3. Does the closing period fail because movement is lower, because time is
shorter, or both?** *Primarily time.* In local-ATR units the close is at 1.056×
the open — no movement deficit at all. What it lacks is runway: no 120-minute
horizon exists after 14:00, no 60-minute horizon after 14:30, and unresolved
rates rise to 5.8–10.2% for larger containers at 2R. **The closing block is
short, not quiet.**

**4. Is one ATR the minimum viable risk container for NQ throughout the day?**
*Slightly more than one.* At the QQQ-measured 6.19 bps, 1.0 ATR costs **11.0%**
of risk and fails the 10% gate. The minimum viable container is **≈1.2 ATR₁ₘ**,
and it is the same at every hour — the gate is set by the container, not the
clock.

**5. Do fixed point containers become increasingly unsuitable later in the
session?** *In economic terms, no; in risk terms, yes.* A fixed 30-point
container costs the same 6.7% of risk at every hour. But because the local
volatility halves, 30 points is 1.5 ATR at the open and about 3 ATR at the
close — the **same money buying a very different amount of market**. A fixed
point stop is a drifting risk decision, and that is the honest form of the
answer.

**6. Which frozen strategies are structurally mismatched to their existing time
windows?** None is mismatched *to its window*. Four are mismatched to their
**container**: IB 1R single and re-entry (13.4 ATR, half of setups resolve
neither barrier), and both Compression variants (48 ATR, stop engages ~1% of the
time). ORB-Fib is marginal at 5.6–6.1 ATR.

**7. Does anything beyond position sizing need to change by time of day?** *On
this evidence, no.* Barrier geometry is the driftless baseline in every block.
Local-ATR excursion is flat to +14%. Cost as a share of risk is identical.
**The single thing that genuinely changes is available runway**, and that is a
constraint on the closing block, not an architecture that differs by hour.

---

# VERDICT

## Primary verdict: **B — TIME AFFECTS ONLY SCALE**

Absolute movement differs by a factor of two from open to close. **ATR-normalised
barrier geometry and excursion distributions do not** — measured against the
volatility of its own time of day, the market offers 2.9 to 3.3 units of
excursion per unit of risk at every hour, and P(target before stop) sits on the
driftless baseline everywhere.

**Strategy architecture should remain unchanged. Only position sizing and
absolute point distances should adapt with the clock.**

## Verdict C also applies, in a restricted form

**Late-session opportunity is insufficient on time, not on movement.** The
closing block matches every other block in local-ATR excursion and barrier
geometry, but it cannot supply a 120-minute horizon at all, cannot supply 60
minutes after 14:30, and leaves 5.8–10.2% of larger-container 2R paths
unresolved. **C applies to the closing block only. Midday is not affected** —
its unresolved rates are 0.0–1.3% and its normalised excursion is the best of
the four.

## Viable risk containers

| | container | cost / risk |
|---|---|---|
| **viable** | 30 NQ points | 6.7% |
| **viable** | 1.5 × ATR₁ₘ | 7.3% |
| **viable, boundary** | 20 NQ points | 10.0%, exactly at the limit, no slippage headroom |
| **minimum** | **≈1.2 × ATR₁ₘ** | 10.0% |

## Structurally incompatible risk containers

| container | cost / risk | |
|---|---|---|
| 10 NQ points | **20.0%** | twice the gate |
| 0.5 × ATR₁ₘ | **21.9%** | twice the gate |
| **1.0 × ATR₁ₘ** | **11.0%** | **fails — the proposal's 9.3% estimate used NQ's ATR; the QQQ-measured unit is 15% smaller** |

## Frozen strategies by architectural compatibility

**Compatible** — container inside the cost gate, target attainable on the
majority of paths, resolution essentially always before the close:
ORB OR15 R3, ORB OR15 R4, ORB OR30 R3, ORB OR30 R4, pullback OR15 R3,
pullback OR30 R3, IB-mid pullback R2.

**Marginal** — feasible only on the upper part of the excursion distribution:
ORB-Fib continuation ORB15 A and ORB30 A (risk ~100 NQ points; target reached on
58–67% of paths; 1.8–5.4% resolve neither barrier).

**Structurally incompatible** — the risk container is the problem, not the
window: IB 1R single, IB 1R re-entry (13.4 ATR; **52% of setups reach neither
barrier before the close**), Compression D=10:00, Compression D=10:30 (48 ATR;
stop engages on **≈1%** of paths; ~$1,700 per MNQ contract).

---

## What this does not claim

No claim that a time block predicts direction; that an opening breakout has
edge; that midday mean reversion has edge; that any strategy should be deployed;
or that changing stop or target sizes creates expectancy. **A block having more
available movement does not mean trades in that block have edge.** Barrier
probabilities on a driftless path are geometry, and the tape confirms the path
is driftless to within a point.

Directional imbalance was measured and is null: median MFE minus median MAE is
−1.70, −0.09, −0.46, −0.21 bps across the four blocks, with 49.2–50.5% of paths
having MFE > MAE. **Diagnostic only; not promoted.**

## No new strategy is proposed

The map identifies one architectural gap — **no frozen strategy operates after
14:00, and the closing block is the one block with a genuine structural
constraint (runway, not movement)**. Whether that gap is worth filling is a
separate question and would need its own proposal and approval. None is made
here.

---

## Declared

No strategy P&L, expectancy, profit factor, win rate, drawdown, allocator, entry
pattern, directional rule or prop-evaluation simulation was calculated. Sealed
NQ dates were not read. 2016–2020 was not opened. All 5-point NQ recordings were
excluded. Every frozen timestamp, horizon, container, multiple and convention
was applied unchanged; the two additions — the NQ clock fix and the block-local
ATR arm — are declared in §0 with their direction of effect.
