#!/usr/bin/env python3
"""Does INITIAL BALANCE width predict when the VALUE-AREA FADE works?

The IB breakout trade itself has no edge (backtest_initial_balance.py), but the
IB width is a clean, free day-type classifier that ATAS draws natively:
  * NARROW IB  -> compression, the day wants to EXPAND -> fading the edges should
    be worse (you are fading a day that is about to trend).
  * WIDE IB    -> the day already spent its range early, balance/rotation ->
    fading the value-area edge back to POC should be BETTER.

If that holds, IB width becomes the one dial that picks which of our two setups
to run — which is exactly what makes a playbook simple.

Splits the validated VA-fade (short the 2nd VAH rejection -> POC) by IB width
measured against the 14-day ATR. QQQ 5-min, ~2y.

Usage: python3 scripts/backtest_ib_regime_filter.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import backtest_tos_fvg as F
import backtest_range_breakout as BR
import backtest_va_fade as VF
from backtest_initial_balance import daily_atr, IB_END


def summ(a):
    a = np.array([x for x in a if np.isfinite(x)], float)
    if len(a) == 0:
        return "n=0"
    sd = a.std(ddof=1) if len(a) > 1 else 0.0
    t = a.mean() / (sd / np.sqrt(len(a))) if sd > 0 else 0.0
    wins = a[a > 0].sum(); losses = -a[a < 0].sum()
    pf = wins / losses if losses > 0 else float("inf")
    return (f"n={len(a):3d}  win {100*(a>0).mean():3.0f}%  mean {a.mean():+.3f}R  "
            f"PF {pf:.2f}  t={t:+.2f}")


def main():
    sess = F.load_sessions()
    days = sorted(sess)
    atr = daily_atr()
    reads = BR.gamma_reads("QQQ")
    rows = []
    for i, d in enumerate(days):
        va = VF.prior_va(sess, days, i)
        if not va:
            continue
        poc, vah, val = va
        b = sess[d]
        if float(b["open"].iloc[0]) > vah:
            continue
        a = atr.get(pd.Timestamp(d).normalize(), np.nan)
        if not pd.notna(a) or a <= 0:
            continue
        ib = b[b.index.strftime("%H:%M") < IB_END]
        if len(ib) < 8:
            continue
        w_atr = (float(ib["high"].max()) - float(ib["low"].min())) / float(a)
        g = BR.gamma_lookup(reads, pd.Timestamp(d))
        net = g.get("net_gex") if g else None
        for r in VF.simulate(b, vah, poc, val):
            rows.append(dict(day=d, w_atr=w_atr, net=net, attempt=r["attempt"],
                             r_poc=r["r_poc"], r_val=r["r_val"]))
    T = pd.DataFrame(rows)
    print(f"=== VA-fade split by INITIAL BALANCE width — QQQ 5-min, "
          f"{T.day.nunique()} days, {len(T)} signals ===")
    print(f"IB width vs ATR: median {T.w_atr.median():.2f}x\n")

    print("target POC (the validated exit):")
    med = T.w_atr.median()
    for lo, hi, lbl in ((0, 0.5, "NARROW IB  <0.5x ATR (expansion day)"),
                        (0.5, 99, "WIDER  IB  >0.5x ATR (balance day)")):
        sub = T[(T.w_atr >= lo) & (T.w_atr < hi)]
        print(f"   {lbl:38} {summ(sub.r_poc)}")
    print()
    for lo, hi, lbl in ((0, med, f"below median IB (<{med:.2f}x)"),
                        (med, 99, f"above median IB (>{med:.2f}x)")):
        sub = T[(T.w_atr >= lo) & (T.w_atr < hi)]
        print(f"   {lbl:38} {summ(sub.r_poc)}")

    print("\n>=2nd VAH attempt only (the tested edge):")
    T2 = T[T.attempt >= 2]
    for lo, hi, lbl in ((0, 0.5, "NARROW IB  <0.5x ATR"),
                        (0.5, 99, "WIDER  IB  >0.5x ATR")):
        sub = T2[(T2.w_atr >= lo) & (T2.w_atr < hi)]
        print(f"   {lbl:38} {summ(sub.r_poc)}")

    print("\nbaseline (no IB filter):")
    print(f"   {'ALL signals':38} {summ(T.r_poc)}")
    print(f"   {'>=2nd attempt':38} {summ(T2.r_poc)}")


if __name__ == "__main__":
    main()
