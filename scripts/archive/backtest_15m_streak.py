#!/usr/bin/env python3
"""15-MINUTE STREAK — confirming the one intraday cell that moved.

The intraday sweep put the daily mechanism on a day-trading clock and only one
bar size responded. On 15-minute bars, buying after k consecutive down bars and
exiting one bar later gave +1.47bp at k=3 (t=+2.18), +2.77bp at k=4 (t=+2.67)
and +4.64bp at k=5 (t=+3.15) against a control of +0.04bp -- the same monotonic
dose-response in streak depth that the 27-year daily study showed. 5-minute and
1-minute were flat, 30-minute too sparse to read.

That was 251 sessions of 1-minute data. This rebuilds 15-minute bars from the
5-minute set instead, which covers 523 sessions, and asks the questions that
decide whether it is tradeable:

  * does it hold on twice the sample, and in both date halves
  * costs -- the raw edge is single-digit NQ points and a round trip on NQ is
    one to two, so every number is also shown net of an assumed cost
  * time of day, since the 5-minute version was negative all morning
  * the short side after up-streaks, for symmetry

Usage: python3 scripts/backtest_15m_streak.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import backtest_tos_fvg as F

NQ_REF = 29400.0
COST_BP = 0.7          # ~2 NQ points round trip at 29,400


def stat(a, cost=0.0):
    a = np.asarray([x for x in a if np.isfinite(x)], float) - cost
    if len(a) < 10:
        return f"n={len(a):5d}  --"
    sd = a.std(ddof=1)
    t = a.mean() / (sd / np.sqrt(len(a))) if sd > 0 else 0.0
    return (f"n={len(a):5d}  {a.mean():+6.2f}bp  win {100*(a>0).mean():3.0f}%  "
            f"t={t:+5.2f}  {a.mean()/1e4*NQ_REF:+6.1f}NQpt")


def sessions15():
    s5 = F.load_sessions()
    out = {}
    for d, b in s5.items():
        r = b.resample("15min").agg({"open": "first", "high": "max", "low": "min",
                                     "close": "last", "volume": "sum"}).dropna()
        if len(r) >= 20:
            out[d] = r
    return out


def runs(c):
    n = len(c)
    d = np.diff(c)
    run = np.zeros(n)
    for i in range(1, n):
        s = 1 if d[i - 1] > 0 else (-1 if d[i - 1] < 0 else 0)
        run[i] = run[i - 1] + s if (run[i - 1] > 0) == (s > 0) and s != 0 else s
    return run


def collect(sess, k, hold, side=-1):
    rows = []
    for d, b in sess.items():
        c = b.close.values
        idx = b.index
        n = len(c)
        if n < k + hold + 2:
            continue
        run = runs(c)
        for i in range(k, n - hold):
            hit = (run[i] <= -k) if side < 0 else (run[i] >= k)
            if not hit:
                continue
            f = (c[i + hold] / c[i] - 1) * 1e4
            rows.append(dict(day=d, hhmm=idx[i].strftime("%H:%M"),
                             r=(f if side < 0 else -f)))
    return pd.DataFrame(rows)


def ctl(sess, hold):
    out = []
    for _, b in sess.items():
        c = b.close.values
        if len(c) > hold + 1:
            out.extend(((c[hold:] / c[:-hold] - 1) * 1e4).tolist())
    return np.array(out)


def main():
    sess = sessions15()
    days = sorted(sess)
    nd = len(days)
    print(f"QQQ 15-minute bars built from the 5-minute set — {nd} sessions, "
          f"{days[0].date()} to {days[-1].date()}")
    print(f"assumed round-trip cost {COST_BP}bp "
          f"(~{COST_BP/1e4*NQ_REF:.1f} NQ points)\n")

    print("=" * 98)
    print("1  GROSS, AND NET OF COST")
    print("=" * 98)
    for hold in (1, 2, 3):
        print(f"  --- exit {hold} bar(s) later --- "
              f"control {stat(ctl(sess, hold))}")
        for k in (3, 4, 5, 6):
            T = collect(sess, k, hold)
            if not len(T):
                continue
            print(f"    k={k} gross  {stat(T.r.values)}")
            print(f"    k={k} net    {stat(T.r.values, COST_BP)}   "
                  f"{len(T)/nd:.2f} trades/day")
        print()

    print("=" * 98)
    print("2  OUT OF SAMPLE  (k=4, exit 1 bar later)")
    print("=" * 98)
    T = collect(sess, 4, 1)
    mid = days[len(days) // 2]
    print(f"  first half  to {mid.date()}   gross {stat(T[T.day < mid].r.values)}")
    print(f"  second half from {mid.date()}  gross {stat(T[T.day >= mid].r.values)}")
    print(f"  first half   net  {stat(T[T.day < mid].r.values, COST_BP)}")
    print(f"  second half  net  {stat(T[T.day >= mid].r.values, COST_BP)}")

    print("\n" + "=" * 98)
    print("3  BY TIME OF DAY  (k=4, exit 1 bar later, net of cost)")
    print("=" * 98)
    T["hr"] = T.hhmm.str.slice(0, 2).astype(int)
    for lo, hi, lbl in ((9, 11, "09:30-10:59"), (11, 12, "11:00-11:59"),
                        (12, 14, "12:00-13:59"), (14, 15, "14:00-14:59"),
                        (15, 17, "15:00-15:59")):
        g = T[(T.hr >= lo) & (T.hr < hi)]
        print(f"  {lbl:14s} {stat(g.r.values, COST_BP)}")

    print("\n" + "=" * 98)
    print("4  DOSE-RESPONSE, BOTH SIDES  (exit 1 bar, net of cost)")
    print("=" * 98)
    for k in (3, 4, 5, 6):
        dn = collect(sess, k, 1, -1)
        up = collect(sess, k, 1, +1)
        print(f"  k={k}  buy after down  {stat(dn.r.values, COST_BP)}")
        print(f"  {'':5s} sell after up   {stat(up.r.values, COST_BP)}")


if __name__ == "__main__":
    main()
