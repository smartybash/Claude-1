#!/usr/bin/env python3
"""FROZEN IB-MIDPOINT PULLBACK ON RELATED INSTRUMENTS.

THE FROZEN SPECIFICATION, UNCHANGED:
    zone = IB midpoint +/- 0.05 x IB range
    rejection = R2 (a later bar closes beyond the first zone bar's extreme)
    exit = 1.5R
Nothing else is touched: 25% ending zone, stop logic, 13:00 expiry, costs and
the honest fill model are exactly as frozen on QQQ at `ebff421`.

UNIT TRANSLATION, declared. The QQQ rule's risk limits were written in NQ
points, which is meaningless on EFA at $80 -- an absolute 0.194 floor there is
24 bps and would reject nearly every trade. The limits are therefore carried
across in RELATIVE terms:
  floor    cost <= 10% of risk  ->  risk >= 10 x COST_F = 6.67 bps. Already
           instrument-neutral; the code computes it from each instrument's
           own price, unchanged.
  ceiling  40 NQ points, converted to bps using QQQ's price ON THE SAME DATE,
           then applied to the other instrument. Date-matched, not a new number.

XLK is excluded from the headline pool: its QQQ overlap makes it the least
independent of the set.

2016-2020 is not opened. Sealed NQ dates are not read.

Usage: python3 scripts/orderflow/ib_pullback_instruments.py
"""
from __future__ import annotations

import datetime as dt
import sys
from math import ceil, sqrt
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ib_pullback as M                                                # noqa

ROOT = Path(__file__).resolve().parents[2]
INSTR = ("SPY", "IWM", "IJH", "EFA")
ZONE, REJ, EXIT = "B_mid", "R2", "1.5R"
WIN_LO, WIN_HI = 2021, 2025           # the related data's span


def load_parquet(path, y0=WIN_LO, y1=WIN_HI):
    d = pd.read_parquet(path)
    d = d[(d.timestamp.dt.year >= y0) & (d.timestamp.dt.year <= y1)]
    d["day"] = d.timestamp.dt.date
    d["ds"] = d.timestamp.dt.strftime("%Y%m%d")
    d = d[~d.ds.str.startswith(M.SEALED_PREFIX)]
    d = d[~d.ds.isin(M.SEALED_DATES)]
    out = []
    for day, g in d.groupby("day", sort=True):
        g = g.sort_values("timestamp")
        if len(g) < M.MIN_BARS:
            continue
        o = pd.Timestamp(dt.datetime.combine(day, dt.time(9, 30)))
        c = pd.Timestamp(dt.datetime.combine(day, dt.time(16, 0)))
        if g.timestamp.iloc[0] > o or g.timestamp.iloc[-1] < c - pd.Timedelta(minutes=5):
            continue
        g = g[(g.timestamp >= o) & (g.timestamp <= c)]
        out.append(dict(day=day, year=day.year,
                        t=(g.timestamp - o).dt.total_seconds().to_numpy() / 60.0,
                        hi=g.high.to_numpy(float), lo=g.low.to_numpy(float),
                        op=g.open.to_numpy(float), cl=g.close.to_numpy(float),
                        vol=g.volume.to_numpy(float), px=float(g.open.iloc[0])))
    return out


def qqq_bps_maps():
    """The two NQ-point quantities as bps of price, per date, from QQQ.
    Date-matched so nothing is re-chosen: the ceiling and the stop buffer are
    exactly what the frozen QQQ rule used on that same calendar day."""
    q = pd.read_parquet(M.SRC, columns=["timestamp", "open"])
    q = q[(q.timestamp.dt.year >= WIN_LO) & (q.timestamp.dt.year <= WIN_HI)]
    q["day"] = q.timestamp.dt.date
    first = q.groupby("day").open.first()
    ceil_px = M.nq_to_qqq(M.MAX_PTS_NQ)            # 40 NQ pts in QQQ dollars
    buf_px = M.nq_to_qqq(M.BUFFER_TICKS_NQ)        # 2 NQ ticks in QQQ dollars
    return ({d: 1e4 * ceil_px / p for d, p in first.items()},
            {d: 1e4 * buf_px / p for d, p in first.items()})


def make_hook(cbps, bbps):
    mc = float(np.median(list(cbps.values())))
    mb = float(np.median(list(bbps.values())))

    def hook(px, day):
        buf = px * bbps.get(day, mb) / 1e4
        lo = px * M.COST_F / M.COST_FRAC_MAX       # cost rule, instrument-neutral
        hi = px * cbps.get(day, mc) / 1e4
        return buf, lo, hi
    return hook


def cluster_se(R, days):
    R = np.asarray(R, float)
    n = len(R)
    mu = R.mean()
    d = pd.Series(R - mu).groupby(np.asarray(days)).sum().to_numpy()
    g = len(d)
    if g < 2:
        return np.nan, g
    return sqrt((g / (g - 1.0)) * float((d ** 2).sum())) / n, g


def block(T, label):
    if len(T) == 0:
        return None
    R = T.R.to_numpy(float)
    w, l = R[R > 0], R[R <= 0]
    eq = np.cumsum(R)
    dd = float((np.maximum.accumulate(eq) - eq).max())
    st = mx = 0
    for x in R:
        st = st + 1 if x <= 0 else 0
        mx = max(mx, st)
    ym = T.groupby("year").R.mean()
    b5 = np.sort(R)[:max(0, len(R) - 5)]
    k = max(10, int(ceil(0.10 * len(R))))
    d10 = np.sort(R)[:len(R) - k] if k < len(R) else np.array([])
    c50 = R - 0.5 * T.cost_pct.to_numpy(float) / 100.0
    return dict(name=label, n=len(R), win=100 * len(w) / len(R),
                avg_w=w.mean() if len(w) else 0, avg_l=l.mean() if len(l) else 0,
                exp=R.mean(), pf=(w.sum() / -l.sum()) if len(l) and l.sum() < 0 else np.inf,
                dd=dd, streak=mx, yp=int((ym > 0).sum()), ny=len(ym),
                ln=int((T.d > 0).sum()),
                lr=T[T.d > 0].R.mean() if (T.d > 0).any() else np.nan,
                sn=int((T.d < 0).sum()),
                sr=T[T.d < 0].R.mean() if (T.d < 0).any() else np.nan,
                b5=b5.mean() if len(b5) else np.nan,
                d10=d10.mean() if len(d10) else np.nan, kdrop=k,
                c50=c50.mean(), per_mo=np.nan)


def row(b):
    if b is None:
        return "      no trades"
    return (f"{b['n']:>6}{b['win']:>7.1f}{b['avg_w']:>7.2f}{b['avg_l']:>7.2f}"
            f"{b['exp']:>+8.3f}{b['pf']:>6.2f}{b['dd']:>7.1f}{b['streak']:>6}"
            f"{b['yp']:>3}/{b['ny']:<2}{b['b5']:>+8.3f}{b['d10']:>+8.3f}"
            f"{b['c50']:>+8.3f}")


HDR = (f"  {'instrument':<12}{'n':>6}{'win%':>7}{'avgW':>7}{'avgL':>7}"
       f"{'expR':>8}{'PF':>6}{'ddR':>7}{'strk':>6}{'yrs':>6}{'-best5':>8}"
       f"{'-dec':>8}{'+50%c':>8}")


def main():
    cb, bb = qqq_bps_maps()
    M.LIMIT_HOOK = make_hook(cb, bb)

    print("=" * 122)
    print("  FROZEN IB-MIDPOINT PULLBACK ON RELATED INSTRUMENTS")
    print("=" * 122)
    print(f"  frozen spec: zone {ZONE} · rejection {REJ} · exit {EXIT} · "
          f"EZ<25 · 13:00 expiry · honest fills — all unchanged")
    print(f"  window {WIN_LO}-{WIN_HI}   XLK excluded from the headline pool")

    DATA = {}
    for s in INSTR:
        DATA[s] = load_parquet(ROOT / f"data/related/{s}_1m.parquet")
    DATA["QQQ*"] = load_parquet(M.SRC)          # same window, like-for-like

    print("\n" + "=" * 122)
    print("  FUNNEL")
    print("=" * 122)
    print(f"  {'instrument':<12}{'sessions':>10}{'qualify':>9}{'reached':>9}"
          f"{'setups':>8}{'trades':>8}{'/mo':>6}{'riskBps':>9}{'cost%':>7}")
    RES, POOL = {}, []
    for s, SS in DATA.items():
        T, fn = M.collect(SS, ZONE, REJ, EXIT)
        qual = sum(v for k, v in fn.items() if k != "unresolved")
        reached = qual - fn.get("no_zone", 0) - fn.get("opp_break", 0)
        setups = len(T) + sum(fn.get(k, 0) for k in
                              ("reject_small", "reject_big", "reject_tgt",
                               "reject_late", "reject_risk"))
        mo = len(pd.PeriodIndex([x["day"] for x in SS], freq="M").unique())
        RES[s] = T
        if s != "QQQ*" and len(T):
            POOL.append(T.assign(sym=s))
        print(f"  {s:<12}{len(SS):>10}{qual:>9}{reached:>9}{setups:>8}"
              f"{len(T):>8}{len(T)/mo:>6.1f}"
              f"{(T.risk_bps.median() if len(T) else np.nan):>9.2f}"
              f"{(T.cost_pct.median() if len(T) else np.nan):>7.2f}")

    print("\n" + "=" * 122)
    print("  TRADING RESULTS")
    print("=" * 122)
    print(HDR)
    for s in list(INSTR) + ["QQQ*"]:
        print(f"  {s:<12}" + row(block(RES[s], s)))

    P = pd.concat(POOL, ignore_index=True)
    pb = block(P, "POOLED")
    print("  " + "-" * 118)
    print(f"  {'POOLED non-QQQ':<12}" + row(pb))

    se, g = cluster_se(P.R.to_numpy(), P.day.to_numpy())
    lo, hi = pb["exp"] - 1.96 * se, pb["exp"] + 1.96 * se
    print(f"\n  clustered by date: SE {se:.4f} over {g} dates   "
          f"95% CI [{lo:+.4f}, {hi:+.4f}]   t {pb['exp']/se:+.2f}")
    print(f"  instruments positive: "
          f"{sum(1 for s in INSTR if RES[s] is not None and len(RES[s]) and RES[s].R.mean() > 0)} of 4")

    print("\n  LONG / SHORT")
    print(f"  {'instrument':<12}{'longN':>8}{'longR':>9}{'shortN':>8}{'shortR':>9}")
    for s in list(INSTR) + ["QQQ*"]:
        b = block(RES[s], s)
        if b:
            print(f"  {s:<12}{b['ln']:>8}{b['lr']:>+9.3f}{b['sn']:>8}{b['sr']:>+9.3f}")
    print(f"  {'POOLED':<12}{pb['ln']:>8}{pb['lr']:>+9.3f}{pb['sn']:>8}{pb['sr']:>+9.3f}")

    # ------------------------------------------------------- controls ---
    print("\n" + "=" * 122)
    print("  MECHANISM CONTROLS — pooled non-QQQ, frozen rule, no optimisation")
    print("=" * 122)
    print(f"  {'control':<28}{'n':>7}{'expR':>9}{'PF':>7}{'vs base':>10}")
    base = pb["exp"]
    print(f"  {'BASE (frozen)':<28}{pb['n']:>7}{base:>+9.3f}{pb['pf']:>7.2f}"
          f"{'--':>10}")
    for lab, kw in (("1 no ending-zone", dict(use_ez=False)),
                    ("2 touch without rejection", dict(touch_only=True)),
                    ("3 zone shifted 0.25 IB", dict(shift=0.25)),
                    ("4 opposite bias", dict(flip=True))):
        parts = []
        for s in INSTR:
            X, _ = M.collect(DATA[s], ZONE, REJ, EXIT, **kw)
            if len(X):
                parts.append(X)
        if not parts:
            print(f"  {lab:<28}{0:>7}      no trades")
            continue
        C = pd.concat(parts, ignore_index=True)
        cb_ = block(C, lab)
        print(f"  {lab:<28}{cb_['n']:>7}{cb_['exp']:>+9.3f}{cb_['pf']:>7.2f}"
              f"{base - cb_['exp']:>+10.3f}")

    # ------------------------------------------------------- decision ---
    print("\n" + "=" * 122)
    print("  DESK DECISION RULE")
    print("=" * 122)
    npos = sum(1 for s in INSTR if len(RES[s]) and RES[s].R.mean() > 0)
    checks = [
        ("1 pooled expectancy >= +0.08R", pb["exp"] >= 0.08, f"{pb['exp']:+.3f}"),
        ("2 pooled PF >= 1.15", pb["pf"] >= 1.15, f"{pb['pf']:.2f}"),
        ("3 CI not centred on zero", not (lo < 0 < hi), f"[{lo:+.3f},{hi:+.3f}]"),
        ("4 >=3 of 4 instruments positive", npos >= 3, f"{npos} of 4"),
        ("5 positive after removing best 5", pb["b5"] > 0, f"{pb['b5']:+.3f}"),
        ("6 positive at +50% costs", pb["c50"] > 0, f"{pb['c50']:+.3f}"),
    ]
    for name, ok, det in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {name:<40} {det}")
    print(f"\n  concentration DIAGNOSTIC (not a pass/fail): after removing the "
          f"top decile ({pb['kdrop']} trades) {pb['d10']:+.3f}")
    print(f"\n  {sum(1 for _, o, _ in checks if o)} of 6 numeric conditions met")
    print("\n  2016-2020 not opened. Sealed dates not read.")


if __name__ == "__main__":
    main()
