# RP-007 Stage 1A1 — QQQ broad level validity screen

Pre-registered at `a72fe50`, written and committed **before** the harness
existed. Price only. **No NQ data, no footprint, no delta, no cumulative fills,
no depth, no absorption. No P&L, expectancy, profit factor, drawdown or trading
rule.**

Sample: **QQQ one-minute, 2021-01-04 → 2026-08-31, 1,421 sessions, 68 months.
Discovery only, forever.**

Every frozen constant applied unchanged: θ = 0.1435, shifts at ±10/3 and ±20/3
zone widths, round interval $2.50, primary outcome reclaim within 10 minutes,
α = 0.05/30 = 0.001667, frequency bar 12 first interactions per month.

---

## 0. Two defects found and fixed **before** any result was read

Both were caught by looking at the counts, which is what counts-before-outcomes
is for.

**Defect 1 — the approach-side convention was inverted.** The code assigned
`side = +1` when the previous bar sat entirely *below* the zone and then treated
`+1` as a support test. Approaching from below makes the level **overhead**,
which is a resistance test. The outcome logic then measured penetration and
reclaim in the wrong direction for every interaction in the study.

It was visible in the counts, not the results: IB high showed **1,307 support
and 0 resistance** interactions, which cannot be true of a level that sits above
the morning's price by construction. Fixed; the counts now read IB high 71
support / 803 resistance, prior-day high 234 / 422, extended-hours low 441 / 30.

**Defect 2 — Initial Balance levels were interacted with before they existed.**
IBH, IBL and IBM are defined by bars 0–59 and were being tested for interaction
from bar 1. The first "interaction" with the IB high was frequently the bar that
*set* it. That is look-ahead, and it produced a fake 13–15% reclaim rate for
those families. Fixed by gating IB levels (and their shifted controls) to bars
≥ 60, as the pre-registration required and the code did not implement.

Neither fix was made after seeing an outcome, and both moved the affected
families **toward** the rest of the pack rather than away.

---

## 1. The headline

| | n | reclaim within 10 min |
|---|---|---|
| **genuine levels** | **12,893** | **76.98%** |
| **shifted controls** | **43,903** | **77.23%** |
| **difference** | | **−0.25 points** |

p = 0.556. **The minimum detectable difference at this sample size is ±1.40
points.** This is a precisely measured zero, not an underpowered null — the
screen could have seen a 1.4-point effect and there is not one.

The pre-registered per-family MDE was ±9.1 points. Pooled, the study resolves
six times finer than that, and still finds nothing.

---

## 2. Counts, before any outcome

| | |
|---|---|
| sessions available | **1,421** |
| excluded: no usable prior session | 1 |
| excluded: fewer than 300 bars | 1 |
| **sessions used** | **1,419** |
| sessions with no extended-hours data (XH/XL/XM only) | **24** — exactly June 2026 plus 23 July, because the QQQ extended-hours fetch already honours the NQ seal |
| clusters: isolated / two-level / three-or-more | **21,071 / 1,113 / 119** |
| `CROSSED` events (gapped through, never tested) | 23 |
| shifted controls generated | **54,932** |
| shifted controls **excluded** for overlapping a genuine level | **6,903 (12.6%)** |
| first interactions with a valid matched random control | **8,921 of 13,733 (65.0%)** |
| first interactions / repeated / total | **13,733 / 88,143 / 101,876** |

| family | level obs | first | **isolated first** | repeated | support | resist | 1st/mo | iso/mo |
|---|---|---|---|---|---|---|---|---|
| prior RTH high | 1,419 | 656 | **584** | 3,892 | 234 | 422 | 9.6 | 8.6 |
| prior RTH low | 1,419 | 551 | **506** | 3,391 | 414 | 137 | 8.1 | 7.4 |
| prior RTH close | 1,419 | 838 | **595** | 5,734 | 460 | 378 | 12.3 | 8.8 |
| prior RTH VWAP | 1,419 | 773 | **677** | 4,451 | 436 | 337 | 11.4 | 10.0 |
| prior VAH | 1,419 | 771 | **653** | 4,753 | 320 | 451 | 11.3 | 9.6 |
| prior VAL | 1,419 | 673 | **576** | 4,314 | 456 | 217 | 9.9 | 8.5 |
| prior POC | 1,419 | 798 | **513** | 5,403 | 443 | 355 | 11.7 | 7.5 |
| extended-hours high | 1,395 | 657 | **591** | 3,844 | 63 | 594 | 9.7 | 8.7 |
| extended-hours low | 1,395 | 471 | **423** | 2,875 | 441 | 30 | 6.9 | 6.2 |
| extended-hours mid | 1,395 | 672 | **581** | 4,351 | 360 | 312 | 9.9 | 8.5 |
| IB high | 1,419 | 874 | **784** | 4,968 | 71 | 803 | 12.9 | 11.5 |
| IB low | 1,419 | 784 | **712** | 4,539 | 733 | 51 | 11.5 | 10.5 |
| IB mid | 1,419 | 988 | **866** | 5,890 | 521 | 467 | 14.5 | 12.7 |
| session VWAP (causal) | 1,419 | 1,403 | **1,403** | 14,366 | 689 | 714 | 20.6 | 20.6 |
| round $2.50 | 3,862 | 3,741 | **3,429** | 21,397 | 1,992 | 1,749 | 55.0 | 50.4 |

The support/resistance splits are the sanity check the inverted convention
failed: prior-day high is approached from below 64% of the time, prior-day low
from above 75%, extended-hours low from above 94%, IB high from below 92%. Those
are the right shapes.

**Primary per-family sample = isolated first interactions.** A cluster's outcome
cannot be attributed to one member, and the selection rule requires a family to
pass **alone** before any cluster may qualify. All-cluster figures are in §9.

---

## 3. Level-family results — isolated first interactions

Advantage in percentage points over each shifted control. `rand` is the true
rate minus the mean of 200 matched-random repetitions. `cov` is the share of the
family's interactions that received a valid matched control. `p(best)` is the
**least** significant of the four shifted comparisons, because a family must
beat all four.

| family | n | reclaim-10 | pen% | −20/3 W | −10/3 W | +10/3 W | +20/3 W | rand | cov | p(best) |
|---|---|---|---|---|---|---|---|---|---|---|
| PDH | 584 | 74.7 | 98.3 | −1.5 | +0.4 | −1.0 | +0.6 | −1.6 | 76% | 0.873 |
| PDL | 506 | 74.5 | 98.8 | +0.3 | +1.6 | +1.9 | +1.3 | −0.3 | 82% | 0.918 |
| PDC | 595 | 77.6 | 98.2 | +0.0 | −2.7 | +2.1 | +4.1 | −1.1 | 73% | 0.997 |
| PDVWAP | 677 | 79.9 | 99.0 | −0.3 | +1.1 | −0.6 | +2.0 | −1.4 | 78% | 0.881 |
| VAH | 653 | 77.9 | 97.7 | +0.9 | −1.4 | +0.1 | +2.3 | −0.7 | 77% | 0.976 |
| VAL | 576 | 76.9 | 98.3 | −2.0 | +0.9 | −2.6 | −1.0 | −2.1 | 80% | 0.748 |
| POC | 513 | 78.2 | 98.6 | +0.0 | −2.6 | −1.2 | +2.6 | −0.5 | 75% | 0.996 |
| XH | 591 | 74.6 | 99.2 | +0.3 | −0.8 | +1.2 | −3.2 | −0.5 | 77% | 0.900 |
| XL | 423 | 78.0 | 98.8 | −0.2 | −1.7 | −0.5 | −1.3 | −0.9 | 82% | 0.940 |
| XM | 581 | 74.9 | 98.8 | −3.3 | −4.4 | −1.6 | −0.1 | −4.5 | 70% | 0.961 |
| IBH | 784 | 72.8 | 99.0 | −1.2 | +1.7 | +3.4 | +2.3 | −0.3 | 73% | 0.614 |
| IBL | 712 | 76.5 | 98.3 | −3.3 | −0.3 | +1.3 | +1.3 | −0.9 | 75% | 0.892 |
| IBM | 866 | 76.3 | 96.5 | −0.0 | +1.6 | −2.1 | +1.4 | — | **0%** | 0.998 |
| VWAP | 1,403 | 82.0 | 98.6 | −4.5 | −0.5 | −0.7 | −3.2 | +18.8 | **3%** | 0.718 |
| ROUND | 3,429 | 76.5 | 98.1 | −0.5 | −0.3 | −0.8 | +1.3 | −1.9 | 83% | 0.769 |

**No family beats all four shifted controls. The largest advantage anywhere is
+4.1 points, on one of four arms, at p = 0.997.** Nothing approaches α = 0.00167.

The reclaim ladder is flat at every horizon, not just at ten minutes:

| horizon | genuine | shifted | difference |
|---|---|---|---|
| 1 min | 48.9% | 48.6% | +0.32 |
| 3 min | 62.6% | 62.9% | −0.29 |
| 5 min | 69.4% | 69.4% | +0.01 |
| **10 min** | **77.0%** | **77.2%** | **−0.25** |
| 15 min | 80.6% | 80.9% | −0.30 |

### Two control-coverage failures, recorded rather than buried

**IB mid receives zero matched random controls, and session VWAP receives 3%.**
The matched control uses each candidate price's *first* interaction of the
session. A genuine interaction that happens late, at a mid-range price, has no
admissible candidate: every mid-range price was already touched early. IB mid is
mid-range **and** gated to bar ≥ 60, so its coverage is exactly zero.

VWAP's "+18.8 vs random" therefore rests on 40 of 1,403 interactions against a
pool whose median size is **two candidates**. **It is not evidence and I am not
treating it as any.** VWAP fails conditions 1, 3 and 4 regardless, so the verdict
does not turn on it — but the number would be the most quotable in the study and
it is worthless.

---

## 4. Support and resistance, never pooled

| family | n supp | reclaim | vs shift | n resist | reclaim | vs shift | both + |
|---|---|---|---|---|---|---|---|
| PDH | 207 | 78.3 | +0.4 | 377 | 72.7 | −0.8 | no |
| PDL | 379 | 72.6 | +0.7 | 127 | 80.3 | +2.6 | **yes** |
| PDC | 324 | 79.9 | +1.0 | 271 | 74.9 | +0.8 | **yes** |
| PDVWAP | 385 | 81.0 | +1.0 | 292 | 78.4 | −0.1 | no |
| VAH | 273 | 85.3 | +4.6 | 380 | 72.6 | −2.5 | no |
| VAL | 400 | 77.2 | −0.5 | 176 | 76.1 | −2.9 | no |
| POC | 304 | 79.6 | −0.4 | 209 | 76.1 | −0.1 | no |
| XH | 52 | 80.8 | −1.2 | 539 | 74.0 | −0.5 | no |
| XL | 399 | 77.7 | −1.2 | 24 | 83.3 | +4.3 | no |
| XM | 315 | 74.6 | −3.8 | 266 | 75.2 | −0.6 | no |
| IBH | 63 | 82.5 | +3.6 | 721 | 72.0 | +1.6 | **yes** |
| IBL | 669 | 76.2 | −0.2 | 43 | 81.4 | +0.9 | no |
| IBM | 451 | 78.9 | +1.7 | 415 | 73.5 | −1.4 | no |
| VWAP | 689 | 85.1 | +0.7 | 714 | 79.0 | −5.1 | no |
| ROUND | 1,836 | 77.8 | −0.5 | 1,593 | 75.0 | +0.4 | no |

**Three of fifteen are positive on both sides**, and the largest of those is
+2.6 points against an MDE of roughly ±13 points per side. VAH's +4.6 on the
support side sits beside −2.5 on the resistance side — the classic one-sided
shape this table exists to expose.

---

## 5. Rotation after reclaim, MFE and MAE — all in ATR₁ₘ units

Economic reference: 3 × MNQ round turn = **0.2871 ATR**.

| family | n reclaimed | rot 5 | rot 10 | rot 15 | **rot 30** | **control rot 30** | MFE | MAE |
|---|---|---|---|---|---|---|---|---|
| PDH | 436 | +0.970 | +0.991 | +1.076 | **+1.084** | **+1.014** | 4.228 | 4.771 |
| PDL | 377 | +1.004 | +0.798 | +0.685 | +0.910 | +0.732 | 4.682 | 5.522 |
| PDC | 462 | +0.566 | +0.580 | +0.514 | +0.426 | +0.378 | 4.432 | 4.962 |
| PDVWAP | 541 | +1.031 | +1.008 | +1.095 | +0.769 | +0.558 | 4.605 | 5.134 |
| VAH | 509 | +0.671 | +0.692 | +0.571 | +0.509 | +0.533 | 4.104 | 4.839 |
| VAL | 443 | +0.947 | +0.886 | +0.965 | +1.050 | +1.012 | 4.716 | 5.181 |
| POC | 401 | +0.749 | +0.764 | +0.929 | +0.297 | +0.318 | 4.385 | 5.355 |
| XH | 441 | +0.917 | +0.848 | +0.895 | +0.631 | +0.553 | 4.142 | 3.984 |
| XL | 330 | +0.682 | +0.791 | +0.885 | +0.878 | +0.594 | 4.594 | 5.480 |
| XM | 435 | +0.750 | +0.736 | +0.723 | +0.810 | +0.695 | 4.532 | 5.067 |
| IBH | 571 | +0.624 | +0.642 | +0.645 | +0.693 | +0.412 | 3.155 | 3.062 |
| IBL | 545 | +0.892 | +0.942 | +0.912 | +0.850 | +0.747 | 3.794 | 4.361 |
| IBM | 661 | +0.802 | +0.868 | +0.887 | +0.839 | +0.770 | 3.484 | 3.815 |
| VWAP | 1,150 | +0.557 | +0.409 | +0.433 | +0.515 | +0.621 | 4.877 | 4.852 |
| ROUND | 2,623 | +1.386 | +1.376 | +1.349 | **+1.389** | **+1.283** | 4.413 | 5.145 |

**Every family clears the 0.287 ATR economic reference, and so does every
control.** Pooled: genuine +0.887 against shifted +0.813. Conditional on a
reclaim, price rotates roughly nine tenths of a one-minute ATR over the next
thirty minutes — **whether the level is real or arbitrary.** That is a property
of conditioning on a reversal, not a property of reference levels. It is the
single most seductive table in the study and it means nothing.

**MAE exceeds MFE for 13 of 15 families** (pooled 4.79 against 4.30). After an
interaction, price travels *further against* the rejection thesis than with it.

---

## 6. First versus repeated interactions — and the control that settles it

All fifteen families pass "first beats repeated". A condition that everything
passes is a structural artefact until something arbitrary fails it, so the same
comparison was run on the shifted controls.

| family | n first | reclaim | n repeat | reclaim | first − repeat | **same on the CONTROL** |
|---|---|---|---|---|---|---|
| PDH | 584 | 74.7 | 3,401 | 74.7 | +0.0 | +0.8 |
| PDL | 506 | 74.5 | 3,086 | 74.2 | +0.3 | −1.1 |
| PDC | 595 | 77.6 | 3,981 | 73.8 | +3.8 | +1.8 |
| PDVWAP | 677 | 79.9 | 3,945 | 75.0 | +5.0 | +4.8 |
| VAH | 653 | 77.9 | 3,967 | 74.1 | +3.9 | +3.2 |
| VAL | 576 | 76.9 | 3,690 | 74.3 | +2.7 | +2.8 |
| POC | 513 | 78.2 | 3,365 | 74.4 | +3.8 | +3.9 |
| XH | 591 | 74.6 | 3,506 | 73.3 | +1.3 | +1.8 |
| XL | 423 | 78.0 | 2,565 | 75.2 | +2.8 | +2.9 |
| XM | 581 | 74.9 | 3,689 | 74.6 | +0.2 | +2.3 |
| IBH | 784 | 72.8 | 4,386 | 72.2 | +0.6 | −0.5 |
| IBL | 712 | 76.5 | 4,075 | 74.4 | +2.2 | +3.1 |
| IBM | 866 | 76.3 | 5,115 | 74.2 | +2.1 | +2.7 |
| VWAP | 1,403 | 82.0 | 14,366 | 75.1 | +6.9 | +8.6 |
| ROUND | 3,429 | 76.5 | 19,586 | 74.2 | +2.3 | +1.8 |

Pooled: **genuine +2.68 points, shifted controls +2.68 points.** Identical to two
decimals on 12,893 and 43,903 observations.

**"The first test of a level works better than later tests" is true of any price
whatsoever.** It is not level decay; it is a property of the first touch of the
day. It survives excluding the last 60 bars of the session (77.0 vs 74.7), so it
is not a window-truncation artefact either — it is simply what first touches do.

This control was added **after** observing that all fifteen families passed, and
it was added because a 15-of-15 pass demands one. It cannot change the verdict:
condition 1 already fails for every family.

---

## 7. By calendar year — advantage over the pooled shifted control

| family | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | years + |
|---|---|---|---|---|---|---|---|
| PDH | +2.6 | +3.2 | −5.5 | −0.9 | +2.2 | −3.4 | 3 |
| PDL | +1.2 | +0.3 | +2.5 | +8.4 | −3.8 | −2.1 | 4 |
| PDC | +3.3 | +0.4 | −3.2 | −3.7 | +5.2 | +5.5 | 4 |
| PDVWAP | +3.8 | −0.5 | −0.8 | +6.3 | −3.2 | −5.2 | 2 |
| VAH | +3.8 | −3.1 | +5.6 | −1.3 | +0.3 | −5.7 | 3 |
| VAL | +3.6 | +0.2 | −1.2 | −7.7 | −0.5 | −2.3 | 2 |
| POC | +1.6 | +0.8 | +2.2 | −5.0 | +2.8 | −5.4 | 4 |
| XH | −3.9 | −1.8 | −3.4 | +2.8 | +5.8 | +1.5 | 3 |
| XL | −1.3 | −0.8 | −1.6 | +5.0 | −3.3 | — | 1 |
| XM | −2.2 | −3.5 | −3.6 | +3.0 | −3.5 | +0.4 | 2 |
| IBH | −7.2 | −0.1 | +5.0 | +6.9 | +3.3 | +0.8 | 4 |
| IBL | −2.5 | +1.4 | −4.1 | +0.9 | +1.7 | +2.6 | 4 |
| IBM | −3.3 | −1.7 | +0.4 | +3.1 | +0.6 | +3.3 | 4 |
| VWAP | −4.2 | +1.5 | −6.0 | −4.8 | +1.5 | −1.0 | 2 |
| ROUND | −0.6 | +0.2 | −0.5 | −0.7 | −0.1 | +0.9 | 2 |

Signs alternate with no pattern. Six families reach four positive years, which
is what a fair coin does across six years about a third of the time.

---

## 8. Matched geometric strata — binding

Direct standardisation of the shifted control onto the genuine mix of
(range-location × time-of-day × volatility) terciles, so composition cannot
carry a result.

| family | pooled advantage | **standardised** | coverage | survives |
|---|---|---|---|---|
| PDH | −0.4 | −0.8 | 99% | no |
| PDL | +1.3 | **−0.8** | 100% | **no — sign flips** |
| PDC | +0.9 | +1.1 | 100% | yes |
| PDVWAP | +0.5 | +0.0 | 98% | yes |
| VAH | +0.5 | +0.1 | 99% | yes |
| VAL | −1.2 | +0.2 | 100% | no |
| POC | −0.3 | −0.1 | 99% | no |
| XH | −0.6 | −0.3 | 99% | no |
| XL | −0.9 | −0.5 | 99% | no |
| XM | −2.4 | −4.2 | 100% | no |
| IBH | +1.5 | +1.2 | 100% | yes |
| IBL | −0.2 | −0.4 | 100% | no |
| IBM | +0.2 | **−1.8** | 100% | **no — sign flips** |
| VWAP | −2.2 | −0.8 | 100% | no |
| ROUND | −0.1 | −0.5 | 100% | no |

Coverage is 98–100% everywhere, so the standardisation is not throwing the
sample away. **Two families' advantages reverse sign under standardisation** —
prior-day low and IB mid were both composition effects. The four that survive do
so at +0.0 to +1.2 points, well inside noise.

---

## 9. Confluence — descriptive only

| bucket | n | reclaim-10 | rot 30 | MFE | MAE |
|---|---|---|---|---|---|
| isolated | 12,893 | **77.0%** | +0.887 | 4.299 | 4.792 |
| two-level cluster | 765 | **74.8%** | +0.968 | 4.011 | 4.206 |
| three-or-more cluster | 75 | **70.7%** | −0.132 | 4.117 | 4.633 |

**Confluence is monotonically worse, not better.** More levels stacked in one
zone gives a *lower* reclaim rate, and the three-or-more bucket's rotation is
negative.

No member family passed alone, so the first of the three confluence
preconditions fails and **nothing is claimed from this table**. It is reported
because it was pre-registered, and it points the wrong way for the folk belief
in any case.

---

## 10. Reconciliation with the 1,414-session QQQ null

| family | earlier study, reaction at 30 min | **now, reclaim-10** | best vs shifted | vs random | adds information |
|---|---|---|---|---|---|
| PDH | 44.8% | 74.7% | +0.6 | −1.6 | **no** |
| PDL | 48.1% | 74.5% | +1.9 | −0.3 | **no** |
| VAH | 47.2% | 77.9% | +2.3 | −0.7 | marginal |
| VAL | 51.5% | 76.9% | +0.9 | −2.1 | **no** |
| POC | 49.0% | 78.2% | +2.6 | −0.5 | **no** |

**The raw rates are not comparable and must not be read as a contradiction.**
The earlier study asked "which side of the level is price on after 30 minutes?",
null 50%. This study asks "did price penetrate a 0.14-ATR zone and close back
through it within 10 minutes?", whose base rate is about 77% for *any* price.
A 74.7% here and a 44.8% there are answers to different questions.

Which of the five declared differences accounts for the change?

| candidate | verdict |
|---|---|
| **the reclaim definition** | **This is the whole of it.** A narrow zone plus a "close back through" test has a ~77% base rate by construction. The level of the number comes from the definition, not from the levels. |
| rotation measured after reclaim | No. Rotation after reclaim is +0.89 ATR genuine against +0.81 control — the conditioning produces it, not the level. |
| first-interaction filtering | No. §6 shows first-minus-repeated is +2.68 for genuine and +2.68 for arbitrary shifted prices. |
| geometry matching | No. It removes advantage rather than creating it: two families reverse sign under standardisation. |
| shifted-level controls | **They are the addition that matters, and they confirm the earlier null rather than overturning it.** The earlier study had a 50% theoretical null; this one has an empirical 77.23% control, and the genuine arm lands 0.25 points *below* it. |

**The two studies agree.** One measured levels against a theoretical coin and
found a coin; this one measures levels against an empirical arbitrary price and
finds the arbitrary price. A smaller or differently labelled sample has not
overridden 1,414 sessions of null, and nothing here asks it to.

---

## 11. Selection rule — all eight conditions

| family | 1 shifted | 2 random | 3 geometry | 4 both sides | 5 first>repeat | 6 ≥4 years | 7 ≥12/mo | 8 adds info | |
|---|---|---|---|---|---|---|---|---|---|
| PDH | · | · | · | · | Y | · | · | · | fail |
| PDL | · | · | · | Y | Y | Y | · | · | fail |
| PDC | · | · | Y | Y | Y | Y | Y | Y | **fail** |
| PDVWAP | · | · | Y | · | Y | · | · | Y | fail |
| VAH | · | · | Y | · | Y | · | · | · | fail |
| VAL | · | · | · | · | Y | · | · | · | fail |
| POC | · | · | · | · | Y | Y | · | · | fail |
| XH | · | · | · | · | Y | · | · | Y | fail |
| XL | · | · | · | · | Y | · | · | Y | fail |
| XM | · | · | · | · | Y | · | · | Y | fail |
| IBH | · | · | Y | Y | Y | Y | Y | Y | **fail** |
| IBL | · | · | · | · | Y | Y | · | Y | fail |
| IBM | · | · | · | · | Y | Y | Y | Y | fail |
| VWAP | · | Y* | · | · | Y | · | Y | Y | fail |
| ROUND | · | · | · | · | Y | · | Y | Y | fail |

\* on 3% control coverage and a median pool of two. Not treated as a pass in any
sense that matters.

**Condition 1 — beat all four shifted controls at α = 0.00167 — fails for every
single family.** Condition 2 fails for every family on any honest reading.
Conditions 3 and 4 are satisfied by four and three families respectively, at
magnitudes inside noise. Condition 5 is passed by all fifteen and is an artefact.

The two closest families, prior RTH close and IB high, pass six of eight and
fail the two that carry the entire question.

**FAMILIES PASSING ALL EIGHT CONDITIONS: NONE.**

The frozen commercial score is not applied, because it ranks qualifiers and
there are none. Ranking non-qualifiers would be selecting on the largest
isolated result, which the rule forbids.

---

## 12. Limitations, recorded

* **The frozen zone is about one seventh of a single QQQ one-minute bar's
  range.** Penetration therefore occurs on **96.5–99.2%** of interactions, so
  "penetrated and reclaimed" is effectively "closed back through within ten
  minutes", with a ~77% base rate. The zone was derived faithfully from the NQ
  geometry and was not changed. The comparison remains valid because genuine and
  control are measured identically — but the outcome has less headroom than the
  design anticipated, and that should be said.
* **One-minute bars cannot see sub-minute path.** The bar-resolution gate
  measured 23.5% of tick-level activity opening and closing inside one minute.
  The 1-minute reclaim column is reported as a diagnostic and is not a gate.
* **Matched random control coverage is 65% overall and 0% / 3% for IB mid and
  session VWAP.** The control uses each candidate's first interaction of the
  session and cannot match a late interaction at a mid-range price.
* **Extended-hours families are not overnight families.** QQQ has a 20:00–04:00
  hole. They are labelled extended-hours throughout.

---

# VERDICT: NO LEVEL FAMILY QUALIFIES — CLOSE RP-007

Fifteen families, 1,419 sessions, 13,733 first interactions, four shifted
controls per level and 200 matched-random repetitions. **Genuine reference
levels reclaim 76.98% of the time; prices shifted arbitrarily away from them
reclaim 77.23%.**

Mechanically defined pre-existing reference levels **do not produce more
rejection and subsequent rotation than nearby arbitrary prices** on QQQ over
five and a half years.

**Stage 1A2 is not requested and NQ outcomes are not opened.** Under the
pre-registered rule, if no family qualifies RP-007 closes without using NQ.

**Stage 1B is not authorised and no absorption threshold is defined.** The
sequence required footprint absorption to be tested only after the level itself
proved non-arbitrary. It did not.

---

## What this does and does not close

It closes the **price-only** claim: that a level's identity, by itself, changes
what price does on contact. That claim is now tested on QQQ against shifted and
matched-random controls, with geometry standardised, and it is a measured zero
to ±1.4 points.

It does not close the claim that levels are useful **descriptively** — they
remain real prices where real business happened, and the confluence map may go
on using them as such. It says only that their identity does not forecast the
next thirty minutes.

**The sixteen NQ sessions being re-recorded remain unspent.** They were preserved
for optionality and no RP-007 stage consumed them. The nine sealed sessions
remain sealed and unread. 2016–2020 remains spent and untouched.
