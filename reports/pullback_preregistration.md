# Pullback continuation: constraints, rule, grid and bar — fixed before any result

Committed before a single backtest runs. Nothing below was chosen knowing an
outcome.

---

## Part 1 — your constraints as mechanical requirements

| your constraint | mechanical requirement |
|---|---|
| max two trades per RTH session | a counter per session, hard cap 2 |
| never open at the same time | a state machine FLAT → ARMED → IN → FLAT; nothing can arm while IN |
| a second setup arms only after the first closes | the scan resumes at the exit timestamp of trade 1, not before |
| no discretionary reading | every branch is a comparison of numbers already recorded |
| no averaging down | position size is fixed at entry and never added to |
| hard stop on entry | a stop price computed from prices known at or before the entry print |
| flat by 22:30 Dubai | **18:30 UTC** hard exit at market, whatever the position |
| realistic commissions and slippage | 2.0 points charged per round turn, applied to every trade |
| no information unavailable at the decision timestamp | every input is a running statistic over prints already seen |

**One thing to confirm, and I have not adjusted it to suit myself.** You said
Dubai, which is UTC+4, so 22:30 Dubai is **18:30 UTC** and that is what I have
used. The earlier record in this project treats "22:30 local" as **17:00 UTC**,
which is India at UTC+5:30. Those are ninety minutes apart and it changes which
variants are even legal. I have used your stated Dubai. If you are actually on
IST, say so and the cutoff becomes 17:00 UTC — it is one constant.

**Cost.** 2.0 points round turn, charged on every trade. NQ is $20 a point, so
that is $40 a round turn against a commission of roughly $4 — the rest is
slippage, one to two ticks in and one to two out, which is honest for stop
entries and market exits in a pullback. Cost is **not** a grid parameter. A
sensitivity run at 3.0 points is reported alongside as a robustness check, not
as a variant to choose from.

### What these rule out automatically

**Every hypothesis in this project as it was previously measured.** That is not
rhetoric, it is arithmetic: each was scored by taking every qualifying signal.

- **VWAP stretch, hold-to-close (20:00 UTC exit)** — illegal. The exit is two
  hours past the flat time. This was the strongest result in the project at
  +21.70 points and t = +2.14, and the constraint kills it outright.
- **VWAP stretch, 19:00 UTC exit** — illegal, thirty minutes past the flat time.
- **VWAP stretch, 17:00 UTC exit** — the clock is legal, but the rule as tested
  takes the top and bottom quintile of *every minute bar*, which is dozens of
  entries a session and frequently overlapping. Illegal as measured. A
  two-trades-only restatement is a different rule and would need its own test.
- **Pullback continuation as originally measured** — 3,246 returns across 47
  sessions, about 69 a session, all overlapping. Illegal as measured. This
  document is that restatement.
- **All order-flow gates** — already closed, and separately illegal as measured
  for the same reason.
- **Level fades, gap fill, the structure trade** — dead on their own merits;
  the constraints are not what closes them.

The honest summary: **the constraints do not merely filter the candidate list,
they invalidate the measurement method used for everything so far.** Nothing
previously reported survives as a number. Everything has to be re-earned under
two trades a session.

---

## Part 2 — why the anchor is not arbitrary

The original pullback result had a placebo attached to it: shifting the level
25 points to a price that was never a level paid the **same or better**. So a
rule anchored to some specific price discovered in the data would be anchored
to nothing — that is exactly what the placebo proved.

The anchor therefore has to satisfy three things: fixed by the clock rather than
chosen from the data, economically meaningful to participants other than us,
and carrying a direction.

**The opening range does all three.** It is complete at a fixed time, so "armed"
has an unambiguous timestamp and no lookahead is possible. Breaking it gives a
direction the bare open price cannot. Its height is the session's own early
volatility, so a departure measured as a multiple of it means the same thing on
a quiet day and a wild one — which the original fixed 15 points did not. And it
is the reference every futures desk already watches, so it is not a construct
invented to fit this data.

The RTH open price alone was considered and rejected: it is a single price with
no direction and no scale.

---

## Part 3 — the rule, every value measurable at entry

All times UTC. Prices are the recorded tape at 0.25 resolution.

```
CONSTANTS (fixed, not swept)
  RTH_OPEN      13:30
  BREAK_TICKS   2        beyond the OR edge to count as a break
  PB_LO, PB_HI  0.25, 0.75   the pullback zone, as a fraction of the move
  REJ_TICKS     4        turn off the pullback extreme to trigger
  STOP_TICKS    4        beyond the pullback extreme for the stop
  MAX_MIN       60       time expiry after entry
  LAST_ENTRY    18:00    no new entry after this
  HARD_FLAT     18:30    exit at market regardless
  COST_PTS      2.0      per round turn
  MAX_TRADES    2        per session

SWEPT (the grid, Part 4)
  OR_MIN        opening range length in minutes
  EXC           minimum excursion, as a multiple of the OR height
  TGT_R         target, as a multiple of the entry risk
```

```
for each session:
    ORH, ORL = high, low of prints in [13:30, 13:30 + OR_MIN)
    ORR      = ORH - ORL
    if ORR <= 0: skip session
    trades = 0
    state  = SCAN
    t      = 13:30 + OR_MIN

    while t < HARD_FLAT and trades < MAX_TRADES:

        if state == SCAN:
            # DEPARTURE: first break of either edge
            if price >= ORH + BREAK_TICKS*TICK:
                dir, edge = +1, ORH
            elif price <= ORL - BREAK_TICKS*TICK:
                dir, edge = -1, ORL
            else:
                advance t; continue
            extreme = price
            state   = EXTEND

        if state == EXTEND:
            extreme = max(extreme, price) if dir>0 else min(extreme, price)
            # the move must actually go somewhere before a pullback counts
            if abs(extreme - edge) >= EXC * ORR:
                move     = abs(extreme - edge)
                zone_far = extreme - dir * PB_LO * move
                zone_near= extreme - dir * PB_HI * move
                state    = WAIT_PULLBACK
            # INVALIDATION: break fails back through its own edge
            elif dir*(price - edge) < -BREAK_TICKS*TICK:
                state = SCAN
            advance t; continue

        if state == WAIT_PULLBACK:
            # RETURN: price trades into the zone
            if dir>0 and price <= zone_far:  pb_ext = price; state = ARMED
            if dir<0 and price >= zone_far:  pb_ext = price; state = ARMED
            # INVALIDATION: retraced past the zone, or back through the edge
            elif dir*(price - zone_near) < 0 or dir*(price - edge) < 0:
                state = SCAN
            advance t; continue

        if state == ARMED:
            pb_ext = min(pb_ext, price) if dir>0 else max(pb_ext, price)
            # INVALIDATION while armed
            if dir*(pb_ext - edge) < 0:
                state = SCAN; advance t; continue
            # REJECTION: price turns REJ_TICKS off the pullback extreme
            trigger = pb_ext + dir * REJ_TICKS * TICK
            if dir*(price - trigger) >= 0 and t < LAST_ENTRY:
                entry = trigger                       # stop order
                stop  = pb_ext - dir * STOP_TICKS*TICK
                risk  = abs(entry - stop)
                if risk <= 0: state = SCAN; advance t; continue
                target  = entry + dir * TGT_R * risk
                expires = t + MAX_MIN minutes
                state   = IN
            advance t; continue

        if state == IN:
            # first touch wins; stop is checked before target on the same print
            if dir*(price - stop) <= 0:      exit at stop
            elif dir*(price - target) >= 0:  exit at target
            elif t >= expires:               exit at market
            elif t >= HARD_FLAT:             exit at market
            else: advance t; continue
            pnl = dir*(exit_price - entry) - COST_PTS
            trades += 1
            state   = SCAN          # a second setup may now arm, not before
```

**No lookahead anywhere.** `ORH`, `ORL`, `ORR` are complete before the loop
starts. `extreme` and `pb_ext` are running statistics over prints already seen.
`entry`, `stop`, `target` and `expires` are all computed from those at the
moment of the trigger print.

**Stop before target on the same print** is deliberate and pessimistic: when a
single print could have hit both, the loss is taken. A tick tape cannot say
which came first inside one print, and assuming the good one is how the earlier
"impossible fill" got into this project.

---

## Part 4 — the grid, declared now

| parameter | values |
|---|---|
| `OR_MIN` | 15, 30 |
| `EXC` | 0.5, 1.0 |
| `TGT_R` | 1.0, 1.5, 2.0 |

**12 variants.** Under the cap of 18, and I am not spending the remaining six
just because they are available. Everything else is fixed at a conventional
value, not one chosen from this data.

---

## Part 5 — rejection criteria, fixed now

A variant is **rejected** if any of these is true:

1. **Expectancy after costs ≤ 0**, per trade.
2. **Fewer than 15 sessions produce a trade.**
3. **Profit factor < 1.15.**
4. **Top-five dependence:** removing the five best trades leaves total P&L ≤ 0.
5. **Instability across the sample.**

### An honest problem with criterion 5, stated before results

Month stability cannot be assessed here. Fourteen of the sixteen sessions are
July 2026 and the other two are August; there is no second month with enough
trades to compare. I am not going to invent a monthly split that does not exist.

The substitute is a **split-half by date** — the first eight sessions against
the last eight — and it is **weaker** than what you asked for. A variant
profitable in both halves has passed something; a variant profitable in one is
rejected. When more months exist this must be redone properly.

### The larger honest problem: this batch can reject, it cannot confirm

Two trades a session across sixteen sessions is **at most 32 trades**, and in
practice fewer because not every session will produce a setup. Expectancy and
profit factor on thirty-odd trades are extremely noisy.

**So the purpose of this run is elimination.** A variant that fails is dead. A
variant that passes is *not* evidence of an edge — it is a candidate that has
not yet been killed, and it would need the sealed days and then many more
sessions before it means anything. I will say exactly that when reporting, and
will not present a survivor as a finding.

---

## Part 6 — reporting

Every variant reports both, and the per-session numbers govern:

- **per trade:** n, expectancy after cost, win rate, profit factor, average win
  and loss, worst trade
- **per session:** sessions with a trade, mean session P&L, t across sessions,
  sessions positive
- **robustness:** the same at 3.0 points of cost, and the split-half

t is computed across sessions, never across trades, because two trades in one
session share that session's conditions and are not independent.

**Sealed days stay sealed.** The session list is built from the explored pile
only, excluded at construction rather than filtered afterwards.
