# H1-B: frozen rule and holdout test — pre-registration

**Frozen 2026-09-30 by the selection rule of `reports/h1b_exploration_plan.md`
(b0a6556), applied to the discovery grid (`reports/h1b_exploration_output.txt`).
Committed before the holdout (2021-01-01 → 2026-09-24) is read for this
hypothesis.** The holdout is read once, and its verdict is final.

## The frozen rule (NQ)

- **Signal (15:44 ET):** r = (close of the 15:44 bar) ÷ (prior RTH day's close) − 1,
  on the back-adjusted RTH series. Days need ≥ 300 bars; the prior day is the
  previous day in that series.
- **Big-day filter:** trade only if |r| is at or above the **90th percentile** of
  |r| over the **prior 250** eligible days (at least 120 required; causal).
- **Direction:** long if r > 0, short if r < 0.
- **Trade:** entry at the **open of the 15:45 bar**, exit at the **close of the
  15:59 bar**. One trade a day at most; flat every night. About 27 trades a year.
- **Costs:** NQ $2.25 + 1 tick per side ($14.50 per round trip).

## What discovery showed (seen; cannot be evidence)

- 281 trades, +$97.3 a trade, +$27,350 total. Halves: +$857 a year (2010-06 →
  2015-09) and +$4,319 a year (2015-09 → 2020-12). ES, same configuration:
  +$17,996. Longs +$85 and shorts +$110 a trade.
- **2020 alone contributes +$20,935 of +$27,350.** Without 2020: 240 trades at
  +$26.7 a trade.
- The discovery p (0.0004) is inflated by the selection over 45 configurations,
  and the null pays full costs on random exposure, so a rule near cost
  break-even beats it easily. **40 of the 45 configurations cleared p ≤ 0.05
  against it.** Only the holdout can show whether the filter works.
- The original H1 top-quintile observation that prompted H1-B was not
  statistically clear on its own: t +0.83, bootstrap 95% CI −$44 to +$106 a
  trade.

## Holdout test (as fixed in the plan)

- **Window:** holdout trade days 2021-01-01 → 2026-09-24. The trailing
  percentile may use late-2020 days as history; that is causal.
- **Null:** 5,000 lists. Each random trade keeps one actual trade's direction and
  the same 15:45 open → 15:59 close window and cost, on a uniformly random
  eligible holdout day (big or not). Seed 20260930.
- **Pass: holdout total net > 0 and p ≤ 0.05.** One test.
- **Pass →** forward paper-tracking from 2026-10-01, plus the prop simulator on
  the full-window trades. **Fail →** H1-B closed for good; no further
  thresholds, entries or measures.
- **Descriptive:**
  - a same-days sign-flip check: random directions on the same big days, to
    isolate the direction call;
  - holdout results by year, per MNQ, and ES with the same frozen rule;
  - the holdout without its biggest year.

Script: `scripts/databento/h1b_holdout.py`, committed with this file before it runs.
