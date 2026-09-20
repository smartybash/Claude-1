#!/usr/bin/env python3
"""RETROACTIVE CONCENTRATION AUDIT — every screen, both rules, side by side.

NO NEW HYPOTHESES. Nothing here is a new test. Every variant below was already
run and already recorded in the ledger. The ONLY thing that changes is which
concentration rule is applied to the same trades.

    OLD: positive after removing the best 1%       -> ceil(0.01 * n) trades
    NEW: positive after removing the best 10 OR
         the top decile, whichever is stricter     -> max(10, ceil(0.10 * n))

The other four rejection rules are UNCHANGED:
    1. expectancy > 0 after costs
    2. profit factor > 1.15
    3. >= 4 of 6 years positive
    4. (the concentration rule -- the one being changed)
    5. positive at 50% higher cost

The question is narrow and is answered per variant: DID THIS VARIANT SURVIVE
ONLY BECAUSE THE CONCENTRATION TEST WAS TOO WEAK?

Families audited (every screen in the repo that used the 1% rule):
    qqq_screen           16 variants
    orb_vwap             16 variants
    or_height             4 variants (promoted, in-sample + holdout blocks)
    disc_pullback         8 variants
    reopen_study          Test 1 (IB re-entry) and Test 2 (VWAP) grids
    related_instruments   5 instruments, frozen IB 1R
    orb_fib_study         4 + 4 variants  (already corrected; included for
                                           completeness of the ledger)

Sealed NQ days stay sealed -- every loader below is the family's own, which
already excludes them. 2016-2020 is NOT read by any of these loaders.
"""
from __future__ import annotations

import sys
from math import ceil
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
ROOT = Path(__file__).resolve().parents[2]

N_FLOOR = 300          # the scope the audit was asked for
ROWS = []              # (family, variant, n, ...) accumulated for the summary


# ----------------------------------------------------------- the two rules --

def old_rule(R):
    """Positive after removing the best 1%. Returns (total_after, k)."""
    k = int(ceil(0.01 * len(R)))
    top = R.sort_values(ascending=False).head(k).sum()
    return float(R.sum() - top), k


def new_rule(R):
    """Positive after removing max(10, top decile). Returns (mean_after, k)."""
    k = max(10, int(ceil(0.10 * len(R))))
    if k >= len(R):
        return np.nan, k
    return float(R.nsmallest(len(R) - k).mean()), k


def assess(family, variant, R, years, cost_pct, note=""):
    """Both verdicts on one variant. R = per-trade R, years = per-trade year."""
    n = len(R)
    if n < 5:
        return
    R = pd.Series(np.asarray(R, float))
    years = pd.Series(np.asarray(years))
    w, l = R[R > 0], R[R <= 0]
    pf = w.sum() / abs(l.sum()) if len(l) and l.sum() else np.inf
    yr = R.groupby(years.values).mean()
    yp = int((yr > 0).sum())
    hc = float((R - 0.5 * np.asarray(cost_pct, float) / 100.0).mean())
    ex1, k1 = old_rule(R)
    exs, ks = new_rule(R)
    base = (R.mean() > 0) and (pf > 1.15) and (yp >= 4) and (hc > 0)
    old_ok = bool(base and ex1 > 0)
    new_ok = bool(base and np.isfinite(exs) and exs > 0)
    ROWS.append(dict(family=family, variant=variant, n=n, mean=float(R.mean()),
                     median=float(R.median()), pf=float(pf), yp=yp, ny=len(yr),
                     hc=hc, ex1=ex1, k1=k1, exs=exs, ks=ks,
                     old=old_ok, new=new_ok, note=note))


# ---------------------------------------------------------------- families --

def cost_pct_from_bps(risk_bps, cost_f):
    """cost/risk as a percent, recovered from risk in bps. Identical to what
    each screen used; the screens just did not all persist the column."""
    return 100.0 * (1e4 * cost_f) / np.asarray(risk_bps, float)


def audit_qqq_screen():
    from itertools import product
    import qqq_screen as M
    S, _rej = M.build_sessions()
    for om, sa, tg in product(M.G_OR, M.G_SATR, M.G_TGT):
        T = M.evaluate(S, om, sa, tg)
        if not len(T):
            continue
        assess("qqq_screen", f"OR{om} SATR{sa} R{tg}", T.R, T.year,
               cost_pct_from_bps(T.risk_bps, M.COST_F))


def audit_orb_vwap():
    from itertools import product
    import orb_vwap as M
    out = M.build_sessions()
    S = out[0] if isinstance(out, tuple) else out
    days = sorted(S)
    for om, sa, tg in product(M.G_OR, M.G_SATR, M.G_TGT):
        T, _D = M.evaluate(S, days, om, sa, tg)
        if not len(T):
            continue
        assess("orb_vwap", f"OR{om} SATR{sa} R{tg}", T.R, T.year,
               cost_pct_from_bps(T.risk_bps, M.COST_F))


def audit_or_height():
    from itertools import product
    import or_height as M
    S, _rej = M.build("data/intraday_long/QQQ_1m.parquet", 1)
    days = sorted(S)
    for om, tg in product(M.G_OR, M.G_TGT):      # the 4 pre-registered variants
        T, _lk = M.evaluate(S, days, om, tg, M.STOP_ATR_1M)
        if not len(T):
            continue
        assess("or_height", f"OR{om} R{tg}", T.R, T.year,
               cost_pct_from_bps(T.risk_bps, M.COST_F))


def audit_disc_pullback():
    from itertools import product
    import disc_pullback as M
    out = M.sessions()
    S = out[0] if isinstance(out, tuple) else out
    for tr, tg, fl in product(M.G_TREND, M.G_TGT, M.G_FLOOR):
        T, _lk = M.evaluate(S, tr, tg, fl, True)   # declared rule keeps the stop
        if not len(T):
            continue
        assess("disc_pullback", f"{tr} {tg} f{fl:.2f}", T.R, T.year,
               cost_pct_from_bps(T.risk_bps, M.COST_F))


def audit_reopen():
    import reopen_study as M
    S = M.load()
    for tg in (1.0, 2.0, 3.0, 4.0):
        for nm, fn in (("IB re-entry", M.test1), ("VWAP", M.test2)):
            out = fn(S, tg)
            T = out[0] if isinstance(out, tuple) else out
            if not len(T):
                continue
            yrs = pd.to_datetime(pd.Series(list(T.day))).dt.year
            assess("reopen_study", f"{nm} {tg}R", T.R, yrs, T.cost_pct)


def audit_related():
    import related_instruments as M
    for sym in ("SPY", "IWM", "XLK", "IJH", "EFA"):
        p = ROOT / f"data/related/{sym}_5m.parquet"
        if not p.exists():
            continue
        T, _m = M.run(pd.read_parquet(p), sym)
        if not len(T):
            continue
        assess("related_inst", f"IB 1R {sym}", T.R, T.year, T.cost_pct)


def audit_frozen_ib():
    """THE FROZEN CANDIDATE: IB 1R, SINGLE TRADE, QQQ 1-MINUTE.

    CORRECTION made during this audit: a first pass reproduced this through
    related_instruments.run on QQQ_5m and got n=675, +0.0578. That was the
    WRONG BAR RESOLUTION -- the frozen candidate was frozen on 1-minute bars
    in reopen_study. The single-trade rule is exactly test1 restricted to the
    FIRST entry (`seq == 1`); test1's own re-entry control is `taken < 2`.
    This reproduces the ledger exactly: n=685, +0.0612, sd 0.7175, t +2.231,
    PF 1.22, 5 of 6 years.

    reopen_study reads QQQ_1m.parquet, which begins 2021-01-04, so 2016-2020
    is unreachable here.
    """
    import reopen_study as M
    S = M.load()
    T, _look = M.test1(S, 1.0)
    F = T[T.seq == 1]
    print(f"     frozen IB 1R single trade: n={len(F)} "
          f"mean={F.R.mean():+.4f} (ledger: 685, +0.0612)")
    assess("FROZEN", "IB 1R QQQ single", F.R, F.year, F.cost_pct,
           note="the live candidate")


def audit_orb_fib():
    import orb_fib as M
    S = M.load()
    for om in M.ORB_MINS:
        for b in M.BANDS:
            C, R, _d = M.run(S, om, b)
            for nm, T in (("cont", C), ("rev", R)):
                if not len(T):
                    continue
                assess("orb_fib", f"{nm} ORB{om}{b}", T.R, T.year, T.cost_pct)


# -------------------------------------------------------------------- main --

def main():
    print("=" * 132)
    print("  RETROACTIVE CONCENTRATION AUDIT")
    print("=" * 132)
    print("  NO NEW HYPOTHESES. Same trades, same four other rules. The only")
    print("  change is the concentration test:")
    print("      OLD  remove best 1%           = ceil(0.01 n)")
    print("      NEW  remove max(10, decile)   = max(10, ceil(0.10 n))")
    print("  Sealed NQ days stay sealed. 2016-2020 is not read.\n")

    for name, fn in (("qqq_screen", audit_qqq_screen),
                     ("orb_vwap", audit_orb_vwap),
                     ("or_height", audit_or_height),
                     ("disc_pullback", audit_disc_pullback),
                     ("reopen_study", audit_reopen),
                     ("related_inst", audit_related),
                     ("FROZEN candidate", audit_frozen_ib),
                     ("orb_fib", audit_orb_fib)):
        try:
            fn()
            print(f"  audited {name}")
        except Exception as e:                      # noqa: BLE001
            print(f"  !! {name} FAILED: {type(e).__name__}: {e}")

    D = pd.DataFrame(ROWS)
    if D.empty:
        print("\n  nothing audited")
        return
    D.to_csv(ROOT / "reports/concentration_audit.csv", index=False)

    print("\n" + "=" * 132)
    print("  EVERY VARIANT, BOTH RULES")
    print("=" * 132)
    print(f"  {'family':<15}{'variant':<22}{'n':>7}{'mean R':>9}{'median':>9}"
          f"{'PF':>7}{'yrs+':>7}{'k old':>7}{'ex-1% tot':>11}"
          f"{'k new':>7}{'after new':>11}{'OLD':>6}{'NEW':>6}{'flip':>7}")
    for _, r in D.iterrows():
        flip = "FLIP" if (r.old and not r["new"]) else ""
        print(f"  {r.family:<15}{r.variant:<22}{r.n:>7,}{r['mean']:>+9.4f}"
              f"{r['median']:>+9.4f}{r.pf:>7.2f}{r.yp:>3}/{r.ny}"
              f"{r.k1:>7}{r.ex1:>+11.1f}{r.ks:>7}"
              f"{(r.exs if np.isfinite(r.exs) else float('nan')):>+11.4f}"
              f"{('PASS' if r.old else '-'):>6}"
              f"{('PASS' if r['new'] else '-'):>6}{flip:>7}")

    # ------------------------------------------------------- the question ---
    print("\n" + "=" * 132)
    print("  THE QUESTION: DID ANYTHING SURVIVE ONLY BECAUSE THE TEST WAS WEAK?")
    print("=" * 132)
    passed_old = D[D.old]
    flips = D[D.old & ~D["new"]]
    print(f"  variants audited                      : {len(D)}")
    print(f"  variants that PASSED under the old rule: {len(passed_old)}")
    print(f"  of those, n < {N_FLOOR}                     : "
          f"{int((passed_old.n < N_FLOOR).sum())}")
    print(f"  variants that FLIP to fail under the new rule: {len(flips)}")

    if len(passed_old):
        print(f"\n  EVERY OLD PASS, with its fate:")
        print(f"  {'family':<15}{'variant':<22}{'n':>7}{'mean R':>9}"
              f"{'after new rule':>16}{'verdict':>10}{'in scope n<300':>16}")
        for _, r in passed_old.iterrows():
            print(f"  {r.family:<15}{r.variant:<22}{r.n:>7,}{r['mean']:>+9.4f}"
                  f"{r.exs:>+16.4f}"
                  f"{('SURVIVES' if r['new'] else 'FAILS'):>10}"
                  f"{('yes' if r.n < N_FLOOR else 'no'):>16}")

    print(f"\n  HOW MANY TRADES THE OLD RULE ACTUALLY REMOVED, by sample size:")
    print(f"  {'n range':<18}{'variants':>10}{'k old':>9}{'k new':>9}"
          f"{'ratio':>9}")
    for lo, hi, lab in ((0, 100, "n < 100"), (100, 300, "100 <= n < 300"),
                        (300, 1000, "300 <= n < 1000"), (1000, 10**9, "n >= 1000")):
        sub = D[(D.n >= lo) & (D.n < hi)]
        if not len(sub):
            continue
        print(f"  {lab:<18}{len(sub):>10}{sub.k1.mean():>9.1f}"
              f"{sub.ks.mean():>9.1f}{sub.ks.mean()/sub.k1.mean():>9.1f}x")

    print("\n  No new hypothesis was run. Sealed NQ days were not read.")
    print("  2016-2020 remains sealed and unspent.")


if __name__ == "__main__":
    main()
