# Vol Desk — mechanical GEX swing system for single-stock options

The full picture from scan to exit. This document is the system spec; the
`vol_desk/` package is the executable version of it, and
`tests/test_vol_desk.py` pins every rule and exception below.

## What the system is

A mechanical swing trading system for single-stock options built entirely on
GEX (Gamma Exposure) and dealer positioning data. The core thesis: when dealer
delta positioning flips bullish on a name with strong options structure, price
tends to accelerate toward the next major gamma level — the +GEX. We enter
just above the positive transition level (pTrans) and ride to +GEX as the
primary target.

## The data layer

Two scans run every evening:

- **Gamma screen** — the master file. 700+ names with dealer delta balance,
  prior-session delta, grade across 11 structural rules, OI depth, Minervini
  momentum score, and all key GEX levels (pTrans, nTrans, zeroGEX, +GEX,
  COTMP, COTMC). Every position lives and dies here.
- **P2P scan** (pTrans to +GEX) — a filtered list of names where spot has
  already crossed above pTrans, showing R/R and cushion to the +GEX target.
  This surfaces the immediate entry candidates each evening.

Code: `vol_desk/models.py` (`ScreenRow` is one gamma-screen name).

## Grading a setup — five filters

Every name must clear all five before it touches the portfolio
(`vol_desk/entry.py`):

| # | Filter | Rule | Exceptions |
|---|--------|------|------------|
| 1 | Grade | ≥ 9/11 structural rules | None. Grade ≤ 8 is a hard block. |
| 2 | db_change | ≥ 0.50 vs prior session | Grade-11 DEEP: ≥ 0.30. Sustained (delta pegged at 1.00 two consecutive sessions): exempt — not recovering, already fully positioned. |
| 3 | COTMP cushion | spot ≥ 2.0% above the Center of Put Mass | Grade-11 DEEP and high-db_change names: 1.0%. |
| 4 | Spike-crash | +GEX target must not be a prior spike high where institutional selling already occurred | None. 0/3 on the validated data. Hard no. |
| 5 | R/R | upside to +GEX vs downside to pTrans ≥ 2.0 | None. |

Statuses off the evening scan:

- **CONFIRMED** — all filters pass, spot above pTrans, greenlit at open.
- **PENDING** — filters pass, spot within 0.5% below pTrans; watch the first
  candle.
- **BLOCKED** — any filter failed. No entry.
- (**WAIT** — nothing failed, but spot is too far below pTrans to be a
  candidate; not surfaced by the P2P scan.)

## Entry

No entries on pre-market snapshots. The trigger is the **first 5-minute
candle close above pTrans at the open**. The confirmed close is the signal —
not the level, not the pre-market price. This eliminates fakeouts and gap
fills. The filters (including R/R, now decidable for PENDING names) are
re-validated at that close (`entry.open_trigger`).

## Position management

Once in, entry filter logic no longer applies. The exit framework
(`vol_desk/exits.py`) is the only thing that governs an open position:

- **Stop 1** — close below nTrans → exit at the next open, no discretion.
- **Stop 2** — hard cap of −10% from entry while below pTrans → out
  immediately. Non-negotiable.
- **Stop 3** — time stop: by day 7 the position needs ≥ 50% progress toward
  T1. If not, exit and revisit — a position sitting still for a week isn't
  going to the target; free the capital.
- **Stop 4** — stalling: below 10%/day progress for three consecutive
  sessions → exit regardless of day count.

While above pTrans but short of target the position is **CONFIRMED** — hold.
Below pTrans but above nTrans it moves to **WATCH** — hold existing, add
nothing.

## Taking profit

T1 is the +GEX level. When it hits, two choices: exit and bank the gain, or
lock the stop to entry and ride toward T2 (the next structural level —
usually +GEX next or COTMC). **You cannot hold for T2 without first locking
T1** — that rule exists to prevent giving back a winner chasing an extension.
This is the only discretion the system allows.

## Regime overlay

Three gates daily before approving new entries (`vol_desk/regime.py`):

- **Basket gate** — SPY or QQQ up more than 0.5% on the session.
- **Bull:Bear gate** — more than 3.0:1 bull:bear names across the full
  700-name universe.
- **VIX delta gate** — dealer positioning on VIX negative (bearish on vol =
  bullish for equities).

P2P Track 1 (mechanical) can run at 2/3 gates on strong individual setups.
The B Continuation bucket requires 3/3 before any entries.

Daily HYG and sector-ETF positioning checks run as a credit/rotation overlay:
HYG going bear while equities stay bullish is a known divergence — new
entries get smaller sizing (0.5×), not a shutdown.

## B Continuation bucket

A second track for names already in confirmed uptrends pulling back into or
breaking above a GEX level. Strong Minervini scores (≥ 100), clean staircase
structure, dealer positioning supporting continuation. Same stop framework as
P2P; entry is at trend continuation rather than the initial pTrans break.
Full 3/3 regime gate required.

## What makes it work

Three things: the grade filter removes structurally weak setups before they
start; the db_change filter catches names where dealer positioning is
*actively shifting*, not just currently bullish; and the mechanical stop
framework removes discretion from the most emotional decision in trading —
when to exit a loser.

Validated edge from the first two weeks:

- db_change ≥ 0.50 on entry → 100% win rate on closed trades.
- Spike-crash pattern → 0% win rate.

That's the core of the system in two data points.

## Notes on the implementation

- All thresholds are named module constants (`entry.py`, `exits.py`,
  `regime.py`) so recalibration is a one-line change with the tests as a
  safety net.
- "High db_change" for the 1.0% cushion exception is codified as
  `HIGH_DB_CHANGE = 1.00` — the spec says "high" without a number; adjust the
  constant if the desk uses a different bar.
- The stall stop (stop 4) fires before the day-7 time stop on any position
  flat for three sessions — by design, per "regardless of day count."
- Run the suite: `python -m pytest tests/`.
