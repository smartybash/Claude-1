# ORB with a session VWAP filter: 0 of 16, and a third fill-model defect

Rule, grid and rejection criteria pre-registered at `bbbddb1` before this ran.
Neither the grid nor the criteria were changed. Sealed NQ days were not read —
this screen never touches the NQ tape.

---

## 1. Counts, before any performance number

| | |
|---|---|
| sessions used | **1,418** — 2021-01-04 to 2026-08-31 |
| dropped | 3 |
| per year | 250 / 250 / 250 / 252 / 250 / 166 (2026 to August) |
| sessions producing a trade | **1,418** at `OR_MIN` 15, 1,398 at `OR_MIN` 30 |
| trades per variant | 2,578 to 2,740 |
| trades per session | 1.84 to 1.93, against a cap of 2.00 |
| median risk | 4.8–6.2 bps (`STOP_ATR` 0.5), 9.1–11.7 bps (1.0) |
| flat-time exits | 0.1% to 1.5% |
| bars spanning stop and target | 0.0% to 4.9% |
| bars reaching both triggers | 2 to 5 per variant, out of ~3,000 signals |

This family fires far more reliably than the pullback did: **every one of the
1,418 sessions produces a breakout trade at `OR_MIN` 15**, against 1,169 for the
pullback. Nearly the full two-trade cap is used every session.

---

## 2. The defect this grid exposed, found before any result was reported

The first run returned expectancies of **−0.26R to −0.75R**, with a 1R target
hitting **19.6%** against a coin's 50%, and session t values reaching **−49**.
That is not a losing strategy, it is a broken one, and it got the same scrutiny
the previous family's +16 did.

**The entry bar was being searched for the exit, and for a breakout that is
wrong rather than conservative.** The trigger sits at the top of the bar's
travel — price had to rise *through* the bar to reach it — so the bar's low is
usually pre-entry price action:

```
entry bars that OPENED on the far side of their trigger        73.9%
trades whose entry-bar adverse extreme is beyond the stop       44.9%
  ...of those, bars that opened on the far side                 87.8%
```

So in nearly nine cases in ten, the low that "stopped" the trade happened
before the trade existed. Charging a trade with a move that preceded its entry
is the model being told something false about sequence — the same category of
error as crediting it with an unavailable fill price, pointing the other way.

**Why the pullback family did not have this problem:** its trigger was a
rejection off a *prior* bar's extreme, so the entry bar was already moving in
the trade's direction. There the same switch was worth about 0.07R. Here it is
worth most of the result:

| | entry bar searched (wrong) | entry bar skipped (used) |
|---|---|---|
| OR15 SATR0.5 R1.0 | −0.656R | **−0.264R** |
| OR15 SATR1.0 R4.0 | −0.261R | **+0.012R** |
| OR30 SATR0.5 R1.0 | −0.749R | **−0.358R** |

**What one-minute bars still cannot say** is what the entry bar did *after* the
fill. That is genuinely unresolvable on this data, and only the NQ tape could
settle it. It is the one place this screen is knowingly optimistic, and it is
recorded rather than buried.

---

## 3. The slippage audit — standing output, as required

| variant | gapped entries | mean slip | **honest exp R** | **naive exp R** | phantom |
|---|---|---|---|---|---|
| OR15 SATR0.5 R1.0 | 55.6% | +0.117 | −0.264 | −0.111 | **+0.153** |
| OR15 SATR0.5 R2.0 | 54.0% | +0.102 | −0.144 | **+0.019** | **+0.163** |
| OR15 SATR0.5 R3.0 | 52.8% | +0.081 | −0.102 | **+0.040** | +0.142 |
| OR15 SATR0.5 R4.0 | 50.8% | +0.064 | −0.092 | **+0.047** | +0.139 |
| OR15 SATR1.0 R1.0 | 52.3% | +0.088 | −0.098 | **+0.025** | +0.123 |
| OR15 SATR1.0 R2.0 | 43.7% | +0.056 | −0.055 | **+0.053** | +0.108 |
| OR15 SATR1.0 R3.0 | 38.5% | +0.037 | −0.019 | **+0.070** | +0.089 |
| OR15 SATR1.0 R4.0 | 35.1% | +0.027 | +0.012 | **+0.093** | +0.082 |
| OR30 SATR0.5 R1.0 | 55.3% | +0.114 | −0.358 | −0.233 | +0.125 |
| OR30 SATR1.0 R4.0 | 34.0% | +0.026 | −0.089 | −0.049 | +0.040 |

**Over half of all entries gap past the trigger**, more than double the rate on
the pullback grid, because a breakout trigger sits exactly where price is
accelerating. The phantom is **+0.04R to +0.16R**, and at `OR_MIN` 15 it is the
difference between a family that loses and a family that looks like it works:
**seven of the eight OR15 variants report positive expectancy under the naive
fill and negative expectancy under the honest one.**

Had the fill model not been fixed two families ago, this screen would have
produced eight apparent winners.

---

## 4. Performance

| variant | n | exp R | win% | coin% | breakeven% | PF | sess t | +yrs |
|---|---|---|---|---|---|---|---|---|
| OR15 SATR0.5 R1.0 | 2,740 | −0.264 | 46.2 | 50.0 | 55.4 | 0.60 | −13.27 | 0/6 |
| OR15 SATR0.5 R2.0 | 2,734 | −0.144 | 35.0 | 33.3 | 37.0 | 0.82 | −5.24 | 0/6 |
| OR15 SATR0.5 R3.0 | 2,720 | −0.102 | 27.7 | 25.0 | 27.9 | 0.89 | −2.98 | 0/6 |
| OR15 SATR0.5 R4.0 | 2,710 | −0.092 | 22.5 | 20.0 | 22.4 | 0.90 | −2.26 | 0/6 |
| OR15 SATR1.0 R1.0 | 2,706 | −0.098 | 48.6 | 50.0 | 52.8 | 0.82 | −5.59 | 0/6 |
| OR15 SATR1.0 R2.0 | 2,660 | −0.055 | 34.2 | 33.3 | 35.3 | 0.92 | −2.05 | 0/6 |
| OR15 SATR1.0 R3.0 | 2,638 | −0.019 | 26.9 | 25.0 | 26.5 | 0.98 | −0.55 | 2/6 |
| **OR15 SATR1.0 R4.0** | 2,619 | **+0.012** | 22.4 | 20.0 | 21.3 | 1.01 | **+0.29** | 4/6 |
| OR30 SATR0.5 R1.0 | 2,693 | −0.358 | 44.7 | 50.0 | 56.3 | 0.51 | −16.32 | 0/6 |
| OR30 SATR0.5 R2.0 | 2,684 | −0.240 | 34.0 | 33.3 | 37.5 | 0.72 | −8.24 | 1/6 |
| OR30 SATR0.5 R3.0 | 2,677 | −0.179 | 27.2 | 25.0 | 28.2 | 0.81 | −5.08 | 1/6 |
| OR30 SATR0.5 R4.0 | 2,668 | −0.153 | 22.4 | 20.0 | 22.6 | 0.85 | −3.68 | 1/6 |
| OR30 SATR1.0 R1.0 | 2,666 | −0.176 | 45.9 | 50.0 | 53.4 | 0.71 | −9.56 | 0/6 |
| OR30 SATR1.0 R2.0 | 2,630 | −0.107 | 33.2 | 33.3 | 35.6 | 0.86 | −4.00 | 1/6 |
| OR30 SATR1.0 R3.0 | 2,600 | −0.077 | 25.8 | 25.0 | 26.7 | 0.91 | −2.31 | 1/6 |
| OR30 SATR1.0 R4.0 | 2,578 | −0.089 | 20.5 | 20.0 | 21.4 | 0.90 | −2.25 | 1/6 |

**Survivors: 0 of 16.** Fifteen fail on expectancy. The sixteenth, `OR15
SATR1.0 R4.0`, is the only variant with positive expectancy and it fails on
criterion 2 (t **+0.29**, against a bar of 3.0), criterion 3 (PF 1.01, against
1.15) and criterion 4 (top-1% dependent).

### This is a nearer miss than the pullback, and the reason is precise

At the wider stop and wider targets the rule genuinely beats the coin:

| target | observed | coin | gap over coin | gap needed |
|---|---|---|---|---|
| 2.0R | 34.2% | 33.3% | +0.9 | +2.0 |
| 3.0R | 26.9% | 25.0% | **+1.9** | +1.5 |
| 4.0R | 22.4% | 20.0% | **+2.4** | +1.3 |

**A breakout above VWAP does reach 3R and 4R slightly more often than chance
says it should.** The margin is one to two and a half percentage points, and
the cost needs one to two. So the rule arrives at breakeven and stops there —
t +0.29 on 2,619 trades is as flat a reading as this data can produce, which is
itself informative: with a sample this size, "not distinguishable from zero"
means the effect really is near zero, not that the test was underpowered.

Note also that the tighter stop is *worse* at every target, which is the
opposite of what a real edge usually looks like — a genuine effect normally
survives being measured at more than one stop distance.

---

## 5. Regime breakdown

### By year, mean R per trade

Reported in full in the script output. The pattern, for the three variants
closest to viable:

| variant | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|
| OR15 SATR1.0 R3.0 | −0.006 | −0.011 | −0.052 | +0.029 | +0.010 | −0.114 |
| OR15 SATR1.0 R4.0 | +0.059 | +0.031 | −0.045 | +0.062 | +0.051 | **−0.134** |
| OR30 SATR1.0 R4.0 | −0.122 | **+0.115** | −0.113 | −0.062 | −0.242 | −0.114 |

The one near-positive variant is positive in four years and **its worst year is
the most recent one**. A rule whose only positive reading depends on 2021–2022
and breaks down in 2025–2026 is not something to carry forward.

`OR30 SATR0.5` is positive *only* in 2022 across every target — the one
high-volatility bear year — and negative in all five others. That is a
volatility artifact, not an edge.

### By time of day (minutes since the RTH open)

| variant | 0–60 | 60–120 | 120–180 | 180+ |
|---|---|---|---|---|
| OR15 SATR0.5 R4.0 | −0.088 | −0.243 | +0.006 | **+0.397** |
| OR15 SATR1.0 R4.0 | −0.001 | +0.109 | −0.008 | +0.217 |
| OR30 SATR1.0 R4.0 | −0.049 | −0.173 | −0.200 | −0.233 |
| **trade counts (OR15 S0.5 R4.0)** | **2,525** | **139** | **28** | **18** |

**The late buckets are noise and must be read as noise.** 92% of all breakouts
fire in the first hour, and the +0.397R in the `180+` column rests on **18
trades**. The honest content of this table is structural, not directional: an
opening range breakout is an opening-hour event, and the time-of-day axis is
effectively one bucket. Anything that looks like a late-session edge here is a
sample of eighteen.

### By opening range height, versus its own trailing 20-session mean

| variant | narrow (<0.8) | normal (0.8–1.2) | wide (>1.2) |
|---|---|---|---|
| OR15 SATR0.5 R1.0 | −0.290 | −0.273 | −0.221 |
| OR15 SATR0.5 R4.0 | −0.143 | −0.052 | −0.076 |
| OR15 SATR1.0 R4.0 | −0.045 | **+0.077** | −0.012 |
| OR30 SATR0.5 R4.0 | −0.251 | −0.121 | **−0.075** |
| OR30 SATR1.0 R4.0 | −0.119 | −0.067 | −0.099 |
| trade counts | ~900–965 | ~980–1,045 | ~650–710 |

**The one consistent gradient in the whole screen:** breakouts from a *narrow*
opening range are worse than from a wide one, in 13 of 16 variants. That is the
opposite of the usual folklore ("a tight range coils for a big move") and it is
the one pattern here supported by a decent sample in every bucket. It is a
description of this data, not a tested hypothesis, and it is logged as such
rather than promoted.

---

## 6. The VWAP filter did almost nothing

| | |
|---|---|
| signals vetoed | **9.0% to 35.8%** |
| change in trade count | **5 to 18 trades**, out of ~2,700 |
| change in expectancy | **+0.005R to +0.017R** |

The filter vetoes up to a third of signals and yet changes the trade count by
well under 1%, because a vetoed breakout is simply replaced by a later one in
the same session — the two-trade cap gets filled either way. It is a
**substitution, not a reduction**.

Its net worth is under two hundredths of an R on a family that needs about a
tenth of an R to break even. **The filter is directionally right and
quantitatively irrelevant.**

### Assessing my own pre-registered prediction

I predicted the veto rate would come in "under about 15%", and said that would
make the filter "close to decorative". **The veto rate is higher than I
predicted** — up to 35.8% — and the filter is decorative anyway. The prediction
was pointed at the wrong quantity: veto rate measures how often a filter fires,
not whether it helps. The expectancy difference is the test, and I should have
pre-registered that instead.

---

## 7. Verdict and ledger

**0 of 16. The opening-range-breakout-with-VWAP family is closed.**

| family | sample | outcome |
|---|---|---|
| order flow | 20 NQ sessions | closed |
| pullback grid 1 | 20 NQ sessions | rejected, broken spec |
| pullback grid 2 | 20 NQ sessions | closed, coin flip |
| pullback, QQQ screen | 1,418 QQQ sessions, 16 variants | closed, 0 of 16 |
| **ORB + VWAP, QQQ screen** | **1,418 QQQ sessions, 16 variants** | **closed, 0 of 16** |

Nothing reached NQ verification, so the sealed days remain unspent. They have
still never been read.

### The pattern across three screens

Each of the last three families produced an extraordinary first result, and
each time it was the fill or sequencing model rather than the market:

1. **Entry lookahead** — the trigger computed from the bar it was tested against.
2. **Unavailable fill price** — a stop order credited with its own trigger.
3. **Pre-entry stop-outs** — the entry bar's adverse range charged to a trade
   that did not yet exist.

All three inflate results in proportion to bar size, and all three are now
fixed and instrumented as standing output. **The slippage audit earned its
place immediately:** it showed that seven of the eight `OR_MIN` 15 variants
would have reported positive expectancy under the old assumption.

### What this does not rule out

The rule is an opening-hour event — 92% of entries in the first sixty minutes —
and QQQ's opening hour follows a closed book while NQ's follows a live
overnight auction. For an *opening range* family that difference is more
pointed than it was for the pullback, not less. This screen is the strongest
evidence available short of several hundred NQ sessions, and it is not proof
about NQ.
