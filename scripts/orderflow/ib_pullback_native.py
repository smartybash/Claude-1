#!/usr/bin/env python3
"""NATIVE-NORMALISED TRANSFER OF THE FROZEN IB-MIDPOINT PULLBACK.

Declared and committed at `146bcbc` BEFORE this file was written or run.

WHAT IS FROZEN AND UNTOUCHED
  IB 09:30-10:30 · first-timestamp extreme · 0-25% ending zone of the
  instrument's OWN IB range · midpoint band +/- 0.05 of OWN IB range ·
  R2 rejection · entry at the next bar open · 13:00 expiry · 16:00 flat ·
  target 1.5R from actual entry and actual risk · honest fills · entry bar
  excluded · stop before target.

WHAT IS NATIVE (the only change, declared in advance)
  buffer   = max(2 ticks, 0.10 x ATR1m)
  min stop = max(1.0 x ATR1m, 10 x true cost)
  max stop = 6.0 x ATR1m
  cost     = 1 tick round turn + $0.0035/share commission, PER INSTRUMENT
  reject if cost > 10% of risk

ATR1m is Wilder ATR14 on 1-minute bars, CAUSAL: the value at the confirmation
bar, computed from bars up to and including it. No session-level lookahead.

The frozen QQQ module is imported, not edited. QQQ is reported under BOTH.

2016-2020 is not opened. Sealed NQ dates are not read.

Usage: python3 scripts/orderflow/ib_pullback_native.py
"""
from __future__ import annotations

import datetime as dt
import sys
from math import ceil, sqrt
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ib_pullback as F                                                # noqa

ROOT = Path(__file__).resolve().parents[2]

# tick size and per-share commission are instrument facts, not parameters
TICK = 0.01
COMM_PER_SHARE = 0.0035               # each way
BUF_ATR_FRAC = 0.10                   # DECLARED at 146bcbc, not changed
MIN_ATR_MULT = 1.0
MAX_ATR_MULT = 6.0
COST_FRAC_MAX = 0.10
TARGET_R = 1.5

WIN_LO, WIN_HI = 2021, 2025
SETS = {
    "QQQ": ROOT / "data/intraday_long/QQQ_1m.parquet",
    "SPY": ROOT / "data/related/SPY_1m.parquet",
    "IWM": ROOT / "data/related/IWM_1m.parquet",
    "IJH": ROOT / "data/related/IJH_1m.parquet",
    "EFA": ROOT / "data/related/EFA_1m.parquet",
}
POOL = ("SPY", "IWM", "IJH", "EFA")


def true_cost(px_unused=None):
    """Round-turn cost in PRICE units: one tick of spread + commission both ways."""
    return TICK + 2 * COMM_PER_SHARE


def atr14(h, l, c):
    pc = np.roll(c, 1)
    pc[0] = c[0]
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    a = np.full(len(tr), np.nan)
    if len(tr) <= 14:
        return a
    a[14] = tr[1:15].mean()
    for i in range(15, len(tr)):
        a[i] = (a[i - 1] * 13 + tr[i]) / 14
    return a


def load_inst(path):
    d = pd.read_parquet(path)
    d = d[(d.timestamp.dt.year >= WIN_LO) & (d.timestamp.dt.year <= WIN_HI)]
    d["day"] = d.timestamp.dt.date
    d["ds"] = d.timestamp.dt.strftime("%Y%m%d")
    d = d[~d.ds.str.startswith(F.SEALED_PREFIX)]
    d = d[~d.ds.isin(F.SEALED_DATES)]
    out = []
    for day, g in d.groupby("day", sort=True):
        g = g.sort_values("timestamp")
        if len(g) < F.MIN_BARS:
            continue
        o = pd.Timestamp(dt.datetime.combine(day, dt.time(9, 30)))
        c = pd.Timestamp(dt.datetime.combine(day, dt.time(16, 0)))
        if g.timestamp.iloc[0] > o or g.timestamp.iloc[-1] < c - pd.Timedelta(minutes=5):
            continue
        g = g[(g.timestamp >= o) & (g.timestamp <= c)]
        hi = g.high.to_numpy(float)
        lo = g.low.to_numpy(float)
        cl = g.close.to_numpy(float)
        out.append(dict(day=day, year=day.year,
                        t=(g.timestamp - o).dt.total_seconds().to_numpy() / 60.0,
                        hi=hi, lo=lo, op=g.open.to_numpy(float), cl=cl,
                        vol=g.volume.to_numpy(float),
                        px=float(g.open.iloc[0]), atr=atr14(hi, lo, cl)))
    return out


def native_session(S, use_ez=True, flip=False, shift=0.0, touch_only=False):
    """The frozen construction with native limits. Structure is unchanged."""
    Q = F.qualify(S, use_ez=use_ez, flip=flip)
    if Q is None:
        return dict(stage="unresolved")
    t, hi, lo, op, cl = S["t"], S["hi"], S["lo"], S["op"], S["cl"]
    atr, n, d = S["atr"], len(t), Q["d"]
    cost = true_cost()
    i0 = int(np.searchsorted(t, 60, "left"))
    broke_at = None
    in_zone = False
    z_start = -1
    pull_ext = None
    reached = False

    for i in range(i0, n):
        if t[i] > F.GIVE_UP_MIN:
            return dict(stage="reached" if reached else "no_zone")
        if (lo[i] < Q["opp"]) if d > 0 else (hi[i] > Q["opp"]):
            return dict(stage="opp_break")
        if broke_at is None:
            if (hi[i] > Q["exp"]) if d > 0 else (lo[i] < Q["exp"]):
                broke_at = i
        b = F.zone_band(S, Q, "B_mid", i, None, broke_at, shift)
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
                return enter(S, Q, i, d, pull_ext, atr, cost)
            continue
        pull_ext = (min(pull_ext, lo[i]) if d > 0 else max(pull_ext, hi[i]))
        ok = (cl[i] > hi[z_start]) if d > 0 else (cl[i] < lo[z_start])
        if ok:
            return enter(S, Q, i, d, pull_ext, atr, cost)
    return dict(stage="reached" if reached else "no_zone")


def enter(S, Q, i_conf, d, pull_ext, atr, cost):  # noqa: C901
    t, hi, lo, op, cl = S["t"], S["hi"], S["lo"], S["op"], S["cl"]
    n, px = len(t), S["px"]
    a = atr[i_conf]                                  # CAUSAL: known at i_conf
    if not np.isfinite(a) or a <= 0:
        return dict(stage="reject_atr")
    ie = i_conf + 1
    if ie >= n - 2:
        return dict(stage="reject_late")
    fill = float(op[ie])
    buf = max(2 * TICK, BUF_ATR_FRAC * a)
    stop = (pull_ext - buf) if d > 0 else (pull_ext + buf)
    risk = abs(fill - stop)
    if risk <= 0:
        return dict(stage="reject_risk")
    lo_lim = max(MIN_ATR_MULT * a, 10.0 * cost)
    hi_lim = MAX_ATR_MULT * a
    if risk < lo_lim:
        return dict(stage="reject_small")
    if risk > hi_lim:
        return dict(stage="reject_big")
    if cost / risk > COST_FRAC_MAX:
        return dict(stage="reject_cost")
    tgt = fill + d * TARGET_R * risk

    mfe = mae = 0.0
    amb = False
    j = ie + 1
    for j in range(ie + 1, n):
        fav = d * (hi[j] - fill) if d > 0 else d * (lo[j] - fill)
        adv = d * (lo[j] - fill) if d > 0 else d * (hi[j] - fill)
        mfe, mae = max(mfe, fav), min(mae, adv)
        st = lo[j] <= stop if d > 0 else hi[j] >= stop
        ht = hi[j] >= tgt if d > 0 else lo[j] <= tgt
        if st and ht:
            amb = True
        if st:
            exi = min(stop, op[j]) if d > 0 else max(stop, op[j])
            return mk(S, d, fill, stop, risk, exi, "stop", cost, mfe, mae, amb, a, Q)
        if ht:
            return mk(S, d, fill, stop, risk, tgt, "target", cost, mfe, mae, amb, a, Q)
        if t[j] >= F.FLAT_MIN:
            break
    return mk(S, d, fill, stop, risk, float(cl[min(j, n - 1)]), "close",
              cost, mfe, mae, amb, a, Q)


def mk(S, d, fill, stop, risk, exi, why, cost, mfe, mae, amb, a, Q):
    return dict(stage="trade", day=S["day"], year=S["year"], d=d, why=why,
                R=(d * (exi - fill) - cost) / risk,
                risk_bps=1e4 * risk / S["px"], risk_atr=risk / a,
                atr_bps=1e4 * a / S["px"], ib_bps=1e4 * Q["rng"] / S["px"],
                cost_pct=100.0 * cost / risk, mfe=mfe / risk, mae=mae / risk,
                amb=amb)


def collect(SS, **kw):
    T, fn = [], {}
    for S in SS:
        r = native_session(S, **kw)
        fn[r["stage"]] = fn.get(r["stage"], 0) + 1
        if r["stage"] == "trade":
            T.append(r)
    return pd.DataFrame(T), fn


# ---------------------------------------------------------- reporting ----

def cluster_se(R, days):
    R = np.asarray(R, float)
    n = len(R)
    dv = pd.Series(R - R.mean()).groupby(np.asarray(days)).sum().to_numpy()
    g = len(dv)
    if g < 2:
        return np.nan, g
    return sqrt((g / (g - 1.0)) * float((dv ** 2).sum())) / n, g


def blk(T):
    if T is None or len(T) == 0:
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
    c50 = R - 0.5 * T.cost_pct.to_numpy(float) / 100.0
    return dict(n=len(R), win=100 * len(w) / len(R),
                aw=w.mean() if len(w) else 0, al=l.mean() if len(l) else 0,
                exp=R.mean(),
                pf=(w.sum() / -l.sum()) if len(l) and l.sum() < 0 else np.inf,
                dd=dd, strk=mx, yp=int((ym > 0).sum()), ny=len(ym),
                ln=int((T.d > 0).sum()),
                lr=T[T.d > 0].R.mean() if (T.d > 0).any() else np.nan,
                sn=int((T.d < 0).sum()),
                sr=T[T.d < 0].R.mean() if (T.d < 0).any() else np.nan,
                b5=b5.mean() if len(b5) else np.nan, c50=c50.mean())


def main():
    DATA = {k: load_inst(v) for k, v in SETS.items()}
    months = 60

    print("=" * 126)
    print("  NATIVE-NORMALISED TRANSFER — declared at 146bcbc before running")
    print("=" * 126)
    print(f"  buffer max(2 ticks, {BUF_ATR_FRAC} x ATR1m) · min stop "
          f"max({MIN_ATR_MULT} x ATR1m, 10 x cost) · max stop {MAX_ATR_MULT} x "
          f"ATR1m · cost 1 tick + 2x${COMM_PER_SHARE}/share")
    print(f"  window {WIN_LO}-{WIN_HI}. Everything else frozen.")

    print("\n" + "=" * 126)
    print("  FUNNEL AND REJECTIONS")
    print("=" * 126)
    print(f"  {'':<8}{'sess':>6}{'qual':>6}{'reach':>7}{'setup':>7}{'trade':>7}"
          f"{'rej<':>6}{'rej>':>6}{'rejC':>6}{'/mo':>6}"
          f"{'ATRbps':>8}{'IBbps':>7}{'stop':>7}{'st/ATR':>8}{'zn/ATR':>8}{'cost%':>7}")
    RES, FN = {}, {}
    for s, SS in DATA.items():
        T, fn = collect(SS)
        RES[s], FN[s] = T, fn
        qual = sum(v for k, v in fn.items() if k != "unresolved")
        reach = qual - fn.get("no_zone", 0) - fn.get("opp_break", 0)
        setup = sum(fn.get(k, 0) for k in
                    ("trade", "reject_small", "reject_big", "reject_cost",
                     "reject_atr", "reject_late", "reject_risk"))
        za = (T.ib_bps.median() * 0.05 / T.atr_bps.median()) if len(T) else np.nan
        print(f"  {s:<8}{len(SS):>6}{qual:>6}{reach:>7}{setup:>7}{len(T):>7}"
              f"{fn.get('reject_small',0):>6}{fn.get('reject_big',0):>6}"
              f"{fn.get('reject_cost',0):>6}{len(T)/months:>6.1f}"
              f"{(T.atr_bps.median() if len(T) else np.nan):>8.2f}"
              f"{(T.ib_bps.median() if len(T) else np.nan):>7.1f}"
              f"{(T.risk_bps.median() if len(T) else np.nan):>7.2f}"
              f"{(T.risk_atr.median() if len(T) else np.nan):>8.2f}"
              f"{za:>8.2f}"
              f"{(T.cost_pct.median() if len(T) else np.nan):>7.2f}")

    # QQQ under the FROZEN implementation, same window, for comparison
    Fq = F.load()
    Fq = [x for x in Fq if WIN_LO <= x["year"] <= WIN_HI]
    Tf, _ = F.collect(Fq, "B_mid", "R2", "1.5R")

    print("\n" + "=" * 126)
    print("  TRADING RESULTS")
    print("=" * 126)
    hdr = (f"  {'':<16}{'n':>6}{'win%':>7}{'avgW':>7}{'avgL':>7}{'expR':>8}"
           f"{'PF':>6}{'ddR':>7}{'strk':>5}{'yrs':>6}{'longN':>7}{'longR':>8}"
           f"{'shrtN':>7}{'shrtR':>8}{'-best5':>8}{'+50%c':>8}")
    print(hdr)

    def line(lab, b):
        if b is None:
            print(f"  {lab:<16}     no trades")
            return
        print(f"  {lab:<16}{b['n']:>6}{b['win']:>7.1f}{b['aw']:>7.2f}"
              f"{b['al']:>7.2f}{b['exp']:>+8.3f}{b['pf']:>6.2f}{b['dd']:>7.1f}"
              f"{b['strk']:>5}{b['yp']:>3}/{b['ny']:<2}{b['ln']:>7}"
              f"{b['lr']:>+8.3f}{b['sn']:>7}{b['sr']:>+8.3f}"
              f"{b['b5']:>+8.3f}{b['c50']:>+8.3f}")

    line("QQQ frozen", blk(Tf.assign(cost_pct=Tf.cost_pct)))
    line("QQQ native", blk(RES["QQQ"]))
    print("  " + "-" * 122)
    for s in POOL:
        line(s + " native", blk(RES[s]))
    P = pd.concat([RES[s].assign(sym=s) for s in POOL if len(RES[s])],
                  ignore_index=True)
    pb = blk(P)
    print("  " + "-" * 122)
    line("POOLED non-QQQ", pb)

    se, g = cluster_se(P.R.to_numpy(), P.day.to_numpy())
    npos = sum(1 for s in POOL if len(RES[s]) and RES[s].R.mean() > 0)
    print(f"\n  clustered by date: SE {se:.4f} over {g} dates   "
          f"95% CI [{pb['exp']-1.96*se:+.4f}, {pb['exp']+1.96*se:+.4f}]   "
          f"t {pb['exp']/se:+.2f}")
    print(f"  instruments positive: {npos} of 4")

    print("\n" + "=" * 126)
    print("  MECHANISM CONTROLS — native definitions")
    print("=" * 126)
    print(f"  {'control':<28}{'QQQ n':>8}{'QQQ R':>9}{'pool n':>8}{'pool R':>9}")
    qb = blk(RES["QQQ"])
    print(f"  {'BASE':<28}{qb['n']:>8}{qb['exp']:>+9.3f}{pb['n']:>8}{pb['exp']:>+9.3f}")
    for lab, kw in (("1 no ending-zone", dict(use_ez=False)),
                    ("2 touch without R2", dict(touch_only=True)),
                    ("3 zone shifted 0.25 IB", dict(shift=0.25)),
                    ("4 opposite bias", dict(flip=True))):
        Xq, _ = collect(DATA["QQQ"], **kw)
        parts = [collect(DATA[s], **kw)[0] for s in POOL]
        parts = [x for x in parts if len(x)]
        Xp = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
        bq, bp = blk(Xq), blk(Xp)
        print(f"  {lab:<28}"
              f"{(bq['n'] if bq else 0):>8}"
              f"{(bq['exp'] if bq else np.nan):>+9.3f}"
              f"{(bp['n'] if bp else 0):>8}"
              f"{(bp['exp'] if bp else np.nan):>+9.3f}")
    print("\n  2016-2020 not opened. Sealed dates not read.")


if __name__ == "__main__":
    main()
