#!/usr/bin/env python3
"""OVERSOLD BOUNCE over 27 years — the test that decides it.

On five years of QQQ and SPY (2021-2026) the rule "buy the close after three or
more consecutive down closes, sell the next close" returned +48.64bp at t=+3.35
and +38.13bp at t=+2.82, with a monotonic dose-response in streak depth, every
calendar year positive in both symbols, and non-signal days returning +2.50bp
against the signal's +48.64bp.

Five years is not enough to trust it. That window is one regime: a period of
strong index drift in which reflexive dip-buying was itself the dominant
behaviour. The rule could be a description of 2021-2026 rather than of markets.

This runs the identical rule on split- and dividend-adjusted daily history back
to 1999 -- through the dot-com unwind, 2008, and 2020 -- and asks whether it is
a market structure or a recent habit:

  * by calendar year and by five-year block
  * the three crashes isolated (2000-2002, 2008-2009, Feb-Apr 2020)
  * bull years against bear years, since a long-only dip-buyer is flattered by
    an uptrend and the honest question is whether it survives without one
  * dose-response across streak depth, on the full history
  * the control: signal days against every other day
  * costs, drawdown and time in market

Prices are adjusted so that a split does not manufacture a fake streak.

Usage: python3 scripts/backtest_oversold_long.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
NQ_REF = 29400.0


def stat(a):
    a = np.asarray([x for x in a if np.isfinite(x)], float)
    if len(a) < 5:
        return f"n={len(a):5d}  --"
    sd = a.std(ddof=1)
    t = a.mean() / (sd / np.sqrt(len(a))) if sd > 0 else 0.0
    ir = a.mean() / sd if sd > 0 else 0.0
    return (f"n={len(a):5d}  {a.mean():+7.2f}bp  win {100*(a>0).mean():3.0f}%  "
            f"t={t:+5.2f}  IR {ir:+.3f}")


def load(sym):
    d = pd.read_csv(ROOT / f"data/daily_long/{sym}.csv", parse_dates=["timestamp"])
    d = d.set_index("timestamp").sort_index()
    d["prev_close"] = d.close.shift(1)
    d["on"] = (d.open / d.prev_close - 1) * 1e4
    d["full"] = (d.close / d.prev_close - 1) * 1e4
    d["up"] = d.close > d.prev_close
    s = np.zeros(len(d))
    up = d.up.values
    for i in range(1, len(d)):
        s[i] = (s[i - 1] + (1 if up[i] else -1)) if up[i] == up[i - 1] else (1 if up[i] else -1)
    d["streak"] = s
    d["nxt"] = d["full"].shift(-1)
    d["nxt_on"] = d["on"].shift(-1)
    return d.dropna(subset=["prev_close"])


def main():
    data = {s: load(s) for s in ("QQQ", "SPY")}
    q = data["QQQ"]
    print(f"QQQ / SPY split-adjusted daily — {len(q)} bars, "
          f"{q.index.min().date()} to {q.index.max().date()}  (~27 years)\n")

    print("=" * 92)
    print("1  DOSE-RESPONSE ACROSS THE FULL HISTORY  (buy close -> sell next close)")
    print("=" * 92)
    for s, d in data.items():
        print(f"  --- {s} ---")
        for k in (1, 2, 3, 4, 5):
            print(f"    {k}+ consecutive down closes  {stat(d.nxt[d.streak <= -k])}")
        print(f"    every day (control)         {stat(d.nxt)}")
        print(f"    NOT 3+ down (control)       {stat(d.nxt[d.streak > -3])}")
        print()

    print("=" * 92)
    print("2  BY FIVE-YEAR BLOCK  (3+ down -> next close)")
    print("=" * 92)
    for s, d in data.items():
        print(f"  --- {s} ---")
        r = d.nxt[d.streak <= -3]
        for lo in range(1999, 2027, 5):
            g = r[(r.index.year >= lo) & (r.index.year < lo + 5)]
            if len(g) >= 5:
                print(f"    {lo}-{min(lo+4, 2026)}  {stat(g)}")
        print()

    print("=" * 92)
    print("3  THE THREE CRASHES  (3+ down -> next close)")
    print("=" * 92)
    windows = [("dot-com unwind 2000-2002", "2000-01-01", "2003-01-01"),
               ("GFC 2008-2009", "2008-01-01", "2010-01-01"),
               ("COVID Feb-Apr 2020", "2020-02-01", "2020-05-01"),
               ("2022 bear", "2022-01-01", "2023-01-01")]
    for s, d in data.items():
        print(f"  --- {s} ---")
        r = d.nxt[d.streak <= -3]
        for lbl, a, b in windows:
            g = r[(r.index >= a) & (r.index < b)]
            print(f"    {lbl:26s} {stat(g)}")
        print()

    print("=" * 92)
    print("4  BULL YEARS vs BEAR YEARS  (does it need an uptrend?)")
    print("=" * 92)
    for s, d in data.items():
        yr = d.close.resample("YE").last().pct_change()
        bear_years = set(yr[yr < 0].index.year)
        r = d.nxt[d.streak <= -3]
        inb = r.index.year.isin(bear_years)
        print(f"  {s}  down years {sorted(bear_years)}")
        print(f"  {s}  in DOWN years  {stat(r[inb])}")
        print(f"  {s}  in UP years    {stat(r[~inb])}")

    print("\n" + "=" * 92)
    print("5  EXIT LEG: next open vs next close")
    print("=" * 92)
    for s, d in data.items():
        m = d.streak <= -3
        print(f"  {s}  -> next OPEN   {stat(d.nxt_on[m])}")
        print(f"  {s}  -> next CLOSE  {stat(d.nxt[m])}")

    print("\n" + "=" * 92)
    print("6  EQUITY / DRAWDOWN / EXPOSURE  (3+ down -> next close)")
    print("=" * 92)
    for s, d in data.items():
        r = d.nxt[d.streak <= -3].dropna().values
        eq = np.cumsum(r)
        dd = (np.maximum.accumulate(eq) - eq).max()
        yrs = (d.index.max() - d.index.min()).days / 365.25
        bh = (d.close.iloc[-1] / d.close.iloc[0] - 1) * 100
        print(f"  {s}  total {eq[-1]/100:+8.2f}%  maxDD {dd/100:5.2f}%  "
              f"trades/yr {len(r)/yrs:4.1f}  in market {100*len(r)/len(d):4.1f}% of days")
        print(f"  {s}  buy & hold over the same span {bh:+.0f}%  "
              f"(the rule is in the market only {100*len(r)/len(d):.1f}% of the time)")
        print(f"  {s}  breakeven round-trip cost {r.mean():.2f}bp "
              f"= {r.mean()/1e4*NQ_REF:.0f} NQ pts")

    print("\n" + "=" * 92)
    print("7  RECENT-ONLY vs OLD  (is the 2021-2026 result the whole thing?)")
    print("=" * 92)
    for s, d in data.items():
        r = d.nxt[d.streak <= -3]
        old = r[r.index < "2021-07-27"]
        new = r[r.index >= "2021-07-27"]
        print(f"  {s}  1999-2021 (out of the original sample)  {stat(old)}")
        print(f"  {s}  2021-2026 (the original sample)         {stat(new)}")


if __name__ == "__main__":
    main()
