# RP-012A Stage 1 — discovery result, 2021–2023

**Descriptive only.** No entry, stop, target, expectancy or prop simulation was
constructed. **2024–2025 was not opened.** Pre-registered at
`reports/rp012a_stage0.md` (`3816474`); construction in `rp012a_common.py`,
unchanged; harness `rp012a_stage1.py`; raw output `rp012a_stage1_output.txt`.

## 0. Gate and corrections

Corrections 1–8 required by the approval were entered in the correction ledger
(§16) **before** the run. Platform suite, run by the harness itself before
anything else: **PASS 139, FAIL 0.**

Definitions the brief left open were declared in the harness docstring before it
ran: "material" = a date-clustered paired difference ≥ one round-trip cost
**and** t ≥ 2.0; "similar" = a difference below one round-trip cost; time to
continuation/reversal = first minute reaching one typical 5-minute move of the
bucket; return to origin = trading back to the level the event window started
from.

**Independent check of the plumbing:** eight QQQ state-A events were recomputed
from raw bars outside the harness — window displacement, direction, entry at the
next bar's open, 15-minute exit. **8 of 8 match exactly.** No event lacked an
entry bar.

## 1. Counts before outcomes

| | QQQ | SPY | IWM | EFA (control) |
|---|---|---|---|---|
| sessions available / half days / used | 753 / 4 / 749 | 753 / 4 / 749 | 753 / 4 / 749 | 753 / 4 / 749 |
| warm-up / labelled | 35 / 714 | 35 / 714 | 35 / 714 | 35 / 714 |
| sessions excluded for missing data | 0 | 0 | 0 | 0 |
| eligible windows | 53,539 | 53,537 | 53,537 | 53,534 |
| A candidates → events | 3,413 → 1,830 | 3,545 → 1,830 | 2,931 → 1,568 | 2,372 → 1,430 |
| B candidates → events | 1,640 → 845 | 1,488 → 772 | 1,806 → 1,051 | 2,108 → 1,293 |
| C observations | 24,438 | 24,410 | 24,943 | 25,185 |
| removed by cooldown | 46.7% | 48.0% | 44.0% | 35.8% |
| events / session · / month | 3.75 · 76.4 | 3.64 · 74.3 | 3.67 · 74.8 | 3.81 · 77.8 |
| A: sessions · buy / sell | 491 · 846 / 984 | 494 · 864 / 966 | 483 · 744 / 824 | 471 · 690 / 740 |

Every instrument × state × year and × block cell is populated. Simultaneous
cross-instrument events: 1,391 slots, **38.6%** of primary events. Blocks as
frozen: opening 09:35–10:00, morning 10:00–11:30, midday 11:30–14:00, closing
14:00–15:50.

**All six Stage 0 count conditions remain satisfied** (min 380 sessions per
cell; block share 0.92–1.23× window share; every block has A and B; buy share
46.2–50.3%; abnormal rate 0.97–1.08× per block; every year in every cell).

## 2. Forward outcomes — state A, direction-adjusted bps

| | 5 min | **15 min** | 30 min | cont % (15) | clustered t (15) |
|---|---|---|---|---|---|
| QQQ | +0.336 | **+0.692** | −0.111 | 51.1 | +1.85 |
| SPY | −0.657 | **+0.015** | +0.399 | 50.3 | −0.14 |
| IWM | −1.181 | **−1.040** | +0.971 | 49.6 | −0.79 |
| EFA (control) | −0.291 | −0.335 | +0.171 | 48.0 | −0.75 |
| **pooled primary, per date** | | **−0.064** | | | **−0.19** |

State B, 15 min: QQQ +0.125, SPY −0.282, IWM −0.316 — returns to its origin
85–87% of the time against 32–38% for A, so B does behave differently in path
shape, but neither state has a forward drift.

**State A does not continue.** Continuation frequency is 49.6–51.1% — a coin
flip. MFE and MAE are symmetric (QQQ 20.35 vs 19.06 bps at 15 min).

**Buy and sell separately, 15 min:**

| | buy | sell |
|---|---|---|
| QQQ A | +0.438 | +0.910 |
| SPY A | −0.148 | +0.161 |
| IWM A | **−3.095** | +0.819 |

**By year, 15 min, state A:** QQQ +0.150 / −0.485 / **+2.671**; SPY −0.141 /
−0.374 / +0.624; IWM −0.425 / −2.174 / −0.381. Pooled per date: **−1.165 /
+0.441 / +0.177.** QQQ's only material year is 2023.

**By block, 15 min, state A:** no block is consistently positive across
instruments (QQQ all four positive and small; IWM negative in three of four).

## 3. Load-bearing controls, 15 min

| | QQQ | SPY | IWM |
|---|---|---|---|
| state A | +0.692 | +0.015 | −1.040 |
| **1 displacement only (C, RD ≥ p80), standardised** | **+0.810** | −0.205 | +0.101 |
| **A minus displacement only, date-paired** | **−0.732 (t −0.76)** | **−1.060 (t −1.73)** | **−1.235 (t −1.22)** |
| 2 abnormal volume, no displacement (B) | +0.125 | −0.282 | −0.316 |
| A minus B | +1.666 (t +1.18) | +1.201 (t +1.15) | −1.894 (t −1.29) |
| 3 ordinary, volatility × block matched | −0.005 | −0.151 | −0.141 |
| A minus matched ordinary | +0.530 (t +0.74) | −0.155 (t −0.31) | −0.572 (t −0.65) |
| 4 absolute volume, same RD rule, cooled | −1.175 | −0.771 | −0.508 |
| A minus absolute volume | +1.183 (t +1.23) | +0.539 (t +0.94) | +1.064 (t +1.09) |
| 5 random direction, A's percentile | 84.7th | 51.2nd | 8.3rd |

**The primary comparison fails in every instrument.** The same-size price move
at *ordinary* volume does **at least as well** as the same move at abnormal
volume. The date-paired A-minus-displacement difference is negative in QQQ, SPY
and IWM, and **negative in 8 of 9 instrument-years**:

| | 2021 | 2022 | 2023 |
|---|---|---|---|
| QQQ | −2.268 | −1.283 | +0.836 |
| SPY | −0.577 | −0.388 | −2.020 (t −2.18) |
| IWM | −1.670 | −1.633 | −0.505 |

The one thing the normalisation achieved: time-normalised relative volume beats
raw volume in point estimate on all three instruments (+0.54 to +1.18 bps). Each
difference exceeds one round-trip cost, so by the declared rule absolute volume
does **not** perform "similarly". But none reaches t = 2, and relative volume
beats raw volume only by making a negative number less negative. Improving on a
worse construction is not information about the future.

**EFA** (lower-liquidity control): state A −0.335, no better than the primaries.
Stale pricing does not flatter it here.

## 4. Independence and concentration — state A, 15 min

| | event mean | date-clustered | t | dates | dates + | LOO range | − best date | − best 5 | best-5 share |
|---|---|---|---|---|---|---|---|---|---|
| QQQ | +0.692 | +1.197 | +1.85 | 491 | 264 | +1.08 … +1.33 | +1.079 | +0.682 | 43.6% |
| SPY | +0.015 | −0.069 | −0.14 | 494 | 244 | −0.17 … +0.04 | −0.169 | −0.520 | — |
| IWM | −1.040 | −0.666 | −0.79 | 483 | 223 | −0.88 … −0.47 | −0.878 | −1.313 | — |
| **pooled** | −0.064 | **−0.093** | **−0.19** | 609 | 311 | −0.18 … −0.00 | −0.179 | −0.487 | — |

QQQ alone is not date-concentrated (it survives removing the best five dates),
but it is not significant after clustering (t 1.85), sits below the
displacement-only control, and exists only in 2023. Pooled by month: **19 of 35
months positive.**

## 5. Commercial hurdle — state A, 15 min

| | gross | median | RT | net | hurdle (3× RT) | clears | gross / 1.2 ATR | cost / risk | trades/mo |
|---|---|---|---|---|---|---|---|---|---|
| QQQ | +0.692 | +0.539 | 0.513 | +0.178 | 1.515 | **no** | +0.083 | 6.1% | 17.4 |
| SPY | +0.015 | +0.217 | 0.404 | −0.389 | 1.213 | **no** | +0.002 | 6.7% | 17.4 |
| IWM | −1.040 | +0.000 | 0.875 | −1.914 | 2.653 | **no** | −0.119 | 10.0% | 14.9 |

No instrument clears its hurdle. The best, QQQ, delivers **46%** of its hurdle
and **8%** of a risk container.

## 6. Discovery pass conditions — 1 of 12

| # | condition | result |
|---|---|---|
| 1 | A continues at 15 min | **FAIL** — pooled −0.064, t −0.19; SPY flat, IWM negative |
| 2 | A exceeds 3× cost | **FAIL** — none of three |
| 3 | A materially beats displacement only | **FAIL** — *below* it in all three, and in 8 of 9 instrument-years |
| 4 | A materially beats abnormal volume without displacement | **FAIL** — QQQ/SPY differences exceed cost but t < 2; IWM negative |
| 5 | relative volume adds information beyond absolute volume | **FAIL** — point estimates favour it, none reaches t 2, and it is better only than a negative baseline |
| 6 | positive and negative events both correct | **FAIL** — QQQ only; IWM buys −3.095 |
| 7 | present in QQQ, SPY and IWM, or two with a reason | **FAIL** — QQQ only |
| 8 | present in two of three years | **FAIL** — pooled positive in 2022 and 2023 at t 0.45 and 0.30; QQQ material only in 2023 |
| 9 | matched controls weaker | **FAIL** — displacement-only is stronger |
| 10 | survives date clustering | **FAIL** — best t 1.85 (QQQ); pooled −0.19 |
| 11 | positive after removing the best five dates | QQQ yes (+0.682); pooled **no** (−0.487) |
| 12 | ≥ 4 trades per month | **PASS** — 14.9–17.4 |

## 7. Kill conditions — 7 of 10 fire

| # | condition | fires? |
|---|---|---|
| 1 | displacement alone performs similarly | **YES** — it performs better |
| 2 | absolute volume performs similarly | **no**, by the declared rule — relative beats absolute by more than one cost in point estimate on all three, though not significantly |
| 3 | A does not continue | **YES** |
| 4 | only positive or only negative events work | **YES** outside QQQ — sells positive, buys negative in SPY and IWM |
| 5 | result appears in only one year | **YES** — QQQ's material year is 2023 alone |
| 6 | driven by a few dates | no — there is no positive pooled result to drive |
| 7 | time and volatility matching removes the effect | **YES** — matched on displacement it reverses; matched on volatility and block it is t 0.74 or less |
| 8 | forward movement below the hurdle | **YES** — all three |
| 9 | cross-instrument results conflict without a market reason | **YES** — QQQ +0.69, SPY +0.02, IWM −1.04; nothing about the mechanism distinguishes them |
| 10 | EFA better solely because of stale prices | no — EFA is not better |

## 8. What the study establishes

- **Abnormal relative volume does not add forward information to a 5-minute
  price move on liquid ETFs.** Holding displacement fixed, the high-volume
  version continues *less* than the ordinary-volume version.
- The scale finding from RP-010 — top-decile delta, progress and volume each ≈
  +15 NQ points at 900 s on 34 sessions — **does not replicate as a mechanism on
  2,142 labelled ETF-sessions (714 × 3).** The RP-010 figures were not controlled against
  displacement at ordinary volume, and that is the control that decides it here.
- State B (volume without displacement) returns to its starting level 85–87% of
  the time within 15 minutes against 32–38% for A — a real path difference, but
  it carries no directional drift either way.

## 9. What it cannot say

Nothing about other windows or horizons (one construction was frozen and run),
about NQ (not acquired, not inspected), about 2024–2025 (not opened), or about
relative volume as a *volatility* predictor rather than a direction predictor —
MFE and MAE both scale with it, which was not the question.

---

## Verdict

> **Relative volume mechanism rejected, close RP 012A.**

State A does not continue (pooled −0.064 bps, t −0.19). It does not beat the same
price move at ordinary volume in any instrument, and falls short of it in 8 of 9
instrument-years. No instrument clears its cost hurdle, the only positive
instrument (QQQ) is positive materially only in 2023, and buy and sell events
disagree outside QQQ. Seven of ten kill conditions fire; one of twelve pass
conditions holds.

**2024–2025 stays unopened**, and remains available as internal validation to a
future family. No NQ data was acquired or inspected. No Stage 2.
