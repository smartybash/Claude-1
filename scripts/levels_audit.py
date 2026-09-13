#!/usr/bin/env python3
"""AUDIT of the level-fade result before it is allowed to mean anything.

The raw run reported +6.56 points at t=+3.13 on a 20-point stop and a 40-point
target. Four things could be manufacturing that, and every one of them has
manufactured a result in this project already:

  1  CLUSTERED LEVELS. On 09-04 pdHIGH sat at 29,584.25 and pdVAH at 29,583.75.
     Half a point apart. Every touch of one is a touch of the other, so 22 and
     23 "independent" observations are the same 22 trades entered twice. Levels
     within a few points are merged into one before anything is counted.

  2  OVERLAPPING TRADES. A 40-point target on NQ can take an hour to resolve.
     Touches minutes apart produce trades that live through the same move and
     are not independent draws.

  3  SELECTION. Six stop/target pairs were tried and the best one reported.
     With six tries the bar is not |t| >= 2.

  4  UNRESOLVED TRADES. A touch late in the session cannot reach a 40-point
     target before the close, and the fallback exits at the last price. If most
     of the profit comes from trades that never hit a barrier, the result is an
     artefact of that convention rather than of the levels.

Usage: python3 scripts/levels_audit.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from levels import (COST_PTS, POINT_USD, REARM_PTS, TOUCH_TOL, features,
                    ib_levels, resolve, session_levels, stat)          # noqa
from tape import load_all, rth                                          # noqa

MERGE_PTS = 5.0        # levels closer than this are one level


def merge_levels(lv: dict) -> dict:
    """Collapse levels that sit within MERGE_PTS into a single named cluster."""
    items = sorted(lv.items(), key=lambda kv: kv[1])
    out, group = {}, [items[0]]
    for name, v in items[1:]:
        if v - group[-1][1] <= MERGE_PTS:
            group.append((name, v))
        else:
            out["+".join(n for n, _ in group)] = float(
                np.mean([x for _, x in group]))
            group = [(name, v)]
    out["+".join(n for n, _ in group)] = float(np.mean([x for _, x in group]))
    return out


def touches_merged(cur, levels, ib_from):
    t = cur.time.to_numpy()
    p = cur.price.to_numpy()
    out = []
    for name, lv in levels.items():
        armed, start = True, 0
        if "IB" in name and ib_from is not None:
            start = int(np.searchsorted(t, np.datetime64(ib_from)))
            if start >= len(p):
                continue
        above = p[start] > lv
        for i in range(start, len(p)):
            if armed and abs(p[i] - lv) <= TOUCH_TOL:
                out.append(dict(idx=i, level=name, price=lv,
                                from_above=above))
                armed = False
            elif not armed and abs(p[i] - lv) >= REARM_PTS:
                armed, above = True, p[i] > lv
    out.sort(key=lambda r: r["idx"])
    return out


def show(lbl, r, bar=3.0):
    if r is None:
        print(f"    {lbl:<40} too few")
        return
    star = " **" if abs(r["t"]) >= bar else ""
    print(f"    {lbl:<40} n={r['n']:<4} {r['mean']:+6.2f}pt "
          f"{r['mean']*POINT_USD:+8.0f}$  win {r['win']:3.0f}%  "
          f"t={r['t']:+5.2f}{star}")


def main():
    days = {d: rth(df) for d, df in sorted(load_all().items())}
    days = {d: s for d, s in days.items() if len(s) > 5000}
    keys = sorted(days)

    print("=" * 92)
    print("LEVEL AUDIT")
    print("=" * 92)

    print(f"\n1  MERGING LEVELS WITHIN {MERGE_PTS} POINTS")
    allrows = []
    for prev_d, d in zip(keys, keys[1:]):
        cur = days[d]
        lv = session_levels(days[prev_d])
        ibl, ib_end = ib_levels(cur)
        lv.update(ibl)
        merged = merge_levels(lv)
        p = cur.price.to_numpy()
        inr = {k: v for k, v in merged.items() if p.min() <= v <= p.max()}
        print(f"   {d}: {len(lv)} raw -> {len(merged)} merged, "
              f"{len(inr)} in range")
        for n, v in merged.items():
            if "+" in n:
                print(f"       {v:>10,.2f}  {n}")
        for tch in touches_merged(cur, inr, ib_end):
            f = features(cur, tch["idx"], tch["price"])
            if f is None:
                continue
            allrows.append(dict(day=d, **tch, **f))

    T = pd.DataFrame(allrows).reset_index(drop=True)
    print(f"\n   touches after merging: {len(T)}")

    # ---------------------------------------------------------------- resolve
    STOP, TARGET = 20.0, 40.0
    pnl, exit_i, at_close = [], [], []
    for _, r in T.iterrows():
        p = days[r.day].price.to_numpy()
        direction = +1 if r.from_above else -1
        v, j = resolve(p, int(r.idx), r.price, direction, STOP, TARGET)
        pnl.append(v)
        exit_i.append(j)
        at_close.append(j >= len(p) - 1)
    T["pnl"], T["exit_i"], T["at_close"] = pnl, exit_i, at_close

    print(f"\n2  UNRESOLVED TRADES (exited at the close, no barrier hit)")
    print(f"   {T.at_close.sum()} of {len(T)} "
          f"({100*T.at_close.mean():.0f}%)")
    show("all touches", stat(T.pnl.values, COST_PTS))
    show("barrier-resolved only", stat(T.loc[~T.at_close, "pnl"].values,
                                       COST_PTS))
    show("close-resolved only", stat(T.loc[T.at_close, "pnl"].values,
                                     COST_PTS))

    # ------------------------------------------------------------ de-overlap
    print(f"\n3  ONE TRADE AT A TIME (no new entry while one is open)")
    keep, busy_until, cur_day = [], -1, None
    for i, r in T.iterrows():
        if r.day != cur_day:
            cur_day, busy_until = r.day, -1
        if r.idx < busy_until:
            continue
        keep.append(i)
        busy_until = r.exit_i
    D = T.loc[keep]
    print(f"   {len(T)} touches -> {len(D)} non-overlapping trades")
    show("de-overlapped", stat(D.pnl.values, COST_PTS))
    for day, g in D.groupby("day"):
        show(f"   {day}", stat(g.pnl.values, COST_PTS), bar=99)

    # ------------------------------------------------------------- selection
    print(f"\n4  THE FULL STOP/TARGET GRID, DE-OVERLAPPED")
    print("   Six cells were tried, so the honest bar is |t| >= 2.9, and a")
    print("   result that only exists in one cell is a fitted parameter.\n")
    for stop, target in ((10, 10), (15, 15), (20, 20), (15, 30),
                         (20, 40), (30, 30)):
        vals, busy, cd = [], -1, None
        for _, r in T.iterrows():
            if r.day != cd:
                cd, busy = r.day, -1
            if r.idx < busy:
                continue
            p = days[r.day].price.to_numpy()
            direction = +1 if r.from_above else -1
            v, j = resolve(p, int(r.idx), r.price, direction, stop, target)
            vals.append(v)
            busy = j
        show(f"stop {stop} / target {target}", stat(vals, COST_PTS), bar=2.9)

    # ----------------------------------------------------------------- flow
    print(f"\n5  FLOW AT THE TOUCH, ON THE DE-OVERLAPPED SET")
    print("   Positive aggression = pressure INTO the level, which should")
    print("   break it. If the fade only works when aggression is weak, that")
    print("   is a usable filter rather than a curve fit.\n")
    D = D.copy()
    D["appr_delta"] = np.where(D.from_above, -D.delta, D.delta)
    for feat, lbl in (("appr_delta", "aggression into level"),
                      ("vol", "volume, last 60s"),
                      ("trades_per_s", "tape speed")):
        try:
            q = pd.qcut(D[feat], 3, labels=False, duplicates="drop")
        except ValueError:
            continue
        print(f"   {lbl}")
        for i, tag in enumerate(("low", "mid", "high")):
            show(f"      {tag}", stat(D.loc[q == i, "pnl"].values, COST_PTS),
                 bar=2.9)


if __name__ == "__main__":
    main()
