#!/usr/bin/env python3
"""INITIAL BALANCE BY REJECTION — Stages 1-3. Pre-registered at `9043ab6`.
22 tests, Bonferroni alpha = 0.00227. Sealed NQ days not read.
"""
from __future__ import annotations
import sys
from math import erfc, sqrt
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ib_rejection import (BUCKETS, COST_F, bucket_of, nq_sessions,     # noqa
                          qqq_sessions)

P_BAR = 0.05 / 22
N_RAND = 1000
RNG = np.random.default_rng(31)


def wilson(k, n, z=1.96):
    if n == 0:
        return (np.nan, np.nan)
    p = k / n
    d = 1 + z*z/n
    c = (p + z*z/(2*n)) / d
    h = z*sqrt(p*(1-p)/n + z*z/(4*n*n)) / d
    return (100*(c-h), 100*(c+h))


def ztest(k, n, p0):
    if n == 0 or not (0 < p0 < 1):
        return np.nan, np.nan
    se = sqrt(p0*(1-p0)/n)
    z = (k/n - p0)/se
    return z, erfc(abs(z)/sqrt(2))


def stage1(D, name):
    print(f"\n  {name}: {len(D):,} sessions   high-first "
          f"{100*D.high_first.mean():.1f}%   unresolvable/no-break "
          f"{int((D.broke.isin(['both','none'])).sum())}")
    print(f"  {'bucket':<10}{'n':>6}{'mean EZ':>9}{'RW base':>9}"
          f"{'observed':>10}{'95% CI':>17}{'excess':>9}{'z':>8}{'p':>10}{'':>6}")
    rows = []
    for lo, hi in BUCKETS:
        b = D[D.bucket == f"{lo}-{hi}%"]
        b = b[~b.broke.isin(["both", "none"])]
        n = len(b)
        if n == 0:
            continue
        k = int(b.expected_broke_first.sum())
        base = b.rw_base.mean()/100.0
        obs = 100.0*k/n
        ci = wilson(k, n)
        z, p = ztest(k, n, base)
        sig = "PASS" if (np.isfinite(p) and p < P_BAR) else ""
        rows.append(dict(inst=name, bucket=f"{lo}-{hi}%", n=n, obs=obs,
                         base=100*base, excess=obs-100*base, z=z, p=p,
                         passes=bool(sig)))
        print(f"  {f'{lo}-{hi}%':<10}{n:>6,}{b.ez.mean():>9.1f}"
              f"{100*base:>8.1f}%{obs:>9.1f}%"
              f"{f'[{ci[0]:.1f}, {ci[1]:.1f}]':>17}{obs-100*base:>+9.1f}"
              f"{z:>+8.2f}{p:>10.2e}{sig:>6}")
    return pd.DataFrame(rows)


def stage3(D, name):
    """Mechanical trade. Honest fills, entry bar excluded, 2pt round turn."""
    b = D[(D.bucket == "0-25%") & (D.expected_broke_first)]
    out = []
    for _, s in b.iterrows():
        d = 1 if s.exp_side == "up" else -1
        trig = s.ibh if d > 0 else s.ibl
        stop = s.ibl if d > 0 else s.ibh
        i = int(s._i_break)
        hi, lo, op, cl = s._post_hi, s._post_lo, s._post_op, s._post_cl
        if i < 0 or i + 1 >= len(hi):
            continue
        fill = max(trig, op[i]) if d > 0 else min(trig, op[i])
        risk = abs(fill - stop)
        if risk <= 0:
            continue
        cost = s.px * COST_F
        rec = dict(day=s.day, dir=d, risk_bps=1e4*risk/s.px,
                   year=pd.Timestamp(s.day).year)
        for tg in (1.0, 2.0, 3.0, None):
            tgt = fill + d*tg*risk if tg else None
            exit_px, why = None, ""
            for j in range(i+1, len(hi)):          # entry bar EXCLUDED
                st = lo[j] <= stop if d > 0 else hi[j] >= stop
                ht = (hi[j] >= tgt if d > 0 else lo[j] <= tgt) if tg else False
                if st:
                    exit_px = min(stop, op[j]) if d > 0 else max(stop, op[j])
                    why = "stop"; break
                if ht:
                    exit_px, why = tgt, "target"; break
            if exit_px is None:
                exit_px, why = cl[-1], "close"
            key = f"{tg:.0f}R" if tg else "Close"
            rec[key] = (d*(exit_px-fill) - cost)/risk
            rec[key+"_why"] = why
        out.append(rec)
    T = pd.DataFrame(out)
    print(f"\n  {name}: {len(T):,} trades from {len(b):,} qualifying sessions")
    if T.empty:
        return T
    print(f"  {'target':<8}{'trades':>8}{'win%':>8}{'RW win%':>9}{'excess':>9}"
          f"{'expR':>9}{'PF':>7}{'t':>7}{'time-exit':>9}{'med risk':>10}{'':>6}")
    print("  PASS requires the standing bar t > 3. The RW win% column is "
          "CONTEXT ONLY where")
    print("  time-exit is high: 1/(1+M) assumes a barrier resolution and does "
          "not apply then.")
    for key, M in (("1R", 1.0), ("2R", 2.0), ("3R", 3.0), ("Close", None)):
        R = T[key]
        w, l = R[R > 0], R[R <= 0]
        wr = 100*(R > 0).mean()
        if M:
            rw = 100/(1+M)
        else:
            mm = w.mean()/abs(l.mean()) if len(l) and l.mean() else np.nan
            rw = 100/(1+mm) if np.isfinite(mm) else np.nan
        pf = w.sum()/abs(l.sum()) if len(l) and l.sum() else np.inf
        tt = R.mean()/(R.std(ddof=1)/sqrt(len(R))) if len(R) > 2 else np.nan
        # The 1/(1+M) benchmark assumes the trade resolves AT A BARRIER. When
        # most trades time-exit at the close it does not apply, so the standing
        # criterion (t > 3) governs instead and the win-rate column is context.
        mix = T[key+"_why"].value_counts().to_dict()
        tex = 100.0*mix.get("close", 0)/len(R)
        sig = "PASS" if (np.isfinite(tt) and tt > 3 and R.mean() > 0) else ""
        print(f"  {key:<8}{len(R):>8,}{wr:>7.1f}%{rw:>8.1f}%{wr-rw:>+9.1f}"
              f"{R.mean():>+9.3f}{pf:>7.2f}{tt:>+7.2f}{tex:>8.0f}%"
              f"{T.risk_bps.median():>9.1f}b{sig:>6}")
    return T


def main():
    print("="*112)
    print("  INITIAL BALANCE BY REJECTION — Stages 1-3")
    print("="*112)
    print(f"  22 tests, Bonferroni alpha = {P_BAR:.5f}")
    print("  BENCHMARK IS NOT 50%. For a driftless walk the break probability")
    print("  is exactly (100 - Ending Zone). Every rate is judged against that.")

    Q = pd.DataFrame(qqq_sessions()); Q["bucket"] = Q.ez.map(bucket_of)
    Q["year"] = pd.to_datetime(Q.day).dt.year
    N = pd.DataFrame(nq_sessions()); N["bucket"] = N.ez.map(bucket_of)

    print("\n" + "="*112)
    print("  STAGE 1 — BREAK RATE BY BUCKET, AGAINST THE GEOMETRIC BASELINE")
    print("="*112)
    r1 = stage1(Q, "QQQ")
    r2 = stage1(N, "NQ tick")
    print("\n  NQ is reported for completeness only: 15 sessions in the headline")
    print("  bucket, +/-29.6 point resolution. It cannot tell 86% from 60%.")

    print("\n" + "="*112)
    print("  STAGE 2 — 0-25% BUCKET BY YEAR (QQQ)")
    print("="*112)
    print(f"  {'year':<8}{'n':>7}{'RW base':>10}{'observed':>11}{'excess':>9}"
          f"{'>=100 obs':>11}")
    hold = 0
    for y in sorted(Q.year.unique()):
        b = Q[(Q.bucket == "0-25%") & (Q.year == y) &
              (~Q.broke.isin(["both", "none"]))]
        if not len(b):
            continue
        obs = 100*b.expected_broke_first.mean()
        base = b.rw_base.mean()
        if obs > base:
            hold += 1
        print(f"  {y:<8}{len(b):>7}{base:>9.1f}%{obs:>10.1f}%"
              f"{obs-base:>+9.1f}{'yes' if len(b) >= 100 else 'NO':>11}")
    print(f"\n  observed ABOVE the geometric baseline in {hold} of 6 years "
          f"(requirement: 5 of 6)")

    print("\n" + "="*112)
    print("  RANDOM-LABEL CONTROL (the weaker one, as declared)")
    print("="*112)
    ok = Q[~Q.broke.isin(["both", "none"])]
    n_a = int((ok.bucket == "0-25%").sum())
    v = ok.expected_broke_first.to_numpy()
    ds = np.array([v[RNG.permutation(len(v))[:n_a]].mean() for _ in range(N_RAND)])
    real = ok[ok.bucket == "0-25%"].expected_broke_first.mean()
    print(f"  real 0-25% break rate {100*real:.1f}%   random-label 95th pct "
          f"{100*np.percentile(ds,95):.1f}%   pooled rate {100*v.mean():.1f}%")
    print(f"  percentile of random: {100*(ds < real).mean():.1f}%")
    print("  NOTE: this control CANNOT detect the geometric confound -- "
          "shuffling labels")
    print("  destroys the distance information that produces the effect.")

    print("\n" + "="*112)
    print("  STAGE 3 — THE MECHANICAL TRADE")
    print("="*112)
    print("  Long: low first, EZ 0-25%, enter first break of IBH. Short: "
          "mirrored.")
    print("  Stop = other side of IB, so risk ~ the full IB range. "
          "Entry bar excluded.")
    T = stage3(Q, "QQQ")
    stage3(N, "NQ tick")
    if not T.empty:
        print("\n  QQQ 1R by year — mean R")
        for y in sorted(T.year.unique()):
            g = T[T.year == y]
            print(f"    {y}  n {len(g):>4}   1R {g['1R'].mean():>+7.3f}   "
                  f"2R {g['2R'].mean():>+7.3f}   3R {g['3R'].mean():>+7.3f}   "
                  f"Close {g['Close'].mean():>+7.3f}")
        print("\n  exit mix at 1R: " +
              str(T["1R_why"].value_counts().to_dict()))
    print("\n  Sealed NQ days were not read. 2016-2020 remains sealed.")


if __name__ == "__main__":
    main()
