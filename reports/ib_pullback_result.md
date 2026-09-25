# IB ending zone + pullback rejection: one variant clears every stated bar, and it is still not a candidate

Pre-registered at `417a012`. 1,396 QQQ sessions, 2021-01-04 → 2026-08-31.
**2016–2020 not opened. Sealed NQ dates not read.**

The boundary-break rate is not used as evidence anywhere. Only the trade taken
after the pullback and rejection is evaluated.

---

## 1. The funnel

**1,396 sessions → 762 qualify** at EZ < 25% with resolvable extremes (54.6%).

| zone | rej | exit | qual | reached zone | traded | /mo | risk NQ | cost % |
|---|---|---|---|---|---|---|---|---|
| C retest | R1 | 1.5R | 762 | 627 | 366 | 5.5 | 26.1 | 4.37 |
| C retest | R2 | 1.5R | 762 | 628 | 379 | 5.7 | 24.7 | 4.52 |
| A vwap | R1 | 1.5R | 762 | 584 | 317 | 4.7 | 19.3 | 5.85 |
| A vwap | R2 | 1.5R | 762 | 553 | 284 | 4.2 | 23.2 | 4.94 |
| B mid | R1 | 1.5R | 762 | **356** | 186 | 2.8 | 19.8 | 5.64 |
| **B mid** | **R2** | **1.5R** | 762 | **330** | **175** | **2.6** | 23.6 | 4.55 |

**Zone C with the IB-boundary exit produces zero trades in both rejections.**
That is structural, not a bug: zone C *is* the boundary, so the boundary target
is never 0.75R away. Recorded rather than silently dropped.

**Cost/risk is 4.4–5.9%** — five times worse than the IB family's 0.77–1.16%.
The 10%-of-risk cost rule bound in every year exactly as pre-registered; the
8-point floor never bound.

---

## 2. Trading results — the desk table

| zone | rej | exit | n | win% | avgW | avgL | **exp R** | PF | ddR | strk | yrs | −best5 | **std conc** | +50% c |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C retest | R2 | 1.5R | 379 | 36.4 | 1.43 | −1.06 | **−0.155** | 0.77 | 70.9 | 14 | 2/6 | −0.177 | −0.336 | −0.179 |
| C retest | R1 | 1.5R | 366 | 38.0 | 1.43 | −1.04 | −0.106 | 0.84 | 47.2 | 12 | 2/6 | −0.127 | −0.283 | −0.129 |
| A vwap | R1 | 1.5R | 317 | 42.6 | 1.44 | −1.07 | +0.002 | 1.00 | 28.3 | 10 | 2/6 | −0.021 | −0.162 | −0.027 |
| A vwap | R2 | 2R | 284 | 38.0 | 1.94 | −1.05 | +0.085 | 1.13 | 17.2 | 11 | 3/6 | +0.051 | −0.129 | +0.059 |
| B mid | R1 | 2R | 186 | 39.2 | 1.93 | −1.08 | +0.104 | 1.16 | 13.9 | 10 | 5/6 | +0.052 | −0.107 | +0.075 |
| B mid | R2 | IBbound | 160 | 41.2 | 1.85 | −1.05 | +0.145 | 1.23 | 8.9 | 5 | 5/6 | −0.001 | −0.224 | +0.120 |
| **B mid** | **R2** | **1.5R** | **175** | **48.0** | **1.45** | **−1.05** | **+0.150** | **1.27** | **8.4** | **5** | **5/6** | **+0.111** | **−0.002** | **+0.125** |

**Zone C is negative in all four of its variants.** The breakout retest is the
worst construction in the family, and it is the one with the most trades.

---

## 3. The best variant passes all ten stated criteria

**B mid / R2 / 1.5R:**

| # | criterion | result | |
|---|---|---|---|
| 1 | ≥150 trades | 175 | ✓ |
| 2 | positive after costs | +0.150 R | ✓ |
| 3 | PF ≥ 1.15 | 1.27 | ✓ |
| 4 | ≥4 of 6 years | 5/6 | ✓ |
| 5 | positive after removing best 5 | +0.111 | ✓ |
| 6 | positive at +50% costs | +0.125 | ✓ |
| 7 | drawdown vs average trade | 8.4 R ÷ 0.150 = 56 trades to recover | acceptable |
| 8 | beats shifted-zone control | +0.150 vs **+0.023** | ✓ |
| 9 | rejection beats touch-only | +0.150 vs **−0.025** | ✓ |
| 10 | EZ beats no-EZ control | +0.150 vs **−0.036** | ✓ |

Long +0.152 (n=102) · short +0.147 (n=73) — **balanced, not one-sided.**
Exit mix 84 target / 91 stop / 0 close. Ambiguous bars **0.0%**. Naive-fill
expectancy +0.149 against honest +0.150 — **the fill model is not doing the
work.**

### And the controls all point the right way

| control | best variant | reading |
|---|---|---|
| C1 no ending zone | **−0.036** (n=431) vs +0.150 | the 0–25% condition is load-bearing |
| C2 touch without rejection | **−0.025** (n=52) vs +0.150 | rejection is load-bearing |
| C3 zone shifted 0.25 IB | **+0.023** (n=102) vs +0.150 | the midpoint is not an arbitrary price |
| C4 opposite bias | **−0.082** (n=88) | the direction rule is load-bearing |

**Every control moved the way the hypothesis predicts.** That is the first time
in this project a family has done that.

---

## 4. Why it is still not a candidate

### 4.1 The t-statistic does not survive the search

| | |
|---|---|
| best variant t | **+1.58** |
| Bonferroni threshold over 18 variants | **2.99** |
| **P(max of 18 independent \|t\| exceeds 1.58) under the null** | **65.3%** |

**A best-of-18 t of 1.58 is exceeded by chance about two times in three.** The
expected maximum from 18 independent draws is ≈2.1 — *higher than what was
found*. Not one of the 18 variants reaches even a single-test p < 0.05.

The pre-registered MDE was ±0.144 R at n = 150 and sd 0.9. The observed
+0.150 sits essentially **on** the MDE, not above it.

### 4.2 The standing concentration rule kills it at the line

| | |
|---|---|
| after removing the best 5 (as asked) | **+0.111** |
| after `max(10, ⌈0.10n⌉)` = 18 trades (**the standing rule**) | **−0.002** |

Flagged in §6 of the pre-registration before running. **This is the split
verdict that was declared in advance, not a rule invented after seeing the
number.** The top 5 trades carry 28% of total R across 175 trades — not the
164% pathology of the frozen IB candidate, but not robust either.

### 4.3 2026 is negative and it is the newest data

| year | n | mean R |
|---|---|---|
| 2021 | 36 | +0.202 |
| 2022 | 33 | +0.018 |
| 2023 | 44 | +0.144 |
| 2024 | 32 | +0.274 |
| 2025 | 19 | +0.389 |
| **2026** | **11** | **−0.385** |

5 of 6 years positive satisfies the rule. But the trade count **falls from 44 to
11** and the newest year is the worst. On 11 trades that is not a trend, but it
is the opposite of reassuring.

### 4.4 The controls are underpowered

C2 rests on **52 trades** and C3 on **102**. Both point the right way; neither
separates from noise. A control that cannot reject cannot confirm.

---

## 5. Verdict

# INTERESTING BUT UNRESOLVED

Positive economics, insufficient sample. **Not "tradeable candidate"** — the
statistical evidence is indistinguishable from the 18-variant search that
produced it, and the standing concentration rule returns −0.002.

**Not "closed" either**, and that distinction is real: this is the only family
in the project where **all four mechanism controls moved in the predicted
direction**. The prior families failed their controls outright — the
compression family's controls *reversed*. This one did not.

---

## 6. Recommendation on next steps

**Freeze `B_mid / R2 / 1.5R` exactly as specified. Do not open 2016–2020.**

| | |
|---|---|
| **related-instrument testing** | **justified, and it should come first** |
| **holdout** | **not justified at t = 1.58** |

Reasoning:

1. **The holdout is a single-use asset and t = 1.58 does not earn it.** At
   n = 175 the effect sits on its own MDE. Spending 1,259 sessions to resolve
   something this marginal wastes the only clean out-of-sample data left.
2. **Related instruments cost nothing.** SPY, IWM, IJH and EFA 1-minute data
   are already in the repo from the IB family's check, and the IB midpoint is
   instrument-agnostic.
3. **The precedent is direct.** The IB 1R candidate looked stronger than this
   (t = +2.23) and the related-instrument check put the pooled non-QQQ estimate
   at +0.027 with an interval spanning zero — which is what closed it. This
   family should face the same test at the same stage.
4. **The concentration split needs resolving.** −0.002 on the standing rule is
   not a pass or a fail; more independent trades is the only thing that moves it.

**Declared in advance for that extension:** pooled non-QQQ expectancy with
clustered errors by date, per-instrument breakdown, the same four controls, and
the standing concentration rule reported alongside the five-trade test. **If the
pooled non-QQQ estimate does not clear +0.10 with an interval excluding zero,
the family closes without the holdout being opened.**

---

Reproduce: `python3 scripts/orderflow/ib_pullback.py`.
Full output `reports/ib_pullback_output.txt`; per-variant
`reports/ib_pullback_variants.csv`.
