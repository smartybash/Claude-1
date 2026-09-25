#!/usr/bin/env python3
"""CONDITIONING EXISTING TRADE SETS ON PRE-OPEN VARIABLES.

Pre-registered at `242c9c4` (`reports/trade_conditioning_preregistration.md`)
before this file was written.

NO NEW RULE IS CREATED AND NOTHING IS RE-OPTIMISED. Every trade comes from a
module already frozen in the ledger, called unchanged. The only new thing is
the PARTITION of those trades by the six pre-open conditions from `32620b8`.

This tests expectancy directly rather than through the efficiency proxy, which
was the one gap the pre-open study left open.

THE BAR, DECLARED BEFORE RUNNING
  n >= 150, mean R > 0 after costs, positive after removing max(10, ceil(0.10n)),
  and >= 4 of 6 years positive.

THE CONTROL, WHICH GOVERNS
  5,000 random-label permutations with exactly matched group sizes. The observed
  best subset must beat the 95th percentile of the permuted MAXIMUM statistic
  across all subsets. If nothing does, the direction closes.

Sealed days stay sealed. 2016-2020 stays unread: QQQ_1m.parquet spans
2021-01-04 to 2026-08-31 and cannot reach the holdout.

Usage: python3 scripts/orderflow/trade_conditioning.py
"""
from __future__ import annotations

import sys
from math import ceil, sqrt
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parents[2]

N_FLOOR = 150
N_PERM = 5_000
PCTL = 95
YEARS_REQUIRED = 4
SEED = 20260920

CONT = ["vix_lvl", "vix_chg", "on_range", "on_disp", "prior_loc"]
BINARY = ["fomc"]
COND = CONT + BINARY
PARTS = [("top half", 0.50, "hi"), ("bottom half", 0.50, "lo"),
         ("top quartile", 0.25, "hi"), ("bottom quartile", 0.25, "lo")]


# ------------------------------------------------------------ trade sets --

def trade_sets():
    """Regenerate the frozen sets unchanged. No rule is touched here."""
    import reopen_study as RS
    import orb_fib as OF

    out = {}
    S = RS.load()
    for tg in (1.0, 2.0, 3.0, 4.0):
        T, _look = RS.test1(S, tg)
        T = T[["day", "year", "R"]].copy()
        if tg == 1.0:
            F, _ = RS.test1(S, 1.0)
            out["IB 1R single"] = F[F.seq == 1][["day", "year", "R"]].copy()
        out[f"IB {int(tg)}R re-entry"] = T

    SS = OF.load()
    for orb in (15, 30):
        C, _R, _d = OF.run(SS, orb, "A")
        C = C.copy()
        C["year"] = pd.to_datetime(C.day).dt.year
        out[f"ORB-Fib cont ORB{orb} A"] = C[["day", "year", "R"]].copy()
    return out


def conditions():
    import preopen as PO
    F, _rej, _noeth = PO.build()
    return F[["day", "year"] + COND].copy()


# ------------------------------------------------------------ statistics --

def cluster_t(R, codes, ng):
    """Date-clustered t of the mean. bincount keeps this fast enough to sit
    inside the permutation loop."""
    n = len(R)
    if n < 2:
        return np.nan, np.nan, np.nan
    mu = R.mean()
    d = np.bincount(codes, weights=R - mu, minlength=ng)
    g = np.count_nonzero(np.bincount(codes, minlength=ng))
    if g < 2:
        return mu, np.nan, np.nan
    se = sqrt((g / (g - 1.0)) * float((d ** 2).sum())) / n
    return float(mu), float(se), (float(mu / se) if se > 0 else np.nan)


def strict_drop(R):
    """THE STANDING RULE: drop max(10, top decile), whichever is stricter."""
    k = max(10, int(ceil(0.10 * len(R))))
    if k >= len(R):
        return np.nan, k
    s = np.sort(R)
    return float(s[:len(R) - k].mean()), k


def years_positive(R, years):
    d = pd.DataFrame({"R": R, "y": years})
    m = d.groupby("y").R.mean()
    return int((m > 0).sum()), int(len(m))


def masks_for(vals, kind):
    """Trade-space quantile cuts, so group sizes are exact by construction."""
    ok = np.isfinite(vals)
    idx = np.flatnonzero(ok)
    if len(idx) < 20:
        return []
    order = idx[np.argsort(vals[idx], kind="stable")]
    out = []
    for name, frac, side in PARTS:
        k = int(round(frac * len(order)))
        if k < 5:
            continue
        sel = order[-k:] if side == "hi" else order[:k]
        m = np.zeros(len(vals), bool)
        m[sel] = True
        out.append((name, m))
    return out


def binary_masks(vals):
    ok = np.isfinite(vals)
    a = ok & (vals > 0.5)
    b = ok & (vals <= 0.5)
    out = []
    if a.sum() >= 5:
        out.append(("FOMC = 1", a))
    if b.sum() >= 5:
        out.append(("FOMC = 0", b))
    return out


# ---------------------------------------------------------------- report --

def decile_ladder(R, vals, codes, ng):
    ok = np.isfinite(vals)
    if ok.sum() < 100:
        return None
    d = pd.DataFrame({"R": R[ok], "v": vals[ok],
                      "c": codes[ok]}).reset_index(drop=True)
    d["b"] = pd.qcut(d.v.rank(method="first"), 10, labels=False)
    rows = []
    for b, g in d.groupby("b"):
        mu, se, t = cluster_t(g.R.to_numpy(), g.c.to_numpy(), ng)
        rows.append(dict(decile=int(b) + 1, n=len(g), mean_R=mu, se=se, t=t))
    return pd.DataFrame(rows)


def main():
    rng = np.random.default_rng(SEED)
    SETS = trade_sets()
    C = conditions().set_index("day")

    print("=" * 112)
    print("  TRADE CONDITIONING — COUNTS AND BURDEN, BEFORE ANY PERFORMANCE NUMBER")
    print("=" * 112)

    prepped = {}
    for name, T in SETS.items():
        T = T[T.day.isin(C.index)].copy().reset_index(drop=True)
        for c in COND:
            T[c] = C.loc[T.day, c].to_numpy()
        codes, uniq = pd.factorize(T.day)
        prepped[name] = dict(T=T, R=T.R.to_numpy(float), codes=codes,
                             ng=len(uniq), years=T.year.to_numpy())
        print(f"  {name:<24} trades {len(T):>5}   dates {len(uniq):>5}   "
              f"trades/date {len(T)/len(uniq):>4.2f}   "
              f"can reach {N_FLOOR}: "
              f"{'yes' if len(T) >= N_FLOOR else 'NO — unresolvable'}")

    n_sub = sum(len(masks_for(p['T'][c].to_numpy(float), c)) if c in CONT
                else len(binary_masks(p['T'][c].to_numpy(float)))
                for p in prepped.values() for c in COND)
    print(f"\n  trade sets                 {len(SETS):>6}")
    print(f"  conditions                 {len(COND):>6}")
    print(f"  declared partitions        {len(PARTS):>6} continuous + 2 binary groups")
    print(f"  TOTAL SUBSETS EXAMINED     {n_sub:>6}")
    print(f"  trade floor for a claim    {N_FLOOR:>6}")
    print(f"  permutations               {N_PERM:>6}")
    print(f"  control percentile         {PCTL:>6}")
    print(f"  years required positive    {YEARS_REQUIRED} of 6")
    print("\n  R is already net of costs (COST_F subtracted before dividing by risk).")
    print("  IB sets 1-5 share entries and are NOT independent tests.")

    # ---------------------------------------------- decile ladders, asked --
    for name in ["IB 1R single", "IB 1R re-entry"]:
        p = prepped[name]
        for c in CONT:
            L = decile_ladder(p["R"], p["T"][c].to_numpy(float),
                              p["codes"], p["ng"])
            print("\n" + "-" * 112)
            print(f"  DECILE LADDER — {name}  by  {c}"
                  f"   (no decile can reach {N_FLOOR}; descriptive only)")
            print("-" * 112)
            if L is None:
                print("    insufficient")
                continue
            print("    " + "".join(f"{v:>9}" for v in L.decile.tolist()))
            print("  n " + "".join(f"{v:>9}" for v in L.n.tolist()))
            print("  R " + "".join(f"{v:>+9.3f}" for v in L.mean_R.tolist()))
            print("  t " + "".join(f"{v:>+9.2f}" for v in L.t.tolist()))
            print(f"  spread d10-d1 {L.mean_R.iloc[-1] - L.mean_R.iloc[0]:+.4f}")

    for name in SETS:
        if name in ("IB 1R single", "IB 1R re-entry"):
            continue
        p = prepped[name]
        print("\n" + "-" * 112)
        print(f"  DECILE SPREADS — {name}   (compact)")
        print("-" * 112)
        for c in CONT:
            L = decile_ladder(p["R"], p["T"][c].to_numpy(float),
                              p["codes"], p["ng"])
            if L is None:
                print(f"    {c:<12} insufficient (n<100)")
                continue
            print(f"    {c:<12} n/decile {int(L.n.mean()):>4}   "
                  f"d1 {L.mean_R.iloc[0]:>+7.3f}   d10 {L.mean_R.iloc[-1]:>+7.3f}"
                  f"   spread {L.mean_R.iloc[-1]-L.mean_R.iloc[0]:>+7.3f}"
                  f"   best {L.mean_R.max():>+7.3f}")

    # --------------------------------------------- the declared subsets ---
    print("\n" + "=" * 112)
    print("  THE DECLARED SUBSETS — every one examined, claimable or not")
    print("=" * 112)
    print(f"  {'set':<20}{'condition':<11}{'partition':<16}{'n':>6}{'mean R':>9}"
          f"{'clus SE':>9}{'t':>7}{'after conc':>12}{'yrs':>6}{'n>=150':>8}"
          f"{'PASS':>6}")

    rows, obs_t = [], []
    for name, p in prepped.items():
        R, codes, ng, yrs = p["R"], p["codes"], p["ng"], p["years"]
        for c in COND:
            v = p["T"][c].to_numpy(float)
            ms = masks_for(v, c) if c in CONT else binary_masks(v)
            for pname, m in ms:
                n = int(m.sum())
                mu, se, t = cluster_t(R[m], codes[m], ng)
                conc, k = strict_drop(R[m])
                yp, yt = years_positive(R[m], yrs[m])
                claimable = n >= N_FLOOR
                ok = (claimable and mu > 0 and np.isfinite(conc) and conc > 0
                      and yp >= YEARS_REQUIRED)
                obs_t.append(t if np.isfinite(t) else -np.inf)
                rows.append(dict(set=name, cond=c, part=pname, n=n, mean_R=mu,
                                 se=se, t=t, after_conc=conc, k_dropped=k,
                                 years=f"{yp}/{yt}", claimable=claimable,
                                 passed=ok))
                print(f"  {name:<20}{c:<11}{pname:<16}{n:>6}{mu:>+9.4f}"
                      f"{se:>9.4f}{t:>+7.2f}{conc:>+12.4f}{yp:>3}/{yt:<2}"
                      f"{'yes' if claimable else 'NO':>8}"
                      f"{'PASS' if ok else '.':>6}")

    D = pd.DataFrame(rows)
    D.to_csv(ROOT / "reports/trade_conditioning.csv", index=False)
    obs_t = np.asarray(obs_t)

    # ------------------------------------------- the random-label control --
    print("\n" + "=" * 112)
    print("  RANDOM-LABEL CONTROL — matched group sizes, max statistic")
    print("=" * 112)
    print("  Conditions are permuted across dates WITHIN each condition's own")
    print("  valid dates, so every subset has exactly the size it has in the")
    print("  real data. This breaks cross-condition correlation, which makes")
    print("  the permuted maximum LARGER and therefore the bar HARDER.")

    day_idx, valid = {}, {}
    Cd = C.reset_index()
    pos = {d: i for i, d in enumerate(Cd.day)}
    for name, p in prepped.items():
        day_idx[name] = p["T"].day.map(pos).to_numpy()
    for c in COND:
        valid[c] = np.flatnonzero(np.isfinite(Cd[c].to_numpy(float)))

    Cvals = {c: Cd[c].to_numpy(float) for c in COND}
    perm_max = np.empty(N_PERM)
    per_set_max = {name: np.empty(N_PERM) for name in prepped}

    for it in range(N_PERM):
        shuf = {}
        for c in COND:
            v = Cvals[c].copy()
            idx = valid[c]
            v[idx] = v[rng.permutation(idx)]
            shuf[c] = v
        gmax = -np.inf
        for name, p in prepped.items():
            R, codes, ng = p["R"], p["codes"], p["ng"]
            di = day_idx[name]
            smax = -np.inf
            for c in COND:
                pv = shuf[c][di]
                ms = masks_for(pv, c) if c in CONT else binary_masks(pv)
                for _pn, m in ms:
                    _mu, _se, t = cluster_t(R[m], codes[m], ng)
                    if np.isfinite(t) and t > smax:
                        smax = t
            per_set_max[name][it] = smax
            gmax = max(gmax, smax)
        perm_max[it] = gmax

    bar = float(np.percentile(perm_max, PCTL))
    best_i = int(np.argmax(obs_t))
    best = D.iloc[best_i]

    print(f"\n  permuted GLOBAL max t, 95th percentile   {bar:>+8.3f}")
    print(f"  permuted GLOBAL max t, median            "
          f"{float(np.median(perm_max)):>+8.3f}")
    print(f"  observed best t across all subsets       {obs_t.max():>+8.3f}")
    print(f"  that subset                              "
          f"{best['set']} / {best['cond']} / {best['part']}  (n={best['n']})")
    print(f"  beats the control?                       "
          f"{'YES' if obs_t.max() > bar else 'NO'}")
    print(f"  empirical p of the observed max          "
          f"{(np.sum(perm_max >= obs_t.max()) + 1) / (N_PERM + 1):>8.4f}")

    print(f"\n  {'set':<24}{'obs max t':>11}{'perm 95th':>11}{'beats?':>9}")
    for name in prepped:
        o = D[D.set == name].t.max()
        b = float(np.percentile(per_set_max[name], PCTL))
        print(f"  {name:<24}{o:>+11.3f}{b:>+11.3f}"
              f"{'YES' if o > b else 'no':>9}")

    # ------------------------------------------------------- the decision --
    print("\n" + "=" * 112)
    print("  THE DECLARED DECISION")
    print("=" * 112)
    claim = D[D.claimable]
    print(f"  subsets examined                         {len(D):>6}")
    print(f"  of those, claimable (n >= {N_FLOOR})          {len(claim):>6}")
    print(f"  unresolvable on size                     {len(D) - len(claim):>6}")
    print(f"  passing all four bars                    {int(D.passed.sum()):>6}")
    print(f"  claimable subsets with mean R > 0        "
          f"{int((claim.mean_R > 0).sum()):>6}")
    print(f"  ... and surviving the concentration rule "
          f"{int(((claim.mean_R > 0) & (claim.after_conc > 0)).sum()):>6}")
    print()
    if obs_t.max() > bar and D.passed.sum() > 0:
        print("  A subset beats the control AND passes all four bars.")
    else:
        print("  NO SUBSET BEATS THE 95TH PERCENTILE OF THE RANDOM-LABEL MAXIMUM.")
        print("  Per the pre-registration, THE DIRECTION CLOSES. No new hypotheses.")
    print()
    print("  2016-2020 was not read. Sealed days were not read.")


if __name__ == "__main__":
    sys.exit(main())
