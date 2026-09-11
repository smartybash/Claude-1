#!/usr/bin/env python3
"""A+ stop sensitivity — how much room the trade actually needs.

The validated convention is a stop 0.25% beyond the level. On QQQ that reads as
a rounding error; on NQ at 29,400 it is ~73 points per contract, which decides
position size and account minimum. So the question is not academic: does the
edge survive a tighter stop, or is the width doing the work?

Sweeps the stop from 0.10% to 0.50% on the surviving spec (both sides, all
eight fixed levels, no open-location condition, no IB filter, target prior-day
POC, first rejection after 10:00), with and without the trigger-bar delta
filter that v3 found was the best of the flow filters.

Reports each stop in QQQ terms and translated to NQ points at 29,400, plus the
R:R the trade actually takes, so the choice can be made on risk-per-contract
rather than on percentage.

Usage: python3 scripts/backtest_aplus_stop.py
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
import backtest_aplus2 as A2
from backtest_aplus import summ, COMPOSITE_N
from backtest_aplus3 import collect, ALL8

NQ_REF = 29400.0     # for translating a % stop into NQ points


def main():
    sess = F.load_sessions()
    days = sorted(sess)
    nd = len(days) - COMPOSITE_N - 1

    print(f"QQQ 5-min RTH — {len(days)} sessions, {days[0].date()} to {days[-1].date()}")
    print("spec: both sides · all 8 fixed levels · no open condition · no IB filter")
    print(f"stop translated to NQ points at {NQ_REF:.0f}\n")

    for bd, tag in ((0.0, "no flow filter"), (0.10, "trigger-bar delta >=10% vs poke")):
        print(f"--- {tag} ---", flush=True)
        print(f"{'stop':>7s} {'NQ pts':>7s}  {'':52s} {'meanRR':>7s}  freq", flush=True)
        for pct in (0.0010, 0.0015, 0.0020, 0.0025, 0.0035, 0.0050):
            A2.STOP_PCT = pct
            T = collect(sess, days, ALL8, dict(flow=False, bar_delta=bd))
            s = summ(T.r) if len(T) else "n=0"
            rr = f"{T.rr.mean():.2f}" if len(T) else "-"
            print(f"{pct*100:6.2f}% {pct*NQ_REF:7.0f}  {s:52s} {rr:>7s}  "
                  f"{len(T)/nd*5:.1f}/wk", flush=True)
        print(flush=True)

    # Drawdown and streak at the two candidate stops, since sizing follows from it.
    print("--- risk profile at candidate stops (bar-delta filter on) ---", flush=True)
    for pct in (0.0015, 0.0025):
        A2.STOP_PCT = pct
        T = collect(sess, days, ALL8, dict(flow=False, bar_delta=0.10))
        r = T.r.values
        eq = np.cumsum(r)
        dd = (np.maximum.accumulate(eq) - eq).max()
        import itertools
        streak = max((len(list(g)) for k, g in itertools.groupby(r < 0) if k), default=0)
        print(f"  stop {pct*100:.2f}% ({pct*NQ_REF:.0f} NQ pts)  "
              f"median {np.median(r):+.2f}R  max DD {dd:.1f}R  "
              f"worst streak {streak}  best {r.max():+.1f}R", flush=True)


if __name__ == "__main__":
    main()
