#!/usr/bin/env python3
"""LEVEL TOUCHES — do fixed levels hold, and does order flow say which will?

The last test the current recording configuration supports, and the one the
whole project started with. Two questions, in order:

  1  when price reaches a level that was fixed before the session started,
     does fading it pay?
  2  if not on average, does the order flow AT the touch separate the holds
     from the breaks? That is the actual claim being made every time someone
     reads a footprint at a level.

Levels are the prior session's profile -- high, low, close, VAH, POC, VAL --
computed from actual traded volume at price, plus the current session's initial
balance once it is complete at 14:30. Every one of them is known before price
arrives. Nothing here is fitted to the day it trades.

The lookahead controls matter more here than anywhere else in this project,
because the earlier level studies were destroyed by exactly one mistake:
entering at the level price while conditioning on a bar that had already closed
back through it. Here the entry is a resting limit order at the level, filled
the moment price trades there, and the outcome is resolved by walking the tick
tape forward one trade at a time until a barrier is hit. Every feature is
computed from trades strictly before the fill.

Usage: python3 scripts/levels.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from tape import load_all, rth, volume_profile          # noqa: E402

TICK = 0.25
POINT_USD = 20.0
COST_PTS = 2.0
TOUCH_TOL = 1.0        # a touch is price trading within this of the level
REARM_PTS = 8.0        # price must leave by this before the level re-arms
IB_END = "14:30"


def session_levels(prev: pd.DataFrame) -> dict:
    p = volume_profile(prev)
    return {"pdHIGH": prev.price.max(), "pdLOW": prev.price.min(),
            "pdCLOSE": float(prev.price.iloc[-1]),
            "pdVAH": p["vah"], "pdPOC": p["poc"], "pdVAL": p["val"]}


def ib_levels(cur: pd.DataFrame) -> tuple[dict, pd.Timestamp]:
    end = cur.time.iloc[0].normalize() + pd.Timedelta(hours=14, minutes=30)
    ib = cur[cur.time < end]
    if len(ib) < 100:
        return {}, end
    return {"IBH": ib.price.max(), "IBL": ib.price.min()}, end


def find_touches(cur: pd.DataFrame, levels: dict, ib_from=None):
    """Every arming touch of every level, with the side price approached from.

    A level re-arms only after price has moved REARM_PTS away, so a single
    grind through a level is one observation rather than two hundred.
    """
    t = cur.time.to_numpy()
    p = cur.price.to_numpy()
    out = []
    for name, lv in levels.items():
        armed = True
        start = 0
        if name.startswith("IB") and ib_from is not None:
            start = int(np.searchsorted(t, np.datetime64(ib_from)))
            if start >= len(p):
                continue
        # Direction of approach is set by where price sat when the level armed.
        above = p[start] > lv
        for i in range(start, len(p)):
            if armed and abs(p[i] - lv) <= TOUCH_TOL:
                out.append(dict(idx=i, level=name, price=lv,
                                from_above=above, time=t[i]))
                armed = False
            elif not armed and abs(p[i] - lv) >= REARM_PTS:
                armed = True
                above = p[i] > lv
    out.sort(key=lambda r: r["idx"])
    return out


def resolve(p: np.ndarray, i: int, entry: float, direction: int,
            stop: float, target: float):
    """Walk the tape forward from the fill until a barrier is hit.

    direction is +1 for a long (fade of a level approached from above), -1 for
    a short. Returns points, and None if neither barrier is reached by the
    close, which is treated as an exit at the last price.
    """
    tp = entry + direction * target
    sl = entry - direction * stop
    for j in range(i + 1, len(p)):
        if direction > 0:
            if p[j] <= sl:
                return -stop, j
            if p[j] >= tp:
                return target, j
        else:
            if p[j] >= sl:
                return -stop, j
            if p[j] <= tp:
                return target, j
    return direction * (p[-1] - entry), len(p) - 1


def features(cur: pd.DataFrame, i: int, lv: float, look_s: int = 60):
    """Flow in the window before the fill. Strictly backward looking."""
    t = cur.time.to_numpy()
    t0 = t[i] - np.timedelta64(look_s, "s")
    a = int(np.searchsorted(t, t0))
    if i - a < 20:
        return None
    w = cur.iloc[a:i]
    dt = (t[i] - t[a]) / np.timedelta64(1, "s")
    return dict(
        delta=float(w.signed.sum()),
        vol=float(w.volume.sum()),
        speed=float(abs(w.price.iloc[-1] - w.price.iloc[0]) / max(dt, 1) * 60),
        trades_per_s=len(w) / max(dt, 1),
    )


def stat(x, cost=0.0):
    x = np.asarray([v for v in x if np.isfinite(v)], float)
    if len(x) < 8:
        return None
    x = x - cost
    sd = x.std(ddof=1)
    return dict(n=len(x), mean=x.mean(), win=100 * (x > 0).mean(),
                t=x.mean() / (sd / np.sqrt(len(x))) if sd > 0 else 0.0)


def show(lbl, r):
    if r is None:
        print(f"    {lbl:<34} too few")
        return
    star = " **" if abs(r["t"]) >= 3.0 else ""
    print(f"    {lbl:<34} n={r['n']:<4} {r['mean']:+6.2f}pt "
          f"{r['mean']*POINT_USD:+8.0f}$  win {r['win']:3.0f}%  "
          f"t={r['t']:+5.2f}{star}")


def main():
    days = {d: rth(df) for d, df in sorted(load_all().items())}
    days = {d: s for d, s in days.items() if len(s) > 5000}
    keys = sorted(days)

    print("=" * 88)
    print("LEVEL TOUCHES — prior-session profile plus initial balance")
    print(f"tolerance {TOUCH_TOL} pt, re-arm {REARM_PTS} pt, "
          f"cost {COST_PTS} pt")
    print("=" * 88)

    rows = []
    for prev_d, d in zip(keys, keys[1:]):
        cur = days[d]
        lv = session_levels(days[prev_d])
        ibl, ib_end = ib_levels(cur)
        lv.update(ibl)
        touches = find_touches(cur, lv, ib_end)
        p = cur.price.to_numpy()

        print(f"\n  {d}  (levels from {prev_d})   "
              f"session {p.min():,.2f} to {p.max():,.2f}")
        for name, v in lv.items():
            hit = sum(1 for x in touches if x["level"] == name)
            reach = "in range" if p.min() <= v <= p.max() else "not reached"
            print(f"     {name:<8} {v:>10,.2f}   {reach:<12} "
                  f"{hit} arming touch(es)")

        for tch in touches:
            f = features(cur, tch["idx"], tch["price"])
            if f is None:
                continue
            rows.append(dict(day=d, **{k: tch[k] for k in
                                       ("level", "price", "from_above")},
                             idx=tch["idx"], **f))

    T = pd.DataFrame(rows)
    if T.empty:
        print("\n  no touches with enough preceding tape")
        return

    print("\n" + "=" * 88)
    print(f"2  FADING EVERY TOUCH — {len(T)} touches over {len(keys)-1} sessions")
    print("=" * 88)
    print("  Entry is a resting limit at the level, filled when price trades")
    print("  there. Direction fades the approach: short a level reached from")
    print("  below, long one reached from above.\n")

    grid = [(10, 10), (15, 15), (20, 20), (15, 30), (20, 40), (30, 30)]
    best = None
    for stop, target in grid:
        pnl = []
        for _, r in T.iterrows():
            p = days[r.day].price.to_numpy()
            direction = +1 if r.from_above else -1
            v, _ = resolve(p, int(r.idx), r.price, direction, stop, target)
            pnl.append(v)
        T[f"pnl_{stop}_{target}"] = pnl
        s = stat(pnl, COST_PTS)
        show(f"stop {stop} / target {target}", s)
        if s and (best is None or s["t"] > best[1]["t"]):
            best = ((stop, target), s)

    if best is None:
        return
    (bs, bt), _ = best
    col = f"pnl_{bs}_{bt}"

    print("\n" + "=" * 88)
    print(f"3  BY LEVEL AND BY DAY  (stop {bs} / target {bt})")
    print("=" * 88)
    for name, g in T.groupby("level"):
        show(f"{name}", stat(g[col].values, COST_PTS))
    print()
    for day, g in T.groupby("day"):
        show(f"{day}", stat(g[col].values, COST_PTS))

    print("\n" + "=" * 88)
    print("4  DOES THE FLOW AT THE TOUCH SEPARATE HOLDS FROM BREAKS?")
    print("=" * 88)
    print("  The claim under test: reading order flow at the level tells you")
    print("  which touches to take. Signed so a positive delta means aggression")
    print("  in the direction of the approach -- into the level.\n")

    T["appr_delta"] = np.where(T.from_above, -T.delta, T.delta)
    for feat, lbl in (("appr_delta", "aggression into the level"),
                      ("vol", "volume in the last 60s"),
                      ("speed", "approach speed, pts/min"),
                      ("trades_per_s", "tape speed, trades/s")):
        try:
            q = pd.qcut(T[feat], 4, labels=False, duplicates="drop")
        except ValueError:
            continue
        cells = [stat(T.loc[q == i, col].values, COST_PTS) for i in range(4)]
        line = "  ".join(
            f"{c['mean']:+6.2f}({c['n']:>2})" if c else "   --   "
            for c in cells)
        print(f"    {lbl:<28} {line}")
    print(f"    {'':<28} " + "  ".join(f"{'Q'+str(i+1):>10}" for i in range(4)))

    print("\n" + "=" * 88)
    print("5  HOLD RATE — how often the level held at all")
    print("=" * 88)
    for name, g in T.groupby("level"):
        w = (g[col] > 0).mean()
        print(f"    {name:<8} {len(g):>3} touches   held {100*w:3.0f}%")
    print(f"    {'ALL':<8} {len(T):>3} touches   held "
          f"{100*(T[col] > 0).mean():3.0f}%")


if __name__ == "__main__":
    main()
