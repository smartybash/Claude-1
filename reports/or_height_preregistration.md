# Opening range height as the hypothesis — declared before running

Promoting a description to a claim. Committed before any result exists. Sealed
NQ days are not read at any point; this screen never touches the NQ tape.

---

## 1. The claim, stated so it can fail

**Breakouts from an opening range that is TALL relative to its own recent
history outperform breakouts from a SHORT one, at a 1.0 ATR stop and targets of
3R and 4R.**

Directional, and the direction matters: the folk version says a tight range
coils for a larger move, which predicts the opposite sign. A null result and a
reversed result are both failures, and both are reportable.

### Where it came from

The ORB screen's regime table, `reports/orb_vwap_result.md` section 5: narrow
ranges underperformed wide ones in **13 of 16 variants**, with 650–1,045 trades
in every bucket. That was the only consistent structure in a screen that
otherwise returned 0 of 16.

### Why the surplus region and nothing else

The ORB screen found breakouts beating the coin only at `STOP_ATR` 1.0:

| target | observed | coin | gap | gap needed |
|---|---|---|---|---|
| 3.0R | 26.9% | 25.0% | +1.9 | +1.5 |
| 4.0R | 22.4% | 20.0% | +2.4 | +1.3 |

The tighter stop was worse at every target — not how a real effect usually
behaves — so it is dropped. Targets below 3R carry a higher cost hurdle and
showed no surplus, so they are dropped. **What remains is the only corner where
there was anything to explain.**

---

## 2. The problem with this test, stated before it runs

**The gradient was found on these 1,418 sessions. Re-measuring it on the same
1,418 sessions cannot confirm it.** It can sharpen the estimate, check year
stability and check that it survives being made the primary object rather than a
by-product — but it is not independent evidence, and no amount of significance
from that run would make it so.

This is the single most important caveat on the whole exercise and it is why
section 3 exists.

## 3. The out-of-sample set, and what licenses it

`data/intraday_long/QQQ_5m.parquet` runs from **2016-01-04**, giving **1,259
sessions across 2016–2020 that this project has never read**, in any family, in
any run.

**Five-minute bars are usable for exactly this corner of the grid, and the NQ
calibration gate is what says so.** From `reports/bar_resolution_gate.md`: at
`STOP_ATR` 1.0 with targets of 2R and above, five-minute ambiguity was **0.0%**,
and Panel C — bar-generated trades re-decided on the tape — agreed **98.8%** of
the time with an expectancy difference of 0.003R. Five-minute bars failed only
at the tight stop with a 1R target, which is precisely the region this grid has
already dropped for independent reasons.

### The stop has to be rescaled, and the constant is declared now

A five-minute bar's range is larger than a one-minute bar's, so `1.0 × ATR`
means a different distance on each grid. Measured across the 1,421 overlapping
sessions:

```
mean 5-minute bar range / mean 1-minute bar range
    median 2.344    mean 2.348    p10 2.245    p90 2.454     (sqrt 5 = 2.236)
```

**`STOP_ATR` on the five-minute grid is therefore 1.0 / 2.344 = 0.4266**, so the
risk in basis points matches. This is a units conversion measured on the overlap
and fixed now; it is not fitted to any outcome, and the realised median risk in
bps is reported on both grids so the match can be checked rather than trusted.

### The bridge check, which can invalidate the out-of-sample run

The same four variants are run on **five-minute bars over 2021–2026**, the
overlap. If that does not reproduce the one-minute result, the five-minute grid
is not measuring the same rule and **the 2016–2020 run is not interpretable — I
will say so and the out-of-sample evidence will be withdrawn rather than
explained away.**

---

## 4. The rule

Identical to `reports/orb_vwap_preregistration.md` section 2 in every respect —
break of the opening range edge, stop anchored to the trigger level, target a
multiple of risk, entry bar skipped for the exit search, honest fill model, no
time expiry, flat at 18:30 UTC — **with the VWAP filter removed.**

The VWAP filter is dropped because it was measured and found decorative: it
vetoed up to 35.8% of signals and moved expectancy by +0.005R to +0.017R. Its
removal is not a change of hypothesis, it is the deletion of a component shown
to do nothing, and it keeps this grid a clean test of one variable.

### Constraints, unchanged

Maximum two trades per session; never concurrent; the second arms only after the
first closes; no discretionary reading; no averaging down; a hard stop fixed at
entry; flat by 18:30 UTC; realistic costs at 0.667 bps round turn; no
information used that was unavailable at the decision timestamp.

### The threshold definition

```
ratio(session) = OR_height(session) / mean(OR_height of the previous 20
                                           sessions at the same OR_MIN)
```

Trailing and shifted by one, so no session is classified using its own data or
anything after it. Sessions without 20 prior sessions are unclassified and
excluded from both arms.

**WIDE = ratio ≥ 1.00. NARROW = ratio < 1.00.**

**The threshold is 1.00 and that choice is deliberate.** It is the natural split
at the mean, requiring no search. It is explicitly **not** 0.8 or 1.2, which
were the bucket edges in the screen where the gradient was observed — picking
either of those would be fitting the threshold to the boundary that produced the
observation.

## 5. The grid: four variants, two of the budget left unspent

| parameter | values |
|---|---|
| `OR_MIN` | 15, 30 |
| `TGT_R` | 3.0, 4.0 |
| `STOP_ATR` | 1.0 — fixed |
| threshold | 1.00 — fixed, one value |

**4 variants.** The budget allows six. A second threshold value would make eight
and blow it; spending the spare two on anything else would be searching for a
result rather than testing a claim. **They stay unspent.**

## 6. The primary statistic is the gradient, not the level

The claim is comparative, so the headline number is the **difference**:

```
gradient = mean R (wide sessions) - mean R (narrow sessions)
```

WIDE and NARROW are disjoint sets of sessions, so this is a two-sample
comparison and the significance test is **Welch's t on session-level mean R**,
never across trades.

Reported per variant: expectancy on **all** sessions, on **wide**, on **narrow**,
the **difference**, and its t. **The expectancy difference the threshold
produces is the reported quantity — not the share of sessions it removes.** Veto
rate was the wrong quantity last time and is not repeated.

## 7. Rejection criteria, fixed now

Applied to the **wide-only** variant, which is the tradeable object:

1. Expectancy ≤ 0 in R, after costs.
2. Fewer than 15 sessions producing a trade.
3. Profit factor < 1.15.
4. Removing the top 1% of trades leaves total R ≤ 0.
5. Positive in fewer than 4 of the 6 calendar years.
6. **NEW — the gradient itself must hold.** `wide − narrow` must be positive in
   at least 4 of the 6 years. A single year carrying it is the failure mode that
   made `OR30 SATR0.5` look positive in 2022 alone, and this criterion exists to
   catch exactly that.

**And criterion 2 keeps its companion from the last two screens: t > 3 across
sessions.** It is not in the list above as written, and it is being kept anyway
— dropping it would make this screen easier than the two it follows, and the bar
does not move down mid-project. With 4 tests the Bonferroni figure is about
t > 2.5, which is below 3, so t > 3 governs.

## 8. Standing instrumentation, every run

- **entry bar skipped** for the exit search
- **honest fill model**, `max(trigger, bar open)`, with the unmodelled slippage
  stated per variant
- **the naive fill result printed beside the honest one**, so the size of the
  correction is visible — on the last grid seven of eight variants flipped sign
- **entry lookahead check**, reported as a count rather than asserted

## 9. Reporting

Trade counts and session counts before any performance number. Then, as standard
output: **by year**, **by OR height bucket**, **by time of day**.

## 10. What a failure here means, stated now

**If this fails, index breakout structures are exhausted at these constraints.**
The next move is a different instrument or a different session — not another
variant of this one, and not an additional filter to rescue it. I will not
propose one.

A survivor remains a candidate, not a finding, and would still need NQ tick
verification before it meant anything for the instrument actually traded.
