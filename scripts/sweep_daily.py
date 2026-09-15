#!/usr/bin/env python3
"""DAILY SWEEP — five years, everything at once, nothing cherry-picked.

Every test so far has been intraday on one instrument. The repo also holds
1,255 daily bars of QQQ and SPY (2021-07 to 2026-07) that have never been
touched. This sweeps the standard daily structures across both symbols and
prints all of them, including the failures, so the multiple-testing problem is
visible rather than hidden.

  1  OVERNIGHT vs INTRADAY   close->open against open->close. The best
                             documented anomaly in index data and never
                             tested here.
  2  DAY OF WEEK             both legs, separately.
  3  GAP                     open gap in ATR buckets -> the day's own
                             open->close. Does a gap get faded or followed?
  4  STREAKS                 n consecutive up or down closes -> next day.
  5  CLOSE LOCATION          where the close sits in the day's range ->
                             next day.
  6  VOLATILITY REGIME       ATR percentile, applied to whichever of the
                             above survives.
  7  MOMENTUM / REVERSAL     trailing 5, 10, 20-day return -> next day.

Roughly forty hypotheses are printed. At the 5% level two of them are expected
to look significant by chance alone, so the bar for calling anything real is a
t-statistic that survives Bonferroni (|t| ~ 3.2 at forty tests) AND appears in
both QQQ and SPY, which are the same underlying and should agree.

Returns are in basis points and, where a comparison needs scaling, in ATR
units. No trading costs are modelled, so any edge under a few bps is not real
for a retail account.

Usage: python3 scripts/sweep_daily.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
N_TESTS = 40
BONF_T = 3.2


def stat(a, unit="bp"):
    a = np.asarray([x for x in a if np.isfinite(x)], float)
    if len(a) < 5:
        return f"n={len(a):4d}  --"
    sd = a.std(ddof=1)
    t = a.mean() / (sd / np.sqrt(len(a))) if sd > 0 else 0.0
    star = " *" if abs(t) >= BONF_T else ""
    return (f"n={len(a):4d}  mean {a.mean():+7.2f}{unit}  "
            f"win {100*(a>0).mean():3.0f}%  t={t:+5.2f}{star}")


def load(sym):
    d = pd.read_parquet(ROOT / f"data/parquet/{sym}_daily.parquet").copy()
    d.index = pd.to_datetime(d.index).tz_localize(None).normalize()
    d = d[~d.index.duplicated(keep="last")].sort_index()
    d["prev_close"] = d.close.shift(1)
    d["on"] = (d.open / d.prev_close - 1) * 1e4          # overnight, bp
    d["id"] = (d.close / d.open - 1) * 1e4               # intraday, bp
    d["full"] = (d.close / d.prev_close - 1) * 1e4
    tr = np.maximum(d.high - d.low,
                    np.maximum((d.high - d.prev_close).abs(),
                               (d.low - d.prev_close).abs()))
    d["atr"] = tr.rolling(14).mean().shift(1)
    d["gap_atr"] = (d.open - d.prev_close) / d.atr
    d["clsloc"] = (d.close - d.low) / (d.high - d.low).replace(0, np.nan)
    d["up"] = d.close > d.prev_close
    streak = np.zeros(len(d))
    for i in range(1, len(d)):
        if d.up.iloc[i] == d.up.iloc[i - 1]:
            streak[i] = streak[i - 1] + (1 if d.up.iloc[i] else -1)
        else:
            streak[i] = 1 if d.up.iloc[i] else -1
    d["streak"] = streak
    for n in (5, 10, 20):
        d[f"mom{n}"] = (d.close / d.close.shift(n) - 1) * 1e4
    return d.dropna(subset=["prev_close", "atr"])


def main():
    data = {s: load(s) for s in ("QQQ", "SPY")}
    a = data["QQQ"]
    print(f"QQQ / SPY daily — {len(a)} bars, {a.index.min().date()} to "
          f"{a.index.max().date()}")
    print(f"~{N_TESTS} hypotheses printed; * marks |t| >= {BONF_T} "
          f"(Bonferroni). Anything unstarred is noise.\n")

    print("=" * 92)
    print("1  OVERNIGHT vs INTRADAY")
    print("=" * 92)
    for s, d in data.items():
        print(f"  {s}  close->open (overnight) {stat(d['on'])}")
        print(f"  {s}  open->close (intraday)  {stat(d['id'])}")
        print(f"  {s}  close->close (buy&hold) {stat(d['full'])}")

    print("\n" + "=" * 92)
    print("2  DAY OF WEEK")
    print("=" * 92)
    for s, d in data.items():
        for leg in ("on", "id"):
            nm = "overnight" if leg == "on" else "intraday "
            out = []
            for dow, g in d.groupby(d.index.dayofweek):
                if dow > 4:
                    continue
                lbl = ["Mon", "Tue", "Wed", "Thu", "Fri"][dow]
                out.append(f"{lbl} {g[leg].mean():+6.1f}")
            print(f"  {s}  {nm}  " + "  ".join(out))

    print("\n" + "=" * 92)
    print("3  GAP -> that day's OPEN->CLOSE   (is a gap followed or faded?)")
    print("=" * 92)
    buckets = [(-9, -1.0, "gap dn > 1.0 ATR"), (-1.0, -0.5, "gap dn 0.5-1.0"),
               (-0.5, -0.15, "gap dn 0.15-0.5"), (-0.15, 0.15, "flat open"),
               (0.15, 0.5, "gap up 0.15-0.5"), (0.5, 1.0, "gap up 0.5-1.0"),
               (1.0, 9, "gap up > 1.0 ATR")]
    for s, d in data.items():
        print(f"  --- {s} ---")
        for lo, hi, lbl in buckets:
            g = d[(d.gap_atr >= lo) & (d.gap_atr < hi)]
            print(f"    {lbl:18s} {stat(g['id'])}")

    print("\n" + "=" * 92)
    print("4  STREAKS -> NEXT DAY")
    print("=" * 92)
    for s, d in data.items():
        print(f"  --- {s} ---")
        for lbl, mask in (("after 1 up", d.streak == 1), ("after 2 up", d.streak == 2),
                          ("after 3+ up", d.streak >= 3), ("after 1 dn", d.streak == -1),
                          ("after 2 dn", d.streak == -2), ("after 3+ dn", d.streak <= -3)):
            nxt = d["full"].shift(-1)[mask]
            print(f"    {lbl:14s} next close-close  {stat(nxt)}")

    print("\n" + "=" * 92)
    print("5  CLOSE LOCATION IN RANGE -> NEXT DAY")
    print("=" * 92)
    for s, d in data.items():
        print(f"  --- {s} ---")
        for lo, hi, lbl in ((0, .2, "closed bottom 20%"), (.2, .4, "20-40%"),
                            (.4, .6, "middle"), (.6, .8, "60-80%"),
                            (.8, 1.01, "closed top 20%")):
            m = (d.clsloc >= lo) & (d.clsloc < hi)
            print(f"    {lbl:18s} next overnight {stat(d['on'].shift(-1)[m])}")
            print(f"    {'':18s} next intraday  {stat(d['id'].shift(-1)[m])}")

    print("\n" + "=" * 92)
    print("6  TRAILING MOMENTUM -> NEXT DAY")
    print("=" * 92)
    for s, d in data.items():
        print(f"  --- {s} ---")
        for n in (5, 10, 20):
            q = d[f"mom{n}"].quantile([0.2, 0.8]).values
            lowm = d[f"mom{n}"] <= q[0]
            him = d[f"mom{n}"] >= q[1]
            print(f"    {n:2d}d weakest quintile  next c-c  {stat(d['full'].shift(-1)[lowm])}")
            print(f"    {n:2d}d strongest quintile next c-c  {stat(d['full'].shift(-1)[him])}")

    print("\n" + "=" * 92)
    print("7  OVERNIGHT LEG BY VOLATILITY REGIME  (the leg most likely to survive)")
    print("=" * 92)
    for s, d in data.items():
        atrp = (d.atr / d.close * 1e4)
        q = atrp.quantile([0.33, 0.67]).values
        print(f"  --- {s} ---")
        for lbl, m in (("calm  (low ATR)", atrp < q[0]),
                       ("mid", (atrp >= q[0]) & (atrp < q[1])),
                       ("stressed (high ATR)", atrp >= q[1])):
            print(f"    {lbl:20s} overnight {stat(d['on'][m])}")
            print(f"    {'':20s} intraday  {stat(d['id'][m])}")


if __name__ == "__main__":
    main()
