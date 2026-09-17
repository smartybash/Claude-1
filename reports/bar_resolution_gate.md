# The bar-resolution gate: result, and a defect it uncovered

Run on the 20 NQ discovery sessions. The eight sealed June days and 23 July
were not read — the session list comes from `roster.split`, which excludes them
at construction.

Gate pre-registered at `697fd55`. Threshold not moved.

---

## 0. A defect found while building the gate, and what it changes

The gate exists to compare the rule at two resolutions. Running it at one
minute made the rule look wildly profitable, which was not credible, and the
cause was a fault in the state machine that had been there the whole time.

**In the `ARMED` state, the code updated the pullback extreme with the current
bar and then asked whether that same bar's opposite extreme had crossed
`pullback extreme + 4 ticks`.** That is buying one point off the low of a bar
you have already seen all of.

Measured share of entries taken on the same bar that set the pullback extreme:

| grid | before the fix | median range of that bar | after |
|---|---|---|---|
| 1 second | 34.5% | 3.25 pts | **0.0%** |
| 1 minute | 72.3% | 28.00 pts | **0.0%** |
| 5 minute | 49.4% | 53.75 pts | **0.0%** |

At one second the bar is a few ticks wide and the bias is small. At one minute
it is the entire result. The fix is to fix the trigger from bars that have
already closed and only then test the current bar; the pullback extreme is
updated afterwards, on bars that did not trigger.

### Correction to the record

**Grid 2's published numbers were produced with this bias present, and it
favoured the rule.** Re-run at one second with the fix:

| | published | corrected |
|---|---|---|
| variants with expectancy > 0 | some | **none — all 12 negative** |
| best per-trade expectancy | — | −0.78 pts (OR15 SATR1.0 R1.5) |
| worst | — | −7.01 pts/session |
| survivors | 0 of 12 | **0 of 12** |

**The conclusion does not change and the family stays closed.** Removing a
favourable bias can only move a result downward, and it did. The correction is
recorded because the numbers changed, not because the verdict did.

A second change, `MIN_OR_BARS`: the opening range required 30 bars, which at a
five-minute grid is impossible. It now requires 3. At one second a 15-minute
range holds 900 bars, so this is never binding on the truth run and changes no
number reported anywhere.

---

## 1. Counts, before any performance number

| grid | bars/session | trades | sessions | trades/session |
|---|---|---|---|---|
| 1 second (truth) | 17,505 | 330 | 15 of 20 | 1.38 |
| 1 minute | 300 | 337 | 15 | 1.40 |
| 5 minute | 60 | 337 | 15 | 1.40 |

16 variants (`OR_MIN` 15/30 × `STOP_ATR` 0.5/1.0 × `TGT_R` 1/2/3/4), each
capped at two trades a session. Five of the twenty sessions produce no trade at
any setting. Trades/session is across all 16 variants pooled, so the ceiling is
2.00.

---

## 2. The four items, per stop setting

Measured on matched pairs: every trade the tape produced, handed to the bar
grid with its entry, stop and target already fixed, with only the exit
re-decided.

### One minute

| | STOP_ATR 0.5 | STOP_ATR 1.0 |
|---|---|---|
| median risk | 17.1 pts | 33.1 pts |
| trades | 167 | 163 |
| **1. bar spans both stop and target** | **0.6%** | **0.0%** |
| **2. expectancy** truth → proxy | −0.181R → −0.289R | −0.234R → −0.156R |
| **difference** | **−0.108R** | **+0.078R** |
| **3. outcome disagreements** | 6 (3.6%) | 8 (4.9%) |
|   truth target → proxy stop | 6 | 2 |
|   truth stop → proxy target | 0 | 6 |
| **4. cost of the stop-first convention** | −2.000R on the 1 ambiguous bar, **−0.012R overall** | no ambiguous bars, **0.000R** |
| **verdict** | **PASS** | **PASS** |

### Five minutes

| | STOP_ATR 0.5 | STOP_ATR 1.0 |
|---|---|---|
| **1. bar spans both** | **13.8%** | **1.8%** |
| **2. expectancy difference** | **+0.162R** | **+0.139R** |
| **3. disagreements** | 37 (22.2%) | 14 (8.6%) |
|   truth target → proxy stop | 16 | 4 |
|   truth stop → proxy target | 21 | 10 |
| **4. cost of the convention** | −2.783R each on 23 bars, **−0.383R overall** | −2.000R each on 3, **−0.037R** |
| **verdict** | **PASS** | **PASS** |

**Item 4 answered directly: yes, the stop-before-target convention biases the
proxy downward, exactly as predicted, and the measured size is −0.012R at one
minute and −0.383R at five minutes** (tight stop, across all trades). It is
negligible at one minute because ambiguity is essentially absent there, and
material at five minutes because one bar in seven spans both levels.

### Ambiguity by target — the prediction was right about the mechanism

| stop | target | n | ambiguous (1m) | ambiguous (5m) |
|---|---|---|---|---|
| 0.5 | 1.0R | 42 | 2.4% | 28.6% |
| 0.5 | 2.0R | 42 | 0.0% | 14.3% |
| 0.5 | 3.0R | 42 | 0.0% | 7.1% |
| 0.5 | 4.0R | 41 | 0.0% | 4.9% |
| 1.0 | 1.0R | 42 | 0.0% | 7.1% |
| 1.0 | 2.0R–4.0R | 121 | 0.0% | 0.0% |

Ambiguity falls as the target widens, because a bar must span stop **to**
target and that distance is `(1 + M) × risk`. The pre-registration reasoned
about a 17-point stop against a 16.6-point median bar; the quantity that
actually matters is the 34-to-85-point stop-to-target span, which one-minute
bars almost never cover. **The tight stop at a 1R target on five-minute bars is
the one cell where this genuinely bites, at 28.6%.**

---

## 3. What the gate's two criteria did not measure

Fixing the entries from the tape holds the trade set constant. The screen will
not have that luxury: on QQQ the bar grid decides which trades exist.

Run end to end, the same rule on different grids is **not the same rule**:

| grid | stop | n | mean R | session t |
|---|---|---|---|---|
| 1 second | 0.5 | 167 | **−0.194** | −0.82 |
| 1 second | 1.0 | 163 | **−0.267** | −1.12 |
| 1 minute | 0.5 | 168 | **+0.165** | +0.76 |
| 1 minute | 1.0 | 169 | +0.029 | +0.11 |
| 5 minute | 0.5 | 168 | **+0.903** | **+2.96** |
| 5 minute | 1.0 | 169 | +0.507 | +1.69 |

Paired by session, the divergence is itself significant: **+0.359R at t +2.39**
(1 minute, tight stop) and **+1.097R at t +4.87** (5 minute, tight stop).

A coarse grid turning a losing rule into a t ≈ 3 winner is the signature of a
manufactured edge, and on that reading the screen was dead. So it was tested
rather than assumed.

---

## 4. Panel C — the decisive test, and it reverses the reading

Take every trade the **bar** backtest produced, locate the moment its trigger
price actually traded on the tape, and let the tape decide the outcome from
there. Nothing hypothetical: the entry is a resting stop order at a price the
bar backtest itself chose.

| grid | stop | n | bar says | tape says | difference | outcomes agreeing |
|---|---|---|---|---|---|---|
| 1 minute | 0.5 | 168 | +0.145R | **+0.168R** | +0.024 | **98.8%** |
| 1 minute | 1.0 | 169 | +0.132R | **+0.130R** | −0.002 | **100.0%** |
| 5 minute | 0.5 | 168 | +0.899R | **+1.232R** | +0.333 | 88.1% |
| 5 minute | 1.0 | 169 | +0.557R | **+0.606R** | +0.049 | 97.6% |

Outcome flow at five minutes: of 147 trades the bar called stops, the tape
agreed on 123 and made 24 of them targets — the pessimistic convention
over-charging, in the predicted direction. Of 188 bar targets the tape agreed
on **all 188**.

**So the bar backtest is not lying about its own trades.** The +0.33R gap in
section 3 is not measurement error. It is real, and it means something else.

---

## 5. What it actually means

Waiting for a bar to close before fixing the pullback extreme is **a different
trading decision, not a degraded view of the same one**. It:

- delays the entry by up to one bar,
- takes the *bar's* low as the pullback extreme rather than the running
  tick-by-tick low, which is deeper,
- and therefore demands a larger, more committed rejection before triggering.

That is a rule a trader would recognise: *don't chase the first one-point
bounce off a tick low — wait for the candle to close and work off its low.* The
tick version reacts to noise; the bar version waits for the noise to resolve.

**This is a new hypothesis and it came out of the data, so it is logged as
data-informed.** It was not pre-registered, it is not a finding, and on 15
sessions with 16 heavily overlapping variants it is a long way from one.

---

## 6. Verdict

**The gate PASSES at both resolutions and at both stop settings.** It passes on
its two pre-registered criteria, and Panel C — which the criteria did not ask
for — supports the same conclusion more directly: a bar backtest's trades
survive contact with the tape at 98.8% and 100% outcome agreement at one
minute.

The QQQ screen goes ahead on **one-minute** bars, as pre-registered.

**Five-minute is reported but not screened.** It was the fallback, it was not
needed, and its 28.6% ambiguity at the tight stop with a 1R target is the one
cell that fails on its own merits.

### One correction to step 3 of the plan

"Verify on the 20 NQ tick sessions" cannot mean *run the one-second rule*,
because section 5 establishes that the one-second rule is a different rule.
Verification means the **Panel C method**: take the surviving variant's trades
as the bar rule generates them on NQ one-minute bars, and let the tape decide
every outcome.

### What still does not translate

Unchanged from the pre-registration, and section 4 does nothing to soften it:
QQQ's cash open follows a closed book and NQ's follows a live overnight
auction. That difference is untestable on this data and is why the screen
cannot be the final word regardless of what survives it.
