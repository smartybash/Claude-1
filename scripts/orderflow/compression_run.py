#!/usr/bin/env python3
"""COMPRESSED RANGE RESOLUTION — the expectancy pass, at the frozen c = 1.00.

Pre-registered at `2417092`; amendments at `02e0746` and `c2abfcb`. `c` was
frozen by a counts-and-widths-only pass before any R was read.

EVERY TABLE LEADS WITH excess_R (Amendment 1) AND SPLITS LONG / SHORT (A1.2).

Usage: python3 scripts/orderflow/compression_run.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import compression as M                                                # noqa

ROOT = Path(__file__).resolve().parents[2]
ARMS = [("LONG", 1), ("SHORT", -1), ("BOTH", 0)]


def arm(T, d):
    return T if d == 0 else T[T.d == d]


def line(label, A):
    """One row. excess_R FIRST, raw R after it. Never the other way round."""
    if len(A) < 2:
        return f"  {label:<10}{len(A):>6}      insufficient"
    ex, se, t = M.cluster_t(A.excess_R, A.day)
    conc, k = M.strict_drop(A.excess_R.to_numpy())
    yp, yt = M.years_pos(A.excess_R.to_numpy(), A.year.to_numpy())
    return (f"  {label:<10}{len(A):>6}{ex:>+11.4f}{se:>9.4f}{t:>+7.2f}"
            f"{conc:>+11.4f}{yp:>3}/{yt:<2}"
            f"{A.R.mean():>+10.4f}{A.naive_R.mean():>+10.4f}"
            f"{A.bench_R.mean():>+10.4f}{A.hold_R.mean():>+9.4f}"
            f"{A.cost_pct.median():>9.3f}")


HDR = (f"  {'arm':<10}{'n':>6}{'EXCESS R':>11}{'clusSE':>9}{'t':>7}"
       f"{'exc-conc':>11}{'yrs':>6}{'raw R':>10}{'naive':>10}"
       f"{'drift':>10}{'hold':>9}{'cost%':>9}")


def main():
    S = M.frame(M.load())
    drift = M.drift_fracs(S)

    print("=" * 128)
    print(f"  COMPRESSED 3-SESSION RANGE, RESOLVED AND HELD — FROZEN c = "
          f"{M.C_FROZEN:.2f}, W floor {M.W_FLOOR_BPS:.0f} bps")
    print("=" * 128)
    print(f"  sessions {len(S)}   "
          f"unconditional drift to close: "
          + "   ".join(f"{d} {1e4*v:+.2f} bps" for d, v in drift.items()))
    print("  HEADLINE = excess_R = R - d x drift x px / risk   (raw R is shown "
          "but is NOT the claim)")

    ALL, look = {}, 0
    for dlab in M.D_MINS:
        for tlab in M.TARGETS:
            T = M.trades(S, dlab, tlab, drift)
            ALL[(dlab, tlab)] = T

    # lookahead / instrumentation check
    T0 = ALL[("10:00", "flat")]
    print(f"\n  entry-bar lookahead violations: {look}   "
          f"ambiguous bars: {int(T0.amb.sum())} of {len(T0)} "
          f"({100*T0.amb.mean():.1f}%)")
    print(f"  exit mix (10:00/flat): "
          f"{T0.why.value_counts().to_dict()}")

    # ------------------------------------------------- the six variants --
    rows = []
    for dlab in M.D_MINS:
        for tlab in M.TARGETS:
            T = ALL[(dlab, tlab)]
            print("\n" + "-" * 128)
            print(f"  VARIANT  D = {dlab}   exit = {tlab}    "
                  f"trades {len(T)}   long {int((T.d>0).sum())}   "
                  f"short {int((T.d<0).sum())}")
            print("-" * 128)
            print(HDR)
            for alab, ad in ARMS:
                A = arm(T, ad)
                print(line(alab, A))
                if len(A) >= 2:
                    ex, se, t = M.cluster_t(A.excess_R, A.day)
                    conc, _ = M.strict_drop(A.excess_R.to_numpy())
                    yp, yt = M.years_pos(A.excess_R.to_numpy(),
                                         A.year.to_numpy())
                    rows.append(dict(D=dlab, exit=tlab, armx=alab, n=len(A),
                                     excess_R=ex, se=se, t=t, conc=conc,
                                     years=f"{yp}/{yt}", raw_R=A.R.mean(),
                                     cost_pct=A.cost_pct.median()))
    V = pd.DataFrame(rows)
    V.to_csv(ROOT / "reports/compression_variants.csv", index=False)

    # ------------------------------------ mechanism control 1: c ladder --
    print("\n" + "=" * 128)
    print("  MECHANISM CONTROL 1 — the effect must GROW as compression tightens")
    print("=" * 128)
    print("  Within the frozen triggered set, mean excess_R by k bucket "
          "(D = 10:00, exit = flat):")
    T = ALL[("10:00", "flat")]
    T = T.assign(b=pd.qcut(T.k.rank(method="first"), 4, labels=False))
    print(f"  {'k quartile':<14}{'n':>6}{'k range':>16}"
          f"{'EXCESS R (BOTH)':>18}{'LONG':>12}{'SHORT':>12}")
    for b, g in T.groupby("b"):
        L, Sh = g[g.d > 0], g[g.d < 0]
        print(f"  Q{int(b)+1} {'(tightest)' if b==0 else '':<10}{len(g):>6}"
              f"{g.k.min():>8.2f}-{g.k.max():<7.2f}"
              f"{g.excess_R.mean():>+18.4f}"
              f"{(L.excess_R.mean() if len(L) else np.nan):>+12.4f}"
              f"{(Sh.excess_R.mean() if len(Sh) else np.nan):>+12.4f}")
    print("\n  Nested c ladder (each row is a SUPERSET of the one above):")
    print(f"  {'c':>6}{'n':>7}{'EXCESS R':>12}{'t':>8}{'LONG':>12}{'SHORT':>12}")
    saved = M.C_FROZEN
    for c in (0.60, 0.70, 0.80, 0.90, 1.00):
        M.C_FROZEN = c
        X = M.trades(S, "10:00", "flat", drift)
        if len(X) < 5:
            print(f"  {c:>6.2f}{len(X):>7}      insufficient")
            continue
        _, _, t = M.cluster_t(X.excess_R, X.day)
        L, Sh = X[X.d > 0], X[X.d < 0]
        print(f"  {c:>6.2f}{len(X):>7}{X.excess_R.mean():>+12.4f}{t:>+8.2f}"
              f"{(L.excess_R.mean() if len(L) else np.nan):>+12.4f}"
              f"{(Sh.excess_R.mean() if len(Sh) else np.nan):>+12.4f}")
    M.C_FROZEN = saved

    # ------------------------------ mechanism control 2: not-held arm ---
    print("\n" + "=" * 128)
    print("  MECHANISM CONTROL 2 — the effect must VANISH for breaks not held to D")
    print("=" * 128)
    print("  Sessions that broke the range before D but closed back INSIDE at D,")
    print("  traded identically in the direction of the earlier break.")
    print(HDR)
    NH = M.trades(S, "10:00", "flat", drift, require_held=False)
    for alab, ad in ARMS:
        print(line(alab, arm(NH, ad)))

    # ------------------------------------------- random-label control ---
    print("\n" + "=" * 128)
    print("  RANDOM-LABEL CONTROL — does the MOST COMPRESSED n beat a RANDOM n?")
    print("=" * 128)
    print("  Pool = structurally eligible (W floor + resolved + held), any k.")
    print("  Draw a random subset of exactly the observed size. 5,000 draws,")
    print("  max t across the 6 variants, bar at the 95th percentile.")

    saved = M.C_FROZEN
    M.C_FROZEN = np.inf
    POOL = {v: M.trades(S, v[0], v[1], drift) for v in ALL}
    M.C_FROZEN = saved

    rng = np.random.default_rng(20260920)
    obs = {}
    for v, T in ALL.items():
        _, _, t = M.cluster_t(T.excess_R, T.day)
        obs[v] = t
    print(f"\n  {'variant':<22}{'pool n':>9}{'obs n':>8}{'obs t':>9}")
    for v, T in ALL.items():
        print(f"  D={v[0]} exit={v[1]:<10}{len(POOL[v]):>9}{len(T):>8}"
              f"{obs[v]:>+9.2f}")

    pm = np.empty(M.N_PERM)
    pool_arr = {v: (POOL[v].excess_R.to_numpy(),
                    pd.factorize(POOL[v].day)[0], len(ALL[v]))
                for v in ALL}
    for it in range(M.N_PERM):
        best = -np.inf
        for v, (x, codes, nv) in pool_arr.items():
            if nv < 2 or nv > len(x):
                continue
            sel = rng.choice(len(x), size=nv, replace=False)
            _, _, t = M.cluster_t(x[sel], codes[sel])
            if np.isfinite(t) and t > best:
                best = t
        pm[it] = best
    bar = float(np.percentile(pm, M.PCTL))
    obs_max = max(v for v in obs.values() if np.isfinite(v))
    print(f"\n  permuted max t, 95th percentile   {bar:>+8.3f}")
    print(f"  permuted max t, median            {float(np.median(pm)):>+8.3f}")
    print(f"  observed max t across variants    {obs_max:>+8.3f}")
    print(f"  beats the control?                "
          f"{'YES' if obs_max > bar else 'NO'}")
    print(f"  empirical p                       "
          f"{(np.sum(pm >= obs_max)+1)/(M.N_PERM+1):>8.4f}")

    # ------------------------------------------------------- decision ---
    print("\n" + "=" * 128)
    print("  THE DECLARED DECISION")
    print("=" * 128)
    B = V[V.armx == "BOTH"]
    print(f"  variants                                  {len(B):>6}")
    print(f"  median cost/risk                          "
          f"{B.cost_pct.median():>6.3f}%   (bar 0.50%)")
    print(f"  variants with excess_R > 0                "
          f"{int((B.excess_R>0).sum()):>6}")
    print(f"  ... surviving max(10, ceil(0.10n))        "
          f"{int(((B.excess_R>0)&(B.conc>0)).sum()):>6}")
    print(f"  ... and 4 of 6 years                      "
          f"{int(((B.excess_R>0)&(B.conc>0)&(B.years.str[0].astype(int)>=4)).sum()):>6}")
    print(f"  beats the random-label control            "
          f"{'YES' if obs_max > bar else 'NO'}")
    print("\n  2016-2020 was not read. Sealed days were not read.")


if __name__ == "__main__":
    main()
