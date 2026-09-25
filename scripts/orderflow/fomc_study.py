#!/usr/bin/env python3
"""FOMC FAMILY — STAGE 1, DESCRIPTIVE ONLY. Pre-registered at `a306378`.

No expectancy, no win rate, no verdict. No rule is run or imported.
20 tests = 4 categories x 5 statistics. Bonferroni alpha = 0.0025.
2016-2020 stays sealed: reads only QQQ_1m.parquet, which begins 2021.
"""
from __future__ import annotations
import sys
from math import erfc, sqrt
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fomc_classify import CATS, STATS, load                          # noqa

N_TESTS, N_RAND = 20, 1000
P_BAR = 0.05 / N_TESTS
RNG = np.random.default_rng(23)
NICE = {"rv_pre": "rv pre (bps)", "rv_post": "rv post (bps)",
        "rv_ratio": "post/pre ratio", "eff_post": "efficiency post",
        "or_ratio": "OR ratio"}


def welch(a, b):
    a, b = a.dropna(), b.dropna()
    if len(a) < 3 or len(b) < 3:
        return np.nan, np.nan
    va, vb = a.var(ddof=1)/len(a), b.var(ddof=1)/len(b)
    if va + vb <= 0:
        return np.nan, np.nan
    t = (a.mean()-b.mean())/sqrt(va+vb)
    return t, erfc(abs(t)/sqrt(2))


def main():
    F, n_csv, n_used = load()
    C = F[F.control]
    print("=" * 104)
    print("  FOMC FAMILY — STAGE 1, DESCRIPTIVE ONLY")
    print("=" * 104)
    print(f"  {n_csv} FOMC dates supplied, {n_used} inside the price sample.")
    print(f"  sessions {len(F):,}   control (non-FOMC, non-day-after) "
          f"{len(C):,}   {N_TESTS} tests, alpha {P_BAR:.5f}")
    print("  windows: pre = 09:30-14:00 (statement at 14:00), "
          "post = 14:00-16:00")
    print("  CONTROL IS CONTAMINATED: ~10% of it is CPI/NFP days, because "
          "those dates are")
    print("  unobtainable here. That biases TOWARD finding nothing.")

    print("\n" + "=" * 104)
    print("  RESULTS — each category against the same control")
    print("=" * 104)
    rows = []
    for lab, col in CATS:
        A = F[F[col]]
        print(f"\n  {lab}   (n {len(A)} vs control {len(C)})")
        print(f"    {'statistic':<18}{'category':>11}{'control':>11}"
              f"{'diff':>10}{'ratio':>8}{'t':>8}{'p':>11}{'':>6}")
        for s in STATS:
            t, p = welch(A[s], B := C[s])
            d = A[s].mean() - B.mean()
            rt = A[s].mean()/B.mean() if B.mean() else np.nan
            sig = "PASS" if (np.isfinite(p) and p < P_BAR) else ""
            rows.append(dict(category=lab, stat=s, n=len(A), a=A[s].mean(),
                             b=B.mean(), diff=d, ratio=rt, t=t, p=p,
                             passes=bool(sig)))
            print(f"    {NICE[s]:<18}{A[s].mean():>11.4f}{B.mean():>11.4f}"
                  f"{d:>+10.4f}{rt:>8.2f}{t:>+8.2f}{p:>11.2e}{sig:>6}")
    R = pd.DataFrame(rows)

    print("\n" + "=" * 104)
    print("  VOLUME SHARE AFTER 14:00")
    print("=" * 104)
    print(f"  {'group':<22}{'vol% post-14:00':>18}")
    print(f"  {'control':<22}{C.volshare_post.mean():>18.1f}")
    for lab, col in CATS:
        print(f"  {lab:<22}{F[F[col]].volshare_post.mean():>18.1f}")

    print("\n" + "=" * 104)
    print(f"  CONTROL — {N_RAND:,} RANDOM LABELS PER CATEGORY, SIZES MATCHED")
    print("=" * 104)
    print(f"  {'category':<20}{'statistic':<18}{'real diff':>11}"
          f"{'rand |diff| 95th':>18}{'percentile':>12}{'':>8}")
    crows = []
    for lab, col in CATS:
        n_a = int(F[col].sum())
        pool = F[F[col] | F.control]
        for s in STATS:
            v = pool[s].to_numpy(float); v = v[np.isfinite(v)]
            real = R[(R.category == lab) & (R.stat == s)].iloc[0]["diff"]
            ds = np.empty(N_RAND)
            for i in range(N_RAND):
                ix = RNG.permutation(len(v))
                ds[i] = v[ix[:n_a]].mean() - v[ix[n_a:]].mean()
            p95 = np.percentile(np.abs(ds), 95)
            pc = 100.0*(np.abs(ds) < abs(real)).mean()
            crows.append(dict(category=lab, stat=s, real=real, p95=p95,
                              pct=pc, beats=abs(real) > p95))
            print(f"  {lab:<20}{NICE[s]:<18}{real:>+11.4f}{p95:>18.4f}"
                  f"{pc:>11.1f}%{'BEATS' if abs(real) > p95 else '':>8}")
    K = pd.DataFrame(crows)

    print("\n" + "=" * 104)
    print("  BY YEAR — FOMC decision day, post-window rv vs that year's control")
    print("=" * 104)
    print(f"  {'year':<8}{'n':>4}{'FOMC rv_post':>15}{'control rv_post':>18}"
          f"{'ratio':>9}")
    hold = 0
    for y in sorted(F.year.unique()):
        a = F[(F.fomc) & (F.year == y)].rv_post
        b = F[(F.control) & (F.year == y)].rv_post
        r = a.mean()/b.mean() if b.mean() else np.nan
        if np.isfinite(r) and r > 1:
            hold += 1
        print(f"  {y:<8}{len(a):>4}{a.mean():>15.2f}{b.mean():>18.2f}{r:>9.2f}")
    print(f"  higher on FOMC day in {hold} of {len(F.year.unique())} years")

    print("\n" + "=" * 104)
    print("  VERDICT")
    print("=" * 104)
    print(f"  clearing Bonferroni (p < {P_BAR:.5f}):       "
          f"{int(R.passes.sum())} of {len(R)}")
    print(f"  beating 95th pct of random labels:      "
          f"{int(K.beats.sum())} of {len(K)}   "
          f"(expected by chance: {0.05*len(K):.1f})")
    both = [(r["category"], r["stat"]) for _, r in K[K.beats].iterrows()
            if R[(R.category == r["category"]) & (R.stat == r["stat"])].iloc[0]["passes"]]
    if both:
        print("\n  CLEARING BOTH:")
        for c, s in both:
            m = R[(R.category == c) & (R.stat == s)].iloc[0]
            k = K[(K.category == c) & (K.stat == s)].iloc[0]
            print(f"    {c:<20}{NICE[s]:<18}{m['a']:>9.3f} vs {m['b']:>8.3f}"
                  f"   x{m['ratio']:.2f}   p {m['p']:.2e}   "
                  f"{k['pct']:.1f}th pct")
    else:
        print("\n  NOTHING CLEARS BOTH.")
    print("\n  No performance test was run. 2016-2020 remains sealed.")


if __name__ == "__main__":
    main()
