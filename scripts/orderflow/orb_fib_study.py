#!/usr/bin/env python3
"""ORB + FIBONACCI — the study. COUNTS FIRST, THEN PERFORMANCE.

Pre-registered at `5612140` (`reports/orb_fibonacci_preregistration.md`).

CONTINUATION AND REVERSAL ARE REPORTED SEPARATELY AND NEVER POOLED, and are
Bonferroni-corrected separately at alpha = 0.05/4 each.

THE BENCHMARK IS THE RANDOM-WALK RATE AT EACH VARIANT'S OWN REALISED
REWARD-TO-RISK, NOT 50%.  P(target first) = 1/(1+M) for a driftless walk
between two barriers.  The claim under test is 59.13% at 1.43 RR, where a
coin gives 1/2.43 = 41.15%, a gap of +17.98 points.

Usage: python3 scripts/orderflow/orb_fib_study.py
"""
from __future__ import annotations

import sys
from math import sqrt
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from orb_fib import BANDS, ORB_MINS, ROOT, X_MULT, Y_BARS, Z_BARS, load, run  # noqa

N_PER_FAMILY = 4
P_BAR = 0.05 / N_PER_FAMILY            # 0.0125, within each family
Z_CRIT = 2.498                         # two-sided at 0.0125
Z_POW = 0.8416                         # 80%
REV_FLOOR = 150                        # below this the family is unresolvable

CLAIM_WR, CLAIM_RR = 59.13, 1.43


def stats(T):
    """Everything derived from a trade frame. No verdict here."""
    R = T.R
    w, l = R[R > 0], R[R <= 0]
    M = (w.mean() / abs(l.mean())) if len(w) and len(l) and l.mean() != 0 else np.nan
    rw = 100.0 / (1.0 + M) if np.isfinite(M) and M > -1 else np.nan
    wr = 100.0 * len(w) / len(R)
    pf = w.sum() / abs(l.sum()) if len(l) and l.sum() else np.inf
    se = R.std(ddof=1) / sqrt(len(R))
    top = R.sort_values(ascending=False).head(int(np.ceil(0.01 * len(R)))).sum()
    yrs = R.groupby(T.year).mean()
    return dict(
        n=len(R), mean=R.mean(), sd=R.std(ddof=1), se=se, t=R.mean() / se,
        pf=pf, wr=wr, M=M, rw=rw, gap=wr - rw,
        ex1=R.sum() - top, hc=(R - 0.5 * T.cost_pct / 100.0).mean(),
        yrs=yrs, yp=int((yrs > 0).sum()), ny=len(yrs),
        naive=T.naive_R.mean(), slip=T.slip_R.mean(),
        amb=100.0 * T.amb.mean(), risk=T.risk_bps.median(),
        cost=T.cost_pct.median(),
        h1=100.0 * T.hit1.mean(), h2=100.0 * T.hit2.mean(),
        h3=100.0 * T.hit3.mean())


def survives(s):
    return (s["mean"] > 0 and s["pf"] > 1.15 and s["yp"] >= 4
            and s["ex1"] > 0 and s["hc"] > 0)


def main():
    sessions = load()
    print("=" * 126)
    print("  ORB + FIBONACCI — CONTINUATION AND REVERSAL")
    print("=" * 126)
    print(f"  Pre-registered at 5612140. X = {X_MULT:.2f} x ORB height, "
          f"Y = {Y_BARS} bars, Z = {Z_BARS} bars, swing fractal k = 2.")
    print(f"  Bands A {BANDS['A']} and B {BANDS['B']}. 1-minute bars. "
          f"Nothing swept. 8 variants of a permitted 12.")
    print(f"  Continuation and reversal are NEVER pooled and are corrected "
          f"separately at alpha = {P_BAR}.")
    print(f"\n  sessions after sealing: {len(sessions):,}   "
          f"{sessions[0][0]} .. {sessions[-1][0]}")
    print("  Sealed NQ days were not read. 2016-2020 is unreachable by this "
          "script.")

    res, lit = {}, {}
    for om in ORB_MINS:
        for b in BANDS:
            res[(om, b)] = run(sessions, om, b)
            lit[(om, b)] = run(sessions, om, b, literal=True)

    print("\n" + "=" * 126)
    print("  AMENDMENT 1 — the literal 50% rule against the amended one")
    print("=" * 126)
    print("  The literal rule measures the retracement against the run-so-far,")
    print("  which is a few cents at the break bar, so the next bar's ordinary")
    print("  range kills the attempt mechanically. 99% die within 3 bars.")
    print("  The amendment measures it against the REQUIRED leg, X x ORB height.")
    print("  Made on counts alone, before any expectancy was displayed.\n")
    print(f"  {'variant':<16}{'outburst lit':>14}{'outburst amd':>14}"
          f"{'CONT lit':>10}{'CONT amd':>10}{'REV lit':>9}{'REV amd':>9}")
    for k in res:
        print(f"  ORB{k[0]:<3} band {k[1]:<4}{lit[k][2]['ob_ok']:>14,}"
              f"{res[k][2]['ob_ok']:>14,}{lit[k][2]['cont_trade']:>10,}"
              f"{res[k][2]['cont_trade']:>10,}{lit[k][2]['rev_trade']:>9,}"
              f"{res[k][2]['rev_trade']:>9,}")

    # ------------------------------------------------------- COUNTS FIRST ---
    print("\n" + "=" * 126)
    print("  COUNTS FIRST — NO PERFORMANCE NUMBER APPEARS UNTIL AFTER THIS")
    print("=" * 126)
    print("  The funnel, per variant. Each column is a strict subset of the "
          "one before it.\n")
    print(f"  {'variant':<16}{'ORB ok':>8}{'broke':>8}{'outburst':>10}"
          f"{'CONT setup':>12}{'CONT trade':>12}{'Fib fail':>10}"
          f"{'shift':>8}{'opp burst':>11}{'REV setup':>11}{'REV trade':>11}")
    for (om, b), (C, R, d) in res.items():
        print(f"  ORB{om:<3} band {b:<4}{d['orb_ok']:>8,}{d['broke']:>8,}"
              f"{d['ob_ok']:>10,}{d['cont_setup']:>12,}{d['cont_trade']:>12,}"
              f"{d['fib_fail']:>10,}{d['shift_close']:>8,}{d['ob2_ok']:>11,}"
              f"{d['rev_setup']:>11,}{d['rev_trade']:>11,}")

    print(f"\n  ENTRY LOOKAHEAD (must be 0) and trades vs sessions:")
    print(f"  {'variant':<16}{'lookahead':>11}{'CONT trades':>13}"
          f"{'CONT sessions':>15}{'REV trades':>12}{'REV sessions':>14}")
    for (om, b), (C, R, d) in res.items():
        cs = C.day.nunique() if len(C) else 0
        rs = R.day.nunique() if len(R) else 0
        print(f"  ORB{om:<3} band {b:<4}{d['look']:>11}{len(C):>13,}"
              f"{cs:>15,}{len(R):>12,}{rs:>14,}")
    print("  One trade per session per variant by construction, so there is no")
    print("  within-variant date clustering to correct. Trades = sessions above.")

    # ---------------------------------------- the resolvability gate ---------
    rev_max = max(len(R) for _, R, _ in res.values())
    print("\n" + "=" * 126)
    print("  THE REVERSAL RESOLVABILITY GATE — declared in advance at "
          f"{REV_FLOOR} sessions")
    print("=" * 126)
    for (om, b), (C, R, d) in res.items():
        n = len(R)
        print(f"  ORB{om:<3} band {b:<4}  reversal fires on {n:>4,} sessions"
              f"   {'RESOLVABLE' if n >= REV_FLOOR else 'BELOW FLOOR'}")
    if rev_max < REV_FLOOR:
        print(f"\n  *** THE REVERSAL FAMILY CANNOT BE RESOLVED. Best variant "
              f"fires on {rev_max} sessions, floor is {REV_FLOOR}. ***")
        print("  Its expectancy is reported below as DESCRIPTIVE ONLY and is "
              "NOT evidence either way.")

    # --------------------------------------------------------- MDE ----------
    print("\n" + "=" * 126)
    print("  MINIMUM DETECTABLE EFFECT, BEFORE ANY EXPECTANCY IS SHOWN")
    print("=" * 126)
    print(f"  MDE = ({Z_CRIT} + {Z_POW}) x sd / sqrt(n) at alpha = {P_BAR}, "
          f"80% power.\n")
    print(f"  {'variant':<16}{'family':<14}{'n':>7}{'sd':>9}{'MDE R':>10}"
          f"{'note':>34}")
    for (om, b), (C, R, d) in res.items():
        for nm, T in (("continuation", C), ("reversal", R)):
            if not len(T):
                print(f"  ORB{om:<3} band {b:<4}{nm:<14}{0:>7}{'--':>9}"
                      f"{'--':>10}{'no trades':>34}")
                continue
            sd = T.R.std(ddof=1)
            mde = (Z_CRIT + Z_POW) * sd / sqrt(len(T))
            note = ("UNDERPOWERED, below floor" if nm == "reversal"
                    and len(T) < REV_FLOOR else "")
            print(f"  ORB{om:<3} band {b:<4}{nm:<14}{len(T):>7,}{sd:>9.4f}"
                  f"{mde:>+10.4f}{note:>34}")

    # ------------------------------------------------ PERFORMANCE, SPLIT ----
    out = {}
    for fam, idx in (("CONTINUATION", 0), ("REVERSAL", 1)):
        print("\n" + "=" * 126)
        print(f"  {fam} — 4 variants, Bonferroni alpha = {P_BAR}")
        if fam == "REVERSAL" and rev_max < REV_FLOOR:
            print("  DESCRIPTIVE ONLY — the family is below the declared "
                  f"{REV_FLOOR}-session floor and cannot be resolved.")
        print("=" * 126)
        print(f"  {'variant':<16}{'n':>6}{'expR':>9}{'t':>7}{'PF':>7}"
              f"{'win%':>7}{'RR':>7}{'RW%':>7}{'GAP':>8}{'yrs+':>7}"
              f"{'ex-top1%':>10}{'+50%c':>9}{'naive':>9}{'amb':>6}{'':>9}")
        rows = []
        for (om, b), r in res.items():
            T = r[idx]
            if not len(T):
                print(f"  ORB{om:<3} band {b:<4}{0:>6}   no trades")
                continue
            s = stats(T)
            ok = survives(s)
            beats = np.isfinite(s["gap"]) and s["gap"] > 0
            tag = "SURVIVES" if (ok and beats) else ("beats RW" if beats else "")
            print(f"  ORB{om:<3} band {b:<4}{s['n']:>6,}{s['mean']:>+9.4f}"
                  f"{s['t']:>+7.2f}{s['pf']:>7.2f}{s['wr']:>7.1f}"
                  f"{s['M']:>7.2f}{s['rw']:>7.1f}{s['gap']:>+8.1f}"
                  f"{s['yp']:>3}/{s['ny']}{s['ex1']:>10.1f}"
                  f"{s['hc']:>+9.4f}{s['naive']:>+9.4f}"
                  f"{s['amb']:>5.1f}%{tag:>9}")
            rows.append(((om, b), s, ok, beats))
        out[fam] = rows

        if rows:
            print(f"\n  REJECTION RULES, all five must hold")
            print(f"  {'variant':<16}{'expR>0':>9}{'PF>1.15':>9}"
                  f"{'4/6 yrs':>9}{'ex-top1%':>10}{'+50% cost':>11}"
                  f"{'beats RW':>10}{'':>12}")
            for k, s, ok, beats in rows:
                print(f"  ORB{k[0]:<3} band {k[1]:<4}"
                      f"{'PASS' if s['mean']>0 else 'FAIL':>9}"
                      f"{'PASS' if s['pf']>1.15 else 'FAIL':>9}"
                      f"{'PASS' if s['yp']>=4 else 'FAIL':>9}"
                      f"{'PASS' if s['ex1']>0 else 'FAIL':>10}"
                      f"{'PASS' if s['hc']>0 else 'FAIL':>11}"
                      f"{'PASS' if beats else 'FAIL':>10}"
                      f"{('SURVIVES' if ok and beats else 'rejected'):>12}")

            print(f"\n  TARGET STRUCTURE — context only, NOT variants, NO "
                  f"verdict drawn")
            print(f"  {'variant':<16}{'hit 1R':>9}{'hit 2R':>9}{'hit 3R':>9}"
                  f"{'whole@1R':>11}{'whole@2R':>11}{'whole@3R':>11}"
                  f"{'med risk':>11}{'cost/R':>8}")
            for k, s, ok, beats in rows:
                T = res[k][idx]
                print(f"  ORB{k[0]:<3} band {k[1]:<4}{s['h1']:>8.1f}%"
                      f"{s['h2']:>8.1f}%{s['h3']:>8.1f}%"
                      f"{T.R1.mean():>+11.4f}{T.R2.mean():>+11.4f}"
                      f"{T.R3.mean():>+11.4f}{s['risk']:>10.1f}b"
                      f"{s['cost']:>7.2f}%")

            print(f"\n  BY YEAR — mean R")
            ally = sorted({y for _, s, _, _ in rows for y in s["yrs"].index})
            print(f"  {'variant':<16}" + "".join(f"{y:>11}" for y in ally))
            for k, s, ok, beats in rows:
                print(f"  ORB{k[0]:<3} band {k[1]:<4}" + "".join(
                    f"{s['yrs'][y]:>+11.4f}" if y in s["yrs"].index
                    else f"{'--':>11}" for y in ally))

    # -------------------------------------------------- two diagnostics -----
    print("\n" + "=" * 126)
    print("  DIAGNOSTIC 1 — HOW CONCENTRATED IS EACH RESULT?")
    print("=" * 126)
    print("  The pre-registered rule removes the best 1%, which at n~100 is one")
    print("  or two trades. Deeper removals are shown because they are not the")
    print("  declared test and cannot reject anything -- they only show how much")
    print("  of each result rests on a handful of trades.\n")
    print(f"  {'family':<14}{'variant':<16}{'n':>6}{'mean':>9}{'median':>9}"
          f"{'top3 % of total':>17}{'drop best 5':>13}{'drop best 10':>14}")
    for fam, idx in (("continuation", 0), ("reversal", 1)):
        for k, r in res.items():
            T = r[idx]
            if len(T) < 15:
                continue
            R = T.R
            t3 = R.nlargest(3).sum()
            print(f"  {fam:<14}ORB{k[0]:<3} band {k[1]:<6}{len(R):>6,}"
                  f"{R.mean():>+9.4f}{R.median():>+9.4f}"
                  f"{100*t3/R.sum() if R.sum() else np.nan:>16.0f}%"
                  f"{R.nsmallest(len(R)-5).mean():>+13.4f}"
                  f"{R.nsmallest(max(len(R)-10,1)).mean():>+14.4f}")

    print("\n" + "=" * 126)
    print("  DIAGNOSTIC 2 — THE FOUR VARIANTS ARE NOT FOUR INDEPENDENT TESTS")
    print("=" * 126)
    print("  Session overlap (Jaccard) between continuation variants. Two "
          "variants that\n  share most of their sessions are one test in two "
          "geometries, not two tests.\n")
    ks = list(res)
    print(f"  {'':<18}" + "".join(f"{'ORB%d/%s' % k:>12}" for k in ks))
    for a in ks:
        sa = set(res[a][0].day) if len(res[a][0]) else set()
        row = ""
        for b in ks:
            sb = set(res[b][0].day) if len(res[b][0]) else set()
            j = len(sa & sb) / len(sa | sb) if (sa | sb) else np.nan
            row += f"{j:>12.2f}"
        print(f"  ORB{a[0]:<3} band {a[1]:<8}" + row)

    # --------------------------------------------------------- verdict ------
    print("\n" + "=" * 126)
    print("  THE CLAIM, AGAINST THE RIGHT BENCHMARK")
    print("=" * 126)
    print(f"  Claimed: {CLAIM_WR}% at {CLAIM_RR} RR. A driftless walk at "
          f"{CLAIM_RR} RR gives {100/(1+CLAIM_RR):.2f}%.")
    print(f"  The claimed gap is {CLAIM_WR - 100/(1+CLAIM_RR):+.2f} points.\n")
    print(f"  {'family':<16}{'variant':<16}{'win%':>8}{'RR':>7}"
          f"{'RW%':>8}{'gap':>8}{'':>10}")
    for fam, rows in out.items():
        for k, s, ok, beats in rows:
            print(f"  {fam.lower():<16}ORB{k[0]:<3} band {k[1]:<6}"
                  f"{s['wr']:>8.1f}{s['M']:>7.2f}{s['rw']:>8.1f}"
                  f"{s['gap']:>+8.1f}{'above' if beats else 'below':>10}")

    nc = sum(1 for k, s, ok, b in out.get("CONTINUATION", []) if ok and b)
    nr = sum(1 for k, s, ok, b in out.get("REVERSAL", []) if ok and b)
    print(f"\n  continuation survivors: {nc} of 4")
    print(f"  reversal survivors:     {nr} of 4"
          + (f"   (and the family is below the {REV_FLOOR}-session floor "
             f"regardless)" if rev_max < REV_FLOOR else ""))
    print("\n  The two families were never pooled at any point in this script.")
    print("  Sealed NQ days were not read. 2016-2020 remains sealed.")

    for fam, idx in (("continuation", 0), ("reversal", 1)):
        A = pd.concat([r[idx].assign(orb=k[0], band=k[1])
                       for k, r in res.items() if len(r[idx])],
                      ignore_index=True) if any(
                          len(r[idx]) for r in res.values()) else pd.DataFrame()
        if len(A):
            A.to_csv(ROOT / f"reports/orb_fib_{fam}_trades.csv", index=False)


if __name__ == "__main__":
    main()
