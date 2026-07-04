# Macro-times liquidity playbook (ICT macros), regime-gated

Time-based liquidity trading: the delivery algorithm seeks liquidity (or
rebalances an imbalance) during fixed 20-30 min windows ("macros"). Trade
only inside the windows; do nothing between them.

## NY-session macro schedule (ET)
| Window | Name | Notes |
|---|---|---|
| 09:50-10:10 | NY AM macro | order flow peak after the open; NQ's best |
| 10:50-11:10 | NY AM macro 2 | brackets our 11:00 regime read |
| 11:50-12:10 | lunch macro | thin tape; smallest size or skip |
| 13:10-13:40 | NY PM macro | |
| 15:15-15:45 | final-hour macro | MOC flows; on TREND days = the push to extremes |

## The play (same every window)
1. **Before the window**: mark the nearest UNTAPPED liquidity pool above and
   below current price (session H/L, overnight H/L, prior-day H/L - all on
   the levels.py sheet). The nearest obvious pool is the "draw."
2. **Direction**: trade TOWARD the draw, aligned with the regime read:
   - TREND day (11:00 read): only take macros in the trend direction;
     the 15:15 macro is the trend-day closer.
   - CHOP day: the draw is the range edge; expect sweep-and-reverse there -
     take the trip TO the pool, and optionally the reversal AFTER a 5-min
     close back inside (the old sweep+reclaim rule).
   - Before 10:30 (no read yet - the 09:50 macro): trade only if one side's
     pool is clearly closer/untapped; half size.
3. **Entry**: at macro open, on the first 1-5 min pullback in the draw's
   direction. No pullback and no clear draw = skip the window.
4. **Stop**: beyond the pre-macro consolidation extreme (the last 15-min
   swing against the draw).
5. **Exit**: AT the liquidity pool - the pool IS the target. Hard time-stop
   at window end (+5 min): if the algo didn't reach, the idea is wrong.
6. Risk fixed fraction per window; max 2 windows traded per day.

## Status
Time-window claims are NOT yet validated on our data (needs 1-5 min history;
IBKR caps at ~3 days of 5-min). Validation plan: log 5-min bars daily,
measure (a) range/velocity inside vs outside windows, (b) P(nearest pool
tapped | window) vs random 20-min windows, conditioned on regime. The regime
gate itself is validated (see trend_regime_study.md).
