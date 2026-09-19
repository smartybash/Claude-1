#!/usr/bin/env python3
"""What CVD number actually blocks the trade?

"CVD is against this trade" is not a rule. A rule needs a number, and saying
the effect exists without giving the cut-off is leaving out the only part that
can be acted on.

There is a complication worth handling rather than ignoring: raw CVD is not
comparable across touches. A touch at 13:45 has twenty minutes of delta behind
it; one at 19:30 has six hours. The same -4,000 means something very different
in each. So three forms are tested and the one that separates best wins:

  raw          cumulative delta in contracts, as the platform shows it
  normalised   CVD divided by the session volume so far -- what share of
               everything traded today was net one way
  per-minute   CVD divided by minutes elapsed -- the current rate of flow

For each, the question is the same: at what value does the trade stop working,
and does that cut-off hold per session rather than only in aggregate.

Usage: python3 scripts/orderflow/cvd_threshold.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from level_weight import COST_PTS, STOP, TARGET, build                  # noqa
from sweep2 import trade                                                # noqa
from tape import RTH_OPEN, _at, load_all, rth                           # noqa

POINT_USD = 20.0


def st(v, minn=10):
    v = np.asarray([x for x in v if np.isfinite(x)], float)
    if len(v) < minn:
        return None
    v = v - COST_PTS
    sd = v.std(ddof=1)
    return dict(n=len(v), mean=v.mean(), win=100 * (v > 0).mean(),
                t=v.mean() / (sd / np.sqrt(len(v))) if sd > 0 else 0.0)


def show(lbl, r):
    if r is None:
        print(f"    {lbl:<46} too few")
        return
    print(f"    {lbl:<46} n={r['n']:<4} {r['mean']:+7.2f}pt "
          f"{r['mean']*POINT_USD:+8.0f}$  win {r['win']:4.1f}%  t={r['t']:+5.2f}")


def main():
    full = load_all()
    days = {d: rth(f) for d, f in sorted(full.items())}
    days = {d: s for d, s in days.items() if len(s) > 5000}
    keys = sorted(days)
    pairs = [(a, b) for a, b in zip(keys, keys[1:])
             if len(pd.bdate_range(a, b)) == 2]
    T = build(days, pairs).reset_index(drop=True)
    T = T[T.light].reset_index(drop=True)
    print(f"{len(days)} sessions, {len(pairs)} usable pairs, "
          f"{len(T)} light-level touches\n")

    raw, norm, rate = [], [], []
    for _, r in T.iterrows():
        s = days[r.day]
        i = int(r.idx)
        past = s.iloc[:i]
        if len(past) < 200:
            raw.append(np.nan); norm.append(np.nan); rate.append(np.nan)
            continue
        c = float(past.signed.sum())
        v = float(past.volume.sum())
        mins = max(1.0, (s.time.iloc[i] -
                         _at(s.time.iloc[0], RTH_OPEN)).total_seconds() / 60.0)
        raw.append(c)
        norm.append(c / v if v > 0 else np.nan)
        rate.append(c / mins)

    # Signed so a POSITIVE value means the day is running AGAINST the fade:
    # a buy is hurt by heavy net selling, a sell by heavy net buying.
    sign = np.where(T.from_above, 1.0, -1.0)
    T["raw"] = -np.array(raw) * sign
    T["norm"] = -np.array(norm) * sign
    T["rate"] = -np.array(rate) * sign
    T = T.dropna(subset=["raw"]).reset_index(drop=True)

    base = trade(days, T, STOP, TARGET, True, np.ones(len(T), bool))
    print("=" * 92)
    print("1  WHICH FORM OF CVD SEPARATES?")
    print("=" * 92)
    show("no filter", st(base))
    print()
    for col, lbl, unit in (("raw", "raw CVD against the fade", "contracts"),
                           ("norm", "CVD / session volume so far", "share"),
                           ("rate", "CVD per minute against the fade", "c/min")):
        q = pd.qcut(T[col].rank(method="first"), 3, labels=False)
        cuts = [T.loc[q == i, col].max() for i in range(3)]
        print(f"  --- {lbl} ---")
        for i, tag in enumerate(("least against", "middle", "MOST against")):
            r = st(trade(days, T, STOP, TARGET, True, (q == i).values))
            hi = cuts[i]
            hs = f"{hi:,.0f}" if col != "norm" else f"{hi:+.3f}"
            show(f"{tag}  (up to {hs} {unit})", r)
        print()

    print("=" * 92)
    print("2  THE ACTUAL CUT-OFF — sweep an absolute threshold")
    print("=" * 92)
    print("  Skip the trade when CVD against the fade exceeds X. This is the")
    print("  number the indicator needs; a tercile is not a rule.\n")
    for col, lbl, grid, fmt in (
        ("raw", "raw CVD", [1000, 2000, 3000, 4000, 6000, 8000, 12000], "{:,.0f}"),
        ("norm", "CVD / volume", [.005, .01, .015, .02, .03, .05], "{:+.3f}"),
        ("rate", "CVD per minute", [5, 10, 20, 30, 50, 80], "{:,.0f}"),
    ):
        print(f"  --- skip when {lbl} exceeds ---")
        for x in grid:
            keep = (T[col] < x).values
            if keep.sum() < 15:
                continue
            r = st(trade(days, T, STOP, TARGET, True, keep))
            if r is None:
                continue
            print(f"    > {fmt.format(x):>10}  keeps {keep.sum():>3}/{len(T)}"
                  f"   {r['mean']:+7.2f}pt  win {r['win']:4.1f}%  t={r['t']:+5.2f}")
        print()

    print("=" * 92)
    print("3  PER SESSION, at the best absolute cut on the normalised form")
    print("=" * 92)
    best_x, best_t = None, -9
    for x in (.005, .01, .015, .02, .03, .05):
        keep = (T.norm < x).values
        if keep.sum() < 20:
            continue
        r = st(trade(days, T, STOP, TARGET, True, keep))
        if r and r["t"] > best_t:
            best_t, best_x = r["t"], x
    if best_x is None:
        print("  nothing to test")
        return
    keep = (T.norm < best_x).values
    print(f"  cut: skip when net delta against the fade exceeds "
          f"{100*best_x:.1f}% of the session's volume so far\n")
    pos = tot = 0
    for d in sorted(T.day.unique()):
        v = trade(days, T, STOP, TARGET, True, (keep & (T.day == d).values))
        if len(v) < 3:
            continue
        m = float(np.mean(v)) - COST_PTS
        tot += 1
        pos += m > 0
        print(f"    {d}  n={len(v):<3} {m:+7.2f}pt {m*POINT_USD:+8.0f}$")
    print(f"    {pos}/{tot} sessions positive")
    show("  pooled, filtered", st(trade(days, T, STOP, TARGET, True, keep)))
    show("  pooled, unfiltered", st(base))


if __name__ == "__main__":
    main()
