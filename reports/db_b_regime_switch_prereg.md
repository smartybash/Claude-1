# Study (b) — regime switch: pre-registration, strict one-shot replication

Registered **before any Databento data is requested or read**. Data roles per
`reports/databento_register.md` §5. **One frozen specification, no variants, run
once.** If it fails, it is closed permanently with no re-tuning.

## Prior

This repository has already closed this idea: regime forecastability **0 of 14**
price-derived predictors (QQQ 2021–2026), and `reports/trend_regime_study.md` —
daily ADX, efficiency ratio and EMA spreads do not predict whether the next
session trends or chops. **The expected result is a null.**

## Data

Databento `ohlcv-1m`, `NQ.v.0`, continuous, 2010-06-06 → latest, UTC → ET.
Daily RTH bars built from 1-minute bars; indicators use the **ratio back-adjusted**
series (as in study (a)); every traded return is within one contract. Half days
and roll days are excluded from trading and still enter indicator history.
**NQ only.**

## Regime label — from data up to the prior RTH close only

Standard published settings and thresholds, not fitted:

| indicator | settings | votes TREND if | votes CHOP if | abstains |
|---|---|---|---|---|
| ADX | 14, Wilder | > 25 | < 20 | 20–25 |
| Efficiency ratio | 10 closes | ≥ 0.30 | < 0.30 | never |
| Choppiness index | 14 | < 38.2 | > 61.8 | 38.2–61.8 |

**TRENDING** = at least 2 trend votes. **CHOPPY** = at least 2 chop votes.
Otherwise **NEUTRAL**, which is not traded.

## Rules — one trigger, two responses

- **Opening range:** 09:30–10:00 ET, RTH high and low.
- **Trigger:** the first 1-minute close outside the range between 10:00 and 15:00 ET.
  One trade per day. Entry at the next bar's open.
- **TRENDING → breakout** in the direction of the break. Stop = the opposite side of
  the opening range. Exit at the close of the last bar before 16:00. No target.
- **CHOPPY → fade**, against the break. Stop = the break-side range edge plus one
  range height. Target = range midpoint. Otherwise exit at the close of the last bar
  before 16:00.
- **Fills:** entries at the next open; stops at the stop, or at the bar's open if the
  bar gaps through; targets at the target. Stop before target within a bar.

Breakout and fade share the same trigger, so **the regime label alone decides the
sign of the trade**. That is exactly what the test isolates.

## Costs

NQ $2.25 commission + 1 tick ($5.00) slippage per side; MNQ $0.62 + $0.50.

## Tests

1. **Regime permutation (decisive):** shuffle the regime labels across days, keeping
   the counts of TRENDING, CHOPPY and NEUTRAL days fixed, 5,000 times; recompute the
   strategy Sharpe. p = (1 + #permuted ≥ observed) ÷ 5,001.
2. **Random-entry null matched to exposure,** 5,000 sims: on the same days, enter in
   a random direction at the same time with the same stop and target geometry.
3. **All four cells** (breakout|trend, fade|chop, breakout|chop, fade|trend) are
   reported **descriptively**. No single cell can be promoted.

**Walk-forward:** nothing is fitted, so there is no refit; results are reported per
year.

## Periods

| block | label |
|---|---|
| first label (after indicator warm-up) → 2020-12-31 | **never used for this hypothesis; read by other daily studies, incl. overnight gap base rates** — **decisive** |
| 2021 → registration date | seen; reported, not decisive |

## Kill criteria — 2010–2020 block

Closed permanently if **any** fails: Sharpe ≥ 0.8; profit factor ≥ 1.3; regime
permutation p ≤ 0.05; random-entry null p ≤ 0.05.

**If it passes, the conflict with `trend_regime_study.md` is explained before
anything else is done with it.**

Metrics as study (a): Sharpe, CAGR, max drawdown in $ per NQ and per MNQ, trade
count, profit factor. Holm-adjusted p across the two tests.
