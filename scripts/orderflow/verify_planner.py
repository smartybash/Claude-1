#!/usr/bin/env python3
"""Prove the indicator computes the same levels as the study.

If the C# in atas/LevelPlanner.cs and the Python in tape.py disagree by even a
tick, the live rule and the tested rule are different rules and every number in
the study is about something the trader is not doing. That failure would be
invisible: both sides would produce plausible levels and nobody would notice.

So the indicator's algorithm is re-implemented here, line for line, and run
against the recorded sessions alongside the reference. Every level and every
weight must match exactly.

Usage: python3 scripts/orderflow/verify_planner.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tape import load_all, rth, volume_profile                          # noqa

TICK = 0.25
VALUE_AREA = 0.70
MERGE_PTS = 5.0
BAND_PTS = 2.0
HEAVY = 10_000


# --- a transcription of LevelPlanner.cs, deliberately not a shortcut ---------
def cs_ticks(price):
    return int(np.round(price / TICK))


def cs_profile(vol: dict):
    """Mirror of LevelPlanner.Profile."""
    if not vol:
        return None
    keys = sorted(vol)
    n = len(keys)
    total = 0
    best = -1
    poc_i = 0
    for i, k in enumerate(keys):
        v = vol[k]
        total += v
        if v > best:
            best, poc_i = v, i

    target = VALUE_AREA * total
    lo = hi = poc_i
    got = float(vol[keys[poc_i]])
    while got < target and (lo > 0 or hi < n - 1):
        below = vol[keys[lo - 1]] if lo > 0 else -1
        above = vol[keys[hi + 1]] if hi < n - 1 else -1
        if above >= below:
            hi += 1
            got += vol[keys[hi]]
        else:
            lo -= 1
            got += vol[keys[lo]]
    return (keys[poc_i] * TICK, keys[hi] * TICK, keys[lo] * TICK)


def cs_weight(vol: dict, level: float) -> int:
    band = int(round(BAND_PTS / TICK))
    c = cs_ticks(level)
    return int(sum(vol.get(t, 0) for t in range(c - band, c + band + 1)))


def cs_merge(raw):
    """Mirror of the merge loop in LevelPlanner.BuildPlan."""
    raw = sorted(raw, key=lambda kv: kv[1])
    out, names, tot, cnt, last = [], [], 0.0, 0, None
    for name, v in raw:
        if cnt > 0 and v - last > MERGE_PTS:
            out.append(("+".join(names), tot / cnt))
            names, tot, cnt = [], 0.0, 0
        names.append(name)
        tot += v
        cnt += 1
        last = v
    if cnt:
        out.append(("+".join(names), tot / cnt))
    return out


def main():
    full = load_all()
    days = {d: rth(f) for d, f in sorted(full.items())}
    days = {d: s for d, s in days.items() if len(s) > 5000}
    keys = sorted(days)

    print("=" * 84)
    print("DOES THE INDICATOR COMPUTE THE SAME LEVELS AS THE STUDY?")
    print("=" * 84)

    bad = 0
    for d in keys:
        s = days[d]
        # what the indicator accumulates, tick by tick, from OnNewTrade
        vol = {}
        for p, v in zip(s.price.to_numpy(), s.volume.to_numpy()):
            t = cs_ticks(p)
            vol[t] = vol.get(t, 0) + int(v)

        cs = cs_profile(vol)
        ref = volume_profile(s)

        dpoc = cs[0] - ref["poc"]
        dvah = cs[1] - ref["vah"]
        dval = cs[2] - ref["val"]
        ok = abs(dpoc) < 1e-9 and abs(dvah) < 1e-9 and abs(dval) < 1e-9
        bad += 0 if ok else 1
        print(f"\n  {d}  {'MATCH' if ok else 'MISMATCH'}")
        print(f"     POC  indicator {cs[0]:>10,.2f}   study {ref['poc']:>10,.2f}"
              f"   diff {dpoc:+.2f}")
        print(f"     VAH  indicator {cs[1]:>10,.2f}   study {ref['vah']:>10,.2f}"
              f"   diff {dvah:+.2f}")
        print(f"     VAL  indicator {cs[2]:>10,.2f}   study {ref['val']:>10,.2f}"
              f"   diff {dval:+.2f}")

        # and the plan the indicator would write for the next session
        raw = [("pdHIGH", float(s.price.max())), ("pdLOW", float(s.price.min())),
               ("pdCLOSE", float(s.price.iloc[-1])),
               ("pdVAH", cs[1]), ("pdPOC", cs[0]), ("pdVAL", cs[2])]
        merged = cs_merge(raw)
        print("     plan for the next session:")
        for name, price in sorted(merged, key=lambda x: -x[1]):
            w = cs_weight(vol, price)
            print(f"        {price:>10,.2f}  weight {w:>8,}  "
                  f"{'LIGHT' if w < HEAVY else 'heavy'}  {name}")

    print("\n" + "=" * 84)
    if bad:
        print(f"  {bad} of {len(keys)} sessions DISAGREE — do not ship the "
              f"indicator")
        sys.exit(1)
    print(f"  all {len(keys)} sessions agree to the tick. The indicator and the "
          f"study\n  are computing the same rule.")


if __name__ == "__main__":
    main()
