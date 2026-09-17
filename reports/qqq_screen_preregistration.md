# QQQ broad screen: translation, the bar-resolution gate, and the plan

Written before anything runs.

---

## 1. Confirming the expectancy point — you are right and I was sloppy

**"1 to 2 points" is average net expectancy per trade after losers. It is not a
profit target.** Confirmed. Nobody is scalping two points. On a 17-point stop
with a 2-point round turn:

| target | points | avg win | avg loss | win rate needed for +1 | +2 | +5 | +10 | coin |
|---|---|---|---|---|---|---|---|---|
| 1.0R | 17 | +15 | −19 | 58.8% | 61.8% | 70.6% | 85.3% | 50.0% |
| 1.5R | 26 | +24 | −19 | 47.1% | 49.4% | 56.5% | 68.2% | 40.0% |
| 2.0R | 34 | +32 | −19 | 39.2% | 41.2% | 47.1% | 56.9% | 33.3% |
| 3.0R | 51 | +49 | −19 | 29.4% | 30.9% | 35.3% | 42.6% | 25.0% |
| 4.0R | 68 | +66 | −19 | 23.5% | 24.7% | 28.2% | 34.1% | 20.0% |

So a **+2 point expectancy** at a 2R target means: risk 17, target 34, win 41%
of the time, average winner +32, average loser −19. That is an ordinary-looking
trade, not a scalp.

The last column is the coin. **The edge the strategy must supply is the gap:**

| target | needed for +2 | coin | edge in win-rate points |
|---|---|---|---|
| 1.0R | 61.8% | 50.0% | **+11.8** |
| 1.5R | 49.4% | 40.0% | +9.4 |
| 2.0R | 41.2% | 33.3% | +7.8 |
| 3.0R | 30.9% | 25.0% | +5.9 |
| 4.0R | 24.7% | 20.0% | **+4.7** |

**Wider targets need less edge**, because the fixed cost is amortised over a
bigger winner. Grid 2 only went to 2.0R. That is a gap in what was tested and
the new grid extends it.

---

## 2. What a desk requires, and it is still several hundred sessions

80% power at two-sided 5% is a lab convention. A desk allocating capital wants,
roughly: **t > 3 on data the rule was not fitted to**, an **annualised Sharpe
above 1** and preferably above 1.5, stability across regimes, and a track
record long enough that the Sharpe itself is distinguishable from zero.

| | edge/session | ann. Sharpe | n for t>2 | **n for t>3** | years @250 |
|---|---|---|---|---|---|
| wide stop (sd 29.2) | 2 pts | 1.08 | 853 | **1,918** | 7.7 |
| | 3 pts | 1.62 | 379 | **853** | 3.4 |
| | 5 pts | 2.71 | 136 | 307 | 1.2 |
| tight stop (sd 13.9) | 2 pts | 2.28 | 193 | **435** | 1.7 |
| | 3 pts | 3.41 | 86 | **193** | 0.8 |
| | 5 pts | 5.69 | 31 | 70 | 0.3 |

**The honest answer is yes, still several hundred sessions** — between about
200 and 2,000 depending on the edge and the stop width. The tight-stop rows are
the achievable ones, and note that a 2-point edge there is a Sharpe of 2.3,
which is a genuinely good strategy rather than a marginal one.

**1,421 QQQ sessions covers every row in that table.** That is the entire
reason for the change of data.

---

## 3. QQQ to NQ: what translates and what does not

### Translates

- **Intraday shape.** Both track NDX. Intraday return correlation is very high,
  and the rule reads structure — an opening range, a break, a retracement — not
  a price level.
- **The rule itself is scale-free.** Every quantity is relative: the excursion
  is a multiple of the opening range height, the pullback is a fraction of the
  move, the stop is a multiple of ATR, the target is a multiple of risk. Nothing
  is denominated in points. This is the property that makes the screen possible
  at all.
- **The cash session.** 09:30–16:00 ET for both.

### Does not translate

- **Absolute points.** QQQ is ~$600, NQ ~30,000. Results must be reported in
  **R multiples and percentages**, never points, and only converted to NQ
  points at the very end.
- **Cost.** 2.0 NQ points is 0.0067% of notional. Expressed that way it carries
  across; expressed in points it is meaningless on QQQ. Cost is modelled in
  **basis points of notional** throughout.
- **The overnight session.** NQ trades around the clock; QQQ does not. The rule
  is RTH-only so this does not affect the mechanics, but the *character* of the
  opening range differs: NQ's cash open follows a live overnight auction, QQQ's
  follows a closed book. **This is the largest untestable difference and is the
  reason the screen cannot be the final word.**
- **The clock.** The flat time is fixed in Dubai wall-clock, so 18:30 UTC. In
  US summer that is 14:30 ET, five hours after the open; in US winter it is
  13:30 ET, four hours. The trading window is genuinely an hour shorter in
  winter and is modelled that way rather than fixed at five hours.
- **Tick size and dividends.** QQQ's penny tick is relatively coarser and it
  pays dividends. Both are small at this stop size and are noted, not modelled.

---

## 4. The intra-bar ambiguity, and why it is a GATE rather than a caveat

When a one-minute bar's high reaches the target and its low reaches the stop,
the bar cannot say which came first.

**I was about to wave this away and the measurement says I should not.**

```
QQQ 1-minute bar range, as % of price:  median 0.055%,  p90 0.132%
NQ equivalent at 30,000:                median 16.6 pts, p90 39.6 pts

a 17-point NQ stop  = 0.057%   <- the SAME SIZE as the median bar
a 34-point NQ stop  = 0.113%   <- about twice the median bar
a  2-point NQ stop  = 0.0067%  <- far inside one bar
```

The 2-point stop of grid 1 was hopeless on bar data, which is right. But a
17-point stop is **not** comfortably larger than a one-minute bar — it is the
same size. So ambiguity will be common at the tighter setting and only moderate
at the wider one.

### The gate

**Before any QQQ result is produced, the proxy gets calibrated against the
truth on data where both exist.**

Run the identical rule twice on the same 20 NQ sessions:

1. on the **tick tape** at one-second resolution — the truth, already built
2. on **NQ one-minute bars** derived from that same tape — the proxy

Then report: the fraction of trades where a single bar spans both stop and
target, and the difference in expectancy and win rate between truth and proxy.

**Pass condition, fixed now:** the proxy is usable for a given stop setting if
the ambiguous fraction is **below 20%** and the expectancy difference is
**below 0.25R**. A setting that fails is **not screened on QQQ at all** — it is
reported as untestable on bar data rather than tested badly.

Throughout, the pessimistic convention already in the backtest holds: when a bar
spans both, **the stop is taken**. That biases every result downward, so a
strategy that survives the screen is not surviving on a favourable assumption.

**If both stop settings fail the gate, the QQQ screen does not happen and I
will say so.** That is a real possible outcome of this step.

---

## 5. The plan, in order

1. **Calibrate** — NQ ticks versus NQ one-minute bars, 20 sessions. Gate above.
2. **Screen** — surviving stop settings on QQQ 1-minute, 1,417 full sessions,
   costs in basis points, results in R multiples.
3. **Verify** — anything surviving the screen is re-run on the 20 NQ tick
   sessions at full resolution.

Sealed days stay sealed at every step.

## 6. The grid, declared now

| parameter | values |
|---|---|
| `OR_MIN` | 15, 30 |
| `STOP_ATR` | 0.5, 1.0 |
| `TGT_R` | 1.0, 2.0, 3.0, 4.0 |

**16 variants.** `TGT_R` extends to 3 and 4 because the table in section 1
shows those need the least edge, and grid 2 never tested them. `EXC` stays at
0.5, still carried from grid-1 counts and still logged as data-informed.

## 7. Criteria, unchanged in spirit and adjusted for the sample

On 1,417 sessions the earlier thresholds are too weak to be meaningful, so:

1. **Expectancy > 0** after costs, in R.
2. **t > 3 across sessions** — the desk standard from section 2, not the lab one.
3. **Profit factor > 1.15.**
4. **Not top-5 dependent** — and on this sample, not top-1% dependent either.
5. **Stable across years.** 2021–2026 gives five calendar years; a variant must
   be positive in at least four, and this finally replaces the split-half
   substitute that 20 sessions forced.

**16 tests.** Bonferroni puts the per-test bar at about t > 3.5; criterion 2 is
stated at 3 and the stricter figure is applied when judging survivors.

**And the standing caveat, now pointing the other way:** a survivor on 1,417
QQQ sessions is a candidate that has passed a real test on a proxy instrument.
It is still not a finding for NQ until step 3 agrees.

## 8. Ledger

The pullback family is **closed** on NQ. This screen is a **new family** — the
same structural idea on a different instrument, with a different sample, testing
targets the closed family never reached. It does not reopen the NQ result and
does not touch the sealed days.
