# Pre-open conditioning — Stage 1, declared before running

**Descriptive and predictive only. No expectancy, no trading rule, no trade is
generated anywhere in this family.**

**Sealed NQ days stay sealed. 2016–2020 stays unread.** Every source below
begins 2021-01-04 and cannot reach the holdout.

---

## 0. The prior result, acknowledged first

The regime study (`43ab596`, `reports/regime_forecastability_result.md`) already
asked whether information available at a decision timestamp predicts what the
rest of the session does.

| | |
|---|---|
| combinations tested | **14** (7 predictors × 2 decision timestamps) |
| largest \|Spearman rho\| | **0.042** |
| clearing the corrected threshold | **0** |
| efficiency autocorrelation session-to-session | **none** |
| cross-session spread in efficiency reproduced by random walks | **91%** |

**That finding is not being retested.** This family exists to ask whether a
*different class* of predictor — conditions formed outside the cash session —
does any better. If it does not, the finding replicates on new ground and the
family stops at Stage 1.

---

## 1. Three problems with the declared condition list, surfaced before running

### 1.1 Two of the eight conditions were already tested in that study

The regime study's predictor list is, verbatim from `regime_forecast.py`:

```
PRED = ["or_ratio", "rv_open", "eff_open", "gap", "prior_range", "or_pos",
        "vol_ratio"]
```

| declared condition | already in that study | as |
|---|---|---|
| **the cash open gap from prior close** | **yes** | `gap` = `1e4 × abs(open − prev_close) / prev_close`, trailing-normalised |
| **prior session range relative to trailing mean** | **yes** | `prior_range` = prev session range, trailing-normalised |

Both were tested against post-decision efficiency and both returned null. The
instruction is *"Do not retest any price-derived predictor from that study."*

**Both are therefore DROPPED from this family's grid.** Their prior results are
reported in the output rather than recomputed. If you would rather I re-run
them against the new outcome set, say so and I will add them back — but as
written, running them is the thing the instruction forbids.

### 1.2 "Overnight net displacement" and "the cash open gap" are the same number

The overnight session runs from the prior 16:00 close to the 09:30 open. Its
**net displacement is, by construction, the open minus the prior close** — which
is the gap. They are not two conditions.

**Resolution:** the gap is dropped under §1.1 anyway, so **overnight net
displacement is kept** as the one surviving member of that pair, computed from
extended-hours data rather than from the cash open. **Its correlation with the
dropped `gap` is reported**, so the redundancy is visible rather than hidden.

### 1.3 The declared outcome list contains no directional measure

The decision point says *"if no condition predicts session efficiency **or
direction**"*. The four declared outcomes — realised volatility, range,
efficiency, post-10:30 efficiency — are all unsigned. None of them can answer a
question about direction.

**Resolution:** a fifth outcome, **signed session return** (`log(close/open)`
in bps), is added so the decision rule you wrote can actually be evaluated.
This is declared here, before results, and is counted in the test burden.

---

## 2. The six conditions, defined exactly

All are known before 09:30 ET. None is derived from the cash session being
predicted.

| # | condition | definition | source |
|---|---|---|---|
| 1 | **overnight range** | `(ETH high − ETH low)` over 16:00 prior day → 09:29, in bps of the prior close, ÷ its own trailing 20-session mean, shifted | QQQ 1-min extended hours |
| 2 | **overnight displacement** | `1e4 × (ETH close 09:29 − prior RTH close) / prior close`, signed | QQQ 1-min extended hours |
| 3 | **prior close location** | `(prior close − prior low) / (prior high − prior low)`, in [0,1] | QQQ RTH, prior session |
| 4 | **VIX level** | prior-day VIX close | `data/vix_daily_5y.json` |
| 5 | **VIX change** | prior-day VIX close − the close before it, in points | same |
| 6 | **FOMC flag** | 1 on a scheduled FOMC decision date, else 0 | `data/events/fomc.csv` |

**Condition 3 is not `or_pos` from the regime study.** `or_pos` is the position
of the *opening range* close within the opening range, measured inside the
session being predicted. Condition 3 is the position of the *prior* session's
close within the *prior* session's range. Different window, different session.

### Declared data limitation

**VIX coverage begins 2021-08-12**, so conditions 4 and 5 run on roughly 1,240
sessions against 1,396 for the others. This is declared now, not discovered
later, and the per-condition n is printed in the counts pass.

---

## 3. The five outcomes

| outcome | definition |
|---|---|
| `rv` | session realised volatility, bps, 09:30–16:00 |
| `range` | `1e4 × (high − low) / open`, 09:30–16:00 |
| `eff_full` | efficiency ratio = \|net displacement\| ÷ path length, full session |
| `eff_post` | efficiency ratio over 10:30–16:00 only |
| `ret` | **signed** session return, `1e4 × log(close/open)` — added per §1.3 |

---

## 4. Test burden and corrected threshold, stated before any result

| | |
|---|---|
| conditions | **6** |
| outcomes | **5** |
| **total tests** | **30** |
| **Bonferroni α** | **0.05 / 30 = 0.001667** |

**Pass requires all three**, fixed now and carried from the regime study so the
two families are directly comparable:

1. \|Spearman rho\| ≥ **0.10**
2. permutation p < **0.001667**
3. top-minus-bottom decile spread ≥ **0.020** in the outcome's own units for
   `eff_full` / `eff_post`; for `rv`, `range` and `ret` the spread is reported
   but the decile criterion is **not applied**, because those are not the
   outcomes the decision rule turns on

**The FOMC flag is binary.** Deciles are undefined for it, so its "spread" is
reported as the difference in group means (FOMC days vs all others) and its rho
is the point-biserial equivalent. Declared rather than fudged.

---

## 5. The positive control, and the run is void without it

**Later realised volatility is known to be forecastable at rho above 0.4.**

Control: early-session realised volatility (09:30–10:00) against post-10:30
realised volatility. This deliberately *does* use cash-session data — it is a
pipeline check, not a candidate, and is excluded from the 30-test burden.

> **If the control does not reproduce rho > 0.40, the run is declared invalid
> and nothing else in it is reported as evidence.**

---

## 6. Controls and splits

- **Random-label control:** 10,000 permutations of the condition against fixed
  outcomes, group sizes matched exactly. The permutation distribution supplies
  the p value used for the decision; the parametric Spearman p is reported
  beside it for reference only.
- **Year split:** every condition-outcome pair is reported by year, with
  **4 of 6 years** required to share the sign of the pooled rho.
- **Clustering:** one observation per session, so there is no within-session
  clustering. Trailing-window normalisation induces mild serial dependence
  across adjacent sessions; the permutation control is non-parametric and does
  not assume independence, which is why it governs rather than the parametric p.

---

## 7. The decision point, declared

**If no condition predicts `eff_full`, `eff_post` or `ret` beyond the corrected
threshold, this stops at Stage 1** and is reported as a replication of the
regime finding on a new class of predictors. No strategy stage.

**A condition that predicts only `rv` or `range` is explicitly NOT sufficient.**
Volatility is already known to be forecastable, and the project has already
shown that volatility scaling does not move R-normalised results. A
volatility-only hit will be reported as a successful positive control and
nothing more.

**If something does predict efficiency or direction**, I will write Stage 2 as
a separate pre-registration for approval and will not run it.

---

## 8. What this run will not do

- No expectancy, no win rate, no trade, no rule.
- No sweep: every definition above is fixed and none is tuned.
- 2016–2020 is not read. Sealed NQ days are not read.

---

Committed before `scripts/orderflow/preopen.py` was written or run, and before
the extended-hours data was fetched.
