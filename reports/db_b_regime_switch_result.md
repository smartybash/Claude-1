# Study (b) — regime switch: result — CLOSED PERMANENTLY

Strict one-shot replication, pre-registered at
`reports/db_b_regime_switch_prereg.md` (`7cf6513`) before any Databento data was
requested. Harness `scripts/databento/study_b_regime.py`; raw output
`reports/db_b_regime_switch_output.txt`. NQ `ohlcv-1m`, labels from ADX(14),
efficiency ratio(10) and Choppiness(14) through the **prior** close, published
thresholds, one opening-range trigger with the response decided by the label.

## Decisive block — 2010-07-20 → 2020-12-31
*Never used for this hypothesis; read by other daily studies, incl. overnight gap
base rates.*

Labels: TREND 783, CHOP 764, NEUTRAL 1,133. Traded: 740 TREND, 742 CHOP.

| | value | kill threshold |
|---|---|---|
| Sharpe | **−1.00** | ≥ 0.8 |
| profit factor | 0.75 | ≥ 1.3 |
| CAGR | −9.30% | |
| max drawdown | $101,718 / NQ · $11,284 / MNQ | |
| regime-permutation p (Holm) | 0.988 (1.000) | ≤ 0.05 |
| random-direction p (Holm) | 0.995 (1.000) | ≤ 0.05 |

**The four cells (descriptive, $ per NQ trade after costs):**

| | on TREND days | on CHOP days |
|---|---|---|
| breakout | **−96.8** (38.2% win) | +9.6 |
| fade | **+30.0** (64.7% win) | **−35.4** |

**The labels point the wrong way.** On "trending" days the breakout loses and the
fade wins, and the reverse on "choppy" days. The real labels do **worse than
shuffled ones** (permutation p = 0.99). The strategy loses in 9 of 11 years.

## Seen block — 2021 → 2026-09-24 (not decisive)

Sharpe +0.53, PF 1.14, permutation p 0.23. **The breakout makes money on both
labels** (TREND +$211, CHOP +$106 per trade) — a period effect, not a regime
effect — and the labelled strategy does not beat shuffled labels.

## Agreement with the prior

`reports/trend_regime_study.md` (daily ADX and efficiency ratio do not predict
trend vs chop) and regime forecastability (0 of 14) predicted a null. This result
is worse than a null in 2010–2020 and null in 2021–2026. **There is no conflict to
reconcile.**

## Verdict

> **Regime switch: fails every kill criterion. Closed permanently. No re-tuning,
> no variants.**
