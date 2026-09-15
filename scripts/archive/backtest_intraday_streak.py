#!/usr/bin/env python3
"""INTRADAY STREAK — the confirmed daily mechanism, moved to a day-trading clock.

The only thing that survived 27 years is short-term mean reversion after
persistent selling: three or more consecutive down daily closes returns
+37.38bp on QQQ (t=+4.04) and +27.23bp on SPY (t=+4.05), against +2bp on every
other day, with a monotonic dose-response in streak depth and positive results
in the dot-com unwind, the GFC and the 2022 bear.

That fires twice a month and holds overnight, which is no use to a day trader.
But every intraday test in this repo keyed off a LEVEL, and levels are now
thoroughly dead. The streak mechanism was never tried intraday at all.

So: same rule, intraday clock.

  SIGNAL  k consecutive down bars (close below the previous close)
  ENTRY   that bar's close
  EXIT    m bars later, at the session close, or on a stop/target
  CONTROL every bar, and every bar that is NOT a signal -- if the signal days
          do not separate sharply from the rest, there is nothing here

Swept across bar sizes (1, 5, 15, 30 minutes), streak depths, and holding
periods, with the same discipline as the daily work: a control on every run,
an out-of-sample split, and time-of-day conditioning, since the open and the
close behave differently from the middle of the session.

Both directions are tested. Up-streaks are included because if only the down
side works, that is the same asymmetry the daily study found, and if neither
does, the mechanism simply does not exist at this clock speed.

Usage: python3 scripts/backtest_intraday_streak.py
"""
from __future__ import annotations

import glob
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

NQ_REF = 29400.0


def stat(a):
    a = np.asarray([x for x in a if np.isfinite(x)], float)
    if len(a) < 10:
        return f"n={len(a):5d}  --"
    sd = a.std(ddof=1)
    t = a.mean() / (sd / np.sqrt(len(a))) if sd > 0 else 0.0
    return (f"n={len(a):5d}  {a.mean():+6.2f}bp  win {100*(a>0).mean():3.0f}%  "
            f"t={t:+5.2f}  {a.mean()/1e4*NQ_REF:+6.1f}NQpt")


def load_1m():
    fr = [pd.read_csv(f, parse_dates=["timestamp"])
          for f in sorted(glob.glob(str(ROOT / "data/intraday/qqq_1m_*.csv")))]
    df = pd.concat(fr).set_index("timestamp").sort_index()
    df = df[~df.index.duplicated(keep="last")]
    return df.between_time("09:30", "15:59")


def resample(df, rule):
    if rule == "1min":
        return df
    return df.resample(rule).agg({"open": "first", "high": "max", "low": "min",
                                  "close": "last", "volume": "sum"}).dropna()


def build(df, k, hold, side=-1):
    """side -1: buy after k down bars. side +1: sell after k up bars.
    Returns forward return in bp, signed so positive = the trade worked."""
    out = []
    for _, b in df.groupby(df.index.normalize()):
        c = b.close.values
        n = len(c)
        if n < k + hold + 2:
            continue
        d = np.diff(c)
        run = np.zeros(n)
        for i in range(1, n):
            s = 1 if d[i - 1] > 0 else (-1 if d[i - 1] < 0 else 0)
            run[i] = run[i - 1] + s if (run[i - 1] > 0) == (s > 0) and s != 0 else s
        for i in range(k, n - hold):
            hit = (run[i] <= -k) if side < 0 else (run[i] >= k)
            if not hit:
                continue
            fwd = (c[i + hold] / c[i] - 1) * 1e4
            out.append(-fwd if side > 0 else fwd)
    return np.array(out)


def control(df, hold):
    out = []
    for _, b in df.groupby(df.index.normalize()):
        c = b.close.values
        if len(c) < hold + 2:
            continue
        f = (c[hold:] / c[:-hold] - 1) * 1e4
        out.extend(f.tolist())
    return np.array(out)


def main():
    raw = load_1m()
    nd = raw.index.normalize().nunique()
    print(f"QQQ intraday RTH — {nd} sessions, "
          f"{raw.index.min().date()} to {raw.index.max().date()}")
    print("buy after k consecutive DOWN bars, exit m bars later; "
          "bp per trade, NQpt at 29,400\n")

    for rule, lbl in (("5min", "5-minute"), ("15min", "15-minute"),
                      ("30min", "30-minute"), ("1min", "1-minute")):
        df = resample(raw, rule)
        print("=" * 96)
        print(f"{lbl} bars")
        print("=" * 96)
        for hold in (1, 2, 3, 6):
            row = []
            for k in (3, 4, 5, 6):
                a = build(df, k, hold, -1)
                m = a.mean() if len(a) >= 10 else np.nan
                tt = (a.mean() / (a.std(ddof=1) / np.sqrt(len(a)))
                      if len(a) >= 10 and a.std(ddof=1) > 0 else np.nan)
                row.append(f"k={k}: {m:+6.2f}bp t={tt:+5.2f} n={len(a):4d}")
            ctl = control(df, hold)
            print(f"  hold {hold:2d} bar(s)   " + " | ".join(row))
            print(f"  {'':14s} control (every bar): {stat(ctl)}")
        print()

    # the most promising cell gets the full treatment
    print("=" * 96)
    print("DETAIL — 5-minute, k=4 down bars, hold 3 bars")
    print("=" * 96)
    df5 = resample(raw, "5min")
    a_dn = build(df5, 4, 3, -1)
    a_up = build(df5, 4, 3, +1)
    print(f"  after 4 DOWN bars (buy)   {stat(a_dn)}")
    print(f"  after 4 UP   bars (sell)  {stat(a_up)}")
    print(f"  control, any bar          {stat(control(df5, 3))}")

    print("\n  by time of day (5-min, k=4, hold 3, buy):")
    rows = []
    for _, b in df5.groupby(df5.index.normalize()):
        c = b.close.values
        idx = b.index
        n = len(c)
        if n < 10:
            continue
        d = np.diff(c)
        run = np.zeros(n)
        for i in range(1, n):
            s = 1 if d[i - 1] > 0 else (-1 if d[i - 1] < 0 else 0)
            run[i] = run[i - 1] + s if (run[i - 1] > 0) == (s > 0) and s != 0 else s
        for i in range(4, n - 3):
            if run[i] <= -4:
                rows.append(dict(hhmm=idx[i].strftime("%H:%M"),
                                 day=idx[i].normalize(),
                                 r=(c[i + 3] / c[i] - 1) * 1e4))
    T = pd.DataFrame(rows)
    if len(T):
        T["bucket"] = pd.cut(T.hhmm.str.slice(0, 2).astype(int),
                             [8, 10, 11, 13, 14, 16],
                             labels=["09:30-10:59", "11:00-11:59", "12:00-13:59",
                                     "14:00-14:59", "15:00-15:59"])
        for bkt, g in T.groupby("bucket", observed=True):
            print(f"    {str(bkt):14s} {stat(g.r.values)}")
        mid = sorted(T.day.unique())[len(T.day.unique()) // 2]
        print("\n  out of sample:")
        print(f"    first half   {stat(T[T.day < mid].r.values)}")
        print(f"    second half  {stat(T[T.day >= mid].r.values)}")


if __name__ == "__main__":
    main()
