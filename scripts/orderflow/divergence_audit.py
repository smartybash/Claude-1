#!/usr/bin/env python3
"""AUDIT of the one cell that cleared the bar: CVD divergence at 60m extremes.

The sweep reported +8.3 pts at 74% on n=78 with t=+5.12. That number cannot be
taken at face value, and this script exists to attack it three ways before it is
allowed anywhere near a trading decision.

  1  OVERLAP. Consecutive 30-second windows at a new 60-minute high all fire.
     Their forward windows overlap almost completely, so they are not 78
     independent observations, they are a handful of episodes counted many
     times. t-statistics assume independence and will be inflated by roughly
     the square root of the duplication factor. Fixed by taking one trade per
     episode and refusing re-entry until the hold has expired.

  2  CONCENTRATION. Two sessions is two draws. If one afternoon's slide
     supplies most of the profit, there is no edge, there is one move.

  3  THE CONTROL, which is the one that matters. H0 already showed this tape
     mean-reverts at every horizon tested. If shorting a 60-minute high pays
     the same with the CVD condition removed, then CVD contributed nothing and
     the finding is plain mean reversion wearing an order-flow costume.

Usage: python3 scripts/divergence_audit.py
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from tape import load_all, rth

POINT_USD = 20.0
COST_PTS = 2.0
LOOK_M = 60
HOLD_S = 300


def windows(s, secs=30):
    g = s.set_index("time").resample(f"{secs}s")
    w = pd.DataFrame({"vol": g.volume.sum(), "delta": g.signed.sum(),
                      "last": g.price.last(), "n": g.price.count()})
    w = w.dropna(subset=["last"])
    w = w[w.n > 0].copy()
    w["cvd"] = w.delta.cumsum()
    return w


def signals(w, use_cvd: bool):
    """Short at a new local high, long at a new local low.

    With use_cvd the extreme must be unconfirmed by cumulative delta; without
    it, every extreme qualifies. Both use rolling windows that end at the
    current bar, so nothing from the future enters the condition.
    """
    L = LOOK_M * 2
    hi = w["last"] >= w["last"].rolling(L).max()
    lo = w["last"] <= w["last"].rolling(L).min()
    if use_cvd:
        hi &= w["cvd"] < w["cvd"].rolling(L).max()
        lo &= w["cvd"] > w["cvd"].rolling(L).min()
    return hi, lo


def trades(w, use_cvd, dedupe):
    """Signal rows as (index, direction). dedupe enforces no overlapping holds."""
    hi, lo = signals(w, use_cvd)
    k = HOLD_S // 30
    out, block_until = [], -1
    for i in range(len(w)):
        if i + k >= len(w):
            break
        if dedupe and i < block_until:
            continue
        if hi.iloc[i]:
            out.append((i, -1))
        elif lo.iloc[i]:
            out.append((i, +1))
        else:
            continue
        block_until = i + k
    return out, k


def pnl(w, tr, k):
    p = w["last"].to_numpy()
    return np.array([d * (p[i + k] - p[i]) for i, d in tr], float)


def stat(x, cost=COST_PTS):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) < 5:
        return None
    x = x - cost
    sd = x.std(ddof=1)
    return dict(n=len(x), mean=x.mean(), win=100 * (x > 0).mean(),
                t=x.mean() / (sd / np.sqrt(len(x))) if sd > 0 else 0.0,
                total=x.sum())


def show(lbl, r):
    if r is None:
        print(f"  {lbl:<44} too few trades")
        return
    print(f"  {lbl:<44} n={r['n']:<4} {r['mean']:+6.2f}pt  "
          f"win {r['win']:3.0f}%  t={r['t']:+5.2f}  "
          f"total {r['total']*POINT_USD:+8.0f}$")


def main():
    days = {d: rth(df) for d, df in sorted(load_all().items())}
    days = {d: s for d, s in days.items() if len(s) > 5000}
    W = {d: windows(s) for d, s in days.items()}

    print("=" * 88)
    print(f"AUDIT — {LOOK_M}m extreme, {HOLD_S//60}m hold, cost {COST_PTS}pt")
    print("=" * 88)

    print("\n1  OVERLAP: how many independent episodes are behind n=78?")
    for d, w in W.items():
        hi, lo = signals(w, True)
        fires = (hi | lo)
        # an episode is a run of consecutive firing windows
        runs = (fires & ~fires.shift(1, fill_value=False)).sum()
        print(f"  {d}  {int(fires.sum())} firing windows in "
              f"{int(runs)} separate episodes "
              f"({fires.sum()/max(runs,1):.1f} windows per episode)")

    print("\n2  THE SAME TEST, ONE TRADE PER EPISODE")
    for tag, dedupe in (("every firing window (as swept)", False),
                        ("no overlapping holds", True)):
        allp, per_day = [], {}
        for d, w in W.items():
            tr, k = trades(w, True, dedupe)
            v = pnl(w, tr, k)
            per_day[d] = stat(v)
            allp.append(v)
        print(f"\n  --- {tag} ---")
        for d, r in per_day.items():
            show(f"{d}", r)
        show("pooled", stat(np.concatenate(allp)))

    print("\n3  CONTROL: is the CVD condition doing any work?")
    print("   Same trades with the divergence requirement removed, so every")
    print("   local extreme is taken. If this matches, CVD added nothing.\n")
    for use_cvd, tag in ((True, "extreme + CVD divergence"),
                         (False, "extreme alone, no CVD")):
        allp, per_day = [], {}
        for d, w in W.items():
            tr, k = trades(w, use_cvd, True)
            v = pnl(w, tr, k)
            per_day[d] = stat(v)
            allp.append(v)
        show(tag + "  [pooled]", stat(np.concatenate(allp)))
        for d, r in per_day.items():
            show(f"    {d}", r)

    print("\n4  CONCENTRATION: does one move carry it?")
    allv = []
    for d, w in W.items():
        tr, k = trades(w, True, True)
        v = pnl(w, tr, k) - COST_PTS
        allv.append(v)
    v = np.concatenate(allv)
    v_sorted = np.sort(v)[::-1]
    if len(v):
        print(f"  {len(v)} de-overlapped trades, total "
              f"{v.sum()*POINT_USD:+,.0f}$")
        print(f"  best single trade {v_sorted[0]*POINT_USD:+,.0f}$ "
              f"= {100*v_sorted[0]/v.sum() if v.sum() else float('nan'):.0f}% "
              f"of all profit")
        top3 = v_sorted[:3].sum()
        print(f"  best three        {top3*POINT_USD:+,.0f}$ "
              f"= {100*top3/v.sum() if v.sum() else float('nan'):.0f}% of it")
        print(f"  median trade      {np.median(v)*POINT_USD:+,.0f}$")
        print(f"  without the best trade: "
              f"{np.mean(v_sorted[1:]):+.2f}pt over {len(v)-1} trades")


if __name__ == "__main__":
    main()
