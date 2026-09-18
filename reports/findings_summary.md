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

## The level test

Prior-session profile (high, low, close, VAH, POC, VAL) plus the current
session's initial balance, all fixed before price arrives. Entry is a **resting
limit at the level**, filled when price trades there, and the outcome is
resolved by walking the tick tape forward one trade at a time to a stop or a
target — the convention that removes the lookahead which destroyed the earlier
level work.

Raw run: 198 touches, +6.56 points, t=+3.13 on a 20/40 stop and target. The
audit took it apart:

| Attack | Effect |
|---|---|
| Clustered levels merged | On 09-04, pdHIGH sat at 29,584.25 and pdVAH at 29,583.75 — half a point apart, the same trade counted twice. 198 touches → **131**. |
| One trade at a time | A 40-point target takes long enough that most touches overlap. 131 → **32** independent trades, t **+3.13 → +0.45**. |
| Per session | 09-02 +9.41, 09-04 −6.59. They disagree. |
| Six cells tried | No cell clears the |t| ≥ 2.9 that six attempts require. |
| Flow filters | Aggression into the level, volume, tape speed: every bucket n=10–11, |t| < 1.3. **Order flow at the touch does not separate holds from breaks on this sample.** |

**Base rate worth keeping: levels held 49% of the time** across 198 touches.
A coin flip. Every level read that claims better than that is claiming to beat
this number, and now there is a number to beat.

### This one is underpowered, not disproven — and that distinction matters

The best-behaved cell is a **15-point stop with a 30-point target: +8.52 points
net, t=+2.51 on 43 de-overlapped trades, 14.3 trades a session.** All six cells
in the grid have a positive mean.

Per-trade dispersion is 22.3 points ($446). At the six-cell bar:

| True edge/trade | Trades | Sessions |
|---|---|---|
| 8 pts | 65 | 5 |
| 5 pts | 167 | 12 |
| **3 pts** | **465** | **32** |

Three sessions can only resolve an edge of **9.9 points per trade**. The
measured +8.52 sits *below* that threshold, so this sample cannot distinguish
it from zero either way. That is the opposite situation to imbalance and
absorption, which produced +0.25 points gross against a 2-point cost and are
dead regardless of sample size.

**Twelve sessions resolves 5 points per trade; twenty resolves 3.8.** This is
the one live hypothesis left, and it is the reason to do the twenty-session run.

## Depth beyond the touch: measured, and it is worse than useless

The 50-level recording answered the open question: **the feed supplies far more
than ten levels.** Ladder reach went from 2.25 points to a **median of 12**,
5.3× further, so a level is now visible well before price arrives. Delivered
depth is variable — median 10 populated levels per side, p90 of 20, max 50 —
because the book thins with distance rather than being dense every tick.

Whether the extra depth carries information is a separate question, and it has
a clean answer. Imbalance recomputed over nested subsets of the same session,
gross and de-overlapped:

| Levels used | hold 30s | hold 60s | hold 300s |
|---|---|---|---|
| **top 1 (the touch)** | **+0.59 pt, t=+1.93** | +0.79, t=+1.52 | +1.52, t=+0.77 |
| top 5 | +0.18, t=+0.57 | +0.32 | +1.06 |
| top 10 | −0.03, t=−0.09 | −0.52 | +0.45 |
| top 25 | −0.12, t=−0.32 | −0.36 | −0.84 |
| top 50 | −0.56, t=−1.52 | −0.74 | −1.33 |

**Monotonic degradation.** Whatever information the book holds is at the touch
and nowhere else; every level added past it dilutes the signal. That is one
session and even the top-1 cell does not clear the bar, but a clean ordering
across five nested measures on the same data is a structural result, not noise.

The practical consequence: **deep book is worth recording for level-approach
work — watching size at a specific price before it is reached — and worthless
as an aggregate imbalance measure.** Those are different uses of the same file.

## What was still not being captured

**Aggressive order size.** The tape is 96.5% single-lot prints because a market
order for 50 contracts matches fifty resting one-lots and the exchange reports
each fill separately. A patient one-at-a-time buyer and a single 50-lot sweep
are identical on this tape, which is exactly why the earlier block-print study
failed with a top 0.1% of size 9. ATAS reassembles fills into a
`CumulativeTrade`; the recorder now writes them to `CUM_*.csv.gz` with first
price, last price, volume and fill count, so a sweep through several levels is
distinguishable from accumulation at one.

That file is compiled optionally, and `build.bat` retries without it
automatically, so this cannot cost the recorder if the API guess is wrong.

---

# Round four: twelve sessions, and the level edge dies

Ten recorded sessions arrived over five batches plus the four from September,
giving **twelve sessions with both tape and depth**, nine of them usable as
consecutive trading-day pairs. Depth quality is uniform: 50 levels, ~12 points
of ladder reach, 270ms snapshots, **zero gaps over five seconds and zero
crossed books in 16.8 million rows**. The recorder is finished.

## The level fade does not survive the larger sample

| | 3 sessions | 12 sessions |
|---|---|---|
| best cell (15/30) | +8.52 pt, t=+2.51, n=43 | **+2.63 pt, t=+1.81, n=232** |
| de-overlapped 20/40 | +2.32 pt | +1.25 pt |

The effect shrank by two thirds as the sample quadrupled. That is the signature
of a small-sample artifact, not an edge.

## And most of what was left was an assumed fill

A touch was registered when price came within **1 point** of the level, and the
trade was then entered **at the level** — a fill up to a point better than
anything that traded. On a gross edge of about 1.6 points, that free slippage
is not a detail, it is the result:

| stop | entry at level | entry at the traded price |
|---|---|---|
| 15 | 56.5% win, +0.03 pt | **53.7% win, −0.91 pt** |
| 20 | 59.0% win, +1.64 pt | **53.6% win, −0.54 pt** |
| 30 | 57.6% win, +2.19 pt | **53.8% win, −0.16 pt** |

Tightening the tolerance to a quarter point makes the two conventions converge,
as they must, and the surviving numbers are 53.4–56.2% win rates worth −0.75 to
+1.30 points net. This is the same family of mistake as the lookahead bias that
invalidated the first level study: an entry price that was never available.

**Both scripts now enter at the price that actually printed.**

## What is actually true about levels

Levels hold **53–56% of touches** — a real tilt, but a small one. The economics
follow directly. At a symmetric stop and target the break-even win rate is
`50% + cost/(2R)`, so with a 2-point round trip:

| stop | break-even | observed |
|---|---|---|
| 10 pt | 60.0% | ~54% |
| 20 pt | 55.0% | ~54% |
| 30 pt | 53.3% | ~56% |

The hold rate barely reaches break-even, and only at wide stops where the fixed
cost is diluted. A 30-point stop on NQ is $600 of risk to harvest a tilt of
about three percentage points. Flow at the touch — aggression into the level,
volume, tape speed — does not separate the holds from the breaks at any stop
size, with every bucket under |t| = 1.7.

## Where that leaves it

Every hypothesis this project has tested is now either rejected or, in the case
of levels, reduced to a tilt too small to trade against a 2-point round trip.
The honest summary after four rounds and roughly thirty hypotheses: **there is
no intraday edge in this data large enough to survive costs.** The one real
edge found anywhere in the project remains the 27-year daily oversold bounce,
which is not a day trade.

That is a finding, not a failure. It is also the reason to stop adding
hypotheses of the same shape and to change something structural — the
instrument, the holding period, or the cost base — rather than keep testing
variations that all die the same way.

---

# The weight rule — the first thing that has survived

Fading levels does not work. Fading the *right* levels might.

A level is not one kind of object. The volume that traded at it in the previous
cash session says which kind it is, and tick data gives that number exactly
where bar data never could:

- **heavy level** — price was *accepted* there. It trades back through.
- **light level** — price was *rejected* there. It holds.

This is market profile's own distinction between a high-volume node and a low
one. It is not a story invented after seeing the result.

Fading only levels with **fewer than 10,000 contracts traded within 2 points of
them yesterday**, 30-point stop and target, entry at the printed price:

| | n | per trade | win | t |
|---|---|---|---|---|
| **fade light levels** | 88 | **+7.58 pt (+$152)** | **67.0%** | **+2.53** |
| fade heavy levels | 33 | −12.00 pt (−$240) | 33.3% | −2.40 |

**7 of 7 sessions positive. t across sessions +3.23.** That per-session
statistic is the honest one — it treats each session as one observation rather
than pretending 88 overlapping trades are independent — and it is the test that
killed the CVD divergence finding and the first level result.

The two halves point opposite ways, which is what a mechanism looks like and
what noise does not.

## Why this is not yet a result

- The 10,000 threshold is a tercile boundary **of the data it was measured on**.
- Roughly ten cells were examined before this one stood out.
- 88 trades across 7 usable sessions.
- Four earlier findings in this project looked at least this good and died: the
  value-area fade (lookahead), CVD divergence (overlap), the level fade
  (assumed fill), and the September level result (sample size).

## The parameters are frozen

`scripts/orderflow/level_weight.py` holds them as absolute constants rather
than quantiles of whatever is loaded, so they cannot silently refit as data
arrives:

```
HEAVY_THRESHOLD  10,000 contracts within +/- 2.0 pts of the level, previous RTH
STOP = TARGET    30 points
ENTRY            the price that actually printed on the touch
TOUCH / RE-ARM   0.25 pt / 8 pt
LEVELS           prior high, low, close, VAH, POC, VAL, merged within 5 pts
COST             2.0 pts round trip
```

Every session recorded from here is out-of-sample. `--oos YYYYMMDD` splits the
report so the frozen in-sample number and the genuine out-of-sample one are
never mixed.

**What would confirm it:** ten more sessions holding a positive mean with the
same split between light and heavy. What would kill it: the light/heavy
separation collapsing, or out-of-sample sessions landing near zero.

## The weight rule survives its two hardest tests

**Threshold sensitivity.** The 10,000 cutoff came from a tercile of the data it
was measured on, so the question is whether it is a fitted spike or part of a
plateau:

| cutoff | n | mean | win | t |
|---|---|---|---|---|
| 2,000 | 50 | +4.06 | 62.0% | 0.99 |
| 4,000 | 63 | +4.24 | 61.9% | 1.16 |
| 6,000 | 72 | +6.38 | 65.3% | 1.90 |
| 8,000 | 81 | +6.56 | 65.4% | 2.08 |
| **10,000** | 88 | **+7.58** | **67.0%** | **2.53** |
| 12,000 | 91 | +4.30 | 61.5% | 1.41 |
| 15,000 | 97 | +4.53 | 61.9% | 1.54 |
| 20,000 | 111 | +1.00 | 55.9% | 0.36 |
| **no filter** | 111 | **+1.00** | **55.9%** | **0.36** |

Not a spike. Every cutoff from 2,000 to 15,000 is positive, and the whole
6,000–10,000 band sits between +6.4 and +7.6. Past 20,000 the filter stops
excluding anything and the result collapses to the unfiltered +1.00 — which is
the fade tilt already known to be too small to trade. **The filter is the entire
edge.** 10,000 is still the maximum of the curve and therefore still flattered;
the defensible number is the +6.4 to +7.6 of the plateau, before any
out-of-sample discount.

**Leave one session out.** Nine sessions is few enough that one good day could
carry everything:

| dropped | n | mean | win | t |
|---|---|---|---|---|
| none | 88 | +7.58 | 67.0% | 2.53 |
| 08-11 | 73 | +8.32 | 68.5% | 2.56 |
| 08-12 | 84 | +6.84 | 65.5% | 2.20 |
| 08-13 | 86 | +7.80 | 67.4% | 2.58 |
| 08-14 | 81 | +6.56 | 65.4% | 2.08 |
| 08-19 | 67 | +6.89 | 65.7% | 1.98 |
| 08-20 | 65 | +9.58 | 70.8% | 2.84 |
| 09-02 | 79 | +8.29 | 68.4% | 2.65 |
| 09-03 | 87 | +7.34 | 66.7% | 2.43 |
| 09-04 | 82 | +6.99 | 65.9% | 2.23 |

**No session carries it.** The range across all nine deletions is +6.56 to
+9.58, and every one keeps t between 1.98 and 2.84. Compare the CVD divergence
finding, where removing the overlap alone took t from +5.12 to +1.00.

**Permutation test.** Shuffling the light/heavy labels 300 times returns
+0.96 pts on average (sd 1.84) against the real +7.58 — 3.6 standard deviations
out, p < 0.001. The classification is doing the work, not the trade.

### What is still wrong with it

The implied economics remain absurd: 9.8 trades a session at +$152 is $1,482 a
day on one contract, roughly $370,000 a year. No edge of that size survives in a
market this liquid. Nine sessions and 88 trades is simply not enough to estimate
a mean, whatever the t-statistic says, and the win-rate interval is
[57.2%, 76.9%] against a break-even of 53.3%. **At the pessimistic end of that
interval the edge is +2.33 points, about $47 a trade** — which is the number to
plan against, not the headline.

Out-of-sample sessions are the only thing that resolves it.

## Can it actually be executed?

Every number above assumed a fill at the printed price on the touch, a target
that fills the moment price kisses it, and a stop that fills exactly where it
sits. None of those are free, and an edge of seven points can be entirely
consumed by execution while still looking perfect in a backtest.

**Hold time is the uncomfortable number.** Median **2.6 minutes**, p25 **48
seconds**, median gap between trades 3.1 minutes, 9.7 trades a session. This is
not a swing trade someone watches develop over half an hour. Roughly 25 minutes
of a 390-minute session is spent in a position, arriving in bursts.

That rules out eyeballing a chart and clicking. It does **not** rule out the
trade, because the levels are computed from the previous session and are known
before the open: the entry is a **resting limit with an OCO bracket**, placed in
advance, and nothing about it needs reaction speed. Buy limits go below price,
sell limits above, which is also the direction the rule wants.

**What the assumptions are worth:**

| assumption | result |
|---|---|
| fill on any touch (as previously reported) | +7.35 pt, 66.7%, t=2.43 |
| entry needs 1 tick **through** the level | +7.11 pt, 66.3%, t=2.33 |
| entry needs 2 ticks through | +6.09 pt, 64.6%, t=1.93 |
| entry needs 4 ticks through | +5.82 pt, 64.2%, t=1.83 |
| + target 1 tick through, stop slips 1.0 pt | **+6.78 pt, 66.3%, t=2.19** |
| + target 2 ticks through, stop slips 2.0 pt | +6.44 pt, 66.3%, t=2.04 |

Queue position was the assumption most likely to be flattering the result —
touches that reverse *without* trading through are precisely the good outcomes,
so assuming a fill on every touch keeps winners that were never entered. It
costs about a point and a quarter, not the whole edge.

**Chasing destroys it.** Entering at market some seconds after the touch instead
of resting a limit:

| delay | result |
|---|---|
| 0s (resting limit) | +7.35 pt |
| 5s | +3.08 pt |
| 15s | +7.26 pt |
| 30s | +3.26 pt |
| 60s | +5.31 pt |

Erratic, because the sample is small enough that each cell moves on a handful of
trades, but every delayed variant is worse or unstable. The edge is in being
*there already*, not in reacting.

**Cost tolerance**, on realistic fills: +6.78 at 2 points, +4.78 at 4, +2.78 at
6, +0.78 at 8. It dies somewhere around 7 to 8 points of total round-trip cost
against a real NQ cost of one to two. That is a reasonable margin.

### What this means operationally

The workflow is: compute the previous session's levels and the volume at each,
drop the heavy ones, place resting limits with brackets at the light ones before
the open, and let them work. It is an order-placement routine, not a screen-
watching one — which is fortunate, because at a 2.6-minute median hold, screen
watching would not be fast enough.

## The CVD filter, with the number

Saying "CVD is against this trade" is not a rule. The cut-off is the only part
that can be acted on, and the first version of the panel left it out.

**Raw CVD in contracts does not work.** Swept across seven cut-offs from 1,000
to 12,000 contracts, it separates nothing — 1,000 gives +7.04, 4,000 gives
+6.90, 6,000 and above give the unfiltered +7.58. The reason is mechanical: a
touch at 13:45 has twenty minutes of delta behind it and one at 19:30 has six
hours, so the same figure means different things. **The number the platform
displays is the wrong unit to threshold on.**

**As a share of the session's volume, it does work:**

| skip when CVD against the fade exceeds | keeps | per trade | win | t |
|---|---|---|---|---|
| 0.5% | 243/367 | +5.86 | 63.5% | +1.76 |
| 1.0% | 282/367 | +8.56 | 68.8% | +2.71 |
| **1.5%** | **319/367** | **+11.00** | **72.8%** | **+3.71** |
| 2.0% | 336/367 | +9.74 | 70.7% | +3.24 |
| 3.0% | 347/367 | +7.32 | 66.7% | +2.38 |
| 5.0% | 356/367 | +8.27 | 68.2% | +2.74 |
| no filter | 367/367 | +7.58 | 67.0% | +2.53 |

Equivalently, CVD per minute works too — skip above 30 contracts/minute against
the fade gives +11.33 at 73.4%.

**Per session at the 1.5% cut: 7 of 7 positive**, +0.73 to +28.00 points, and
the pooled result is **+11.00 pts at 72.8% on 81 trades, t=+3.71** against
+7.58 at 67.0% unfiltered. Every neighbouring cut from 1.0% to 5.0% also beats
no filter, so this is a plateau rather than one lucky value.

It is still a number taken from the same data the effect was measured on, and
it is the next thing out-of-sample sessions have to confirm.

### And the count has to start at the open

The first build counted CVD from the moment the indicator was attached, so
attaching mid-session disagreed with the platform's own CVD by everything that
had already traded — caught on a live chart showing ATAS at roughly +4,000 and
this at −292. The session's completed candles are now read once to seed it.
Candle members are reached by reflection so an unexpected property name costs a
"PARTIAL" label in the panel rather than the build, and the panel says plainly
when the count is not the full session.

## Out of sample, four test days

08-17 arrived after the rule was frozen and unlocked two pairs, because 08-18
had previously had no prior session to work from.

| session | trades | per trade | total |
|---|---|---|---|
| 08-17 | 5 | **+16.00 pt** | +$1,600 |
| 08-18 | **0** | — | gap day, see below |
| 08-25 | 17 | −0.24 pt | −$80 |
| 08-26 | 12 | −8.79 pt | −$2,110 |
| **pooled, with the CVD filter** | **34** | **−0.87 pt** | **−$590** |

`t = −0.17`. That is not a losing result, it is **no result**: thirty-four trades
cannot distinguish a small edge from nothing in either direction, and the
earlier reading of "both days lost" was drawn from half this sample.

**08-18 traded nothing on purpose.** 08-17 closed near 30,100 and 08-18 traded
29,514–29,770, so not one of the previous session's levels was reachable. The
rule stands aside on gap days rather than reaching for something, which is the
correct behaviour and the same situation that made 09-09 and 09-10 untestable.

Pooled across everything, the filter still earns its place and the cut is still
in the right region:

| cut | n | per trade | win | t |
|---|---|---|---|---|
| no filter | 123 | +4.92 | 62.6% | +1.89 |
| 1.0% | 108 | +5.61 | 63.9% | +2.03 |
| **1.5%** | **115** | **+7.49** | **67.0%** | **+2.86** |
| 2.0% | 116 | +6.63 | 65.5% | +2.52 |
| 3.0% | 118 | +4.96 | 62.7% | +1.87 |

**The verdict has changed shape but not direction.** It is no longer "the rule
lost out of sample"; it is "out of sample is too small to say anything". Four
test days, one strongly positive, one flat, one negative, one correctly absent.
The honest position is that this still cannot be funded, and the reason is
sample size rather than evidence of failure.

## Six out-of-sample days: the in-sample figure was fitted

| session | trades | per trade | total |
|---|---|---|---|
| 08-17 | 5 | +16.00 pt | +$1,600 |
| 08-18 | 0 | — | gap day |
| 08-21 | 15 | −2.40 pt | −$720 |
| 08-24 | 2 | −2.00 pt | −$80 |
| 08-25 | 17 | −0.24 pt | −$80 |
| 08-26 | 12 | −8.79 pt | −$2,110 |

**The comparison that settles it:**

| | n | per trade | win | t |
|---|---|---|---|---|
| in sample (9 days) | 81 | **+11.00 pt** ±5.81 | 72.8% | +3.71 |
| out of sample (6 days) | 51 | **−1.36 pt** ±8.16 | 51.0% | −0.33 |

Difference **+12.36 points, SE 5.11, t = +2.42.** The gap between the two is
itself larger than chance. That is the definition of a fitted result: the
in-sample number was not an estimate of an edge, it was a description of the
data it was found in.

**Best honest estimate of the edge is the out-of-sample mean: −1.36 points a
trade, 95% interval −9.52 to +6.80.** Zero sits inside that interval, so the
rule cannot be distinguished from no edge at all. The win rate tells the same
story more plainly: **72.8% in sample, 51.0% out.** A coin.

And the pooled figure has decayed monotonically as honest data arrived:

| sessions | 1.5% cut | t |
|---|---|---|
| 14 | +11.00 | 3.71 |
| 16 | +7.10 | 2.64 |
| 17 | +7.49 | 2.86 |
| **18** | **+6.22** | **2.52** |

That decay is not noise; it is the in-sample portion being diluted.

### The verdict

**Do not trade this.** Not "not yet", and not "needs more data to confirm" —
the out-of-sample evidence is now sufficient to say the measured edge does not
reproduce. Fifty-one trades at 51% is not a small sample failing to detect a
real effect; it is what a rule with no edge looks like.

What remains genuinely true and worth keeping:

- **Levels hold 53–56% of touches.** A real, small tilt, measured on 198 touches
  and stable across stop sizes.
- **Heavy levels break.** Fading a level carrying 10,000+ contracts lost 12
  points a trade at 33% in sample. That half of the split had a mechanism behind
  it and is worth respecting even without the trade.
- **The infrastructure.** A verified recorder, sixteen clean sessions, an
  indicator that computes the levels live and agrees with the backtest to the
  tick, and a test harness that caught this rather than letting it reach live
  money.

The last of those is the point. Four findings in this project looked good and
died — lookahead, overlap, an impossible fill, and now an overfit threshold.
Each one was caught before it cost anything.

---

## The gap trade — gap at the open, structure turns, price travels back

Tested after it was annotated on a live chart: gap down at the open, a 5‑minute
fair value gap that holds as a higher low, a second higher low, a break of
structure, then enter toward the gap level. `scripts/orderflow/gapfill.py`.

Every element of it is definable, so it was measured rather than admired. But
the order of the questions decides the answer, and the first one is not about
the entry. It is: **is the destination reachable?** If price only returns to
the previous close half the time, no amount of structure reading turns that
into a trade.

### The base rate, on 13,500 sessions rather than 15

Fifteen recorded sessions cannot answer this — every gap bucket would hold two
or three days. A gap is fully defined by four numbers a daily bar already
carries, so the question was asked on 27 years of QQQ and SPY instead.

| gap size | sessions | fills | median share of gap closed |
|---|---|---|---|
| under 0.15% | 3,427 | 92% | over 200% |
| 0.15–0.3% | 2,841 | 76% | ~195% |
| 0.3–0.5% | 2,606 | 64% | ~140% |
| 0.5–1% | 2,894 | 51% | ~103% |
| 1–2% | 1,352 | 39% | 78% |
| over 2% | 390 | 33% | 70% |

The fill rate falls monotonically with gap size in both symbols. For NQ at
29,400: 1% is 294 points, 0.3% is 88 points.

**Small gaps fill; large gaps do not.** The trade is being asked for on exactly
the gaps where the target is least reachable.

### With a stop on it

Reach statistics are best‑case excursions and flatter the trade. Entering at
the open toward the gap, targeting the gap level, stopping the same distance
away (1:1, so the win rate *is* the edge). Days that touched both target and
stop cannot be ordered by a daily bar, so both bounds are reported.

| gap size | clean win | clean loss | unknown | worst | best |
|---|---|---|---|---|---|
| 0.3–0.5% | 35% | 36% | 29% | −0.31R | +0.27R |
| 0.5–1% | 35% | 49% | 16% | −0.30R | **+0.01R** |
| 1–2% | 31% | 61% | 8% | −0.38R | **−0.22R** |
| over 2% | 30% | 67% | 3% | −0.39R | **−0.34R** |

On gaps above 1%, **both bounds are negative** — the trade loses even if every
ambiguous day is generously counted a win. That is 1,742 sessions saying the
same thing, and it is the bucket the chart in question sat in. Below 0.5% the
bounds straddle zero and the daily bar genuinely cannot resolve it.

Shortening the target to half the gap lifts the large‑gap buckets to roughly
break‑even at the optimistic bound and still negative at the pessimistic one.

### The structured entry on recorded sessions

The full pattern — pivot‑confirmed higher low, break of the prior swing, stop
beyond the swing, target the previous close, pivots confirmed two bars late so
nothing is known before it could have been:

**5 qualifying setups, −16.20 points a trade, 20% win, −0.17R, −$1,620.** One
winner (08/17, +97.8), four losers. Far too few to judge on its own — but it
points the same way as the 13,500‑session base rate, which is not.

### Verdict

The setup is simple, it is fully automatable, and it is already automated —
that was never the obstacle. The obstacle is that on the gap sizes NQ actually
produces (median around 100 points, ~0.35%), the gap closes 64% of the time at
best and the 1:1 trade against it is a coin; on the large gaps that look most
dramatic on a chart, it is a measured loser across 27 years.

**Do not trade the large‑gap fill.** The only region left unresolved is small
gaps under 0.5%, where the daily bar cannot order the touches and there are 15
intraday sessions to work with — which is not enough, and is the same sample
size that produced four dead findings already.

---

## The structure trade, tested properly — 2,680 sessions of 5-minute bars

The previous entry tested the gap **base rate** on 13,500 daily bars and the
**structure** on 5 recorded sessions, and never joined them. That was a real
flaw and the objection to it was right: a daily bar holds four numbers and
cannot express a higher low, so the open-entry result describes a trader who
does not read structure. It is not evidence about one who does.

Fixed by pulling **2,680 sessions of QQQ 5-minute RTH bars, 2016-01 to 2026-08**
(`scripts/orderflow/harvest_av.py`), and running the pattern exactly as drawn:
pivot-confirmed higher low, second higher low, break of structure, enter toward
the gap level, stop under the swing. Every term is causal — a pivot at bar *i*
is not known until *i+k*, and nothing looks at a bar before it existed.
`scripts/orderflow/gapstructure.py`.

### Reading structure is worth something — that part was right

Same 778 sessions, same target, matched controls:

| | n | mean | win | t |
|---|---|---|---|---|
| 2 higher lows + BOS | 778 | −0.074R | 43.2% | −1.71 |
| control: enter at the open, fixed stop | 778 | −0.249R | 24.3% | −4.29 |
| **difference** | | **+0.176R** | | **+2.43** |

Waiting for the sequence is **+16.5 NQ points a trade better** than entering
blind on the same days. That is a genuine effect at t = +2.43. The structure is
seeing something.

### But every complete version still loses

| variant | n | mean | win | t |
|---|---|---|---|---|
| 1 HL + BOS | 1,322 | −0.138R | 40.1% | −4.07 |
| 2 HLs + BOS (as drawn) | 778 | −0.074R | 43.2% | −1.71 |
| 3 HLs + BOS | 310 | −0.043R | 43.5% | −0.60 |
| + an FVG that held | 593 | −0.098R | 42.8% | −2.03 |
| target ½ the gap | 778 | −0.077R | 51.3% | −2.11 |
| target 1R / 2R / 3R | 1,228 | −0.098 / −0.102 / −0.084R | | −3.65 / −3.00 / −2.23 |
| only when the gap is ≥2R away | 419 | −0.124R | 32.9% | −1.81 |
| enter on the retest, not the break | 738 | −0.115R | 38.1% | −2.33 |
| retest halfway back to the HL | 630 | −0.125R | 27.0% | −1.50 |

Negative in both directions, in all four eras (2016–18, 2019–21, 2022–24,
2025–26), at every target, and in every gap-size bucket. Bar-level ambiguity is
0% — 5-minute bars order the touches, so none of this rests on an assumption.

### Why both things are true at once

The control is *terrible*: 24% win rate. Beating it is not the same as making
money, and the gap between those two is the whole result. The sequence
correctly identifies that a turn has happened — but it confirms at the **top of
the leg**, which is simultaneously the worst price in the move and the widest
stop. The information is real and the entry it dictates gives it all back.

The retest was the obvious repair and it does not work either: resting the
order back at the broken level gets a better price but only fills on 738 of 778
setups, and the ones that come back to fill are disproportionately the ones
that keep going the wrong way.

### Verdict

The pattern is simple, it is automatable, and it is now automated and measured
on 2,680 sessions rather than 5. **Reading structure beats not reading it. It
does not beat not trading.** The remaining honest question is not whether the
sequence is real — it is — but whether there is an entry that collects the
information without paying the leg for it. Nothing tested so far does.

---

## Re-opening every rejected rule on 1,421 sessions — and two corrections

The rejections in this file were made on 198 touches and 51 out-of-sample
trades. That was the data that existed; it was not the data that was
obtainable. Re-run on **1,421 sessions of QQQ 1-minute bars (2021-01 to
2026-08)**, 3,682 level touches. `scripts/orderflow/levels_long.py`.

1-minute bars matter here specifically: a 30-point NQ stop is 0.73 QQQ points,
narrower than a 5-minute bar. Testing it on 5-minute data would repeat the
daily-bar error. At 1-minute resolution the both-touched ambiguity is 1–2%.

### Correction 1 — levels do not hold 53–56%

| | n | mean | win | t |
|---|---|---|---|---|
| fade every level | **3,682** | −2.34 NQ pts | **49.1%** | −4.57 |

The 53–56% hold rate was 198 touches of sampling noise. On twenty times the
data the fade is a coin that loses to costs. **This claim is withdrawn.**

### Correction 2 — the heavy/light split was backwards

The rule said light levels hold and are the ones to fade; heavy levels break.

| | n | mean | win | t |
|---|---|---|---|---|
| fade the **lightest** third | 760 | **−4.45** | 45.8% | −4.12 |
| fade the middle third | 1,237 | −2.14 | 49.3% | −2.39 |
| fade the **heaviest** third | 1,685 | −1.52 | 50.4% | −2.01 |

Light levels are the **worst** to fade, not the best. The rule was inverted,
and the live indicator's grey "NO TRADE" bands are drawn on the wrong third.

### What is real: prior-day extremes break

Fading PDH loses at t = −3.65; fading PDL at t = −3.92, on 1,044 touches.
That is the strongest signal in the project and it clears the |t| ≥ 3 bar. But
traded the right way round it still does not pay:

| | n | mean | win | t |
|---|---|---|---|---|
| go with the PDH/PDL break | 1,044 | −0.22 NQ pts | **52.8%** | −0.24 |
| de-overlapped, one a session | 947 | +0.43 NQ pts | 54.1% | +0.44 |

52.8% is a real tilt, stable at 51–55% in every one of six years. At 1:1 with
2 points of cost, break-even is 53.4%. **The edge exists and is slightly
smaller than the cost of trading it.** Lower cost or better reward-to-risk is
the only route; fading it is the one thing definitively ruled out.

### CVD cannot be tested on bars — proven, not assumed

`scripts/orderflow/cvd_proxy.py` builds 1-minute bars from the recorded tape,
computes three standard CVD reconstructions from those bars alone, and scores
them against the true signed volume from the same trades:

| proxy | path corr | sign agreement | end error |
|---|---|---|---|
| tick rule | 0.33 | 62% | 374% |
| close location | 0.19 | 50% | 276% |
| open-close | 0.33 | 68% | 259% |

The best one **points the wrong way on 4 of 18 sessions**. So the CVD filter,
CVD divergence, absorption and book imbalance cannot be re-opened at scale by
any amount of bar data. They stay where they are. More recorded tape is the
only thing that moves them.

### Gap + CVD, on the 18 tape sessions

`scripts/orderflow/gap_cvd.py`. Flow measured over the first 30 minutes — the
earliest read a live rule could act on — on 15 gap sessions:

| | n | mean | win |
|---|---|---|---|
| gap trade, no filter | 15 | +4.00 pt | 60.0% |
| early CVD **agrees** with the trade | 6 | **+28.00 pt** | **100%** |
| early CVD **against** | 9 | −12.00 pt | 33.3% |

Permutation test on the split (the t-test is useless — an all-winners group
has zero variance): **p = 0.028**.

It survives at 5%, and it is six sessions with a perfect record, which is the
exact shape of the four findings that already died here. Recorded as a
direction, not sized as a rule. About 40 gap sessions would settle it, and
recording them is the cheapest useful thing left to do.

---

## Go with the break, target the next level — and which timeframe

The proposal: once one side of the auction has won, take a break of structure
or change of character in that direction and target the next confluence level.
A different animal from everything above — every losing rule in this file was a
**fade**. `scripts/orderflow/structure_trade.py`, 1,420 sessions.

Signals computed on the stated timeframe; outcomes always simulated on
**1-minute** bars, so a stop and target inside one 15-minute bar are ordered
rather than guessed. Ambiguity 0%.

### The timeframe question has a clean answer

| timeframe | signals/session | n | mean | win | t |
|---|---|---|---|---|---|
| 1 min | 25.7 | 36,546 | −0.074R | 44.1% | **−9.41** |
| 3 min | 7.7 | 10,923 | −0.059R | 53.8% | −5.80 |
| 5 min | 4.1 | 5,815 | −0.044R | 57.7% | −3.73 |
| 15 min | 0.9 | 1,219 | −0.015R | 60.5% | −0.91 |
| 30 min | 0.2 | 271 | −0.017R | 56.8% | −0.71 |

**Monotonic: the more labels, the worse.** The "too many labels on 5-minute"
instinct is correct and then some — 1- and 3-minute structure is decisively
negative. 15 minutes is where it stops being noise, at about one signal a
session. BOS and CHoCH behave the same; neither is the better half.

### The real lever is reward-to-risk, not the signal

Splitting 15-minute signals by how far the next level sits:

| next level | n | mean | win |
|---|---|---|---|
| **under 1R away** | 971 | −0.029R | **64.5%** |
| 1 to 2R | 162 | +0.029R | 48.8% |
| 2 to 4R | 63 | +0.220R | 42.9% |
| over 4R | 23 | −0.387R | 21.7% |

Setups whose target is nearer than their stop **win 64.5% and lose money.**
That is where the damage is, it is known at the entry bar, and refusing them is
implementable.

But swept as a threshold rather than read as a bucket, the improvement is a
plateau at **zero**, not an edge — pooled across 5/15/30-minute signals at
R:R ≥ 2: n=1,181, −0.003R, t = −0.06. Years scatter (2022 −0.181R, 2023
+0.214R). De-overlapped to one trade a session: n=611, −0.021R.

**Verdict: the structure trade is flat once the bad-R:R setups are refused, and
negative if they are not. The +0.220R bucket was an artefact.**

### The CVD gate — not shown to help

`scripts/orderflow/structure_cvd.py`, 15 pairs of recorded tape (the only
source of real signed flow). R:R ≥ 2 leaves 14 signals, too few to split, so
this is every break:

| 5-minute signals | n | mean | win |
|---|---|---|---|
| no flow gate | 58 | +0.026R | 56.9% |
| delta ≥ +1,000 with the trade | 25 | **−0.112R** | 52.0% |
| delta under +1,000 (refused) | 33 | **+0.131R** | 60.6% |

The gate points the **wrong way** at 5 minutes, and the other way at 3 minutes
— inconsistency between adjacent timeframes is itself the signature of noise.
Difference −0.243R, 95% interval by **session-level bootstrap** (signals inside
a day share that day's move) **−0.711R to +0.336R: includes zero.**

Not shown to do anything. With 15 sessions that is a statement about the
sample, not about the idea — and it cannot be improved without more tape,
because CVD is unrecoverable from bars.

### CVD *change*, not CVD *level* — the check that was missing

The first pass gated on cumulative delta since the open. That is "who has won
the session", and by mid-afternoon it is mostly history. What should matter to
a break is "who is winning **right now**" — the delta in the bars that actually
pushed price through the level, measured on the signal's own timeframe.

Both forms, each judged against **the trades it refuses inside the same
sessions** rather than against zero. That pairing matters: the 3-minute
baseline on this tape is +0.101R while the same signal over 1,420 sessions runs
t = −5.80, so the tape sample is running hot and any gate sitting on it would
flatter itself.

| gate (3-minute signals) | n | vs refused | 95% interval |
|---|---|---|---|
| LEVEL: session delta ≥ +1,000 | 50 | +0.051R | [−0.43, +0.56] |
| LEVEL: session delta ≥ 1% of volume | 32 | **−0.356R** | [−0.77, +0.01] |
| CHANGE: breaking bar 5%+ of its volume | 90 | +0.229R | [−0.08, +0.65] |
| CHANGE: last 2 bars 10%+ of volume | 29 | **+0.339R** | **[+0.06, +0.63]** |
| CHANGE: last 5 bars delta ≥ +1,000 | 16 | +0.191R | [−0.36, +0.99] |

At 5-minute the same 2-bar gate gives **+0.348R** — two timeframes landing
within 0.01R of each other.

**The tally across both timeframes: change gates 10/10 positive, median
+0.181R. Level gates 1/4 positive, median −0.287R.**

That split is the finding, not any single cell. Sixteen tests were run, so one
interval clearing 5% is what chance hands you — but every change gate landing
on one side and every level gate on the other is not. The gates overlap
heavily, so this is suggestive rather than a p-value, and it rests on fifteen
sessions.

**Status: the most promising lead in the project, and explicitly not yet a
rule.** It is decidable with more recorded tape and by nothing else.

---

## Filter survey: what else in the recording shows direction and strength?

`scripts/orderflow/filter_survey.py`. Same methodology as the CVD gates —
each candidate judged against **the trades it refuses, inside the same
sessions**, 95% intervals from resampling sessions.

### The headline is a recorder bug, not a filter

**The CUM stream was recording nothing usable.** Every row: `fills = 1`,
`first_price = last_price`, median volume 1 — 177,133 "aggressive orders"
sharing 177,133 fills between them. A duplicate of the tape with three
constant columns.

`OnCumulativeTrade` fires when an order *starts* filling; the fills join the
same object afterwards. Writing inside that callback always caught it at one
fill. **Fixed** by holding the trade and writing it when the next one arrives —
no API guess needed (two previous guesses cost builds).

This matters because CUM is the only stream that separates **one 100-lot from a
hundred 1-lots**. CVD counts them identically. That is the most obvious
order-flow filter there is, and it was *missing data*, not a null result.

### What was testable, and what it showed

| family | 3-min tally | 5-min tally |
|---|---|---|
| BOOK (ladder imbalance) | 1/3 positive, median −0.207R | 1/2 positive, median +0.129R |
| SURGE (volume vs last 20 bars) | 0/2, median −0.210R | 1/1, median +0.049R |
| SPEED (prints vs last 20 bars) | 0/2, median −0.198R | 1/1, median +0.049R |
| RUN (consecutive agreeing bars) | 2/2, median +0.095R | 0/2, median −0.213R |
| BIGPRINT (prints ≥10 lots) | 1/2, median +0.018R | 0/1, median −0.242R |

**Nothing is consistent between timeframes.** Every family flips sign. Two
cells exclude zero and they **contradict each other** — book imbalance ≥ +0.10
is −0.507R on 3-minute, while book imbalance ≥ 0 is +0.483R on 5-minute, same
family, opposite directions. Eighteen tests were run; two clearing 5% is
almost exactly what chance produces.

### Why this null is worth having

Compare with the CVD-change result: **10/10 positive across both timeframes,
median +0.181R**. Here, five families and not one holds its sign.

That contrast is the useful part. The same harness that produced a consistent
pattern for CVD change produces scatter for everything else — so the method is
not a machine for manufacturing positives, and the CVD-change signal is not an
artefact of how these tests are built.

### Three analysis bugs found and fixed

Worth recording because two of them would have produced confident false
findings:

1. **Depth writes `A` for the ask, not `S`.** Filtering for `S` gave an empty
   book. This silently made depth look unusable in *earlier* work too.
2. **Expanding session median as a "busy" baseline** is dominated by the
   opening surge — 87% of bars scored below their own median, arithmetically
   impossible. It was about to report that breaks on volume do worse.
3. **A `>= 0` cut on a net-delta column** lumps "no large orders at all" with
   "large orders agreeing", which is why signal counts *rose* as the size
   threshold rose.

---

## The cumulative stream works — verified on 3 August

First session recorded after the fix. The reconciliation is exact:

| check | result |
|---|---|
| CUM volume vs RTH tape volume | 385,275 vs 385,275 — **ratio 1.000** |
| CUM fills aggregated vs RTH tape prints | 359,224 vs 359,224 — **exact** |

Every print accounted for once, nothing lost, nothing double-counted.

| | old build (11 Aug) | new build (3 Aug) |
|---|---|---|
| max fills in one order | 1 | **171** |
| orders with >1 fill | 0.00% | **32.07%** |
| orders that swept price | 0.00% | **1.19%** |
| volume from orders ≥10 lots | 0.57% | **13.78%** |

The old stream was the tape with three constant columns. The new one carries
aggressive-order size and sweep depth — the thing CVD structurally cannot see.

### Which size threshold is actually new information

Answerable on one session, and it decides what is worth recording days for. If
large-order delta tracks plain delta closely it cannot add anything at any
sample size.

| threshold | corr with plain delta (5-min) | share of volume |
|---|---|---|
| ≥5 lots | +0.936 | 28.4% |
| ≥10 lots | +0.875 | 13.8% |
| **≥25 lots** | **+0.653** | 5.1% |
| **≥50 lots** | **+0.464** | 2.2% |
| **sweeping orders** | **+0.526** | 5.6% |

**At 10 lots it is 88% the same series as CVD and cannot add much.** The
thresholds carrying genuinely separate information are **≥25 lots**, **≥50
lots** and **sweep delta** — and ≥25 is likely the sweet spot, since ≥50 is
only 2.2% of volume and will be sparse in a 5-minute bar.

That is the test queued for when enough paired sessions exist. 3 August alone
cannot be used: the previous session (31 July) was not recorded, and every
structure test needs the prior day for its levels.

---

## Information coefficient harness — and why IC is not edge

`scripts/orderflow/ic_harness.py`. Adopts forward-return scoring, which is a
genuine improvement: trade outcomes give ~60 observations from 19 sessions,
forward returns give **6,954 one-minute bars**. Features computed from ticks;
bars are only the evaluation grid, so the aggressor tag survives into every
feature.

IC computed **per session**, t-statistic across the 19 — bars inside a day are
not independent. Every result calibrated against a **null**: the same features
against returns circularly shifted within each session, which breaks the link
and keeps the autocorrelation.

| forward 15 min | IC | t | sessions agreeing | null t |
|---|---|---|---|---|
| **vwap_disp** | −0.2950 | **−9.21** | 95% | −0.90 |
| cvd | −0.2279 | −5.50 | 89% | +0.64 |
| cvd_share | −0.1823 | −4.73 | 84% | +0.72 |
| poc_shift | −0.0932 | −2.61 | 74% | −0.88 |

Null calibration across all 60 feature-horizons:

| bar | real | by chance |
|---|---|---|
| \|t\| ≥ 2 | 18 of 60 | 5 |
| \|t\| ≥ 3 | **11 of 60** | **0** |

So the signal is real. Every strong feature is **negative** — price above VWAP,
or high cumulative delta, predicts *lower* forward returns. Intraday mean
reversion, and it disagrees with "go with the flow".

### The number that matters

Converting the strongest feature in the project into points:

| | |
|---|---|
| IC | −0.295, t = −9.21, 95% of sessions agreeing |
| **as a trade, net of 2 points** | **+0.08 points, t = +1.58** |

**A t of −9.21 is worth eight hundredths of a point.** The deciles are not
monotonic in points either — decile 2 pays +7.78 while decile 9 pays −1.50 —
so the ranking is right and the payoff is noise.

This is the calibration the whole project needed. **IC, t-statistic and Sharpe
rank candidates by whether the ordering is right. They do not say the ordering
pays.** Any workflow that shortlists on IC would have put `vwap_disp` first, and
it is worth nothing after costs.

### On generating 500–1,000 candidate features

Our own null says what that would do here. 60 feature-horizons produced 5
false positives at |t| ≥ 2. A thousand features across three horizons is 3,000
tests — roughly **250 would clear |t| ≥ 2 by chance alone** on 19 sessions.

The feature count is not the bottleneck. The sample is, and so is the gap
between a correlation and a cost-covering edge.

---

## Forecasting the next 15 minutes — and a lookahead bug worth 8.75 points

`scripts/orderflow/forecast.py`, 24 sessions (July batch added), 7,404 bars.

### The bug first

The first version standardised each feature against its session's **full-day**
mean and standard deviation. At 10:00 those have not happened yet. Result:

| | IC | trade, net of cost |
|---|---|---|
| full-session z-score (**lookahead**) | +0.2551, t +8.93 | **+8.95 pts**, t +6.49 |
| expanding z-score (**honest**) | +0.1351, t +3.68 | **+0.20 pts**, t +0.54 |

**The lookahead was worth 8.75 points a trade.** Everything that looked like an
edge was knowing the day's own statistics in advance. Kept in the script behind
a flag so the size of the bias stays visible.

### What survives

| | IC | t | trade after 2 pts | t |
|---|---|---|---|---|
| fixed blend (no fitting) | +0.1351 | **+3.68** | +0.20 pts | +0.54 |
| fitted, in sample | +0.1030 | +3.60 | +1.17 pts | +0.68 |
| fitted, **out of sample** | +0.0308 | +0.99 | **−3.69 pts** | −0.61 |
| vwap_disp alone | +0.1404 | +3.27 | −2.24 pts | −0.62 |

Two things at once: **the information is real** (blend IC t = +3.68, and the
null harness showed 11 of 60 features clearing |t| ≥ 3 against 0 by chance),
and **it does not cover costs**. Fitting makes it worse — the least-squares
combination collapses from +3.60 in sample to +0.99 out of sample, which is
what 24 sessions does to a five-parameter fit.

### The one asymmetry worth recording

| quintile | median move | up rate | bars |
|---|---|---|---|
| 0 (most bearish score) | **−6.0 pts** | **40%** | 1,342 |
| 2 | 0.0 pts | 49% | 1,342 |
| 4 (most bullish score) | +0.3 pts | 50% | 1,342 |

The bearish extreme leans (60% down, median −6 points). The bullish extreme is
a coin. Recorded as an observation, not a finding — it was seen after the fact
and has not been tested as a rule.

### What this means for the indicator

A forecast display cannot honestly be built from this yet. The score carries
real information and does not pay for the spread, so an indicator that prints a
direction would be selling a t of +0.54 as a signal. What it can honestly show
is **where the session currently sits**, with the up-rate attached, and say
plainly that the extremes are a lean rather than a call.

---

## The CVD-change gate does not reproduce — finding number five dies

34 sessions now (July batches added). The July sessions are genuinely new data
for a claim that was made on August and September, so the first thing they were
used for was testing it.

| gate | Aug/Sep (original) | July (new) |
|---|---|---|
| breaking bar 5%+ of volume | +0.229R | **−0.169R** |
| breaking bar 10%+ | +0.160R | **−0.153R** |
| **last 2 bars 10%+** | **+0.339R** | **−0.100R** |
| last 3 bars 5%+ | +0.170R | −0.053R |
| 5-min, breaking bar 5%+ | +0.144R | −0.180R |
| 5-min, last 2 bars 10%+ | +0.348R | −0.093R |

**Six of eight negative on the new data**, and the two positives are +0.007R
and +0.042R — indistinguishable from zero. This was reported as "the most
promising lead in the project". It was a 15-session artefact.

### What that costs the reasoning, not just the result

The evidence for it was **sign consistency**: 10/10 gates positive across two
timeframes, which I argued was hard to get by chance even though single cells
were not significant. That argument was wrong, and the reason is now obvious:
the gates overlap heavily, so they are close to *one* observation wearing ten
hats, not ten. Ten correlated views of the same 15 sessions agreeing tells you
those 15 sessions leaned one way — nothing more.

**Sign consistency across correlated gates is not evidence of reproducibility.**
Only new sessions are.

## Order size and sweep — promising, and explicitly unconfirmed

`scripts/orderflow/bigorder.py`. The first test possible on a working
cumulative stream, 13 July pairs.

| gate | 3-min | 5-min |
|---|---|---|
| 25+ lot net delta with trade | +0.240R | +0.132R |
| 25+ lot net ≥2% of volume | −0.003R | **+0.302R** [+0.03, +0.61] |
| 50+ lot net delta with trade | +0.228R | +0.281R |
| 50+ lot net ≥2% of volume | +0.311R | +0.197R |
| sweep delta with trade | +0.004R | +0.095R |
| sweep net ≥2% of volume | +0.112R | +0.217R |

**11 of 12 positive, median +0.17R and +0.21R.**

That is *exactly* the evidence shape that just failed above — sign consistency
on a single block of sessions, one cell clearing zero out of twelve. So it is
recorded as a candidate and nothing more. It cannot be confirmed on existing
data: every August and September session has a degenerate cumulative stream,
so the only possible out-of-sample test is **sessions not yet recorded**.

The incremental test — does size add anything on top of CVD change — came back
underpowered (n=13, n=9). Correlation between the two gates is +0.53, so they
are neither the same thing nor independent.

---

## Order size: survives a first out-of-sample test

39 sessions. July 21–28 arrived after the order-size gates were measured on
July 1–20, so the twelve gates were re-run on the new sessions with **no
parameter changes** — the test promised before the data existed.

| gate | July 1–20 (fitted) | July 21–28 (new) |
|---|---|---|
| 25+ lot net delta with trade | +0.240R | −0.059R |
| 25+ lot net ≥2% of volume | −0.003R | +0.146R |
| **50+ lot net delta with trade** | **+0.228R** | **+0.225R** |
| **50+ lot net ≥2% of volume** | **+0.311R** | **+0.271R** |
| sweep delta with trade | +0.004R | +0.158R |
| sweep net ≥2% of volume | +0.112R | +0.063R |
| *5-min:* 25+ lot ≥2% | +0.302R | +0.169R |
| *5-min:* sweep delta | +0.095R | +0.272R |

**8 of 10 positive on the new block, median +0.15R.** The two **50+ lot** gates
reproduce almost exactly (+0.228 → +0.225, +0.311 → +0.271).

### How this differs from the finding that just died

CVD change was never tested out of sample before being called promising, and
when it finally was, six of eight measurements flipped negative. Order size has
now been put through the same test and held. That is a real difference in
status.

It is still **not confirmed**, for reasons worth stating plainly:

- **4 pairs** in the new block. At 5-minute several gates had too few trades.
- **Adjacent weeks in the same month.** Same regime, so this is the weakest
  useful form of out-of-sample test.
- Sign consistency across correlated gates is exactly what misled the previous
  finding, and 8/10 here carries the same caveat.

### The test that would settle it

August and September cannot help — every one of those sessions has a
degenerate cumulative stream. The decisive test is a **different month with a
working stream**, either freshly recorded or re-recorded from replay on the
current build. The gates are frozen and written down above; nothing about them
will be adjusted for the next block.

---

## Third block: one gate reproduces, and still cannot be called an edge

43 sessions. July 29 – Aug 4 is a third block, run on the frozen gates.

| 3-min gate | A: Jul 1–20 | B: Jul 21–28 | C: Jul 29–Aug 4 |
|---|---|---|---|
| 25+ lot net delta | +0.240R | −0.059R | −0.235R |
| 25+ lot ≥2% vol | −0.003R | +0.146R | +0.078R |
| 50+ lot net delta | +0.228R | +0.225R | +0.031R |
| **50+ lot ≥2% vol** | **+0.311R** | **+0.271R** | **+0.264R** |
| sweep ≥2% vol | +0.112R | +0.063R | +0.420R |

**One gate reproduces cleanly three times.** The others scatter or decay — the
25+ lot net delta gate goes +0.240 → −0.059 → −0.235 and is effectively dead.

### Testing that one gate properly

Pooled over all 22 pairs, 142 breaks:

| | n | mean | win rate |
|---|---|---|---|
| gate ON | 34 | +0.095R | **70.6%** |
| gate OFF | 108 | −0.197R | 50.0% |
| difference | | **+0.292R** | 95% CI **[−0.007, +0.592]** |

**The interval includes zero**, barely. And the more important number: the
trades the gate *selects* average **+0.095R at a per-session t of +0.37** over
16 sessions. That is not distinguishable from zero.

**The gate separates bad from less bad.** It is not selecting a profitable
trade — it is declining an unprofitable one. Those are different products, and
only the second is worth acting on.

Block C also has the gated arm slightly negative (−0.059R), so even the
reproduction is not uniform.

### Status

This is the best-behaved thing in this project: pre-registered, tested on two
blocks it was not fitted on, reproducing to within 0.05R three times. It is
still **not an edge** — a 95% interval touching zero and a selected-trade t of
+0.37 do not support risk.

It fires about **1.5 times a session**, so accumulating evidence on it is slow.
Roughly 40 more sessions with a working cumulative stream would halve the
interval; a different month matters more than more of the same one.

---

## A different month kills the order-size gate — finding number six

46 sessions. Aug 10 and 11 were **re-recorded** on the fixed build, so their
degenerate cumulative files were replaced (existing maxfills 1, incoming 461
and 427). Aug 5–11 is the first block from a genuinely different month with a
working stream — the test asked for last round.

| 3-min gate | A: Jul 1–20 | B: Jul 21–28 | C: Jul 29–Aug 4 | **D: Aug 5–11** |
|---|---|---|---|---|
| 25+ lot net delta | +0.240R | −0.059R | −0.235R | **−0.434R** |
| 25+ lot ≥2% vol | −0.003R | +0.146R | +0.078R | +0.239R |
| 50+ lot net delta | +0.228R | +0.225R | +0.031R | −0.055R |
| **50+ lot ≥2% vol** | **+0.311R** | **+0.271R** | **+0.264R** | **−0.098R** |
| sweep ≥2% vol | +0.112R | +0.063R | +0.420R | +1.007R |

**The gate that reproduced three times fails on the different month.**

Pooled over 182 breaks and 27 sessions: difference +0.229R, 95% CI
**[−0.077, +0.516]** — includes zero. Selected trades run a per-session t of
**+0.82** over 20 sessions. Not an edge.

### The lesson is sharper than last time

After CVD change died I concluded that only new sessions test a claim. That was
not precise enough. This gate *was* tested on new sessions — twice — and held
to within 0.05R both times. Then it broke the moment the calendar moved.

Blocks B and C were **adjacent weeks inside the fitting month**. Adjacent weeks
share the regime that produced the pattern, so reproducing across them measures
persistence within a regime, not the existence of an effect.

**Out-of-sample means a different period, not merely later rows.** Three
consecutive reproductions inside one month were worth less than one test
against a different month.

### What is left standing

`25+ lot net delta` decays monotonically across all four blocks (+0.240 →
−0.059 → −0.235 → −0.434) and is definitively dead. `sweep ≥2% vol` reads
+0.112, +0.063, +0.420, +1.007 — the last value is large and the series is
erratic, which is the signature of noise rather than an effect strengthening.

No order-flow gate tested here separates the structure trade. Six findings have
now died in this project; five of them looked strong first.

---

## Reset: the edge grows with holding time

46 sessions (Aug 12–18 re-recorded; 34 now carry a working cumulative stream).

### Two hypotheses tested and rejected

**Magnitude is not more predictable than direction here.** Strongest |t| on the
signed move is **12.05**; on the absolute move it is **6.24**. The prior that
volatility is easier to forecast than direction does not hold in this data, so
that reframe is dead.

**A range filter does not rescue the structure trade.** High-range half
vs low: difference +3.95 pts, 95% CI **[−10.67, +18.94]**. Both halves have
*negative* per-session means (−4.44, −5.40) while the pooled numbers look
positive — the pooled figure is a few busy sessions carrying it. By month:
July −4.32, August +19.91. Unstable.

### What the evidence actually says

Every test in this project has used an intraday stop-and-target held for
minutes. Nobody checked what happens over longer holds:

| horizon | IC (vwap_disp) | t | quintile trade, net of cost |
|---|---|---|---|
| 15 min | −0.1206 | −4.08 | −2.78 pts (t −0.80) |
| 30 min | −0.2021 | −5.71 | +0.83 pts |
| 60 min | −0.2835 | −6.49 | +2.19 pts |
| 120 min | −0.4518 | −10.05 | +7.52 pts (t +1.24) |
| **to close** | **−0.5668** | **−10.98** | **+21.70 pts (t +2.14)** |

**The edge grows monotonically with holding time**, and only becomes larger
than costs somewhere past 30 minutes. At 15 minutes — where every previous
test lived — it is negative.

That is consistent with a real effect rather than noise: a spurious pattern has
no reason to strengthen smoothly across five horizons. It is also the obvious
explanation for six dead filters. **The trade was never given time to work.**
Two points of cost against a 30-point stop needs roughly a 7% edge; the same
two points against a multi-hour move needs about 1%.

### The structural point about sample size

Every intraday test here had an inflated sample: 300 "independent" breaks that
were really 40 sessions. **A one-trade-per-day design has 46 genuinely
independent observations** — statistically cleaner than anything attempted so
far, despite the smaller number.

### Status and the pre-registered next test

t = +2.14 over 45 sessions is **marginal** (p ≈ 0.04), and six findings have
already died here. This is not a green light.

Frozen before looking at anything further:

- **Trade**: at a fixed time each session, if vwap displacement is in the top
  quintile of the session so far, go short; bottom quintile, go long. Exit at
  the close. One decision a day.
- **Test**: July sessions fit, August/September held back entirely.
- **Bar to clear**: positive per-session mean after 2 points, t ≥ 2 on the
  held-back month, and the sign must not flip between months.

### Without holding to the close, nothing clears the bar

The constraint is a hard one, so it was tested directly rather than argued
with. Same trade, exit at a fixed clock time:

| exit (UTC) | IST | pts/trade | per-session t | sessions |
|---|---|---|---|---|
| 17:00 | 22:30 | +9.73 | +1.55 | 45 |
| 18:00 | 23:30 | +3.61 | +0.83 | 45 |
| 19:00 | 00:30 | +13.02 | +1.49 | 45 |
| **20:00 (close)** | 01:30 | **+21.70** | **+2.14** | 45 |

And bounded holds, all entry times: 60 minutes **+2.19 pts (t +0.95)**, 120
minutes **+7.52 pts (t +1.24)**.

**Every point estimate is positive. Not one reaches t ≥ 2 except the close.**
The earlier exits are also non-monotonic (+9.73, +3.61, +13.02), unlike the
clean monotonic growth across holding horizons — which is a warning sign, not
a detail.

Slicing by entry hour produces +13.74 at 15:00 and −8.59 at 14:00. That is
twelve cells on 45 sessions and it is noise; it is recorded here so it does not
get rediscovered and believed later.

### What it would take

The 17:00 exit (22:30 IST, a 3.5-hour session from the cash open) is the best
candidate that respects the constraint: **+9.73 points a trade at t = +1.55**.

t scales with the square root of the sample, so reaching t = 2 on the current
effect size needs about **75 sessions — roughly 30 more than exist.** That is a
concrete, finite requirement rather than an open-ended search.

If the effect is real, 30 more sessions establish it. If it is not, 30 more
sessions kill it. Either outcome is worth more than another filter.

---

## Order-size gate: confirmed dead on 3× the August data

The August sessions were re-recorded on the fixed build, taking the August
sample from 5 pairs and 40 breaks to **18 pairs and 130 breaks**. The gate
declared dead last round was re-tested on it, with the prediction that it stays
dead.

| gate | July (fitted) | August (test) |
|---|---|---|
| 25+ lot net delta | +0.093R | −0.287R |
| 50+ lot net delta | +0.152R | +0.021R |
| **50+ lot ≥2% vol** | **+0.241R** | **−0.019R** |
| sweep net delta | +0.062R | −0.270R |

The gate that reproduced three times inside July: **−0.019R on 17 August
sessions, 95% CI [−0.324, +0.283]**. Squarely zero. Closed.

## The holding constraint is final, and it sets the target

Holding to the close is ruled out on both counts — being awake at 01:30 and
carrying the risk. So the only candidate is the **17:00 UTC exit (22:30 local),
a 3.5-hour session from the cash open: +9.73 points a trade at t = +1.55.**

### Discipline for this test, fixed now

The +9.73 figure was measured on all 46 sessions, so it is a discovery-set
number and cannot also be its own test. From here:

- **The 46 existing sessions are the discovery set. Closed.**
- **Every future session is holdout.**
- **The test is evaluated ONCE, at ~30 new dates.** Not per batch.

Re-running it on each delivery and stopping when t crosses 2 is the peeking
problem, and it manufactures significance from noise as reliably as any of the
six dead findings did. So no interim readings will be reported, including if
asked — the number would not mean what it appears to mean.

### Re-recordings do not count toward it

This batch was five re-recordings: CUM maxfills 1 → 248, 247, 142, 272, 232.
Valuable for order-flow work (39 sessions now carry a working stream) and worth
**zero** for the day-trade test, which needs independent observations.

**Session count is unchanged at 46.**

Missing business days in the July–September window, all of which would count:

- **August**: 27, 28, 31
- **September**: 7, 8, 9, 10, 14, 15, 16, 17, 18, 21, 22, 23, 24, 25, 28, 29, 30

That is 21 dates available without going outside the window; about 30 are
needed, so October would supply the rest.

## Correction: the date list was wrong

The previous entry listed September 16–30 and all of October as dates to
record. Today is 15 September — those sessions have not happened. The
recordable pool is the PAST, and it is not where I said it was.

**Recent history is nearly exhausted.** Only four business days remain
unrecorded between July and today: **23 July, and 9, 10, 14 September.**

**The pool is earlier in the year.** April–June 2026 holds **65** unrecorded
business days, all of which exist in replay now. That is more than twice what
the holdout needs, available without waiting a single day.

That changes the recommendation from "keep recording forward" to **"record
backwards into June, May and April"** — the target can be met immediately
rather than over six weeks of calendar time.

### Note on 7 September

Labor Day. 84,777 tape rows against a normal ~450,000. It is a holiday
session, not a short one, and must be excluded from the day-trade test rather
than counted as an observation.

---

## Pre-registration: three exit variants, one holdout, evaluated once

Hold-to-close is **not** withdrawn. It is the strongest result here and a
trader's constraint decides what is tradeable, not what is true. If it confirms
while the bounded versions do not, that is itself the answer: the signal is
real and the constraint is what blocks it — which is an argument about position
size, automation or risk appetite, not about the research.

Fixed now, before any holdout session is looked at.

### The signal (identical in all three)

At each minute, VWAP displacement standardised against the session so far
(expanding window — never the full day). Top quintile → short. Bottom quintile
→ long. One position at a time.

### The three exits

| # | exit | discovery-set result | trader can take it |
|---|---|---|---|
| 1 | **17:00 UTC** (22:30 local) | +9.73 pts, t +1.55 | yes |
| 2 | **19:00 UTC** (00:30 local) | +13.02 pts, t +1.49 | marginal |
| 3 | **session close, 20:00 UTC** | +21.70 pts, t +2.14 | not as stated |

### The bar

Three tests, so a single one clearing t = 2 proves nothing — at 5% across
three, one false positive is roughly a one-in-seven event. Bonferroni gives
each test **p < 0.0167**, which is about **t ≥ 2.4** at this sample size.

To pass, a variant needs:

- per-session mean **positive after 2 points of cost**
- **t ≥ 2.4** on holdout sessions alone
- the **sign stable** between the discovery set and the holdout

### The holdout

Every session recorded after the 46-session discovery set. Currently **5**
(7 September excluded as a holiday). Target ~30.

Evaluated **once**, all three variants together, when the holdout is complete.
No interim readings — a result peeked at repeatedly does not mean what it
appears to mean, and that is how several of the seven dead findings here got
their credibility in the first place.

### If hold-to-close passes and the others do not

The honest options are then a resting bracket left in the market rather than
watching it, a smaller size that makes the overnight-adjacent risk tolerable,
or accepting that the edge exists and is not reachable under the current
constraints. Which of those is right is the trader's call, not a research
question — but it only becomes a live question if the test passes.

---

## June backfill, and two things the bookkeeping was hiding

Five June sessions ingested: **17, 18, 19, 22, 23 June**. All new dates, all
with a working cumulative stream (fills per order max 80–224, so none of them
predate the `OnUpdateCumulativeTrade` fix). Totals: 58 dates on disk.

Ingesting them prompted the first proper audit of session *coverage*, and it
turned up two problems that had nothing to do with June.

### Four recordings are not full cash days

| date | RTH ticks | last print | coverage |
|---|---|---|---|
| 19 June | 27,188 | 16:59 | 54% |
| 3 July | 21,679 | 16:59 | 54% |
| 7 September | 23,259 | 16:59 | 54% |
| 12 July | 0 | — | 0% |

Median on a normal session is **346,000** RTH ticks. The three at 16:59 are CME
early closes at 13:00 New York — Juneteenth, the day before Independence Day,
and Labor Day. 12 July is a Sunday.

Every study in this project guards with `len(s) > 5000`. A half day clears that
by a factor of five, so **3 July has been counted as an ordinary session in the
discovery numbers all along**, and 19 June would have walked straight into the
holdout. Only 7 September was ever caught, and only because its file was
conspicuously small.

They are now excluded by `tape.is_full_session`, on coverage and tick count
alone. The reason is not that they perform differently — that has not been
looked at — it is that **the tested rule is undefined on them**: the 19:00 UTC
exit has no data, and "the close" means 13:00 New York on those days and 16:00
on every other, which is a different trade.

### The discovery/holdout split was a count, not a roster

"46 sessions" was a tally kept by hand across batches. Nothing in the code
could answer whether a given date was discovery or holdout, which is precisely
how a holdout stops being one. It is now pinned by date in
`scripts/orderflow/roster.py`:

```
DISCOVERY   2026-07-01 .. 2026-09-08          47 sessions
HOLDOUT     everything outside, plus 23 July   7 sessions
```

Two corrections fall out, and **both cost sessions rather than adding them**:

- The hand tally said 46; the window holds 47 usable. The window governs from
  here because it can be checked.
- **2, 3, 4 and 8 September were previously called holdout.** They were on disk
  when the discovery table was last restated, so they cannot be called unseen.
  They move to discovery. The holdout drops from 7 to 3, and the June backfill
  puts it back to 7.
- 23 July is inside the window by date but was never recorded, so no fit has
  seen it. It is holdout. Recording that **now**, before any holdout number
  exists, is the whole point of writing it down.

**Holdout: 7 of ~30.** Unchanged in size, different in membership, and for the
first time it is a list rather than a number.

## The replay window is nearly empty

ATAS replay reaches back three months — to about **15 June**. Within 15 June
to 14 September there are 66 business days and **57 are already recorded**.

**Nine remain: 15, 16, 24, 25, 26, 29, 30 June; 23 July; 14 September.**

All nine are holdout-eligible. Recording every one of them takes the holdout to
**16**, and that is the ceiling from history. The rest can only come forward in
calendar time, one session a trading day.

## The test as pre-registered cannot be won at 30 sessions

This should have been computed before the target was set rather than after. It
uses only the discovery-set figures already published; no holdout session is
read.

The per-session effect size implied by each discovery t is `t / √47`. Carrying
that forward against the pre-registered bar of **t ≥ 2.4**:

| exit | discovery t | effect/sd | n=16 | n=30 | n=47 | n=108 |
|---|---|---|---|---|---|---|
| 17:00 UTC | +1.55 | 0.226 | 7% | **12%** | 20% | 48% |
| 19:00 UTC | +1.49 | 0.217 | 6% | 11% | 18% | 44% |
| close | +2.14 | 0.312 | 12% | **25%** | 40% | 80% |

Those are powers: the chance the test passes **if the discovery effect is
exactly real**.

At the 30 sessions the plan called for, the 17:00 exit — the only one that can
actually be traded — fails **88% of the time when it is right**. Sessions
needed for an even chance: **113** for the 17:00 exit, **60** for the close.
For 80%: **206** and **108**.

So a null result at 30 sessions would mean almost nothing, and the plan as
written was set up to produce one and call it an answer.

**The bar does not move.** Lowering t ≥ 2.4 after seeing this would be the same
error as peeking, wearing a lab coat. Three things follow instead, all fixed
now:

1. **The outcome set gains a third value.** Confirmed / refuted / **inconclusive
   for want of power** — and at n < 60 the honest verdict for a near-miss is
   the third, stated as such rather than dressed as a refutation.
2. **Record all nine remaining replay dates**, then forward from 16 September.
   Sixteen by the weekend, thirty by roughly 5 October, sixty by late November.
3. **The statistic is worth improving before the test, not the threshold.** The
   session-level mean in raw points is noisy largely because a session's P&L
   scales with its range; normalising by session range, or taking one trade per
   session instead of every qualifying bar, may raise t materially without
   touching the rule being tested. That work belongs on the **discovery set**,
   which is what a discovery set is for, and whatever it produces must be
   written down before the holdout is opened.

Nothing in this entry looked at a holdout session.

---

## Second June block, and the replay window is spent

24, 25, 26, 29, 30 June ingested. All full cash sessions, all with a working
cumulative stream. **63 dates on disk; holdout 12.**

June is exhausted. Replay does not reach 15 and 16 June after all, so the only
recordable dates left in history are **23 July and 14 September** — a ceiling
of **14**, not the 16 estimated last entry. Everything past that arrives one
session per trading day, so the test runs as an open loop: each batch is
ingested, the roster updated, and nothing is evaluated until the holdout is
complete.

## The feed is on a 5-point grid, and NQ trades in 0.25

Building the footprint turned this up, and it is the more important of the two
results.

Every recorded price is a whole multiple of **5.00**. Not the tape only — all
three streams:

```
TAPE  2026-09-08 00:01:00.082,29585,1,B
CUM   2026-09-08 13:30:00.000,S,29645,29645,1,1
L2    2026-09-08 13:30:00.003,B,0,29640.00,60
      2026-09-08 13:30:00.003,B,1,29635.00,94
```

Level 0 and level 1 of the order book are **five points apart**. In a real NQ
book they are 0.25 apart. A whole session touches 54–114 distinct prices where
it should touch two thousand.

This is upstream of the recorder — depth level prices come straight off the
feed object — so it is the instrument, the chart type, or the data source. A
diagnostic is now in the recorder (`2026-09-16.n`): it tracks the smallest gap
between consecutive prints and prints it beside whatever the platform says its
step is, with an explicit warning when the two disagree. **Run it once and the
status file will name the cause.**

What it costs, and what it does not:

- **Unaffected:** bars, VWAP, CVD, levels, structure, the day-trade test.
  Anything that divides one tick count by another has the error cancel.
- **Degraded:** sweep depth in `bigorder.py` is overstated twentyfold. The
  ranking is monotone so the gate's verdict — dead — stands.
- **Blocked:** the footprint proper. One rung of that ladder holds twenty real
  prices, and separating prices is the only thing a footprint does.

## Footprint: the eighth finding to die

Built the real thing from the tape at 5-minute bars — bid and ask volume at
every price, then the five shapes a footprint trader actually reads: diagonal
imbalance at 3:1, stacked imbalance at 3+, unfinished auction at the extremes,
bar POC position, and absorption at the extremes. Discovery set only. **The
holdout is sealed against every study, not just the VWAP one** — spending it on
a second family of features would spend it just as surely, and it cannot be
refilled.

**The first pass was wrong and it is worth recording how.** I indexed the
ladder in 0.25 steps on a 5-point grid, so nineteen of every twenty rungs were
empty and every traded price was compared against a guaranteed zero. Result:
every bar "imbalanced", stacks impossible (0.00% of bars), and buy and sell
imbalance counts correlating **+0.99 with each other and +0.996 with the bar's
range**. They were not imbalances. They were the bar's width, counted twice —
and they scored t = +2.46 while being nothing at all.

Rebuilt on the grid the data actually uses, the whole imbalance family
collapses: b_imb at 5 minutes goes from **+2.46 to −1.04**.

One shape survived to a real test. `absorb_lo` — buy volume at the bar's lowest
price as a share of the bar:

| horizon | IC | t | after residualising on the bar's own body |
|---|---|---|---|
| 5m | −0.0545 | **−3.56** | −0.0548, t −3.55 |
| 15m | −0.0539 | −2.90 | −0.0534, t −2.82 |
| 30m | −0.0436 | −2.15 | −0.0444, t −2.14 |

It is not "the bar closed on its low" in disguise — controlling for the body
leaves it untouched. Two things killed it anyway.

**The null produced one just as strong.** Circularly shifted returns threw up
`b_imb` at 30 minutes with t = −3.39 against the best real t of −3.56. One
survivor and one null survivor out of 36 tests is the calibration saying, in
numbers, that this is what chance looks like here.

**And it does not price.** Short the top quintile, exits by clock, 2 points of
cost:

| hold | quintile means (points) | short top quintile |
|---|---|---|
| 5m | +1.34 +1.14 −2.35 −0.47 −1.25 | **−0.75 pts**, t +0.63 |
| 15m | +1.99 +0.04 −4.54 +0.04 −0.13 | **−1.87 pts**, t −0.39 |
| 30m | +0.59 −0.44 −5.78 +2.02 −1.24 | **−0.76 pts**, t +0.32 |

The quintiles do not order, and the worst cell is the **middle** one at every
horizon. That is not a weak edge, it is a wiggle a rank correlation is happy to
score and a trader cannot hold. The mirror shape at the high never showed the
opposite sign either, and a real effect at the extremes should be roughly
symmetric.

**Footprint is dead on this data.** Eighth finding to die, and the first to
fail the null calibration and the points test in the same run.

Whether it would be alive on a true 0.25 tape is genuinely unknown — that is
what the recorder diagnostic is for, and it is worth re-running this study if
the grid turns out to be a settings problem rather than the feed.

---

## Correction: the 5-point grid is a setting, not a defect

Step is set to 20 ticks, so the footprint is deliberately a $5 one. The "feed is
broken" entry above is wrong and the recorder diagnostic will simply report the
configuration working as intended. It is left in — it costs nothing and it means
the grid can never be silently assumed again.

The ladder-indexing bug was separate and real: indexing in 0.25 on a 5-point
grid still put nineteen empty rungs between traded prices. That fix stands.

## The footprint test was asking a quant's question, not a trader's

The bar-level study scored every bar's shape against the next fifteen minutes —
"given this bar, where is price going." No footprint trader works that way. A
footprint marks a **price**; the trade is the **return** to that price. Scoring
3,658 bars dilutes a handful of meaningful prices into invisibility, and would
have read as noise even if the levels were perfect.

Rebuilt as an event study on returns. A level is a rung with ≥2× the bar's
median volume. Price must clear it by 15 points and come **back**. Everything
is measured from the moment of return, which is the only moment a trader has a
decision to make. Matched against ordinary rungs (0.8–1.2×) from the same
sessions through identical machinery.

**The first version of this was broken too**: it called it a return the moment
price touched the level again, usually the next print — a median wait of one
minute. Price had never left. Requiring a departure is what made the test a
test.

### It looked like a finding

| | n | +15m | +30m | +60m | held 30m |
|---|---|---|---|---|---|
| heavy levels | 3,246 | **+4.09** | +2.54 | +0.53 | 50.7% |
| ordinary rungs | 3,191 | +1.38 | −0.31 | −1.02 | 49.1% |

Heavy levels after cost: **+2.88 points at 15 minutes, t = +2.07**, 31 of 47
sessions positive.

### Three controls, and it dies on the third

**Paired against the control, the gap is not significant.** +1.83 pts at 15m,
t = +1.20, 95% CI **[−0.99, +4.71]**. Heavy levels beat *zero*; they do not beat
*ordinary prices*. Beating zero is the flattering comparison and the wrong one.

**The aggressor at the level carries no direction.** Splitting heavy levels into
buyers / even / sellers gives cell numbers that look dramatic — buyers +9.98 at
60m against sellers −5.88 — but the buyers-minus-sellers gap has per-session
t of **+0.41, +0.84, +1.17**, and at 15 minutes it flips sign depending on which
way price approached. Noise with good tailoring.

**And the placebo kills it outright.** Move the level 25 points to a price that
was never a level, change nothing else:

| price used | n | +15m | +30m | +60m | t@15m |
|---|---|---|---|---|---|
| the real level | 3,246 | +2.09 | +0.54 | −1.47 | **+2.07** |
| shifted +25 pts | 3,057 | **+2.43** | +2.36 | +0.35 | +1.41 |
| shifted −25 pts | 3,044 | +1.59 | −0.30 | +0.91 | **+2.09** |

A price 25 points away from the level pays **the same or better**.

**Footprint levels are dead — ninth finding to die, and the first killed by a
placebo rather than a holdout.** The footprint did not find a level. It found a
pullback, and a pullback happens at whatever price you nominate.

### What is actually there, and it is not a footprint thing

The symmetric effect underneath all of it:

```
price leaves a price by 15+ points, then returns   ->  it resumes
    left upward    +2.95 pts over the next 15 min
    left downward  -2.56 pts over the next 15 min
```

Opposite signs, near-equal magnitude — so it is not drift, it is a real
pullback-continuation shape. Worth roughly **+2 points after cost at 15
minutes**, and it decays fast: t +2.07 at 15m, +1.03 at 30m, +0.26 at 60m.

Note the time profile is the **exact opposite** of the VWAP hypothesis, which
strengthens with holding time. Two different effects, if both are real.

**This is not a finding yet and must not be treated as one.** It came out of a
search over thresholds (2× heaviness, 15-point departure, three horizons) on
the discovery set, which is precisely the specification search that produced
seven of the nine corpses above. It needs pre-registering and testing on the
same sealed holdout, and the honest thing is that it has no better claim than
the VWAP rule did at this stage.

It also needs no ATAS, no order flow and no footprint — which is worth saying
plainly given how much of this project has been spent recording them.

---

# Order-flow batch: the four never-measured families, plus the unsafe kills

Pre-registered in `reports/orderflow_batch_preregistration.md`, committed at
`d85b15c` before any test ran. Twelve tests, one horizon, bar |t| ≥ 3.0.

**Provenance.** 16 explored-pile sessions at a verified 0.25 grid:
`0701 0702 0706 0707 0708 0709 0710 0713 0714 0715 0716 0717 0720 0721 0812
0820`. Families C, D and F run on 14 of them — 12 and 20 August are 0.25 tapes
but their cumulative and depth files predate the per-fill and encoded formats.
Recorder lineage `2026-09-16.r` to `2026-09-17.z` for July, original captures
for August. **The eight sealed June dates were not read by any script in this
batch**; they are excluded when each session list is built rather than filtered
afterwards.

## First: the fields are alive now

This is the part the coarse grid made impossible, and it is worth separating
from the results.

| | on the 5-point grid | at 0.25 |
|---|---|---|
| aggressive orders with zero sweep span | 94–97% | **82.0%** |
| orders spanning ≥ 1 tick | — | **18.0%** |
| bars containing a 3+ stacked imbalance | **0.00%** | **21.1%** |
| bars with any diagonal imbalance | (meaningless) | 90.9% |

Stacked imbalance could not physically form before. It now forms in a fifth of
all bars, and the longest run seen is 5. Sweep depth was a near-constant zero
and is now a distribution. **The earlier nulls on these were about the
instrument, not the market** — that classification was correct.

## The twelve tests

| family | feature | IC | t | null t | points after cost | t |
|---|---|---|---|---|---|---|
| C sweep | sweep ≥2 ticks | +0.0187 | +0.80 | +0.23 | −0.35 | −0.23 |
| C sweep | sweep ≥8 ticks | −0.0021 | −0.06 | −1.12 | +1.38 | +0.42 |
| A diagonal | imbalance net | +0.0122 | +0.47 | +1.42 | −1.72 | −1.03 |
| A diagonal | at the extremes | −0.0012 | −0.06 | −2.67 | −0.84 | −0.36 |
| B stacked | 3+ stack net | −0.0239 | −1.22 | −1.27 | — | — |
| B stacked | run length | +0.0187 | +0.68 | −0.76 | −1.96 | −1.30 |
| E absorption | absorb net | −0.0451 | −1.54 | +1.04 | −1.94 | −1.55 |
| E absorption | unfinished net | −0.0518 | −1.63 | −0.77 | — | — |
| **D book** | **imbalance ≤ 1 pt** | **+0.0763** | **+3.05** | −0.59 | +1.88 | +0.64 |
| D book | imbalance ≤ 5 pt | −0.0066 | −0.29 | −0.05 | +2.38 | +0.97 |
| F pull/fill | size pulled | −0.1025 | −2.12 | +1.70 | −4.05 | −0.66 |
| F pull/fill | size filled | −0.0791 | −1.43 | −0.94 | −1.41 | −0.21 |

**One of twelve clears the IC bar. None clears all three gates.**

## The one survivor, and why it is not a finding

Book imbalance **within one point of the touch** scores IC +0.0763 at t = +3.05
against a null of −0.59. It is the only thing in this batch that is not noise,
and it says something specific: the same measure taken over **five** points is
t = −0.29. The information is at the touch and nowhere else.

That reproduces, on 14 sessions, the "monotonic degradation" ordering that was
previously asserted from **one** session. The Group 3 classification was right —
the conclusion stood, the reasoning did not, and now it does.

**It does not pay.** +1.88 points a trade after cost at t = +0.64, 10 of 14
sessions positive. Pre-registration called this outcome in advance: a feature
clearing correlation but failing the points test is reported as a correlation
that does not trade, not as a finding.

## Would more sessions settle it?

| | effect/sd | sessions for t ≥ 2 | expected t at 53 sessions |
|---|---|---|---|
| the correlation | 0.815 | 7 | 5.93 |
| **the trade** | **0.171** | **137** | **1.25** |

Fifty-three is every explored-pile day re-recorded — the 16 held plus the 37
remaining. **Finishing the re-record takes the trade's t from 0.64 to about
1.25.** It does not settle it. Settling it needs roughly 137 sessions for a
two-sigma answer and 308 for three, which is six to fourteen months of
recording for a signal already measured at under two points a trade.

## Recommendation

**The order-flow branch is done. Move to the pullback work.**

Not because the data was bad — it is now good, and the fields that could not
form are forming. Because with a real 0.25 grid, per-fill sweep detail, a true
book and an unaligned quote stream, eleven of twelve pre-registered features are
indistinguishable from their own shuffled nulls, and the twelfth is a
correlation worth under two points that would need an order of magnitude more
data than exists to prove it covers its own cost.

**Do not finish the re-record for order flow's sake.** The arithmetic above is
the reason: 37 more days moves the only live number from 0.64 to 1.25.

**Do keep recording, for a different reason.** The pullback candidate and the
VWAP holdout both need sessions the strategy has never seen, and re-recorded
days are better data for them than the coarse originals. That is a strategy-work
argument, not an order-flow one, and it should not be dressed as this batch
having found something.

## What this closes

Sweep depth, diagonal imbalance and stacked imbalance move from **never
measured** to **measured and null**. Extreme absorption and the BOOK ladder
family move from **unsafely killed** to **killed on data that can carry the
question**. Book imbalance moves from **one session** to **fourteen**, and its
verdict is now specific: real at the touch, absent one point further out, and
too small to trade.

---

## Correction: every prior "22:30 local" was an IST deadline, and it was wrong

Confirmed by the trader: **Dubai, UTC+4. The flat time is 18:30 UTC.**

Every earlier statement in this record that reads "22:30 local" was computed
against **17:00 UTC**, which is 22:30 India Standard Time. That is ninety
minutes earlier than the real constraint.

What it touches:

- The three pre-registered VWAP exits were 17:00 UTC (+9.73 pts, t +1.55),
  19:00 UTC (+13.02, t +1.49) and the close (+21.70, t +2.14). The first was
  labelled "the only one a trader can take" **on the wrong clock**. Under the
  real 18:30 deadline the 17:00 variant is legal but no longer the boundary
  case, the 19:00 variant is illegal by thirty minutes rather than legal-ish,
  and hold-to-close remains illegal by ninety.
- The conclusion those figures fed — that the tradeable exit is the weakest of
  the three — is unchanged in direction, because 18:30 sits between 17:00 and
  19:00 and the series was monotonic. But the specific number attached to "what
  the trader can actually take" was never measured at the trader's actual
  deadline.

No result is rescued by this and none is invalidated outright; the point is
that a constraint was carried for weeks in the wrong timezone and every
statement conditioned on it inherited the error. The constant is now a single
named value and the pullback work uses 18:30 UTC.

---

# Pullback batch: all 12 rejected, and the rejection is about my specification

Run against `reports/pullback_preregistration.md`, committed at `7f19544`
before the code existed. **20 discovery sessions at 0.25**, sealed days not
read, flat 18:30 UTC, 2.0 points a round turn, max two trades a session.

## Trade counts first

| variant | trades | sessions | per session |
|---|---|---|---|
| OR15 EXC0.5 (×3 targets) | 26 | 15 | 1.73 |
| OR30 EXC0.5 (×3) | 16 | 9 | 1.78 |
| OR15 EXC1.0 (×3) | 11 | 8 | 1.38 |
| OR30 EXC1.0 (×3) | 7 | 4 | 1.75 |

Only one of the four setup definitions reaches the 15-session minimum at all.

## All 12 rejected

Every variant fails on expectancy, profit factor, top-five dependence and the
split-half. Per-session t ranges from −0.51 to −2.67; **no variant has a single
positive half.**

## The rejection does not mean what it looks like

Every trade in the entire grid has **exactly the same risk: 2.00 points.**

```
distinct risk values across all trades: [2.0]
```

That is not a property of the market, it is arithmetic I built in:

```
trigger = pullback extreme + REJ_TICKS  × 0.25 = +1.00
stop    = pullback extreme − STOP_TICKS × 0.25 = −1.00
risk    = trigger − stop                       =  2.00   always
```

Both offsets are fixed tick counts from the **same** price, so the risk can
never be anything else. Cost is 2.00 points. **The cost is 100% of the risk on
every trade.**

What that forced:

| target | winner nets | loser nets | breakeven win rate | observed |
|---|---|---|---|---|
| 1.0R | **+0.00** | −4.00 | impossible | 0.0% "wins" |
| 1.5R | +1.00 | −4.00 | **80.0%** | 73.1% |
| 2.0R | +2.00 | −4.00 | **66.7%** | 61.5% |

At 1.0R a winning trade nets **exactly zero**, which is why those three
variants report a 0% win rate — not one trade made money, by construction. At
1.5R the rule needed to be right 80% of the time and managed 73%. At 2.0R it
needed 67% and managed 62%.

Those are not bad hit rates for a pullback entry. They lost because a 2-point
stop on NQ is roughly one second of noise and the round turn costs as much as
the entire risk.

**So this batch tested whether a 2-point stop can survive a 2-point round trip.
It cannot, and that was decidable with arithmetic before any data was touched.**
I should have caught it when fixing the constants and did not.

## What is and is not established

**Established:** the specification is unusable. `REJ_TICKS` and `STOP_TICKS`
cannot both be fixed offsets from the pullback extreme, because that pins risk
to a constant independent of the session, the instrument's volatility and the
size of the move being retraced.

**Not established:** anything about pullback continuation. The hypothesis was
never given a risk large enough to clear its own costs, so these twelve
rejections carry no information about it. Recording them as a kill would be
exactly the failure mode flagged before this batch began — a verdict resting on
a test that was never properly conceived.

## The corrected specification, for approval before it runs

The stop must be anchored to structure, not to a tick count:

```
stop = pullback extreme − dir × max(STOP_MIN_TICKS × 0.25, STOP_ATR × ATR)
```

with the trigger unchanged, so risk scales with the session's own volatility.
On these sessions a 20-bar one-minute ATR runs 8–15 points, which puts a
typical stop at 4–8 points and cost at 25–50% of risk rather than 100%.

That is one changed line and it does not touch a single trading constraint:
still two trades, still never concurrent, still hard stop at entry, still flat
at 18:30 UTC, still 2.0 points of cost. The grid stays at 12 by swapping the
`EXC` axis for `STOP_ATR ∈ {0.5, 1.0}` and keeping `EXC` fixed at 0.5, which is
the only value that produced enough sessions to test.

**I have not run it.** The spec changed after seeing a result, even though what
was seen is a construction error rather than a performance number, and that
distinction is exactly the sort a person should get to judge rather than have
assumed on their behalf.

---

# Pullback grid 2: a properly conceived test, and it finds nothing

Pre-registered at `1a02a18`, run after. 20 discovery sessions at 0.25, sealed
days not read, flat 18:30 UTC, 2.0 points a round turn, max two trades a
session, `EXC` fixed at 0.5 (data-informed, logged).

## Trade counts first

| variant | trades | sessions | per session | expiry | avg risk |
|---|---|---|---|---|---|
| OR15 SATR0.5 (×3) | 25–26 | 15 | 1.7 | **0%** | 17.2 |
| OR15 SATR1.0 (×3) | 26 | 15 | 1.7 | **0%** | 33.7 |
| OR30 SATR0.5 (×3) | 16 | 9 | 1.8 | **0%** | 15.4 |
| OR30 SATR1.0 (×3) | 16 | 9 | 1.8 | **0%** | 29.9 |

**The specification fault is fixed.** Risk now runs 15 to 34 points and varies
trade to trade, so cost is 6–12% of risk rather than 100%.

**My pre-run prediction about expiry was wrong.** I said expiry exits would be
a large share, particularly at wide stops. They are **zero** in all twelve
variants — every trade resolved at its stop or its target inside the hour.
Recording that because a prediction made before a run is worth nothing if it is
quietly dropped afterwards.

## All 12 rejected again — but this time the test was sound

Expectancy runs −0.87 to −5.76 points a trade. Profit factor 0.48 to 0.96.
Per-session t from −0.10 to −1.42. Every variant fails on expectancy, profit
factor, top-five dependence and the split-half.

## Why this rejection means something and grid 1's did not

The question is whether the rule beats a coin **on its own stop and target**.
For a random walk, `P(hit +M×R before −R) = 1/(1+M)`.

| variant | n | observed | random walk | breakeven | vs random |
|---|---|---|---|---|---|
| OR15 SATR0.5 R1.0 | 26 | 46.2% | 50.0% | 55.8% | −3.8 |
| OR15 SATR0.5 R1.5 | 25 | 36.0% | 40.0% | 44.7% | −4.0 |
| OR15 SATR0.5 R2.0 | 26 | 30.8% | 33.3% | 37.2% | −2.5 |
| OR15 SATR1.0 R1.0 | 26 | 50.0% | 50.0% | 53.0% | +0.0 |
| OR15 SATR1.0 R1.5 | 26 | 38.5% | 40.0% | 42.4% | −1.5 |
| OR15 SATR1.0 R2.0 | 26 | 26.9% | 33.3% | 35.3% | −6.4 |
| OR30 SATR0.5 R1.0 | 16 | 43.8% | 50.0% | 56.5% | −6.2 |
| OR30 SATR0.5 R1.5 | 16 | 37.5% | 40.0% | 45.2% | −2.5 |
| OR30 SATR0.5 R2.0 | 16 | 37.5% | 33.3% | 37.6% | +4.2 |
| OR30 SATR1.0 R1.0 | 16 | 56.2% | 50.0% | 53.3% | +6.2 |
| OR30 SATR1.0 R1.5 | 16 | 43.8% | 40.0% | 42.7% | +3.8 |
| OR30 SATR1.0 R2.0 | 16 | 37.5% | 33.3% | 35.6% | +4.2 |

**Eight of twelve sit below the random-walk rate and four above, and not one is
statistically distinguishable from it** — the smallest binomial p is 0.32.

That is the finding. **The rule is a coin flip on its own stop and target, and
a coin flip cannot pay a round turn.** Costs did not eat a thin edge; there was
no edge to eat. Every variant needs 2 to 6 percentage points over random and
delivers, on average, slightly less than random.

The four "above random" cells are all `OR30`, all on 16 trades over 9 sessions,
and they fail the 15-session minimum anyway. They are what four cells out of
twelve look like when the true rate is the coin.

## Status of the hypothesis

The original pullback observation — price leaves a price by 15 points, returns,
and resumes, worth +2.95 and −2.56 points over 15 minutes — was measured by
taking **every** qualifying signal, about 69 a session, with no stop and no
cost discipline. Under two trades a day with a hard stop and a real round turn,
**it is gone.**

That is not a contradiction. A tiny per-event drift spread across seventy
overlapping observations a day is not the same object as a trade you can take
twice, and the placebo attached to the original result already showed the
specific price did no work.

**Two grids, 24 variants, 20 discovery sessions, nothing above a coin.** The
sealed days are not needed and must not be spent: a holdout tests something
that survived discovery, and nothing here did.

## Where that leaves the project

Every mechanical hypothesis tried under the real constraints has now failed on
discovery. What has not been tried is the one thing the constraints point at
directly: the trader takes **two** trades a session, so the binding question is
not "does this pattern have an edge" but "which two moments in a session are
worth acting on". Every test so far has answered the first question with a rule
that fires whenever its conditions are met, which is a different problem.

That is a new direction, not a retest, and it needs its own pre-registration
and the trader's agreement before anything is run.

---

# CLOSED: the pullback family

**Reason for closure: the rule is indistinguishable from a coin flip on its own
stop and target.** Across 12 variants in grid 2, measured against
`P(hit +M×R before −R) = 1/(1+M)`, eight sat below the random-walk rate and four
above, and **not one differed from it significantly** — the smallest binomial p
was 0.32. Every variant needed 2 to 6 percentage points over a coin and
delivered, on average, slightly less than a coin.

That is a stronger statement than "it lost money". A losing rule might have an
edge eaten by costs; this one has no edge to eat.

**Consumed:** two grids, 24 variants, 20 discovery sessions. **Sealed days: not
spent.**

**Cannot be reopened without new data.** Not new parameters, not a new anchor,
not a different target ladder — new *sessions*. The discovery set has now been
searched twice over this family and a third pass would be fitting noise.

---

# How much can 20 sessions actually see?

The question that decides whether to finish the re-record.

## The noise, measured

Per-session P&L standard deviation on the 12 grid-2 variants:

| stop setting | sd per session | avg risk | trades/session |
|---|---|---|---|
| OR30 SATR0.5 (tightest) | **13.9** | 15.4 | 0.80 |
| OR15 SATR0.5 | 18.5–28.2 | 17.2 | 1.30 |
| OR30 SATR1.0 | 30.1–38.9 | 29.9 | 0.80 |
| OR15 SATR1.0 (widest) | **43.1–55.1** | 33.7 | 1.30 |

Median **29.2 points a session**. Variance scales with the stop, which is the
trap: tightening the stop cuts the noise but raises cost as a share of risk,
and grid 1 is what happens at the far end of that trade-off.

## Minimum detectable edge, 80% power, two-sided 5%

`MDE = 2.80 × sd / √n`, at the median sd of 29.2:

| sessions | MDE per session | per trade |
|---|---|---|
| **20** (now) | **18.3 pts** | 10.7 |
| **53** (re-record finished) | **11.2 pts** | 6.6 |
| 65 (entire replay window) | 10.1 pts | 5.9 |
| 250 | 5.2 pts | 3.0 |
| 1,000 | 2.6 pts | 1.5 |

At the tightest viable stop (sd 13.9) those halve: 8.7 points at 20 sessions,
4.8 at 65.

## Sessions required for a real edge

| edge per session | per trade | sessions | years at 250/yr |
|---|---|---|---|
| 1 pt | 0.6 | **6,674** | 26.7 |
| 2 pts | 1.2 | **1,668** | 6.7 |
| 3 pts | 1.8 | 742 | 3.0 |
| 5 pts | 2.9 | 267 | 1.1 |
| 8 pts | 4.7 | 104 | 0.4 |

At the tightest stop, the 2-point row falls to about 380 sessions and the
3-point row to about 170.

## The answer

**A genuinely good discretionary futures day trader nets on the order of one to
two points a trade after costs.** At 1.3 trades a session that is 1 to 3 points
a session — the top three rows. **Detecting it requires roughly 400 to 1,700
sessions.**

**Twenty sessions can only see an edge of 18 points a session**, which on a
50k account at one contract is about 180% a year. Any edge that large would be
visible without a backtest.

**Finishing the re-record does not change this.** Fifty-three sessions detects
11 points a session. And the binding limit is harder than that: **ATAS replay
reaches back three months, about 65 sessions total.** Even exhausting it
entirely, the floor is roughly 5 to 10 points a session. **A realistic edge is
not detectable from ATAS replay data at these constraints, at any point, ever.**

That is not a statement about the market. It is arithmetic about two trades a
session against a 15-to-34-point stop.

## What this means for the re-record

**Stop it.** The 0.25 re-record was worth doing for the order-flow question,
which needed tick-level price separation and is now answered. For strategy
validation it cannot reach the required sample, and 37 more days changes the
detection floor from 18 points to 11.

## The only sample that could answer it

Already on disk, and it is not ATAS:

```
QQQ 1-minute   553,973 bars   1,421 sessions   2021-01 .. 2026-08
QQQ 5-minute   208,941 bars   2,680 sessions   2016-01 .. 2026-08
```

**1,421 sessions is exactly the range required.** The honest caveats: QQQ is
not NQ, one-minute bars cannot order a stop against a target inside a bar, and
the cost structure differs. But with a 15-to-34-point stop the intra-bar
ordering problem is small — it was fatal at a 2-point stop and is minor at
twenty times that — and the pessimistic convention already in the backtest
(stop before target) bounds the error in the conservative direction.

**This inverts the order of work:** screen wide and cheap on years of bar data,
then verify narrow and expensive on NQ tick data for whatever survives. This
project did it the other way round, which is why twenty sessions of
beautifully-recorded ticks cannot answer a question a proxy with seventy times
the sample could.

## On the "which two moments" idea — the sample it would need

Selecting the best two moments from roughly 78 five-minute bars is a ranking
problem over a large candidate space. Fitting it on 20 sessions would find
noise with certainty. Before any such thing is proposed it needs a data source
of **at least 500 sessions**, and the MDE arithmetic above applies on top of
the selection cost, not instead of it. **Not proposed now.**

---

# The QQQ screen ran. 0 of 16. And two defects came out of it.

`reports/bar_resolution_gate.md`, `reports/qqq_screen_result.md`.

## The result

| | |
|---|---|
| QQQ sessions | **1,418** (2021-01-04 to 2026-08-31) |
| trades per variant | 1,425 to 2,175 |
| variants surviving | **0 of 16** |
| significantly negative | 4 (t −3.4 to −4.5) |
| positive in ≥4 of 6 years | **none** |

Target hit rates land within a couple of points of the random-walk rate at
every target from 1R to 4R. The rule is a coin; the cost is 6–11% of risk; the
coin loses. Extending to 3R and 4R — the cells needing the least edge, which
grid 2 never reached — did not rescue it.

**The pullback family is finished, and now on a sample big enough that the
absence of an edge is a measurement rather than a shrug.**

## Two defects, both of which flattered the rule

**1. Entry lookahead.** The `ARMED` state updated the pullback extreme with the
current bar and then asked whether that same bar had crossed extreme + 4 ticks.
Same-bar entries: 34.5% at one second, **72.3% at one minute** where the bar is
28 points wide. Fixed.

**2. A stop order assumed to fill at its own trigger.** On **90.8%** of QQQ
one-minute entries the bar had already opened past the trigger, so the trigger
price was never on offer. Mean unmodelled slippage **+0.561R**, against
expectancies of +0.24R to +0.55R. **The edge was the defect.** Entries now fill
at `max(trigger, open)`; stop exits gap through the same way.

## What each defect was pretending to be

Defect 2 scaled with bar width, so it looked exactly like a resolution effect:
the tape said −0.19R, five-minute bars said +0.90R at a session t of +2.96, and
the paired divergence was t +4.87. An earlier version of the gate report read
that as a real finding — "wait for the candle to close rather than chasing the
first bounce off a tick low" — and built a mechanism for it. **That hypothesis
is withdrawn in full.** With honest fills the one-minute grid reproduces the
tape to within 0.003R on every trade.

Before the fill fix the QQQ screen returned **16 of 16 surviving, t +5.8 to
+16.5, every year positive, a 74% win rate at 1R**. Nobody leaves that in QQQ
minute bars since 2021.

## The rule that earned its keep

**A favourable-looking difference between two ways of measuring the same rule
is almost always a defect in the more favourable one.** Twice today an
extraordinary result was treated as a defect until proven otherwise, and twice
it was a defect.

## Corrections to previously reported numbers

Grid 2 carried defect 1. Re-run with both fixes, all twelve variants are
negative on expectancy (best −3.65 pts, worst −11.36) against a published table
where some were near zero. **Survivors were 0 of 12 and remain 0 of 12.** The
verdict is unchanged; the numbers moved and are corrected here because they
moved.

## What is not settled

NQ's cash open follows a live overnight auction; QQQ's follows a closed book.
If the edge lives entirely in that difference, this screen could not see it.
Named before the run, still true — but it is a narrow escape hatch for a rule
that performs at coin-flip rates on 1,418 sessions of an instrument tracking
the same index.

**Sealed days: still sealed.** Eight June days and 23 July have never been read.

---

# ORB with a session VWAP filter: 0 of 16. Third fill-model defect found.

`reports/orb_vwap_preregistration.md` (declared at `bbbddb1`),
`reports/orb_vwap_result.md`.

| | |
|---|---|
| QQQ sessions | **1,418**, every one producing a trade at `OR_MIN` 15 |
| trades per variant | 2,578 to 2,740 |
| survivors | **0 of 16** |
| best variant | OR15 SATR1.0 R4.0 — exp **+0.012R**, t **+0.29**, PF 1.01 |

## A nearer miss than the pullback, and precisely why

At the wider stop and wider targets the rule does beat the coin: **+1.9 points
at 3R and +2.4 at 4R**. Cost needs +1.3 to +1.5. So it arrives at breakeven and
stops — t +0.29 on 2,619 trades. With a sample that size, flat means flat, not
underpowered. The tighter stop is worse at every target, which is the opposite
of how a real effect usually behaves.

## The third defect: pre-entry stop-outs

First run: −0.26R to −0.75R, a 1R target hitting **19.6%** against a coin's
50%, session t of **−49**. Broken, not losing.

For a breakout the trigger sits at the top of the bar's travel, so the entry
bar's low is usually pre-entry price action: **73.9%** of entry bars opened on
the far side of their trigger, **44.9%** of trades had an entry-bar adverse
extreme beyond the stop, and **87.8% of those** opened on the far side. The
model was being told something false about sequence. The pullback family was
immune because its trigger was a rejection off a *prior* bar's extreme — the
same switch was worth 0.07R there and most of the result here.

## The slippage audit paid for itself on its first outing

Over **half** of all entries gap past the trigger, double the pullback rate,
because a breakout trigger sits where price is accelerating. Phantom of +0.04R
to +0.16R — and **seven of the eight `OR_MIN` 15 variants report positive
expectancy under the naive fill and negative under the honest one.** Without
the fix made two families ago, this screen would have produced eight apparent
winners.

## The VWAP filter is decorative

It vetoes **9.0% to 35.8%** of signals, changes the trade count by **5 to 18
out of ~2,700**, and changes expectancy by **+0.005R to +0.017R**. A vetoed
breakout is replaced by a later one in the same session, so it substitutes
rather than reduces. My pre-registered prediction guessed the veto rate would
be under 15% — it is higher, and the filter is decorative anyway. The
prediction was aimed at the wrong quantity: veto rate measures how often a
filter fires, not whether it helps.

## Regime findings worth keeping

- **92% of breakouts fire in the first hour.** The time-of-day axis is
  effectively one bucket; the +0.40R in the `180+` column rests on **18 trades**
  and is noise.
- **Narrow opening ranges are worse than wide ones, in 13 of 16 variants.**
  Opposite to the folklore that a tight range coils for a big move. Decent
  sample in every bucket. Logged as a description of this data, not a
  hypothesis.
- **`OR30 SATR0.5` is positive only in 2022** across every target. A
  volatility artifact.
- The one near-positive variant has its **worst year in 2026**, the most recent.

## Three screens, three sequencing defects

1. Entry lookahead — trigger computed from the bar it was tested against.
2. Unavailable fill — a stop order credited with its own trigger price.
3. Pre-entry stop-outs — the entry bar's adverse range charged to a trade that
   did not yet exist.

All three inflate results in proportion to bar size. All three are now fixed
and instrumented as standing output.

**Sealed days: still sealed, still never read.**

---

# OR height promoted to a hypothesis: 0 of 4. The gradient was a sign count.

`reports/or_height_preregistration.md` (declared at `9307834`),
`reports/or_height_result.md`.

## Result

| | |
|---|---|
| in sample | 1,418 QQQ sessions, 1-minute, 2021–2026 |
| held out | 1,256 sessions, 5-minute, 2016–2020, never previously read |
| variants | **4** of a 6 budget; **2 left unspent** |
| survivors | **0 of 4** in sample, **0 of 4** held out |
| largest gradient | **+0.083R at Welch t +1.21**; two of four have the wrong sign |

## Correcting my own over-read

The ORB screen's "narrow worse than wide in 13 of 16 variants" was presented as
"the one consistent gradient in the whole screen". **It was a count of signs,
not of effects.** Applying the same split to all sixteen cells: 14 of 16 signs
positive, **largest Welch t anywhere +1.72**. Sixteen heavily overlapping cells
sharing sessions and trades will agree on the sign of a small common noise term
— that is what the count measured.

**And the gradient was concentrated at `STOP_ATR` 0.5**, the setting dropped
from this grid for being worse at every target. The gradient was largest exactly
where the underlying rule was least credible.

**My threshold choice was not the reason it looks weak.** I checked the tails
(<0.8 vs >1.2, the cuts the gradient was first seen at) at the wide stop: t of
+0.11 to +1.04. As weak as the median split.

## The bridge check failed, and the design fault was mine

Signs disagreed on all four variants between 1-minute and 5-minute over the same
years, so per the pre-registration the held-out run was **withdrawn rather than
explained away**. Two reasons, one of them my fault:

1. **The test was too weak to be informative.** I specified sign agreement
   without anticipating that both quantities would sit within noise of zero.
   Comparing signs of two near-zero measurements fails about as often as a coin.
2. **The 5-minute grid genuinely is not the same rule.** Realised risk came out
   **19% wider** than my scale constant intended, and flat-time exits were **13×
   more common**, because waiting for a 5-minute bar to close delays entry.

The withdrawal cost nothing: the held-out run was 0 of 4 as well.

## The largest phantom yet measured

On 5-minute bars, **over half of all entries gap past the trigger** and the naive
fill reports **+0.78R to +1.04R** where the honest one reports roughly zero.
Phantom of **+0.47R to +1.08R**. A five-minute backtest of this rule with a
trigger-price fill would look like an outstanding strategy and be entirely
imaginary. The artifact scales with bar width exactly as the last two families
predicted.

## Instrumentation

**Entry lookahead: 0 entries**, all three runs, all four variants. Ambiguous
bars 0.0% on 1-minute, 0.2–0.3% on 5-minute — the calibration gate's prediction
that a 1.0 ATR stop with a 3R–4R target puts the stop-to-target span four to
five times the bar held exactly.

## The plain statement

**Index breakout structures are exhausted at these constraints.** Three screens
on 1,418 QQQ sessions returned 0 of 16, 0 of 16 and 0 of 4. The one piece of
structure that survived the second dissolved when isolated and tested directly.

**The next move is a different instrument or a different session, not another
variant of this one.** No rescue filter is proposed and none will be.

**Sealed NQ days: still sealed, still never read.**

---

# European vs US session on NQ: same market, different hour, worse terms

`reports/european_session_data_inventory.md`,
`reports/european_vs_us_session_profile.md`. **Descriptive only — no
expectancy, no win rate, no verdict.** P&L fields deleted at source.

## The data position

The tape recordings are **24-hour**, not cash-session only — the filtering to
US hours was in the analysis code. That gives **21 usable European sessions**
(22 dates at 0.25 covering ≥539 of 540 European minutes, minus sealed). 21
rather than 20 because a US half day is a normal European one.

Nothing else on disk reaches those hours; the ETH bar files are 30-minute and
1-hour over 54–78 days. External access was probed: FMP denies intraday on the
current plan, Alpha Vantage intraday is US equities only, and IBKR serves NQ
and DAX at the right hours but caps at 3,500 bars per request with no date
paging — six sessions at one minute.

**MDE at 21 sessions is +1.55 R/session** against a largest observed effect of
~0.04 across three screens. 500–1,300 sessions would be required.

## The profile, length-matched (EU 07:00–13:30 vs US 13:30–20:00)

| range | vol | path | **efficiency** | ATR | OR30 | prints | volume |
|---|---|---|---|---|---|---|---|
| 0.54 | 0.58 | 0.55 | **1.00** | 0.53 | **0.34** | **0.15** | **0.16** |

**The efficiency ratio is 0.05 in both.** Every rule in this project is a
continuation rule and every one depends on the market trending rather than
chopping. On that property the two sessions are indistinguishable. It is the
same shape at 55% of the size.

## The cost arithmetic decides it

Cost is fixed at 0.667 bps; the stop is a multiple of ATR and European ATR is
half. So **cost/risk goes from 5.0% to 16.3%**, and the edge needed over the
coin at 3R goes from **+1.2 to +4.1 percentage points** — **2.7× to 3.3× more
edge required** for the same rule at the same target. Liquidity at **15% of US
levels** means the 2.0-point cost assumption is optimistic for Europe, so every
figure understates the hurdle.

## Reported fairly, the two findings that point the other way

1. The opening range is **34% of the session range in Europe against 55% in the
   US** — a European break has more room to run relative to what it broke.
2. The pullback rule fires **21/21 sessions against 17/21** length-matched,
   ~45% more setups.

More setups on worse terms with the same chop character is not obviously a
better bet.

## Position

**Nothing bought, nothing recommended for purchase.** The one favourable
finding does not justify 500–1,300 sessions of acquisition. **The recorder
keeps running on 24-hour tapes** — European coverage now accumulates at no
extra cost.

What would change the answer is not more of this measurement: it is a cost
structure where a 4 bps stop is viable, or a rule family that does not need the
efficiency ratio to be above 0.05.

**Sealed NQ days: still sealed, still never read.**

---

# The session regime is not forecastable: 0 of 14, and there is barely a regime

`reports/regime_forecastability_preregistration.md` (`43ab596`),
`reports/regime_forecastability_result.md`. Descriptive. **No rule traded, no
expectancy computed, stage-2 budget unspent.**

## The prior question, asked before any performance test

The regime hypothesis — continuation rules win in trending sessions, lose in
choppy ones, netting to flat — requires the regime to be callable **before** the
trade. The whole-session efficiency ratio cannot do it: it reads bars from after
the decision timestamp. So: does anything available at D = open + `OR_MIN`
predict the efficiency ratio over the remainder?

**7 predictors × 2 decision timestamps = 14 combinations. 0 of 14.**

Largest effect in the entire grid: **|ρ| = 0.042, decile spread 0.0054**, against
pre-registered bars of 0.10 and 0.020. Not one reached nominal significance at an
uncorrected 0.05. The strongest candidate a priori — early efficiency predicting
later efficiency — returned **ρ = +0.035 and −0.001**.

## The positive control rules out a broken pipeline

Later **realised volatility**, same predictors, same timestamp, same code:

| predictor | ρ vs eff_later | ρ vs rv_later |
|---|---|---|
| rv_open | −0.016 | **+0.414** (p = 1e-64) |
| or_ratio | −0.002 | **+0.347** |
| vol_ratio | +0.010 | **+0.315** |

Later volatility roughly **doubles** bottom-decile to top-decile. Five of seven
clear every bar all fourteen missed on efficiency. **The null is a fact about the
market, not the measurement** — and it is what the pre-registration predicted in
writing: efficiency divides the volatility level out by construction, and
volatility clustering is the one reliably forecastable thing here.

## The deeper finding: sessions do not come in two kinds

| | observed | random walk | ratio |
|---|---|---|---|
| cross-sectional SD of efficiency | 0.0499 | 0.0458 (95%: .0440–.0480) | **1.09** |
| mean efficiency | 0.0682 | 0.0608 | **1.12** |

Session-to-session autocorrelation of efficiency: **−0.054, −0.009, −0.037,
−0.001** at lags 1, 2, 3, 5. A persistent state would autocorrelate positively.

**Driftless random walks of the same length reproduce ~91% of the dispersion.**
The difference between a session that trended and one that chopped is mostly the
arithmetic of short samples. The two real effects — mean 12% above random walk,
SD 9% above — are **constants, not states**, already inside what the three flat
screens measured.

## What this settles

The flat pooled results are **not** a positive and a negative cancelling. There
is no forecastable state to separate them with. Stage 2 was not run.

Not ruled out: regimes on a slower clock; regimes defined by something other
than the efficiency ratio. The **1,259 sessions of 2016–2020** remain unread.

**Sealed NQ days: still sealed, still never read.**

---

# A public discretionary NQ strategy, mechanised: 0 of 8, below the random walk

`reports/pullback_discretionary_preregistration.md` (`b8db9d2`),
`reports/pullback_discretionary_result.md`.

## The claim

77% win rate at 1.87 R:R, PF 6.39, 31 trades, January 2024, manual TradingView
bar replay. At 1.87 R:R a driftless random walk touches the target first 34.8%
of the time, so the claim sits **42.2 points above chance — z = 4.9 on n = 31**,
from a method with no fill model. Its internal arithmetic checks out (77% at 1.87
implies PF 6.26 against 6.39 reported), which is why it was mechanised rather
than dismissed.

## Result: 1,417 sessions, 12,253 trades, 0 of 8

Judged against **each variant's own realised reward-to-risk**, not against 50%:

| realised R:R span | RW rate span | observed span | **gap** |
|---|---|---|---|
| 0.87 – 1.54 | 53.4% – 39.4% | 51.5% – 39.2% | **−2.4 to −0.2 pts** |

**Every variant lands below its own random-walk rate.** Mean gap **−1.45 points**
against the +42.2 the claim needs — a shortfall of **43.6 points**. A 77% rate on
the mechanised sample would be a **27.5-sigma** event. Zero entry lookahead,
0.0–0.3% ambiguous bars.

### The finding inside the grid

Across the eight variants, **correlation between observed win rate and 1/(1+R:R)
= 0.9982**, mean absolute deviation 1.45 points. **The win rate is the target
distance.** Move the target and the hit rate moves exactly as far as a coin says
it should, with no residual. That is what no edge looks like when you sweep a
target.

## Where the 42 points did not come from

- **Not fills.** Naive-versus-honest phantom profit is **+0.001 to +0.006 R**.
  Even a backtest filling every entry at the trigger and every stop exactly would
  still be at or below chance. The claimed gap is ~7,000× the fill correction.
- **Not the daily stop.** Pre-registered as unable to move per-trade expectancy;
  confirmed — differences of −0.031 to +0.005 R, both signs, a composition
  effect. It removes ~25% of trades and flatters the equity curve and drawdown
  **without touching expectancy**. That is the mechanism by which a PF of 6.39
  can coexist with negative per-trade expectancy.
- **Not the trend rule, depth or levels.** Eight combinations move trade counts
  from 822 to 2,823 and move the gap over the random walk by 2.2 points total.

## The levels story is decorative — the pre-registered sentence, now due

**P1 (exit at nearest prior-session level) loses to P2 (flat 3R) in all four
pairs**, by −0.014 to −0.028 R. Levels raise the win rate (50% vs 41%) and lower
the reward-to-risk by just enough to make it worse than not using them. They are
not attracting price; they are a nearer target.

## Plainly

**The reported figure was method, not market.** The trader's realised 1.87 R:R is
also above every value the mechanised rule produces (0.87–1.54) — obtainable only
by selecting setups and targets, which is the discretion that cannot be tested and
that hindsight replay makes feel reliable. 2024, the claim's year, is the worst
year for three of four T1 variants.

**The 21 NQ tick sessions are not spent.** Verification was conditional on landing
materially above the random-walk rate. It landed below.

**Sealed NQ days: still sealed, still never read.**

---

# Dealer gamma: 0 of 4 on the regime, best-in-project on volatility

`reports/regime_forecast_gamma_preregistration.md` (`dd6e7ea`),
`reports/regime_forecast_gamma_result.md`. Descriptive, stage-2 budget unspent.

## Does ATAS have gamma? No

The API inventory has no GEX — every `gex` hit is a substring of `RangeX`,
`Regex` or `LegExecId`. `Security` carries `StrikePrice`/`OptionType`/
`OpenInterest`, but that is generic plumbing for venues serving options; the CME
route delivers futures only. An `OptionsKeyLevels` indicator exists but sits in a
bare namespace (third-party, not core), reads from a `DataPath` file, and has **no
gamma** — max pain and OI walls only. **`data/gex_history.jsonl` (335 QQQ
sessions from real chains) is better than anything ATAS would supply**, and the
existing architecture — compute outside, export lines into ATAS — is already
right.

## The hypothesis: 0 of 4

323 sessions, gamma from the chain as-of the **immediately preceding** close, so
known before the open.

| predictor | best ρ vs eff_later | bar | best spread | bar |
|---|---|---|---|---|
| net_gex / dist_flip | **0.076** | 0.167 (gate at this n) | **0.0076** | 0.020 |

Nothing reaches nominal significance uncorrected. The declared 2025–2026
robustness read agrees. **Combined with the price-based run: 0 of 18 across two
independent predictor families — price structure and dealer positioning.**

## The positive control is the interesting half

| predictor | ρ vs later **volatility** | later vol d1 → d10 |
|---|---|---|
| **net_gex** | **−0.520** (p = 1.1e-27) | **95.3 → 50.6 bps** |
| dist_flip | −0.474 | 94.0 → 62.5 bps |

**Most-negative-gamma sessions run 1.9× the later volatility of most-positive** —
sharper than the 1.49× on record from daily close-to-close data.

### It beats the free price predictor — correcting what I said beforehand

I told the user gamma "would have to beat a free predictor we already have." **On
the same 322 sessions it does.** `rv_open` +0.445, `or_ratio` +0.335, **`net_gex`
−0.521**. And partial rank corr(net_gex, rv_later | rv_open) = **−0.439**: gamma
keeps 0.44 of its 0.52 after the price predictor is removed. **Complementary, not
redundant.**

## What it settles

**Gamma cannot be a regime filter for these rules.** The regime a continuation
rule needs is trend-vs-chop; gamma predicts it at ρ = 0.08.

**Gamma is the best volatility forecaster in the project**, which strengthens what
is already shipped (`gamma_em_mult`, ×1.20/×1.00/×0.80 expected-move scaling).

**But the structural limit is unchanged.** These rules are R-normalised — stop
1.0 ATR, target 3R. Double the volatility and the stop, target and ATR all widen;
the R distribution is untouched. **An excellent volatility forecast is near a
no-op for a strategy denominated in R.** The one real channel is cost, fixed in
points while risk scales: a 1.9× wider session nearly halves cost/risk, worth
about half a percentage point on a 3R breakeven. Too small to rescue a rule
already at its random-walk rate.

**2022 is absent from the gamma sample**, so the year-stability rule could not be
applied — a thing to fix by fetching chains, not to waive.

**Sealed NQ days: still sealed, still never read.**

---

# Prior-day and gamma levels do not predict the next session: 0 of 13

`reports/levels_predictive_preregistration.md` (`d6539a1`),
`reports/levels_predictive_result.md`. Plus: **2022 gamma chains fetched**, so all
six years are now present (12/13/13/12/133/153) and the year-stability rule is
applicable for the first time. Re-running the gamma regime check with the gap
closed leaves it unchanged — largest ρ 0.076 → **0.069**, still 0 of 4, while the
volatility control strengthens to **−0.524**.

## The test that was refused

**Containment is degenerate and was not run.** "Next-day high stayed below the
call wall 90%" is fixed entirely by P(price travels that far) — a wall, a random
price and an arbitrary number score *identically* at the same distance, so no
placebo repairs it. That 90% measures "QQQ rarely moves 2% in a day."

## Test A — reaction at touch: 0 of 8

Counted only where price **reached** the level, so distance cannot do the work.

| level | touches | react 30m | react 60m |
|---|---|---|---|
| **PDH** | 545 | **44.8%** | 46.7% |
| PDL | 468 | 48.1% | 49.6% |
| VAH / VAL / POC | 586–661 | 47.2–51.5% | 48.8–52.4% |

Five price levels properly tested, all coins. **The three gamma levels are
INELIGIBLE, not failed** — 40, 24 and 90 touches against a pre-registered minimum
of 100. The call wall is reached in **12%** of sessions, the put wall **7%**:
settling them needs ~5,000 sessions of chains.

**PDH leans continuation (44.8%), not rejection** — the opposite of the folk
claim, consistent at both horizons, uncorrected p = 0.015, does not survive
correction. Noted, not claimed.

## Test B — turning-point clustering: 0 of 5

Do the day's high and low land nearer these levels than a **stranger's level
set** (same geometry, random other session, 200 shuffles)?

| level set | real | placebo | ratio | p |
|---|---|---|---|---|
| **prior-day (PDH/PDL)** | 47.4 bps | 50.8 | **0.934** | **0.005** (0 of 200) |
| all five price levels | 28.4 bps | 30.4 | 0.936 | 0.005 |
| gamma (walls + flip) | 64.2 bps | 65.9 | 0.975 | 0.294 |

**PDH/PDL genuinely do attract the next day's turning points** — not one of 200
shuffles beat them. **And the effect is 3.4 bps.** On a level already half a
percent from the turn, knowing it is the real prior-day high buys three basis
points of precision. Fails the pre-registered ≤0.90 magnitude bar and the
corrected significance gate both. **Detectable and immaterial — the distinction
the two-part bar exists to make.**

## Plainly

**These levels describe where the market has been. They do not measurably move
where it goes next.** That does not contradict how the project already uses them
— a prior-day high is a real price where real business happened, and fine for
hanging a confluence map on. The claim it will not support is prediction.

**Sealed NQ days: still sealed, still never read.**

---

# The setup grading scheme is worse than random — and backwards

`reports/setup_grading_preregistration.md` (`bb0ab30`),
`reports/setup_grading_result.md`. Grades applied to trades the existing ORB and
pullback machines already generate. No new rule.

## Counts first

**13,840 trades** across 6 trade sets, **0 entry lookahead**, **0.0% ambiguous**.
Grade shares A+ 11.6% / A 28.8% / B 59.6%, all ≥300 — the only pre-registered
criterion that passes.

## Result

| grade | trades | NET expR | GROSS expR | cost drag |
|---|---|---|---|---|
| **A+** | 1,604 | **−0.1600** | −0.1233 | +0.0366 |
| A | 3,990 | −0.0305 | +0.0256 | +0.0562 |
| B | 8,246 | −0.0504 | +0.0395 | +0.0899 |

**A+ is the worst grade.** A+ − B = **−0.1096 R net**, sitting at the **1.4th
percentile** of 1,000 random assignments — beaten by 98.6% of them. Years 2 of 6.
All six trade sets negative.

### The pre-registered decomposition did its job

The accounting identity behaved exactly as declared: A+ **does** pay a smaller
toll, 0.0366 against 0.0899, a mechanical saving of **0.053 R**. **And the market
swamped it three to one** — in gross terms, cost fully removed, A+ underperforms
B by **0.163 R**.

## Which component (diagnostic, not a new test)

| component | gross: on − off | net: on − off |
|---|---|---|
| **cost/risk ≤ 5% (wide stop)** | **−0.1525** | **−0.1013** |
| OR ratio ≥ 1.00 | −0.0378 | −0.0210 |
| **minutes ≤ 60 (early)** | **+0.0630** | **+0.0840** |

**The culprit is the component pre-registered as mechanically guaranteed to
help.** Selecting a wide stop selects high volatility, and those trades lose
0.15 R gross. Only early entry points the right way. The composite fails because
it weights one helpful condition equally with two harmful ones.

## Two things said plainly

**The real grading does not beat random assignment. Grade does not separate
outcome. Drop it.**

**And "significant in the wrong direction" is not a result to invert and trade.**
The 1.4th percentile would be a strong finding had that direction been declared.
It was not. Flipping after seeing which way it failed is what pre-registration
exists to stop. An inverted version needs its own pre-registration and should be
spent on the **1,259 sessions of 2016–2020 still never read** — not re-measured
on the sample that produced the idea.

**Outranking both:** every grade is negative — pooled **−0.0574 R over 13,840
trades**. Grading sorts an unprofitable rule into unprofitable buckets.

**Sealed NQ days: still sealed, still never read.**

---

# Calendar classification, Stage 1: the mechanism families show nothing

`reports/calendar_classification_preregistration.md` (`c147285`),
`reports/calendar_classification_result.md`. **Descriptive only. 2016–2020 stays
sealed** — the script reads only QQQ_1m.parquet, which begins 2021.

## One third of the design could not be built, and was not faked

**FOMC / CPI / NFP need real release dates.** Repo has none; FMP's
`economics-calendar` is **denied on this plan**; Alpha Vantage's series are keyed
by **reference month, not release date** (verified). Not derived from memory — the
NFP "first Friday" heuristic mislabels often enough to contaminate category *and*
control. Unblocking needs an FMP Starter tier or a Fed/BLS date CSV.

## Result: 13 categories × 4 statistics = 52 tests, α = 0.000962

| | |
|---|---|
| clearing Bonferroni | **1 of 52** |
| beating 95th pct of random labels | **6 of 52** (2.6 expected) |

**The families carrying the mechanism are empty.** Month-end, quarter-end,
first-of-month, roll week and all four expiry categories: flat on every statistic
and in every intraday window. The closing-window split was built so rebalancing
flow could not be averaged away — last-3-of-quarter puts 16.6% of volume in the
final 30 min vs 14.1% overall, visible but not significant.

**The only structure is day of week** — the category with the *least* obligation
content in the set:

| day | raw OR15 | OR ratio | rv | rv mid | vol% open30 |
|---|---|---|---|---|---|
| **Mon** | **55.9** | **1.075** | **91.3** | **76.7** | **16.0** |
| **Wed** | **49.8** | **0.946** | **102.0** | **88.1** | 14.4 |
| all | 53.1 | 1.014 | 97.6 | 83.3 | 15.0 |

**Monday front-loads then goes quiet** — widest opening vs its own norm, most
volume in the first 30 min, lowest mid-session vol. Coherent, with an obvious
mechanism (weekend news priced at the open). Raw OR runs **~12% wider Monday than
Wednesday** (F = 2.77, p ≈ 0.026); the trailing-mean normalisation sharpens it to
F = 4.38 by removing volatility drift rather than by creating the effect.

## The surviving axis already points the wrong way

The setup-grading run measured the OR-ratio axis on 13,840 trades: **OR ratio ≥
1.00 returned −0.021 R net.** Monday's distinguishing feature is a *high* OR
ratio.

## Stage 2 proposed, and recommended against

Grid would be {Monday, Wednesday} × {ORB OR15 3R, pullback OR15 3R} on the sealed
1,259 sessions. **MDE ≈ 0.60 R/session against observed effects of 0.04–0.08 —
roughly eight times underpowered.** It would return a meaningless null and consume
the only clean sample left doing it.

**Recommendation: do not approve.** If the calendar direction continues, unblock
the scheduled-events family instead — that is where the obligation mechanism is
strongest and where a pre/post split has real content. It needs release dates, not
more analysis of what is already on disk.

**Sealed NQ days: still sealed. 2016–2020: still sealed.**
