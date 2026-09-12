#!/usr/bin/env python3
"""A+ v3 — the surviving spec, stress-tested.

backtest_aplus2.py isolated what the first spec got wrong. What survived:

  * the LEVEL SET can be widened (all eight fixed levels stay positive)
  * the LONG side works, and is stronger than the short side
  * the open-location condition HURTS — dropping it raises t from +3.58 to +5.95
  * the wide-IB filter HURTS on the widened set (+0.438R -> +0.268R)
  * what must not change: stop = fixed % beyond the LEVEL (not the trigger
    bar's extreme), target = prior-day POC (not the next level, not developing)

This file checks whether that survives contact with the things that kill
backtests: an out-of-sample split, level-set choice, the 2nd-attempt rule, and
the flow filters.

On flow: requiring session CVD to AGREE with a fade is close to
self-contradictory — price only reached an upper level because buyers were
aggressive, so cumulative delta is positive there by construction. That filter
cut 110 trades to 24. Both directions are tested here: agree, and oppose
(the absorption reading), plus the trigger bar's own delta on its own.

Delta is a PROXY on QQQ bars — ((close-open)/(high-low)) * volume. Nothing
under a flow filter is settled until it is replayed on aggressor-tagged ticks.

Usage: python3 scripts/backtest_aplus3.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import backtest_tos_fvg as F
from backtest_aplus import build_levels, summ, COMPOSITE_N
from backtest_aplus2 import trade_at_level, UPPER, LOWER

CORE = ("pdVAH", "pdVAL", "pdHigh", "pdLow")     # the four significant levels
ALL8 = UPPER + LOWER


def collect(sess, days, levels_used, cfg, open_cond=False):
    """One trade per day: the earliest qualifying rejection across levels."""
    rows = []
    for i, d in enumerate(days):
        if i < COMPOSITE_N + 1:
            continue
        b = sess[d]
        op = float(b["open"].iloc[0])
        lv = build_levels(sess, days, i, op)
        if not lv or "pdPOC" not in lv:
            continue
        best = None
        for name in levels_used:
            if name not in lv:
                continue
            L = lv[name]
            side = -1 if name in UPPER else +1
            if open_cond and ((side < 0 and op > L) or (side > 0 and op < L)):
                continue
            t = trade_at_level(b, L, side, lv["pdPOC"], cfg)
            if t and (best is None or t["ts"] < best["ts"]):
                t.update(level=name, side=side, day=d)
                best = t
        if best:
            rows.append(best)
    return pd.DataFrame(rows)


def line(label, T, n_days):
    s = summ(T.r) if len(T) else "n=0"
    f = f"{len(T)/n_days*5:.1f}/wk" if n_days else ""
    print(f"{label:44s} {s:52s} {f}", flush=True)


def main():
    sess = F.load_sessions()
    days = sorted(sess)
    nd = len(days) - COMPOSITE_N - 1
    base = dict(flow=False, bar_delta=0.0)

    print(f"QQQ 5-min RTH — {len(days)} sessions, {days[0].date()} to {days[-1].date()}")
    print("spec: both sides · no open-location condition · no IB filter")
    print("      stop 0.25% beyond the level · target prior-day POC · "
          "first rejection after 10:00\n")

    print("LEVEL SET")
    T8 = collect(sess, days, ALL8, base)
    T4 = collect(sess, days, CORE, base)
    line("  all 8 fixed levels", T8, nd)
    line("  4 core levels (pd VAH/VAL/High/Low)", T4, nd)

    print("\nOUT OF SAMPLE — split by date, all 8 levels")
    mid = days[len(days) // 2]
    for lbl, sub in (("  first half  " + str(days[0].date()) + " to " + str(mid.date()),
                      T8[T8.day < mid]),
                     ("  second half " + str(mid.date()) + " to " + str(days[-1].date()),
                      T8[T8.day >= mid])):
        line(lbl, sub, nd / 2)

    print("\nBY SIDE / BY LEVEL (all 8)")
    for s, g in T8.groupby("side"):
        line(f"  {'short' if s < 0 else 'long'}", g, nd)
    for nm, g in T8.groupby("level"):
        line(f"    {nm}", g, nd)

    print("\nATTEMPT NUMBER (all 8)")
    line("  1st attempt at the level", T8[T8.attempt == 1], nd)
    line("  2nd or later attempt", T8[T8.attempt >= 2], nd)

    print("\nFLOW FILTERS (proxy delta — provisional)")
    line("  none", T8, nd)
    line("  session CVD agrees with trade",
         collect(sess, days, ALL8, dict(base, flow=True)), nd)
    line("  trigger-bar delta opposes poke >=10%",
         collect(sess, days, ALL8, dict(base, bar_delta=0.10)), nd)
    line("  trigger-bar delta opposes poke >=20%",
         collect(sess, days, ALL8, dict(base, bar_delta=0.20)), nd)

    print("\nRISK PROFILE (all 8, no flow filter)")
    r = T8.r.values
    print(f"  worst trade {r.min():+.2f}R   best {r.max():+.2f}R   "
          f"median {np.median(r):+.2f}R", flush=True)
    eq = np.cumsum(r)
    dd = np.maximum.accumulate(eq) - eq
    print(f"  max drawdown {dd.max():.1f}R   longest losing streak "
          f"{max((len(list(g)) for k, g in __import__('itertools').groupby(r < 0) if k), default=0)}",
          flush=True)
    print(f"  mean R:R taken {T8.rr.mean():.2f}", flush=True)


if __name__ == "__main__":
    main()
