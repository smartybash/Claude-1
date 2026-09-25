#!/usr/bin/env python3
"""THE ONE AUTHORISED HOLDOUT RUN. 2016-2020 QQQ, frozen native specification.

Run ONCE. No optimisation, no second candidate, no reinterpretation.
The specification is imported from ib_pullback_native, unchanged.

Usage: python3 scripts/orderflow/ib_pullback_holdout.py
"""
from __future__ import annotations
import sys
from math import ceil, sqrt, erf
from pathlib import Path
import numpy as np, pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ib_pullback_native as N
import ib_pullback as F

ROOT = Path(__file__).resolve().parents[2]
HOLD = ROOT / "data/intraday_long/QQQ_1m_holdout.parquet"
Phi = lambda x: 0.5 * (1 + erf(x / sqrt(2)))


def main():
    N.WIN_LO, N.WIN_HI = 2016, 2020
    SS = N.load_inst(HOLD)
    T, fn = N.collect(SS)
    months = len(pd.PeriodIndex([s["day"] for s in SS], freq="M").unique())
    qual = sum(v for k, v in fn.items() if k != "unresolved")

    R = T.R.to_numpy(float)
    n = len(R)
    w, l = R[R > 0], R[R <= 0]
    eq = np.cumsum(R)
    dd = float((np.maximum.accumulate(eq) - eq).max())
    st = mx = 0
    for x in R:
        st = st + 1 if x <= 0 else 0
        mx = max(mx, st)
    srt = np.sort(R)
    gross = w.sum()

    print("=" * 110)
    print("  HOLDOUT — 2016-2020 QQQ, FROZEN NATIVE SPECIFICATION, ONE RUN")
    print("=" * 110)
    print(f"  sessions                 {len(SS)}")
    print(f"  qualifying at 10:30      {qual}  ({100*qual/len(SS):.1f}%)")
    print(f"  reached midpoint zone    {qual - fn.get('no_zone',0) - fn.get('opp_break',0)}")
    print(f"  trades                   {n}")
    print(f"  trades per month         {n/months:.2f}")
    print()
    print(f"  win rate                 {100*len(w)/n:.1f}%")
    print(f"  average winner           {w.mean():+.3f} R")
    print(f"  average loser            {l.mean():+.3f} R")
    print(f"  EXPECTANCY               {R.mean():+.4f} R")
    print(f"  profit factor            {gross/-l.sum():.3f}")
    print(f"  max drawdown             {dd:.1f} R")
    print(f"  max losing streak        {mx}")
    print(f"  median risk              {T.risk_bps.median():.2f} bps"
          f"   ({T.risk_atr.median():.2f} x ATR1m)")
    print(f"  median cost as % of risk {T.cost_pct.median():.2f}%")
    print(f"  exit mix                 {T.why.value_counts().to_dict()}")
    print(f"  ambiguous bars           {100*T.amb.mean():.1f}%")
    print()
    L, S_ = T[T.d > 0], T[T.d < 0]
    print(f"  LONG    n {len(L):>4}   {L.R.mean():+.4f} R   PF "
          f"{(L.R[L.R>0].sum()/-L.R[L.R<=0].sum() if (L.R<=0).any() else np.inf):.2f}")
    print(f"  SHORT   n {len(S_):>4}   {S_.R.mean():+.4f} R   PF "
          f"{(S_.R[S_.R>0].sum()/-S_.R[S_.R<=0].sum() if (S_.R<=0).any() else np.inf):.2f}")
    print()
    print("  BY YEAR")
    print(f"    {'year':<6}{'n':>5}{'expR':>10}{'PF':>8}{'win%':>8}")
    for y, g in T.groupby("year"):
        gr = g.R.to_numpy()
        pw, pl = gr[gr > 0], gr[gr <= 0]
        pf = (pw.sum() / -pl.sum()) if len(pl) and pl.sum() < 0 else np.inf
        print(f"    {y:<6}{len(g):>5}{gr.mean():>+10.4f}{pf:>8.2f}"
              f"{100*len(pw)/len(gr):>8.1f}")
    print()
    b5, b10 = srt[:n-5].mean(), srt[:n-10].mean()
    c50 = (R - 0.5 * T.cost_pct.to_numpy(float) / 100.0).mean()
    print(f"  after removing best 5    {b5:+.4f} R")
    print(f"  after removing best 10   {b10:+.4f} R")
    print(f"  with 50% higher costs    {c50:+.4f} R")
    print(f"  top 5 share of gross profit   {100*srt[-5:].sum()/gross:.1f}%")
    print(f"  top 10 share of gross profit  {100*srt[-10:].sum()/gross:.1f}%")
    print()
    se = R.std(ddof=1) / sqrt(n)
    print(f"  APPENDIX: SE {se:.4f}  t {R.mean()/se:+.2f}  "
          f"p(single) {2*(1-Phi(abs(R.mean()/se))):.4f}")
    k = max(10, int(ceil(0.10 * n)))
    print(f"  top-decile diagnostic (drop {k}): {srt[:n-k].mean():+.4f}")
    T.to_csv(ROOT / "reports/ib_pullback_holdout_trades.csv", index=False)


if __name__ == "__main__":
    main()
