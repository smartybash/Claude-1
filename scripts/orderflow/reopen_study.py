#!/usr/bin/env python3
"""TEST 1 (IB re-entry) and TEST 2 (VWAP hold to close). Pre-reg `40f4727`.
Flat at the cash close. Honest fills, entry bar excluded, 2pt round turn.
Sealed NQ days not read. 2016-2020 holdout NOT opened by this script.
"""
from __future__ import annotations
import datetime as dt, sys
from math import sqrt
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data/intraday_long/QQQ_1m.parquet"
COST_F = 2.00 / 30000.0
MIN_BARS = 360
TRAIL_N, PCTL = 20, 80
EXITS = [("1R", 1.0), ("2R", 2.0), ("3R", 3.0), ("Close", None)]


def load():
    d = pd.read_parquet(SRC); d["day"] = d.timestamp.dt.date
    out = []
    for day, g in d.groupby("day", sort=True):
        g = g.sort_values("timestamp")
        if len(g) < MIN_BARS: continue
        o = pd.Timestamp(dt.datetime.combine(day, dt.time(9, 30)))
        out.append(dict(day=day, year=day.year,
            t=(g.timestamp - o).dt.total_seconds().to_numpy()/60.0,
            hi=g.high.to_numpy(float), lo=g.low.to_numpy(float),
            op=g.open.to_numpy(float), cl=g.close.to_numpy(float),
            vol=g.volume.to_numpy(float), px=float(g.open.iloc[0])))
    return out


def run_trade(S, i, d, fill, stop, tg, maxn):
    """Exit search from bar i+1 (entry bar EXCLUDED). Returns dict or None."""
    hi, lo, op, cl = S["hi"], S["lo"], S["op"], S["cl"]
    risk = abs(fill - stop)
    if risk <= 0: return None
    tgt = fill + d*tg*risk if tg else None
    mfe = mae = 0.0; amb = False
    for j in range(i+1, maxn):
        fav = d*(hi[j]-fill) if d > 0 else d*(lo[j]-fill)
        adv = d*(lo[j]-fill) if d > 0 else d*(hi[j]-fill)
        mfe = max(mfe, fav); mae = min(mae, adv)
        st = lo[j] <= stop if d > 0 else hi[j] >= stop
        ht = (hi[j] >= tgt if d > 0 else lo[j] <= tgt) if tg else False
        if st and ht: amb = True
        if st:
            ex = min(stop, op[j]) if d > 0 else max(stop, op[j])
            return dict(R=(d*(ex-fill)-S["px"]*COST_F)/risk, why="stop",
                        naive_R=(d*(stop-fill)-S["px"]*COST_F)/risk,
                        risk=risk, mfe=mfe/risk, mae=mae/risk, amb=amb, j=j)
        if ht:
            return dict(R=(d*(tgt-fill)-S["px"]*COST_F)/risk, why="target",
                        naive_R=(d*(tgt-fill)-S["px"]*COST_F)/risk,
                        risk=risk, mfe=mfe/risk, mae=mae/risk, amb=amb, j=j)
    ex = cl[maxn-1]
    return dict(R=(d*(ex-fill)-S["px"]*COST_F)/risk, why="close",
                naive_R=(d*(ex-fill)-S["px"]*COST_F)/risk,
                risk=risk, mfe=mfe/risk, mae=mae/risk, amb=amb, j=maxn-1)


def test1(sessions, tg):
    rows, look = [], 0
    for S in sessions:
        t, hi, lo, cl = S["t"], S["hi"], S["lo"], S["cl"]
        ib = (t >= 0) & (t < 60); n = len(t)
        if ib.sum() < 30 or (t >= 60).sum() < 60: continue
        ih, il = hi[ib], lo[ib]; tib = t[ib]
        a, b = int(np.argmax(ih)), int(np.argmin(il))
        if tib[a] == tib[b]: continue
        ibh, ibl = float(ih[a]), float(il[b]); rng = ibh - ibl
        if rng <= 0: continue
        high_first = tib[a] < tib[b]
        close = float(cl[ib][-1])
        exp_lvl = ibl if high_first else ibh
        ez = 100.0*abs(close - exp_lvl)/rng
        if ez >= 25: continue
        d = -1 if high_first else 1
        stop = ibh if high_first else ibl
        i0 = int(np.searchsorted(t, 60, "left"))
        # DECLARED RULE (IB pre-registration): if the OPPOSITE boundary breaks
        # first, no trade -- the stop level was violated before entry.
        fe = np.where(hi[i0:] > exp_lvl)[0] if d > 0 else np.where(lo[i0:] < exp_lvl)[0]
        fo = np.where(lo[i0:] < stop)[0] if d > 0 else np.where(hi[i0:] > stop)[0]
        if len(fe) == 0:
            continue
        if len(fo) and int(fo[0]) < int(fe[0]):
            continue
        taken, i, armed = 0, i0, True
        while i < n and taken < 2:
            brk = hi[i] > exp_lvl if d > 0 else lo[i] < exp_lvl
            if armed and brk:
                if i < i0: look += 1
                fill = max(exp_lvl, S["op"][i]) if d > 0 else min(exp_lvl, S["op"][i])
                r = run_trade(S, i, d, fill, stop, tg, n)
                if r:
                    taken += 1
                    rows.append({**r, "day": S["day"], "year": S["year"],
                                 "dir": d, "seq": taken,
                                 "risk_bps": 1e4*r["risk"]/S["px"],
                                 "cost_pct": 100*S["px"]*COST_F/r["risk"]})
                    i = r["j"] + 1
                    armed = False           # must re-enter the IB to re-arm
                    continue
            if not armed:
                inside = (lo[i] < exp_lvl) if d > 0 else (hi[i] > exp_lvl)
                if inside: armed = True
            i += 1
    return pd.DataFrame(rows), look


def test2(sessions, tg):
    """VWAP mean reversion. Threshold = 80th pct of trailing 20 sessions'
    own |disp|, shifted. First two qualifying bars, non-concurrent."""
    hist, rows, look = [], [], 0
    for S in sessions:
        t, cl, vol, hi, lo = S["t"], S["cl"], S["vol"], S["hi"], S["lo"]
        n = len(t)
        tp = (hi + lo + cl)/3.0
        cv = np.cumsum(tp*vol); cw = np.cumsum(vol)
        vwap = np.where(cw > 0, cv/np.maximum(cw, 1e-9), cl)
        disp = (cl - vwap)/np.maximum(vwap, 1e-9)
        thr = (np.percentile(np.concatenate(hist), PCTL)
               if len(hist) >= TRAIL_N else None)
        hist.append(np.abs(disp)); hist = hist[-TRAIL_N:]
        if thr is None: continue
        taken, i = 0, 0
        while i < n - 1 and taken < 2:
            if t[i] >= 30 and abs(disp[i]) >= thr:       # 30-min VWAP warmup
                d = -1 if disp[i] > 0 else 1             # MEAN REVERSION
                j = i + 1                                # enter next bar open
                fill = S["op"][j]
                stop = (float(lo[:j+1].min()) if d > 0
                        else float(hi[:j+1].max()))
                r = run_trade(S, j, d, fill, stop, tg, n)
                if r and abs(fill - stop) > 0:
                    taken += 1
                    rows.append({**r, "day": S["day"], "year": S["year"],
                                 "dir": d, "seq": taken,
                                 "risk_bps": 1e4*r["risk"]/S["px"],
                                 "cost_pct": 100*S["px"]*COST_F/r["risk"]})
                    i = r["j"] + 1
                    continue
            i += 1
    return pd.DataFrame(rows), look


def report(T, look, name, tg):
    if T.empty:
        print(f"  {name:<22} no trades"); return None
    R = T.R; w, l = R[R > 0], R[R <= 0]
    per = R.groupby(T.day).sum()
    t = per.mean()/(per.std(ddof=1)/sqrt(len(per))) if len(per) > 2 else np.nan
    pf = w.sum()/abs(l.sum()) if len(l) and l.sum() else np.inf
    top = R.sort_values(ascending=False).head(int(np.ceil(0.01*len(R)))).sum()
    ex1 = R.sum() - top
    hi_cost = (R - 0.5*T.cost_pct/100.0)
    yrs = R.groupby(T.year).mean()
    yp = int((yrs > 0).sum())
    ok = (R.mean() > 0 and pf > 1.15 and yp >= 4 and ex1 > 0
          and hi_cost.mean() > 0)
    print(f"  {name:<22}{len(T):>7,}{T.day.nunique():>8,}{R.mean():>+9.4f}"
          f"{pf:>7.2f}{t:>+7.2f}{yp:>4}/6{ex1:>+9.1f}{hi_cost.mean():>+10.4f}"
          f"{T.risk_bps.median():>9.1f}b{T.cost_pct.median():>7.2f}%"
          f"{100*T.amb.mean():>6.1f}%{look:>6}{'SURVIVES' if ok else '':>10}")
    return dict(name=name, tg=tg, n=len(T), sess=T.day.nunique(),
                exp=R.mean(), pf=pf, t=t, yp=yp, ex1=ex1,
                hc=hi_cost.mean(), ok=ok, T=T)


def main():
    S = load()
    print("="*126)
    print("  REOPENED FAMILIES — flat at the cash close (15:59), "
          "honest fills, entry bar excluded, 2pt round turn")
    print("="*126)
    print(f"  sessions loaded {len(S):,}   {S[0]['day']} .. {S[-1]['day']}")
    print("  Test 1 was ALREADY run under this exit: the minute data ends "
          "15:59 and the post-window\n  had no upper bound. Only the second "
          "trade is new.\n")
    hdr = (f"  {'variant':<22}{'trades':>7}{'sessions':>8}{'expR':>9}"
           f"{'PF':>7}{'t':>7}{'yrs+':>7}{'ex-top1%':>9}{'+50% cost':>10}"
           f"{'med risk':>10}{'cost/R':>8}{'amb':>6}{'look':>6}{'':>10}")
    res = []
    print("  TEST 1 — IB BY REJECTION, MAX 2 TRADES")
    print(hdr)
    for k, tg in EXITS:
        T, lk = test1(S, tg); r = report(T, lk, f"IB {k}", tg)
        if r: r["fam"] = "IB"; res.append(r)
    print("\n  TEST 2 — VWAP MEAN REVERSION, FIRST TWO SIGNALS, NON-CONCURRENT")
    print(hdr)
    for k, tg in EXITS:
        T, lk = test2(S, tg); r = report(T, lk, f"VWAP {k}", tg)
        if r: r["fam"] = "VWAP"; res.append(r)

    print("\n" + "="*126)
    print("  DIAGNOSTICS — excursions, fills, direction, sequence")
    print("="*126)
    print(f"  {'variant':<22}{'mean MFE':>10}{'mean MAE':>10}{'naive expR':>12}"
          f"{'correction':>12}{'trade1 expR':>13}{'trade2 expR':>13}"
          f"{'n trade2':>10}")
    for r in res:
        T = r["T"]; t2 = T[T.seq == 2]
        print(f"  {r['name']:<22}{T.mfe.mean():>+10.3f}{T.mae.mean():>+10.3f}"
              f"{T.naive_R.mean():>+12.4f}"
              f"{T.naive_R.mean()-T.R.mean():>+12.4f}"
              f"{T[T.seq==1].R.mean():>+13.4f}"
              f"{(t2.R.mean() if len(t2) else np.nan):>+13.4f}{len(t2):>10,}")

    print("\n" + "="*126)
    print("  BY YEAR — mean R")
    print("="*126)
    yrs = sorted({y for r in res for y in r["T"].year.unique()})
    print(f"  {'variant':<22}" + "".join(f"{y:>11}" for y in yrs))
    for r in res:
        g = r["T"].groupby("year").R.mean()
        print(f"  {r['name']:<22}" + "".join(
            f"{g[y]:>+11.4f}" if y in g.index else f"{'--':>11}" for y in yrs))

    print("\n" + "="*126)
    print("  DECISION — all five required: expR>0, PF>1.15, >=4/6 years, "
          "ex-top1%>0, positive at +50% cost")
    print("="*126)
    for fam in ("IB", "VWAP"):
        f = [r for r in res if r["fam"] == fam]
        s = [r for r in f if r["ok"]]
        print(f"  {fam:<6} survivors: {len(s)} of {len(f)}"
              + ("   -> FAMILY CLOSES" if not s else
                 "   -> " + ", ".join(x["name"] for x in s)))
    print("\n  Sealed NQ days were not read. 2016-2020 NOT opened.")


if __name__ == "__main__":
    main()
