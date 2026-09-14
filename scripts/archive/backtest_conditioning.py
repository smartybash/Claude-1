"""The conditioning test: same trade, different regime call.

Template on every session: at 11:00 trade in the direction of the first-90-min
move (market entry, 0.30-ATR stop, exit MOC). Group results by the filter's
call. If the filter earns its keep, the identical trade should be at least
breakeven on TREND calls and clearly negative on CHOP calls.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backtest_trend import build_sessions, simulate

pd.set_option("display.width", 200)


def call_of(s) -> str:
    rng = s["fh_hi"] - s["fh_lo"]
    r = rng / s["atr"]
    pos = (s["p_dec"] - s["fh_lo"]) / rng if rng > 0 else 0.5
    if r < 0.35 or (s["er"] < 0.40 and 0.20 < pos < 0.80):
        return "CHOP"
    if r >= 0.55 and (pos >= 0.75 or pos <= 0.25):
        return "TREND"
    return "NEUTRAL"


def main():
    sessions = build_sessions("qqq") + build_sessions("spy")
    rows = []
    for s in sessions:
        d = 1 if s["p_dec"] >= s["open"] else -1  # first-90-min direction
        p = simulate(s, d, "mkt", "atr")
        if p is None:
            continue
        rows.append({"call": call_of(s), "pnl": p, "date": s["date"]})
    df = pd.DataFrame(rows)

    print("Same trade (11:00 mkt entry w/ first-90-min direction, 0.30-ATR stop, MOC exit):\n")
    g = df.groupby("call")["pnl"]
    rep = pd.DataFrame({
        "n": g.size(), "win%": g.apply(lambda x: (x > 0).mean()).round(3),
        "avg_ATR": g.mean().round(4), "med_ATR": g.median().round(4),
        "total_ATR": g.sum().round(2),
    }).reindex(["CHOP", "NEUTRAL", "TREND"])
    print(rep.to_string())
    print(f"\nALL sessions: n={len(df)} avg={df['pnl'].mean():+.4f} ATR")

    # stability: split halves
    df = df.sort_values("date")
    mid = df["date"].iloc[len(df) // 2]
    for name, part in [("first half", df[df["date"] < mid]), ("second half", df[df["date"] >= mid])]:
        gg = part.groupby("call")["pnl"].agg(["size", "mean"]).round(4)
        print(f"\n{name}:")
        print(gg.to_string())


if __name__ == "__main__":
    main()
