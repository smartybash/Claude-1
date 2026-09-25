# Opening range breakout with a session VWAP filter — declared before running

New hypothesis family. Committed before a single result exists. Screened on the
1,418 QQQ sessions; **no NQ verification unless something survives**, and the
eight sealed June days and 23 July are not read at any point.

---

## 1. Why this is a different family from the one that just closed

The pullback family asked *does a retracement continue*. This asks *does a
range break hold*, and it adds a condition the pullback never had: **a filter
that can veto a signal outright**. The two rules share an anchor (the opening
range) and nothing else — different entry, different trigger geometry,
different failure mode.

The VWAP filter is the point of the family, so it is **not a swept axis**. It
is fixed on, and the unfiltered version is run separately as a diagnostic that
**cannot produce a survivor** (section 7).

---

## 2. The rule, every value known at its decision timestamp

All times are the session's own clock. Prices are QQQ one-minute bars.

```
FIXED (not swept)
  RTH_OPEN     09:30 ET
  BREAK        0.167 bps of price     beyond the OR edge to count as a break
  LAST_ENTRY   18:00 UTC              no new entry after this
  HARD_FLAT    18:30 UTC              exit at the close of that bar, always
  COST         0.667 bps round turn   the NQ 2.00-point figure restated
  FLOOR        0.667 bps              minimum stop distance
  MAX_TRADES   2 per session

SWEPT (section 6)
  OR_MIN       opening range length, minutes
  STOP_ATR     stop distance as a multiple of 20-bar 1-minute ATR
  TGT_R        target as a multiple of entry risk
```

```
ORH, ORL = high, low of bars in [09:30, 09:30 + OR_MIN)
ORR      = ORH - ORL ;  skip the session if ORR <= 0
armed    = {long: True, short: True}
state    = SCAN ;  trades = 0

while bars remain and trades < 2:

  SCAN:
    # RE-ARMING. Without this a stopped-out long re-triggers on the next bar,
    # because the stop sits above the range edge. A side re-arms only when
    # price trades back INSIDE the range.
    if not armed.long  and low  <= ORH:  armed.long  = True
    if not armed.short and high >= ORL:  armed.short = True

    trig_long  = ORH + BREAK
    trig_short = ORL - BREAK
    hit_long   = armed.long  and high >= trig_long
    hit_short  = armed.short and low  <= trig_short

    # A single bar reaching BOTH triggers cannot say which came first.
    # Take neither, count it, move on.
    if hit_long and hit_short:  skip the bar

    dir, trig = the one that fired
    fill = max(trig, bar_open) if dir>0 else min(trig, bar_open)

    # THE FILTER. VWAP runs from the RTH open over bars already CLOSED, so it
    # is known before this bar. Evaluated at the fill, which is where price
    # actually was at the decision timestamp.
    if dir>0 and fill <= VWAP_prior:  veto, count it, move on
    if dir<0 and fill >= VWAP_prior:  veto, count it, move on

    if now >= LAST_ENTRY: move on

    stop   = trig - dir * max(FLOOR, STOP_ATR * ATR)
    risk   = |fill - stop|
    target = fill + dir * TGT_R * risk
    armed[dir] = False ;  state = IN

  IN:
    stopped = low <= stop   (long) ;  hit = high >= target (long)
    if stopped:  exit at min(stop, bar_open), or at stop on the entry bar
    elif hit:    exit at target
    elif last bar of the window:  exit at that bar's CLOSE
    on exit: trades += 1 ;  state = SCAN      # a second setup may now arm
```

**Three deliberate differences from the last grid, each stated with its
reason:**

1. **No 60-minute expiry.** The constraints given are stop, target, and flat at
   18:30 UTC. The pullback grid's hour-long expiry was my addition and at a 4R
   target it turned the test into *does it move 0.4% within the hour*. The flat
   time is the exit of last resort here, and the window is already only four to
   five hours.
2. **The flat exit is the final bar's close**, not its midpoint. The midpoint
   was never a fillable price and flat exits will be more common without an
   expiry.
3. **The stop is anchored to the trigger level**, not to a pullback extreme,
   because this rule has no pullback.

**Fills use the corrected model throughout.** A stop order fills at the first
price available: `max(trigger, bar open)` for a long. Assuming otherwise is
what manufactured the entire apparent edge of the previous screen.

---

## 3. The arithmetic check, done before the run

From the previous screen's risk distribution, median risk is roughly 7 bps at
`STOP_ATR` 0.5 and 11 bps at 1.0, against a 0.667 bps cost — so cost is about
**9.5% and 6.1% of risk**. Breakeven win rate is `p = (1 + c) / (M + 1)`:

| target | breakeven, tight stop | breakeven, wide stop | random walk | **edge needed** |
|---|---|---|---|---|
| 1.0R | 54.8% | 53.1% | 50.0% | +4.8 / +3.1 |
| 2.0R | 36.5% | 35.4% | 33.3% | +3.2 / +2.1 |
| 3.0R | 27.4% | 26.5% | 25.0% | +2.4 / +1.5 |
| 4.0R | 21.9% | 21.2% | 20.0% | **+1.9 / +1.2** |

**Wider targets need less edge**, which is why the axis reaches 4R. These
figures are recomputed from the realised risk distribution when the run
reports.

**A prediction, stated now so it cannot be claimed afterwards:** I expect the
VWAP filter to veto a *minority* of breakouts, because a break of the range
high on a normal session is usually already above VWAP. If the veto rate comes
in under about 15% the filter is close to decorative, and I will say so rather
than crediting it with whatever the grid does.

---

## 4. Reporting, fixed now

**Trade counts and session counts before any performance number.** Then, as
standard output and not on request:

- **by calendar year**, 2021–2026
- **by time-of-day bucket**, minutes since the RTH open: `0–60`, `60–120`,
  `120–180`, `180+`
- **by opening range height**, as a ratio to the trailing 20-session mean OR
  height for that same `OR_MIN`: **narrow < 0.8**, **normal 0.8–1.2**, **wide >
  1.2**. Trailing, so no session is bucketed using its own future.

## 5. The slippage audit, reported for every variant

This is what fabricated the last result, so it is a standing output:

- share of entries where the bar had already opened past the trigger
- mean and median unmodelled slippage, in R
- **the expectancy the naive trigger-price fill would have reported**, beside
  the honest one, so the size of the phantom is visible rather than asserted

## 6. The grid: exactly 16

| parameter | values |
|---|---|
| `OR_MIN` | 15, 30 |
| `STOP_ATR` | 0.5, 1.0 |
| `TGT_R` | 1.0, 2.0, 3.0, 4.0 |

The VWAP filter is fixed on and consumes no axis.

## 7. Rejection criteria, fixed now — unchanged from the last screen

A variant is **rejected** if any is true:

1. Expectancy ≤ 0 in R, after costs.
2. `t` ≤ 3 across sessions, zero-trade sessions counted as zero.
3. Profit factor < 1.15.
4. Removing the top 1% of trades leaves total R ≤ 0.
5. Positive in fewer than 4 of the 6 calendar years.

Bonferroni over 16 tests puts the honest bar at **t > 3.5**; criterion 2 is
stated at 3.0 and the stricter figure is applied when judging any survivor.

**The unfiltered control.** The same 16 variants with the VWAP condition
removed are run for attribution only — to say whether the filter does anything
at all. **A control variant cannot be a survivor and cannot be promoted**, and
survivors are drawn only from the 16 filtered variants. Reporting both is not a
32-variant search; selecting from both would be, and that is forbidden here in
advance.

## 8. Standing caveat

**A surviving variant is a candidate, not a finding.** It would have passed a
real test on a proxy instrument, and would still need NQ verification at full
tick resolution before it meant anything for the instrument actually traded.
QQQ's cash open follows a closed book and NQ's follows a live overnight
auction — for an *opening range* family that difference is more pointed than it
was for the pullback, not less, because the opening range is precisely the
object the overnight session shapes.
