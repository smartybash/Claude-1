"""Time-of-day breakdown for the FVG continuation trade on EXPANSION days.
Is the first ~2 hours (9:30-11:30 ET) the best window? Reuses the exit engine.

Bar index i maps to session time: RTH bars are contiguous 5-min from 9:30, so
entry time = 9:30 + 5*i minutes. i<12 = first hour, i<24 = first 2 hours.
"""

from __future__ import annotations

import pandas as pd

from backtest_fvg_exits import entries, exit_R
from backtest_vwap_fvg_v2 import earnings_reaction_days


def label(i):
    m = i * 5
    return f"{9 + (30 + m)//60:02d}:{(30 + m) % 60:02d}"


def main():
    ents = entries()
    er = earnings_reaction_days(sorted({e[0] for e in ents}))
    buckets = [("09:30-10:30 (hr1)", 0, 12),
               ("10:30-11:30 (hr2)", 12, 24),
               ("09:30-11:30 (first 2h)", 0, 24),
               ("11:30-13:30 (midday)", 24, 48),
               ("13:30-16:00 (pm)", 48, 999)]
    for rule in ("half@1", "vwapCross", "fixed2R"):
        rows = []
        for (day, s, i, entry, stop, risk, net, h, l, c, vwap, n) in ents:
            exp = (net is not None and net < 0) or (day in er)
            if not exp:
                continue
            rows.append((i, exit_R(rule, s, i, entry, stop, risk, h, l, c, vwap, n)))
        df = pd.DataFrame(rows, columns=["i", "R"])
        print(f"===== {rule}  (EXPANSION days only, n={len(df)}) =====")
        for name, lo, hi in buckets:
            sub = df[(df["i"] >= lo) & (df["i"] < hi)]
            if len(sub):
                print(f"  {name:24s} n={len(sub):3d}  win {(sub['R']>0).mean():.0%}  "
                      f"mean {sub['R'].mean():+.3f}R  total {sub['R'].sum():+.0f}R")
        print()
    print("read: if the first-2h buckets carry clearly higher mean R (and the pm bucket "
          "is weak/negative), restricting entries to 9:30-11:30 sharpens the edge.")


if __name__ == "__main__":
    main()
