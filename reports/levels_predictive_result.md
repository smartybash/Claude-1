# Prior-day and gamma levels: 0 of 8 on reaction, 0 of 5 on clustering

Pre-registered at `d6539a1`
(`reports/levels_predictive_preregistration.md`) before this ran. Descriptive.
No rule was traded. Sealed NQ days were not read.

---

## 1. The test that was refused, and why it matters more than the ones that ran

The famous number in this area — **next-day high stayed below the call wall 90%
of the time** — was not re-run, because it is degenerate. At a fixed distance the
answer is entirely determined by P(price travels that far). A call wall, a random
price and an arbitrary number score **identically**, not similarly, so no placebo
can rescue it. That 90% measures "QQQ rarely moves 2% in a day."

The two designs below each remove distance instead of being confounded by it.

---

## 2. Test A — reaction at touch: 0 of 8

Counted only where price actually **reached** the level, which eliminates the
distance confound. Null is 50%: from a walk started at the level, either side is
equally likely.

| level | group | touched | touch% | react 30m | p | react 60m | p |
|---|---|---|---|---|---|---|---|
| **PDH** | price | 545 | 39% | **44.8%** | 0.015 | 46.7% | 0.130 |
| PDL | price | 468 | 33% | 48.1% | 0.405 | 49.6% | 0.851 |
| VAH | price | 644 | 46% | 47.2% | 0.156 | 48.8% | 0.550 |
| VAL | price | 586 | 41% | 51.5% | 0.457 | 49.9% | 0.967 |
| POC | price | 661 | 47% | 49.0% | 0.613 | 52.4% | 0.224 |
| *call_wall* | *gamma* | *40* | *12%* | *35.0%* | *0.058* | *42.5%* | *0.343* |
| *put_wall* | *gamma* | *24* | *7%* | *54.2%* | *0.683* | *56.5%* | *0.532* |
| *gamma_flip* | *gamma* | *90* | *27%* | *48.9%* | *0.833* | *49.4%* | *0.916* |

**The five price levels are properly tested** — 468 to 661 touches each — and
every one sits within a few points of a coin. Nothing approaches the 55% bar.

**All three gamma levels are INELIGIBLE, not failed.** The pre-registration set a
minimum of 100 touches precisely so small samples could not be over-read, and
they return 40, 24 and 90. They are printed in italics above and **not judged**.

The reason is itself the finding: **the call wall is reached in 12% of sessions
and the put wall in 7%.** They sit far from price by construction. That reproduces
the earlier intraday result (~37 tags in 123 sessions) and it means the walls
cannot be tested as reaction levels on any sample this project is likely to have.
A rule that fires on 7% of sessions needs roughly fourteen times the data.

### The one directional lean, which points the wrong way for the folk version

**PDH reacts at 44.8%, not 55%.** When price reaches yesterday's high it is
slightly more likely to *carry through* than to reject — the opposite of the
standard "prior-day high is resistance" claim. The lean is consistent at both
horizons (44.8%, 46.7%) and uncorrected p = 0.015, which **does not survive**
Bonferroni over 24 tests, so it is not claimed as a result. It is noted because
it is the only structure in the table and because its sign is inconvenient for
the belief that motivated the test.

---

## 3. Test B — turning-point clustering: 0 of 5

Do the session's own high and low land nearer these levels than a **stranger's
level set** — the same geometry lifted from a random other session as relative
offsets and applied to today's price? 200 shuffles.

| level set | sessions | real | placebo | ratio | shuffles beating real | p |
|---|---|---|---|---|---|---|
| **prior-day (PDH/PDL)** | 1,414 | 47.4 bps | 50.8 | **0.934** | **0 of 200** | **0.005** |
| **all five price levels** | 1,414 | 28.4 bps | 30.4 | **0.936** | **0 of 200** | **0.005** |
| price + gamma combined | 336 | 18.7 bps | 20.4 | 0.915 | 10 of 200 | 0.055 |
| value area (VAH/VAL/POC) | 1,414 | 45.2 bps | 46.6 | 0.970 | 16 of 200 | 0.085 |
| gamma (walls + flip) | 336 | 64.2 bps | 65.9 | 0.975 | 58 of 200 | 0.294 |

**This is the interesting row of the whole study, and it is the one the
pre-registered bar was written for.**

Prior-day high and low **are** genuinely closer to the next session's turning
points than a stranger's levels. Not one of 200 shuffles beat them. The effect is
real and reproducible.

**And it is far too small to use.** The day's extreme lands a median **47.4 bps**
from the nearest prior-day level, against **50.8 bps** for a stranger's — a
sharpening of **3.4 bps, or 6.6%**. On a level already sitting half a percent
away from the turn, knowing it is the *real* prior-day high rather than an
arbitrary price buys you three basis points of precision.

The pre-registration required ≤ 0.90. The observed 0.934 fails that, and p = 0.005
also fails the corrected 0.00208 gate. **Detectable and immaterial — which is
exactly the distinction the two-part bar was built to make.**

Gamma levels alone show nothing at all (0.975, p = 0.29).

---

## 4. The answer to the question asked

> *Can gamma, previous-day value areas and PDH/PDL be used to predict pricing,
> levels and moves on the following day?*

**No, on this evidence.**

- **As reaction levels:** the five testable ones behave like coins at touch
  (44.8% to 51.5%). The three gamma levels are touched too rarely to test.
- **As pivots:** prior-day high and low do attract the next day's turning points
  measurably, and the size of it is 3.4 bps.
- **As containment boundaries:** the question is not answerable, because the
  statistic that appears to answer it is fixed by distance alone.

**They describe where the market has been. They do not measurably move where it
goes next.**

That does not make them useless, and it does not contradict how this project
already uses them. A prior-day high is a real price at which real business
happened, and it is a reasonable place to hang a confluence map or an expected
range. The claim it will not support is the one in the question — prediction.

### What is not ruled out

- **Levels conditioned on context** rather than tested unconditionally. This
  screen asked whether a touch reacts on average. Whether a touch reacts
  differently after a trend day, or on the third test, is a different question —
  and one that needs its own pre-registration, because it is exactly the kind of
  conditioning that manufactures effects if it is done after seeing this table.
- **The walls**, which remain untested rather than cleared. At a 7–12% touch
  rate, settling them needs roughly 5,000 sessions of chains.

---

## 5. Where the ledger stands

| screen | sample | outcome |
|---|---|---|
| pullback, QQQ screen | 1,418 sessions, 16 variants | closed, 0 of 16 |
| ORB + VWAP, QQQ screen | 1,418 sessions, 16 variants | closed, 0 of 16 |
| OR height, promoted | 1,418 + 1,256 held out, 4 variants | closed, 0 of 4 |
| European session, descriptive | 21 NQ sessions | same market, worse terms |
| regime forecastability, price | 1,418 sessions, 14 combinations | closed, 0 of 14 |
| discretionary strategy, mechanised | 1,417 sessions, 8 variants | closed, 0 of 8 |
| regime forecastability, gamma | 336 sessions, 4 combinations | closed, 0 of 4 |
| **levels, predictive** | **1,414 + 336 sessions, 13 tests** | **closed, 0 of 13** |

Reproduce: `python3 scripts/orderflow/levels_predictive.py`.
Detail in `reports/levels_predictive_A.csv` and `_B.csv`.
