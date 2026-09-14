#!/usr/bin/env python3
"""OVERSOLD OVERNIGHT — building and stress-testing the one surviving family.

The daily sweep produced three cuts that all point the same way in BOTH QQQ and
SPY, which is a far better sign than any single cell:

  * after 3+ consecutive down closes: +48.64bp t=+3.35 (QQQ), +38.13bp t=+2.82 (SPY)
  * overnight leg in a calm ATR regime: +9.85bp t=+3.60 (QQQ), +5.00bp t=+2.45 (SPY)
    and the regime table is monotonic in both -- overnight pays when calm and
    turns negative under stress, intraday does the opposite
  * closing in the bottom 20% of the range: positive next overnight in both

One mechanism: buy weakness at the close, carry it overnight, in calm
conditions. This assembles that into a rule and then tries to break it.

  ENTRY   at the close, when the signal fires
  EXIT    next open (overnight only) or next close (full day) -- both tested
  SIGNAL  k consecutive down closes, optionally combined with close-in-range
          and an ATR regime filter

The checks that matter, because a three-way agreement can still be one regime:
  * out of sample by date half, on both symbols
  * the 2022 bear market held out separately -- the sample is 2021-2026 and a
    long-only dip-buyer that only works after 2022 is a bull-market artifact
  * Sharpe and max drawdown, not just the mean
  * cost sensitivity: the overnight edge is small in bp and dies at some
    round-trip cost, so the breakeven cost is reported directly
  * per-year returns, so a single quarter cannot carry it

Usage: python3 scripts/backtest_oversold_overnight.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sweep_daily import load

NQ_REF = 29400.0


def stat(a):
    a = np.asarray([x for x in a if np.isfinite(x)], float)
    if len(a) < 5:
        return f"n={len(a):4d}  --"
    sd = a.std(ddof=1)
    t = a.mean() / (sd / np.sqrt(len(a))) if sd > 0 else 0.0
    # annualised Sharpe on a per-trade series is meaningless without a holding
    # period, so report the per-trade information ratio and the NQ-point value
    ir = a.mean() / sd if sd > 0 else 0.0
    return (f"n={len(a):4d}  {a.mean():+7.2f}bp  win {100*(a>0).mean():3.0f}%  "
            f"t={t:+5.2f}  IR {ir:+.3f}  {a.mean()/1e4*NQ_REF:+6.1f}NQpt")


def signal(d, k, use_range=False, regime=None):
    m = (d.streak <= -k)
    if use_range:
        m &= (d.clsloc <= 0.35)
    if regime is not None:
        atrp = d.atr / d.close * 1e4
        q = atrp.quantile([0.33, 0.67]).values
        if regime == "calm":
            m &= atrp < q[0]
        elif regime == "notstressed":
            m &= atrp < q[1]
        elif regime == "stressed":
            m &= atrp >= q[1]
    return m


def main():
    data = {s: load(s) for s in ("QQQ", "SPY")}
    a = data["QQQ"]
    print(f"QQQ / SPY daily — {len(a)} bars, {a.index.min().date()} to "
          f"{a.index.max().date()}")
    print("entry at the close on the signal; bp are per trade, "
          f"NQpt at {NQ_REF:.0f}\n")

    print("=" * 100)
    print("1  STREAK DEPTH x EXIT LEG")
    print("=" * 100)
    for s, d in data.items():
        print(f"  --- {s} ---")
        nxt_on = d["on"].shift(-1)
        nxt_full = d["full"].shift(-1)
        for k in (1, 2, 3, 4):
            m = signal(d, k)
            print(f"    {k}+ down  ->next open   {stat(nxt_on[m])}")
            print(f"    {k}+ down  ->next close  {stat(nxt_full[m])}")
        print()

    print("=" * 100)
    print("2  ADD THE REGIME FILTER  (3+ down closes)")
    print("=" * 100)
    for s, d in data.items():
        print(f"  --- {s} ---")
        nxt_on, nxt_full = d["on"].shift(-1), d["full"].shift(-1)
        for reg, lbl in ((None, "any regime"), ("calm", "calm only"),
                         ("notstressed", "calm or mid"), ("stressed", "stressed only")):
            m = signal(d, 3, regime=reg)
            print(f"    {lbl:16s} ->next open   {stat(nxt_on[m])}")
            print(f"    {'':16s} ->next close  {stat(nxt_full[m])}")
        print()

    print("=" * 100)
    print("3  OUT OF SAMPLE  (3+ down -> next close, any regime)")
    print("=" * 100)
    for s, d in data.items():
        m = signal(d, 3)
        r = d["full"].shift(-1)[m]
        mid = d.index[len(d) // 2]
        print(f"  {s}  first half  to {mid.date()}   {stat(r[r.index < mid])}")
        print(f"  {s}  second half from {mid.date()}  {stat(r[r.index >= mid])}")

    print("\n" + "=" * 100)
    print("4  BY CALENDAR YEAR  (3+ down -> next close) — can one year carry it?")
    print("=" * 100)
    for s, d in data.items():
        m = signal(d, 3)
        r = d["full"].shift(-1)[m]
        print(f"  --- {s} ---")
        for y, g in r.groupby(r.index.year):
            print(f"    {y}  {stat(g)}")

    print("\n" + "=" * 100)
    print("5  THE 2022 BEAR HELD OUT  (a dip-buyer that needs a bull market is not an edge)")
    print("=" * 100)
    for s, d in data.items():
        m = signal(d, 3)
        r = d["full"].shift(-1)[m]
        bear = (r.index >= "2022-01-01") & (r.index < "2023-01-01")
        print(f"  {s}  2022 only        {stat(r[bear])}")
        print(f"  {s}  excluding 2022   {stat(r[~bear])}")

    print("\n" + "=" * 100)
    print("6  EQUITY, DRAWDOWN, BREAKEVEN COST")
    print("=" * 100)
    for s, d in data.items():
        for lbl, k, leg in (("3+ down -> next close", 3, "full"),
                            ("3+ down -> next open ", 3, "on"),
                            ("calm overnight, every day", 0, "on")):
            if k == 0:
                atrp = d.atr / d.close * 1e4
                m = atrp < atrp.quantile(0.33)
            else:
                m = signal(d, k)
            r = (d[leg].shift(-1)[m]).dropna().values
            if len(r) < 5:
                continue
            eq = np.cumsum(r)
            dd = (np.maximum.accumulate(eq) - eq).max()
            sd = r.std(ddof=1)
            # breakeven round-trip cost in bp = the mean
            print(f"  {s}  {lbl:26s} total {eq[-1]/100:+7.2f}%  "
                  f"maxDD {dd/100:5.2f}%  trades/yr {len(r)/5:4.0f}  "
                  f"breakeven cost {r.mean():5.2f}bp "
                  f"({r.mean()/1e4*NQ_REF:.1f} NQ pts)")

    print("\n" + "=" * 100)
    print("7  DOES IT NEED THE STREAK, OR IS IT JUST 'BUY EVERY CLOSE'?")
    print("=" * 100)
    for s, d in data.items():
        print(f"  {s}  every day  ->next open   {stat(d['on'].shift(-1))}")
        print(f"  {s}  every day  ->next close  {stat(d['full'].shift(-1))}")
        m = signal(d, 3)
        print(f"  {s}  3+ down    ->next close  {stat(d['full'].shift(-1)[m])}")
        print(f"  {s}  NOT 3+ down->next close  {stat(d['full'].shift(-1)[~m])}")


if __name__ == "__main__":
    main()
