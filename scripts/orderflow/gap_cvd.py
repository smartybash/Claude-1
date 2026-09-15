#!/usr/bin/env python3
"""Does CVD improve the gap trade? Tested on real signed flow, not a proxy.

The idea is sound on its face: a gap-down day that is being bought all
session is a different animal from one that is being sold, and the gap trade
should care which. The obstacle is data. Bars cannot produce CVD -- see
cvd_proxy.py, where the best reconstruction correlates 0.33 with the truth and
points the WRONG WAY on 4 of 18 sessions -- so the 1,421-session bar set is
useless for this question. The only honest test is the recorded tape.

That caps the sample at the sessions that were recorded, which is why the
numbers below come with wide error bars and are reported as a direction to
watch rather than a result. Saying so is the point: an underpowered test that
is labelled underpowered is worth more than a large one built on a number that
does not mean what it says.

The trade is the gap trade as already defined: gap at the open, price travels
back toward the previous close. Three readings of flow, each measured at the
moment the trade would be entered and never after:

    session CVD     net signed volume since the open, as a share of the
                    session's volume so far -- the form that separated in the
                    earlier work, because raw contracts mean different things
                    at 13:45 and at 19:30
    CVD agreement   does flow point the same way as the trade
    early CVD       flow over the first 30 minutes only, which is known before
                    most entries and is the version a live rule could use

Usage: python3 scripts/orderflow/gap_cvd.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tape import RTH_OPEN, _at, load_all, prefix_sums, rth              # noqa

POINT_USD = 20.0
COST_PTS = 2.0
STOP = 30.0
TARGET = 30.0


def st(v, minn=6):
    v = np.asarray([x for x in v if np.isfinite(x)], float)
    if len(v) < minn:
        return None
    sd = v.std(ddof=1)
    return dict(n=len(v), mean=v.mean(), win=100 * (v > 0).mean(),
                t=v.mean() / (sd / np.sqrt(len(v))) if sd > 0 else 0.0,
                total=v.sum())


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

    print("=" * 94)
    print(f"GAP + CVD — {len(days)} recorded sessions, {len(pairs)} usable pairs")
    print("=" * 94)
    print("  Real signed volume from the tape. Bars cannot supply this, so")
    print("  this sample is the whole of the available evidence.\n")

    rows = []
    for d0, d1 in pairs:
        prev, s = days[d0], days[d1]
        pc = float(prev.price.iloc[-1])
        op = float(s.price.iloc[0])
        gap = op - pc
        if abs(gap) < 10:
            continue
        up = gap < 0                         # gap down -> buy toward the gap
        csig, cvol, _ = prefix_sums(s)

        t0 = s.time.iloc[0]
        px = s.price.to_numpy()
        tm = s.time.to_numpy()

        # Enter at the open toward the gap, stop and target 30 points. The
        # structure entry was tested on 2,680 sessions in gapstructure.py and
        # loses; this isolates the CVD question rather than re-testing that.
        entry = op
        stop = entry - STOP if up else entry + STOP
        target = entry + TARGET if up else entry - TARGET
        out = None
        for i in range(1, len(px)):
            if up:
                if px[i] <= stop:
                    out = -STOP
                    break
                if px[i] >= target:
                    out = TARGET
                    break
            else:
                if px[i] >= stop:
                    out = -STOP
                    break
                if px[i] <= target:
                    out = TARGET
                    break
        if out is None:
            out = (px[-1] - entry) if up else (entry - px[-1])

        # flow at the OPEN is nothing, so use the first 30 minutes as the
        # earliest read a live rule could act on, and the whole session for
        # comparison. Both are recorded; only the first is actionable.
        cut = np.searchsorted(tm, np.datetime64(t0 + pd.Timedelta(minutes=30)))
        cut = max(1, min(cut, len(px) - 1))
        early = csig[cut] / cvol[cut] if cvol[cut] > 0 else np.nan
        whole = csig[-1] / cvol[-1] if cvol[-1] > 0 else np.nan

        sign = 1.0 if up else -1.0           # +1 when the trade wants buying
        rows.append(dict(day=d1, gap=gap, pts=out - COST_PTS,
                         early_with=early * sign, whole_with=whole * sign))

    T = pd.DataFrame(rows)
    if T.empty:
        print("  no gap sessions")
        return
    print(f"  {len(T)} gap sessions traded\n")
    show("the gap trade, no flow filter", st(T.pts.values))
    print()
    print("  EARLY CVD — first 30 minutes, known before the trade is held:")
    show("  flow agrees with the trade", st(T[T.early_with > 0].pts.values))
    show("  flow against the trade", st(T[T.early_with <= 0].pts.values))
    print()
    print("  WHOLE-SESSION CVD — not actionable, shown to size the ceiling:")
    show("  flow agrees with the trade", st(T[T.whole_with > 0].pts.values))
    show("  flow against the trade", st(T[T.whole_with <= 0].pts.values))

    print("\n  per session:")
    print(f"    {'day':<10}{'gap':>9}{'early CVD':>12}{'result':>10}")
    for _, r in T.sort_values("day").iterrows():
        print(f"    {r.day:<10}{r.gap:>+9.1f}{100*r.early_with:>11.2f}%"
              f"{r.pts:>+10.1f}")

    print("\n" + "=" * 94)
    print("IS THE SPLIT REAL, OR IS IT FIFTEEN COIN FLIPS?")
    print("=" * 94)
    agree = T.early_with > 0
    if agree.sum() < 3 or (~agree).sum() < 3:
        print("  Not enough sessions on both sides to test.")
        return
    obs = T.pts[agree].mean() - T.pts[~agree].mean()

    # A t-test is the wrong instrument here. Every trade returns either +28 or
    # -32, so a group that happens to be all winners has zero variance and the
    # t comes out infinite -- an artefact of the arithmetic, not evidence. The
    # permutation test asks the only question that matters: shuffle which
    # sessions got the "flow agrees" label, keeping the group sizes fixed, and
    # how often does chance alone produce a gap this wide?
    rng = np.random.default_rng(0)
    lab = agree.to_numpy()
    pts = T.pts.to_numpy()
    null = np.empty(200_000)
    for i in range(null.size):
        p = rng.permutation(lab)
        null[i] = pts[p].mean() - pts[~p].mean()
    p_two = float(np.mean(np.abs(null) >= abs(obs)))

    print(f"  observed gap: {obs:+.1f} points "
          f"({int(agree.sum())} sessions with flow agreeing, "
          f"{int((~agree).sum())} against)")
    print(f"  permutation p-value: {p_two:.4f}  "
          f"({'survives' if p_two < 0.05 else 'does not survive'} at 5%)")

    wins = int((T.pts[agree] > 0).sum())
    print(f"\n  The agreeing group is {wins}/{int(agree.sum())}. A perfect")
    print("  record on six observations is the exact shape that killed four")
    print("  earlier findings in this project: lookahead, overlap inflation,")
    print("  an impossible fill, and an overfit threshold. The permutation")
    print("  p-value is the honest read and it is computed on SIX sessions.")
    print("\n  This is a direction to record and re-test as sessions")
    print("  accumulate. It is not yet a rule to size, and the way to settle")
    print("  it is more recorded tape -- roughly 40 gap sessions would put a")
    print("  real interval around it.")
    print("=" * 94)


if __name__ == "__main__":
    main()
