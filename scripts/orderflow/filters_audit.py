#!/usr/bin/env python3
"""Audit the two filters that moved, before they go anywhere near the chart.

Session CVD and five-minute delta both showed a spread worth noticing. So did
four earlier findings in this project that turned out to be nothing. The same
three questions decide it:

  1  does the filter survive PER SESSION, or is it one day again
  2  is the effect monotonic across terciles, or a single odd bucket
  3  how many cells were examined to find it -- four features times three
     buckets is twelve, so the bar is not |t| >= 2

Usage: python3 scripts/orderflow/filters_audit.py
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from level_weight import COST_PTS, STOP, TARGET, build
from sweep2 import trade
from tape import load_all, rth
POINT_USD = 20.0

def main():
    full = load_all()
    days = {d: rth(f) for d, f in sorted(full.items())}
    days = {d: s for d, s in days.items() if len(s) > 5000}
    keys = sorted(days)
    pairs = [(a,b) for a,b in zip(keys,keys[1:]) if len(pd.bdate_range(a,b))==2]
    T = build(days, pairs).reset_index(drop=True)
    T = T[T.light].reset_index(drop=True)

    cvd, local = [], []
    for _, r in T.iterrows():
        s = days[r.day]; i = int(r.idx); past = s.iloc[:i]
        if len(past) < 200:
            cvd.append(np.nan); local.append(np.nan); continue
        cvd.append(float(past.signed.sum()))
        t0 = s.time.iloc[i] - pd.Timedelta(minutes=5)
        local.append(float(past[past.time >= t0].signed.sum()))
    sign = np.where(T.from_above, 1.0, -1.0)
    T["cvd_against"] = -np.array(cvd) * sign     # high = day trending against the fade
    T["absorb"] = -np.array(local) * sign        # high = aggression INTO the level

    def st(v, minn=10):
        v = np.asarray(v, float); v = v[np.isfinite(v)]
        if len(v) < minn: return None
        v = v - COST_PTS; sd = v.std(ddof=1)
        return dict(n=len(v), mean=v.mean(), win=100*(v>0).mean(),
                    t=v.mean()/(sd/np.sqrt(len(v))) if sd>0 else 0.0)
    def show(l, r):
        if r is None: print(f"    {l:<42} too few"); return
        print(f"    {l:<42} n={r['n']:<4} {r['mean']:+7.2f}pt win {r['win']:4.1f}%  t={r['t']:+5.2f}")

    base = trade(days, T, STOP, TARGET, True, np.ones(len(T), bool))
    print("="*88); print("AUDIT OF THE TWO FILTERS THAT MOVED"); print("="*88)
    show("no filter", st(base))

    # the proposed rule: skip when the day trends hard against the fade
    cvd_cut = T.cvd_against.quantile(2/3)
    keep = (T.cvd_against < cvd_cut).values
    print(f"\n  A  SKIP when session CVD is in the top third against the fade")
    print(f"     (cut at {cvd_cut:,.0f} contracts)")
    show("filtered", st(trade(days, T, STOP, TARGET, True, keep)))
    show("the trades it removes", st(trade(days, T, STOP, TARGET, True, ~keep)))

    print("\n     per session:")
    pos = tot = 0
    for d in sorted(T.day.unique()):
        v = trade(days, T, STOP, TARGET, True, (keep & (T.day==d).values))
        if len(v) < 3: continue
        m = float(np.mean(v)) - COST_PTS; tot += 1; pos += m > 0
        print(f"       {d}  n={len(v):<3} {m:+7.2f}pt")
    print(f"       {pos}/{tot} sessions positive")

    print("\n  B  MONOTONIC?  mean by tercile, both features")
    for col, lbl in (("cvd_against","session CVD against the fade"),
                     ("absorb","aggression into the level, 5 min")):
        q = pd.qcut(T[col].rank(method="first"), 3, labels=False)
        row = []
        for i in range(3):
            r = st(trade(days, T, STOP, TARGET, True, (q==i).values))
            row.append(f"{r['mean']:+6.2f}" if r else "  --  ")
        print(f"     {lbl:<36} {' -> '.join(row)}")

    print("\n  C  BOTH FILTERS TOGETHER")
    both = keep & (T.absorb > T.absorb.quantile(1/3)).values
    show("skip trending days AND require absorption", st(trade(days,T,STOP,TARGET,True,both)))
    print(f"     keeps {both.sum()} of {len(T)} trades "
          f"({100*both.sum()/len(T):.0f}%), {both.sum()/tot if tot else 0:.1f} a session")
