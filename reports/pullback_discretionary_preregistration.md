# A public discretionary NQ strategy, mechanised — declared before running

Committed before `scripts/orderflow/disc_pullback.py` was run. Sealed NQ days
are not read at any point; this screen never opens the NQ tape.

---

## 1. The claim being tested

A publicly posted discretionary method, reported by its author as:

| | |
|---|---|
| win rate | **77%** |
| reward : risk | **1.87** |
| profit factor | **6.39** |
| trades | **31**, January 2024 |
| method | manual TradingView bar replay |

### What that claim actually asserts

For a driftless random walk with a stop at 1R and a target at *M*R, the
probability of touching the target first is **1/(1+M)**. At M = 1.87 that is
**34.8%**.

So the reported 77% sits **42.2 percentage points above the random-walk rate**.
On n = 31 that is z = (0.77 − 0.348)/√(0.348·0.652/31) = **4.9**, a five-sigma
claim from 31 manually replayed trades with no fill model.

The internal arithmetic is at least consistent — 77% at 1.87 R:R implies a
profit factor of (0.77 × 1.87)/0.23 = **6.26** against the 6.39 reported — so
the numbers were not invented independently of each other. That makes them
worth mechanising rather than dismissing on arithmetic alone.

### The prior

Bar-replay backtesting has a well-known failure mode: the replay shows the bar
forming, and a discretionary operator decides entry and exit while already
seeing where the bar is heading. That is not a fill model, it is an oracle. The
mechanical version removes it. **If the mechanised rule lands near the
random-walk rate, the reported figure was method, not market**, and this
document commits in advance to saying so plainly.

---

## 2. The three non-mechanical components, as specified by the user

These definitions are used **as given**. Cleaner substitutes are not permitted;
the object of the test is their rule, not an improved one.

### Session and timing

- Decision window opens at the **US cash open** and closes **90 minutes later**.
- All values computed from data **at or before the decision bar**.
- **Entry bar excluded from the exit search**, as in the existing pipeline.
- Both trend definitions require the 15-minute opening range, so no entry is
  possible before **09:45 ET**. The effective entry window is **09:45–11:00**.
- Positions still open at the 90-minute mark are **closed there**. The rule says
  trading stops; this fixes what happens to an open position, and the choice is
  declared rather than left to the code.

### Trend, two candidates

- **T1** — long bias if the first 15-minute bar closes **above the prior session
  VWAP**, short if below. **Fixed at the end of that bar, never revised.**
- **T2** — long bias if price is above the session open by **≥ 0.5 × the
  15-minute opening range height**, short if below by the same amount,
  **re-evaluated every bar**. Between the two thresholds the bias is neutral and
  no entry is permitted. A bias flip voids any armed setup.

### Pullback and entry

- A pullback is a retracement **against the bias** of at least the **retracement
  floor** and **no more than 0.75** of the move since the session open, measured
  from the extreme reached so far.
  - move = |extreme so far − session open|, in the bias direction, must be > 0
  - retracement = |extreme so far − current price|
  - armed when **floor ≤ retracement/move ≤ 0.75**
  - retracement/move > 0.75 **voids** the setup until a new extreme is made
- Entry triggers on the **first bar that closes back in the direction of the
  bias** after that condition is met. Mechanised as: **close > open** of that bar
  for a long bias, **close < open** for a short.
- **Enter at the next bar's open, not at the trigger price.**

### Stop

Stop distance = the **maximum** of three quantities:

1. **1.0 × ATR(14) of one-minute bars.** True range, the standard definition,
   shifted one bar so the forming bar is never used.
2. **Distance to the pullback swing extreme + 2 ticks.** The swing extreme is
   the furthest price against the bias reached during the pullback.
3. **Distance to the nearest prior session level on the protective side.**

**Prior session level = prior session high, low, close, VWAP.** Four fixed
prices, no discretion, nearest one on the protective side. If no level lies on
the protective side, that component is 0 and does not bind.

### Target, two variants

- **P1 structural** — exit at the **nearest of those same four levels lying in
  the profit direction**. If none lies beyond entry, exit at **2R**.
- **P2 control** — exit at **3R**.

**If P1 does not beat P2, the levels story is decorative, and this document
commits in advance to stating that.**

### Daily stop rule

After any closed trade with profit ≥ **10 NQ points equivalent**, stop for the
session. Otherwise continue until **cumulative** session profit reaches that
threshold or the 90-minute window expires.

**Reported both with and without.** It changes the equity curve and the drawdown
— which is where the most impressive reported number comes from — but it
**cannot change per-trade expectancy**, and that is to be confirmed in the
output rather than asserted here.

---

## 3. Grid — 8 variants, the rest of the budget unspent

| | |
|---|---|
| trend | T1, T2 |
| target | P1, P2 |
| retracement floor | 0.33, 0.50 |

2 × 2 × 2 = **8 variants.** No other parameter is swept.

---

## 4. Sample, and the two fidelity gaps in it

| | |
|---|---|
| instrument | QQQ, 1-minute, `data/intraday_long/QQQ_1m.parquet` |
| sessions | **1,418** — 2021-01-04 to 2026-08-31 |
| years | 2021–2026, six, as the rejection rule requires |

NQ point quantities are mapped to QQQ by the project's standing convention — an
NQ point as a fraction of a ~30,000 index level, applied to QQQ's price. So
**2 ticks = 0.5 NQ points = 0.167 bps**, **10 NQ points = 3.33 bps**, **cost =
2 NQ points = 0.667 bps round turn**.

Two gaps are declared now rather than discovered later:

1. **Prior session VWAP is an RTH VWAP.** `QQQ_1m.parquet` holds 09:30–15:59
   only. An NQ trader's "prior session VWAP" would almost certainly be an
   overnight-inclusive figure. There is no ETH data for QQQ in this repository,
   so the RTH VWAP is what T1 and the level set use. This is a substitution, not
   an equivalence.
2. **QQQ is not NQ.** They track the same index and the tick and cost scaling is
   handled, but the instruments are not identical. The user's own framing
   already anticipates this: a result materially above the random-walk rate
   earns verification on the 21 NQ tick sessions. A null does not.

---

## 5. What is reported

**Trade counts and session counts before any performance number.**

- **Win rate against the random-walk rate implied by each variant's realised
  reward-to-risk**, not against 50%. RW rate = 1/(1+M) where M = mean winning R
  ÷ mean |losing R|, measured per variant. Reported alongside the nominal rate
  implied by the specified target, so the difference between the two is visible.
- Expectancy in R after costs; profit factor; per-session t.
- **Split by year**, all six.
- **Honest fill beside the naive fill.** Honest = entry at the next bar's open
  and gap-aware stop fills. Naive = entry at the trigger bar's close and stops
  filling exactly at the stop price. The difference is the correction the manual
  replay would not have applied.
- **Entry lookahead check** — entries at or before the opening-range close.
  Should be structurally zero; counted, not assumed.
- **Ambiguous bar rate** — bars touching both stop and target.
- **With and without the daily stop rule**, both.

---

## 6. Rejection criteria, fixed now

The standing set, unchanged from the three prior screens:

1. Expectancy ≤ 0 in R after costs.
2. Fewer than 15 sessions producing a trade.
3. Profit factor < 1.15.
4. Removing the top 1% of trades leaves total R ≤ 0.
5. Positive in fewer than 4 of the 6 calendar years.
6. **Per-session t ≤ 3.** With 8 variants the Bonferroni figure is about t > 2.7,
   which is below 3, so **t > 3 governs.** The bar does not move down mid-project.

And the criterion specific to this claim:

7. **Win rate not materially above the variant's own realised random-walk rate.**
   This is the test the reported 77% actually has to pass.

---

## 7. The comparison this is for, and both of its outcomes

- **If the mechanical version lands near the random-walk rate**, the reported
  figure was **method rather than market** — bar-replay discretion, not edge —
  and it will be said plainly, with the size of the gap between the mechanised
  rate and 77% stated.
- **If it lands materially above the random-walk rate on the full sample**, that
  is the **first result in this project worth verifying on the 21 NQ tick
  sessions**, and that verification becomes the next step rather than a claim.

Either outcome is reportable. Neither is assumed here.

---

Committed before the script was run.
