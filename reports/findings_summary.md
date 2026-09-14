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
