# Native-normalised transfer: the audit was right, and it still does not port

Run once under the definitions declared and committed at `146bcbc` **before**
this executed. The 0.10 ATR buffer fraction was not changed after seeing
results. 2021–2025. **2016–2020 not opened. Sealed NQ dates not read.**

---

## 1. Trading results

| | n | win% | avgW | avgL | **exp R** | PF | ddR | strk | yrs | longR | shortR | −best5 | +50% c |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **QQQ frozen** | 164 | 49.4 | 1.45 | −1.05 | **+0.185** | **1.35** | **8.4** | 5 | **5/5** | +0.201 | +0.163 | +0.145 | +0.161 |
| **QQQ native** | 233 | 46.4 | 1.44 | −1.02 | **+0.124** | **1.23** | **15.3** | 8 | 4/5 | +0.185 | +0.047 | +0.094 | +0.110 |
| SPY native | 251 | 38.2 | 1.44 | −1.02 | −0.082 | 0.87 | 38.9 | 10 | 1/5 | −0.045 | −0.122 | −0.114 | −0.098 |
| IWM native | 248 | 44.4 | 1.41 | −1.05 | +0.043 | 1.07 | 22.0 | 8 | 2/5 | +0.068 | +0.020 | +0.013 | +0.019 |
| IJH native | 145 | 41.4 | 1.44 | −1.07 | −0.031 | 0.95 | 13.8 | 7 | 3/5 | +0.109 | −0.208 | −0.085 | −0.058 |
| EFA native | **23** | 69.6 | 1.17 | −1.02 | **+0.503** | 2.62 | 2.2 | 2 | 5/5 | +0.274 | +0.753 | +0.246 | +0.464 |
| **POOLED non-QQQ** | **667** | 42.3 | 1.41 | −1.04 | **−0.004** | **0.99** | 38.9 | 10 | 3/5 | +0.042 | −0.053 | −0.016 | −0.026 |

**Pooled, clustered by date: SE 0.0529 over 468 dates, 95% CI
[−0.108, +0.100], t = −0.08. 2 of 4 instruments positive.**

### EFA's +0.503 is an artefact of the cost floor, not a result

EFA produced **23 trades from 315 setups — 275 were rejected by the minimum
stop.** The survivors are only the highest-ATR days, which is a volatility
selection, not the strategy. **Pooled excluding EFA: −0.022 on 644 trades.**
EFA's 23 trades contribute +11.6 R and are doing all the work that lifts the
pool from −0.022 to −0.004.

---

## 2. The comparability quantities are now aligned

| | ATR bps | IB bps | stop bps | **stop/ATR** | **zone/ATR** | cost % of risk |
|---|---|---|---|---|---|---|
| QQQ | 7.59 | 86.9 | 17.67 | **2.27** | 0.57 | 2.58 |
| SPY | 5.45 | 57.8 | 12.95 | **2.28** | 0.53 | 2.78 |
| IWM | 8.00 | 104.3 | 19.36 | **2.32** | 0.65 | 4.36 |
| IJH | 5.97 | 93.7 | 14.51 | **2.55** | 0.78 | 5.31 |
| EFA | 6.64 | 66.5 | 30.46 | 4.74 | 0.50 | 8.10 |

**stop/ATR collapses from a 1.63× spread to 2.27–2.55 across the four
comparable instruments.** True cost as a share of risk falls from a 6.62×
spread to 2.58–5.31%. **The economics are now genuinely comparable.**

EFA remains the outlier at 4.74 × ATR precisely because the cost floor forces
it there — which is the rule correctly refusing to trade an instrument whose
tick is too coarse for the setup.

---

## 3. The four questions asked

**Was the previous related-instrument test economically mismatched?**
**Yes.** The pool moved from **−0.046 to −0.004** on the same construction, and
the comparability spreads collapsed. The audit's diagnosis was correct.

**Does native normalisation materially improve portability?**
**Yes, and not enough.** −0.046 → −0.004 is a real improvement — from clearly
negative to indistinguishable from zero. It is not a reproduction. PF 0.99,
2 of 4 positive, CI straddling zero, and −0.022 once EFA's 23-trade artefact is
removed.

**Does the midpoint + R2 mechanism reproduce outside QQQ?**
**No.** On the pool the ending-zone condition — the element that carries QQQ —
is worth **−0.007** (base −0.004 vs no-EZ −0.011), and the **opposite bias is
better than the rule** (+0.087 vs −0.004).

**Does QQQ remain uniquely positive under both definitions?**
**Yes, but it weakens materially under native normalisation.**

| | frozen | native | change |
|---|---|---|---|
| expectancy | +0.185 | **+0.124** | **−33%** |
| profit factor | 1.35 | 1.23 | −0.12 |
| max drawdown | 8.4 R | **15.3 R** | **+82%** |
| losing streak | 5 | 8 | +3 |
| positive years | 5/5 | **4/5** | −1 |
| top-decile diagnostic | +0.037 | **−0.033** | sign flip |

---

## 4. Mechanism controls, native definitions

| control | QQQ n | QQQ R | pool n | pool R |
|---|---|---|---|---|
| **BASE** | 233 | **+0.124** | 667 | **−0.004** |
| 1 no ending-zone | 597 | −0.034 | 1,527 | −0.011 |
| 2 touch without R2 | 37 | −0.062 | 71 | −0.154 |
| 3 zone shifted 0.25 IB | 129 | +0.003 | 322 | −0.146 |
| 4 opposite bias | 110 | +0.043 | 287 | **+0.087** |

**On QQQ all four behave correctly** — the ending zone, the R2 rejection, the
midpoint location and the direction rule are each load-bearing, and the
opposite bias is worse than the rule. **The controls do not fail on QQQ.**

**On the pool two of four invert**, as before. No control is promoted.

---

## 5. Verdict

# NON-PORTABLE, and QQQ-SPECIFIC / UNRESOLVED

QQQ remains commercially positive under **both** definitions. The related
instruments remain negative after an economically valid native normalisation
that demonstrably fixed the mismatch. **Cross-instrument failure is not by
itself being used to call QQQ overfit**, per the brief.

**"Closed" was considered and not chosen.** The closure branch requires QQQ to
weaken materially *or* the controls to fail on QQQ. The controls pass cleanly.
QQQ did weaken — a third of its expectancy, 82% more drawdown, a lost positive
year, and a **sign flip on the top-decile diagnostic** — which is the single
most uncomfortable number in this report and is recorded as such.

---

## 6. Recommendation on the 2016–2020 QQQ holdout

# DO NOT OPEN IT YET

Not because cross-instrument failure condemns QQQ, but on the arithmetic.

| | frozen | native |
|---|---|---|
| **t-statistic** | **+1.89** | **+1.53** |
| single-test p | 0.059 | 0.127 |

**The native renormalisation lowered t from 1.89 to 1.53** — and 1.58 was the
best of an 18-variant search, a level a random search beats 65% of the time.
**Neither version reaches single-test significance, let alone corrected
significance.**

The holdout holds ~1,259 sessions ≈ 175 trades. At the observed sd, that gives
SE ≈ 0.08 and an MDE of ±0.16 R. **The effect being tested is +0.124. A holdout
of this size cannot resolve it** — it would return an inconclusive number and
the only clean out-of-sample data in the project would be spent.

### What would justify opening it

One of:

1. **The QQQ result surviving its own sensitivity.** The top-decile diagnostic
   flipping from +0.037 to −0.033 on a neutral renormalisation says the edge is
   carried by a small number of trades. That is the thing to resolve first, and
   it needs more independent trades, not more QQQ history.
2. **Forward collection on QQQ.** At 3.9 trades/month, a year adds ~47 trades.
   Two years would roughly double the sample at no cost to the holdout.
3. **A prior reason to expect a Nasdaq-specific microstructure effect.** None
   has been proposed, and without one "QQQ-specific" is a description of the
   data, not a mechanism.

**If the holdout is opened anyway, open it once, on the frozen definition, with
the pass criterion declared first** — and accept that an inconclusive result
ends the family with the asset spent.

---

## Appendix — formal statistics

| | n | exp R | SE | t | p (single) | top-decile diagnostic |
|---|---|---|---|---|---|---|
| QQQ frozen | 164 | +0.1854 | 0.0979 | **+1.89** | 0.059 | +0.0366 |
| QQQ native | 233 | +0.1238 | 0.0810 | **+1.53** | 0.127 | **−0.0326** |
| Pooled non-QQQ | 667 | −0.0040 | 0.0529¹ | −0.08 | 0.94 | — |
| Pooled ex-EFA | 644 | −0.0224 | — | — | — | — |

¹ clustered by calendar date over 468 shared dates.

QQQ native by year: 2021 +0.185 (43) · 2022 −0.099 (54) · 2023 +0.292 (49) ·
2024 +0.220 (50) · 2025 +0.025 (37).

Reproduce: `python3 scripts/orderflow/ib_pullback_native.py`.
Output `reports/ib_pullback_native_output.txt`.
