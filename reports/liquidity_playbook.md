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
