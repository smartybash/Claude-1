#!/usr/bin/env python3
"""FROZEN IB 1R, UNCHANGED, ON RELATED INSTRUMENTS. 5-minute bars.

RELATED-INSTRUMENT CHECK, NOT A REPLICATION. Same period as discovery
(2021-2025), so the macro regime is shared; only the instrument differs.
A pass here is weaker evidence than a true out-of-period holdout.

Rule frozen at the pre-registered spec: IB 09:30-10:30, expected side =
opposite the extreme that formed first, require the 10:30 close in the 0-25%
ending zone, no trade if the opposite boundary breaks first, enter on the first
break of the expected boundary at max(trigger, bar open), stop at the opposite
IB boundary, target 1R, ONE trade, flat at the cash close. Entry bar excluded.
Cost 2 NQ points as a fraction of a ~30,000 index = 0.667 bps, the project's
standing convention applied unchanged.
"""
from __future__ import annotations
import datetime as dt, sys
from math import sqrt
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parents[2]
COST_F = 2.00 / 30000.0
TGT = 1.0


def run(df, name, lo_year=2021, hi_year=2025):
    df = df.copy()
    df["day"] = df.timestamp.dt.date
    rows, look, amb_n, ties, qual = [], 0, 0, 0, 0
    for day, g in df.groupby("day", sort=True):
        if not (lo_year <= day.year <= hi_year):
            continue
        g = g.sort_values("timestamp")
        if len(g) < 70:
            continue
        o = pd.Timestamp(dt.datetime.combine(day, dt.time(9, 30)))
        t = (g.timestamp - o).dt.total_seconds().to_numpy() / 60.0
        hi = g.high.to_numpy(float); lo = g.low.to_numpy(float)
        op = g.open.to_numpy(float); cl = g.close.to_numpy(float)
        px = float(op[0]); n = len(t)
        ib = (t >= 0) & (t < 60)
        if ib.sum() < 10 or (t >= 60).sum() < 20:
            continue
        ih, il, tib = hi[ib], lo[ib], t[ib]
        a, b = int(np.argmax(ih)), int(np.argmin(il))
        if tib[a] == tib[b]:
            ties += 1; continue
        ibh, ibl = float(ih[a]), float(il[b]); rng = ibh - ibl
        if rng <= 0:
            continue
        high_first = tib[a] < tib[b]
        close = float(cl[ib][-1])
        exp_lvl = ibl if high_first else ibh
        stop = ibh if high_first else ibl
        ez = 100.0 * abs(close - exp_lvl) / rng
        if ez >= 25:
            continue
        qual += 1
        d = -1 if high_first else 1
        i0 = int(np.searchsorted(t, 60, "left"))
        fe = np.where(hi[i0:] > exp_lvl)[0] if d > 0 else np.where(lo[i0:] < exp_lvl)[0]
        fo = np.where(lo[i0:] < stop)[0] if d > 0 else np.where(hi[i0:] > stop)[0]
        if len(fe) == 0:
            continue
        if len(fo) and int(fo[0]) < int(fe[0]):
            continue
        i = i0 + int(fe[0])
        if i + 1 >= n:
            continue
        if i < i0:
            look += 1
        fill = max(exp_lvl, op[i]) if d > 0 else min(exp_lvl, op[i])
        risk = abs(fill - stop)
        if risk <= 0:
            continue
        cost = px * COST_F
        tgt = fill + d * TGT * risk
        ex, why, mfe, mae, ambi = None, "", 0.0, 0.0, False
        for j in range(i + 1, n):                      # entry bar EXCLUDED
            fav = d * (hi[j] - fill) if d > 0 else d * (lo[j] - fill)
            adv = d * (lo[j] - fill) if d > 0 else d * (hi[j] - fill)
            mfe = max(mfe, fav); mae = min(mae, adv)
            st = lo[j] <= stop if d > 0 else hi[j] >= stop
            ht = hi[j] >= tgt if d > 0 else lo[j] <= tgt
            if st and ht: ambi = True
            if st:
                ex = min(stop, op[j]) if d > 0 else max(stop, op[j]); why = "stop"; break
            if ht:
                ex, why = tgt, "target"; break
        if ex is None:
            ex, why = cl[-1], "close"
        amb_n += int(ambi)
        rows.append(dict(day=day, year=day.year, dir=d,
                         R=(d * (ex - fill) - cost) / risk,
                         naive_R=(d * ((stop if why == "stop" else ex) - fill) - cost) / risk,
                         why=why, risk_bps=1e4 * risk / px,
                         cost_pct=100 * cost / risk,
                         mfe=mfe / risk, mae=mae / risk, amb=ambi))
    T = pd.DataFrame(rows)
    return T, dict(name=name, look=look, ties=ties, qual=qual)


def report(T, meta, sessions_total):
    if T.empty:
        print(f"  {meta['name']:<10} no trades"); return
    R = T.R; w, l = R[R > 0], R[R <= 0]
    t = R.mean() / (R.std(ddof=1) / sqrt(len(R)))
    pf = w.sum() / abs(l.sum()) if len(l) and l.sum() else np.inf
    top = R.sort_values(ascending=False).head(int(np.ceil(0.01 * len(R)))).sum()
    ex1 = R.sum() - top
    hc = (R - 0.5 * T.cost_pct / 100.0).mean()
    yrs = R.groupby(T.year).mean()
    yp = int((yrs > 0).sum())
    ok = (R.mean() > 0 and pf > 1.15 and yp >= 4 and ex1 > 0 and hc > 0)
    print(f"  {meta['name']:<10}{sessions_total:>9,}{meta['qual']:>7,}"
          f"{len(T):>8,}{R.mean():>+9.4f}{pf:>7.2f}{t:>+7.2f}{yp:>4}/{len(yrs)}"
          f"{ex1:>+9.1f}{hc:>+10.4f}{T.risk_bps.median():>9.1f}b"
          f"{T.cost_pct.median():>7.2f}%{100*T.amb.mean():>6.1f}%"
          f"{meta['look']:>6}{'PASSES 5' if ok else '':>10}")
    return dict(name=meta['name'], T=T, yrs=yrs, t=t, pf=pf, ok=ok)


if __name__ == "__main__":
    print("=" * 130)
    print("  FROZEN IB 1R ON RELATED INSTRUMENTS — 5-minute bars, 2021-2025")
    print("=" * 130)
    print("  RELATED-INSTRUMENT CHECK, NOT A REPLICATION. Same period as")
    print("  discovery, so the macro regime is shared. Only the instrument is")
    print("  new. A pass is weaker evidence than a true out-of-period holdout.")
    print("  Rule and cost convention unchanged. Entry bar excluded.\n")
    print(f"  {'inst':<10}{'sessions':>9}{'qualif':>7}{'trades':>8}{'expR':>9}"
          f"{'PF':>7}{'t':>7}{'yrs+':>7}{'ex-top1%':>9}{'+50%cost':>10}"
          f"{'med risk':>10}{'cost/R':>7}{'amb':>6}{'look':>6}{'':>10}")
    out = []
    for sym in ("SPY", "IWM", "XLK"):
        p = ROOT / f"data/related/{sym}_5m.parquet"
        if not p.exists():
            print(f"  {sym:<10}   not fetched")
            continue
        d = pd.read_parquet(p)
        T, m = run(d, sym)
        tot = d[(d.timestamp.dt.year >= 2021) & (d.timestamp.dt.year <= 2025)]
        r = report(T, m, tot.timestamp.dt.date.nunique())
        if r: out.append(r)
    if out:
        print(f"\n  BY YEAR — mean R")
        yrs = sorted({y for r in out for y in r["yrs"].index})
        print(f"  {'inst':<10}" + "".join(f"{y:>11}" for y in yrs))
        for r in out:
            print(f"  {r['name']:<10}" + "".join(
                f"{r['yrs'][y]:>+11.4f}" if y in r["yrs"].index else f"{'--':>11}"
                for y in yrs))
        print(f"\n  EXITS / FILLS")
        print(f"  {'inst':<10}{'mean MFE':>10}{'mean MAE':>10}"
              f"{'naive expR':>12}{'correction':>12}{'exit mix':>40}")
        for r in out:
            T = r["T"]
            print(f"  {r['name']:<10}{T.mfe.mean():>+10.3f}{T.mae.mean():>+10.3f}"
                  f"{T.naive_R.mean():>+12.4f}"
                  f"{T.naive_R.mean()-T.R.mean():>+12.4f}"
                  f"{str(T.why.value_counts().to_dict()):>40}")
