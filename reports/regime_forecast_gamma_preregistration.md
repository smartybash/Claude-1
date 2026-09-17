# Does dealer gamma predict the later regime? — amendment, declared before running

An amendment to `reports/regime_forecastability_preregistration.md` (`43ab596`),
which tested 7 price-based predictors at 2 decision timestamps and returned
**0 of 14**. This adds dealer gamma as predictors 8 and 9 and asks the same
question, under the same constraint.

Sealed NQ days are not read. This screen never opens the NQ tape.

---

## 1. The question, unchanged

> Does information available at the decision timestamp predict whether the
> **remainder** of the session trends or chops?

Outcome, predictors and the binding constraint are exactly as before:

> **The predictor window ends at or before D. The outcome window starts at D.
> They share no bars.**

`eff_later` = |net displacement| ÷ path length over [D, flat], D = open + `OR_MIN`.

**Why gamma is a fair candidate and not an obvious one.** Gamma is already
established *on this project's own data* as a predictor of **range** — terciles
1.85% / 1.55% / 1.24%, corr(distance-below-flip, next-day range) = +0.40
(`reports/gamma_backtest_findings.md`). But range is a volatility quantity, and
`eff_later` is scale-free by construction. The original run found exactly that
split for price-based predictors: they forecast later *volatility* at ρ up to
0.414 and later *efficiency* at ρ ≤ 0.042. **The specific question here is
whether gamma breaks that pattern or repeats it.**

---

## 2. The two predictors

For QQQ session *t*, both come from the option chain as-of the **close of
session t−1**, which is how `av_gex.py` computes them and how
`gamma_backtest_findings.md` uses them.

| # | name | definition |
|---|---|---|
| 8 | `net_gex` | net dealer gamma exposure, signed, from the prior close's chain |
| 9 | `dist_flip` | (spot − gamma_flip) / spot, in bps, signed. Negative = below the flip |

**Both are known before the session opens**, so they clear the causality gate by
a wider margin than the price-based predictors did — those needed bars from
inside the session.

**Alignment is strict.** A session is used only if its gamma row is from the
**immediately preceding** trading session. No stale rows, no forward fill, no
nearest-match.

**No normalisation is applied to `net_gex`, deliberately.** The headline
statistics — Spearman ρ and the decile ladder — are both rank-based and therefore
invariant to any monotone rescaling, so normalising would change nothing.
**Pearson r is scale-sensitive** across a six-year span in which the index level
and open interest both drifted; it is reported as the original harness did, with
that caveat attached rather than silently.

---

## 3. Sample, and its two real weaknesses

| | |
|---|---|
| source | `data/gex_history.jsonl`, computed by `av_gex.py` from Alpha Vantage chains |
| rows | 335 QQQ (1 SPY row excluded), 2020-01-15 to 2026-08-17 |
| **usable sessions** | **323**, after strict one-session alignment against the QQQ 1-minute set |

### Weakness 1 — the sample is 89% one two-year block

| year | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|
| sessions | 12 | **0** | 13 | 12 | 133 | 153 |

**2022 is entirely absent**, and 2021/2023/2024 are monthly samples of ~12. 286
of 323 sessions (89%) are 2025–2026. Two consequences, both declared now:

1. **The standing "holds in ≥4 of 6 years" rejection rule cannot be applied to
   this sample.** If stage 2 were ever reached, that would have to be resolved
   first — by fetching the missing chains, not by waiving the rule.
2. A **declared robustness read** on the 2025–2026 block alone is reported
   alongside the full sample. It is a diagnostic, not a pass/fail gate, and it is
   named here so it cannot be introduced afterwards if the full-sample result is
   inconvenient.

### Weakness 2 — this test is less powerful than the one it amends

n = 323 against the original's 1,418.

| | |
|---|---|
| ρ needed to clear the p-value gate at n=323 | **0.167** |
| ρ detectable with 80% power | **≈ 0.21** |

**So the `|ρ| ≥ 0.10` criterion is no longer the binding one — the significance
gate is, and it effectively demands ρ ≈ 0.17.** A true effect of ρ = 0.12 would
fail here on sample size alone. That is a real limitation and it is stated before
the result, not after.

**But the test is well-powered against the effect size that matters.** Gamma's
known relationship to *range* on this same data is corr **+0.40**. If gamma
predicted efficiency anywhere near as well as it predicts volatility, this sample
would detect it comfortably. The null is therefore informative against the
interesting hypothesis, and weak only against effects far smaller than gamma is
already known to produce.

---

## 4. Correction to the test count

I told the user this would take the Bonferroni denominator from 14 to 16. **That
was wrong.** Running both decision timestamps, as the original harness does, gives
2 predictors × 2 windows = **4 new combinations, not 2.**

| | |
|---|---|
| original | 14 |
| new | 4 |
| **total** | **18** |
| **p-value bar** | **0.05 / 18 = 0.002778** |

The bar tightens slightly rather than loosening, so the correction makes the test
harder, not easier.

---

## 5. Pass criteria — the same three, unchanged except for the denominator

| criterion | threshold |
|---|---|
| Spearman \|ρ\| | ≥ 0.10 |
| p-value | **< 0.002778** (0.05 Bonferroni over 18) |
| top-minus-bottom decile spread in `eff_later` | ≥ 0.020 |

All three required, as before. Deciles of 323 sessions hold ~32 each.

**Positive control carried through unchanged.** `rv_later` is measured for both
new predictors. It is not part of the hypothesis. If gamma predicts later
volatility through this code but not later efficiency, that reproduces the
original finding on a new and independent predictor family — which is a stronger
result than the original null alone.

---

## 6. What each outcome means, fixed now

- **Nothing clears all three.** Gamma joins the price-based predictors: it
  forecasts volatility, not trend-vs-chop. A gamma regime filter cannot help a
  continuation rule, and the 6-variant stage-2 budget stays unspent. Combined
  with the structural point that an R-normalised rule is near-invariant to a pure
  volatility scaling, that closes the gamma-as-regime-filter line.
- **Something clears all three.** Then gamma has done what nothing else has, and
  a pre-registered stage 2 becomes worth writing — but only after the 2022 gap is
  filled, because the year-stability rule cannot be applied to this sample.

---

Committed before `scripts/orderflow/regime_forecast_gamma.py` was run.
