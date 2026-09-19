# The setup grading scheme is worse than random — and backwards

Pre-registered at `bb0ab30` (`reports/setup_grading_preregistration.md`) before
this ran. Grades applied to trades the existing machines already generate. No new
rule. Sealed NQ days were not read.

---

## 1. Counts first

| trade set | trades | lookahead | ambiguous |
|---|---|---|---|
| ORB OR15 R3 | 2,479 | 0 | 0.0% |
| ORB OR15 R4 | 2,637 | 0 | 0.0% |
| ORB OR30 R3 | 2,611 | 0 | 0.0% |
| ORB OR30 R4 | 2,590 | 0 | 0.0% |
| pullback OR15 R3 | 2,086 | 0 | 0.0% |
| pullback OR30 R3 | 1,437 | 0 | 0.0% |
| **POOLED** | **13,840** | **0** | **0.0%** |

| grade | trades | share | med cost/risk | med risk | med mins | med OR ratio |
|---|---|---|---|---|---|---|
| A+ | 1,604 | 11.6% | 3.77% | 17.7 bps | 30 | 1.34 |
| A | 3,990 | 28.8% | 5.09% | 13.1 bps | 33 | 1.11 |
| B | 8,246 | 59.6% | 8.06% | 8.3 bps | 57 | 0.78 |

**≥300 trades in every grade: yes.** That is the only pre-registered criterion
that passes.

---

## 2. Expectancy by grade

| grade | trades | NET expR | GROSS expR | NAIVE expR | cost drag |
|---|---|---|---|---|---|
| **A+** | 1,604 | **−0.1600** | −0.1233 | −0.1478 | +0.0366 |
| A | 3,990 | −0.0305 | +0.0256 | +0.0081 | +0.0562 |
| B | 8,246 | −0.0504 | +0.0395 | −0.0210 | +0.0899 |

**A+ is the worst grade.** A is the best. The ordering is not merely flat, it is
scrambled — and the top grade is at the bottom.

| | |
|---|---|
| A+ minus B, **net** | **−0.1096 R** |
| A+ minus B, **gross** | **−0.1628 R** |
| the difference | **+0.0533 R** |

**The accounting identity behaved exactly as pre-registered.** The A+ bucket does
pay a smaller toll — cost drag 0.0366 against B's 0.0899, a mechanical saving of
0.053 R, predicted in advance and delivered.

**And the market swamped it three to one.** In gross terms, with cost removed
entirely, A+ underperforms B by 0.163 R. The grading buys a genuine cost
advantage and then gives back three times as much in behaviour.

---

## 3. The control

1,000 random assignments at the same proportions, over the same pooled trades:

| | |
|---|---|
| random A+ − B spread | mean −0.0028, sd 0.0494 |
| 5th / 95th percentile | −0.0864 / +0.0767 |
| **real spread** | **−0.1096** |
| **percentile of random** | **1.4th** |

**The real grading does not beat random assignment.** It is beaten by 98.6% of
random assignments.

Year by year, net A+ − B: **−0.1455, −0.2043, −0.1881, +0.0596, −0.3938,
+0.2448 — 2 of 6.** And every one of the six trade sets shows a negative spread,
from −0.011 to −0.209. The direction is not a fluke of pooling; it is unanimous.

| criterion | result |
|---|---|
| ≥ 300 trades per grade | **PASS** |
| monotonic A+ ≥ A ≥ B | **FAIL** |
| spread beats 95th pct of random | **FAIL** |
| A+ > B in ≥ 4 of 6 years | **FAIL** |

---

## 4. Which component did it — diagnostic, not a new test

Each condition on its own, gross R (cost removed) and net R:

| component | n | gross: on − off | net: on − off |
|---|---|---|---|
| **cost/risk ≤ 5% (wide stop)** | 3,964 | **−0.1525** | **−0.1013** |
| OR ratio ≥ 1.00 (tall OR) | 5,588 | −0.0378 | −0.0210 |
| **minutes ≤ 60 (early)** | 9,346 | **+0.0630** | **+0.0840** |

- **The cost/risk component is the culprit, and it is the one I pre-registered as
  having a mechanical reason to work.** It does save cost, exactly as predicted.
  But selecting for a wide stop is selecting for high volatility, and those
  trades lose 0.15 R in gross terms — so the component that was guaranteed to
  help on arithmetic is the one that hurts most in total.
- **OR ratio contributes −0.038**, mildly against the direction the OR-height
  screen claimed, consistent with that screen's 0-of-4 null.
- **Early entry is the only component pointing the right way**, at +0.084 net.

The composite fails because it bundles one helpful condition with two harmful
ones and weights them equally. Any *mechanism* for why wide-stop trades
underperform is post hoc and is not claimed here.

---

## 5. Two things that must be said plainly

**First, as asked: the real grading does not beat random assignment, so grade
does not separate outcome. The idea should be dropped.**

**Second, "significant in the wrong direction" is not a result you can invert and
trade.** The spread sits at the 1.4th percentile, which would be a strong finding
had the opposite direction been declared. It was not. Flipping a hypothesis after
seeing which way it failed is precisely what pre-registration exists to stop, and
the same discipline that makes the seven prior nulls trustworthy forbids it here.
If an inverted version is wanted, it needs its own pre-registration and it should
be spent on the **1,259 sessions of 2016–2020 that this project has still never
read** — not re-measured on the sample that produced the idea.

**And the finding that outranks both:** every grade is negative. A+ −0.160,
A −0.031, B −0.050, pooled **−0.0574 R over 13,840 trades**. Grading sorts an
unprofitable rule into unprofitable buckets. No labelling scheme rescues a rule
with no edge, which is what the seven prior screens already established.

---

## 6. Where the ledger stands

| screen | sample | outcome |
|---|---|---|
| pullback, QQQ screen | 1,418 sessions, 16 variants | closed, 0 of 16 |
| ORB + VWAP, QQQ screen | 1,418 sessions, 16 variants | closed, 0 of 16 |
| OR height, promoted | 1,418 + 1,256 held out, 4 variants | closed, 0 of 4 |
| European session, descriptive | 21 NQ sessions | same market, worse terms |
| regime forecastability, price | 1,418 sessions, 14 combinations | closed, 0 of 14 |
| discretionary strategy, mechanised | 1,417 sessions, 8 variants | closed, 0 of 8 |
| regime forecastability, gamma | 336 sessions, 4 combinations | closed, 0 of 4 |
| levels, predictive | 1,414 + 336 sessions, 13 tests | closed, 0 of 13 |
| **setup grading** | **13,840 trades, 6 sets** | **closed, 1 of 4 criteria; worse than random** |

Reproduce: `python3 scripts/orderflow/setup_grading.py`.
Per-trade detail in `reports/setup_grading_trades.csv`.
