# Compressed range resolution: the economics worked, the mechanism is falsified

Pre-registered at `2417092`, amended at `02e0746` and `c2abfcb`. `c` was frozen
at **1.00** by a counts-and-widths-only pass before any R was read.

**Every table leads with `excess_R` (drift-adjusted). Long and short arms are
reported separately, always, before any pooled row.**

**Sealed days unread. 2016–2020 unread.**

---

## 1. The economic premise was met, decisively

This was the point of the whole change of direction, so it goes first.

| | cost / risk |
|---|---|
| ATR-stopped families | 5–16% |
| IB family | 0.77–1.16% |
| **this rule (median)** | **0.227%** |
| p75 / p90 | 0.286% / 0.334% |
| rejection threshold | 0.50% |

**A 3.4–5.1× improvement on the IB family and 22–70× on the ATR families.**
Median risk 293 bps against the IB family's 57–87. Selectivity did buy a wider
stop exactly as the design argued it must, and the rule passed the design-grounds
gate with room to spare.

**It then found nothing.** The two facts are separable and both are the result.

---

## 2. Counts, instrumentation, and one structural fact about the variants

| | |
|---|---|
| sessions | 1,396 |
| triggers, D = 10:00 / 10:30 | **200 / 208** |
| trades per month | **3.04** (target 3–6) |
| long / short | 126 / 74 and 132 / 76 |
| entry-bar lookahead violations | **0** |
| ambiguous bars | **0 of 200 (0.0%)** |
| honest vs naive mean R | identical to 4 dp in all six variants |
| exit mix (10:00, flat) | close 197, **stop 3**, target 0 |

**Two of the three exit variants do nothing.** With a stop at the far edge of a
3-session range, +1.0R is a ~293 bps move and is never reached; +0.5R fires on a
handful. Variants 1 and 3 are byte-identical, and 4 and 6 likewise. **The six
declared variants are really three, and the exit axis was dead on arrival** —
predicted in the proposal ("1R is unreachable intraday"), now confirmed.

The stop was hit **3 times in 200 trades**. This is the non-convex, truncated-
linear payoff the proposal warned about, and it means the concentration rule was
never going to be the binding test here.

---

## 3. The six variants — excess_R first

| D | exit | arm | n | **EXCESS R** | clus SE | t | after conc | yrs | raw R | drift | hold |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 10:00 | flat | **LONG** | 126 | **+0.0092** | 0.0252 | +0.36 | −0.0371 | 3/6 | +0.0166 | +0.0074 | +0.0238 |
| 10:00 | flat | **SHORT** | 74 | **−0.0231** | 0.0378 | −0.61 | −0.1010 | 3/6 | −0.0303 | −0.0072 | −0.0260 |
| 10:00 | flat | BOTH | 200 | −0.0028 | 0.0211 | −0.13 | −0.0544 | 3/6 | −0.0007 | +0.0020 | +0.0054 |
| 10:00 | +0.5R | **LONG** | 126 | **+0.0084** | 0.0250 | +0.34 | −0.0371 | 3/6 | +0.0159 | | |
| 10:00 | +0.5R | **SHORT** | 74 | **−0.0172** | 0.0380 | −0.45 | −0.0958 | 3/6 | −0.0244 | | |
| 10:00 | +0.5R | BOTH | 200 | −0.0011 | 0.0211 | −0.05 | −0.0518 | 2/6 | +0.0010 | | |
| 10:30 | flat | **LONG** | 132 | **+0.0025** | 0.0193 | +0.13 | −0.0342 | 3/6 | +0.0127 | +0.0102 | +0.0150 |
| 10:30 | flat | **SHORT** | 76 | **+0.0044** | 0.0298 | +0.15 | −0.0526 | 3/6 | −0.0055 | −0.0099 | −0.0022 |
| 10:30 | flat | BOTH | 208 | +0.0032 | 0.0164 | +0.19 | −0.0362 | 3/6 | +0.0060 | +0.0029 | +0.0087 |
| 10:30 | +0.5R | **LONG** | 132 | **+0.0025** | 0.0193 | +0.13 | −0.0342 | 3/6 | +0.0127 | | |
| 10:30 | +0.5R | **SHORT** | 76 | **+0.0082** | 0.0303 | +0.27 | −0.0517 | 3/6 | −0.0018 | | |
| 10:30 | +0.5R | BOTH | 208 | +0.0046 | 0.0165 | +0.28 | −0.0358 | 3/6 | +0.0074 | | |

(+1.0R rows are identical to the `flat` rows and are omitted; see §2.)

**Largest |t| anywhere in the family is 0.61.** The MDE declared before running
was ±0.062 at n = 200, sd 0.45, and ±0.084 after Bonferroni. **The largest
absolute excess_R is 0.023 — about a third of the MDE.** Nothing here is near
resolution in either direction.

### What the drift adjustment did

The raw long arm at 10:00 is +0.0166; the drift term is +0.0074, so **45% of the
raw long number was market drift.** The adjustment was worth making and the
amendment was right to demand it lead.

**No arm is consistent.** Every single row is 3 of 6 years or worse — one is 2 of
6. The 4-of-6 requirement is failed by all twelve arm-rows independently of
everything else.

---

## 4. Mechanism control 1: the effect must GROW as compression tightens

**It does the opposite.**

Nested `c` ladder, D = 10:00, flat (each row a superset of the one above):

| c | n | **EXCESS R** | t | LONG | SHORT |
|---|---|---|---|---|---|
| **0.60** | 29 | **−0.1106** | −1.50 | −0.0673 | **−0.2243** |
| 0.70 | 67 | −0.0428 | −0.98 | −0.0227 | −0.0812 |
| 0.80 | 120 | −0.0092 | −0.31 | −0.0061 | −0.0142 |
| 0.90 | 160 | −0.0116 | −0.47 | +0.0008 | −0.0313 |
| **1.00** | 200 | **−0.0028** | −0.13 | +0.0092 | −0.0231 |

The pre-registered prediction was that tighter compression concentrates
positioning and therefore strengthens the effect. **The effect is monotonically
*worse* the tighter the compression**, and most negative at the tightest setting
where the mechanism should be strongest. The short arm at c = 0.60 is −0.2243.

By k quartile within the frozen set, the pattern is not even monotone — it
alternates: −0.0467, +0.0352, −0.0339, +0.0344. That is noise, not a gradient.

**This is a falsification of the stated mechanism, not merely a null on the
headline.** Had I only reported the headline, this would have looked like an
ordinary underpowered null. The control says something stronger: the direction
of the claimed relationship is wrong.

---

## 5. Mechanism control 2: the effect must VANISH for breaks not held to D

**It is larger there.**

| arm | n | **EXCESS R** | clus SE | t | after conc | yrs |
|---|---|---|---|---|---|---|
| LONG | 55 | **+0.0086** | 0.0472 | +0.18 | −0.0970 | 4/6 |
| SHORT | 40 | **+0.0236** | 0.0881 | +0.27 | −0.2227 | 2/6 |
| BOTH | 95 | **+0.0149** | 0.0458 | +0.33 | −0.0918 | 4/6 |

The not-held arm — breaks that had already **failed** by D, which the mechanism
says carry no forced flow — returns **+0.0149** against the held arm's
**−0.0028**. Both are indistinguishable from zero (|t| ≤ 0.33), so the honest
statement is that **the condition the entire rule is built on separates nothing**.
What it certainly does not do is what was predicted.

---

## 6. The random-label control

Does taking the **most compressed** n of the structurally eligible pool beat
taking a **random** n of the same size?

| | |
|---|---|
| pool (W floor + resolved + held, any k) | 362 / 377 |
| observed n | 200 / 208 |
| **observed max t across the 6 variants** | **+0.276** |
| permuted max t, median | +0.518 |
| **permuted max t, 95th percentile** | **+1.372** |
| **beats the control?** | **NO** |
| empirical p | 0.707 |

**The observed best variant is below the median random draw.** Choosing the most
compressed 200 of 362 eligible sessions is worse than choosing 200 at random.

---

## 7. The concentration caveat does not apply here, and that is worth saying

You asked that a candidate failing **only** on concentration be reported
separately rather than closed.

**No variant qualifies.** Every variant fails on expectancy (largest |t| = 0.61,
effects a third of the MDE), on year consistency (3 of 6 or worse, everywhere),
and on the random-label control — before concentration is reached. There is no
candidate whose only problem is tail dependence.

And the caveat was always going to be inert for this design, exactly as flagged
in §6 of the proposal: **the stop was hit 3 times in 200 trades**, so the payoff
is truncated-linear rather than convex. This rule was never the kind the
concentration rule is unfair to. **That remains an open concern for some future
convex candidate; it is not a live concern here.**

---

## 8. The decision

| | |
|---|---|
| variants | 6 (really 3 — see §2) |
| median cost/risk | **0.227%**, bar 0.50% — **MET** |
| variants with excess_R > 0 | 3 of 6 |
| ...surviving max(10, ⌈0.10n⌉) | **0** |
| ...and 4 of 6 years | **0** |
| beats the random-label control | **NO** |
| mechanism control 1 (effect grows as c falls) | **FAILED — reversed** |
| mechanism control 2 (effect vanishes when not held) | **FAILED — reversed** |

**The family closes.**

### What is actually new here

The rarity change worked on its own terms. This is the first family in the
project to fire on **14% of sessions at 3.04 trades/month**, against the 40–100%
of everything before it, and the first to get **cost down to 0.23% of risk**. The
economic premise — that selectivity buys a wider stop and a wider stop buys back
the cost — is demonstrated. **What is not demonstrated is that anything is on
the other side of the trade.**

Both mechanism controls reversing is the most informative part of the run. A
null on the headline alone would leave open "underpowered, try more data". The
controls close that off: at the tightest compression, where the forced-flow story
predicts the strongest effect, the result is most negative; and the arm the story
says should be empty is the better one.

---

## 9. Ledger entry

| screen | sample | outcome |
|---|---|---|
| **compressed 3-session range, resolved and held** | **1,396 sessions, 200–208 trades, 6 variants (3 distinct)** | **closed. Cost/risk 0.227% — the economic requirement MET, a 3.4–5.1× improvement on the IB family. Largest \|t\| 0.61, effects ~⅓ of the declared MDE, 3 of 6 years everywhere, fails the random-label control at p 0.707. BOTH mechanism controls failed in the reversed direction: effect most negative at tightest compression (−0.111 at c = 0.60), and the not-held arm (+0.015) beat the held arm (−0.003). Mechanism falsified, not merely unresolved.** |

Standing constraints honoured: `c` frozen on counts and widths before any R was
read, sealed days unread, **2016–2020 unread and unspent**, nothing frozen that
would justify opening it.

Reproduce: `python3 scripts/orderflow/compression.py calibrate` then
`python3 scripts/orderflow/compression_run.py`.
Full output in `reports/compression_output.txt`; calibration ladder in
`reports/compression_calibration.csv`; per-variant detail in
`reports/compression_variants.csv`.
