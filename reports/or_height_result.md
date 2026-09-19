# Opening range height: 0 of 4, and the gradient was never there

Rule, grid, threshold and rejection criteria pre-registered at `9307834` before
this ran. Nothing was changed. Sealed NQ days were not read; this screen never
opens the NQ tape.

---

## 1. Counts, before any performance number

### Run A — 1-minute, 2021–2026, in sample

| | |
|---|---|
| sessions | **1,418** — 2021-01-04 to 2026-08-31 |
| classified (20 prior sessions available) | 1,398 |
| **WIDE** (ratio ≥ 1.00) | **588** at OR15, **590** at OR30 |
| **NARROW** (ratio < 1.00) | **810** at OR15, **808** at OR30 |
| median ratio | 0.928 |

| variant | trades | sessions | tr/sess | med risk | flat% | ambiguous | **lookahead** |
|---|---|---|---|---|---|---|---|
| OR15 R3.0 | 2,656 | 1,418 | 1.87 | 10.6 bps | 0.5% | 0.0% | **0** |
| OR15 R4.0 | 2,637 | 1,418 | 1.86 | 10.5 bps | 0.9% | 0.0% | **0** |
| OR30 R3.0 | 2,611 | 1,398 | 1.87 | 9.2 bps | 0.5% | 0.0% | **0** |
| OR30 R4.0 | 2,590 | 1,398 | 1.85 | 9.1 bps | 0.6% | 0.0% | **0** |

**The median ratio is 0.928, not 1.000** — the distribution is right-skewed, so a
threshold at the mean puts 42% of sessions in the wide arm, not half. That was
foreseeable and is not a problem: both arms carry 780–1,510 trades.

### Standing instrumentation

- **Entry lookahead: 0 entries** in all three runs, all four variants. The
  trigger is fixed by the opening-range window, which closes before any bar that
  can trigger it, so this is structural — but it is now counted rather than
  assumed.
- **Ambiguous bars: 0.0%** on 1-minute, 0.2–0.3% on 5-minute. At a 1.0 ATR stop
  with a 3R or 4R target the stop-to-target span is four to five times the bar,
  as the calibration gate predicted.
- **Entry bar skipped** for the exit search throughout.

---

## 2. The slippage audit

### Run A, 1-minute, wide arm

| variant | gapped | mean slip | **honest exp R** | **naive exp R** | phantom |
|---|---|---|---|---|---|
| OR15 R3.0 | 37.5% | +0.041 | +0.021 | +0.086 | +0.064 |
| OR15 R4.0 | 33.6% | +0.027 | +0.015 | +0.061 | +0.047 |
| OR30 R3.0 | 36.8% | +0.042 | −0.103 | −0.083 | +0.020 |
| OR30 R4.0 | 32.8% | +0.031 | −0.134 | −0.119 | +0.015 |

### Runs B and C, 5-minute — the largest phantom yet measured

| run | variant | gapped | mean slip | **honest** | **naive** | phantom |
|---|---|---|---|---|---|---|
| B | OR15 R3.0 | 57.4% | +0.246 | −0.040 | **+0.783** | **+0.823** |
| B | OR15 R4.0 | 56.2% | +0.236 | −0.031 | **+0.773** | +0.805 |
| C | OR15 R3.0 | 54.0% | +0.246 | −0.076 | **+0.997** | **+1.073** |
| C | OR15 R4.0 | 51.8% | +0.238 | −0.044 | **+1.036** | **+1.080** |
| C | OR30 R4.0 | 51.4% | +0.150 | −0.025 | +0.482 | +0.507 |

**On five-minute bars, more than half of all entries gap past the trigger and the
naive fill assumption reports a full R of expectancy where the honest one reports
roughly zero.** A backtest of this rule on five-minute data with a trigger-price
fill would show +0.78R to +1.04R per trade — an outstanding strategy, entirely
imaginary. The phantom scales with bar width exactly as the previous two families
predicted it would.

---

## 3. The gradient — the expectancy difference the threshold produces

| variant | all | **WIDE** | **NARROW** | **wide − narrow** | **Welch t** | wide n | narrow n |
|---|---|---|---|---|---|---|---|
| OR15 R3.0 | −0.026 | **+0.021** | −0.061 | **+0.083** | **+1.21** | 1,108 | 1,511 |
| OR15 R4.0 | −0.003 | +0.015 | −0.015 | +0.030 | +0.37 | 1,097 | 1,503 |
| OR30 R3.0 | −0.095 | −0.103 | −0.089 | **−0.015** | −0.19 | 1,076 | 1,501 |
| OR30 R4.0 | −0.110 | −0.134 | −0.093 | **−0.041** | −0.49 | 1,067 | 1,489 |

**Two of the four have the wrong sign.** The largest is +0.083R at t +1.21,
which on 2,619 trades is not a result. **Isolated as its own hypothesis, in the
region where it was supposed to live, the gradient is not measurable.**

### Gradient by year

| variant | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | holds |
|---|---|---|---|---|---|---|---|
| OR15 R3.0 | +0.250 | −0.133 | +0.217 | +0.152 | −0.102 | +0.173 | 4/6 |
| OR15 R4.0 | +0.203 | −0.105 | +0.067 | +0.206 | −0.237 | +0.105 | 4/6 |
| OR30 R3.0 | +0.149 | −0.141 | −0.147 | −0.001 | −0.118 | +0.238 | **2/6** |
| OR30 R4.0 | +0.112 | −0.248 | −0.042 | −0.046 | −0.214 | +0.274 | **2/6** |

The two OR15 variants clear the new criterion 6 at 4/6 — but they are 4/6 of a
quantity whose pooled t is +1.21 and +0.37. A sign holding in four years out of
six is what a coin does 34% of the time.

---

## 4. The verdict

### In sample, run A

| variant | why rejected |
|---|---|
| OR15 R3.0 | PF 1.03; top-1% dependent; 3/6 positive years; **t +0.41** |
| OR15 R4.0 | PF 1.02; top-1% dependent; 2/6 positive years; **t +0.24** |
| OR30 R3.0 | exp −0.103; PF 0.87; top-1% dependent; 1/6 years; gradient 2/6; t −2.07 |
| OR30 R4.0 | exp −0.134; PF 0.85; top-1% dependent; 1/6 years; gradient 2/6; t −2.26 |

**Survivors: 0 of 4.**

The two OR15 variants have positive expectancy (+0.021R, +0.015R) and fail on
everything else: profit factor of 1.02–1.03 against a 1.15 bar, total P&L that
goes negative once the best 1% of trades are removed, and session t of +0.41 and
+0.24 against a bar of 3.0.

---

## 5. The bridge check failed, and run C is withdrawn

| variant | A gradient (1-min) | B gradient (5-min, same years) | A risk | B risk |
|---|---|---|---|---|
| OR15 R3.0 | **+0.083** | **−0.019** | 12.5 bps | 14.9 bps |
| OR15 R4.0 | **+0.030** | **−0.049** | 12.3 bps | 14.6 bps |
| OR30 R3.0 | **−0.015** | **+0.067** | 10.7 bps | 12.9 bps |
| OR30 R4.0 | **−0.041** | **+0.000** | 10.6 bps | 12.6 bps |

**The signs disagree on all four variants.** The pre-registration said: *"If that
does not reproduce the one-minute result, the five-minute grid is not measuring
the same rule and the 2016–2020 run is not interpretable — I will say so and the
out-of-sample evidence will be withdrawn rather than explained away."*

**Run C is withdrawn as evidence.** Its numbers are below for completeness and
carry no weight.

### Two honest reasons it failed, and one of them is my fault

**1. The bridge test I wrote was too weak to be informative.** I specified sign
agreement between the two grids without anticipating that both quantities would
sit within noise of zero. Comparing the signs of two measurements that are each
indistinguishable from zero is a test with roughly a coin's chance of failing by
construction. That is a badly designed check and I am recording it as such
rather than treating its failure as a finding about the data.

**2. The five-minute grid genuinely is not the same rule, and my scale constant
undershot.** Realised risk came out **19% wider** than intended (14.9 vs 12.5
bps), because the conversion factor was measured on mean bar range across the
whole session while entries cluster in the first hour, where five-minute bars are
relatively larger. And flat-time exits are **13 times more common** (12.3% vs
0.5%), because waiting for a five-minute bar to close delays entry enough to
change which trades reach their target before the clock. Both are real
differences in the rule, not in the measurement.

### Run C's numbers, withdrawn

1,256 sessions, 2016–2020. Gradients **+0.033, +0.058, +0.105, +0.137**, Welch t
**+0.47, +0.68, +1.39, +1.53**. All four positive, none significant, and the
verdict there is **also 0 of 4** — every variant fails on expectancy, profit
factor and top-1% dependence.

**The withdrawal costs nothing.** Run C would not have rescued the hypothesis
even if it counted.

---

## 6. Where the original observation actually came from

The ORB screen's regime table showed narrow underperforming wide in 13 of 16
variants and I called it "the one consistent gradient in the whole screen". That
was an over-read and here is the correction.

### Diagnostic — the same split applied to all 16 ORB cells

| variant | wide | narrow | gradient | Welch t |
|---|---|---|---|---|
| OR30 **SATR0.5** R3.0 | −0.108 | −0.229 | **+0.121** | **+1.72** |
| OR30 **SATR0.5** R4.0 | −0.096 | −0.197 | **+0.101** | +1.22 |
| OR30 **SATR0.5** R2.0 | −0.186 | −0.278 | +0.092 | +1.61 |
| OR30 **SATR0.5** R1.0 | −0.319 | −0.389 | +0.070 | +1.66 |
| OR15 SATR1.0 R3.0 | +0.026 | −0.052 | +0.078 | +1.14 |
| OR15 SATR1.0 R4.0 | +0.018 | +0.004 | +0.013 | +0.17 |
| OR30 SATR1.0 R3.0 | −0.092 | −0.070 | **−0.022** | −0.31 |
| OR30 SATR1.0 R4.0 | −0.122 | −0.073 | **−0.049** | −0.59 |

**Fourteen of sixteen signs are positive and the largest t anywhere is +1.72.**
The "13 of 16" was a count of signs, not of effects. Sixteen heavily overlapping
cells sharing sessions and trades will agree on the sign of a small common noise
term; that is what counting them measured.

**And the gradient is concentrated at `STOP_ATR` 0.5** — the setting dropped from
this grid because it was worse at every target, which argued against a real
effect. The two facts belong together: the gradient was largest exactly where the
underlying rule was least credible.

### Was my threshold choice the reason it looks weak? No.

I picked 1.00 deliberately rather than 0.8/1.2, the bucket edges where the
gradient was first seen, and a median split has less contrast than a tail
comparison. So I checked the tails at the surplus stop:

| variant | wide > 1.2 | narrow < 0.8 | gradient | Welch t |
|---|---|---|---|---|
| OR30 SATR0.5 R3.0 | −0.110 | −0.284 | **+0.174** | **+2.00** |
| OR30 SATR0.5 R4.0 | −0.075 | −0.251 | **+0.177** | +1.72 |
| OR15 **SATR1.0** R3.0 | +0.010 | −0.080 | +0.090 | +1.04 |
| OR15 **SATR1.0** R4.0 | −0.012 | −0.045 | +0.032 | +0.32 |
| OR30 **SATR1.0** R3.0 | −0.094 | −0.100 | +0.006 | +0.11 |
| OR30 **SATR1.0** R4.0 | −0.099 | −0.119 | +0.020 | +0.23 |

**At the wide stop, the tail comparison is as weak as the median split** — t of
+0.11 to +1.04. The threshold choice was not the problem. The effect is not in
this region at either cut.

---

## 7. Regime breakdown, run A, wide arm

### By year, mean R

| variant | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|
| OR15 R3.0 | +0.130 | −0.113 | +0.070 | +0.124 | −0.035 | −0.026 |
| OR15 R4.0 | +0.144 | −0.060 | −0.018 | +0.192 | −0.071 | −0.099 |
| OR30 R3.0 | −0.074 | +0.031 | −0.146 | −0.054 | **−0.333** | −0.031 |
| OR30 R4.0 | −0.100 | −0.055 | −0.153 | −0.096 | **−0.381** | +0.039 |

Both OR15 variants are negative in the two most recent years.

### By time of day, mean R (count)

| variant | 0–60 | 60–120 | 120–180 | 180+ |
|---|---|---|---|---|
| OR15 R3.0 | +0.012 (929) | +0.217 (126) | −0.345 (32) | −0.175 (21) |
| OR15 R4.0 | +0.004 (918) | +0.204 (124) | −0.269 (30) | −0.211 (25) |
| OR30 R3.0 | −0.098 (730) | −0.048 (250) | −0.170 (70) | −0.599 (26) |
| OR30 R4.0 | −0.098 (725) | −0.127 (239) | −0.335 (73) | −0.567 (30) |

Unchanged from the ORB screen: breakouts are an opening-hour event. 84% of wide-arm
trades fire in the first sixty minutes and the late buckets hold 21 to 73 trades.
The +0.217R in the 60–120 column rests on 126 trades and is not separable from
noise; the deeply negative late cells rest on fewer still.

### By OR height bucket

That *is* the wide/narrow split, reported in section 3.

---

## 8. What this means, stated plainly

**Index breakout structures are exhausted at these constraints.** Three screens
on 1,418 QQQ sessions — pullback continuation, opening range breakout with a VWAP
filter, and opening range height as its own hypothesis — have returned 0 of 16,
0 of 16 and 0 of 4. The one piece of structure that survived the second screen
dissolved when it was isolated and tested on its own terms, and the diagnostic
shows it was a sign count over correlated cells rather than an effect.

**The next move is a different instrument or a different session, not another
variant of this one.** I am not proposing an additional filter and will not.

### Ledger

| family | sample | outcome |
|---|---|---|
| order flow | 20 NQ sessions | closed |
| pullback grids 1 and 2 | 20 NQ sessions | closed, coin flip |
| pullback, QQQ screen | 1,418 QQQ sessions, 16 variants | closed, 0 of 16 |
| ORB + VWAP, QQQ screen | 1,418 QQQ sessions, 16 variants | closed, 0 of 16 |
| **OR height, promoted** | **1,418 QQQ + 1,256 held out, 4 variants** | **closed, 0 of 4** |

Two of the six-variant budget were left unspent and stay unspent. Sealed NQ days
have still never been read.

### What this does not rule out

Unchanged and still true: QQQ's opening hour follows a closed book, NQ's follows a
live overnight auction, and 84% of these trades fire in that hour. For opening
range structures specifically, that is the sharpest version of the caveat this
project has carried. It is a reason the NQ answer could differ — not a reason to
run a seventeenth variant here.
