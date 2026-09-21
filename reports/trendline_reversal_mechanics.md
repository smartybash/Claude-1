# Trendline reversal system — mechanics, state machine, and what is still missing

**No performance number is produced here.** This file does the step you asked
for first: replicate the mechanics, name every discretionary element, and
convert the triggers into a state machine. It also reports what the supplied
TradingView export already settles on its own.

**Sealed NQ days stay sealed. 2016–2020 stays unread.**

---

## 1. Can we test? Partly. Three rule facts are still missing.

**The execution-model comparison is feasible** — the data supports it, on a
smaller window than the export covers. **But I cannot generate a single signal
yet**, because the export shows what the system *did*, not what it *decides*.

Missing, and each one is blocking:

| # | Unknown | Why nothing runs without it |
|---|---|---|
| 1 | **How the trendline is anchored** | Pivot lookback? Fractal degree? Highest/lowest over N bars? Manually drawn? This *is* the entry price. Every fill in every model is the line's value. |
| 2 | **How the stop price is set** | The one stop in your sample is 6.36 pts from entry. Fixed points? ATR multiple? The opposite line? A swing extreme? |
| 3 | **How the target price is set** | Your 13 targets range **14.43 → 21.55 pts**, so it is **not a fixed distance**. Something scales it, and Model C's answer depends entirely on what. |

Everything else I need, the export already gave me (§4).

---

## 2. What your export settles before I run anything

### 2.1 Your own stop-vs-reverse figure is the first hypothesis, answered

> *"438 trades hit their stop on a bar where the opposite trade opened between
> entry and stop. Reverse on books them at the new entry; Reverse off, at the
> stop. 'Stop' shows that case: **−$70,788** at this size."*

| Reverse setting | Net P&L |
|---|---|
| **on** (your chart) | **+$343,262** |
| **off** | **−$70,788** |
| **swing** | **$414,050** |

**One intrabar ordering assumption, applied to 438 of 2,147 trades (20.4%), is
worth 121% of the entire result.** Flip it and the system loses money.

That assumption is not a cost model or a slippage estimate. It is the claim
that *when a bar touched both your stop and the opposite entry, the opposite
entry came first* — a claim a 5-minute OHLC bar contains no information about.

**Caveat on this number, stated rather than glossed:** your text does not make
clear whether "Reverse off" re-prices the *same* 438 trades or produces a
*different trade path* from that point on. A $414,050 swing over 438 trades is
$945 a trade, which is larger than your average win ($630) — too large for a
pure re-pricing, since the difference per trade is bounded by the stop
distance. So it is probably a path change. **The replication will resolve
which**, and that distinction matters for how the result is described.

### 2.2 27 of 30 fills in your sample cannot exist

NQ trades on a 0.25 grid. From the 15 trades you supplied for Fri 18 Sep:

| | on the 0.25 grid | off it |
|---|---|---|
| entries | **3 of 15** | 12 |
| exits | **0 of 15** | 15 |
| **all fills** | **3 of 30** | **27** |

Prices like `29697.38`, `29690.80`, `29686.42` are the mathematical value of a
sloped line, not tradeable prices. Entries, stops and targets are all computed
as continuous values and never snapped to the tick grid.

This is not a rounding quibble. **A 6.36-point stop is 25 ticks.** Snapping
entry and stop to the grid moves each by up to half a tick, and the direction
of that movement is not random — it is adverse on both legs for a strategy
entering *at* a line rather than through it.

### 2.3 Same-bar re-entry is favourable every time it appears

Your v2.6.2 note flags this: with re-entry wait 0, a new trade can open on the
bar the last one closed, at a line price the market passed *before* that exit.

In your 15-trade sample:

| exit | re-entry | side | advantage |
|---|---|---|---|
| Thu 20:10 @ 29676.20 | 29689.50 | short | **+13.30 pts** |
| Thu 20:35 @ 29673.82 | 29686.42 | short | **+12.60 pts** |
| Thu 21:40 @ 29674.89 | 29662.02 | long | **+12.87 pts** |
| Thu 22:40 @ 29695.70 | 29690.86 | long | **+4.84 pts** |
| Fri 04:25 @ 29904.42 | 29904.42 | short | 0.00 (a true reversal) |

**4 instances with a non-zero gap. All four favourable. None adverse.**
Total **+43.61 points = $872**, which is **22.4% of that day's $3,889**.

If same-bar re-entry were a neutral artefact, roughly half of these should be
adverse. Zero are. My reconstruction of the day totals 194.46 pts = $3,889
against your reported $3,888.92, so I am reading the export correctly.

### 2.4 The win rate against the right benchmark

Your aggregate: average win $630 (31.5 pts), average loss $464 (23.2 pts), so
the **realised reward-to-risk is 1.36**.

For a driftless random walk between two barriers at that ratio:

```
P(target first) = 1 / (1 + 1.36) = 42.4%
```

| | |
|---|---|
| reported win rate | **57%** |
| random-walk rate at the realised 1.36 RR | **42.4%** |
| **gap** | **+14.6 points** |

**That 14.6-point gap is the whole claim.** It is what Models B and C have to
either preserve or destroy. Benchmarking against 50% would understate it;
benchmarking against nothing would make it unfalsifiable.

---

## 3. The state machine

Positions are `FLAT`, `LONG`, `SHORT`. With Reverse on and re-entry wait 0, the
system is near-always in the market.

```
                    ┌──────────────────────────────────────────┐
                    │                  FLAT                    │
                    │   (only at the very start of the record) │
                    └───────┬──────────────────────┬───────────┘
              LONG_TRIGGER  │                      │  SHORT_TRIGGER
                            ▼                      ▼
        ┌────────────────────────┐      ┌────────────────────────┐
        │         LONG           │      │         SHORT          │
        │  entry = line price    │      │  entry = line price    │
        │  stop  = ?  (UNKNOWN)  │      │  stop  = ?  (UNKNOWN)  │
        │  tp    = ?  (UNKNOWN)  │      │  tp    = ?  (UNKNOWN)  │
        └──┬────────┬────────┬───┘      └──┬────────┬────────┬───┘
     TARGET│    STOP│     REV│         TARGET│    STOP│     REV│
           ▼        ▼        ▼               ▼        ▼        ▼
         exit@tp  exit@stop  exit@new      exit@tp  exit@stop  exit@new
                             short entry                       long entry
           │        │        │               │        │        │
           └────────┴────────┴──► re-entry wait = 0 ◄─┴────────┘
                        a new position may open ON THE SAME BAR
```

### The four triggers

| trigger | condition | fill price | model sensitivity |
|---|---|---|---|
| **ENTRY** | price reaches the trendline value | **at the line price, intrabar** | **A: at the line. B: next bar open. C: first tick at/through the line, snapped to 0.25** |
| **STOP** | price reaches the stop level | at the stop | A: intrabar. B: next bar open. C: first tick through, with BBO |
| **TARGET** | price reaches the target level | at the target | as above |
| **REVERSAL** | the opposite ENTRY fires while in position | **Reverse on: the new entry price. Reverse off: the stop** | **the 438-trade fork in §2.1** |

**SESSION END never fires.** Your session is 24h, so the bell has no boundary
to trigger on. That is consistent with your sample: 0 session-end exits.

### The ordering problem, stated exactly

When one 5-minute bar touches **both** the stop and the opposite entry, the
OHLC contains **no information** about which came first. Model A resolves it
optimistically (reversal first, book at the new entry). Model C resolves it
from the tick sequence. **That single disagreement is the 438 trades.**

---

## 4. Discretionary and undetermined elements, listed explicitly

### Known from the export — no discretion left

| element | value |
|---|---|
| instrument / timeframe | NQ (CME Mini NQ1!), **5-minute** |
| session | **24h**; bell ticked but never fires |
| re-entry wait | **0 bars** |
| entry execution | intrabar, **at the trendline price** |
| reversal booking | **at the new entry** (Reverse on) |
| pyramiding | none evident — one position at a time |
| costs on the headline | **none charged** |

### Unknown — blocking (§1)

Trendline anchoring · stop rule · target rule.

### Undetermined — not blocking, but each needs a declared answer

| # | element | why it matters |
|---|---|---|
| 1 | **Does the trendline repaint?** If a new pivot re-anchors the line, do past signals change? | If yes, Model A is not merely optimistic — it is unimplementable, and a fourth model is needed |
| 2 | **Intrabar ordering** when stop and reversal both touch | the 438 trades; Model C settles it |
| 3 | **Gap-through entries** — the line price is passed without trading at it | A fills anyway; C cannot |
| 4 | **Tick snapping** of entry, stop and target | §2.2; 27 of 30 fills currently impossible |
| 5 | **Trigger type** — close beyond the line, wick touch, or tick through | changes the bar on which everything fires |
| 6 | **Always-in-market?** Does "trade count" mean entries or round turns? | 2,147 entries vs ~1,074 round turns |

---

## 5. What the data allows, decided

### 5.1 The tick archive is not uniform, and this constrains Model C

| tape format | price resolution | sessions (non-sealed) | span |
|---|---|---|---|
| encoded `fmt=1` | **0.25 pts — true tick** | **36** | 2026-07-01 → 2026-08-20 |
| plain CSV | **5.0 pts — quantised** | 17 | 2026-07-12, 2026-08-21 → 09-11 |

The plain files carry only 93–123 distinct prices a day. **A 6.36-point stop is
1.3 steps on a 5-point grid** — whether it was touched is not resolvable, and
neither is the stop-versus-reversal ordering that the whole question turns on.
**Model C is therefore impossible on those 17 sessions** and they are excluded
from the comparison rather than silently included at lower fidelity.

### 5.2 The testable window

| | |
|---|---|
| **Models A, B and C all comparable on** | **36 sessions, 2026-07-01 → 2026-08-20** |
| true tick resolution | 0.25 pts, ~470–515k prints a session, 24h coverage |
| BBO available | **all 36** — bid/ask at the execution instant |
| sealed days included | **zero** |
| your trades in that window | **≈1,031** (July 22 days ≈597, August 14 days ≈434) |
| share of your 2,147 | **≈48%** |

All three models run on **bars built from the same ticks**, not from a stored
bar file. A vendor mismatch would show up as a fill difference that is not one.

### 5.3 What is excluded, and why

| excluded | trades | P&L | reason |
|---|---|---|---|
| **8–30 June 2026** | **436** | **$97,328 (28.4%)** | **sealed. Not read.** |
| 2026-07-23 | ~27 | — | sealed |
| 2026-08-21 → 09-11 | ~330 | — | 5-point quantised; Model C impossible |
| 2026-09-12 → 09-18 | ~110 | — | outside the archive |

**Your headline period opens inside the sealed block.** 8 June is the first
trading day of your record and June carries 28.4% of the reported P&L. None of
it will be read.

---

## 6. What I will report, per model, once the rule is supplied

Trade count · win rate · average win · average loss · profit factor ·
expectancy · maximum drawdown · P&L — for A, B and C separately, plus:

- **trades that change solely because of fill assumptions**, decomposed into:
  entry-price difference, stop-versus-reversal ordering, same-bar re-entry, and
  gap-through entries that cannot fill;
- **win rate against the random-walk rate at each model's own realised
  reward-to-risk**, not against 50%;
- clustered errors by date, and the `max(10, ⌈0.10n⌉)` concentration profile.

**Maximum drawdown over 36 sessions carries almost no information** and will be
reported flagged as such rather than left to read as a risk statistic.

**No optimisation.** Every parameter is whatever you supply.

---

## 7. The three answers I need

1. **Trendline anchoring** — what defines the two points, and does it repaint?
2. **Stop rule** — what sets the stop price?
3. **Target rule** — what sets the target? Your 13 targets span 14.43–21.55 pts,
   so it is not fixed.

With those, the state machine in §3 has no empty slots and all three models run.

---

# PART 2 — what the evidence constrains, and the pseudocode

**I cannot supply the four specification blocks.** Anchoring, stop rule, target
rule and reversal ordering are facts about your script. Writing plausible
answers and then testing them would produce numbers describing my guess.

What follows is (a) what your data *does* constrain, and (b) the full state
machine with the unknowns as named slots.

## 2.1 The stop is not fixed

| | |
|---|---|
| the one stop in your sample | **6.36 pts** |
| aggregate average loss | **23.2 pts** |
| ratio | **3.6×** |

A fixed-point stop caps ordinary losses near a constant. These are 3.6× apart.
**Rules out a fixed stop.** Consistent with ATR-scaled, swing-based, or
geometry-based.

## 2.2 Target does not scale with per-trade risk — or risk is flat within a day

| | |
|---|---|
| TP spread **within** the sample day | 14.43 → 21.55 = **1.49×** |
| stop spread **across** the record (implied) | **3.6×** |

If `TP = m × risk` and risk varies 3.6× across the record, TP should vary as
much wherever risk does. Within one day it varies only 1.49×. Two readings,
both consistent:

- TP scales with something smoother than per-trade risk (session volatility,
  channel width); **or**
- risk is near-constant *within* a day and varies *across* days — which is
  exactly what an ATR-based stop does.

**The second is the more economical explanation and fits everything else.**

## 2.3 A reversal exit breached its own stop by ~4×

Fri 04:20 Long 29929.25 → Fri 04:25 exit **29904.42** on `Rev`, **−24.83 pts**.

The sample's stop was 6.36 pts. If that trade's stop were similar, price ran
**18.5 points past it** and the trade still booked at the reversal price.

**This contradicts the export's own description** — *"the opposite trade opened
between entry and stop"*. Either that trade's stop was wider than 24.83, or
**reversal exits are not bounded by the stop**. Both cannot be true.

**This is the single most important thing to resolve**, because it decides
whether the stop is a real risk limit or a level the reversal path can ignore.

## 2.4 Where the losses actually sit — a reconstruction, assumptions stated

Assuming the sample day's reward-to-risk (2.62) holds on average, and that
stop exits lose R while reversal exits lose X:

| | |
|---|---|
| implied average risk R | **12.0 pts ($241)** |
| implied average target | 31.5 pts |
| stop exits | 485, losing ~12.0 pts |
| **reversal exits** | **438, losing ~35.6 pts = 3.0× the stop** |
| **share of ALL loss carried by reversal exits** | **≈ 73%** |

**Cross-check:** the reconstruction predicts reversal exits average 3.0× their
stop; the one observed `Rev` is **3.9×**. Right order of magnitude.

> **20.4% of trades carry roughly three-quarters of all losses, and those are
> exactly the trades whose exit price is set by an intrabar ordering
> assumption.**

This sharpens the hypothesis. The A-versus-C difference will not be spread
evenly across 2,147 trades — it concentrates almost entirely in the 438.

**Flagged as a reconstruction, not a measurement.** It rests on the sample day's
RR generalising, and that day was 87% winners against a 57% record. A full
trade list replaces it with the real numbers.

## 2.5 Pseudocode — complete except for three named slots

```
# ---------------- UNKNOWN, must be supplied ----------------
# U1  anchor(bars, i) -> (line_long, line_short)
#       Q1.1 what two points anchor the line?
#       Q1.2 do anchors move after placement?
#       Q1.3 do pivots need future bars to confirm?   <- if yes, LOOKAHEAD
#       Q1.4 can the line repaint?                    <- if yes, Model A is
#                                                        unimplementable, not
#                                                        merely optimistic
# U2  stop_px(side, entry, bars, i) -> price
#       Q2.1 rule?  Q2.2 ATR?  Q2.3 swing?  Q2.4 line geometry?
# U3  target_px(side, entry, stop, bars, i) -> price
#       Q3.1 formula?  Q3.2 scales with risk?  Q3.3 with channel size?
#       Q3.4 modified after entry?              <- trailing changes everything
# -----------------------------------------------------------

REENTRY_WAIT = 0        # known
REVERSE_ON   = True     # known
SESSION      = 24h      # known: the bell has no boundary, never fires
TICK         = 0.25     # NQ

state, pos = FLAT, None

for i in bars:                                   # 5-minute NQ
    line_L, line_S = U1.anchor(bars, i)
    sig_L = triggered(bars[i], line_L, UP)       # UNKNOWN trigger type:
    sig_S = triggered(bars[i], line_S, DOWN)     # touch | close | tick-through

    if state == FLAT:
        if sig_L or sig_S:
            enter(side, px = line_price)         # A: at the line
        continue                                 # B: next bar open
                                                 # C: first tick at/through,
                                                 #    snapped to TICK, BBO-crossed
    hit_stop = touched(bars[i], pos.stop_px)
    hit_tp   = touched(bars[i], pos.tp_px)
    hit_rev  = sig_S if pos.side == LONG else sig_L

    # ================= THE ORDERING PROBLEM =================
    # When two or more of these fire on ONE 5-minute bar, the OHLC
    # contains NO information about which came first.
    #
    #  MODEL A  reversal wins ties, books at the NEW ENTRY price.
    #           This is the 438 trades. Optimistic by construction.
    #  MODEL B  nothing resolves intrabar. Everything executes at the
    #           NEXT bar's open. Ties cannot exist.
    #  MODEL C  read the tick sequence. Whichever price printed first,
    #           wins. No tie is ever resolved by assumption.
    # ========================================================

    if hit_stop or hit_tp or hit_rev:
        exit_px = resolve_exit(model, bars[i], ticks[i], pos)
        close(pos, exit_px)
        if hit_rev and REENTRY_WAIT == 0:
            enter(opposite_side, px = line_price)   # SAME BAR — the
                                                    # v2.6.2 lookahead
```

## 2.6 The one artefact that removes all three unknowns without source code

**The full List of Trades export as CSV** — all 2,147 rows, with entry price,
exit price, both timestamps, side, and exit type.

From that I can **derive** the rules rather than be told them:

| derivable | how |
|---|---|
| **stop rule** | every `SL` row gives an exact stop distance. Regress it on ATR(n) at entry, on the prior swing distance, and on the line-to-line channel width. Whichever fits, wins |
| **does TP scale with risk** | pair `TP` distances against the stop distances of neighbouring trades on the same day. Constant ratio → risk-scaled. Constant absolute → volatility-scaled |
| **TP formula** | same regression, against the same candidates |
| **reversal ordering** | every `Rev` row where the exit is *beyond* the stop distance proves reversal exits are not stop-bounded. One such row already exists (§2.3); the count settles it |
| **anchoring** | the hardest. Entry prices give the line's value at known timestamps. **Two entries on the same line give its slope**, and the slope points back at the anchor bars |

That last one is the real prize: **a full trade list is a set of samples of the
trendline function**, and with enough of them the anchoring rule is recoverable
by fitting rather than by guessing.

**If you can send the trade list covering 2026-07-01 → 2026-08-20**, those rows
sit inside the true-tick window and I can reconcile them print by print.
