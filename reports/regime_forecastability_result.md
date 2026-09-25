# The session regime is not forecastable — 0 of 14, and there is barely a regime there

Pre-registered at `43ab596`
(`reports/regime_forecastability_preregistration.md`) before this ran.
Descriptive. **No rule was traded. No expectancy was computed. The 6-variant
stage-2 budget is unspent.**

Sealed NQ days were not read.

---

## 1. Result

| | |
|---|---|
| sessions | **1,418** — QQQ 1-minute, 2021-01-04 to 2026-08-31, 0 rejected |
| combinations tested | **14** — 7 predictors × 2 decision timestamps |
| cleared \|ρ\| ≥ 0.10 | **0 of 14** |
| cleared p < 0.00357 | **0 of 14** |
| cleared spread ≥ 0.020 | **0 of 14** |
| **cleared all three** | **0 of 14** |

**Largest effect anywhere in the grid: \|ρ\| = 0.042, decile spread 0.0054.**
The bars were 0.10 and 0.020. Nothing came within a factor of two of either.

Not one of the fourteen reached even **nominal** significance at an uncorrected
0.05 — the smallest p-value against later efficiency was 0.118.

### Efficiency after the decision timestamp — the thing the hypothesis needs

`OR_MIN` 15 (D = 09:45 ET), median 285 post-decision bars:

| predictor | n | Spearman | p | Pearson | bottom d1 | top d10 | spread |
|---|---|---|---|---|---|---|---|
| or_ratio | 1,398 | −0.007 | 0.795 | +0.005 | 0.0696 | 0.0678 | −0.0018 |
| rv_open | 1,398 | −0.025 | 0.346 | −0.013 | 0.0652 | 0.0705 | +0.0054 |
| **eff_open** | 1,418 | **+0.035** | 0.193 | +0.040 | 0.0692 | 0.0716 | +0.0025 |
| gap | 1,397 | −0.023 | 0.389 | −0.012 | 0.0688 | 0.0695 | +0.0007 |
| prior_range | 1,397 | −0.042 | 0.118 | −0.020 | 0.0708 | 0.0658 | −0.0050 |
| or_pos | 1,418 | +0.029 | 0.270 | +0.022 | 0.0643 | 0.0686 | +0.0043 |
| vol_ratio | 1,398 | +0.015 | 0.588 | +0.005 | 0.0694 | 0.0680 | −0.0014 |

`OR_MIN` 30 (D = 10:00 ET), median 270 post-decision bars — if anything weaker:

| predictor | Spearman | p | spread |
|---|---|---|---|
| or_ratio | −0.002 | 0.943 | +0.0038 |
| rv_open | −0.016 | 0.543 | −0.0048 |
| **eff_open** | **−0.001** | 0.971 | +0.0025 |
| gap | −0.024 | 0.363 | −0.0045 |
| prior_range | −0.041 | 0.127 | −0.0029 |
| or_pos | −0.024 | 0.366 | −0.0050 |
| vol_ratio | +0.010 | 0.715 | −0.0025 |

**The strongest candidate a priori was `eff_open` — early efficiency predicting
later efficiency. It returned ρ = +0.035 and ρ = −0.001.** Whatever the first
fifteen or thirty minutes are doing, it carries no information about whether the
rest of the session trends.

The decile ladders confirm the correlations are not hiding a non-monotonic
relationship. The best spread in the grid, `rv_open` at OR15:

| decile | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| mean eff_later | .0652 | .0751 | .0727 | .0612 | .0743 | .0669 | .0670 | .0636 | .0643 | .0705 |

That is not a weak signal. It is a flat line with noise on it.

---

## 2. The positive control fired hard, so this is not a broken pipeline

Later realised volatility was carried as a second outcome, declared in advance
as a check on the machinery rather than part of the hypothesis. Same predictors,
same windows, same code path, same sessions:

| predictor | ρ vs **eff**_later | ρ vs **rv**_later | rv_later d1 → d10 |
|---|---|---|---|
| rv_open | −0.016 | **+0.414** (p = 1e-64) | 54.8 → 116.4 bps |
| or_ratio | −0.002 | **+0.347** (p = 2e-43) | 55.8 → 106.3 bps |
| vol_ratio | +0.010 | **+0.315** (p = 2e-35) | 61.5 → 105.6 bps |
| prior_range | −0.041 | **+0.249** (p = 6e-22) | 60.0 → 98.8 bps |
| gap | −0.024 | **+0.190** (p = 4e-13) | 67.6 → 92.5 bps |

**Later volatility is powerfully forecastable from the same information, at the
same timestamp, through the same code.** Bottom-decile to top-decile later
volatility slightly more than doubles. Five of seven predictors clear every bar
that all fourteen missed against efficiency.

So the null is a fact about the market, not about the measurement. **This is
exactly what section 6 of the pre-registration said would happen, written down
before the run:** the efficiency ratio divides the volatility level out by
construction, and volatility clustering is the one thing that was reliably
forecastable here.

`eff_open` is the informationally inert case in both directions — it predicts
later efficiency at ρ = +0.035 and later *volatility* at ρ = +0.020. It predicts
nothing at all.

---

## 3. The deeper finding: there is barely a regime to forecast

A null on prediction leaves one loophole open — perhaps trending and choppy
sessions are real and persistent states, and these seven predictors simply
missed them. Two checks close it.

**Session efficiency does not persist from one session to the next.**

| lag | 1 | 2 | 3 | 5 |
|---|---|---|---|---|
| autocorrelation | **−0.054** | −0.009 | −0.037 | −0.001 |

A persistent regime state would autocorrelate positively. This is
indistinguishable from zero and, at lag 1, marginally *negative*.

**And the spread across sessions is almost entirely sampling noise.** Simulating
1,418 driftless random walks of the same length, 400 times over:

| | observed | random walk | ratio |
|---|---|---|---|
| cross-sectional SD | 0.0499 | 0.0458 (95% range 0.0440–0.0480) | **1.09** |
| mean | 0.0682 | 0.0608 | **1.12** |
| p10 → p90 | 0.0103 → 0.1385 | 0.0096 → 0.1252 | — |

**Random walks of 270 steps produce almost exactly the dispersion in efficiency
that the real sessions show.** The visible difference between a session that
trended and one that chopped is, to about 91%, what finite-length coin flipping
looks like. Sessions do not come in two kinds. They come in one kind, and the
appearance of kinds is the arithmetic of short samples.

There are two genuine, small effects, and both are constants rather than states:
mean efficiency runs **12% above** the random-walk value, and cross-sectional SD
runs **9% above** it. Real, but unconditional — already fully inside what the
three flat screens measured, and not something regime-conditioning could unlock.

---

## 4. What this settles

The hypothesis was that continuation rules win in trending sessions and lose in
choppy ones, netting to the flat pooled results seen three times.

**That mechanism requires the regime to be callable before the trade. It is
not** — 0 of 14, with the best effect a fifth of the size required, while the
same machinery forecasts volatility at ρ = 0.41.

**And the mechanism requires sessions to have regimes at all.** Their efficiency
does not persist across sessions and their dispersion is 91% reproducible by
random walks.

So the flat pooled results are not a positive and a negative cancelling. There
is no forecastable state to separate them with.

**Stage 2 was not run. The 6-variant budget is unspent.** Promoting this would
have meant conditioning on a whole-session statistic — the lookahead the
pre-registration was built to prevent.

### What is not ruled out

- Regimes on a **slower clock**. This tested session-level state called at 09:45
  or 10:00. Multi-week volatility or trend regimes are a different question and
  this says nothing about them.
- Regimes defined by something **other than the efficiency ratio**. Efficiency
  was chosen because every rule in this project is a continuation rule and it is
  the property those rules need. A different definition is a different test —
  and would need its own pre-registration and its own reckoning with the fact
  that later volatility, which *is* forecastable, has already been shown not to
  move these rules' results.
- The **1,259 sessions of 2016–2020** in `QQQ_5m.parquet` remain unread by this
  project, and are still available for something worth spending them on.

---

## 5. Where the ledger stands

| screen | sample | outcome |
|---|---|---|
| pullback, QQQ screen | 1,418 sessions, 16 variants | closed, 0 of 16 |
| ORB + VWAP, QQQ screen | 1,418 sessions, 16 variants | closed, 0 of 16 |
| OR height, promoted | 1,418 + 1,256 held out, 4 variants | closed, 0 of 4 |
| European session, descriptive | 21 NQ sessions | same market, worse terms; nothing bought |
| **regime forecastability** | **1,418 sessions, 14 combinations** | **closed, 0 of 14; stage 2 not run** |

Reproduce: `python3 scripts/orderflow/regime_forecast.py`.
Per-session values in `reports/regime_forecast_OR{15,30}.csv`,
grid summary in `reports/regime_forecast_summary.csv`.
