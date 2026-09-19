#!/usr/bin/env python3
"""SWEEP — every hypothesis the two recorded sessions can actually carry.

The absorption 2x2 failed at a two-minute horizon. Three things could make that
verdict premature rather than final, and each is tested here:

  H1  the horizon was wrong. Two minutes is arbitrary; absorption might need
      longer to express itself.
  H2  window delta is the wrong measure of aggression. It counts a thousand
      one-lots the same as a hundred ten-lots, and the tape is 96% singles, so
      genuine size is drowned. Block prints are separated out.
  H3  the comparison was wrong. Absorption is supposed to matter at extremes,
      not everywhere -- price making a new local high on falling CVD is the
      textbook divergence and was never isolated.

H0 runs first and is the one that matters most: plain price autocorrelation at
every horizon. If NOTHING predicts the next N minutes, no amount of order flow
cleverness will, and the honest answer is that this sample has no edge in it.

Every test enters at a window close on information available at that instant.
Roughly twenty hypotheses are run, so the bar for calling anything real is
|t| >= 3.0, not 2.0, and it must hold with the same sign on both days.

Usage: python3 scripts/sweep_tape.py
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from tape import load_all, rth

POINT_USD = 20.0
COST_PTS = 2.0
BAR_T = 3.0          # Bonferroni-ish bar for ~20 hypotheses


def stat(x, cost=0.0):
    x = np.asarray([v for v in x if np.isfinite(v)], float)
    if len(x) < 25:
        return None
    x = x - cost
    sd = x.std(ddof=1)
    t = x.mean() / (sd / np.sqrt(len(x))) if sd > 0 else 0.0
    return dict(n=len(x), mean=x.mean(), t=t, win=100 * (x > 0).mean())


def show(label, r, mark=True):
    if r is None:
        print(f"  {label:<40} too few")
        return
    star = " **" if (mark and abs(r["t"]) >= BAR_T) else ""
    print(f"  {label:<40} n={r['n']:<5} {r['mean']:+6.2f}pt "
          f"{r['mean']*POINT_USD:+8.0f}$  win {r['win']:3.0f}%  "
          f"t={r['t']:+5.2f}{star}")


def windows(s, secs):
    g = s.set_index("time").resample(f"{secs}s")
    w = pd.DataFrame({
        "vol": g.volume.sum(), "delta": g.signed.sum(),
        "first": g.price.first(), "last": g.price.last(),
        "n": g.price.count(),
    }).dropna(subset=["last"])
    w = w[w.n > 0].copy()
    w["move"] = w["last"] - w["first"]
    return w


def block_windows(s, secs, q):
    """Same windows, but delta computed only from prints at or above size q."""
    thr = s.volume.quantile(q)
    b = s[s.volume >= thr]
    g = b.set_index("time").resample(f"{secs}s")
    bd = g.signed.sum().rename("bdelta")
    bv = g.volume.sum().rename("bvol")
    return pd.concat([bd, bv], axis=1), thr


def main():
    days = {d: rth(df) for d, df in sorted(load_all().items())}
    days = {d: s for d, s in days.items() if len(s) > 5000}
    names = list(days)

    print("=" * 88)
    print("SWEEP OVER THE RECORDED TAPE")
    print(f"{len(days)} RTH sessions: {', '.join(names)}   "
          f"cost {COST_PTS} pts   bar for significance |t| >= {BAR_T}")
    print("=" * 88)

    print("\nHOW SELECTIVE WAS THE 'NO PROGRESS' FILTER?")
    print("  On a 5-point grid a flat window may be the common case, in which")
    print("  case the filter selected nothing in particular.\n")
    for d, s in days.items():
        w = windows(s, 30)
        print(f"  {d}  |move| <= 5pt on {100*(w['move'].abs() <= 5).mean():.0f}% "
              f"of 30s windows;  move == 0 on {100*(w['move'] == 0).mean():.0f}%")

    # ---------------------------------------------------------------- H0
    print("\n" + "=" * 88)
    print("H0  IS THERE ANY LINEAR PREDICTABILITY AT ALL?")
    print("=" * 88)
    print("  Sign of the last window's move, held forward. Momentum if positive,")
    print("  mean reversion if negative, nothing if flat.\n")
    for secs in (30, 60, 300):
        for k in (1, 2, 4):
            rows = []
            for s in days.values():
                w = windows(s, secs)
                f = w["last"].shift(-k) - w["last"]
                sgn = np.sign(w["move"])
                rows.append((sgn * f).values)
            show(f"{secs:>4}s window, hold {secs*k//60 or secs}"
                 f"{'m' if secs*k >= 60 else 's'}",
                 stat(np.concatenate(rows)))

    # ---------------------------------------------------------------- H1
    print("\n" + "=" * 88)
    print("H1  ABSORPTION AT LONGER HORIZONS")
    print("=" * 88)
    print("  Heavy buying (top 20% delta) that did not move price, held longer.\n")
    for secs in (30, 60):
        for hold_s in (120, 300, 600, 1800):
            k = max(1, hold_s // secs)
            rows_d, per_day = [], []
            for s in days.values():
                w = windows(s, secs)
                f = w["last"].shift(-k) - w["last"]
                sel = (w.delta >= w.delta.quantile(0.80)) & (w["move"].abs() <= 5)
                v = (-f[sel]).values
                rows_d.append(v)
                per_day.append(np.nanmean(v) if len(v) else np.nan)
            agree = "both days same sign" if (
                np.nanprod(per_day) > 0) else "days disagree"
            show(f"{secs}s win, hold {hold_s//60}m  [{agree}]",
                 stat(np.concatenate(rows_d), COST_PTS))

    # ---------------------------------------------------------------- H2
    print("\n" + "=" * 88)
    print("H2  BLOCK PRINTS — is size informative where count is not?")
    print("=" * 88)
    for d, s in days.items():
        for q in (0.99, 0.999):
            thr = s.volume.quantile(q)
            b = s[s.volume >= thr]
            print(f"  {d}  top {100*(1-q):.1f}%: size >= {thr:.0f}, "
                  f"{len(b):,} prints, {100*b.volume.sum()/s.volume.sum():.0f}% "
                  f"of volume")
    print()
    for q in (0.99, 0.999):
        for hold_s in (120, 600):
            k = hold_s // 30
            go, fade, per_day = [], [], []
            for s in days.values():
                w = windows(s, 30)
                bw, _ = block_windows(s, 30, q)
                w = w.join(bw).fillna({"bdelta": 0.0, "bvol": 0.0})
                f = w["last"].shift(-k) - w["last"]
                hot = w.bdelta.abs() >= w.bdelta.abs().quantile(0.90)
                sgn = np.sign(w.bdelta)
                go.append((sgn * f)[hot & (sgn != 0)].values)
                fade.append((-sgn * f)[hot & (sgn != 0)].values)
                per_day.append(np.nanmean((sgn * f)[hot & (sgn != 0)].values))
            agree = "agree" if np.nanprod(per_day) > 0 else "disagree"
            show(f"blocks q{q} go-with, hold {hold_s//60}m [{agree}]",
                 stat(np.concatenate(go), COST_PTS))
            show(f"blocks q{q} fade,    hold {hold_s//60}m",
                 stat(np.concatenate(fade), COST_PTS))

    # ---------------------------------------------------------------- H3
    print("\n" + "=" * 88)
    print("H3  CVD DIVERGENCE AT LOCAL EXTREMES")
    print("=" * 88)
    print("  Price makes a new high over the lookback while cumulative delta")
    print("  does not confirm it. The classic read, isolated at last.\n")
    for look_m in (15, 30, 60):
        for hold_s in (300, 900):
            k = hold_s // 30
            L = look_m * 2          # windows of 30s in the lookback
            rows, per_day = [], []
            for s in days.values():
                w = windows(s, 30)
                w["cvd"] = w.delta.cumsum()
                f = w["last"].shift(-k) - w["last"]
                ph = w["last"].rolling(L).max()
                ch = w["cvd"].rolling(L).max()
                new_hi = w["last"] >= ph
                cvd_lags = w["cvd"] < ch
                short = new_hi & cvd_lags
                pl = w["last"].rolling(L).min()
                cl = w["cvd"].rolling(L).min()
                long_ = (w["last"] <= pl) & (w["cvd"] > cl)
                v = np.concatenate([(-f[short]).values, (f[long_]).values])
                rows.append(v)
                per_day.append(np.nanmean(v) if len(v) else np.nan)
            agree = "agree" if np.nanprod(per_day) > 0 else "disagree"
            show(f"divergence {look_m}m look, hold {hold_s//60}m [{agree}]",
                 stat(np.concatenate(rows), COST_PTS))

    print("\n" + "=" * 88)
    print("Anything marked ** cleared the multiple-testing bar on both counts.")
    print("=" * 88)


if __name__ == "__main__":
    main()
