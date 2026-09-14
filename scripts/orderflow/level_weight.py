#!/usr/bin/env python3
"""THE WEIGHT RULE — pre-registered, with fixed parameters, for out-of-sample test.

A level is not one kind of object. The volume that traded at it in the previous
cash session says which kind, and tick data gives that number exactly where bar
data never could.

    heavy level   price was ACCEPTED there. It trades back through.
    light level   price was REJECTED there. It holds.

Measured on eight session pairs, fading only the light levels and leaving the
heavy ones alone:

    stop = target = 20   +3.42 pt, 63.5% win, n=137, t=+2.09, 6/8 sessions up
    stop = target = 30   +7.16 pt, 66.3% win, n=92,  t=+2.43, 7/8 sessions up

and fading a HEAVY level is actively bad: -13.25 pt at 31% on a 30-point stop.

That is the strongest result this project has produced, and it still does not
clear the bar. t across sessions is +1.92. The volume cutoff was a tercile of
the very data it was measured on. Perhaps ten cells were examined to find it.
Every one of those is a reason the number could be flattering itself, and this
project has killed four findings that looked at least this good.

So the parameters are FROZEN HERE, in absolute terms rather than as quantiles
of whatever data happens to be loaded, and every session recorded from now on
is a genuine out-of-sample test rather than another chance to fit.

    HEAVY_THRESHOLD  10,000 contracts within +/- 2.0 points, previous RTH
    STOP = TARGET    30 points
    ENTRY            the price that actually printed on the touch
    TOUCH            within 0.25 points of the level
    RE-ARM           price must move 8 points away before the level re-arms
    LEVELS           previous session high, low, close, VAH, POC, VAL,
                     merged when within 5 points of each other
    COST             2.0 points per round trip

Run it as sessions arrive. `--oos 20260821` splits at a date so the frozen
in-sample result and the out-of-sample one are reported separately.

Usage: python3 scripts/orderflow/level_weight.py [--oos YYYYMMDD]
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from levels import ib_levels, resolve, session_levels                   # noqa
from levels_audit import merge_levels                                   # noqa
from sweep2 import level_volume, touches, trade                         # noqa
from tape import load_all, rth                                          # noqa

# ---- frozen parameters. Do not tune these on new data. ----------------------
HEAVY_THRESHOLD = 10_000.0
BAND_PTS = 2.0
STOP = 30.0
TARGET = 30.0
COST_PTS = 2.0
POINT_USD = 20.0
# -----------------------------------------------------------------------------


def build(days, pairs) -> pd.DataFrame:
    rows = []
    for prev_d, d in pairs:
        cur = days[d]
        p = cur.price.to_numpy()
        lv = merge_levels(session_levels(days[prev_d]))
        inr = {k: v for k, v in lv.items() if p.min() <= v <= p.max()}
        for t in touches(cur, inr):
            rows.append(dict(day=d, **t,
                             lvl_vol=level_volume(days[prev_d], t["price"],
                                                  BAND_PTS)))
    T = pd.DataFrame(rows)
    T["light"] = T.lvl_vol < HEAVY_THRESHOLD
    return T


def report(days, T, label):
    if T.empty:
        print(f"  {label}: no touches")
        return
    v = trade(days, T, STOP, TARGET, True, T.light.values)
    h = trade(days, T, STOP, TARGET, True, (~T.light).values)
    print(f"\n  ── {label} " + "─" * (66 - len(label)))
    for tag, x in (("fade LIGHT levels  (the rule)", v),
                   ("fade heavy levels  (avoid)  ", h)):
        x = np.asarray(x, float) - COST_PTS
        if len(x) < 3:
            print(f"     {tag}  too few")
            continue
        sd = x.std(ddof=1)
        t = x.mean() / (sd / np.sqrt(len(x))) if sd > 0 and len(x) > 1 else 0.0
        print(f"     {tag}  n={len(x):<4} {x.mean():+7.2f}pt "
              f"{x.mean()*POINT_USD:+8.0f}$  win {100*(x>0).mean():4.1f}%  "
              f"t={t:+5.2f}")

    print("     per session:")
    means = []
    for d in sorted(T.day.unique()):
        x = trade(days, T, STOP, TARGET, True, (T.light & (T.day == d)).values)
        if len(x) < 3:
            continue
        m = float(np.mean(x)) - COST_PTS
        means.append(m)
        print(f"       {d}  n={len(x):<3} {m:+7.2f}pt {m*POINT_USD:+8.0f}$")
    if len(means) > 1:
        a = np.array(means)
        t = a.mean() / (a.std(ddof=1) / np.sqrt(len(a)))
        print(f"       {int((a > 0).sum())}/{len(a)} sessions positive   "
              f"mean {a.mean():+.2f}pt   t across sessions {t:+.2f}")


def main():
    oos = None
    if "--oos" in sys.argv:
        oos = sys.argv[sys.argv.index("--oos") + 1]

    full = load_all()
    days = {d: rth(f) for d, f in sorted(full.items())}
    days = {d: s for d, s in days.items() if len(s) > 5000}
    keys = sorted(days)
    pairs = [(a, b) for a, b in zip(keys, keys[1:])
             if len(pd.bdate_range(a, b)) == 2]

    print("=" * 88)
    print("THE WEIGHT RULE — frozen parameters")
    print("=" * 88)
    print(f"  fade a prior-session level only if fewer than "
          f"{HEAVY_THRESHOLD:,.0f} contracts")
    print(f"  traded within {BAND_PTS} points of it yesterday.")
    print(f"  stop {STOP:.0f} / target {TARGET:.0f} / cost {COST_PTS} pts / "
          f"entry at the printed price")
    print(f"\n  {len(pairs)} session pairs available")

    T = build(days, pairs)
    print(f"  {len(T)} touches, {T.light.sum()} light / "
          f"{(~T.light).sum()} heavy")

    if oos:
        report(days, T[T.day < oos], f"IN SAMPLE (before {oos})")
        report(days, T[T.day >= oos], f"OUT OF SAMPLE (from {oos})")
    else:
        report(days, T, "all sessions")


if __name__ == "__main__":
    main()
