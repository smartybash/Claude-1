#!/usr/bin/env python3
"""Out-of-sample test. Nothing here is allowed to be re-fitted.

The weight rule was found on nine session pairs and the 1.5% CVD cut was swept
on those same nine. 08-24, 08-25 and 08-26 arrived afterwards and give two new
pairs that neither was fitted on. Two days is not a verdict, but it is the only
honest kind of evidence left, and the rule either behaves or it does not.

Every parameter is imported frozen. The split is by date and nothing is tuned
on the far side of it.

Usage: python3 scripts/orderflow/oos.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from level_weight import COST_PTS, HEAVY_THRESHOLD, STOP, TARGET, build  # noqa
from sweep2 import trade                                                 # noqa
from tape import RTH_OPEN, _at, load_all, prefix_sums, rth                            # noqa

POINT_USD = 20.0
SKIP_SHARE = 0.015          # frozen: skip when CVD against the fade > 1.5%
# The in-sample set is the NINE TEST DAYS the rule and the CVD cut were fitted
# on, listed explicitly. A date cut-off got this wrong: 09-02, 09-03 and 09-04
# arrived early and were part of the fitting, but fall after 08-24 and were
# being reported as out-of-sample. Only 08-25 and 08-26 are genuinely new.
IN_SAMPLE_DAYS = {
    "20260811", "20260812", "20260813", "20260814",
    "20260819", "20260820",
    "20260902", "20260903", "20260904",
}


def st(v, minn=8):
    v = np.asarray([x for x in v if np.isfinite(x)], float)
    if len(v) < minn:
        return None
    v = v - COST_PTS
    sd = v.std(ddof=1)
    return dict(n=len(v), mean=v.mean(), win=100 * (v > 0).mean(),
                t=v.mean() / (sd / np.sqrt(len(v))) if sd > 0 else 0.0,
                total=v.sum())


def show(lbl, r):
    if r is None:
        print(f"    {lbl:<44} too few trades")
        return
    print(f"    {lbl:<44} n={r['n']:<4} {r['mean']:+7.2f}pt "
          f"{r['mean']*POINT_USD:+8.0f}$  win {r['win']:4.1f}%  "
          f"t={r['t']:+5.2f}   total {r['total']*POINT_USD:+,.0f}$")


def main():
    full = load_all()
    days = {d: rth(f) for d, f in sorted(full.items())}
    days = {d: s for d, s in days.items() if len(s) > 5000}
    keys = sorted(days)
    pairs = [(a, b) for a, b in zip(keys, keys[1:])
             if len(pd.bdate_range(a, b)) == 2]
    T = build(days, pairs).reset_index(drop=True)
    T = T[T.light].reset_index(drop=True)

    # CVD as a share of the session's volume so far, signed so positive means
    # the day is running AGAINST the fade.
    share = []
    for _, r in T.iterrows():
        csig, cvol, _ = prefix_sums(days[r.day])
        i = int(r.idx)
        if i < 200:
            share.append(np.nan)
            continue
        v = cvol[i]
        share.append(csig[i] / v if v > 0 else np.nan)
    sign = np.where(T.from_above, 1.0, -1.0)
    T["cvd_against"] = -np.array(share) * sign
    T = T.dropna(subset=["cvd_against"]).reset_index(drop=True)

    IS = T.day.isin(IN_SAMPLE_DAYS).values
    OOS = ~IS

    print("=" * 94)
    print("OUT-OF-SAMPLE TEST — frozen parameters, nothing re-fitted")
    print("=" * 94)
    print(f"  heavy threshold {HEAVY_THRESHOLD:,.0f} contracts   "
          f"stop = target {STOP:.0f}   CVD skip above {100*SKIP_SHARE:.1f}%")
    print(f"  in sample:      {sorted(set(T.day[IS]))}")
    print(f"  out of sample:  {sorted(set(T.day[OOS]))}")

    for tag, mask in (("IN SAMPLE", IS), ("OUT OF SAMPLE", OOS)):
        print(f"\n  ── {tag} " + "─" * (70 - len(tag)))
        if mask.sum() == 0:
            print("     nothing")
            continue
        raw = trade(days, T, STOP, TARGET, True, mask)
        show("weight rule alone", st(raw))
        keep = mask & (T.cvd_against < SKIP_SHARE).values
        show("weight rule + CVD filter", st(trade(days, T, STOP, TARGET, True, keep)))
        skipped = mask & (T.cvd_against >= SKIP_SHARE).values
        show("  what the CVD filter removed", st(
            trade(days, T, STOP, TARGET, True, skipped), minn=3))

        print("     per session:")
        for d in sorted(set(T.day[mask])):
            v = trade(days, T, STOP, TARGET, True,
                      (keep & (T.day == d).values))
            if len(v) == 0:
                continue
            m = float(np.mean(v)) - COST_PTS
            print(f"       {d}  n={len(v):<3} {m:+7.2f}pt "
                  f"{m*POINT_USD:+8.0f}$  total {(np.sum(v)-COST_PTS*len(v))*POINT_USD:+,.0f}$")

    print("\n" + "=" * 94)
    print("DOES THE CVD CUT STILL WANT TO BE 1.5% ON EVERYTHING?")
    print("=" * 94)
    print("  Re-swept over ALL sessions. If the shape has moved a lot with two")
    print("  more days, the 1.5% was fitted to noise.\n")
    for x in (0.005, 0.010, 0.015, 0.020, 0.030, 0.050, 9.9):
        keep = (T.cvd_against < x).values
        r = st(trade(days, T, STOP, TARGET, True, keep))
        if r is None:
            continue
        lbl = "no filter" if x > 1 else f"skip above {100*x:.1f}%"
        star = "  <-- frozen" if abs(x - SKIP_SHARE) < 1e-9 else ""
        print(f"    {lbl:<20} n={r['n']:<4} {r['mean']:+7.2f}pt  "
              f"win {r['win']:4.1f}%  t={r['t']:+5.2f}{star}")


if __name__ == "__main__":
    main()
