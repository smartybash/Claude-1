# Do prior-day levels and gamma levels predict the next session? — declared before running

Tests whether the three named families — **dealer gamma levels**, **prior-day
value area**, and **prior-day high/low** — do anything to the following
session's price beyond what their distance from price already explains.

Descriptive. No rule is traded. Sealed NQ days are not read.

---

## 1. The trap this is built around, and the test it disqualifies

The best-known result in this area is on this project's own record: next-day
**high stayed below the call wall 90%** of the time, low stayed above the put
wall 73% (`reports/gamma_backtest_findings.md`). That looks like strong evidence
of resistance. It is not evidence of anything, and the reason needs stating
before any new number is produced.

**A containment test is degenerate.** Ask whether today's high stays below a
level sitting 2% above yesterday's close, and the answer is entirely fixed by
P(today's high < +2%). It does not matter what the level is *called*. A call
wall, a put wall, a random price and the number 47 all score identically at the
same distance. The 90% figure measures "QQQ rarely rises 2% in a day", which is
true, and says nothing about dealers.

There is no placebo that fixes this, because a distance-matched placebo gives a
*mathematically identical* answer, not merely a similar one. **So the containment
test is not being run.** That is the finding, declared in advance.

What is left are two designs that are not degenerate, because each one removes
distance rather than being confounded by it.

---

## 2. The eight levels

All are computed from the **prior session** and are known **before the open**, so
every one clears the causality gate by a wider margin than any intraday
predictor.

| family | levels |
|---|---|
| prior-day extremes | **PDH**, **PDL** |
| prior-day value area | **VAH**, **VAL**, **POC** |
| dealer gamma | **call wall**, **put wall**, **gamma flip** |

- **Value area**: standard 70%-of-volume region around the point of control,
  built from the prior session's 1-minute price/volume histogram.
- **Gamma levels**: from `data/gex_history.jsonl`, chain as-of the prior close,
  strict one-session alignment — no stale rows, no forward fill.

---

## 3. Test A — reaction at touch (primary)

**Conditioning on a touch removes distance entirely.** Only sessions where price
actually reached the level are counted, so "price rarely travels that far" can no
longer do the work.

- **Touch** = the first 1-minute bar whose [low, high] contains the level.
- **Approach side** = the side price was on in the bar *before* the touch.
- **Reaction** = K minutes after the touch, is price back on the approach side?
- **K = 30 and 60 minutes.**

**Null = 50%.** For a random walk started at the level, either side is equally
likely. This is the correct null and it needs no placebo.

8 levels × 2 horizons = **16 tests**.

---

## 4. Test B — do the session's turning points cluster at these levels?

The other thing a level could do is act as a pivot: the day's swing highs and
lows land on it more often than chance.

- **Turning points** = the session high and the session low.
- **Statistic** = distance from each turning point to the nearest level in the
  set, in bps.
- **Placebo** = the *same level set taken from a different, randomly chosen
  session*, expressed as relative offsets from that session's prior close and
  applied to today's. This preserves the geometry of a level set — how many
  levels, how far apart, how far from the close — while destroying the date
  correspondence. 200 shuffles.

**If real levels are no closer to the day's turning points than a stranger's
levels, the set is decorative.**

8 levels × 1 = **8 tests**. Test A + Test B = **24 tests**.

---

## 5. Pass criteria, fixed now

| test | criterion | threshold |
|---|---|---|
| A | reaction rate | **≥ 55%** |
| A | p-value | **< 0.00208** (0.05 Bonferroni over 24) |
| A | touches | **≥ 100** for the level to be eligible at all |
| B | median distance, real ÷ placebo | **≤ 0.90** (real levels at least 10% closer) |

The 55% bar is deliberate. A level that repels 52% of the time is real and
useless: at a 1:1 stop/target with 0.667 bps cost against a typical 20 bps risk,
breakeven is already above 51.5%. **55% is roughly where a touch becomes
tradeable**, and that is the standard being applied rather than mere
detectability.

---

## 6. Sample

| | |
|---|---|
| price levels (PDH, PDL, VAH, VAL, POC) | **1,418** QQQ sessions, 2021-01-04 to 2026-08-31 |
| gamma levels (walls, flip) | **336** sessions, all six years now present |

The two groups are reported **separately and never pooled** — they have different
sample sizes and different provenance, and a combined figure would be dominated
by the price levels.

2022 was fetched today specifically to close the gamma year gap, so the
year-stability rule is applicable to both groups for the first time.

---

## 7. What each outcome means, fixed now

- **Nothing clears.** The levels are chart furniture: real prices that describe
  where the market has been, with no measurable effect on where it goes next.
  Combined with the degeneracy of the containment test, that would close the
  levels line as a source of prediction — while leaving them perfectly valid as
  a *description* of prior-session structure, which is how the confluence map
  already uses them.
- **Something clears.** Then that specific level, at that specific horizon, has
  an effect that distance does not explain — and it becomes the first thing in
  this project worth building a pre-registered rule around.

**A reminder of the standing asymmetry:** this is a descriptive screen, so a
pass here licenses a pre-registered strategy test, not a strategy.

---

Committed before `scripts/orderflow/levels_predictive.py` was run.
