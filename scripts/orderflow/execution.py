#!/usr/bin/env python3
"""Can this actually be executed, or does it only work on paper?

Every number so far assumed a fill at the printed price the instant price
touched the level, a target that fills the moment price kisses it, and a stop
that fills exactly where it sits. None of those are free. This measures what
each assumption is worth, because an edge of seven points can be entirely
consumed by execution and still look perfect in a backtest.

Four things get tested, from most to least favourable:

  1  TIMING. The level is known before the session opens, so the entry is a
     resting limit rather than a reaction -- no human speed is needed for it.
     That claim is checked by measuring how long trades last and how far apart
     they arrive. If the average trade resolves in ninety seconds, it is a
     scalp and a person cannot run it; if it takes half an hour, they can.

  2  QUEUE. A resting limit at a level only fills if enough volume trades
     there. Price touching the level and reversing leaves the order unfilled --
     and those are exactly the good outcomes, so assuming a fill on every touch
     captures winners that would never have been entered. Tested by requiring
     price to trade N ticks THROUGH the level before the entry counts.

  3  TARGET. Same problem on the way out: a limit at the target needs price to
     trade there, not merely reach it.

  4  STOP SLIPPAGE. A stop is a market order in a fast market. Tested by
     charging extra points on every loss.

Usage: python3 scripts/orderflow/execution.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from level_weight import COST_PTS, STOP, TARGET, build                  # noqa
from tape import load_all, rth                                          # noqa

TICK = 0.25
POINT_USD = 20.0


def resolve_exec(p, t, i, level, direction, stop, target,
                 entry_through=0.0, target_through=0.0, stop_slip=0.0,
                 delay_s=0.0):
    """One trade under explicit execution assumptions.

    entry_through   ticks price must trade beyond the level before the resting
                    limit is considered filled. 0 reproduces the old optimistic
                    fill on any touch.
    target_through  same for the profit target.
    stop_slip       points added to every loss.
    delay_s         seconds to wait before entering at market instead, which is
                    what reacting to a chart looks like.
    Returns (points, exit_index) or None if the order never filled.
    """
    n = len(p)
    if delay_s > 0:
        j = int(np.searchsorted(t, t[i] + np.timedelta64(int(delay_s), "s")))
        if j >= n:
            return None
        entry = p[j]
        start = j
    else:
        need = level - direction * entry_through * TICK
        start = None
        for j in range(i, min(i + 20000, n)):
            if (direction > 0 and p[j] <= need) or \
               (direction < 0 and p[j] >= need):
                start = j
                break
            # give up once price has run a stop's distance away unfilled
            if abs(p[j] - level) > stop:
                return None
        if start is None:
            return None
        entry = level

    tp = entry + direction * target
    sl = entry - direction * stop
    tp_need = tp + direction * target_through * TICK

    for j in range(start + 1, n):
        if direction > 0:
            if p[j] <= sl:
                return -stop - stop_slip, j
            if p[j] >= tp_need:
                return target, j
        else:
            if p[j] >= sl:
                return -stop - stop_slip, j
            if p[j] <= tp_need:
                return target, j
    return direction * (p[-1] - entry), n - 1


def run(days, T, **kw):
    out, busy, cd = [], -1, None
    for _, r in T[T.light].iterrows():
        if r.day != cd:
            cd, busy = r.day, -1
        if r.idx < busy:
            continue
        s = days[r.day]
        p = s.price.to_numpy()
        t = s.time.to_numpy()
        d = +1 if r.from_above else -1
        res = resolve_exec(p, t, int(r.idx), r.price, d, STOP, TARGET, **kw)
        if res is None:
            continue
        v, j = res
        out.append((v, int(r.idx), j, r.day))
        busy = j
    return out


def summarise(lbl, trades, cost=COST_PTS):
    if len(trades) < 10:
        print(f"  {lbl:<46} too few ({len(trades)})")
        return None
    v = np.array([x[0] for x in trades], float) - cost
    sd = v.std(ddof=1)
    t = v.mean() / (sd / np.sqrt(len(v)))
    print(f"  {lbl:<46} n={len(v):<4} {v.mean():+7.2f}pt "
          f"{v.mean()*POINT_USD:+8.0f}$  win {100*(v>0).mean():4.1f}%  "
          f"t={t:+5.2f}")
    return v


def main():
    full = load_all()
    days = {d: rth(f) for d, f in sorted(full.items())}
    days = {d: s for d, s in days.items() if len(s) > 5000}
    keys = sorted(days)
    pairs = [(a, b) for a, b in zip(keys, keys[1:])
             if len(pd.bdate_range(a, b)) == 2]
    T = build(days, pairs)

    print("=" * 92)
    print("EXECUTION REALITY CHECK")
    print("=" * 92)

    base = run(days, T)
    print("\n1  IS THERE TIME TO TRADE IT?")
    hold, gap = [], []
    prev_day, prev_exit = None, None
    for v, i, j, d in base:
        s = days[d]
        hold.append((s.time.iloc[j] - s.time.iloc[i]).total_seconds() / 60)
        if d == prev_day and prev_exit is not None:
            gap.append((s.time.iloc[i] - prev_exit).total_seconds() / 60)
        prev_day, prev_exit = d, s.time.iloc[j]
    hold = np.array(hold)
    gap = np.array(gap)
    print(f"   hold time   median {np.median(hold):5.1f} min   "
          f"p25 {np.percentile(hold,25):5.1f}   p75 {np.percentile(hold,75):5.1f}"
          f"   max {hold.max():.0f}")
    print(f"   gap between trades  median {np.median(gap):5.1f} min")
    print(f"   -> {len(base)/T[T.light].day.nunique():.1f} trades a session, "
          f"one at a time")
    print("   The level is known before the open, so the entry is a resting")
    print("   limit with a bracket, not a reaction. Nothing here needs speed.")

    print("\n2  THE BASELINE, AS PREVIOUSLY REPORTED")
    summarise("fill on any touch, target on any touch", base)

    print("\n3  QUEUE POSITION — the limit only fills if price trades through")
    print("   Touches that reverse without trading through are the GOOD")
    print("   outcomes, so assuming a fill on every touch keeps winners that")
    print("   were never entered. This is the assumption most likely to be")
    print("   flattering the result.\n")
    for th in (0, 1, 2, 4):
        summarise(f"entry needs {th} tick(s) through the level",
                  run(days, T, entry_through=th))

    print("\n4  TARGET FILL AND STOP SLIPPAGE")
    for tt, ss in ((0, 0.0), (1, 0.5), (1, 1.0), (2, 2.0)):
        summarise(f"target {tt} tick through, stop slips {ss} pt",
                  run(days, T, entry_through=1, target_through=tt,
                      stop_slip=ss))

    print("\n5  REACTING INSTEAD OF RESTING — market entry N seconds late")
    for dl in (0, 5, 15, 30, 60):
        summarise(f"market entry {dl}s after the touch",
                  run(days, T, delay_s=dl))

    print("\n6  HOW MUCH TOTAL COST KILLS IT")
    tr = run(days, T, entry_through=1, target_through=1, stop_slip=1.0)
    for c in (2.0, 3.0, 4.0, 6.0, 8.0):
        summarise(f"realistic fills, total cost {c:.0f} pt", tr, cost=c)


if __name__ == "__main__":
    main()
