#!/usr/bin/env python3
"""ABSORPTION — does aggression that fails to move price predict a reversal?

This is the one claim the recording can actually test, and the only one that
does not need fixed levels: the two recorded sessions gapped 370 points apart,
so not a single prior-day level was touched on the second day and level work is
impossible on this sample.

The mechanism under test is the 2x2 of aggression against price response:

    heavy buying, price rises      -> aggression achieved something, go with
    heavy buying, price does not   -> someone sold into all of it, fade
    heavy selling, price falls     -> go with
    heavy selling, price does not  -> fade

Only the second and fourth are interesting, because only they say something a
price chart does not already say.

Design, and specifically the lookahead controls:

  * the session is cut into fixed windows; delta and the price change WITHIN a
    window are known the instant it closes
  * entry is the last trade price of that window -- never a price inside it,
    which was exactly the bias that invalidated the earlier level studies
  * the forward move is measured from that entry over the following windows
  * a control of every window measures what a coin flip earns here

Reporting is per day as well as pooled. Two sessions are two draws of market
regime, so a pooled t-statistic is not evidence of anything; agreement between
two independent days is weak evidence, and disagreement is decisive against.

Usage: python3 scripts/absorption.py
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from tape import load_all, rth

POINT_USD = 20.0
COST_PTS = 2.0        # round trip: one tick of spread plus commission


def windows(s: pd.DataFrame, secs: int) -> pd.DataFrame:
    """Fixed-time windows with delta, price change, and the closing price."""
    g = s.set_index("time").resample(f"{secs}s")
    w = pd.DataFrame({
        "vol": g.volume.sum(),
        "delta": g.signed.sum(),
        "first": g.price.first(),
        "last": g.price.last(),
        "n": g.price.count(),
    }).dropna(subset=["last"])
    w = w[w.n > 0].copy()
    w["move"] = w["last"] - w["first"]
    return w


def fwd(w: pd.DataFrame, k: int) -> np.ndarray:
    """Points from this window's close to the close k windows later."""
    return w["last"].shift(-k).to_numpy() - w["last"].to_numpy()


def stat(x, label, cost=0.0):
    x = np.asarray([v for v in x if np.isfinite(v)], float)
    if len(x) < 25:
        return f"  {label:<34} n={len(x):<5} too few"
    x = x - cost
    sd = x.std(ddof=1)
    t = x.mean() / (sd / np.sqrt(len(x))) if sd > 0 else 0.0
    return (f"  {label:<34} n={len(x):<5} {x.mean():+6.2f}pt "
            f"{x.mean()*POINT_USD:+8.2f}$  win {100*(x > 0).mean():3.0f}%  "
            f"t={t:+5.2f}")


def main():
    days = {d: rth(df) for d, df in sorted(load_all().items())}
    days = {d: s for d, s in days.items() if len(s) > 5000}

    SECS, K = 30, 4          # 30-second windows, hold 2 minutes

    print("=" * 84)
    print(f"ABSORPTION TEST — {SECS}s windows, hold {K} windows "
          f"({SECS*K}s), RTH only")
    print(f"cost assumed {COST_PTS:.1f} pts round trip "
          f"(${COST_PTS*POINT_USD:.0f}); price grid is 5 pts")
    print("=" * 84)

    W = {}
    for d, s in days.items():
        w = windows(s, SECS)
        w["f"] = fwd(w, K)
        W[d] = w
        print(f"  {d}: {len(w)} windows, median {w.vol.median():.0f} contracts, "
              f"delta p10/p90 {w.delta.quantile(.1):+.0f}/{w.delta.quantile(.9):+.0f}")

    print("\n" + "=" * 84)
    print("1  BASELINE — what a random entry earns")
    print("=" * 84)
    for d, w in W.items():
        print(stat(w.f.values, f"{d} long every window"))
    pool = np.concatenate([w.f.values for w in W.values()])
    print(stat(pool, "pooled"))

    print("\n" + "=" * 84)
    print("2  DOSE-RESPONSE — forward move by delta decile")
    print("=" * 84)
    print("  If aggression predicts continuation, this rises left to right.")
    print("  If it predicts reversal, it falls. If it is noise, it is flat.\n")
    for d, w in W.items():
        q = pd.qcut(w.delta, 10, labels=False, duplicates="drop")
        cells = [w.f[q == i].mean() for i in range(10)]
        print(f"  {d}  " + " ".join(f"{c:+6.1f}" for c in cells))
    print("     decile   " + " ".join(f"{i+1:>6}" for i in range(10)))

    print("\n" + "=" * 84)
    print("3  THE 2x2 — aggression crossed with price response")
    print("=" * 84)
    print("  'heavy' = top/bottom 20% of delta. 'no progress' = price ended the")
    print("  window within one 5-point bin of where it started.")
    print("  Sign convention: the number shown is what the FADE earns, so a")
    print("  positive absorption cell means selling into heavy buying paid.\n")

    for d, w in W.items():
        hi, lo = w.delta.quantile(0.80), w.delta.quantile(0.20)
        flat = w["move"].abs() <= 5.0
        print(f"  --- {d} ---")
        buy_stuck = w[(w.delta >= hi) & flat]
        sell_stuck = w[(w.delta <= lo) & flat]
        buy_works = w[(w.delta >= hi) & (w["move"] > 5.0)]
        sell_works = w[(w.delta <= lo) & (w["move"] < -5.0)]
        print(stat(-buy_stuck.f.values, "buying absorbed -> short"))
        print(stat(sell_stuck.f.values, "selling absorbed -> long"))
        print(stat(buy_works.f.values, "buying working -> long (go with)"))
        print(stat(-sell_works.f.values, "selling working -> short (go with)"))

    print("\n  --- pooled, net of cost ---")
    cat = lambda f: np.concatenate([f(w) for w in W.values()])
    def cell(sel, sign):
        return cat(lambda w: sign * w[sel(w)].f.values)
    hi_ = lambda w: w.delta >= w.delta.quantile(0.80)
    lo_ = lambda w: w.delta <= w.delta.quantile(0.20)
    fl_ = lambda w: w["move"].abs() <= 5.0
    print(stat(cell(lambda w: hi_(w) & fl_(w), -1),
               "buying absorbed -> short", COST_PTS))
    print(stat(cell(lambda w: lo_(w) & fl_(w), +1),
               "selling absorbed -> long", COST_PTS))
    print(stat(cell(lambda w: hi_(w) & (w["move"] > 5), +1),
               "buying working -> long", COST_PTS))
    print(stat(cell(lambda w: lo_(w) & (w["move"] < -5), -1),
               "selling working -> short", COST_PTS))

    print("\n" + "=" * 84)
    print("4  ROBUSTNESS — does the best cell survive a change of clock?")
    print("=" * 84)
    for secs, k in ((15, 8), (30, 4), (60, 2), (120, 1)):
        rows = []
        for d, s in days.items():
            w = windows(s, secs)
            w["f"] = fwd(w, k)
            hi = w.delta.quantile(0.80)
            sel = w[(w.delta >= hi) & (w["move"].abs() <= 5.0)]
            rows.append(-sel.f.values)
        print(stat(np.concatenate(rows),
                   f"{secs:>3}s window, hold {secs*k:>3}s", COST_PTS))


if __name__ == "__main__":
    main()
