#!/usr/bin/env python3
"""IB ENDING ZONE + PULLBACK REJECTION CONTINUATION.

Pre-registered at `417a012` before this file was written.

A NEW TRADE CONSTRUCTION. The prior IB expectancy result is not reused, and the
boundary-break rate is NOT treated as evidence -- it is the geometric identity
P(break) ~ (100 - EZ)%. The ending zone is a qualification state only.

GRID: 3 zones x 2 rejections x 3 exits = 18 variants. Complete, nothing added.

UNITS: rules are in NQ points, data is QQQ. NQ = QQQ x 41.27, measured over
four true-tick sessions. All NQ quantities convert per session in bps.

Sealed NQ dates are not read. 2016-2020 is not opened.

Usage: python3 scripts/orderflow/ib_pullback.py
"""
from __future__ import annotations

import datetime as dt
import sys
from math import ceil
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data/intraday_long/QQQ_1m.parquet"

FIRST_YEAR = 2021
MIN_BARS = 360
SEALED_PREFIX, SEALED_DATES = "202606", {"20260723"}

NQ_RATIO = 41.27                 # measured
COST_F = 2.00 / 30000.0          # 0.667 bps round turn
EZ_MAX = 25.0
GIVE_UP_MIN = 210                # 13:00 ET = open + 210 min
FLAT_MIN = 390                   # 16:00 ET

MIN_PTS_NQ, MAX_PTS_NQ = 8.0, 40.0
BUFFER_TICKS_NQ = 2 * 0.25       # 0.5 NQ points
COST_FRAC_MAX = 0.10

ZONES = ("C_retest", "A_vwap", "B_mid")      # fixed overlap priority
REJECTS = ("R1", "R2")
EXITS = ("IBbound", "1.5R", "2R")

N_VARIANTS = len(ZONES) * len(REJECTS) * len(EXITS)      # 18


def nq_to_qqq(pts):
    """NQ points -> QQQ price units. NQ = QQQ x 41.27, so 1 NQ pt = 1/41.27."""
    return pts / NQ_RATIO


def load():
    d = pd.read_parquet(SRC)
    d = d[d.timestamp.dt.year >= FIRST_YEAR]          # 2016-2020 not opened
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
        t = (g.timestamp - o).dt.total_seconds().to_numpy() / 60.0
        out.append(dict(
            day=day, year=day.year, t=t,
            hi=g.high.to_numpy(float), lo=g.low.to_numpy(float),
            op=g.open.to_numpy(float), cl=g.close.to_numpy(float),
            vol=g.volume.to_numpy(float), px=float(g.open.iloc[0])))
    return out


def qualify(S, use_ez=True, flip=False):
    """IB structure and direction. Returns None if unresolved."""
    t, hi, lo, cl = S["t"], S["hi"], S["lo"], S["cl"]
    ib = (t >= 0) & (t < 60)
    if ib.sum() < 30 or (t >= 60).sum() < 60:
        return None
    ih, il, tib = hi[ib], lo[ib], t[ib]
    a, b = int(np.argmax(ih)), int(np.argmin(il))    # FIRST occurrence
    if tib[a] == tib[b]:
        return None                                   # unresolved, no trade
    ibh, ibl = float(ih[a]), float(il[b])
    rng = ibh - ibl
    if rng <= 0:
        return None
    high_first = tib[a] < tib[b]
    d = -1 if high_first else 1
    exp_lvl = ibl if high_first else ibh              # 0% boundary
    opp_lvl = ibh if high_first else ibl              # 100% boundary
    close1030 = float(cl[ib][-1])
    ez = 100.0 * abs(close1030 - exp_lvl) / rng
    if use_ez and ez >= EZ_MAX:
        return None
    if flip:
        # Control 4: mirror the WHOLE construction, not just the sign of d.
        # Flipping d alone left exp/opp on their original sides, so the
        # opposite-boundary expiry fired on bar one and no trade could form.
        d = -d
        exp_lvl, opp_lvl = opp_lvl, exp_lvl
    return dict(ibh=ibh, ibl=ibl, rng=rng, d=d, exp=exp_lvl, opp=opp_lvl,
                ez=ez, mid=(ibh + ibl) / 2.0)


def vwap_series(S):
    """Running session VWAP from 09:30, causal at every timestamp."""
    tp = (S["hi"] + S["lo"] + S["cl"]) / 3.0
    v = S["vol"]
    cv = np.cumsum(v)
    cpv = np.cumsum(tp * v)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(cv > 0, cpv / cv, np.nan)


def zone_band(S, Q, zone, i, vw, broke_at, shift=0.0):
    """(lo, hi) of the zone at bar i, or None if unavailable."""
    r = Q["rng"]
    sh = shift * r * (-Q["d"])           # shifted AWAY from the boundary
    if zone == "A_vwap":
        c = vw[i]
        if not np.isfinite(c):
            return None
        w = 0.10 * r
    elif zone == "B_mid":
        c, w = Q["mid"], 0.05 * r
    else:                                 # C_retest
        if broke_at is None or i < broke_at:
            return None
        c, w = Q["exp"], 0.05 * r
    c = c + sh
    return (c - w, c + w)


# ------------------------------------------------------- the trade ------

def run_session(S, zone, rej, ex, use_ez=True, flip=False, shift=0.0,
                touch_only=False):
    """One session -> at most one trade. Returns a dict or a funnel marker."""
    Q = qualify(S, use_ez=use_ez, flip=flip)
    if Q is None:
        return dict(stage="unresolved")
    t, hi, lo, op, cl = S["t"], S["hi"], S["lo"], S["op"], S["cl"]
    n, px, d = len(t), S["px"], Q["d"]
    vw = vwap_series(S)
    buf = nq_to_qqq(BUFFER_TICKS_NQ)
    lo_lim = max(nq_to_qqq(MIN_PTS_NQ), px * COST_F / COST_FRAC_MAX)
    hi_lim = nq_to_qqq(MAX_PTS_NQ)

    i0 = int(np.searchsorted(t, 60, "left"))
    broke_at = None
    in_zone = False
    z_start = -1
    pull_ext = None
    reached = False

    for i in range(i0, n):
        if t[i] > GIVE_UP_MIN:
            return dict(stage="reached" if reached else "no_zone", Q=Q)
        # expiry: the opposite boundary breaks before entry
        if (lo[i] < Q["opp"]) if d > 0 else (hi[i] > Q["opp"]):
            return dict(stage="opp_break", Q=Q)
        # has the expected boundary broken yet? (needed for zone C)
        if broke_at is None:
            if (hi[i] > Q["exp"]) if d > 0 else (lo[i] < Q["exp"]):
                broke_at = i

        b = zone_band(S, Q, zone, i, vw, broke_at, shift)
        if b is None:
            continue
        zlo, zhi = b
        touched = (lo[i] <= zhi) and (hi[i] >= zlo)

        if not in_zone:
            if not touched:
                continue
            in_zone, z_start, reached = True, i, True
            pull_ext = lo[i] if d > 0 else hi[i]
            if touch_only:
                return _enter(S, Q, i, d, pull_ext, buf, lo_lim, hi_lim, ex)
            continue

        # tracking the pullback while waiting for confirmation
        pull_ext = (min(pull_ext, lo[i]) if d > 0 else max(pull_ext, hi[i]))
        if rej == "R1":
            ok = ((cl[i] > zhi and cl[i] > (hi[i] + lo[i]) / 2.0) if d > 0
                  else (cl[i] < zlo and cl[i] < (hi[i] + lo[i]) / 2.0))
        else:                                   # R2
            ok = (cl[i] > hi[z_start]) if d > 0 else (cl[i] < lo[z_start])
        if ok:
            return _enter(S, Q, i, d, pull_ext, buf, lo_lim, hi_lim, ex)
    return dict(stage="reached" if reached else "no_zone", Q=Q)


def _enter(S, Q, i_conf, d, pull_ext, buf, lo_lim, hi_lim, ex):
    """Entry at the NEXT bar open. Entry bar excluded from the exit search."""
    t, hi, lo, op, cl = S["t"], S["hi"], S["lo"], S["op"], S["cl"]
    n, px = len(t), S["px"]
    ie = i_conf + 1
    if ie >= n - 2:
        return dict(stage="reject_late", Q=Q)
    fill = float(op[ie])
    naive = float(cl[i_conf])                    # the naive trigger price
    stop = (pull_ext - buf) if d > 0 else (pull_ext + buf)
    risk = abs(fill - stop)
    if risk <= 0:
        return dict(stage="reject_risk", Q=Q)
    if risk < lo_lim:
        return dict(stage="reject_small", Q=Q)
    if risk > hi_lim:
        return dict(stage="reject_big", Q=Q)

    if ex == "IBbound":
        tgt = Q["exp"]
        if d * (tgt - fill) < 0.75 * risk:
            return dict(stage="reject_tgt", Q=Q)
    else:
        m = 1.5 if ex == "1.5R" else 2.0
        tgt = fill + d * m * risk

    cost = px * COST_F
    mfe = mae = 0.0
    amb = False
    for j in range(ie + 1, n):
        fav = d * (hi[j] - fill) if d > 0 else d * (lo[j] - fill)
        adv = d * (lo[j] - fill) if d > 0 else d * (hi[j] - fill)
        mfe, mae = max(mfe, fav), min(mae, adv)
        st = lo[j] <= stop if d > 0 else hi[j] >= stop
        ht = hi[j] >= tgt if d > 0 else lo[j] <= tgt
        if st and ht:
            amb = True
        if st:                                   # STOP BEFORE TARGET
            exi = min(stop, op[j]) if d > 0 else max(stop, op[j])
            return _trade(S, Q, d, fill, naive, stop, risk, exi, "stop",
                          cost, mfe, mae, amb, i_conf)
        if ht:
            return _trade(S, Q, d, fill, naive, stop, risk, tgt, "target",
                          cost, mfe, mae, amb, i_conf)
        if t[j] >= FLAT_MIN:
            break
    return _trade(S, Q, d, fill, naive, stop, risk, float(cl[min(j, n - 1)]),
                  "close", cost, mfe, mae, amb, i_conf)


def _trade(S, Q, d, fill, naive, stop, risk, exi, why, cost, mfe, mae, amb, ic):
    R = (d * (exi - fill) - cost) / risk
    Rn = (d * (exi - naive) - cost) / abs(naive - stop) if abs(naive - stop) > 0 else np.nan
    return dict(stage="trade", day=S["day"], year=S["year"], d=d, why=why,
                R=R, naive_R=Rn, risk_bps=1e4 * risk / S["px"],
                risk_nq=risk * NQ_RATIO,
                cost_pct=100.0 * cost / risk, mfe=mfe / risk, mae=mae / risk,
                amb=amb, ez=Q["ez"], zone_bar=ic)


# ---------------------------------------------------------- reporting ----

def collect(SS, zone, rej, ex, **kw):
    T, funnel = [], {}
    for S in SS:
        r = run_session(S, zone, rej, ex, **kw)
        funnel[r["stage"]] = funnel.get(r["stage"], 0) + 1
        if r["stage"] == "trade":
            T.append(r)
    return pd.DataFrame(T), funnel


def stats(T, cmul=1.0, drop_best=0, use_std_conc=False):
    if len(T) == 0:
        return None
    R = T.R.to_numpy(float).copy()
    if cmul != 1.0:
        R = R - (cmul - 1.0) * T.cost_pct.to_numpy(float) / 100.0
    if use_std_conc:
        k = max(10, int(ceil(0.10 * len(R))))
        if k >= len(R):
            return None
        R = np.sort(R)[:len(R) - k]
    elif drop_best:
        R = np.sort(R)[:max(0, len(R) - drop_best)]
    if len(R) == 0:
        return None
    w, l = R[R > 0], R[R <= 0]
    eq = np.cumsum(R)
    dd = float((np.maximum.accumulate(eq) - eq).max()) if len(eq) else 0.0
    streak = mx = 0
    for x in R:
        streak = streak + 1 if x <= 0 else 0
        mx = max(mx, streak)
    return dict(n=len(R), win=100.0 * len(w) / len(R),
                avg_w=w.mean() if len(w) else 0.0,
                avg_l=l.mean() if len(l) else 0.0,
                exp=R.mean(), pf=(w.sum() / -l.sum()) if len(l) and l.sum() < 0 else np.inf,
                dd=dd, streak=mx)


def years_pos(T):
    m = T.groupby("year").R.mean()
    return int((m > 0).sum()), int(len(m))


def main():
    SS = load()
    months = len(pd.PeriodIndex([s["day"] for s in SS], freq="M").unique())
    print("=" * 124)
    print("  IB ENDING ZONE + PULLBACK REJECTION — pre-registered at 417a012")
    print("=" * 124)
    print(f"  sessions {len(SS)}   months {months}   "
          f"{SS[0]['day']} .. {SS[-1]['day']}")
    print(f"  grid {N_VARIANTS} variants   Bonferroni alpha "
          f"{0.05/N_VARIANTS:.5f}   NQ = QQQ x {NQ_RATIO}")

    # ---------------------------------------------------------- funnel --
    _, f0 = collect(SS, "A_vwap", "R1", "2R")
    nq_ = sum(v for k, v in f0.items() if k != "unresolved")
    print(f"\n  QUALIFICATION: {len(SS)} sessions -> "
          f"{nq_} qualify at EZ<25 with resolvable extremes "
          f"({100*nq_/len(SS):.1f}%)")

    rows = []
    print("\n" + "=" * 124)
    print("  FUNNEL PER VARIANT   qualifying -> zone reached -> rejection -> "
          "trade -> target/stop/close")
    print("=" * 124)
    print(f"  {'zone':<10}{'rej':<4}{'exit':<9}{'qual':>6}{'reached':>9}"
          f"{'traded':>8}{'/mo':>6}{'riskNQ':>8}{'cost%':>7}"
          f"{'tgt':>6}{'stop':>6}{'close':>7}{'amb%':>7}")
    for z in ZONES:
        for rj in REJECTS:
            for ex in EXITS:
                T, fn = collect(SS, z, rj, ex)
                qual = sum(v for k, v in fn.items() if k != "unresolved")
                reached = qual - fn.get("no_zone", 0) - fn.get("opp_break", 0)
                if len(T) == 0:
                    print(f"  {z:<10}{rj:<4}{ex:<9}{qual:>6}{reached:>9}"
                          f"{0:>8}      no trades")
                    continue
                st = stats(T)
                yp, yt = years_pos(T)
                mix = T.why.value_counts()
                rows.append(dict(zone=z, rej=rj, exit=ex, qual=qual,
                                 reached=reached, **st,
                                 per_mo=len(T) / months,
                                 risk_nq=T.risk_nq.median(),
                                 cost_pct=T.cost_pct.median(),
                                 years=f"{yp}/{yt}", yp=yp,
                                 mae=T.mae.median(), mfe=T.mfe.median(),
                                 tgt=int(mix.get("target", 0)),
                                 stop=int(mix.get("stop", 0)),
                                 close=int(mix.get("close", 0)),
                                 amb=100 * T.amb.mean(),
                                 naive=T.naive_R.mean(),
                                 long_n=int((T.d > 0).sum()),
                                 long_R=T[T.d > 0].R.mean() if (T.d > 0).any() else np.nan,
                                 short_n=int((T.d < 0).sum()),
                                 short_R=T[T.d < 0].R.mean() if (T.d < 0).any() else np.nan,
                                 T=T))
                print(f"  {z:<10}{rj:<4}{ex:<9}{qual:>6}{reached:>9}"
                      f"{len(T):>8}{len(T)/months:>6.1f}"
                      f"{T.risk_nq.median():>8.1f}{T.cost_pct.median():>7.2f}"
                      f"{int(mix.get('target',0)):>6}{int(mix.get('stop',0)):>6}"
                      f"{int(mix.get('close',0)):>7}{100*T.amb.mean():>7.1f}")
    V = pd.DataFrame([{k: v for k, v in r.items() if k != "T"} for r in rows])
    V.to_csv(ROOT / "reports/ib_pullback_variants.csv", index=False)

    # -------------------------------------------------- trading results --
    print("\n" + "=" * 124)
    print("  TRADING RESULTS — desk first")
    print("=" * 124)
    print(f"  {'zone':<10}{'rej':<4}{'exit':<9}{'n':>6}{'win%':>7}{'avgW':>7}"
          f"{'avgL':>7}{'expR':>8}{'PF':>6}{'ddR':>7}{'strk':>6}{'yrs':>6}"
          f"{'-best5':>8}{'-10%':>8}{'+50%c':>8}{'naive':>8}")
    for r in rows:
        T = r["T"]
        b5 = stats(T, drop_best=5)
        sc = stats(T, use_std_conc=True)
        c5 = stats(T, cmul=1.5)
        print(f"  {r['zone']:<10}{r['rej']:<4}{r['exit']:<9}{r['n']:>6}"
              f"{r['win']:>7.1f}{r['avg_w']:>7.2f}{r['avg_l']:>7.2f}"
              f"{r['exp']:>+8.3f}{r['pf']:>6.2f}{r['dd']:>7.1f}"
              f"{r['streak']:>6}{r['years']:>6}"
              f"{(b5['exp'] if b5 else np.nan):>+8.3f}"
              f"{(sc['exp'] if sc else np.nan):>+8.3f}"
              f"{(c5['exp'] if c5 else np.nan):>+8.3f}{r['naive']:>+8.3f}")

    print("\n  LONG / SHORT SPLIT, and excursions")
    print(f"  {'zone':<10}{'rej':<4}{'exit':<9}{'longN':>7}{'longR':>8}"
          f"{'shortN':>8}{'shortR':>8}{'medMAE':>8}{'medMFE':>8}")
    for r in rows:
        print(f"  {r['zone']:<10}{r['rej']:<4}{r['exit']:<9}{r['long_n']:>7}"
              f"{r['long_R']:>+8.3f}{r['short_n']:>8}{r['short_R']:>+8.3f}"
              f"{r['mae']:>+8.2f}{r['mfe']:>+8.2f}")
    return rows, SS, months


if __name__ == "__main__":
    main()
