"""Round 2: structural variants on the R*=0.55 / POS*=0.75 trend signal.

Questions:
  1. Do stops destroy the edge (stopped-then-reverse) or protect it?
  2. Does a SHALLOW pullback entry (0.15/0.30 ATR below the 11:00 print)
     beat chasing, where the deep OR-edge pullback failed?
  3. Long vs short asymmetry?
  4. Does exiting earlier (14:00) beat holding to the close?
"""

import sys
from datetime import time as dtime
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backtest_trend import build_sessions, signal, COST_ATR

pd.set_option("display.width", 220)

R_MIN, POS_MIN = 0.55, 0.75


def simulate2(s, d, entry_mode, stop_atr, exit_time):
    a = s["atr"]
    rest = s["rest"]

    if entry_mode == "mkt":
        entry, active = s["p_dec"], rest
    else:  # shallow limit pullback: pb15 / pb30 = 0.15 / 0.30 ATR from the print
        depth = {"pb15": 0.15, "pb30": 0.30}[entry_mode] * a
        limit = s["p_dec"] - d * depth
        fill = None
        for ts, b in rest.iterrows():
            if ts.time() >= dtime(15, 0):
                break
            if (d > 0 and b["low"] <= limit) or (d < 0 and b["high"] >= limit):
                fill = ts
                break
        if fill is None:
            return None
        entry, active = limit, rest.loc[fill:]

    stop = entry - d * stop_atr * a if stop_atr else None

    for ts, b in active.iterrows():
        if exit_time and ts.time() >= exit_time:
            return d * (float(b["open"]) - entry) / a - COST_ATR
        if stop is not None:
            if (d > 0 and b["low"] <= stop) or (d < 0 and b["high"] >= stop):
                return -stop_atr - COST_ATR
    return d * (float(rest["close"].iloc[-1]) - entry) / a - COST_ATR


def report(sessions, label):
    print(f"\n================ {label}")
    rows = []
    for em in ["mkt", "pb15", "pb30"]:
        for st in [0.30, 0.50, None]:
            for xt, xn in [(None, "close"), (dtime(14, 0), "14:00")]:
                pnl, pnl_l, pnl_s = [], [], []
                for s in sessions:
                    d = signal(s, R_MIN, POS_MIN)
                    if d == 0:
                        continue
                    p = simulate2(s, d, em, st, xt)
                    if p is None:
                        continue
                    pnl.append(p)
                    (pnl_l if d > 0 else pnl_s).append(p)
                pnl = np.array(pnl)
                rows.append({
                    "entry": em, "stop": st or "none", "exit": xn,
                    "n": len(pnl), "win%": (pnl > 0).mean().round(3),
                    "avg": pnl.mean().round(4), "total": pnl.sum().round(2),
                    "avg_long": np.mean(pnl_l).round(4) if pnl_l else np.nan,
                    "n_long": len(pnl_l),
                    "avg_short": np.mean(pnl_s).round(4) if pnl_s else np.nan,
                    "n_short": len(pnl_s),
                })
    print(pd.DataFrame(rows).sort_values("avg", ascending=False).to_string(index=False))


def main():
    sessions = build_sessions("qqq") + build_sessions("spy")
    sessions.sort(key=lambda s: s["date"])
    mid = sessions[len(sessions) // 2]["date"]
    report([s for s in sessions if s["date"] < mid], f"TRAIN (to {mid.date()})")
    report([s for s in sessions if s["date"] >= mid], f"TEST (from {mid.date()})")
    report(sessions, "FULL")


if __name__ == "__main__":
    main()
