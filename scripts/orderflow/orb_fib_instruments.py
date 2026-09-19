#!/usr/bin/env python3
"""ORB + FIBONACCI CONTINUATION — INSTRUMENT EXTENSION.

Frozen continuation rule from `5612140` / `c9196d1`, UNCHANGED, on SPY, IWM,
IJH and EFA, 1-minute bars, 2021-01-04 .. 2025-12-31.

ONLY ORB15 BAND A AND ORB30 BAND A ARE RUN. Bands A and B were shown to share
86-90% of their sessions, so they are not independent tests; band B is dropped
rather than reported as if it were a second observation.

RESOLUTION. The frozen rule is defined in BARS -- Y = 30, Z = 5, swing fractal
k = 2 -- on a 1-minute grid. Running it on 5-minute bars would silently
redefine all three, so 1-minute data was fetched for all four instruments
rather than reusing the 5-minute files from the IB family.

STANDING CHANGE TO THE CONCENTRATION RULE (applies from here on, every family):
    OLD: remove the best 1% of trades.
    NEW: remove the best 10 trades OR the top decile, WHICHEVER IS STRICTER,
         i.e. remove max(10, ceil(0.10 * n)).
At n ~ 100 the old rule stripped one or two trades and could not fail. The new
rule is applied to every variant here, including the QQQ discovery figures,
which are recomputed under it for a like-for-like comparison.

THE SE IS CLUSTERED BY DATE. All four instruments trade the same 1,255
sessions and move together. One trade per session per instrument per variant,
so clustering matters only across instruments -- which is exactly where the
pooling happens.

2016-2020 stays unread. Sealed NQ days stay sealed. This script reads only
2021-2025 ETF files and QQQ_1m.parquet.
"""
from __future__ import annotations

import datetime as dt
import sys
from math import ceil, erf, sqrt
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from orb_fib import (BANDS, MIN_BARS, ROOT, SEALED_DATES, SEALED_PREFIX,  # noqa
                     session_setups)

INSTRUMENTS = ("SPY", "IWM", "IJH", "EFA")
VARIANTS = ((15, "A"), (30, "A"))
N_VARIANTS = 2
P_BAR = 0.05 / N_VARIANTS              # 0.025, the two surviving variants
Z_BONF = 2.241                         # two-sided at 0.025
Z_POW = 0.8416                         # 80%
Z_95 = 1.96                            # the decision rule's interval

DISC = {(15, "A"): 0.1154, (30, "A"): 0.2071}   # QQQ, frozen
HOLDOUT_SESSIONS = 1259


def ncdf(z):
    return 0.5 * (1.0 + erf(z / sqrt(2.0)))


def strict_drop(R):
    """THE STANDING CHANGE: drop max(10, top decile), whichever is stricter."""
    k = max(10, int(ceil(0.10 * len(R))))
    if k >= len(R):
        return np.nan, k
    return float(R.nsmallest(len(R) - k).mean()), k


def cluster_se(R, keys):
    R = np.asarray(R, float)
    n = len(R)
    d = pd.Series(R - R.mean()).groupby(np.asarray(keys)).sum().to_numpy()
    g = len(d)
    if g < 2:
        return np.nan, g
    return sqrt((g / (g - 1.0)) * float((d ** 2).sum())) / n, g


def load_frame(path, sealed=False):
    raw = pd.read_parquet(path)
    raw["day"] = raw.timestamp.dt.date
    out = []
    for day, g in raw.groupby("day", sort=True):
        if sealed:
            s = day.strftime("%Y%m%d")
            if s.startswith(SEALED_PREFIX) or s in SEALED_DATES:
                continue
        if len(g) < MIN_BARS:
            continue
        out.append((day, g.sort_values("timestamp")))
    return out


def run_one(sessions, orb_min, band):
    rows, look = [], 0
    for day, g in sessions:
        o = pd.Timestamp(dt.datetime.combine(day, dt.time(9, 30)))
        t = (g.timestamp - o).dt.total_seconds().to_numpy() / 60.0
        c, _r, d = session_setups(
            day, t, g.high.to_numpy(float), g.low.to_numpy(float),
            g.open.to_numpy(float), g.close.to_numpy(float), orb_min, band)
        look += d["look"]
        if c:
            rows.append(c)
    return pd.DataFrame(rows), look


def main():
    print("=" * 128)
    print("  ORB + FIBONACCI CONTINUATION — INSTRUMENT EXTENSION")
    print("=" * 128)
    print("  Frozen rule from 5612140 / c9196d1, unchanged. 1-minute bars, "
          "2021-2025.")
    print("  ORB15 band A and ORB30 band A only -- bands A and B share 86-90% "
          "of sessions")
    print("  and are not independent tests.")
    print("  SE clustered by date. 2016-2020 unread; sealed NQ days not read.")

    data = {}
    for sym in INSTRUMENTS:
        p = ROOT / f"data/related/{sym}_1m.parquet"
        data[sym] = load_frame(p)
    qqq = load_frame(ROOT / "data/intraday_long/QQQ_1m.parquet", sealed=True)

    print(f"\n  {'instrument':<12}{'sessions':>10}{'first':>14}{'last':>14}")
    for sym in INSTRUMENTS:
        print(f"  {sym:<12}{len(data[sym]):>10,}{str(data[sym][0][0]):>14}"
              f"{str(data[sym][-1][0]):>14}")
    print(f"  {'QQQ (disc)':<12}{len(qqq):>10,}{str(qqq[0][0]):>14}"
          f"{str(qqq[-1][0]):>14}")

    # ----------------------------------------------------- counts first -----
    res = {}
    for om, b in VARIANTS:
        for sym in INSTRUMENTS:
            res[(om, b, sym)] = run_one(data[sym], om, b)
        res[(om, b, "QQQ")] = run_one(qqq, om, b)

    print("\n" + "=" * 128)
    print("  COUNTS FIRST")
    print("=" * 128)
    print(f"  {'variant':<14}{'instrument':<12}{'sessions':>10}{'trades':>9}"
          f"{'rate':>8}{'lookahead':>11}{'ambiguous':>11}")
    for om, b in VARIANTS:
        for sym in list(INSTRUMENTS) + ["QQQ"]:
            T, look = res[(om, b, sym)]
            ns = len(qqq) if sym == "QQQ" else len(data[sym])
            amb = 100.0 * T.amb.mean() if len(T) else np.nan
            print(f"  ORB{om:<3} band {b:<4}{sym:<12}{ns:>10,}{len(T):>9,}"
                  f"{100*len(T)/ns:>7.1f}%{look:>11}{amb:>10.1f}%")

    # ------------------------------------------------- per instrument -------
    print("\n" + "=" * 128)
    print("  PER-INSTRUMENT BREAKDOWN")
    print("=" * 128)
    print("  'drop strict' = the STANDING CHANGE: remove max(10, top decile).")
    print("  'ex-1%' is the OLD rule, shown once so the change is visible.\n")
    print(f"  {'variant':<14}{'inst':<7}{'n':>6}{'mean R':>9}{'clus SE':>9}"
          f"{'t':>7}{'PF':>7}{'win%':>7}{'RW%':>7}{'gap':>7}"
          f"{'ex-1%':>9}{'drop strict':>13}{'k':>5}{'+50%c':>9}")
    for om, b in VARIANTS:
        for sym in list(INSTRUMENTS) + ["QQQ"]:
            T, _ = res[(om, b, sym)]
            if len(T) < 5:
                continue
            R = T.R
            se, _g = cluster_se(R.to_numpy(float), T.day.to_numpy())
            w, l = R[R > 0], R[R <= 0]
            M = w.mean() / abs(l.mean()) if len(w) and len(l) else np.nan
            rw = 100.0 / (1.0 + M) if np.isfinite(M) else np.nan
            wr = 100.0 * len(w) / len(R)
            pf = w.sum() / abs(l.sum()) if len(l) and l.sum() else np.inf
            old = R.nsmallest(len(R) - max(1, int(ceil(0.01 * len(R))))).mean()
            new, k = strict_drop(R)
            hc = (R - 0.5 * T.cost_pct / 100.0).mean()
            tag = " <- discovery" if sym == "QQQ" else ""
            print(f"  ORB{om:<3} band {b:<4}{sym:<7}{len(R):>6,}{R.mean():>+9.4f}"
                  f"{se:>9.4f}{R.mean()/se:>+7.2f}{pf:>7.2f}{wr:>7.1f}"
                  f"{rw:>7.1f}{wr-rw:>+7.1f}{old:>+9.4f}{new:>+13.4f}"
                  f"{k:>5}{hc:>+9.4f}{tag}")

    # --------------------------------------------------------- pooled -------
    print("\n" + "=" * 128)
    print("  POOLED NON-QQQ ESTIMATE — SPY + IWM + IJH + EFA")
    print("=" * 128)
    print("  SE clustered by date. The 95% interval is the one the decision "
          "rule refers to;")
    print(f"  the Bonferroni interval at alpha = {P_BAR} over {N_VARIANTS} "
          f"variants is shown beside it.\n")
    print(f"  {'variant':<14}{'trades':>8}{'dates':>7}{'mean R':>9}{'sd':>8}"
          f"{'clus SE':>9}{'t':>7}{'95% CI':>24}{'Bonferroni CI':>26}")
    pooled = {}
    for om, b in VARIANTS:
        A = pd.concat([res[(om, b, s)][0].assign(inst=s) for s in INSTRUMENTS],
                      ignore_index=True)
        R = A.R.to_numpy(float)
        mu = R.mean()
        se, g = cluster_se(R, A.day.to_numpy())
        pooled[(om, b)] = dict(mu=mu, se=se, n=len(R), g=g, sd=R.std(ddof=1),
                               A=A)
        print(f"  ORB{om:<3} band {b:<4}{len(R):>8,}{g:>7,}{mu:>+9.4f}"
              f"{R.std(ddof=1):>8.4f}{se:>9.4f}{mu/se:>+7.2f}"
              f"   [{mu-Z_95*se:>+7.4f}, {mu+Z_95*se:>+7.4f}]"
              f"   [{mu-Z_BONF*se:>+7.4f}, {mu+Z_BONF*se:>+7.4f}]")

    # all eight instrument-variant cells pooled
    AA = pd.concat([res[(om, b, s)][0].assign(inst=s, variant=f"{om}{b}")
                    for om, b in VARIANTS for s in INSTRUMENTS],
                   ignore_index=True)
    R_all = AA.R.to_numpy(float)
    mu_all = float(R_all.mean())
    se_all, g_all = cluster_se(R_all, AA.day.to_numpy())
    n_all = len(R_all)
    print(f"  {'BOTH VARIANTS':<14}{n_all:>8,}{g_all:>7,}{mu_all:>+9.4f}"
          f"{R_all.std(ddof=1):>8.4f}{se_all:>9.4f}{mu_all/se_all:>+7.2f}"
          f"   [{mu_all-Z_95*se_all:>+7.4f}, {mu_all+Z_95*se_all:>+7.4f}]"
          f"   [{mu_all-Z_BONF*se_all:>+7.4f}, {mu_all+Z_BONF*se_all:>+7.4f}]")

    # ---------------------------------------- strengthened concentration ----
    print("\n" + "=" * 128)
    print("  THE STRENGTHENED CONCENTRATION TEST, ON THE POOLED ESTIMATE")
    print("=" * 128)
    print("  Remove max(10, top decile), whichever is stricter. Applied to "
          "every variant.\n")
    print(f"  {'set':<20}{'n':>7}{'mean R':>9}{'median':>9}{'k removed':>11}"
          f"{'after removal':>15}{'survives':>10}")
    conc = {}
    for om, b in VARIANTS:
        d = pooled[(om, b)]
        R = d["A"].R
        new, k = strict_drop(R)
        conc[(om, b)] = new
        print(f"  ORB{om:<3} band {b:<10}{len(R):>7,}{R.mean():>+9.4f}"
              f"{R.median():>+9.4f}{k:>11}{new:>+15.4f}"
              f"{('yes' if new > 0 else 'NO'):>10}")
    new_all, k_all = strict_drop(AA.R)
    print(f"  {'BOTH VARIANTS':<20}{n_all:>7,}{mu_all:>+9.4f}"
          f"{AA.R.median():>+9.4f}{k_all:>11}{new_all:>+15.4f}"
          f"{('yes' if new_all > 0 else 'NO'):>10}")

    # ------------------------------------------------------------- MDE ------
    print("\n" + "=" * 128)
    print("  MDE AGAINST THE OBSERVED EFFECT")
    print("=" * 128)
    print(f"  MDE = ({Z_BONF} + {Z_POW}) x clustered SE, at alpha = {P_BAR}, "
          f"80% power.\n")
    print(f"  {'variant':<14}{'n':>7}{'clus SE':>10}{'MDE':>10}"
          f"{'observed':>11}{'QQQ disc':>11}{'detectable?':>13}")
    for om, b in VARIANTS:
        d = pooled[(om, b)]
        mde = (Z_BONF + Z_POW) * d["se"]
        print(f"  ORB{om:<3} band {b:<4}{d['n']:>7,}{d['se']:>10.4f}"
              f"{mde:>+10.4f}{d['mu']:>+11.4f}{DISC[(om, b)]:>+11.4f}"
              f"{('YES' if d['mu'] >= mde else 'no'):>13}")
    mde_all = (Z_BONF + Z_POW) * se_all
    print(f"  {'BOTH VARIANTS':<14}{n_all:>7,}{se_all:>10.4f}{mde_all:>+10.4f}"
          f"{mu_all:>+11.4f}{'--':>11}"
          f"{('YES' if mu_all >= mde_all else 'no'):>13}")

    # --------------------------------------------------- decision rule ------
    print("\n" + "=" * 128)
    print("  THE DECLARED DECISION RULE")
    print("=" * 128)
    print("  Stays open only if the pooled non-QQQ estimate is POSITIVE, its")
    print("  interval EXCLUDES ZERO, and it SURVIVES the strengthened")
    print("  concentration test. Otherwise the family closes.\n")
    print(f"  {'variant':<16}{'positive':>10}{'CI excl 0':>12}"
          f"{'survives conc':>15}{'verdict':>12}")
    verdicts = []
    for om, b in VARIANTS:
        d = pooled[(om, b)]
        pos = d["mu"] > 0
        excl = (d["mu"] - Z_95 * d["se"]) > 0
        cc = np.isfinite(conc[(om, b)]) and conc[(om, b)] > 0
        ok = pos and excl and cc
        verdicts.append(ok)
        print(f"  ORB{om:<3} band {b:<6}{('yes' if pos else 'no'):>10}"
              f"{('yes' if excl else 'NO'):>12}{('yes' if cc else 'NO'):>15}"
              f"{('OPEN' if ok else 'CLOSE'):>12}")
    pos = mu_all > 0
    excl = (mu_all - Z_95 * se_all) > 0
    cc = np.isfinite(new_all) and new_all > 0
    ok = pos and excl and cc
    verdicts.append(ok)
    print(f"  {'BOTH VARIANTS':<16}{('yes' if pos else 'no'):>10}"
          f"{('yes' if excl else 'NO'):>12}{('yes' if cc else 'NO'):>15}"
          f"{('OPEN' if ok else 'CLOSE'):>12}")

    print(f"\n  RESULT: {'the family stays OPEN' if any(verdicts) else 'the family CLOSES'}.")
    print("\n  Sealed NQ days were not read. 2016-2020 remains sealed and "
          "unspent.")

    AA.to_csv(ROOT / "reports/orb_fib_instruments_trades.csv", index=False)


if __name__ == "__main__":
    main()
