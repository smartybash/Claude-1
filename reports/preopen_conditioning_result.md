# Pre-open conditioning, Stage 1: the null replicates on a new class of predictors

Pre-registered at `dc4f4bf` before `scripts/orderflow/preopen.py` was written
and before the extended-hours data was fetched. **Descriptive and predictive
only — no expectancy, no win rate, no trade, no rule appears anywhere in this
family.**

**Sealed NQ days were not read. 2016–2020 was not read** — the session builder
filters to `year >= 2021` before any frame reaches a condition.

---

## 1. The prior result this was testing against

| | |
|---|---|
| regime study combinations | 14 (price-derived, at a decision timestamp) |
| largest \|rho\| there | 0.042 |
| clearing the corrected threshold | 0 |
| cross-session spread in efficiency reproduced by random walks | 91% |

This family asked the same question of a **different class of predictor** —
conditions formed outside the cash session, none of them price-derived from the
session being predicted.

---

## 2. Counts and burden, stated before any result

| | |
|---|---|
| sessions built | **1,395** (2021-01-05 → 2026-08-31) |
| rejected by the builder | 3 |
| sessions with no overnight tape | **0** |
| conditions | 6 |
| outcomes | 5 |
| **total tests** | **30** |
| **Bonferroni α** | **0.001667** |
| permutations per test | 10,000 (matched group sizes) |
| pass bar | \|rho\| ≥ 0.10 **and** perm p < 0.001667 **and** 4 of 6 years agree **and**, for efficiency outcomes, \|decile spread\| ≥ 0.020 |

Per-condition n (the VIX limitation was declared in advance):

| condition | n |
|---|---|
| overnight range / trailing mean | 1,375 |
| overnight net displacement | 1,395 |
| prior close location in prior range | 1,395 |
| prior-day VIX close | **1,229** |
| prior-day VIX change | **1,228** |
| FOMC decision flag | 1,395 |

---

## 3. The positive control passed, so the run is valid

| | |
|---|---|
| early rv (09:30–10:00) vs post-10:30 rv | **rho = +0.7327**, n = 1,395 |
| required | > 0.40 |

The pipeline reproduces a known-forecastable outcome comfortably. Had it not,
nothing below would have been reported as evidence.

---

## 4. The answer

**Zero of the 30 tests pass on an outcome the decision rule turns on.**

| | |
|---|---|
| tests run | 30 (declared 30) |
| **passing on `eff_full`, `eff_post` or `ret`** | **0** |
| passing on `rv` or `range` (declared insufficient) | 9 |
| **largest \|rho\| on a decision outcome** | **0.0763** |
| largest \|rho\| anywhere | 0.6956 (VIX level → rv) |

### Efficiency, full session

| condition | n | Spearman | perm p | decile spread | years |
|---|---|---|---|---|---|
| overnight displacement | 1,395 | +0.0725 | 0.00740 | +0.0083 | 5/6 |
| VIX level | 1,229 | +0.0763 | 0.00870 | +0.0039 | 5/6 |
| VIX change | 1,228 | −0.0690 | 0.01640 | −0.0076 | 5/6 |
| prior close location | 1,395 | +0.0212 | 0.42566 | +0.0051 | 5/6 |
| FOMC flag | 1,395 | +0.0216 | 0.42366 | +0.0038 | 5/6 |
| overnight range | 1,375 | −0.0162 | 0.54755 | −0.0054 | 4/6 |

### Efficiency, post-10:30

| condition | n | Spearman | perm p | decile spread | years |
|---|---|---|---|---|---|
| VIX change | 1,228 | −0.0708 | 0.01280 | −0.0080 | 5/6 |
| prior close location | 1,395 | +0.0686 | 0.01140 | +0.0083 | 6/6 |
| VIX level | 1,229 | +0.0488 | 0.08659 | +0.0037 | 4/6 |
| overnight displacement | 1,395 | +0.0356 | 0.18628 | +0.0028 | 4/6 |
| FOMC flag | 1,395 | +0.0124 | 0.64514 | +0.0053 | 4/6 |
| overnight range | 1,375 | −0.0109 | 0.68523 | +0.0049 | 4/6 |

### Direction, signed session return

| condition | n | Spearman | perm p | decile spread, bps | years |
|---|---|---|---|---|---|
| overnight range | 1,375 | −0.0372 | 0.16738 | −9.4 | 5/6 |
| VIX level | 1,229 | +0.0407 | 0.15828 | +10.6 | 5/6 |
| VIX change | 1,228 | −0.0169 | 0.55424 | +23.6 | 4/6 |
| prior close location | 1,395 | +0.0085 | 0.75542 | −10.8 | 4/6 |
| overnight displacement | 1,395 | +0.0084 | 0.75232 | −17.2 | 3/6 |
| FOMC flag | 1,395 | +0.0015 | 0.95550 | −2.0 | 4/6 |

**The largest directional rho in the family is 0.0407.** Nothing here is within
reach of the bar, and the three closest calls on efficiency (0.0725, 0.0763,
−0.0708) miss the α by factors of 4 to 10 and miss the decile-spread bar by
factors of 2.4 to 5.

---

## 5. What did pass, and why it is not sufficient

Declared in advance as not sufficient, because volatility is already known to be
forecastable and the project has already shown that volatility scaling does not
move R-normalised results.

| condition | outcome | rho | perm p | years |
|---|---|---|---|---|
| **VIX level** | rv | **+0.6956** | 0.00010 | 6/6 |
| **VIX level** | range | **+0.5901** | 0.00010 | 6/6 |
| overnight range | rv | +0.2966 | 0.00010 | 6/6 |
| overnight range | range | +0.2495 | 0.00010 | 6/6 |
| prior close location | rv | −0.1984 | 0.00010 | 6/6 |
| overnight displacement | rv | −0.1781 | 0.00010 | 5/6 |
| prior close location | range | −0.1466 | 0.00010 | 6/6 |
| FOMC flag | rv | +0.1258 | 0.00010 | 6/6 |
| VIX change | rv | +0.1081 | 0.00020 | 6/6 |

`0.00010` is the permutation floor at 10,000 shuffles — it means "no shuffle out
of 10,000 reached the observed rho", not a measured value.

**This is the sharpest thing in the run and it is the thing that does not
matter.** The conditions carry real, six-of-six-years-consistent information —
about magnitude. **They carry none about shape or sign.** VIX level moves rv by
a factor of 2.6 across deciles (69.4 → 181.0 bps) and moves full-session
efficiency by 0.0039, which is 0.4 percentage points on a quantity whose own
level is about 0.06.

That contrast is the result. It is not that the predictors are weak — two of
them are among the strongest relationships the project has measured. It is that
**the predictable component of a session is its size, and size is exactly what
R-normalisation divides out.**

---

## 6. The declared redundancy check

| | |
|---|---|
| Spearman(\|overnight displacement\|, the dropped `gap`) | **+0.9995**, n = 1,395 |

As stated in §1.2 of the pre-registration, these are the same quantity by
construction. `gap` was dropped because the regime study already tested it;
overnight displacement was kept and computed from extended-hours data. The
0.9995 confirms the redundancy was real and that dropping one of the pair cost
nothing.

---

## 7. A defect I found and fixed before writing this up

The first run reported the FOMC flag as `0/6` years in every panel. The year-
split guard required a condition to take at least 3 distinct values in a year,
which a binary flag never does — **so the FOMC condition could not have satisfied
the consistency rule regardless of its rho.**

Fixed: a binary condition is admitted to a year when both groups have at least 3
observations. On the corrected run the FOMC flag reports 4/6 to 6/6.

**The correction changed one verdict, and it was on the volatility side**
(FOMC → rv, which clears rho 0.1258 at p 0.00010, moving the volatility-pass
count from 8 to 9). **No decision-outcome verdict moved**, because no FOMC test
came within a factor of 4 of the rho bar on `eff_full`, `eff_post` or `ret`.
The result in §4 is identical under both versions.

---

## 8. The decision, as declared

> *"If no condition predicts session efficiency or direction beyond the
> corrected threshold, stop and report that the finding replicates on a new
> class of predictors. Do not proceed to a strategy stage."*

**Zero conditions clear the threshold on `eff_full`, `eff_post` or `ret`.**

**This family stops at Stage 1. No Stage 2 is proposed and none is written.**

The regime study's null was on price-derived predictors measured inside the
session. This run reaches the same null from outside it — overnight tape, the
volatility surface, and the event calendar — across 1,395 sessions and six
years, with a positive control at rho +0.73 confirming the machinery works.

**Two independent classes of predictor, 44 tests between them, largest
efficiency rho 0.076 and largest directional rho 0.041.** Session shape does not
appear to be forecastable from anything this project has been able to measure.

---

## 9. Ledger entry

| screen | sample | outcome |
|---|---|---|
| **pre-open conditioning, Stage 1** | **1,395 sessions, 30 tests** | **closed, 0 of 30 on decision outcomes. 9 of 30 on volatility outcomes, declared insufficient in advance. Positive control +0.733. Stops at Stage 1; no strategy stage.** |

Standing constraints honoured: sealed NQ days unread, **2016–2020 unread and
unspent**, nothing frozen that would justify opening it.

Reproduce: `python3 scripts/orderflow/preopen.py`.
Full output in `reports/preopen_conditioning_output.txt`; per-test detail in
`reports/preopen_conditioning.csv`.
