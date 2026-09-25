# The mechanised discretionary strategy: 0 of 8, and the win rate is the target distance

Pre-registered at `b8db9d2`
(`reports/pullback_discretionary_preregistration.md`) before this ran. Sealed NQ
days were not read.

---

## 1. Counts first

| | |
|---|---|
| sessions | **1,417** — QQQ 1-minute, 2021-01-05 to 2026-08-31, 4 rejected |
| years | 2021 (249), 2022 (250), 2023 (250), 2024 (252), 2025 (250), 2026 (166) |
| **total trades across the grid** | **12,253**, against the claim's 31 |
| entry lookahead | **0** in every variant |
| ambiguous bars | **0.0–0.3%** |

| variant | trades | sessions | tr/sess | max/sess | med risk | flat% |
|---|---|---|---|---|---|---|
| T1 P1 f0.33 | 1,539 | 952 | 1.62 | 11 | 30.3 bps | 33.1% |
| T1 P1 f0.50 | 993 | 729 | 1.36 | 8 | 31.2 bps | 34.0% |
| T1 P2 f0.33 | 1,172 | 952 | 1.23 | 5 | 33.0 bps | 50.9% |
| T1 P2 f0.50 | 822 | 729 | 1.13 | 4 | 31.6 bps | 52.2% |
| T2 P1 f0.33 | 2,823 | 1,325 | 2.13 | 10 | 22.7 bps | 25.1% |
| T2 P1 f0.50 | 1,549 | 981 | 1.58 | 6 | 23.4 bps | 27.7% |
| T2 P2 f0.33 | 2,075 | 1,325 | 1.57 | 6 | 22.6 bps | 41.0% |
| T2 P2 f0.50 | 1,280 | 981 | 1.30 | 5 | 22.6 bps | 43.4% |

---

## 2. The comparison the claim has to survive

Each variant is judged against **its own realised reward-to-risk**, not against
50% and not against the trader's 1.87.

| variant | trades | realised R:R | RW hit rate | observed | **gap** | z | expR | PF | t | yrs+ |
|---|---|---|---|---|---|---|---|---|---|---|
| T1 P1 f0.33 | 1,539 | 0.87 | 53.4% | 51.5% | **−1.9** | −1.51 | −0.030 | 0.93 | −1.17 | 2/6 |
| T1 P1 f0.50 | 993 | 0.90 | 52.7% | 50.3% | **−2.4** | −1.52 | −0.038 | 0.91 | −1.14 | 1/6 |
| T1 P2 f0.33 | 1,172 | 1.30 | 43.5% | 42.7% | **−0.9** | −0.59 | −0.017 | 0.97 | −0.47 | 4/6 |
| T1 P2 f0.50 | 822 | 1.36 | 42.3% | 41.2% | **−1.1** | −0.61 | −0.021 | 0.96 | −0.49 | 3/6 |
| T2 P1 f0.33 | 2,823 | 0.91 | 52.3% | 49.8% | **−2.4** | −2.57 | −0.041 | 0.91 | −1.92 | 2/6 |
| T2 P1 f0.50 | 1,549 | 0.94 | 51.7% | 49.8% | **−1.9** | −1.48 | −0.032 | 0.93 | −1.13 | 2/6 |
| T2 P2 f0.33 | 2,075 | 1.50 | 40.0% | 39.1% | **−0.9** | −0.83 | −0.020 | 0.96 | −0.70 | 2/6 |
| T2 P2 f0.50 | 1,280 | 1.54 | 39.4% | 39.2% | **−0.2** | −0.11 | −0.003 | 0.99 | −0.09 | 2/6 |
| **claimed** | **31** | **1.87** | **34.8%** | **77.0%** | **+42.2** | **+4.93** | — | **6.39** | — | — |

**Every variant lands below its own random-walk rate. Mean gap −1.45 points,
range −2.4 to −0.2.** The claim needs +42.2. The shortfall is **43.6 points**.

Against the mechanised rule's best-matched variant, a 77% hit rate would be a
**27.5-sigma** event.

### The finding inside the table

The eight variants span realised reward-to-risk from **0.87 to 1.54** and
observed win rates from **39.1% to 51.5%** — a 12-point spread in hit rate. That
spread is not evidence of anything. Across the eight:

> **correlation between observed win rate and 1/(1+R:R) = 0.9982**
> **mean absolute deviation from the random-walk rate = 1.45 points**

**The win rate is the target distance.** Move the target closer and the hit rate
rises exactly as far as a coin says it should; move it further and it falls
exactly as far. There is no residual. This is what a strategy with no edge looks
like when you sweep its target, and it is the cleanest demonstration of that in
this project.

---

## 3. Where the 42 points did not come from

### Not the fill model

The honest fill was expected to be the correction that ate the claim. It is not.

| variant | gapped% | mean slip R | HONEST expR | NAIVE expR | phantom |
|---|---|---|---|---|---|
| T1 P1 f0.33 | 49.8% | +0.002 | −0.030 | −0.025 | **+0.006** |
| T2 P1 f0.33 | 47.6% | +0.001 | −0.041 | −0.038 | **+0.003** |
| T2 P2 f0.50 | 42.6% | +0.000 | −0.003 | −0.001 | **+0.002** |

**The phantom profit from naive fills is +0.001 to +0.006 R.** Even a backtest
that filled every entry at the trigger price and every stop exactly at the stop
would still have been at or below the random-walk rate. The gap between 77% and
chance is roughly **7,000 times** the size of the fill correction. Whatever
produced the reported figure, it was not optimistic fills.

### Not the daily stop

Pre-registered as unable to change per-trade expectancy, and confirmed rather
than assumed:

| variant | trades off → on | expR off | expR on | diff | win% off → on |
|---|---|---|---|---|---|
| T1 P1 f0.33 | 1,539 → 1,165 | −0.030 | −0.046 | −0.016 | 51.5 → 49.7 |
| T1 P2 f0.33 | 1,172 → 1,109 | −0.017 | −0.014 | +0.003 | 42.7 → 42.6 |
| T2 P2 f0.33 | 2,075 → 1,886 | −0.020 | −0.015 | +0.005 | 39.1 → 39.5 |
| T2 P2 f0.50 | 1,280 → 1,210 | −0.003 | −0.001 | +0.003 | 39.2 → 39.3 |

Differences run **−0.031 to +0.005 R** and take both signs — a composition
effect from truncating the trade sequence, not an edge. The rule removes about a
quarter of the trades and moves per-trade expectancy by nothing.

It does exactly what such rules always do: it shortens the losing tail of a
session and flatters the equity curve and the drawdown **without touching the
thing that determines whether the strategy makes money.** The reported profit
factor of 6.39 is an equity-curve statistic, and this is the mechanism by which
that number can look spectacular while per-trade expectancy is negative.

### Not the trend definition, the pullback depth, or the levels

All eight combinations fail, and they fail by similar margins. The two trend
definitions, the two retracement floors and the two targets move trade counts
around substantially — from 822 to 2,823 — and move the gap over the random walk
by **2.2 points in total**.

---

## 4. The levels story is decorative — as pre-registered, stated plainly

P1 exits at the nearest prior-session level (high, low, close, VWAP); P2 exits at
a flat 3R. **P1 loses to P2 in all four pairs:**

| trend | floor | P1 expR | P2 expR | **P1 − P2** | P1 win% | P2 win% | P1 R:R | P2 R:R |
|---|---|---|---|---|---|---|---|---|
| T1 | 0.33 | −0.030 | −0.017 | **−0.014** | 51.5 | 42.7 | 0.87 | 1.30 |
| T1 | 0.50 | −0.038 | −0.021 | **−0.017** | 50.3 | 41.2 | 0.90 | 1.36 |
| T2 | 0.33 | −0.041 | −0.020 | **−0.021** | 49.8 | 39.1 | 0.91 | 1.50 |
| T2 | 0.50 | −0.032 | −0.003 | **−0.028** | 49.8 | 39.2 | 0.94 | 1.54 |

The pre-registration committed to this sentence in advance: **if P1 does not beat
P2, the levels story is decorative.** It does not. Prior-session levels raise the
win rate — 50% against 41% — and lower the reward-to-risk by exactly enough to
make it worse than not using them at all. They are not attracting price. They are
just a nearer target.

---

## 5. Rejection criteria

| variant | expR>0 | sess≥15 | PF≥1.15 | ex-top1%>0 | yrs+≥4 | t>3 | beats RW | **survives** |
|---|---|---|---|---|---|---|---|---|
| all eight | **NO** | yes | **NO** | **NO** | 1 of 8 | **NO** | **NO** | **no** |

**0 of 8.** Only one variant (T1 P2 f0.33) manages positive years in 4 of 6, and
it is negative overall with t = −0.47.

Year by year, nothing holds. 2024 — the year the claim was made in — is the
**worst** year for three of the four T1 variants (−0.117, −0.126, −0.204, −0.154
mean R), which is the configuration closest to the trader's described method.

---

## 6. The answer to the question asked

> *If the mechanical version lands near the random walk rate, the reported figure
> was method rather than market, and say so plainly.*

**It lands slightly below the random-walk rate, in all eight variants, on 12,253
trades.** The reported 77% at 1.87 R:R was **method, not market.**

The specific mechanism is visible in the numbers. It is not fills, which are
worth 0.006 R. It is not the daily stop, which moves expectancy by nothing. It is
that the win rate of this rule is fixed by how far away the target is, and 31
hand-replayed trades in a single month — with the bar forming on screen while
the operator decides whether this one counts — is not a sample that can
distinguish a strategy from its target distance.

The trader's realised 1.87 reward-to-risk is also **above every value the
mechanised rule produces** (0.87 to 1.54). Getting 1.87 out of this rule's
structure requires selecting which setups to take and which targets to use —
which is exactly the discretion that cannot be tested, and exactly the discretion
that a replay with hindsight makes feel reliable.

**The 21 NQ tick sessions are not spent.** Verification there was conditional on
the mechanised rule landing materially above the random-walk rate. It landed
below it.

---

## 7. Where the ledger stands

| screen | sample | outcome |
|---|---|---|
| pullback, QQQ screen | 1,418 sessions, 16 variants | closed, 0 of 16 |
| ORB + VWAP, QQQ screen | 1,418 sessions, 16 variants | closed, 0 of 16 |
| OR height, promoted | 1,418 + 1,256 held out, 4 variants | closed, 0 of 4 |
| European session, descriptive | 21 NQ sessions | same market, worse terms; nothing bought |
| regime forecastability | 1,418 sessions, 14 combinations | closed, 0 of 14 |
| **discretionary strategy, mechanised** | **1,417 sessions, 8 variants, 12,253 trades** | **closed, 0 of 8; below the random walk** |

Reproduce: `python3 scripts/orderflow/disc_pullback.py`.
