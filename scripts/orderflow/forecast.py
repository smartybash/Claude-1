#!/usr/bin/env python3
"""WHAT DO THE RECENT BARS IMPLY ABOUT THE NEXT FIFTEEN MINUTES?

The indicator is supposed to end up saying what happens next, so this asks
whether that can be said at all, and how loudly.

Two combinations are tested, and the difference between them is the whole
point:

  FIXED    the features that showed real IC, standardised and added with
           their signs fixed in advance by direction. Nothing is fitted, so
           there is nothing to overfit.
  FITTED   a least-squares combination of the same features.

Both are scored LEAVE-ONE-SESSION-OUT: the score for a session is produced
without that session in the fit. In-sample numbers are printed beside them so
the shrinkage is visible, because the gap between the two is what a backtest
usually hides.

Every number is then converted into POINTS AFTER COST. That conversion is the
lesson of this project: vwap displacement scored IC -0.295 with t = -9.21 and
paid +0.08 points a trade. A correlation says the ordering is right, not that
it covers the spread.

Usage: python3 scripts/orderflow/forecast.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ic_harness import features, spearman                                 # noqa
from tape import load_all, rth                                            # noqa

HORIZON = 15
COST_PTS = 2.0

# Chosen from the IC table BEFORE anything is fitted here, and signed so that
# a positive score means "expect the price to go up". Every one of them was
# negative against forward returns -- high displacement and heavy cumulative
# delta both preceded lower prices -- so the sign is flipped to make the score
# read the natural way.
FEATURES = {
    "vwap_disp": -1.0,
    "cvd_share": -1.0,
    "divergence5": -1.0,
    "poc_shift": -1.0,
    "dshare5": +1.0,
}


def build():
    full = load_all()
    days = {d: rth(x) for d, x in sorted(full.items())}
    days = {d: s for d, s in days.items() if len(s) > 5000}
    out = []
    for d, s in days.items():
        f = features(s)
        if f is None:
            continue
        px = s.set_index("time").resample("1min").price.last().reindex(f.index)
        f = f.assign(day=d, px=px)
        out.append(f)
    F = pd.concat(out)
    F["fwd_pts"] = F[f"fwd{HORIZON}"] * F.px
    keep = list(FEATURES) + ["day", "px", "fwd_pts"]
    return F[keep].replace([np.inf, -np.inf], np.nan).dropna()


def zscore_within(F, cols, expanding=True):
    """Standardise each feature against the session SO FAR.

    Across sessions the same raw value means different things -- a two-point
    VWAP displacement is large on a quiet day and nothing on a volatile one --
    so some within-session scaling is needed.

    It must be EXPANDING. Standardising against the whole session uses that
    day's closing mean and standard deviation, which at 10:00 have not
    happened yet. That is lookahead, and it is not subtle: with the full-day
    version this model scored IC +0.36 out of sample and +11.52 points a
    trade, against +0.08 points for the same feature ranked globally. The
    entire difference was knowing the day's statistics in advance.

    expanding=False reproduces the broken version, kept so the size of the
    bias stays visible rather than becoming folklore.
    """
    Z = F.copy()
    for c in cols:
        g = F.groupby("day")[c]
        if expanding:
            mu = g.transform(lambda x: x.expanding(min_periods=30).mean())
            sd = g.transform(lambda x: x.expanding(min_periods=30).std())
        else:
            mu, sd = g.transform("mean"), g.transform("std")
        Z[c] = (F[c] - mu) / sd.replace(0, np.nan)
    return Z.dropna(subset=cols)


def report(name, score, y, day, px):
    ic = []
    for d in day.unique():
        m = day == d
        if m.sum() > 50:
            v = spearman(score[m].to_numpy(), y[m].to_numpy())
            if np.isfinite(v):
                ic.append(v)
    ic = np.array(ic)
    t = ic.mean() / (ic.std(ddof=1) / np.sqrt(len(ic))) if len(ic) > 2 else 0.0

    # trade the extremes: long the top fifth, short the bottom fifth
    q = pd.qcut(score.rank(method="first"), 5, labels=False)
    top, bot = q == 4, q == 0
    pts = np.concatenate([y[top].to_numpy(), -y[bot].to_numpy()]) - COST_PTS
    dd = np.concatenate([day[top].to_numpy(), day[bot].to_numpy()])
    per = pd.Series(pts).groupby(dd).mean()
    tt = per.mean() / (per.std(ddof=1) / np.sqrt(len(per))) if len(per) > 2 else 0.0
    print(f"  {name:<28} IC {ic.mean():+.4f} (t {t:+5.2f})   "
          f"trade {pts.mean():+6.2f} pts  win {100*(pts > 0).mean():4.1f}%  "
          f"t {tt:+5.2f}  n={len(pts):,}")
    return pts.mean(), tt


def main():
    F = build()
    cols = list(FEATURES)
    Z = zscore_within(F, cols)
    print("=" * 98)
    print(f"FORECASTING THE NEXT {HORIZON} MINUTES — {Z.day.nunique()} sessions, "
          f"{len(Z):,} bars")
    print("=" * 98)
    print("  Features are standardised against the session SO FAR -- an")
    print("  expanding window, which is all a live indicator can see. Trades")
    print("  take the top and bottom fifth of the score, net of 2 points.\n")

    y, day, px = Z.fwd_pts, Z.day, Z.px

    print("  --- FIXED: signs set in advance, nothing fitted ---")
    fixed = sum(Z[c] * w for c, w in FEATURES.items()) / len(FEATURES)
    report("fixed blend", fixed, y, day, px)

    print("\n  --- FITTED: least squares, in sample vs leave-one-session-out ---")
    X = Z[cols].to_numpy()
    yy = y.to_numpy()
    A = np.column_stack([X, np.ones(len(X))])
    beta, *_ = np.linalg.lstsq(A, yy, rcond=None)
    report("fitted, IN SAMPLE", pd.Series(A @ beta, index=Z.index), y, day, px)

    oos = pd.Series(index=Z.index, dtype=float)
    for d in Z.day.unique():
        tr = (Z.day != d).to_numpy()
        te = ~tr
        b, *_ = np.linalg.lstsq(A[tr], yy[tr], rcond=None)
        oos[te] = A[te] @ b
    report("fitted, OUT OF SAMPLE", oos, y, day, px)

    print("\n  --- each feature alone, for reference ---")
    for c, w in FEATURES.items():
        report(c, Z[c] * w, y, day, px)

    print("\n" + "=" * 98)
    print("WHAT A LIVE INDICATOR COULD HONESTLY SAY")
    print("=" * 98)
    q = pd.qcut(fixed.rank(method="first"), 5, labels=False)
    print(f"  Using the fixed blend, by quintile of the score:\n")
    print(f"    {'quintile':<12}{'median move':>14}{'up rate':>10}"
          f"{'mean':>10}{'bars':>9}")
    for i in sorted(pd.Series(q).dropna().unique()):
        m = q == i
        print(f"    {int(i):<12}{y[m].median():>+13.1f}p{100*(y[m] > 0).mean():>9.0f}%"
              f"{y[m].mean():>+10.1f}{int(m.sum()):>9,}")
    print()
    print("  That column of up-rates is the honest output: a lean, not a call.")
    print("  If the extremes sit near 50% the indicator should say so rather")
    print("  than dress it as a signal.")

    print("\n" + "=" * 98)
    print("HOW MUCH OF THIS WAS LOOKAHEAD?")
    print("=" * 98)
    print("  The same model standardised against the FULL session instead of")
    print("  the session so far -- i.e. knowing the day's mean and standard")
    print("  deviation in advance. The gap is the bias, not an improvement.\n")
    B = zscore_within(F, cols, expanding=False)
    fb = sum(B[c] * w for c, w in FEATURES.items()) / len(FEATURES)
    report("fixed blend, FULL-SESSION z", fb, B.fwd_pts, B.day, B.px)


if __name__ == "__main__":
    main()
