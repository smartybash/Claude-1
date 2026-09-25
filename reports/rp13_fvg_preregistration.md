# RP-13 pre-registration — FVG family, multi-timeframe

**Committed before any script exists.** The frozen specification is the one you
supplied (§§2–10 of your brief), reproduced below. Where the brief leaves a rule
open, **my reading is frozen here, before any count or R is computed**, and
marked **[FROZEN READING]**. Nothing in this document may change after an R is
read.

Harness to follow: `scripts/orderflow/rp13_fvg.py`.

---

## 0. Data, declared

| | |
|---|---|
| intended instrument | NQ (the rule was defined on NQ) |
| NQ 1-minute history, unsealed | **not available** — the only NQ tape is 44 sessions, all consumed by RP-010 |
| substitute, declared | **QQQ 1-minute RTH**, `QQQ_1m_holdout.parquet` (2016-01-04 → 2020-12-31, 1,259 sessions) + `QQQ_1m.parquet` (2021-01-04 → 2026-08-31, 1,421 sessions) |
| span | **2,680 sessions**, clearing the 2,000-session minimum. The 2021-onward file alone (1,421) would not |
| conversion | NQ ≈ 41.27 × QQQ. Every rule is ATR-normalised and cost is in bps, so the ratio affects **only the one-tick stop buffer**: 0.25 NQ pt ÷ 41.27 = $0.006, rounded **up to one QQQ tick, $0.01** |
| resampling | 1m → 2m, 3m, 5m, 15m, 30m, 60m **in-script**, RTH only, bars anchored at 09:30 ET. No separately fetched resolution |
| half days | excluded, by the corrected two-signal `sessioncal.early_closes` |
| sealed dates | not applicable — no NQ tape is read; `holdout.py` guard is still imported |

### Prior use, declared

- **Every QQQ 1-minute period on disk has been examined** by earlier families.
  **2016–2020 was spent as an out-of-sample block** (IB pullback) and may never
  again be *called* out-of-sample; here it is **discovery**.
- **FVG itself has prior positive, non-pre-registered results in this
  repository** on overlapping data: a 5-minute QQQ FVG on 2024-07 → 2026-07
  (`f2bab1f`: fixed 2R +0.173R, t 4.54, n 1,081) and a 27-year daily FVG
  (`0761d41`). This family is designed **after** those results. They were
  different rules (swing stops, trend filters, no ATR gap floor, no sweep
  prerequisite), but the family is not naïve about FVGs, and the 5m arm's
  2024-07 → 2026-07 window overlaps the earlier study.
- **There is no out-of-sample block.** As your brief says, the controls and the
  max-statistic permutation are the only discipline.

---

## 1. Frozen specification (from the brief)

### 1.1 FVG detection

- **Bullish FVG:** high(C1) < low(C3); zone = [high(C1), low(C3)].
- **Bearish FVG:** low(C1) > high(C3); zone = [high(C3), low(C1)].
- **Gap size** ≥ 1.0 × ATR(14, TF).
- **Displacement:** range(C2) ≥ 1.5 × ATR(14, TF).
- **Liquidity-sweep prerequisite:** the FVG forms within 5 bars of a PDH/PDL raid.

**[FROZEN READING] ATR(14, TF):** simple mean of true range over the **14 bars
ending at C1**, on RTH bars of that timeframe, carried across sessions. The first
bar of each session uses high − low (the overnight gap is not RTH range). ATR is
taken at C1 so that the displacement candle cannot inflate its own threshold.

**[FROZEN READING] PDH/PDL raid.** PDH and PDL are the prior RTH session's high
and low (a half day's RTH ends at 13:00). A **raid bar** is a bar whose high
exceeds PDH while the previous bar's high did not, or whose low undercuts PDL
while the previous bar's low did not — a fresh excursion, not every bar that sits
beyond the level. **"Within 5 bars" means C3 lies 0–5 bars after the raid bar.**
**Direction is the reversal:** a **PDL raid qualifies a bullish FVG**, a **PDH
raid qualifies a bearish FVG** — the sweep takes liquidity and the displacement
reverses away from it. The any-direction reading is **not tested**.

### 1.2 Entry

Trigger: price touches the near edge of a valid FVG. Enter on the next candle's
open.

**[FROZEN READING]** The brief's "enter on next candle open at that level" admits
two readings (a limit order at the edge, or the next bar's open). The honest-fill
language it cites ("stop entries at max(trigger, bar_open)") belongs to stop
orders, which a retracement entry is not. Frozen: **the touch bar is the first
bar after C3 whose low ≤ zone top (bullish) or high ≥ zone bottom (bearish); entry
is at the open of the next bar.** No intrabar fill is assumed.

- **One trade per FVG**, on its first touch, **same session only** (the 15:59
  time stop makes this an intraday family).
- **One open position per timeframe.** Touches while a position is open are
  skipped and counted.
- **Voided setups:** if the entry open is already at or beyond the stop, no trade
  is taken; counted.

### 1.3 Exit

- **Stop:** opposite gap boundary ∓ one tick ($0.01). Bullish: high(C1) − $0.01.
- **Target:** fixed **2R** from the actual entry price. No trailing, break-even
  or partials.
- **Time stop:** close of the last bar at or before 15:59 ET.
- **Honest fills:** stop exits at min(stop, bar_open) for longs (max for shorts)
  when a bar opens through the stop. Targets fill **at the target**, never better.
- **Entry bar excluded from the exit search**, as the brief specifies.

**[FROZEN READING] Same-bar ambiguity:** a bar touching both stop and target is
resolved **stop first**. **Sensitivity, declared now:** because entry is at the
bar's open, the entry bar's full range lies after the fill; excluding it (the
brief's rule) is optimistic. The **entry-bar-inclusive, stop-first** version is
reported alongside as a sensitivity. It is not the primary.

### 1.4 Cost

**0.667 bps round trip** per trade, charged in R: cost_R = 0.667e-4 × entry ÷
risk. **A timeframe whose median cost/risk exceeds 10% is rejected before its
expectancy is computed**, and its R is not printed.

---

## 2. Timeframe grid

**Primary:** 1m, 2m, 3m, 5m. **Diagnostic, never promotable:** 15m, 30m, 60m.

**[FROZEN READING] The grid-adjustment rule the brief anticipates,
mechanised:** valid setups per month are counted **before any R is read**. **A
primary timeframe below 12 valid setups/month is moved to diagnostic** before
its R is computed, and the move is printed. If no primary timeframe survives, the
family **cannot promote at any resolution**, and every R reported is
descriptive.

---

## 3. Multiple testing

Four primary tests. Bonferroni α = 0.0125 (conservative given overlap).
**Decisive control: max-statistic permutation, 10,000 draws.**

**[FROZEN READING] What "permute trade labels" means.** The label is the FVG's
**direction**. For every trade the harness also simulates the **mirror trade** —
same entry bar and price, stop and target at the same distances on the opposite
side, same exits, same cost. A permutation draw assigns each trade's direction
at random (keeping timing and risk geometry fixed), recomputes the per-trade t
at each primary timeframe, and records the **maximum |t| across the primary
timeframes**. The observed max |t| is compared with that distribution. **A
timeframe's result can be claimed only if the empirical p < 0.05.**

This tests whether the FVG's direction carries information, holding fixed
everything else the pattern selects — when, where, and at what risk.

---

## 4. Power (from the brief, stated before results)

Per-trade R sd ≈ 1.5. MDE at 2 SE: 1m ±0.034–0.054R; 2m ±0.048–0.078R; 3m
±0.060–0.094R; 5m ±0.086–0.134R. **5m is secondary if n < 800.** Diagnostic arms
are not powered and not claimable. **Realised n will be reported against these
priors before any R**, because they assume 50–100 setups/month at 1m, which the
gap-floor, displacement and sweep filters may make optimistic.

---

## 5. Controls, per timeframe

**6.1 Mechanism (load-bearing).** The identical pipeline with **no ATR filters**
— any three-candle non-overlap — **keeping the sweep prerequisite**, so the only
difference is gap size and displacement. **[FROZEN READING]** "Performs as well
or better" = the control's net expectancy ≥ the primary's at that timeframe (point
estimate). **If the mechanism control fails at all four primary timeframes: stop.
Placebo, timing and directional controls are not run.**

**6.2 Placebo.** For each real valid FVG, a random three-candle window in the
same session and timeframe, after the first 5 bars, with a zone of the **same
width in ATR units** anchored on the random window's C3 (bullish: top = low(C3),
bottom = top − width; bearish mirrored), **same direction** as its paired real
FVG. Identical entry and exit. Seeded.

**6.3 Timing.** Primary is all hours. Reported diagnostically: the NY-AM window
**09:30–11:00 ET** and R by hour. If the effect lives in one hour, the family is
a time-of-day bet.

**6.4 Directional (iFVG).** A valid FVG that a later bar **closes through** (below
the bottom of a bullish zone, above the top of a bearish one) becomes an inverse
FVG in the opposite direction. Entry on the first later touch of the zone's
**new** near edge, next bar's open; stop beyond the opposite boundary ± tick; 2R;
same session, same fills. If iFVG beats the primary, the directional reading is
wrong.

---

## 6. Promotion rule (mechanical, unchanged)

All at **one** pre-registered primary timeframe:

1. net expectancy ≥ +0.10R, 90% CI lower bound > 0
2. ≥ 12 trades/month
3. trades/month × expectancy ≥ 2.0R
4. max **out-of-sample** drawdown ≤ 6R — **cannot be satisfied in discovery;
   there is no OOS block.** Discovery drawdown is reported descriptively
5. Monte Carlo pass probability ≥ 45% on a 50k evaluation — **run only if 1–3 and
   6–8 hold**, since it cannot rescue a failure elsewhere
6. median cost/risk ≤ 10%
7. mechanism control passed at that timeframe
8. max-statistic permutation p < 0.05
9. no promotion if the permutation p ≥ 0.05, whatever the marginal t

**Because criterion 4 cannot be met without an OOS block, this discovery run
cannot promote anything.** The best outcome is "survives discovery, requires a
forward block".

## 7. Falsification (from the brief)

- Mean ≤ 0 at all four primary timeframes → **family closed**. No rescue via
  iFVG, order blocks or Silver Bullet as a new primary.
- Mechanism control fails at all four → **mechanism dead; stop.**
- Mechanism passes at some timeframes only → resolution-specific finding, **not
  a promotion**; re-specify under a new pre-registration.
- Permutation p ≥ 0.05 despite a strong marginal t → **null**.

## 8. Order of the report

1. platform suite count
2. data quality and session counts
3. **counts before R**: valid FVGs, touches, trades, voids, skips per timeframe;
   setups/month against the priors; the grid adjustment if any
4. cost/risk per timeframe, and rejections
5. primary R per timeframe, with the entry-bar-inclusive sensitivity
6. mechanism control → stop here if it fails at all four
7. placebo, timing, iFVG
8. max-statistic permutation
9. promotion table and one verdict
