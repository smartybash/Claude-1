#!/usr/bin/env python3
"""CALENDAR SESSION CLASSIFICATION — STAGE 1, DESCRIPTIVE ONLY.

Pre-registered at `c147285`
(`reports/calendar_classification_preregistration.md`) before this ran.

NO EXPECTANCY. NO WIN RATE. NO VERDICT ON ANY RULE. No trade is generated and
no performance measure is computed anywhere in this file -- there is no rule
imported and nothing to compute one from.

WHAT IS BEING ASKED

Every hypothesis before this lacked a mechanism. A calendar label identifies
participants with an OBLIGATION to trade rather than a choice, and the label is
knowable years in advance, so nothing has to be forecast. Stage 1 asks only
whether the label separates session CHARACTER.

THE SCHEDULED-EVENTS FAMILY IS ABSENT AND THAT IS DELIBERATE

FOMC / CPI / NFP need real release dates. The repo has none, FMP's
economics-calendar is denied on this plan, and Alpha Vantage's series are keyed
by reference month, not release date (verified). Deriving them from memory would
mislabel enough sessions to contaminate both category and control, so the family
is reported as blocked rather than faked.

52 TESTS: 13 categories x 4 statistics. Bonferroni alpha = 0.000962.
Quarterly expiry (n=22) can only detect a volatility effect of ~half the sample
mean; its null is UNDERPOWERED, not negative. Declared in advance.

2016-2020 stays sealed: this script reads only QQQ_1m.parquet, which starts 2021.

Usage: python3 scripts/orderflow/calendar_session_study.py
"""
from __future__ import annotations

import sys
from math import erfc, sqrt
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from calendar_classify import CATS, ROOT, STATS, WINDOWS, load       # noqa

N_TESTS = 52
P_BAR = 0.05 / N_TESTS
N_RAND = 1000
RNG = np.random.default_rng(11)

NICE = {"rv_bps": "realised vol bps", "range_bps": "range bps",
        "eff": "efficiency", "or_ratio": "OR ratio"}


def welch(a, b):
    a, b = a.dropna(), b.dropna()
    if len(a) < 3 or len(b) < 3:
        return np.nan, np.nan
    va, vb = a.var(ddof=1) / len(a), b.var(ddof=1) / len(b)
    if va + vb <= 0:
        return np.nan, np.nan
    t = (a.mean() - b.mean()) / sqrt(va + vb)
    return t, erfc(abs(t) / sqrt(2))


def main():
    M = load()
    print("=" * 112)
    print("  CALENDAR SESSION CLASSIFICATION — STAGE 1, DESCRIPTIVE ONLY")
    print("=" * 112)
    print("  No expectancy, no win rate, no verdict. No rule is run and none "
          "is imported.")
    print(f"  {len(CATS)} categories x {len(STATS)} statistics = {N_TESTS} "
          f"tests   Bonferroni alpha = {P_BAR:.6f}")
    print("\n  BLOCKED: the scheduled-events family (FOMC / CPI / NFP). Real "
          "release dates are")
    print("  unavailable — repo has none, FMP's calendar is denied on this "
          "plan, and Alpha Vantage's")
    print("  series are keyed by reference month, not release date. Not "
          "derived from memory.")

    print(f"\n  sessions {len(M):,}   {M.day.min()} .. {M.day.max()}")

    print("\n" + "=" * 112)
    print("  COUNTS FIRST")
    print("=" * 112)
    print(f"  {'category':<24}{'n':>6}{'control n':>11}{'MDE rv bps':>13}"
          f"{'as % of mean':>14}   note")
    mu_rv, sd_rv = M.rv_bps.mean(), M.rv_bps.std(ddof=1)
    mult = 4.143                      # (z_alpha/2 + z_beta) at the declared bar
    for label, col, ctrl in CATS:
        a = int(M[col].sum())
        b = int(M[ctrl].sum()) if ctrl else int((~M[col]).sum())
        mde = mult * sd_rv * sqrt(1 / a + 1 / b)
        note = "UNDERPOWERED" if 100 * mde / mu_rv > 40 else ""
        print(f"  {label:<24}{a:>6,}{b:>11,}{mde:>13.1f}"
              f"{100*mde/mu_rv:>13.0f}%   {note}")

    print("\n" + "=" * 112)
    print("  EACH CATEGORY AGAINST ITS CONTROL — real means, side by side")
    print("=" * 112)
    rows = []
    for label, col, ctrl in CATS:
        A = M[M[col]]
        B = M[M[ctrl]] if ctrl else M[~M[col]]
        print(f"\n  {label}   (n {len(A):,} vs control {len(B):,}"
              + (f", control = {ctrl}" if ctrl else ", control = all others")
              + ")")
        print(f"    {'statistic':<18}{'category':>11}{'control':>11}"
              f"{'diff':>10}{'Welch t':>10}{'p':>11}{'':>6}")
        for s in STATS:
            t, p = welch(A[s], B[s])
            d = A[s].mean() - B[s].mean()
            sig = "PASS" if (np.isfinite(p) and p < P_BAR) else ""
            rows.append(dict(category=label, stat=s, n=len(A), nctrl=len(B),
                             a=A[s].mean(), b=B[s].mean(), diff=d, t=t, p=p,
                             passes=bool(sig)))
            print(f"    {NICE[s]:<18}{A[s].mean():>11.4f}{B[s].mean():>11.4f}"
                  f"{d:>+10.4f}{t:>+10.2f}{p:>11.2e}{sig:>6}")

    R = pd.DataFrame(rows)

    print("\n" + "=" * 112)
    print("  INTRADAY DISTRIBUTION — where the session's volume and movement "
          "actually sit")
    print("=" * 112)
    print("  The mechanism claims flow concentrates at a known time. A whole-"
          "session statistic would")
    print("  average that away, so each window is shown separately.\n")
    wn = list(WINDOWS)
    print(f"  {'category':<24}" + "".join(f"{'vol% ' + w:>13}" for w in wn)
          + "".join(f"{'rv ' + w:>12}" for w in wn))
    base = M
    print(f"  {'ALL SESSIONS':<24}"
          + "".join(f"{base['volshare_'+w].mean():>13.1f}" for w in wn)
          + "".join(f"{base['rv_'+w].mean():>12.1f}" for w in wn))
    for label, col, ctrl in CATS:
        A = M[M[col]]
        print(f"  {label:<24}"
              + "".join(f"{A['volshare_'+w].mean():>13.1f}" for w in wn)
              + "".join(f"{A['rv_'+w].mean():>12.1f}" for w in wn))

    print("\n" + "=" * 112)
    print(f"  THE CONTROL — {N_RAND:,} RANDOM LABEL ASSIGNMENTS PER CATEGORY, "
          f"GROUP SIZES MATCHED")
    print("=" * 112)
    print(f"  {'category':<24}{'statistic':<18}{'real diff':>11}"
          f"{'random |diff| 95th':>20}{'percentile':>12}{'':>8}")
    ctrl_rows = []
    for label, col, ctrl in CATS:
        n_a = int(M[col].sum())
        pool = M if ctrl is None else M[M[col] | M[ctrl]]
        n_pool = len(pool)
        for s in STATS:
            v = pool[s].to_numpy(float)
            v = v[np.isfinite(v)]
            if len(v) < n_a + 5:
                continue
            real = R[(R.category == label) & (R.stat == s)].iloc[0]["diff"]
            ds = np.empty(N_RAND)
            for i in range(N_RAND):
                idx = RNG.permutation(len(v))
                ds[i] = v[idx[:n_a]].mean() - v[idx[n_a:]].mean()
            pc = 100.0 * (np.abs(ds) < abs(real)).mean()
            p95 = np.percentile(np.abs(ds), 95)
            beats = abs(real) > p95
            ctrl_rows.append(dict(category=label, stat=s, real=real, p95=p95,
                                  pct=pc, beats=beats))
            print(f"  {label:<24}{NICE[s]:<18}{real:>+11.4f}{p95:>20.4f}"
                  f"{pc:>11.1f}%{'BEATS' if beats else '':>8}")
    C = pd.DataFrame(ctrl_rows)

    print("\n" + "=" * 112)
    print("  VERDICT")
    print("=" * 112)
    nb = int(C.beats.sum())
    npass = int(R.passes.sum())
    print(f"  tests clearing Bonferroni (p < {P_BAR:.6f}):        "
          f"{npass} of {len(R)}")
    print(f"  tests beating the 95th pct of random labels:     {nb} of {len(C)}")
    print(f"  expected by chance at the 95th pct alone:        "
          f"{0.05*len(C):.1f} of {len(C)}")
    if npass:
        print("\n  CLEARING BOTH — category, statistic, difference, percentile "
              "of random:")
        for _, r in C[C.beats].iterrows():
            m = R[(R.category == r["category"]) & (R.stat == r["stat"])].iloc[0]
            if m.passes:
                print(f"    {r['category']:<24}{NICE[r['stat']]:<18}{r['real']:>+10.4f}"
                      f"   p {m.p:.2e}   {r['pct']:.1f}th pct of random   "
                      f"n={m.n}")
    else:
        print("\n  NOTHING CLEARS. Real calendar categories do not separate "
              "session character")
        print("  beyond what random labels of the same size produce.")

    R.to_csv(ROOT / "reports/calendar_study_tests.csv", index=False)
    C.to_csv(ROOT / "reports/calendar_study_control.csv", index=False)
    print("\n  No performance test was run. 2016-2020 remains sealed and "
          "unreadable by this script.")
    print("  Sealed NQ days were not read.")


if __name__ == "__main__":
    main()
