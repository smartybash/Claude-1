#!/usr/bin/env python3
"""RP-005 Stage 1 — close auction / time-constrained flow. DESCRIPTIVE ONLY.

No P&L, no expectancy, no profit factor, no evaluation simulation.

Discovery 2021-2023, internal validation 2024-2025, both frozen before running.
Jan-Aug 2026 is EXCLUDED: it sits inside the QQQ discovery set already used by
the IB midpoint pullback, pre-open conditioning and compression families, so it
is contaminated rather than a clean diagnostic period.

The state window ends at the 15:00 bar OPEN and every reported outcome starts at
that same price, so no part of the classifying return is inside any headline
outcome.

Data ends at 15:59. The official 16:00 auction print is NOT in the dataset. This
tests movement INTO the close, not the auction itself.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RTH = ROOT / "data/intraday_long/QQQ_1m.parquet"
DISC = ("2021-01-04", "2023-12-31")
VAL = ("2024-01-01", "2025-12-31")
LOOKBACK = 60
SEED = 20260923


def load():
    d = pd.read_parquet(RTH)
    d["ts"] = pd.to_datetime(d["timestamp"])
    d["date"] = d["ts"].dt.normalize()
    d["t"] = d["ts"].dt.time
    return d[d["date"] <= VAL[1]]


def px_at(g, hhmm, field="open"):
    m = g["t"] == pd.Timestamp(hhmm).time()
    return float(g.loc[m, field].iloc[0]) if m.any() else np.nan


def win(g, a, b):
    return g[(g["t"] >= pd.Timestamp(a).time()) & (g["t"] <= pd.Timestamp(b).time())]


def rv(g):
    if len(g) < 3:
        return np.nan
    return float(np.sqrt(np.sum(np.diff(np.log(g["close"].values)) ** 2)) * 1e4)


def build():
    d = load()
    days = sorted(d["date"].unique())
    G = {k: v.sort_values("ts").reset_index(drop=True) for k, v in d.groupby("date")}

    recs, short_days = [], 0
    for i, day in enumerate(days):
        g = G[day]
        p0930 = px_at(g, "09:30")
        p1300 = px_at(g, "13:00")
        p1400 = px_at(g, "14:00")
        p1500 = px_at(g, "15:00")
        p1530 = px_at(g, "15:30")
        if not np.isfinite([p0930, p1300, p1400, p1500, p1530]).all() or len(g) < 380:
            short_days += 1
            continue
        last = float(g["close"].iloc[-1])

        pre = win(g, "09:30", "14:59")
        post = win(g, "15:00", "15:59")
        d15 = np.sign(p1500 / p0930 - 1.0)
        if d15 == 0:
            continue

        mfe = (post["high"].max() - p1500) if d15 > 0 else (p1500 - post["low"].min())
        mae = (p1500 - post["low"].min()) if d15 > 0 else (post["high"].max() - p1500)
        newext = (post["high"].max() > pre["high"].max()) if d15 > 0 \
            else (post["low"].min() < pre["low"].min())

        # 14:00-14:59 control, built the same way one hour earlier
        pre14 = win(g, "09:30", "13:59")
        post14 = win(g, "14:00", "14:59")
        d14 = np.sign(p1400 / p0930 - 1.0)
        p1459 = float(post14["close"].iloc[-1]) if len(post14) else np.nan

        recs.append(dict(
            date=day, i=i, p1500=p1500, last=last, d=d15,
            ret_state=abs(p1500 / p0930 - 1.0),
            ret_1300_1500=1e4 * d15 * (p1500 / p1300 - 1.0),
            r1530=1e4 * d15 * (p1530 / p1500 - 1.0),
            r1559=1e4 * d15 * (last / p1500 - 1.0),
            mfe=1e4 * mfe / p1500, mae=1e4 * mae / p1500,
            rv_post=rv(post), rv_pre=rv(pre),
            close_with=float(d15 * (last - p1500) > 0),
            new_extreme=float(newext),
            move=last - p1500,
            # 14:00 control
            c14_state=abs(p1400 / p0930 - 1.0), c14_d=d14,
            c14_ret=1e4 * d14 * (p1459 / p1400 - 1.0) if np.isfinite(p1459) else np.nan,
        ))

    S = pd.DataFrame(recs).set_index("date")

    # next-session diagnostics
    nxt = {}
    for k, r in S.iterrows():
        j = int(r["i"]) + 1
        if j >= len(days):
            continue
        gn = G[days[j]]
        w = win(gn, "09:30", "10:00")
        if len(w) < 10:
            continue
        no = px_at(gn, "09:30")
        adverse = (r["last"] - w["low"].min()) if r["d"] > 0 else (w["high"].max() - r["last"])
        frac = adverse / abs(r["move"]) if abs(r["move"]) > 1e-9 else np.nan
        nxt[k] = dict(
            nm_ret=1e4 * r["d"] * (float(w["close"].iloc[-1]) / no - 1.0),
            retr25=float(frac >= 0.25), retr50=float(frac >= 0.50),
            retr75=float(frac >= 0.75),
        )
    S = S.join(pd.DataFrame(nxt).T)
    print(f"sessions built {len(S)} | dropped for short/incomplete: {short_days}")
    return S


def tier(S, col):
    v = S[col].values
    q = np.full(len(v), np.nan)
    for i in range(LOOKBACK, len(v)):
        q[i] = (v[i - LOOKBACK:i] < v[i]).mean()
    return q


def summarise(S, idx, label):
    if len(idx) == 0:
        return dict(state=label, n=0)
    s = S.loc[idx]
    mo = len(pd.PeriodIndex(s.index, freq="M").unique())
    return dict(
        state=label, n=len(s), per_mo=round(len(s) / max(mo, 1), 2),
        up=int((s.d > 0).sum()), dn=int((s.d < 0).sum()),
        r1530=round(s.r1530.mean(), 1), r1559=round(s.r1559.mean(), 1),
        MFE=round(s.mfe.mean(), 1), MAE=round(s.mae.mean(), 1),
        rv=round(s.rv_post.mean(), 1),
        close_w=round(100 * s.close_with.mean(), 1),
        newext=round(100 * s.new_extreme.mean(), 1),
        nm=round(s.nm_ret.mean(), 1),
        r25=round(100 * s.retr25.mean(), 1), r50=round(100 * s.retr50.mean(), 1),
        r75=round(100 * s.retr75.mean(), 1),
    )


COLS = ["state", "n", "per_mo", "up", "dn", "r1530", "r1559", "MFE", "MAE",
        "rv", "close_w", "newext", "nm", "r25", "r50", "r75"]


def block(S, lo, hi):
    return S[(S.index >= lo) & (S.index <= hi)]


def report(S, name):
    print(f"\n{'='*100}\n{name}  n={len(S)}\n{'='*100}")
    L = S.index[S.tier == "L"]; M = S.index[S.tier == "M"]; SM = S.index[S.tier == "S"]

    print("\n--- 1/2. STATE COUNTS, LARGE vs MEDIUM vs SMALL ---")
    T = pd.DataFrame([summarise(S, L, "LARGE"), summarise(S, M, "MEDIUM"),
                      summarise(S, SM, "SMALL")])
    print(T[COLS].to_string(index=False))

    print("\n--- 3. CONTROL 1: matched realised volatility through 15:00 ---")
    rs = np.random.default_rng(SEED)
    pool = list(S.index[S.tier != "L"]); matched = []
    for k in L:
        t = S.at[k, "rv_pre"]
        cand = [c for c in pool if abs(S.at[c, "rv_pre"] - t) <= 0.10 * t]
        if cand:
            p = cand[rs.integers(len(cand))]; matched.append(p); pool.remove(p)
    print(pd.DataFrame([summarise(S, L, "LARGE"),
                        summarise(S, pd.Index(matched), "MATCHED-RV")])[COLS].to_string(index=False))
    print(f"  mean pre-15:00 RV  LARGE {S.loc[L].rv_pre.mean():.1f} bps | "
          f"MATCHED {S.loc[matched].rv_pre.mean():.1f} bps  (n={len(matched)} of {len(L)})")

    print("\n--- CONTROL 2: matched magnitude, RANDOMISED direction ---")
    flip = rs.choice([-1.0, 1.0], size=len(L))
    print(f"  LARGE 15:00->15:59 as traded {S.loc[L].r1559.mean():+.1f} bps | "
          f"direction randomised {(S.loc[L].r1559.values*flip).mean():+.1f} bps")

    print("\n--- 4. CONTROL 3: 14:00-14:59 window, same construction ---")
    L14 = S.index[S.tier14 == "L"]
    print(f"  LARGE by 14:00, 14:00->14:59 : {S.loc[L14].c14_ret.mean():+.1f} bps  n={len(L14)}")
    print(f"  LARGE by 15:00, 15:00->15:59 : {S.loc[L].r1559.mean():+.1f} bps  n={len(L)}")

    print("\n--- 5. UP vs DOWN (LARGE) ---")
    print(pd.DataFrame([summarise(S, L[S.loc[L].d > 0], "LARGE-UP"),
                        summarise(S, L[S.loc[L].d < 0], "LARGE-DOWN")])[COLS].to_string(index=False))

    print("\n--- 6. NEXT MORNING (already in nm / r25 / r50 / r75 above) ---")
    for lab, ix in (("LARGE", L), ("MEDIUM", M), ("SMALL", SM)):
        s = S.loc[ix]
        print(f"  {lab:7s} close move {s.r1559.mean():+6.1f} -> next 09:30-10:00 "
              f"{s.nm_ret.mean():+6.1f} bps | retrace>=50% on {100*s.retr50.mean():.1f}% of sessions")

    print("\n--- 8. CALENDAR (diagnostic only, never pooled) ---")
    for lab, m in (("ordinary", ~(S.eom | S.eoq | S.opex)), ("month-end (last 3)", S.eom),
                   ("quarter-end (last 3)", S.eoq), ("monthly opex", S.opex),
                   ("quarterly opex", S.qopex)):
        ix = S.index[m & (S.tier == "L")]
        if len(ix):
            s = S.loc[ix]
            print(f"  {lab:22s} n={len(ix):4d}  15:00->15:59 {s.r1559.mean():+6.1f}  "
                  f"next-am {s.nm_ret.mean():+6.1f}")

    print("\n--- 7. BY YEAR (LARGE) ---")
    for y, g in S.loc[L].groupby(S.loc[L].index.year):
        print(f"   {int(y)}  n={len(g):3d}  15:00->15:59 {g.r1559.mean():+6.1f}  "
              f"close-with {100*g.close_with.mean():4.1f}%  next-am {g.nm_ret.mean():+6.1f}")


def main() -> int:
    S = build()
    S = S.assign(q=tier(S, "ret_state"), q14=tier(S, "c14_state"))
    S = S[S.q.notna()]
    S["tier"] = np.where(S.q >= 0.67, "L", np.where(S.q >= 0.33, "M", "S"))
    S["tier14"] = np.where(S.q14 >= 0.67, "L", np.where(S.q14 >= 0.33, "M", "S"))

    dts = pd.DatetimeIndex(S.index)
    mrank = pd.Series(dts, index=S.index).groupby([dts.year, dts.month]).rank(ascending=False)
    qmask = dts.month.isin([3, 6, 9, 12])
    qrank = pd.Series(dts, index=S.index).groupby([dts.year, dts.quarter]).rank(ascending=False)
    third_fri = (dts.dayofweek == 4) & (dts.day >= 15) & (dts.day <= 21)
    S["eom"] = (mrank <= 3).values
    S["eoq"] = ((qrank <= 3) & qmask).values
    S["opex"] = third_fri
    S["qopex"] = third_fri & qmask

    print(f"\nDATA ROLES FROZEN: discovery {DISC[0]}..{DISC[1]} | "
          f"validation {VAL[0]}..{VAL[1]} | Jan-Aug 2026 EXCLUDED (contaminated)")
    report(block(S, *DISC), "DISCOVERY 2021-2023")
    report(block(S, *VAL), "INTERNAL VALIDATION 2024-2025")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
