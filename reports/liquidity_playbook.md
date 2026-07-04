# Liquidity playbook (sweep + reclaim), regime-gated

Levels that hold resting liquidity (printed daily by `scripts/levels.py`):
overnight high/low, prior-day high/low.

1. **Sweep** — price wicks through the level. Never enter in anticipation.
2. **Reclaim** — a 5-min close back inside. No reclaim = liquidity run, no fade.
3. **Regime gate** — fade sweeps only on CHOP-read days (10:30 veto / 11:00 read).
   Never fade a sweep in the trend direction on TREND days. Skip NEUTRAL.

Trade: enter at reclaim close; stop beyond the sweep wick + buffer; target the
opposite liquidity pool (other side of ON range, prior close first scale);
flat at 15:59; fixed-fraction risk sizing.

Evidence (this repo, 306 pooled QQQ/SPY sessions, 136 sweep events of the
prior-day H/L, hold-to-close): unconditioned fade -0.021 ATR/trade;
CHOP-day fades +0.041 ATR (58% win, n=38); NEUTRAL -0.068; TREND ~0 and
unstable. Thin sample - treat as directional support for the regime gate,
not a standalone edge. Live illustration 2026-07-02: ES swept the overnight
high and round-tripped (fade worked, day read CHOP); NQ swept its morning low
on a TREND_DOWN day and kept running (fade would have failed).
