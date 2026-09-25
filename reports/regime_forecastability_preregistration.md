# Is the session regime forecastable? — declared before running

The hypothesis is that continuation rules have positive expectancy in trending
sessions and negative expectancy in choppy ones, which would net to the flat
pooled results returned by three screens. This document fixes the prior question
and its pass/fail criteria before any number exists.

**A regime-conditional strategy is impossible if the regime is not forecastable
at the decision timestamp.** That is tested first, descriptively, and if it fails
the work stops there and that is the complete answer.

Sealed NQ days are not read at any point. This screen never opens the NQ tape.

---

## 1. The trap this is built to avoid

The efficiency ratio reported in `reports/european_vs_us_session_profile.md` was
a **whole-session statistic**. It used bars from after the decision timestamp to
classify the session those bars belong to. Conditioning a trade on it would be
pure lookahead, and no result built on it would mean anything.

Everything below therefore obeys one constraint, and it is the only constraint
that matters here:

> **The predictor window ends at or before the decision timestamp. The outcome
> window starts at the decision timestamp. They share no bars.**

Trailing-history terms are shifted by one session so that no session is ever
classified using its own data or anything after it.

---

## 2. Sample

| | |
|---|---|
| instrument | QQQ, 1-minute, `data/intraday_long/QQQ_1m.parquet` |
| sessions | **1,418** — 2021-01-04 to 2026-08-31 |
| session filter | unchanged from the three prior screens (`MIN_BARS` 360 of 390) |
| years | 2021, 2022, 2023, 2024, 2025, 2026 — six, as the rejection rule requires |

**This is the in-sample set.** Stage 1 is a descriptive question about the data's
own structure, so in-sample is the right place to ask it and the user asked for
these 1,418. But it must be said plainly: anything found here is found in
sample. `data/intraday_long/QQQ_5m.parquet` holds **1,259 sessions across
2016–2020 that this project has never read**, and that set stays untouched
unless and until there is something worth spending it on.

---

## 3. Decision timestamp, outcome, and what is actually being predicted

The rules enter after the opening range closes, so the decision timestamp is

> **D = session open + `OR_MIN`**, for `OR_MIN` ∈ {15, 30} — i.e. 09:45 and
> 10:00 ET.

**Outcome — the later regime:**

> `eff_later` = |log(close at flat) − log(close at D)| ÷ Σ|1-minute log returns
> from D to flat|

over the post-decision window **[D, flat]**, where flat is 18:30 UTC as in every
prior screen. High = the remainder of the session trends. Low = it chops.

**The null this is measured against.** For a driftless random walk of N steps
the expected efficiency ratio is √(2/πN). The post-decision window holds roughly
270 one-minute bars, giving a random-walk baseline of **≈0.049**. A sample
median near that figure means the sessions are, on this measure,
indistinguishable from random walks — so the baseline is stated now rather than
discovered later.

---

## 4. The candidate predictors

Seven, each computable from bars at or before D, each measured at both `OR_MIN`
values, for **14 predictor–window combinations**. Scale-free or
trailing-normalised, because the outcome is scale-free and a raw level would
mostly measure the volatility regime rather than the trend/chop regime.

| # | name | definition, all using only bars ≤ D |
|---|---|---|
| 1 | `or_ratio` | OR height ÷ its trailing 20-session mean (shifted) — the existing project quantity, from `or_height.py` |
| 2 | `rv_open` | realised vol over [open, D] ÷ its trailing 20-session mean (shifted) |
| 3 | `eff_open` | \|net displacement\| ÷ path length **within [open, D]** — the direct early analogue of the outcome, and the strongest candidate a priori |
| 4 | `gap` | \|open − prior close\| in bps ÷ its trailing 20-session mean (shifted) |
| 5 | `prior_range` | prior session's high−low in bps ÷ its trailing 20-session mean (shifted) |
| 6 | `or_pos` | \|2·(close at D − ORL)/(ORH − ORL) − 1\| — 1 = price sits at an OR extreme, 0 = mid-range |
| 7 | `vol_ratio` | volume over [open, D] ÷ its trailing 20-session mean (shifted) |

### Overnight range is not on disk, and is substituted rather than faked

`QQQ_1m.parquet` runs **09:30–15:59 only**. There is no pre-market or overnight
data for QQQ anywhere in this repository, so the requested overnight-range
predictor **cannot be computed**. Its information content is approached by two
quantities that can: **`gap`** (the overnight move that actually printed) and
**`prior_range`** (the prior session's realised range). This is a substitution,
it is declared here, and it is not claimed to be equivalent.

---

## 5. What is reported for stage 1

For each of the 14 combinations:

- **Spearman ρ** between predictor and `eff_later`, with its p-value. Spearman
  rather than Pearson as the headline because both series are bounded, skewed
  and heavy-tailed; **Pearson r is reported alongside** as asked.
- **Top-decile minus bottom-decile mean `eff_later`**, with each decile's mean
  and n (~142 sessions per decile).
- The full decile ladder, so a non-monotonic relationship is visible rather than
  hidden inside a single correlation coefficient.

---

## 6. Stage 1 pass criteria — fixed now

A candidate **predicts** only if it clears all three:

| criterion | threshold | why |
|---|---|---|
| **Spearman \|ρ\|** | **≥ 0.10** | below this it explains under 1% of variance |
| **p-value** | **< 0.00357** | 0.05 Bonferroni-corrected over the 14 combinations declared above |
| **decile spread** | **≥ 0.020 in `eff_later`** | ≈40% of the random-walk baseline of 0.049 — a materially different regime, not a detectable wobble |

The decile-spread bar is the binding one and it is deliberately demanding. With
1,418 sessions a decile mean carries a standard error near 0.0025, so spreads of
0.005 would be statistically significant and economically meaningless. **The
question is not whether a relationship is detectable. It is whether it is large
enough to sort sessions into two different markets.**

### If nothing clears all three

**The work stops and the answer is reported as a null.** No grid is run, no rule
is tested, nothing is promoted. A regime-conditional strategy is impossible if
the regime is not forecastable, and that is a complete answer to the hypothesis.

### A prior worth recording before the result exists

The efficiency ratio is **deliberately scale-free** — net displacement over path
length, with the volatility level divided out. The best-established
short-horizon regularity in equity index data is **volatility clustering**, and
that regularity has been normalised away by construction. So the single most
likely outcome of stage 1 is that `rv_open`, `prior_range` and `vol_ratio`
predict *later volatility* strongly while predicting *later efficiency* barely
at all. Writing that down now is what stops it being reframed as an insight
afterwards.

---

## 7. Stage 2 — only if stage 1 passes

### Predictor and threshold, both fixed by rules declared here

- **Predictor:** the single best stage-1 candidate, ranked by decile spread,
  ties broken by |ρ|. One predictor. Not a combination, not a fitted weight.
- **Direction:** set by the **sign of the stage-1 Spearman ρ**, which is fixed
  before stage 2 runs.
- **Threshold:** the predictor's **trailing 250-session median, shifted by one
  session**. Not the full-sample median — a full-sample median leaks the whole
  period's distribution into every session's classification and would not be
  implementable live. The trailing median is causal and a live desk could
  compute it.

### The grid — exactly 6 variants, the full budget

The surplus region from the prior screens, unchanged: **stop 1.0 ATR**, entry
bar skipped, honest fills, max 2 trades/session, flat 18:30 UTC.

| # | rule | `OR_MIN` | target |
|---|---|---|---|
| 1 | ORB (`or_height.run_session`, unchanged) | 15 | 3R |
| 2 | ORB | 15 | 4R |
| 3 | ORB | 30 | 3R |
| 4 | ORB | 30 | 4R |
| 5 | pullback (`pullback.run_session`, unchanged) | 15 | 3R |
| 6 | pullback | 30 | 3R |

Both rules are taken **as already specified**. No parameter is re-tuned.

### Rejection rules — the standing set, plus the two added for this test

1. **The favourable bucket must contain ≥ 300 sessions.**
2. **The effect must hold in ≥ 4 of the 6 years within the favourable regime.**
   A regime that exists only in 2022 is a volatility artifact, not a regime.
3. Favourable-arm expectancy **> 0 after costs**, with a per-session **t ≥ 2**.
4. **The unfavourable regime is reported alongside, for every variant.** This is
   the test of the regime story itself: if the rule is merely *absent* in the
   unfavourable bucket rather than *negative*, the story is weaker than it looks,
   because the hypothesis specifically claims the losses live there. That
   finding is reported as such and not buried.

### Standing instrumentation, unchanged

Honest fills with the naive result beside them; entry bar skipped; entry
lookahead check counted rather than assumed; ambiguous-bar rate; **trade and
session counts printed before any performance number.**

---

## 8. What would make this whole exercise wrong

If stage 1 passes on `eff_open` alone and stage 2 then shows an effect, the most
likely mundane explanation is that early efficiency and later efficiency are
both driven by a slow-moving volatility state, and the rule is picking up the
volatility regime while wearing a trend label. The stage-2 report must therefore
show the favourable and unfavourable buckets' **median risk in bps** side by
side. If they differ materially, the buckets are sorted by volatility and the
regime claim is not established.

---

Committed before `scripts/orderflow/regime_forecast.py` was run.
