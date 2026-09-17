# The bar-resolution gate: result, and two defects it uncovered

Run on the 20 NQ discovery sessions. The eight sealed June days and 23 July
were not read — the session list comes from `roster.split`, which excludes them
at construction.

Gate pre-registered at `697fd55`. **Threshold not moved.**

> **This file was rewritten.** A first version was committed at `26e0350` after
> the first defect was found and before the second was. It concluded that a
> bar-close grid was "a genuinely different and better rule". **That conclusion
> was wrong**, and section 5 now says why. The numbers below are the corrected
> ones throughout.

---

## 0. Two defects, both of which made the rule look better than it is

The gate exists to compare the rule at two resolutions. Running it at one
minute made the rule look wildly profitable, which was not credible. Chasing
that produced two separate faults, neither of them about resolution.

### Defect 1 — entry lookahead in the `ARMED` state

The code updated the pullback extreme with the current bar and then asked
whether that same bar's opposite extreme had crossed `pullback extreme + 4
ticks`. That is buying one point off the low of a bar you have already seen in
full.

| grid | entries taken on the bar that set the extreme | median range of that bar | after the fix |
|---|---|---|---|
| 1 second | 34.5% | 3.25 pts | **0.0%** |
| 1 minute | 72.3% | 28.00 pts | **0.0%** |
| 5 minute | 49.4% | 53.75 pts | **0.0%** |

Fixed by fixing the trigger from bars that have already closed, testing the
current bar against it, and updating the extreme only on bars that did not
trigger.

### Defect 2 — a stop order assumed to fill at its own trigger price

This one is bigger, and it was invisible until the rule ran on QQQ.

A buy stop at `trigger` fills at **the first price actually available**, which
is the bar's open when the bar has already opened beyond the trigger. The code
credited every entry with the trigger price itself.

```
QQQ one-minute entries where the bar OPENED past the trigger : 90.8%
mean unmodelled slippage, in the strategy's favour           : +0.561 R
median                                                        : +0.348 R
```

**The QQQ screen's entire apparent edge was +0.24R to +0.55R. The unmodelled
fill was +0.56R.** The result was the defect.

It scales with bar size, which is exactly why it masqueraded as a resolution
effect: at one second consecutive prints rarely gap a full point past the
trigger, at one minute they routinely do, and on a $600 share where the trigger
sits 0.333 bps away they almost always do.

Entries now fill at `max(trigger, bar open)` for longs and `min(...)` for
shorts, with risk and target recomputed from the real fill. Stop exits gap
through in the same way.

### Correction to the record — grid 2

Grid 2's published numbers carried defect 1, and after the fixes carry neither.
Both corrections moved the result downward, as a bias removal must.

| | published | corrected |
|---|---|---|
| variants with expectancy > 0 | some | **none — all 12 negative** |
| best per-trade expectancy | — | −3.65 pts |
| worst | — | −11.36 pts |
| survivors | 0 of 12 | **0 of 12** |

**The verdict does not change and the family stays closed.** The numbers are
corrected because they moved, not because the conclusion did.

A third change, `MIN_OR_BARS`: the opening range required 30 bars, which a
five-minute grid cannot satisfy. It now requires 3. At one second a 15-minute
range holds 900 bars, so this is never binding on the truth run.

---

## 1. Counts, before any performance number

| grid | bars/session | trades | sessions | trades/session |
|---|---|---|---|---|
| 1 second (truth) | 17,505 | 328 | 15 of 20 | 1.37 |
| 1 minute | 300 | 334 | 15 | 1.39 |
| 5 minute | 60 | 334 | 15 | 1.39 |

16 variants (`OR_MIN` 15/30 × `STOP_ATR` 0.5/1.0 × `TGT_R` 1/2/3/4), two trades
a session each. Five of the twenty sessions produce no trade at any setting.

---

## 2. The four items, per stop setting

Measured on matched pairs: every trade the tape produced, handed to the bar grid
with its entry, stop and target already fixed, only the exit re-decided.

### One minute

| | STOP_ATR 0.5 | STOP_ATR 1.0 |
|---|---|---|
| median risk | 17.6 pts | 33.4 pts |
| trades | 166 | 162 |
| **1. bar spans both stop and target** | **0.6%** | **0.0%** |
| **2. expectancy** truth → proxy | −0.272R → −0.336R | −0.246R → −0.148R |
| **difference** | **−0.064R** | **+0.097R** |
| **3. outcome disagreements** | 4 (2.4%) | 7 (4.3%) |
|   truth target → proxy stop | 4 | 1 |
|   truth stop → proxy target | 0 | 6 |
| **4. cost of the stop-first convention** | −2.000R on the 1 ambiguous bar, **−0.012R overall** | none ambiguous, **0.000R** |
| **verdict** | **PASS** | **PASS** |

### Five minutes

| | STOP_ATR 0.5 | STOP_ATR 1.0 |
|---|---|---|
| **1. bar spans both** | **14.5%** | **1.9%** |
| **2. expectancy difference** | **+0.171R** | **+0.159R** |
| **3. disagreements** | 33 (19.9%) | 13 (8.0%) |
|   truth target → proxy stop | 14 | 3 |
|   truth stop → proxy target | 19 | 10 |
| **4. cost of the convention** | −2.833R each on 24 bars, **−0.410R overall** | −2.000R each on 3, **−0.037R** |
| **verdict** | **PASS** | **PASS** |

**Item 4 answered directly: yes, the stop-before-target convention biases the
proxy downward exactly as predicted. The measured size is −0.012R at one minute
and −0.410R at five minutes** (tight stop, across all trades). Negligible at
one minute because ambiguity is essentially absent; material at five because
one bar in seven spans both levels.

### Ambiguity by target — the mechanism, and where the prediction missed

| stop | target | ambiguous (1m) | ambiguous (5m) |
|---|---|---|---|
| 0.5 | 1.0R | 2.4% | **26.2%** |
| 0.5 | 2.0R | 0.0% | 19.0% |
| 0.5 | 3.0R | 0.0% | 7.1% |
| 0.5 | 4.0R | 0.0% | ~5% |
| 1.0 | 1.0R | 0.0% | 7.1% |
| 1.0 | 2.0R–4.0R | 0.0% | 0.0% |

Ambiguity falls as the target widens, because a bar must span stop **to**
target and that distance is `(1 + M) × risk`. The pre-registration reasoned
about a 17-point stop against a 16.6-point median bar; the quantity that
actually matters is the 35-to-88-point stop-to-target span, which one-minute
bars essentially never cover. **The tight stop at a 1R target on five-minute
bars is the one cell that genuinely fails, at 26.2%.**

### A quantity the gate never asked for, and should have

**23.5% of tick-level trades at the tight stop open and close before the next
one-minute bar even starts** (62.0% at five minutes). Those trades are not
"resolved differently" by bar data — they cannot exist on it at all. One-minute
data does not see roughly a quarter of what the tape does.

---

## 3. End to end: with honest fills, the grids agree

| grid | stop | n | mean R | session t |
|---|---|---|---|---|
| 1 second | 0.5 | 166 | −0.272 | −1.12 |
| 1 second | 1.0 | 162 | −0.246 | −1.15 |
| 1 minute | 0.5 | 167 | −0.273 | −1.60 |
| 1 minute | 1.0 | 167 | −0.207 | −1.43 |
| 5 minute | 0.5 | 167 | −0.049 | −0.33 |
| 5 minute | 1.0 | 167 | −0.212 | −1.33 |

Paired by session, the one-minute divergence is **−0.001R** at the tight stop
and **+0.039R** at the wide one.

**Before the fill fix these same rows read −0.19R for the tape and +0.90R for
the five-minute grid, a paired t of +4.87.** A coarse grid appearing to turn a
losing rule into a t ≈ 3 winner was the signature of a manufactured edge, and it
was manufactured — by the fill assumption, not by the resolution.

---

## 4. Panel C — the bar backtest's own trades, re-decided on the tape

Take every trade the **bar** backtest produced, locate the moment its trigger
price actually traded, fill at the price the tape was offering, and let the
tape decide the outcome.

| grid | stop | n | bar says | tape says | outcomes agreeing |
|---|---|---|---|---|---|
| 1 minute | 0.5 | 167 | −0.273R | **−0.272R** | **100.0%** |
| 1 minute | 1.0 | 167 | −0.207R | **−0.210R** | **100.0%** |
| 5 minute | 0.5 | 167 | −0.049R | −0.008R | 97.0% |
| 5 minute | 1.0 | 167 | −0.212R | −0.215R | 98.8% |

**One-minute bars reproduce the tape's own answer to within 0.003R, on every
trade.** That is the gate passing for the right reason.

---

## 5. Correcting the wrong conclusion

The first version of this file read the pre-fix +0.33R divergence as a real
effect and concluded that waiting for a bar to close was a *different and
better rule* — "don't chase the first one-point bounce off a tick low, wait for
the candle to close". It even had a mechanism, and the mechanism was plausible.

**It was an artifact of assuming a fill at a price the bar never offered**, and
the size of the artifact scaled with bar width, which is precisely what made it
look like a resolution effect. Panel C appeared to confirm it because Panel C
was making the same fill assumption on the tape.

Nothing survives of that hypothesis. There is no bar-close filter, there is no
new family, and nothing is logged as data-informed because nothing was learned
that the data supports.

The lesson worth keeping: **a favourable-looking difference between two ways of
measuring the same rule is almost always a defect in the more favourable one.**

---

## 6. Verdict

**The gate PASSES at one minute, at both stop settings**, on its two
pre-registered criteria and on the stronger test the criteria did not ask for.

**Five minutes passes the stated criteria but fails on its merits** at the tight
stop: 26.2% ambiguity at a 1R target, 62% of tick trades invisible to it, and a
−0.410R convention cost. It was the fallback and it is not needed.

The QQQ screen proceeds on one-minute bars.

### What still does not translate

Unchanged: QQQ's cash open follows a closed book, NQ's follows a live overnight
auction. Untestable on this data, and the reason the screen cannot be the final
word regardless of what survives it.
