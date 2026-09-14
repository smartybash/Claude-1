#!/usr/bin/env python3
"""Can CVD be recovered from OHLCV bars? Test it before trusting it.

CVD needs the aggressor side of every trade, and bars do not carry it. But
there are standard reconstructions, and whether they work is a measurable
question rather than a matter of opinion. The recorded NQ tape settles it: it
has both the true signed volume AND enough resolution to build 1-minute bars
from. Build the bars, compute each proxy from the bars alone, and compare to
the truth derived from the same trades.

Three candidates:

    tick rule      sign of the bar's close against the previous close, times
                   the whole bar volume. The classic Lee-Ready idea, applied
                   at bar resolution.
    close location where the close sits inside the bar's range, scaled to
                   [-1, +1]. A close on the high means buyers finished in
                   control of that minute.
    open-close     the bar's own direction as a share of its range.

The number that matters is not the correlation of the per-bar delta -- that
can be mediocre while the running total is still right. What a trade uses is
the CUMULATIVE line and its sign at a decision point, so that is what is
scored: correlation of the session CVD path, and how often the proxy agrees
with the truth about which side is in control.

If none of them clears a useful bar, the answer is that bar data cannot test
any CVD rule, at any sample size, and the honest move is to say so rather
than to run a large backtest on a number that does not mean what it claims.

Usage: python3 scripts/orderflow/cvd_proxy.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tape import load_all, rth                                          # noqa


def bars1m(s: pd.DataFrame) -> pd.DataFrame:
    """1-minute OHLCV bars plus the TRUE signed volume, from the same trades."""
    g = s.set_index("time").resample("1min")
    b = g.agg(o=("price", "first"), h=("price", "max"), l=("price", "min"),
              c=("price", "last"), v=("volume", "sum"), true=("signed", "sum"))
    return b.dropna(subset=["c"])


def proxies(b: pd.DataFrame) -> dict:
    """Each proxy's per-bar delta, computed from OHLCV only."""
    o, h, l, c, v = (b.o.to_numpy(), b.h.to_numpy(), b.l.to_numpy(),
                     b.c.to_numpy(), b.v.to_numpy())
    rng = np.where(h > l, h - l, np.nan)

    prev = np.concatenate([[c[0]], c[:-1]])
    tick = np.sign(c - prev) * v

    clv = (2 * (c - l) / rng - 1)
    clv = np.nan_to_num(clv, nan=0.0) * v

    oc = np.nan_to_num((c - o) / rng, nan=0.0) * v

    return {"tick rule": tick, "close location": clv, "open-close": oc}


def main():
    full = load_all()
    days = {d: rth(f) for d, f in sorted(full.items())}
    days = {d: s for d, s in days.items() if len(s) > 5000}
    print("=" * 88)
    print(f"CAN CVD BE REBUILT FROM BARS?   {len(days)} recorded NQ sessions")
    print("=" * 88)
    print("  Bars are built from the same trades that give the true CVD, so")
    print("  this isolates the reconstruction and nothing else.\n")

    names = ["tick rule", "close location", "open-close"]
    path_r, sign_ok, end_err = {n: [] for n in names}, {n: [] for n in names}, {n: [] for n in names}

    for d, s in days.items():
        b = bars1m(s)
        if len(b) < 100:
            continue
        truth = b.true.to_numpy().cumsum()
        for n, delta in proxies(b).items():
            est = delta.cumsum()
            if truth.std() > 0 and est.std() > 0:
                path_r[n].append(np.corrcoef(truth, est)[0, 1])
            # does it agree on WHICH SIDE is in control, bar by bar?
            m = truth != 0
            sign_ok[n].append(np.mean(np.sign(est[m]) == np.sign(truth[m])))
            # and how far off is the close-of-session total, in true units
            scale = np.abs(truth).max() or 1.0
            end_err[n].append(abs(est[-1] - truth[-1]) / scale)

    print(f"  {'proxy':<18}{'path corr':>12}{'sign agree':>13}{'end error':>12}")
    for n in names:
        print(f"  {n:<18}{np.mean(path_r[n]):>11.2f} "
              f"{100*np.mean(sign_ok[n]):>11.0f}% {100*np.mean(end_err[n]):>10.0f}%")

    print("\n  path corr    correlation of the running CVD line with the truth")
    print("  sign agree   how often the proxy has the same side in control")
    print("  end error    session-end gap, as a share of the day's CVD range\n")

    best = max(names, key=lambda n: np.mean(path_r[n]))
    r = np.mean(path_r[best])
    agree = np.mean(sign_ok[best])
    print("=" * 88)
    print(f"  BEST: {best}   path corr {r:+.2f}, sign agreement {100*agree:.0f}%")
    if r > 0.85 and agree > 0.80:
        print("  Good enough to stand in for CVD in a backtest.")
    elif r > 0.6:
        print("  Partial. It tracks the shape but not well enough to trust a")
        print("  THRESHOLD on -- the 1.5%-of-volume rule needs the level, not")
        print("  just the direction. Usable only for coarse sign questions.")
    else:
        print("  Not usable. Bars cannot stand in for CVD, so no bar-based")
        print("  backtest can test a CVD rule -- at any sample size.")
    print("=" * 88)

    # Per-session spread on the best one: an average can hide days that invert.
    print(f"\n  per-session path correlation for {best}:")
    vals = sorted(path_r[best])
    print(f"    worst {vals[0]:+.2f}   25th {np.percentile(vals,25):+.2f}   "
          f"median {np.median(vals):+.2f}   75th {np.percentile(vals,75):+.2f}   "
          f"best {vals[-1]:+.2f}")
    print(f"    sessions where it points the WRONG WAY (corr < 0): "
          f"{sum(v < 0 for v in vals)}/{len(vals)}")


if __name__ == "__main__":
    main()
