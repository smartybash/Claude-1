# Pullback continuation, grid 2: corrected stop, declared before running

Supersedes `pullback_preregistration.md` for the stop definition only. Every
trading constraint is unchanged. Committed before the corrected code runs.

---

## What changed, and the honest status of each change

**1. The stop is anchored to volatility, not to a tick count.** *Not
data-informed.* Grid 1 fixed the trigger four ticks above the pullback extreme
and the stop four ticks below it — both offsets from the same price — which
pins risk to exactly 2.00 points on every trade regardless of session,
instrument or the size of the move being retraced. Cost was 2.00 points, so
cost was 100% of risk and a 1.0R winner netted zero. That was decidable by
arithmetic before any data was read.

```
stop_distance = max(STOP_MIN_TICKS × 0.25, STOP_ATR × ATR)
stop          = pullback extreme − dir × stop_distance
ATR           = mean high−low of the last 20 completed 1-minute bars
```

ATR is a rolling statistic over bars already closed, so it is known at the
trigger print.

**2. `EXC` fixed at 0.5, freeing a grid axis.** **This IS data-informed and is
recorded as such.** In grid 1, `EXC = 1.0` produced trades on only 8 and 4
sessions against the 15-session minimum, while `EXC = 0.5` produced 15 and 9. I
fixed it at 0.5 because the other value could not generate enough sessions to
test — a choice made *after* seeing discovery trade counts.

That is a real, if small, use of the discovery set, and it is not the same kind
of change as the arithmetic fix. It is logged in the ledger below.

**3. The freed axis becomes `STOP_ATR`.** Follows from 1 and 2.

---

## Ledger: what the pullback family has now consumed

| grid | what was searched | outcome |
|---|---|---|
| 1 | OR_MIN × EXC × TGT_R, 12 variants | all rejected; specification unusable |
| 2 | OR_MIN × STOP_ATR × TGT_R, 12 variants, EXC fixed at 0.5 from grid 1 counts | this run |

**The pullback family has now consumed two grids on the discovery set**, 24
variants in total, with one parameter carried forward on the basis of discovery
trade counts. The sealed days remain untouched, and that is what protects the
eventual test — but discovery is being spent, and this is the record of it.

---

## The arithmetic check I failed to do last time

**Measured ATR across the 20 discovery sessions** (20-bar, 1-minute):

| p10 | p25 | median | p75 | p90 |
|---|---|---|---|---|
| 10.11 | 13.97 | **19.32** | 27.05 | 37.73 |

My earlier estimate of "8–15 points" was wrong; it is roughly double that.
Implied stop distance:

| STOP_ATR | p10 | median | p90 |
|---|---|---|---|
| 0.5 | 5.06 | **9.66** | 18.86 |
| 1.0 | 10.11 | **19.32** | 37.73 |

**Breakeven win rate**, `p = (R + cost) / (R × (M + 1))`, cost 2.0:

| risk | 1.0R | 1.5R | 2.0R | cost/risk |
|---|---|---|---|---|
| 3 | 83.3% | 66.7% | 55.6% | 67% |
| 4 | 75.0% | 60.0% | 50.0% | 50% |
| 6 | 66.7% | 53.3% | 44.4% | 33% |
| 8 | 62.5% | 50.0% | 41.7% | 25% |
| 12 | 58.3% | 46.7% | 38.9% | 17% |

At the median stop for each variant:

- **STOP_ATR 0.5 (≈9.7 pts):** needs about 60% / 48% / 40%
- **STOP_ATR 1.0 (≈19.3 pts):** needs about 55% / 44% / 37%

**Random-walk benchmark**, `P(hit +M×R before −R) = 1/(1+M)`: **50% / 40% /
33.3%**.

So the rule must beat a coin by **3.5 to 10 percentage points** depending on
the variant — demanding but not absurd, where grid 1 demanded 30 points at
1.5R and an impossibility at 1.0R.

### Would the hit rates observed in grid 1 clear this?

Grid 1 observed **73.1% at 1.5R and 61.5% at 2.0R**. Taken at face value those
clear every cell in the table comfortably.

**I do not think they should be taken at face value, and I am saying so before
the run rather than after.** They were measured on a different trade. With a
2-point stop the 1.5R target sat 3 points away and the whole thing resolved in
seconds — that hit rate measures very short-term noise, not whether a pullback
continues. Under the corrected spec the stop is 10–19 points and the target 15
to 39, so the trade must survive far longer and travel far further. There is no
mechanism by which the old rate transfers, and the expected direction is
downward, toward the random-walk value.

**So: no, I am not predicting the observed rates will clear the new bar.** The
honest reference is the random-walk rate, and the question is whether the rule
beats it by the few points listed above.

### One more prediction, stated now

With a median target of 19 to 39 points and a 60-minute expiry, I expect
**expiry exits to be a large share of outcomes**, particularly at `STOP_ATR
1.0` with `TGT_R 2.0`. If that dominates, the variant is testing "does the move
travel 39 points within the hour", which is a different question from whether
the pullback continues. `MAX_MIN` stays at 60 as pre-registered; I am flagging
the consequence rather than tuning it away.

---

## The grid: 12 variants

| parameter | values |
|---|---|
| `OR_MIN` | 15, 30 |
| `STOP_ATR` | 0.5, 1.0 |
| `TGT_R` | 1.0, 1.5, 2.0 |

Fixed: `EXC = 0.5` (data-informed, logged above), `STOP_MIN_TICKS = 8` (a
2-point floor so a dead-quiet patch cannot recreate grid 1's fault),
`BREAK_TICKS = 2`, `PB_LO/PB_HI = 0.25/0.75`, `REJ_TICKS = 4`, `MAX_MIN = 60`,
`LAST_ENTRY = 18:00 UTC`, `HARD_FLAT = 18:30 UTC`, `COST = 2.0`,
`MAX_TRADES = 2`.

---

## Unchanged from grid 1

Rejection criteria, all five. Reporting order — **trade counts before any
performance number**. Per-session t alongside per-trade. Split-half for
stability, still flagged as weaker than the month test the sample cannot
support. Robustness at 3.0 points of cost. Sealed days excluded at
construction.

**And the same caveat: a variant that passes on 20 sessions is a surviving
candidate, not a finding.** At most two trades a session means a few dozen
trades. Survival means not yet killed.
