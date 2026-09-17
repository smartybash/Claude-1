#!/usr/bin/env python3
"""DOES DEALER GAMMA PREDICT THE LATER REGIME? Predictors 8 and 9.

Pre-registered at `dd6e7ea`
(`reports/regime_forecast_gamma_preregistration.md`) before this ran. An
amendment to the 14-combination run that returned 0 of 14.

THE QUESTION, UNCHANGED

Does information available at the decision timestamp predict whether the
REMAINDER of the session trends or chops? Same outcome, same constraint:

  predictor window ends at or before D  |  outcome window starts at D
                          they share no bars

WHY GAMMA IS A FAIR CANDIDATE

Gamma is already established ON THIS PROJECT'S OWN DATA as a predictor of range
-- terciles 1.85/1.55/1.24%, corr(distance-below-flip, next-day range) = +0.40.
But range is a volatility quantity and eff_later is scale-free by construction.
The original run found price-based predictors forecasting later VOLATILITY at
rho up to 0.414 and later EFFICIENCY at rho <= 0.042. This asks whether gamma
breaks that pattern or repeats it.

Both predictors come from the chain as-of the PRIOR CLOSE, so they are known
before the session opens -- a wider causal margin than the price-based
candidates, which needed bars from inside the session. Alignment is strict: a
session is used only where its gamma row is the immediately preceding trading
session. No stale rows, no forward fill.

PASS REQUIRES ALL THREE:
  |rho| >= 0.10, p < 0.002778 (Bonferroni over 18), decile spread >= 0.020

At n=323 the significance gate binds harder than the rho floor, demanding
rho ~= 0.167. Declared in the pre-registration, not discovered here.

Sealed NQ days are not read: this script never opens the NQ tape.

Usage: python3 scripts/orderflow/regime_forecast_gamma.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from regime_forecast import (ROOT, G_OR, deciles, measure, pearson,  # noqa
                             pval, sessions, spearman)

GEX = ROOT / "data/gex_history.jsonl"

N_TESTS = 18                      # 14 original + 4 new (2 predictors x 2 windows)
P_BAR = 0.05 / N_TESTS            # 0.002778
RHO_BAR = 0.10
SPREAD_BAR = 0.020

GPRED = ["net_gex", "dist_flip"]


def gamma_frame(sess_dates):
    """Gamma from the chain as-of the close of session t-1, mapped to session t.

    Strict: only the IMMEDIATELY preceding trading session counts."""
    rows = [json.loads(l) for l in open(GEX) if l.strip()]
    G = pd.DataFrame(rows)
    G = G[G.sym == "QQQ"].copy()
    G["date"] = pd.to_datetime(G.date).dt.date
    G = G.drop_duplicates("date").sort_values("date")

    order = {d: i for i, d in enumerate(sess_dates)}
    out = []
    for _, r in G.iterrows():
        i = order.get(r.date)
        if i is None or i + 1 >= len(sess_dates):
            continue
        spot, flip = float(r.spot), float(r.gamma_flip)
        out.append(dict(
            day=sess_dates[i + 1],                 # the session it predicts
            chain_day=r.date,
            net_gex=float(r.net_gex),
            dist_flip=1e4 * (spot - flip) / spot if spot else np.nan))
    return pd.DataFrame(out)


def block(F, or_min, outcome, label, results, tag=""):
    print("\n" + "=" * 104)
    print(f"  OUTCOME: {label}")
    print(f"  D = open + {or_min} min{tag}")
    print("=" * 104)
    print(f"  {'predictor':<12}{'n':>7}{'Spearman':>10}{'p':>12}{'Pearson':>10}"
          f"{'bottom d1':>12}{'top d10':>11}{'spread':>11}{'verdict':>10}")
    for p in GPRED:
        d = F[[p, outcome]].dropna()
        n = len(d)
        if n < 100:
            print(f"  {p:<12}{n:>7}   insufficient")
            continue
        rho, pr = spearman(d[p], d[outcome]), pearson(d[p], d[outcome])
        pv = pval(rho, n)
        dec = deciles(d[p], d[outcome])
        lad, spread = dec if dec else (None, np.nan)
        d1 = lad["mean"].iloc[0] if lad is not None else np.nan
        d10 = lad["mean"].iloc[-1] if lad is not None else np.nan
        ok = abs(rho) >= RHO_BAR and pv < P_BAR and abs(spread) >= SPREAD_BAR
        if outcome == "eff_later" and results is not None:
            results.append(dict(pred=p, or_min=or_min, n=n, rho=rho, p=pv,
                                pearson=pr, spread=spread, passes=ok,
                                ladder=lad))
        fmt = "{:>12.4f}{:>11.4f}{:>11.4f}" if outcome == "eff_later" \
            else "{:>12.2f}{:>11.2f}{:>11.2f}"
        print(f"  {p:<12}{n:>7,}{rho:>+10.3f}{pv:>12.2e}{pr:>+10.3f}"
              + fmt.format(d1, d10, spread)
              + "{:>10}".format("PASS" if ok else "--"))


def main():
    print("=" * 104)
    print("  DOES DEALER GAMMA PREDICT WHETHER THE REST OF THE SESSION TRENDS "
          "OR CHOPS?")
    print("=" * 104)
    print("  Predictors 8 and 9, amending the run that returned 0 of 14. "
          "Descriptive; no rule is traded.")
    print(f"  Pass requires ALL THREE: |rho| >= {RHO_BAR}, p < {P_BAR:.6f} "
          f"(Bonferroni/{N_TESTS}), spread >= {SPREAD_BAR}")
    print("  Gamma is from the chain as-of the PRIOR CLOSE, so it is known "
          "before the session opens.")

    S, _ = sessions()
    sess_dates = sorted(S)
    Gm = gamma_frame(sess_dates)
    print(f"\n  QQQ gamma rows aligned to a following session: {len(Gm):,}")

    results = []
    for or_min in G_OR:
        F = measure(S, or_min)
        M = F.merge(Gm, on="day", how="inner")
        yr = pd.to_datetime(M.day).dt.year
        print("\n" + "-" * 104)
        print(f"  OR_MIN {or_min}:  {len(M):,} sessions carry both gamma and a "
              f"measurable outcome")
        print("  per year: " + "  ".join(
            f"{y} {int((yr == y).sum())}" for y in sorted(yr.unique())))
        print(f"  2025-2026 block: {int((yr >= 2025).sum())} of {len(M)} "
              f"= {100 * (yr >= 2025).mean():.0f}%   "
              f"(2022 absent -- the year-stability rule cannot be applied)")

        block(M, or_min, "eff_later",
              "EFFICIENCY AFTER D — THE REGIME, THE THING THE HYPOTHESIS NEEDS",
              results)
        block(M, or_min, "rv_later",
              "REALISED VOL AFTER D (bps) — POSITIVE CONTROL, NOT PART OF THE "
              "HYPOTHESIS", None)

        # Declared robustness read, named in the pre-registration as a
        # diagnostic rather than a gate.
        R = M[yr >= 2025]
        block(R, or_min, "eff_later",
              "EFFICIENCY AFTER D — DECLARED ROBUSTNESS READ, 2025-2026 ONLY "
              "(diagnostic, not a gate)", None, tag="   [2025-2026 block]")

    print("\n" + "=" * 104)
    print("  VERDICT")
    print("=" * 104)
    Rf = pd.DataFrame([{k: v for k, v in r.items() if k != "ladder"}
                       for r in results])
    passed = Rf[Rf.passes]
    print(f"  4 new predictor-window combinations tested against eff_later.")
    print(f"  cleared |rho| >= {RHO_BAR}:       "
          f"{int((Rf.rho.abs() >= RHO_BAR).sum())} of 4")
    print(f"  cleared p < {P_BAR:.6f}:     {int((Rf.p < P_BAR).sum())} of 4")
    print(f"  cleared spread >= {SPREAD_BAR}:   "
          f"{int((Rf.spread.abs() >= SPREAD_BAR).sum())} of 4")
    print(f"  cleared ALL THREE:          {len(passed)} of 4")
    i = Rf.rho.abs().idxmax()
    j = Rf.spread.abs().idxmax()
    print(f"\n  largest |rho|:    {Rf.rho.abs().max():.4f}  "
          f"({Rf.loc[i,'pred']} OR{Rf.loc[i,'or_min']})   "
          f"significance gate needs ~0.167 at this n")
    print(f"  largest |spread|: {Rf.spread.abs().max():.4f}  "
          f"({Rf.loc[j,'pred']} OR{Rf.loc[j,'or_min']})   bar is {SPREAD_BAR}")

    for idx in {i, j}:
        r = results[idx]
        print(f"\n  DECILE LADDER — {r['pred']} at OR{r['or_min']}, "
              f"eff_later   (spread {r['spread']:+.4f})")
        lad = r["ladder"]
        print("    decile " + "".join(f"{k+1:>8}" for k in range(len(lad))))
        print("    mean   " + "".join(f"{v:>8.4f}" for v in lad["mean"]))
        print("    n      " + "".join(f"{v:>8,}" for v in lad["count"]))

    print("\n" + "=" * 104)
    if passed.empty:
        print("  GAMMA DOES NOT PREDICT THE LATER REGIME EITHER. 0 of 4.")
        print("=" * 104)
        print("  Combined with the original run: 0 of 18 combinations across "
              "two independent")
        print("  predictor families -- price structure and dealer positioning.")
        print("  Stage 2 is NOT run. The 6-variant budget stays unspent.")
    else:
        print("  CANDIDATES CLEARING ALL THREE:")
        print(passed.to_string(index=False))
        print("\n  Stage 2 would require the 2022 gap to be filled FIRST -- the "
              "year-stability")
        print("  rule cannot be applied to a sample with a missing year.")

    Rf.to_csv(ROOT / "reports/regime_forecast_gamma_summary.csv", index=False)
    print("\n  Sealed NQ days were not read.")


if __name__ == "__main__":
    main()
