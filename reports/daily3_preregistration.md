# Three daily effects — forward paper-tracking: pre-registration (decision P7)

**Registered 2026-09-25, before any forward session exists and before the repaired
rules below are computed on any data.** The user's instruction: frozen rules; the
effects must beat an **exposure-matched random-entry null**, not merely be positive;
paper-track from the registration date; **first review in 12 months** (on or after
2026-09-25 + 12 months). Evidence from before today (2010-06-07 → 2026-09-24) is
**seen** and can never be the test.

## 0. The rules as archived cannot be traded forward — the minimal repairs

Reading the archive code for freezing exposed look-ahead in two of the three rules:

| rule | archive code | problem |
|---|---|---|
| daily FVG (`backtest_daily_fvg.py`) | fills at the gap edge during bar *i*; trend filter `close[i] > SMA20[i]`; stop = lowest low of bars *i−5 … i*; exit search starts at *i+1* | the filter and the stop use bar *i*'s close and low, unknown when the limit fills intrabar; a stop hit on the entry day is ignored |
| compression breakout (`backtest_range_breakout.py`) | compression test `box ≤ 2.0 × ATR14[i]`, where ATR14[i] includes bar *i*; long and short can both fire on bar *i*; exit search starts at *i+1* | the breakout bar's own range inflates the ATR that qualifies it; same-day stop hits are ignored |
| oversold bounce (`backtest_oversold_long.py`) | buy the close after 3+ consecutive down closes, sell the next close | the signal needs the very close it buys at |

**The frozen rules below are the archive rules with only these repairs** (each
marked **R**): every filter uses information available before the order; the entry
day is resolved on the 1-minute path. Nothing else — thresholds, lookbacks, slots,
exits — changes. The seen-data context run reports both the archived and the
repaired version, so the size of the repair is visible.

## 1. Data and bars

NQ continuous front month (Databento `GLBX.MDP3`, `NQ.v.0`), RTH only (09:30–16:00
ET). Daily bars are built from the 1-minute RTH bars; prices are ratio
back-adjusted at rolls so that levels are continuous. A position open across a
roll is rolled at that session's close and pays **one extra round trip**. Costs
per round trip: **NQ $2.25 + 1 tick per side**, MNQ $0.62 + 1 tick per side. Fills
and exits are resolved on 1-minute bars: a resting limit or stop fills at its
level, or at the bar's open if the market opens through it; the stop is checked
before the target within a minute.

## 2. The three frozen rules

**D1 · Daily FVG continuation** (chart rule, `0761d41`).
- Gap: 3-bar FVG on daily bars — bull if `low[i] > high[i−2]`, bear if
  `high[i] < low[i−2]`, size ≥ 0.03% of the close. The **3 most recent open gaps per
  side** are kept; a slot empties when price fully fills the gap (as archived).
- Signal on day *i*: first touch of an open bull gap's top arriving from above
  (`low[i] ≤ top`, `low[i−1] > top`); bear mirror at the bottom of a bear gap.
- **R1** trend filter: long only if `close[i−1] > SMA20` computed through *i−1*;
  short only if below.
- Entry: resting limit at the touched gap edge (the highest touched top for longs).
- **R2** stop: lowest low of the prior 5 daily bars (*i−5 … i−1*) for longs, highest
  high for shorts; no trade if the stop is not beyond the entry.
- **R3** risk filter: skip if risk > 2.5 × ATR14 computed through *i−1* (Wilder, as archived).
- Exit: **3R target** or stop; no time exit. **R4** the path is followed from the
  fill minute on day *i*.

**D2 · 5-day compression breakout** (chart rule, `2fed2b4`).
- Box: high and low of the prior 5 daily bars. **R5** compression: box height
  ≤ 2.0 × ATR14 computed through *i−1*.
- Entry: resting stop at the box high (long) / box low (short) on day *i*. **R6** if
  both sides trade on day *i*, only the side reached first (1-minute order) is taken.
- Stop: the opposite side of the box. Exit: **3R target** or stop (the archived
  "fixed3R", the chart's shipped target). **R4** path from the fill minute.
- As archived, every qualifying day is a signal (positions may overlap).

**D3 · Oversold bounce** (`5a5051a`).
- **R7** signal at 15:59 ET: the 15:58 bar's close is below the prior RTH close, and
  the prior two RTH closes were each below the one before (three consecutive down
  closes, the 3+ bucket).
- Long at the 15:59 bar's close; exit at the next session's 15:59 bar close. Long only.

## 3. The test — exposure-matched random-entry null

For each rule, over the forward window, the actual trade list is compared with
**5,000 random trade lists** of the same size. Each random trade keeps one actual
trade's **direction, holding length (sessions held, entry and exit time of day)
and costs**, and is placed at a uniformly random eligible session of the same
window. Same number of trades, same time in the market, same long/short mix:
market drift is matched and cannot be mistaken for the effect.

- Statistic: total net P&L in NQ dollars. p = share of random lists ≥ the actual.
- **Pass at a review**: total net P&L > 0 **and** p ≤ 0.05, **Holm across the
  three**. Anything else: not demonstrated. A rule is never promoted on seen data.
- **Power, stated now.** On seen data the rules trade roughly 15–60 times a year
  each. Twelve months may be too few trades to reach p ≤ 0.05 even for a real
  effect. The first review therefore reports the result and its power (the
  smallest per-trade effect twelve months could detect); it does not close a rule
  for being underpowered.

## 4. Paper-tracking protocol

- Window starts **2026-09-25** (the first session after the last pulled bar).
- `scripts/databento/daily3.py --forward` rebuilds bars from forward 1-minute data
  and appends every signal, fill and exit to `reports/daily3_paper_ledger.csv`.
  Trades still open at a review are marked to market and flagged.
- Forward data: `ohlcv-1m` for `NQ.v.0`, about **$0.11 a month** (quoted
  2026-09-25). Every pull follows the budget rule (quote, plan, approval); a
  standing approval is requested as decision P8.
- **First review: 2027-09-25** or the first session after it.

## 5. Seen-data context (not a test)

Before paper-tracking starts, the archived and repaired rules are run once on
2010-06-07 → 2026-09-24 with the same null, **labelled seen, context only**, to show
what the repairs cost and what the null does to the drift. Nothing in it can pass
or fail a rule.
