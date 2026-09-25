# Initial Balance by Rejection — declared before running

Sealed NQ days are not read. 2016–2020 stays sealed.

## 1. The geometric identity that governs this whole family

`close_10:30` always lies **inside** `[IBL, IBH]`. So the distance from it to the
expected break level and the distance to the opposite level sum to **exactly the
IB range**:

```
d_expected = EZ% x IB_range          d_opposite = (100 - EZ)% x IB_range
```

For a **driftless random walk** started at `close_10:30` between two absorbing
barriers, the probability of touching the expected side first is

```
P = d_opposite / (d_expected + d_opposite) = (100 - EZ)%
```

**The random-walk break probability is simply 100 minus the Ending Zone.** It
requires no market behaviour, no rejection, no momentum and no participants.

**Measured on the actual data, before any break rate was computed:**

| bucket | QQQ n | mean EZ | **random-walk baseline** |
|---|---|---|---|
| **0–25%** | **772** | **10.5%** | **89.5%** |
| 25–50% | 400 | 35.4% | 64.6% |
| 50–75% | 181 | 60.6% | 39.4% |
| 75–100% | 65 | 83.1% | 16.9% |

**The claimed 86% sits BELOW the 89.5% that a coin produces in that bucket.**
If the break rate comes in near 86–90%, the correct reading is not "86% edge" but
"the Ending Zone is a restatement of how close price already is to the level".

**So 50% is not the benchmark and will not be used as one.** Every break rate is
reported against its own bucket's `(100 − EZ)` baseline, computed per session and
averaged, and the *excess over that baseline* is the quantity of interest.

The random-label control requested is also run, but it is the weaker of the two:
shuffling bucket labels destroys the distance information that is the entire
confound, so it cannot detect this problem. The geometric baseline can.

## 2. Definitions, exactly as specified

- **IB** = 09:30–10:30 ET. **IBH/IBL** = high/low of that window.
- **High formed first** = the bar making IBH precedes the bar making IBL.
  Sessions where both fall on the same bar are **dropped** (order undefined).
- **Expected break side** = the side *opposite* the extreme that formed first —
  Low first → expect UP; High first → expect DOWN.
- **EZ** = `|close_10:30 − expected_break_level| / IB_range × 100`.
- **Break** = a post-10:30 bar trading beyond IBH or IBL. First one wins; a bar
  breaching both is recorded as unresolvable.

## 3. Stages and burden

| stage | tests |
|---|---|
| 1 — break rate by bucket, QQQ + NQ | 8 |
| 2 — 0–25% bucket by year, QQQ | 6 |
| 3 — mechanical trade, 4 targets × 2 instruments | 8 |
| **total** | **22** |

**Bonferroni α = 0.05 / 22 = 0.00227**, two-sided z = 3.047.

### Minimum detectable difference

| test | n | MDE vs baseline |
|---|---|---|
| **QQQ 0–25% break rate** | **772** | **±4.3 points** |
| QQQ 25–50% | 400 | ±7.4 points |
| **NQ 0–25% break rate** | **15** | **±29.6 points — USELESS** |

**The NQ tick set has 36 usable sessions total and 15 in the headline bucket.**
It cannot distinguish 86% from 60%. It is reported for completeness and **no null
or positive from NQ will be treated as evidence either way.** Stage 2 by year is
QQQ only, because NQ spans two months.

## 4. Stage 2 stability requirement, as specified

Same direction in **≥5 of 6 years**, **≥100 observations per bucket-year**. The
0–25% bucket averages ~129/year, so it qualifies; the other three buckets do not
and will be reported without a stability claim.

## 5. Stage 3 — the mechanical trade

- **Long:** Low first, EZ 0–25%, enter on first break of IBH.
- **Short:** High first, EZ 0–25%, enter on first break of IBL.
- **If the opposite side breaks first, no trade** — the stop level was violated
  before entry. Declared here rather than left ambiguous.
- **Stop:** the other side of the IB. So **risk ≈ the full IB range**.
- **Targets:** 1R, 2R, 3R, and hold-to-close.
- Honest fills (`max(trigger, bar open)`), **entry bar excluded** from the exit
  search, **2 NQ points round turn** (0.667 bps).

**The random-walk benchmark for the trade is 1/(1+M)** — 50% at 1R, 33.3% at 2R,
25% at 3R. Note this is a *different* benchmark from the break rate: the break is
near-certain by geometry, but the trade then needs a full IB range of profit
before giving back a full IB range. **A high break rate and a negative expectancy
are entirely compatible**, which is the question Stage 3 exists to answer.

## 6. Committed in advance

If the break rate matches `(100 − EZ)` within the MDE, the finding is that the
Ending Zone measures proximity, not rejection, and that will be stated plainly.

Committed before `scripts/orderflow/ib_study.py` was run.
