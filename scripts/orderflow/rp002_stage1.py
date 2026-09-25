#!/usr/bin/env python3
"""RP-002 Stage 1 — descriptive mechanism test. NO expectancy, NO P&L.

Pre-registered `1a65e8c`, Stage 1 authorised with rulings. Discovery block only:
QQQ 2021-01-04 -> 2024-12-31. The 2025-01 -> 2026-08 internal validation block is
NOT read here -- Stage 1 is descriptive, and spending the validation block on a
descriptive pass would burn it.

Two specification details resolved before running, both declared in the report:

1. "Second highest DISTINCT bar high" would break ties wrongly. The approved
   intent is two-bar confirmation: an extreme is admitted if >=2 bars traded at
   or beyond it. If two bars both print X, X IS confirmed and must remain the
   clean high; de-duplicating would discard it. Implemented as the second-largest
   value of the bar-high multiset (ties kept), which is exactly the confirmation
   rule.

2. The six states are not exhaustive as written. Location has THREE bins, not
   two: the open can land in the outer third OPPOSITE the overnight direction.
   Folding that into "middle" would contaminate S4, whose whole job is to be the
   location control at the same q. It is kept as a reported residual instead.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RTH = ROOT / "data/intraday_long/QQQ_1m.parquet"
ETH = ROOT / "data/intraday_long/QQQ_1m_eth.parquet"

DISC = ("2021-01-04", "2024-12-31")   # discovery block, frozen at 1a65e8c
ON_START, ON_END = "04:00", "09:29"   # overnight window, approved
LOOKBACK = 60                         # trailing sessions for the q percentile
SEED = 20260923


# ------------------------------------------------------------------ loading

def sessions():
    """Per-session state variables plus the cash-session path."""
    r = pd.read_parquet(RTH)
    e = pd.read_parquet(ETH)
    for d in (r, e):
        d["ts"] = pd.to_datetime(d["timestamp"])
        d["date"] = d["ts"].dt.normalize()
        d["t"] = d["ts"].dt.time

    r = r[(r["date"] >= DISC[0]) & (r["date"] <= DISC[1])]
    e = e[(e["date"] >= DISC[0]) & (e["date"] <= DISC[1])]

    on = e[(e["t"] >= pd.Timestamp(ON_START).time())
           & (e["t"] <= pd.Timestamp(ON_END).time())]

    recs, paths = [], {}
    prev_close = None
    for date, g in r.groupby("date", sort=True):
        g = g.sort_values("ts")
        o = on[on["date"] == date]
        if prev_close is None or len(o) < 30 or len(g) < 300:
            prev_close = float(g["close"].iloc[-1])
            continue

        hi, lo = np.sort(o["high"].values)[::-1], np.sort(o["low"].values)
        # two-bar confirmation: second-largest / second-smallest, TIES KEPT
        ch, cl = float(hi[1]), float(lo[1])
        rh, rl = float(hi[0]), float(lo[0])

        px0929 = float(o["close"].iloc[-1])
        cash_open = float(g["open"].iloc[0])
        rng = ch - cl
        if rng <= 0:
            prev_close = float(g["close"].iloc[-1])
            continue

        recs.append(dict(
            date=date, prev_close=prev_close, px0929=px0929, cash_open=cash_open,
            ch=ch, cl=cl, rh=rh, rl=rl, rng=rng,
            raw_rng=rh - rl,
            on_ret=px0929 / prev_close - 1.0,
            loc=(cash_open - cl) / rng,
        ))
        paths[date] = g[["t", "open", "high", "low", "close"]].reset_index(drop=True)
        prev_close = float(g["close"].iloc[-1])

    S = pd.DataFrame(recs).set_index("date")
    return S, paths


# ------------------------------------------------------------------ states

def classify(S: pd.DataFrame) -> pd.DataFrame:
    a = S["on_ret"].abs()
    # causal: percentile of |on_ret| within the PRECEDING LOOKBACK sessions only
    q = pd.Series(index=S.index, dtype=float)
    v = a.values
    for i in range(LOOKBACK, len(v)):
        w = v[i - LOOKBACK:i]
        q.iloc[i] = (w < v[i]).mean()
    S = S.assign(q=q, d=np.sign(S["on_ret"]))
    S = S[S["q"].notna() & (S["d"] != 0)]

    up, loc = S["d"] > 0, S["loc"]
    corr_outer = np.where(up, loc >= 2 / 3, loc <= 1 / 3)
    opp_outer = np.where(up, loc <= 1 / 3, loc >= 2 / 3)
    middle = ~corr_outer & ~opp_outer

    tier = np.where(S["q"] >= 0.67, "hi", np.where(S["q"] >= 0.33, "mid", "lo"))
    st = np.full(len(S), "RESID", dtype=object)
    for t, o, name in (("hi", "c", "S1"), ("mid", "c", "S2"), ("lo", "c", "S3"),
                       ("hi", "m", "S4"), ("mid", "m", "S5"), ("lo", "m", "S6")):
        sel = (tier == t) & (corr_outer if o == "c" else middle)
        st[sel] = name
    return S.assign(state=st, corr_outer=corr_outer, opp_outer=opp_outer)


# ------------------------------------------------------------------ metrics

def at(p, hhmm):
    m = p["t"] == pd.Timestamp(hhmm).time()
    return float(p.loc[m, "close"].iloc[0]) if m.any() else np.nan


def window(p, a, b):
    return p[(p["t"] >= pd.Timestamp(a).time()) & (p["t"] <= pd.Timestamp(b).time())]


def metrics(row, p):
    d, o = row["d"], row["cash_open"]
    r15, r60 = at(p, "09:44"), at(p, "10:29")
    r1100 = at(p, "10:59")
    full = window(p, "09:30", "15:59")
    late = window(p, "09:45", "15:59")

    c = np.log(full["close"].values)
    h1 = window(p, "09:30", "10:29")
    lr = np.diff(np.log(h1["close"].values))
    rv = float(np.sqrt(np.sum(lr ** 2)) * 1e4)

    def exc(w, anchor):
        if not len(w):
            return np.nan, np.nan
        fav = (w["high"].max() - anchor) if d > 0 else (anchor - w["low"].min())
        adv = (anchor - w["low"].min()) if d > 0 else (w["high"].max() - anchor)
        return 1e4 * fav / anchor, 1e4 * adv / anchor

    mfe, mae = exc(full, o)
    mfe45, mae45 = exc(late, at(p, "09:44"))

    gap = o - row["prev_close"]
    if abs(gap) > 0:
        retr = ((o - full["low"].min()) if gap > 0 else (full["high"].max() - o)) / abs(gap)
    else:
        retr = np.nan

    return dict(
        ret15=1e4 * d * (r15 / o - 1), ret60=1e4 * d * (r60 / o - 1),
        ret0945_1100=1e4 * d * (r1100 / r15 - 1),
        rv_h1=rv,
        mfe=mfe, mae=mae, mfe45=mfe45, mae45=mae45,
        touch_onhi=float(full["high"].max() >= row["ch"]),
        touch_onlo=float(full["low"].min() <= row["cl"]),
        touch_prevclose=float((full["low"].min() <= row["prev_close"])
                              & (full["high"].max() >= row["prev_close"])),
        gap_half=float(retr >= 0.5) if np.isfinite(retr) else np.nan,
        ext15=float(d * (r15 / o - 1) > 0),
        on_rng_bps=1e4 * row["rng"] / o,
    )


def summarise(S, M, idx, label, months):
    if not len(idx):
        return dict(state=label, n=0)
    s, m = S.loc[idx], M.loc[idx]
    return dict(
        state=label, n=len(idx), per_mo=round(len(idx) / months, 2),
        long=int((s["d"] > 0).sum()), short=int((s["d"] < 0).sum()),
        ret15=round(m.ret15.mean(), 1), ret60=round(m.ret60.mean(), 1),
        r0945_1100=round(m.ret0945_1100.mean(), 1),
        rv_h1=round(m.rv_h1.mean(), 1),
        MFE=round(m.mfe.mean(), 1), MAE=round(m.mae.mean(), 1),
        MFE45=round(m.mfe45.mean(), 1), MAE45=round(m.mae45.mean(), 1),
        t_hi=round(100 * m.touch_onhi.mean(), 1),
        t_lo=round(100 * m.touch_onlo.mean(), 1),
        t_prev=round(100 * m.touch_prevclose.mean(), 1),
        gap50=round(100 * m.gap_half.mean(), 1),
        ext=round(100 * m.ext15.mean(), 1),
        onrng=round(m.on_rng_bps.mean(), 1),
    )


def main() -> int:
    S, paths = sessions()
    S = classify(S)
    months = len(pd.PeriodIndex(S.index, freq="M").unique())
    M = pd.DataFrame([metrics(r, paths[d]) for d, r in S.iterrows()], index=S.index)

    print(f"DISCOVERY {DISC[0]} -> {DISC[1]} | usable sessions {len(S)} | "
          f"months {months} | warm-up dropped {LOOKBACK}")

    print("\n--- 1. CLEANING IMPACT (raw is diagnostic only) ---")
    shrink = 1e4 * (S.raw_rng - S.rng) / S.cash_open
    print(f"  sessions where cleaning changed the range: "
          f"{int((shrink > 0.01).sum())} of {len(S)} ({100*(shrink>0.01).mean():.1f}%)")
    print(f"  range shrink bps: median {shrink.median():.1f} | "
          f"p90 {shrink.quantile(.90):.1f} | p99 {shrink.quantile(.99):.1f} | "
          f"max {shrink.max():.1f}")
    print(f"  mean ON range bps: raw {1e4*(S.raw_rng/S.cash_open).mean():.1f} -> "
          f"clean {1e4*(S.rng/S.cash_open).mean():.1f}")

    print("\n--- 2. STATE COUNTS ---")
    rows = [summarise(S, M, S.index[S.state == k], k, months)
            for k in ["S1", "S2", "S3", "S4", "S5", "S6"]]
    rows.append(summarise(S, M, S.index[S.state == "RESID"], "RESID", months))
    T = pd.DataFrame(rows)
    print(T[["state", "n", "per_mo", "long", "short", "onrng", "ext"]].to_string(index=False))
    print(f"\n  opposite-outer residual: {int(S.opp_outer.sum())} sessions "
          f"({100*S.opp_outer.mean():.1f}%) -- reported, not folded into S4")

    print("\n--- 3. S1 vs CONTROLS ---")
    # matched-random control: non-S1 sessions matched on cleaned ON range in bps
    rng_bps = M.on_rng_bps
    rs = np.random.default_rng(SEED)
    pool = list(S.index[S.state != "S1"])
    matched = []
    for d0 in S.index[S.state == "S1"]:
        tgt = rng_bps[d0]
        cand = [c for c in pool if abs(rng_bps[c] - tgt) <= 0.10 * tgt]
        if cand:
            pick = cand[rs.integers(len(cand))]
            matched.append(pick); pool.remove(pick)
    rows = [summarise(S, M, S.index[S.state == k], k, months) for k in ("S1", "S3", "S4")]
    rows.append(summarise(S, M, pd.Index(matched), "MATCHED", months))
    C = pd.DataFrame(rows)
    print(C[["state", "n", "onrng", "ret15", "ret60", "r0945_1100", "rv_h1",
             "MFE", "MAE", "MFE45", "MAE45", "t_hi", "t_lo", "t_prev", "gap50"]]
          .to_string(index=False))

    print("\n--- 4. S1 CONTINUATION vs REJECTION (never pooled) ---")
    s1 = S.index[S.state == "S1"]
    ext = s1[M.loc[s1, "ext15"] == 1]
    rej = s1[M.loc[s1, "ext15"] == 0]
    B = pd.DataFrame([summarise(S, M, ext, "S1-EXTEND", months),
                      summarise(S, M, rej, "S1-REJECT", months)])
    print(B[["state", "n", "per_mo", "long", "short", "ret60", "r0945_1100",
             "MFE", "MAE", "MFE45", "MAE45", "t_hi", "t_lo", "t_prev", "gap50"]]
          .to_string(index=False))

    print("\n--- 5. YEARLY STABILITY ---")
    for lab, idx in (("S1", s1), ("S1-EXTEND", ext), ("S1-REJECT", rej),
                     ("S3", S.index[S.state == "S3"]), ("S4", S.index[S.state == "S4"])):
        yr = {}
        for y, g in M.loc[idx].groupby(S.loc[idx].index.year):
            yr[int(y)] = (len(g), round(g.ret60.mean(), 1), round(g.ret0945_1100.mean(), 1))
        print(f"  {lab:10s} " + "  ".join(f"{y}:n{n} h1{a:+.0f} late{b:+.0f}"
                                          for y, (n, a, b) in yr.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
