# Findings — what was tested, what failed, what is left

Written 2026-09-11. This is the record of record: if the session is gone, this
file is what survives.

---

## Bottom line

**There is no validated setup in this repository.** Nine strategies have been
mechanised and tested. All nine were rejected. Nothing here should be traded
with real size on the strength of a backtest.

The last one to fall — the value-area fade — appeared to work for most of a
week. It did not. Its apparent edge was a **lookahead bug** in the entry price,
and that bug was also in the original `backtest_va_fade.py` result that
everything else was built on.

---

## The lookahead, in one paragraph

The rule takes the trade when a 5-minute bar **closes back through** a level.
Every version of the test then filled the entry **at the level** — a price from
earlier in that same bar. Both facts cannot be known at once: when price touches
the level, the bar has not closed and the rejection has not happened. The
backtest was buying at a price that the rule's own information had not yet
identified as a buy.

Removing it (`backtest_aplus4.py`) collapses the result:

| stop 0.15% (44 NQ pts) | n | win | mean R | PF | t |
|---|---|---|---|---|---|
| entry at LEVEL (lookahead) | 400 | 50% | **+0.628R** | 2.26 | **+4.68** |
| entry at CLOSE (realistic) | 395 | 45% | −0.047R | 0.91 | −0.66 |
| resting LIMIT, every touch | 500 | 20% | −0.513R | 0.36 | −10.30 |
| CLOSE + bar delta ≥10% | 337 | 48% | −0.049R | 0.90 | −0.73 |

**Any result in this repo that enters at a level price on a bar-close condition
is suspect and must be re-derived before it is believed.**

---

## The nine rejected

| Strategy | Script | Result |
|---|---|---|
| ICT prior-day sweep + reclaim | `backtest_ict_sweep.py` | −0.19R, t=−2.78, 63% stop-out |
| NWOG weekend gap fade (1,351 gaps, 27y) | `backtest_nwog.py` | −0.34R, t=−13.2 |
| 15-min ORB + FVG | `backtest_orb15.py` | PF 1.01; the imbalance filter made it worse (0.87) |
| Initial Balance breakout (full sweep) | `backtest_initial_balance.py` | 98% break rate, no configuration pays |
| VWAP retest | `backtest_vwap_retest.py` | +0.049R — noise |
| MAGS/SMH/IGV breadth veto | `backtest_breadth_filter.py` | backwards: blocked signals won 72%, kept won 62% |
| Value-area fade | `backtest_va_fade.py` | +0.334R / t=+3.80 — **invalidated by the lookahead** |
| VA fade + wide Initial Balance | `backtest_ib_regime_filter.py` | +0.482R / PF 2.51 — **same lookahead** |
| Fixed-level fade, all variants | `backtest_aplus*.py` | flat to negative under every honest entry |

The last row covers: prior-day VAH/VAL/High/Low, 20-session composite
VAH/POC/VAL, naked POCs; both sides; stop widths from 44 to 206 NQ points; time
window; wide-IB filter; session-CVD filter; trigger-bar delta filter; and three
entry conventions. 523 sessions. Nothing survived.

The final entry attempt — wait for the rejection bar to close, then rest a limit
back at the level for K bars — is in `backtest_aplus5.py`. Best of sixteen cells
searched was +0.196R at t=+1.68, which is not significant before accounting for
having searched sixteen cells. Its out-of-sample half is **−0.235R, t=−2.02**.

---

## Two findings that did survive

Both are negative results, and both are worth more than another failed setup.

**1. Fading fixed levels blindly loses money, reliably.**
A resting limit at prior-day VAH/VAL/High/Low, filled on every touch:
**−0.513R at t=−10.30 over 500 trades.** This is the most statistically solid
number in the whole repo. Those levels are not support and resistance in the
way they are usually taught.

**2. The rejection bar carries real information — it just cannot be monetised
on 5-minute bars.**
Going from "every touch" (−0.513R) to "only touches where the bar closes back
through" (−0.047R) recovers **0.47R per trade**. The poke-and-close-back pattern
genuinely separates the touches that hold from the ones that do not. By the time
the bar closes and you can act, the price is gone.

That is a precise diagnosis: **the read is right, the execution window is the
problem.** It is also the one gap that tick-level order flow could plausibly
close — at the tick you may see absorption *while* it happens instead of after
the fact. That claim cannot be tested on 5-minute bars.

---

## Data limitations that bound all of the above

- **QQQ, not NQ.** 523 sessions of QQQ 5-min RTH (2024-07 to 2026-07) is the
  only intraday history deep enough to test on; NQ has 11 days. Same index,
  but tick size, spread and slippage differ.
- **No aggressor tag.** QQQ bars carry no bid/ask split, so per-bar delta is a
  proxy — `((close-open)/(high-low)) * volume`. Every flow-filtered number
  inherits that approximation. Real CVD and real footprint imbalance have not
  been tested at all.
- **RTH only.** No overnight/Globex high and low, which are part of the fixed
  level set in live use.
- **No commissions or slippage** are modelled. At the R:R levels involved this
  is small, but it is not zero.

---

## The open drive — tested, and rejected too

After the level-touch families were exhausted, the opening sequence was tested
(`backtest_open_location.py`, `backtest_open_drive.py`). Taking the direction of
09:30-10:00 at 10:00, stop at the opposing IB extreme, target 2R, produced
+0.099R / PF 1.20 / t=+1.84 over 509 sessions — the only adequately-sampled
positive in the programme.

It was pre-committed to three checks: hold in both date halves, and strengthen
on wide-gap and wide-IB days if the momentum mechanism is real. It failed all
three.

| split | n | mean R | t |
|---|---|---|---|
| first half 2024-07 → 2025-07 | 247 | +0.021R | **+0.28** |
| second half 2025-07 → 2026-07 | 262 | +0.172R | +2.31 |
| gap < 0.25 ATR | 189 | +0.067R | +0.77 |
| gap 0.25–0.50 ATR | 75 | +0.047R | +0.35 |
| gap ≥ 0.50 ATR | 80 | +0.146R | +1.08 |
| narrow IB | 168 | +0.059R | +0.57 |
| wide IB | 168 | +0.084R | +1.01 |

The edge exists in one date half and not the other, shows no monotonic response
to gap size or IB width, and the delta filter adds nothing (+0.099R → +0.104R).
Median trade is **−0.38R**, max drawdown 16.8R, worst streak 8. Down-drives
carry it (+0.181R, t=+2.24) and up-drives are flat (+0.024R, t=+0.34), which on
a rising two-year sample is another warning rather than a feature.

**Verdict: fitted artifact, not an edge.** Ten strategies tested, ten rejected.

---

## The base rates — the one genuinely usable output

These are not a trade. They are context, and they are solid on 509 sessions.

| | |
|---|---|
| days opening **outside** prior-day value | **68%** |
| of those, price returns **into** value same day | **63%** |
| ...and having returned, reaches the **POC** | **74%** |
| return rate when the gap is **< 0.5 ATR** | **70%** |
| return rate when the gap is **≥ 0.5 ATR** | **40%** |

The gap-size split is the real finding: a **30-point swing** in return probability
off a classifier that is known at 09:30, costs nothing, and needs no indicator.
Half an ATR or more from the value edge and the day stops being a rotation.

---

## What is left

**ATAS Market Replay, Ticks + DOM mode, 20–30 sessions, one setup, executions
logged to the Trading Journal.**

This is not a consolation prize. It is the only way to test the one claim that
the bar data cannot reach: whether tick-level order flow gives an entry that
5-minute bars cannot. Everything else has been falsified.

Rules for it to be worth anything:
1. One setup at a time. No switching mid-sample.
2. Log every trade, including the ones you skipped and why.
3. Ticks + DOM mode — generated-tick modes do not reproduce absorption.
4. 20–30 sessions before drawing any conclusion.
5. If you cannot execute the trigger cleanly under live speed, it is not an
   edge you own, regardless of what the sample says.

---

# Round two: the recorded tape (2026-09-09, 2026-09-10)

954,203 trades with aggressor tags, recorded out of ATAS by `atas/L2Recorder.cs`.
This is the first data in the project that bar files cannot produce.

## Data quality — checked before anything was built on it

| Check | Result |
|---|---|
| Aggressor split | 50.24/49.76 and 50.14/49.86 buy/sell. Correct: every contract bought is sold, so a full day must be near even. The flag is real. |
| Clock | **UTC.** The one-hour CME maintenance halt sits at 21:00–22:00 in both files; that halt is 17:00–18:00 New York. RTH is therefore **13:30–20:00** in these files. |
| Daily volume | 486k and 544k contracts — matches real NQ. Nothing is being dropped. |
| Continuity | Largest non-halt gap between trades is 47 seconds. No holes. |
| **Price grid** | **Broken: 5.00 points, not 0.25.** Only 61 and 94 distinct prices across ranges of 300 and 465 points. |

The price grid is a recording-side defect, not a market fact. The chart's price
step was set to 20 ticks, and ATAS applies it before the data reaches the
indicator. Delta and volume survive it; price resolution does not. **The next
recording must be made with the price step at 1 tick.**

## What was tested, and what happened

Two sessions gapped 370 points apart, so not one prior-day level was touched on
the second day. Level work is impossible on this sample; everything below is
microstructure, where the event count is in the hundreds rather than the twos.

**The absorption 2×2 — all four cells negative.** Heavy aggression that fails to
move price, held two minutes, at 30-second windows: −3.34 pts fading absorbed
buying, −2.69 fading absorbed selling. Going with working aggression also loses.
The delta dose-response is flat and its sign flips between the two days. There
is nothing here.

The "no progress" filter was also barely a filter: on a 5-point grid, 82% and
74% of 30-second windows moved 5 points or less, and a third moved zero. Fixing
the price step will sharpen this test as much as it sharpens anything.

**Block prints — nothing, and barely present.** The top 0.1% of prints means
size ≥ 9. This feed is 96.5% singles and blocks carry 2% of volume, so there is
almost no institutional size to detect in the first place.

**CVD divergence at 60-minute extremes — the one cell that cleared the bar, and
it did not survive audit.** As swept: +8.32 pts, 74% win, n=78, t=+5.12. Three
attacks:

| Attack | Result |
|---|---|
| Overlap | The 78 "observations" were 21 independent episodes counted 2–3 times each. De-overlapped: **+3.48 pts, t=+1.00.** |
| Per day | 09-09 **−3.67 pts**, 09-10 +6.33. The two days disagree once the duplication is removed. |
| **Control** | Taking every local extreme with **no CVD condition at all** pays +3.87 pts — *better* than +3.48. CVD contributed nothing. |
| Concentration | 3 of 21 trades supply 95% of the profit. |

So the finding was overlap inflation plus one day plus mean reversion at local
extremes wearing an order-flow costume. It joins the rejected pile.

`H0` is worth keeping though: the sign of the last window's move, held forward,
is negative at **every** horizon tested from 30 seconds to 20 minutes. This tape
mean-reverts intraday. Nothing survived the significance bar after de-overlapping,
but the sign is consistent, and it is the opposite of what a breakout trader
assumes.

## Why two sessions could never have settled this

Per-trade standard deviation is **15.9 points ($318)** at roughly 10 independent
signals per session. What that buys, at the |t| ≥ 3.0 bar this project uses:

| True edge per trade | Trades needed | Sessions |
|---|---|---|
| 2 pts | 568 | 54 |
| 3 pts | 252 | 24 |
| 5 pts | 91 | 9 |
| 8 pts | 35 | 3 |

Three sessions can only resolve an edge of 8 points or larger. An 8-point-per-
trade intraday edge does not exist; if it did it would have been arbitraged.
**Twenty sessions is the point at which a realistic 3-point edge becomes
detectable**, and that is the number to collect.

## The collection spec

1. **Price step = 1 tick** on the recording chart. Non-negotiable — it is the
   one defect that degrades every test.
2. **Send the `L2_*.csv` depth files.** The status file shows 4,089,447 depth
   updates were recorded and none of them have been analysed, because only the
   tape files were sent. Resting size, and whether it is pulled or replenished
   as price arrives, is the entire reason the recorder was built and remains
   completely untested.
3. **Twenty sessions**, Ticks + DOM.
4. Sessions with a **prior-day level in range** are worth more than quiet ones,
   because level behaviour is the open question the gap between these two days
   made untestable.

---

# Round three: four clean sessions with depth (2026-09-01 to 09-04)

The first recordings that support the measurement the whole exercise was built
for. 6.4M depth rows and 1.7M aggressor-tagged trades across four cash sessions.

## Data quality

| Check | Result |
|---|---|
| Price grid | **0.25 tick.** Fixed. 793–1,555 distinct prices per session. |
| RTH coverage | **100%** of 13:30–20:00 on all four days, no gap over 5 seconds. |
| Snapshot rate | median 268 ms, p99 ~400 ms. Matches the 250 ms throttle. |
| Book integrity | **zero crossed or locked books.** Spread median 2 ticks, p95 3. |
| Aggressor split | 50.6/49.4, 50.4/49.6, 50.3/49.7, 47.7/52.3. Sound. |
| **09-01 duplication** | **Recorded twice.** The clock steps from 19:59:59.999 back to 13:30:00.000 at exactly the halfway row, in both files. Deduplicated in analysis; the recorder now writes `_run2` instead of appending. |
| **Ladder reach** | **2.25 points, median.** Ten levels at a 0.25 tick. This is the binding limitation. |

The ladder reach is the one number that constrains what can be asked. Resting
size only becomes visible once price is already within about two points, so
"watch a level build or evaporate from ten points away" is not answerable with
this configuration. Whether ten levels is the recorder's cap or the feed's is
not decidable from the files, since exactly ten always arrive: **set depth
levels to 50 and record five minutes.** If ten still arrive it is the exchange
feed (CME distributes market-by-price ten deep) and the question is closed.

## What the two files together revealed

At the touch, **filled volume exceeds cancellation by about 5 to 1** — 207k
contracts traded against 43k added or pulled, and the same ratio on all four
days. Size at the best bid and offer mostly disappears because it is traded,
not because it is withdrawn. That is worth knowing: it argues against reading
disappearing size at the touch as a spoof or a fake.

## Three more hypotheses tested and rejected

**Order book imbalance.** The standard measure, `(bid size − ask size) /
total`, over ten levels. Dose-response across deciles is noise with no trend
and no consistent sign. At the extremes, de-overlapped: **+0.09 to +0.26 points
gross, t = +0.7 to +1.5** — below the bar, and a fraction of the half-point
spread it would have to clear. Net of two points it is −1.7, which is simply
the cost.

**Absorption, properly instrumented.** Resting size decomposed into what was
filled and what was cancelled, so "the bid took supply and refilled anyway" is
computed rather than eyeballed. Gross **+0.25 points at t = +1.50** on 30
seconds, decaying to nothing by five minutes.

**Cancellation alone**, with trading stripped out entirely: −0.14 points,
t = −0.91. Nothing.

All three are negative on the same four sessions where the control — a random
long — earns +0.13 to +1.19 points over the same horizons. The signals are not
beating a coin flip, let alone the spread.

## Where this leaves the search

Every order-flow hypothesis tested at horizons from 10 seconds to 5 minutes has
produced a gross edge under 0.3 points against a round-trip cost of 2. The
pattern across three rounds is consistent and worth stating plainly: **the
short-horizon microstructure signals in this data do not clear costs.** That is
a real finding, not a failure to look hard enough — the imbalance and
absorption tests are the two most commonly claimed edges in order flow, and
both were measured directly rather than argued about.

What has not been tested, and now can be, is level behaviour: these four
sessions do contain prior-day levels in range, unlike the gapped pair in round
two. That is the next test and the last one the current configuration supports.
