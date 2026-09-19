# ORB + Fibonacci, continuation and reversal — declared before running

Everything below is fixed before any performance number exists. **X, Y, Z, the
Fibonacci bands, the bar resolution, the entry rule, the stop buffer, the exit
rule, the variant grid and the rejection thresholds are all declared here and
will not be moved.**

**Sealed NQ days stay sealed. 2016–2020 stays unread.** This screen reads only
`data/intraday_long/QQQ_1m.parquet`, which begins 2021-01-04 and cannot reach
2016–2020. Sealed dates (`202606*`, `20260723`) are excluded at construction.

**Continuation and reversal are reported separately and never pooled.** They
are different hypotheses with different sequence lengths and different sample
sizes. Pooling would let the larger family carry the smaller one, which is the
specific failure mode this instruction exists to prevent.

---

## 1. The two undefined components, mechanised as specified

I am testing their rule, not an improved one. Where the source is silent I pick
one value, declare it here, and do not sweep it.

### 1.1 Outburst — the impulse leg

> *"After the ORB breaks, an outburst is the first move of at least X times the
> ORB height in the breakout direction, completing within Y bars, with no
> retracement deeper than 50 percent of the leg while it forms. The leg
> terminates at its extreme, and the extreme must be confirmed by Z bars
> without a new extreme."*

| parameter | **declared value** | reasoning, fixed in advance |
|---|---|---|
| **X** | **1.00 × ORB height** | The minimal non-trivial reading of "impulse": the leg must travel at least one full opening range beyond the break. Below 1.0 the word "outburst" means nothing; above it the value is arbitrary. |
| **Y** | **30 bars (30 minutes)** | The leg must reach X within 30 minutes of the break. An impulse that takes longer is not an impulse. |
| **Z** | **5 bars (5 minutes)** | Five consecutive bars with no new extreme confirms the leg has terminated. |

**Operational sequence, exactly:**

1. **Origin O** = the ORB boundary that was broken (ORB high for an up-break,
   ORB low for a down-break). This is the outburst origin.
2. The break is the first bar whose **high exceeds ORB high** (up) or whose
   **low falls below ORB low** (down), on a bar starting at or after the ORB
   window ends.
3. From the break bar forward, track the running extreme `E_run`.
4. **50% invalidation, while forming:** at each bar, if price retraces ≥ 50% of
   `|E_run − O|` before `|E_run − O| ≥ X × ORB height` is achieved, **the
   outburst attempt fails and the session produces no setup.** The 50% rule
   applies from the break until X is reached, which is what *"while it forms"*
   means. Once X is reached the leg is established.
5. **Y limit:** if X is not reached within 30 bars of the break, the attempt
   fails.
6. **Z confirmation:** after X is reached, continue tracking the extreme. The
   outburst extreme **E** is fixed when 5 consecutive bars pass with no new
   extreme. Bars before that confirmation are not available to the entry logic.

**One attempt per session per direction.** The first break is the one tested. A
failed outburst is not retried — *"the first move"* is what the source says.

### 1.2 Structure shift — for the reversal only

> *"After a bullish outburst, a bearish structure shift is a close below the
> most recent confirmed swing low that formed during the outburst. A wick
> through is explicitly not enough, per the source."*

| parameter | **declared value** |
|---|---|
| swing fractal width **k** | **2 bars either side** (the standard 5-bar fractal) |
| confirmation | a swing is *confirmed* only once the **k bars after it have closed** |
| trigger | a bar **CLOSE** strictly below the swing low (above, for the mirror) |

A swing low is a bar whose low is strictly lower than the lows of the 2 bars
before and the 2 bars after it. "Formed during the outburst" = the swing bar's
timestamp lies between the break bar and the confirmed outburst extreme E.

**The close requirement is implemented as a close, not a wick, exactly as the
source insists.** Wick-through is recorded separately as a diagnostic so the
cost of honouring the source's stricter rule is visible.

---

## 2. Fibonacci band — declared, two bands, not swept

| band | near edge (entry) | deep edge (failure) |
|---|---|---|
| **A** | **0.382** | 0.618 |
| **B** | **0.500** | 0.786 |

**Entry is the first touch of the near edge**, as a limit order. This is the
shallowest point of the band, adds no parameter, and is the only choice that
does not require picking a spot inside the band.

**These two bands are the ones named in the brief and are the only two tested.
The band is not swept.**

### The geometry, stated before results, because it sets the burden

Leg length `L = |E − O|`. Entry at retracement `r`. Stop at O. Then:

`risk = (1 − r) × L`

| band | entry | risk | 1R sits at | 2R sits at | 3R sits at |
|---|---|---|---|---|---|
| **A** (r = 0.382) | E − 0.382L | 0.618L | **E + 0.236L** | E + 0.854L | E + 1.472L |
| **B** (r = 0.500) | E − 0.500L | 0.500L | **E (exactly)** | E + 0.500L | E + 1.000L |

**This matters and it is known now, not after.** Because the stop sits all the
way back at the outburst origin, band A's 1R target requires a *new* extreme
0.236 leg-lengths beyond E, and 3R requires price to travel nearly 2.5× the
original impulse. Band B's 1R lands exactly on the outburst extreme. **2R and
3R on either band are demanding intraday targets and are expected to be reached
rarely.** If the family fails, the geometry is a candidate explanation and will
be reported as such rather than presented as a surprise.

---

## 3. The variant grid — 8 of a permitted 12, and the other 4 deliberately unused

| axis | levels |
|---|---|
| ORB window | 09:30–09:45, 09:30–10:00 |
| Fibonacci band | A (0.382–0.618), B (0.500–0.786) |

**4 variants per setup × 2 setups = 8 variants.**

The brief permits 12. **I am using 8 and leaving 4 unused.** The remaining
budget is not spent on a third axis, because any third axis would be a sweep of
X, Y, Z or the band, all of which are declared fixed above. Declaring unused
headroom is the point: it removes the temptation to fill it after seeing
results.

**Targets are not a variant axis.** *"Targets 1R, 2R, 3R and close"* is read as
one managed trade, not four hypotheses. Treating targets as an axis would give
2 × 2 × 4 = 16 variants per setup and blow the budget twice over.

### Exit rule, declared

**Primary (the rule that is tested):** scale out in **equal thirds at 1R, 2R and
3R**, with any remainder closed at **16:00 ET**. The stop at the outburst origin
applies to the whole remaining position. Thirds is the only symmetric division
of three targets and introduces no free parameter.

**Context only (explicitly non-inferential):** the same trades exited whole at
1R, at 2R, and at 3R are reported alongside so the target structure is visible.
**These are not counted as variants and no pass/fail verdict is drawn from
them.** They exist so that a failure can be attributed correctly.

### Stop

`stop = O − buffer` for longs, `O + buffer` for shorts, **buffer = $0.01** (one
cent on QQQ). This is what *"beyond the outburst origin"* means. Stop exits fill
at `min(stop, bar open)` for longs — gapping through is modelled, not ignored.

---

## 4. The reversal sequence, in full

All seven conditions must complete **within the same session**:

1. ORB break (say up)
2. Bullish outburst, as defined in §1.1
3. **Fib failure** — a bar **closes beyond the deep edge** of the declared band
   (below 0.618 for band A, below 0.786 for band B) measured on the retracement
   from E back toward O
4. **Bearish structure shift** — a close below the most recent confirmed swing
   low that formed during the outburst (§1.2)
5. **Opposite (bearish) outburst** — same X, Y, Z, same 50% rule, mirrored.
   Its origin `O2` = the highest high between E and the start of the opposite
   leg, which is *"the new swing"* the brief refers to
6. **New Fibonacci** from `O2` to the opposite outburst extreme `E2`
7. **Entry** on first touch of the near edge of the band; stop beyond `O2`;
   same target logic

**This is a seven-link chain inside one session. It will fire rarely, and how
rarely is the first thing reported.**

---

## 5. The count that decides whether this family can be resolved at all

> *"State up front how many sessions produce a reversal setup. If it fires on
> fewer than 150 sessions the family cannot be resolved and I want to know that
> before results."*

**The counting pass runs first and is reported before any performance number
exists.** If the reversal setup fires on fewer than 150 sessions at every
variant, I will report that the reversal family is **unresolvable at this
sample size** and will not present its expectancy as evidence either way.

A count below 150 is not a negative result. It is an absence of resolution, and
it will be labelled that way.

---

## 6. Benchmark — the random-walk rate at each variant's realised reward-to-risk

**Not 50%.** For a trade that exits at either a target or a stop, a driftless
random walk gives

`P(target first) = 1 / (1 + M)` where `M = reward-to-risk`

Realised M is computed per variant as `mean(R | R > 0) / |mean(R | R ≤ 0)|`,
which is well defined for the scale-out rule. A "win" is `net R > 0`.

**The claim under test:** 59.13% at 1.43 RR. A coin at 1.43 RR gives
`1/2.43 = 41.15%`. **The claimed gap is +17.98 percentage points.**

**The gap is stated for every variant**, as `observed win% − 100/(1+M)`.

---

## 7. Multiple testing, stated before results

| | continuation | reversal |
|---|---|---|
| variants | 4 | 4 |
| **Bonferroni α** | **0.05 / 4 = 0.0125** | **0.05 / 4 = 0.0125** |
| two-sided critical z | 2.498 | 2.498 |

Corrected **within each family separately**, because the families are never
pooled. The 8 variants are not corrected as a single block of 8 — that would be
the pooling this brief forbids, applied to the error rate instead of the
returns.

**MDE** = `(2.498 + 0.8416) × sd / √n = 3.340 × sd / √n`, reported with the
actual per-variant sd and n in the counts pass, before expectancy.

**Clustering:** the rule takes **at most one trade per session per variant**
(one ORB break, one outburst, one entry), so there is no within-variant
date clustering to correct. Stated rather than silently skipped; the trade
count and session count are printed side by side so this is checkable.

---

## 8. Standing instrumentation, unchanged

| item | treatment |
|---|---|
| honest fills | entry is a **limit**: fill = `min(limit, bar open)` long, `max(...)` short. Stops gap: `min(stop, bar open)` long |
| naive result | reported alongside every honest figure |
| entry bar | **excluded** from the exit search |
| entry lookahead | counted and reported; must be **0** |
| ambiguous bars | bars spanning both stop and target counted and reported |
| cost | `2.00 / 30000 = 0.667 bps` of price, the project's standing convention, applied unchanged |
| flat by | **16:00 ET**, the current standing constraint |
| bar resolution | **1-minute**, fixed in advance. Both 1m and 5m passed the resolution gate; 1m is chosen because swing-fractal and structure-shift logic needs the granularity. Not swept. |

**Counts before performance, in this order:** sessions → outburst attempts →
outbursts confirmed → setups → trades → *then* any expectancy.

---

## 9. Rejection rules, unchanged

A variant survives only if **all five** hold:

1. positive expectancy **after costs**
2. profit factor **> 1.15**
3. **≥ 4 of 6** years positive
4. positive after **removing the best 1%** of trades
5. positive at **50% higher cost**

Plus, for this family specifically: the win rate must **exceed the random-walk
rate at its own realised reward-to-risk**. A variant that clears the five
rejection rules but sits at or below `1/(1+M)` has not demonstrated anything
the geometry did not already supply.

---

Committed before `scripts/orderflow/orb_fib.py` was written or run.
