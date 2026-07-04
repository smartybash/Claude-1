# Liquidity-trap playbook (Marco Trades style), regime-gated

Core idea (Marco Trades / @marcotrades): stops pile up under obvious lows and
above obvious highs. Price returns to run those stops, trapping traders who
entered at the level; the trade is taking the OTHER side of the trap.
No time windows, no jargon - levels, sweeps, traps.

## What counts as a level
A high/low that was RESPECTED: price touched it, moved firmly away, and left
it intact. Those are where stops rest. On our sheet: prior-day high/low,
overnight high/low, plus intraday swing highs/lows that caused clear moves
away. Ignore levels price chopped through repeatedly - no stops left there.

## BUY setup (SELL is the mirror image)
1. Find a respected low that price moved away from (liquidity resting below).
2. WAIT for price to come back and trade BELOW that low. Never buy above it,
   never buy in anticipation - the sweep must happen first.
3. Confirmation = the trap forms: price stalls below the level (false
   reaction / small internal structure shift), sellers who chased get stuck.
4. Buy (market) below the low once the trap is confirmed.
5. Stop-loss: below the low that just got taken (the sweep extreme). Always
   covered by the last low - never inside the trap zone.
6. Target: resting liquidity at respected highs (the opposite pool). First
   scale at the nearest one; runner to the far side of the range.
7. Keep it simple - don't over-refine entries (his rule, verbatim).

## Our regime gate on top (this is the part that's ours, and tested)
The trap trade is a sweep-fade. Our 306-session test of sweep-fades at
prior-day highs/lows:
  - CHOP-read days:   +0.041 ATR/trade, 58% win  <- trade the playbook
  - NEUTRAL days:     -0.068 ATR/trade           <- skip
  - TREND days:        ~0, unstable              <- do NOT fade sweeps in the
    trend direction; the "sweep" is the trend refueling (see 2026-07-02 NQ:
    morning low swept, then -170 more points).
So: run the 10:30/11:00 regime read first. Trap setups are ON for chop days,
counter-trend traps are OFF on trend days. Before 10:30, half size.

## Daily flow
levels.py sheet pre-open -> mark respected highs/lows -> 10:30/11:00 regime
read -> stalk returns into levels -> sweep, trap, enter, stop beyond the
sweep, target the opposite pool, flat by 15:59, fixed-fraction risk.

## Backtest results (scripts/backtest_marco.py)

Mechanized literally and tested on pooled QQQ+SPY 30-min (152 sessions) and
15-min (75 sessions) with respected-level and gap-through filters, 0.02 ATR
costs, conservative fills:

- RAW playbook, all trades: no edge. Best cell +0.01 ATR/trade; most negative.
- "Zone" entry (literal buy-below-the-low limit): -0.03 to -0.08 ATR/trade in
  every configuration. Without Marco's discretionary trap-reading, a resting
  limit under a swept level is catching knives - you become the liquidity.
- "Trap" entry (wait for a bar CLOSE back inside the level): better everywhere.
- Nearest-pool target (prior close) beats far targets (opposite extreme drops
  win rate to ~28%).
- The gate is what creates the edge: trap entry + prior-close target, entered
  after the 11:00 regime read, non-trend days: +0.04 to +0.07 ATR/trade
  (chop-only: +0.06 to +0.22, n small). Consistent in sign with the earlier
  independent 306-session hourly test (+0.041 on chop days, n=38).

## Implementable version (the only one the data supports)
1. Levels: prior-day H/L (and overnight H/L on futures), only if respected
   (prior close >= 0.15 ATR away) and not consumed by an opening gap.
2. After 11:00, on CHOP/NEUTRAL read only (never against a TREND read).
3. Sweep happens -> wait for a 15/30-min CLOSE back inside the level.
4. Enter market at that close. Stop beyond the sweep extreme + buffer.
   If the sweep ran deeper than 0.45 ATR past the level, no trade.
5. Target the NEAREST pool (prior close first). Flat by 15:59.
Expect ~1-2 trades/week/instrument, avg +0.04-0.06 ATR (~30-45 NQ pts),
~45-55% win. Small samples: run it as a logged forward test first.
