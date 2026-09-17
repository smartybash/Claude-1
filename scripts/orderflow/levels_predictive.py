#!/usr/bin/env python3
"""DO PRIOR-DAY AND GAMMA LEVELS PREDICT THE NEXT SESSION?

Pre-registered at `d6539a1`
(`reports/levels_predictive_preregistration.md`) before this ran. Descriptive.
No rule is traded.

THE TEST THAT IS DELIBERATELY ABSENT

Containment -- "the next day's high stayed below the call wall 90% of the time"
-- is DEGENERATE and is not run. At a given distance the answer is fixed by
P(price travels that far); a wall, a random price and an arbitrary number all
score identically. No placebo repairs it, because a distance-matched placebo
returns a mathematically IDENTICAL answer, not a similar one. That 90% measures
"QQQ rarely moves 2% in a day" and says nothing about dealers.

THE TWO DESIGNS THAT ARE NOT DEGENERATE

  A  REACTION AT TOUCH. Counted only where price actually reached the level, so
     distance cannot do the work. Null is 50%: from a random walk started at the
     level, either side is equally likely. No placebo needed.

  B  TURNING-POINT CLUSTERING. Does the session's own high/low land nearer these
     levels than a STRANGER'S level set -- the same geometry taken from a random
     other session as relative offsets. 200 shuffles.

All eight levels come from the PRIOR session and are known before the open.

Sealed NQ days are not read: this script never opens the NQ tape.

Usage: python3 scripts/orderflow/levels_predictive.py
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data/intraday_long/QQQ_1m.parquet"
GEX = ROOT / "data/gex_history.jsonl"

MIN_BARS = 360
HORIZONS = (30, 60)
N_TESTS = 24
P_BAR = 0.05 / N_TESTS            # 0.00208
REACT_BAR = 0.55
MIN_TOUCH = 100
CLUSTER_BAR = 0.90
N_SHUFFLE = 200

PRICE_LV = ["PDH", "PDL", "VAH", "VAL", "POC"]
GAMMA_LV = ["call_wall", "put_wall", "gamma_flip"]
RNG = np.random.default_rng(0)


# ------------------------------------------------------------------ build --

def value_area(g, pct=0.70):
    """Standard 70%-of-volume region around the point of control."""
    px = ((g.high + g.low + g.close) / 3.0).to_numpy(float)
    vol = g.volume.to_numpy(float)
    step = max(float(np.nanstd(px)) / 50.0, 1e-4)
    bins = np.round(px / step).astype(int)
    prof = pd.Series(vol).groupby(bins).sum().sort_index()
    if prof.empty or prof.sum() <= 0:
        return np.nan, np.nan, np.nan
    poc_i = int(prof.idxmax())
    order = prof.index.to_numpy()
    target = pct * prof.sum()
    lo = hi = int(np.where(order == poc_i)[0][0])
    acc = float(prof.iloc[lo])
    while acc < target and (lo > 0 or hi < len(order) - 1):
        up = float(prof.iloc[hi + 1]) if hi < len(order) - 1 else -1.0
        dn = float(prof.iloc[lo - 1]) if lo > 0 else -1.0
        if up >= dn:
            hi += 1
            acc += up
        else:
            lo -= 1
            acc += dn
    return (order[hi] * step, order[lo] * step, poc_i * step)   # VAH, VAL, POC


def build():
    d = pd.read_parquet(SRC)
    d["day"] = d.timestamp.dt.date
    days = sorted(d.day.unique())
    prev = None
    out = []
    for day in days:
        g = d[d.day == day].sort_values("timestamp")
        if len(g) < MIN_BARS:
            prev = None
            continue
        vah, val, poc = value_area(g)
        cur = dict(hi=float(g.high.max()), lo=float(g.low.min()),
                   cl=float(g.close.iloc[-1]), vah=vah, val=val, poc=poc)
        if prev is not None:
            out.append(dict(
                day=day, bars=g, prior_close=prev["cl"],
                PDH=prev["hi"], PDL=prev["lo"],
                VAH=prev["vah"], VAL=prev["val"], POC=prev["poc"]))
        prev = cur
    return out


def gamma_map(days):
    rows = [json.loads(l) for l in open(GEX) if l.strip()]
    G = pd.DataFrame(rows)
    G = G[G.sym == "QQQ"].copy()
    G["date"] = pd.to_datetime(G.date).dt.date
    G = G.drop_duplicates("date").sort_values("date")
    order = {dd: i for i, dd in enumerate(days)}
    out = {}
    for _, r in G.iterrows():
        i = order.get(r.date)
        if i is None or i + 1 >= len(days):
            continue
        out[days[i + 1]] = dict(call_wall=float(r.call_wall),
                                put_wall=float(r.put_wall),
                                gamma_flip=float(r.gamma_flip))
    return out


# ------------------------------------------------- Test A: react at touch --

def react(bars, level, k):
    """First touch, then: is price back on the approach side k minutes later?"""
    hi = bars.high.to_numpy(float)
    lo = bars.low.to_numpy(float)
    cl = bars.close.to_numpy(float)
    n = len(cl)
    hit = np.where((lo <= level) & (hi >= level))[0]
    if len(hit) == 0:
        return None
    i = int(hit[0])
    if i == 0 or i + k >= n:
        return None
    side = np.sign(cl[i - 1] - level)          # approach side
    if side == 0:
        return None
    return bool(np.sign(cl[i + k] - level) == side)


# --------------------------------------- Test B: turning-point clustering --

def nearest(levels, price):
    lv = np.array([x for x in levels if np.isfinite(x)], dtype=float)
    return float(np.min(np.abs(lv - price))) if len(lv) else np.nan


def cluster(S, names, gm=None):
    """Real level set vs a stranger's, matched on geometry, 200 shuffles."""
    rows = []
    for s in S:
        lv = [s.get(k) for k in names if k in s]
        if gm is not None:
            g = gm.get(s["day"])
            if g is None:
                continue
            lv += [g[k] for k in names if k in g]
        lv = [x for x in lv if x is not None and np.isfinite(x)]
        if len(lv) < 2:
            continue
        pc = s["prior_close"]
        rows.append(dict(day=s["day"], pc=pc,
                         off=np.array([(x - pc) / pc for x in lv]),
                         hi=float(s["bars"].high.max()),
                         lo=float(s["bars"].low.min())))
    if len(rows) < 50:
        return None
    real = []
    for r in rows:
        lv = r["pc"] * (1 + r["off"])
        real += [1e4 * nearest(lv, r["hi"]) / r["pc"],
                 1e4 * nearest(lv, r["lo"]) / r["pc"]]
    sham = []
    for _ in range(N_SHUFFLE):
        j = RNG.integers(0, len(rows), len(rows))
        for r, q in zip(rows, (rows[x] for x in j)):
            lv = r["pc"] * (1 + q["off"])         # stranger's geometry, today's price
            sham += [1e4 * nearest(lv, r["hi"]) / r["pc"],
                     1e4 * nearest(lv, r["lo"]) / r["pc"]]
    return (float(np.median(real)), float(np.median(sham)),
            float(np.median(real) / np.median(sham)), len(rows))


# ------------------------------------------------------------------- run --

def binom_p(k, n, p0=0.5):
    if n == 0:
        return np.nan
    z = (k / n - p0) / np.sqrt(p0 * (1 - p0) / n)
    try:
        from scipy import stats
        return float(2 * stats.norm.sf(abs(z)))
    except Exception:
        from math import erfc, sqrt
        return float(erfc(abs(z) / sqrt(2)))


def main():
    print("=" * 106)
    print("  DO PRIOR-DAY AND GAMMA LEVELS PREDICT THE NEXT SESSION? "
          "DESCRIPTIVE.")
    print("=" * 106)
    print("  The containment test ('high stayed below the call wall 90%') is "
          "DEGENERATE and is NOT run.")
    print("  At a fixed distance a wall, a random price and an arbitrary "
          "number score identically.")
    print(f"\n  Pass: reaction >= {REACT_BAR:.0%}, p < {P_BAR:.5f} "
          f"(Bonferroni/{N_TESTS}), >= {MIN_TOUCH} touches; "
          f"clustering ratio <= {CLUSTER_BAR}")

    S = build()
    days = sorted({s["day"] for s in S})
    gm = gamma_map(sorted(pd.read_parquet(SRC).timestamp.dt.date.unique()))
    ng = sum(1 for s in S if s["day"] in gm)
    print(f"\n  price-level sessions {len(S):,}   {days[0]} to {days[-1]}")
    print(f"  gamma-level sessions {ng:,}")

    print("\n" + "=" * 106)
    print("  TEST A — REACTION AT TOUCH.  Counted only where price REACHED the "
          "level, so distance cannot")
    print("  do the work. Null is 50%: from a walk started at the level either "
          "side is equally likely.")
    print("=" * 106)
    print(f"  {'level':<12}{'group':<9}{'touched':>9}{'touch%':>8}"
          f"{'react 30m':>11}{'p':>11}{'react 60m':>11}{'p':>11}{'verdict':>9}")

    rowsA = []
    for name in PRICE_LV + GAMMA_LV:
        is_g = name in GAMMA_LV
        pool = [s for s in S if s["day"] in gm] if is_g else S
        res = {}
        for k in HORIZONS:
            hits = []
            for s in pool:
                lv = gm[s["day"]][name] if is_g else s.get(name)
                if lv is None or not np.isfinite(lv):
                    continue
                r = react(s["bars"], lv, k)
                if r is not None:
                    hits.append(r)
            res[k] = (sum(hits), len(hits))
        n30, t30 = res[30][0], res[30][1]
        n60, t60 = res[60][0], res[60][1]
        if t30 == 0:
            continue
        r30, r60 = n30 / t30, (n60 / t60 if t60 else np.nan)
        p30, p60 = binom_p(n30, t30), binom_p(n60, t60)
        ok = any(r >= REACT_BAR and p < P_BAR and t >= MIN_TOUCH
                 for r, p, t in ((r30, p30, t30), (r60, p60, t60)))
        rowsA.append(dict(level=name, group="gamma" if is_g else "price",
                          touches=t30, r30=r30, p30=p30, r60=r60, p60=p60,
                          passes=ok))
        print(f"  {name:<12}{('gamma' if is_g else 'price'):<9}{t30:>9,}"
              f"{100*t30/max(len(pool),1):>7.0f}%{100*r30:>10.1f}%{p30:>11.2e}"
              f"{100*r60:>10.1f}%{p60:>11.2e}"
              f"{('PASS' if ok else '--'):>9}")

    print("\n  touch% = share of sessions in which price reached the level at "
          "all.")

    print("\n" + "=" * 106)
    print("  TEST B — DO THE SESSION'S OWN HIGH AND LOW LAND NEARER THESE "
          "LEVELS THAN A STRANGER'S?")
    print("=" * 106)
    print(f"  {'level set':<26}{'sessions':>10}{'real bps':>11}"
          f"{'placebo bps':>13}{'ratio':>9}{'verdict':>10}")
    rowsB = []
    for label, names, g in (("prior-day (PDH/PDL)", ["PDH", "PDL"], None),
                            ("value area (VAH/VAL/POC)",
                             ["VAH", "VAL", "POC"], None),
                            ("all five price levels", PRICE_LV, None),
                            ("gamma (walls + flip)", GAMMA_LV, gm),
                            ("price + gamma combined", PRICE_LV, gm)):
        nm = names + (GAMMA_LV if g is not None else [])
        c = cluster(S, nm, g)
        if c is None:
            continue
        real, sham, ratio, n = c
        ok = ratio <= CLUSTER_BAR
        rowsB.append(dict(set=label, n=n, real=real, sham=sham, ratio=ratio,
                          passes=ok))
        print(f"  {label:<26}{n:>10,}{real:>11.1f}{sham:>13.1f}{ratio:>9.3f}"
              f"{('PASS' if ok else '--'):>10}")
    print("  ratio < 1 means the real levels sit CLOSER to the day's turning "
          f"points than a stranger's.\n  Bar is {CLUSTER_BAR}.")

    print("\n" + "=" * 106)
    print("  VERDICT")
    print("=" * 106)
    A = pd.DataFrame(rowsA)
    B = pd.DataFrame(rowsB)
    pa, pb = int(A.passes.sum()), int(B.passes.sum())
    print(f"  Test A (reaction at touch):        {pa} of {len(A)} levels pass")
    print(f"  Test B (turning-point clustering): {pb} of {len(B)} sets pass")
    best = A.loc[A[["r30", "r60"]].max(axis=1).idxmax()]
    print(f"\n  strongest reaction anywhere: {best.level} "
          f"{100*max(best.r30, best.r60):.1f}%   bar is {REACT_BAR:.0%}, "
          f"coin is 50%")
    print(f"  best clustering ratio:       {B.ratio.min():.3f} "
          f"({B.loc[B.ratio.idxmin(),'set']})   bar is {CLUSTER_BAR}")
    if pa == 0 and pb == 0:
        print("\n  NOTHING PASSES. These levels describe where the market has "
              "been.")
        print("  They do not measurably move where it goes next.")
    A.to_csv(ROOT / "reports/levels_predictive_A.csv", index=False)
    B.to_csv(ROOT / "reports/levels_predictive_B.csv", index=False)
    print("\n  Sealed NQ days were not read.")


if __name__ == "__main__":
    main()
