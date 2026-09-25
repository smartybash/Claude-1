#!/usr/bin/env python3
"""COMPRESSED MULTI-DAY RANGE, RESOLVED AND HELD — measurement module.

Pre-registered at `2417092`, amended at `02e0746` and in AMENDMENT 2 below.

THE RULE
  RANGE  = high/low of the prior 3 RTH sessions (today excluded). Width W bps.
  k      = W / trailing-20 mean of W, shifted. Compression.
  D      = 10:00 or 10:30 ET.

  TRIGGER, all four:
    1  k <= C_FROZEN                      compressed
    2  W >= W_FLOOR_BPS                   economically viable, cost written in
    3  the D bar CLOSED outside RANGE     resolved; direction = side broken
    4  still outside at D                 held (a reverted break does not count)

  ENTRY  open of the bar after D. Entry bar EXCLUDED from the exit search.
  STOP   the OPPOSITE edge of RANGE -/+ BUFFER. Risk ~ W + overshoot.
  EXIT   flat 16:00 ET; variants add a +0.5R or +1.0R target.

  6 VARIANTS = 3 exits x 2 decision timestamps. N=3 fixed. Nothing else swept.

HEADLINE (Amendment 1)
  excess_R = R - d * drift_frac_D * px / risk
  drift_frac_D is an UNCONDITIONAL constant per timestamp: the mean over ALL
  sessions of (close_16:00 - open at D+1) / px. It removes the expected profit
  of a directional position of sign d, sized 1/risk, over the same clock window.
  Long and short arms are reported separately, always, before any pooled row.

AMENDMENT 2, declared before the expectancy pass ran
  The proposal's random-label control was "permute the trade direction". That is
  STRUCTURALLY UNDEFINED here: a session that broke UP has its stop at the range
  LOW, so the mirrored short has no valid stop at a range edge and the trade
  cannot be constructed. Replaced with the control that actually tests the
  claim: PERMUTE THE COMPRESSION VALUE k ACROSS SESSIONS, recompute which
  sessions trigger, and recompute the statistic. Group sizes match exactly. This
  isolates whether compression specifically selects anything, holding the
  structural conditions (resolved, held, W floor) fixed -- which is the
  mechanism claim itself.

Sealed NQ days are not read. 2016-2020 is not read: QQQ_1m.parquet spans
2021-01-04 to 2026-08-31 and cannot reach the holdout.

Usage:
  python3 scripts/orderflow/compression.py calibrate   # counts and widths ONLY
  python3 scripts/orderflow/compression.py run         # expectancy, frozen c
"""
from __future__ import annotations

import datetime as dt
import sys
from math import ceil, sqrt
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data/intraday_long/QQQ_1m.parquet"

MIN_BARS = 360
COST_F = 2.00 / 30000.0
BUFFER = 0.01
N_RANGE = 3
TRAIL_N = 20
W_FLOOR_BPS = 150.0
FIRST_YEAR = 2021
SEALED_PREFIX, SEALED_DATES = "202606", {"20260723"}

D_MINS = {"10:00": 30, "10:30": 60}
TARGETS = {"flat": None, "+0.5R": 0.5, "+1.0R": 1.0}
VARIANTS = [(d, t) for d in D_MINS for t in TARGETS]      # 2 x 3 = 6

TARGET_LO, TARGET_HI = 3.0, 6.0          # trades per month, declared
TARGET_MID = 4.5
COST_REJECT_PCT = 0.50                   # design-grounds rejection threshold

# Frozen by the counts-only calibration pass. None until then.
C_FROZEN = 1.00        # FROZEN by the counts-only pass, Amendment 3

N_PERM = 5_000
PCTL = 95
YEARS_REQUIRED = 4


# ------------------------------------------------------------------ build --

def load():
    d = pd.read_parquet(SRC)
    d = d[d.timestamp.dt.year >= FIRST_YEAR]          # 2016-2020 stays unread
    d["day"] = d.timestamp.dt.date
    d["ds"] = d.timestamp.dt.strftime("%Y%m%d")
    d = d[~d.ds.str.startswith(SEALED_PREFIX)]
    d = d[~d.ds.isin(SEALED_DATES)]
    out = []
    for day, g in d.groupby("day", sort=True):
        g = g.sort_values("timestamp")
        if len(g) < MIN_BARS:
            continue
        o = pd.Timestamp(dt.datetime.combine(day, dt.time(9, 30)))
        c = pd.Timestamp(dt.datetime.combine(day, dt.time(16, 0)))
        if g.timestamp.iloc[0] > o or g.timestamp.iloc[-1] < c - pd.Timedelta(minutes=5):
            continue
        g = g[(g.timestamp >= o) & (g.timestamp <= c)]
        out.append(dict(
            day=day, year=day.year,
            t=(g.timestamp - o).dt.total_seconds().to_numpy() / 60.0,
            hi=g.high.to_numpy(float), lo=g.low.to_numpy(float),
            op=g.open.to_numpy(float), cl=g.close.to_numpy(float),
            px=float(g.open.iloc[0])))
    return out


def frame(S):
    """Per-session RANGE, width and compression. Nothing reads today's bars."""
    hi = np.array([s["hi"].max() for s in S])
    lo = np.array([s["lo"].min() for s in S])
    px = np.array([s["px"] for s in S])
    H = pd.Series(hi).rolling(N_RANGE).max().shift(1).to_numpy()
    L = pd.Series(lo).rolling(N_RANGE).min().shift(1).to_numpy()
    W = 1e4 * (H - L) / px
    trail = pd.Series(W).rolling(TRAIL_N, min_periods=TRAIL_N).mean().shift(1)
    k = W / trail.to_numpy()
    for i, s in enumerate(S):
        s["H3"], s["L3"], s["W"], s["k"] = H[i], L[i], W[i], k[i]
    return S


def drift_fracs(S):
    """Unconditional mean (close - open at D+1)/px over ALL sessions."""
    out = {}
    for dlab, dmin in D_MINS.items():
        v = []
        for s in S:
            i = int(np.searchsorted(s["t"], dmin, "left"))
            if i >= len(s["t"]) - 2:
                continue
            v.append((s["cl"][-1] - s["op"][i]) / s["px"])
        out[dlab] = float(np.mean(v))
    return out


# ------------------------------------------------------------- the rule ---

def setup(s, dmin, kval=None, require_held=True):
    """Structure at D. kval overrides s['k'] for the permutation control.
    Returns None or a dict; reads NO bar after the entry bar."""
    k = s["k"] if kval is None else kval
    if not np.isfinite(k) or not np.isfinite(s["W"]):
        return None
    if s["W"] < W_FLOOR_BPS:
        return None
    if C_FROZEN is None or k > C_FROZEN:
        return None
    iD = int(np.searchsorted(s["t"], dmin, "left")) - 1       # bar closing at D
    ie = iD + 1                                               # entry bar
    if iD < 5 or ie >= len(s["t"]) - 2:
        return None
    cD = s["cl"][iD]
    out_up, out_dn = cD > s["H3"], cD < s["L3"]
    if require_held:
        if not (out_up or out_dn):
            return None
        d = 1 if out_up else -1
    else:
        # NOT-HELD control arm: broke before D, but D closed back inside.
        if out_up or out_dn:
            return None
        pre = slice(0, iD + 1)
        up = bool((s["hi"][pre] > s["H3"]).any())
        dn = bool((s["lo"][pre] < s["L3"]).any())
        if up == dn:                       # neither, or both -> ambiguous
            return None
        d = 1 if up else -1
    fill = float(s["op"][ie])
    stop = (s["L3"] - BUFFER) if d > 0 else (s["H3"] + BUFFER)
    risk = abs(fill - stop)
    if risk <= 0:
        return None
    return dict(d=d, ie=ie, fill=fill, stop=stop, risk=risk, k=k)


def walk(s, u, tg):
    """Exit search from ie+1. Entry bar EXCLUDED. Honest fills, naive alongside."""
    hi, lo, op, cl = s["hi"], s["lo"], s["op"], s["cl"]
    d, fill, stop, risk = u["d"], u["fill"], u["stop"], u["risk"]
    n = len(cl)
    tgt = fill + d * tg * risk if tg else None
    cost = s["px"] * COST_F
    mfe = mae = 0.0
    amb = False
    for j in range(u["ie"] + 1, n):
        fav = d * (hi[j] - fill) if d > 0 else d * (lo[j] - fill)
        adv = d * (lo[j] - fill) if d > 0 else d * (hi[j] - fill)
        mfe = max(mfe, fav)
        mae = min(mae, adv)
        st = lo[j] <= stop if d > 0 else hi[j] >= stop
        ht = (hi[j] >= tgt if d > 0 else lo[j] <= tgt) if tg else False
        if st and ht:
            amb = True
        if st:
            ex = min(stop, op[j]) if d > 0 else max(stop, op[j])
            return dict(R=(d * (ex - fill) - cost) / risk, why="stop",
                        naive_R=(d * (stop - fill) - cost) / risk,
                        mfe=mfe / risk, mae=mae / risk, amb=amb)
        if ht:
            return dict(R=(d * (tgt - fill) - cost) / risk, why="target",
                        naive_R=(d * (tgt - fill) - cost) / risk,
                        mfe=mfe / risk, mae=mae / risk, amb=amb)
    ex = cl[n - 1]
    return dict(R=(d * (ex - fill) - cost) / risk, why="close",
                naive_R=(d * (ex - fill) - cost) / risk,
                mfe=mfe / risk, mae=mae / risk, amb=amb)


def trades(S, dlab, tlab, drift, kmap=None, require_held=True):
    dmin, tg = D_MINS[dlab], TARGETS[tlab]
    rows = []
    for i, s in enumerate(S):
        u = setup(s, dmin, None if kmap is None else kmap[i], require_held)
        if u is None:
            continue
        r = walk(s, u, tg)
        bench = u["d"] * drift[dlab] * s["px"] / u["risk"]
        rows.append(dict(
            day=s["day"], year=s["year"], d=u["d"], k=u["k"],
            W=s["W"], risk_bps=1e4 * u["risk"] / s["px"],
            cost_pct=100.0 * s["px"] * COST_F / u["risk"],
            R=r["R"], naive_R=r["naive_R"], excess_R=r["R"] - bench,
            bench_R=bench, why=r["why"], mfe=r["mfe"], mae=r["mae"],
            amb=r["amb"],
            hold_R=u["d"] * (s["cl"][-1] - u["fill"]) / u["risk"]))
    return pd.DataFrame(rows)


# ------------------------------------------------------------ statistics --

def cluster_t(x, days):
    x = np.asarray(x, float)
    n = len(x)
    if n < 2:
        return np.nan, np.nan, np.nan
    mu = x.mean()
    dv = pd.Series(x - mu).groupby(np.asarray(days)).sum().to_numpy()
    g = len(dv)
    if g < 2:
        return mu, np.nan, np.nan
    se = sqrt((g / (g - 1.0)) * float((dv ** 2).sum())) / n
    return float(mu), float(se), (float(mu / se) if se > 0 else np.nan)


def strict_drop(x):
    x = np.asarray(x, float)
    k = max(10, int(ceil(0.10 * len(x))))
    if k >= len(x):
        return np.nan, k
    return float(np.sort(x)[:len(x) - k].mean()), k


def years_pos(x, years):
    m = pd.DataFrame({"x": x, "y": years}).groupby("y").x.mean()
    return int((m > 0).sum()), int(len(m))


# --------------------------------------------------------- calibration ----

def structural(s, dmin, c):
    """Counts and widths ONLY. Deliberately returns no R and never calls walk."""
    if not np.isfinite(s["k"]) or not np.isfinite(s["W"]):
        return None
    if s["W"] < W_FLOOR_BPS or s["k"] > c:
        return None
    iD = int(np.searchsorted(s["t"], dmin, "left")) - 1
    ie = iD + 1
    if iD < 5 or ie >= len(s["t"]) - 2:
        return None
    cD = s["cl"][iD]
    if cD > s["H3"]:
        d, stop = 1, s["L3"] - BUFFER
    elif cD < s["L3"]:
        d, stop = -1, s["H3"] + BUFFER
    else:
        return None
    risk = abs(float(s["op"][ie]) - stop)
    if risk <= 0:
        return None
    return dict(d=d, risk_bps=1e4 * risk / s["px"],
                cost_pct=100.0 * s["px"] * COST_F / risk)


def calibrate():
    S = frame(load())
    months = len(pd.PeriodIndex([s["day"] for s in S], freq="M").unique())
    print("=" * 100)
    print("  CALIBRATION — COUNTS AND WIDTHS ONLY. NO R IS COMPUTED ANYWHERE IN THIS PASS.")
    print("=" * 100)
    print(f"  sessions {len(S)}   months {months}   "
          f"sessions/month {len(S)/months:.1f}")
    print(f"  target {TARGET_LO:.0f}-{TARGET_HI:.0f} trades/month, "
          f"frozen at the c closest to {TARGET_MID}")
    print(f"  W floor {W_FLOOR_BPS:.0f} bps   "
          f"design rejection if median cost/risk >= {COST_REJECT_PCT}%")
    print(f"\n  {'c':>6}{'trig 10:00':>12}{'trig 10:30':>12}{'mean/mo':>10}"
          f"{'long':>7}{'short':>7}{'risk p50':>10}{'cost% p50':>11}"
          f"{'cost% p75':>11}{'cost% p90':>11}")
    rows = []
    for c in np.arange(0.50, 1.31, 0.02):
        cnt, cp, rb, nl, ns = {}, [], [], 0, 0
        for dlab, dmin in D_MINS.items():
            u = [structural(s, dmin, c) for s in S]
            u = [x for x in u if x]
            cnt[dlab] = len(u)
            cp += [x["cost_pct"] for x in u]
            rb += [x["risk_bps"] for x in u]
            nl += sum(1 for x in u if x["d"] > 0)
            ns += sum(1 for x in u if x["d"] < 0)
        per_mo = (cnt["10:00"] + cnt["10:30"]) / 2.0 / months
        cp = np.asarray(cp)
        rows.append(dict(c=round(float(c), 2), n1=cnt["10:00"], n2=cnt["10:30"],
                         per_mo=per_mo, long=nl, short=ns,
                         risk50=np.median(rb) if len(rb) else np.nan,
                         cost50=np.median(cp) if len(cp) else np.nan,
                         cost75=np.percentile(cp, 75) if len(cp) else np.nan,
                         cost90=np.percentile(cp, 90) if len(cp) else np.nan))
        r = rows[-1]
        mark = " <-" if TARGET_LO <= per_mo <= TARGET_HI else ""
        print(f"  {r['c']:>6.2f}{r['n1']:>12}{r['n2']:>12}{r['per_mo']:>10.2f}"
              f"{r['long']:>7}{r['short']:>7}{r['risk50']:>10.1f}"
              f"{r['cost50']:>11.3f}{r['cost75']:>11.3f}{r['cost90']:>11.3f}{mark}")

    T = pd.DataFrame(rows)
    ok = T[(T.per_mo >= TARGET_LO) & (T.per_mo <= TARGET_HI)]
    print("\n" + "=" * 100)
    if ok.empty:
        print("  NO c LANDS IN THE TARGET BAND. Nothing is frozen and nothing runs.")
        return
    pick = ok.iloc[(ok.per_mo - TARGET_MID).abs().to_numpy().argmin()]
    print(f"  FROZEN c = {pick.c:.2f}")
    print(f"    trades/month          {pick.per_mo:.2f}   (target "
          f"{TARGET_LO:.0f}-{TARGET_HI:.0f})")
    print(f"    triggers 10:00/10:30  {int(pick.n1)} / {int(pick.n2)}")
    print(f"    long / short          {int(pick.long)} / {int(pick.short)}")
    print(f"    median risk           {pick.risk50:.1f} bps")
    print(f"    median cost/risk      {pick.cost50:.3f}%   "
          f"p75 {pick.cost75:.3f}%   p90 {pick.cost90:.3f}%")
    print()
    if pick.cost50 >= COST_REJECT_PCT:
        print(f"  *** REJECTED ON DESIGN GROUNDS: median cost/risk "
              f"{pick.cost50:.3f}% >= {COST_REJECT_PCT}%. ***")
        print("  Selectivity is not buying a wider stop. The expectancy pass")
        print("  does NOT run.")
    else:
        print(f"  Cost requirement MET: {pick.cost50:.3f}% < {COST_REJECT_PCT}%")
        print(f"  vs IB family 0.77-1.16% and ATR families 5-16%.")
        print(f"\n  Set C_FROZEN = {pick.c:.2f} and run the expectancy pass.")
    T.to_csv(ROOT / "reports/compression_calibration.csv", index=False)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "calibrate"
    if mode == "calibrate":
        calibrate()
    else:
        import compression_run
        compression_run.main()
