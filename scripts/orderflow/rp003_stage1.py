#!/usr/bin/env python3
"""RP-003 Stage 1 — QQQ/SPY beta residual behaviour. DESCRIPTIVE ONLY.

No P&L, no profit factor, no drawdown, no entries, stops or targets.

Frozen definitions (approved, not to be varied):
  aligned 1-min bars; sessions with <380 aligned bars dropped; no-intercept
  rolling beta from the previous 20 COMPLETED sessions with the current session
  excluded; 15-minute cumulative residual; normalised by its trailing 20-session
  sd; EXTREME |z|>=2.0; ORDINARY 0.5<=|z|<1.0; 60-minute cooldown; horizons
  5/15/30/60; contraction reported positive when movement is toward zero.

Discovery block 2021-2022 ONLY. 2023 and 2024-2025 are not read by this run.

Contraction is the TRADEABLE quantity, not a re-measured rolling statistic:
    F_h = ln(Q_{t+h}/Q_t) - beta*ln(S_{t+h}/S_t)      forward residual return
    C_h = -sign(R_t) * F_h                            positive = toward zero
    closed_h = C_h / |R_t|
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
BLOCK = ("2021-01-04", "2022-12-31")     # DISCOVERY ONLY
NBARS_MIN = 380
BETA_LOOKBACK = 20
FORM = 15
Z_EXT, Z_ORD_LO, Z_ORD_HI = 2.0, 0.5, 1.0
COOLDOWN = 60
HORIZONS = (5, 15, 30, 60)
SEED = 20260923


def load():
    q = pd.read_parquet(ROOT / "data/intraday_long/QQQ_1m.parquet")
    s = pd.read_parquet(ROOT / "data/related/SPY_1m.parquet")
    for d in (q, s):
        d["ts"] = pd.to_datetime(d["timestamp"])
    m = q[["ts", "close"]].merge(s[["ts", "close"]], on="ts", suffixes=("_q", "_s"))
    m["date"] = m["ts"].dt.normalize()
    m = m[(m["date"] >= BLOCK[0]) & (m["date"] <= BLOCK[1])].sort_values("ts")
    keep = m.groupby("date").size()
    good = keep[keep >= NBARS_MIN].index
    dropped = len(keep) - len(good)
    m = m[m["date"].isin(good)]
    return m, dropped


def sessionise(m):
    """Per-session arrays of 1-minute log returns and minute-of-day."""
    out = {}
    for d, g in m.groupby("date"):
        g = g.sort_values("ts")
        lq = np.log(g["close_q"].values)
        ls = np.log(g["close_s"].values)
        out[d] = dict(
            tod_min=(g["ts"].dt.hour * 60 + g["ts"].dt.minute).values,
            lq=lq, ls=ls, rq=np.diff(lq), rs=np.diff(ls),
        )
    return out


def beta_and_sigma(S, days, i, mult=1.0):
    """No-intercept OLS beta from the 20 PRIOR sessions, and the sd of 15-minute
    cumulative residuals over those same sessions. Current session excluded."""
    num = den = 0.0
    res = []
    for j in range(i - BETA_LOOKBACK, i):
        d = S[days[j]]
        num += float(np.dot(d["rq"], d["rs"]))
        den += float(np.dot(d["rs"], d["rs"]))
    if den <= 0:
        return np.nan, np.nan
    beta = mult * num / den
    for j in range(i - BETA_LOOKBACK, i):
        d = S[days[j]]
        lq, ls = d["lq"], d["ls"]
        if len(lq) <= FORM:
            continue
        r = (lq[FORM:] - lq[:-FORM]) - beta * (ls[FORM:] - ls[:-FORM])
        res.append(r)
    if not res:
        return beta, np.nan
    return beta, float(np.concatenate(res).std(ddof=1))


def signals(z, lo, hi):
    """Indices where lo <= |z| < hi (hi=inf for extreme), with a 60-min cooldown."""
    out, until = [], -1
    for t in range(len(z)):
        if t <= until or not np.isfinite(z[t]):
            continue
        a = abs(z[t])
        if a >= lo and (hi is None or a < hi):
            out.append(t)
            until = t + COOLDOWN
    return out


def forward(lq, ls, beta, t, R):
    """Contraction path for one signal. Positive = toward zero."""
    sg = np.sign(R)
    n = len(lq)
    rec = {}
    path = []
    for h in range(1, max(HORIZONS) + 1):
        if t + h >= n:
            break
        F = (lq[t + h] - lq[t]) - beta * (ls[t + h] - ls[t])
        path.append(-sg * F * 1e4)          # bps, positive = contraction
    path = np.array(path)
    absR = abs(R) * 1e4
    for h in HORIZONS:
        if len(path) >= h:
            c = path[h - 1]
            rec[f"c{h}"] = c
            rec[f"f{h}"] = c / absR if absR > 0 else np.nan
            rec[f"adv{h}"] = float(max(0.0, -path[:h].min()))
        else:
            rec[f"c{h}"] = rec[f"f{h}"] = rec[f"adv{h}"] = np.nan
    half = np.where(path >= 0.5 * absR)[0]
    rec["t_half"] = float(half[0] + 1) if len(half) else np.nan
    rec["absR"] = absR
    return rec


def collect(S, days, start, mult=1.0, donor=None, qqq_only=False,
            lo=Z_EXT, hi=None):
    rows = []
    for i in range(start, len(days)):
        d = S[days[i]]
        beta, sig = beta_and_sigma(S, days, i, mult)
        if not np.isfinite(beta) or not np.isfinite(sig) or sig <= 0:
            continue
        lq, ls, tod = d["lq"], d["ls"], d["tod_min"]
        if donor is not None:                      # date-shuffled SPY leg
            dd = S[donor[days[i]]]
            k = min(len(lq), len(dd["ls"]))
            lq, ls, tod = lq[:k], dd["ls"][:k], tod[:k]
        n = len(lq)
        R = np.full(n, np.nan)
        R[FORM:] = (lq[FORM:] - lq[:-FORM]) - beta * (ls[FORM:] - ls[:-FORM])
        z = R / sig
        for t in signals(z, lo, hi):
            if qqq_only:
                rec = forward(lq, ls * 0.0, 0.0, t, R[t])   # hedge removed
            else:
                rec = forward(lq, ls, beta, t, R[t])
            rec.update(date=days[i], tod=int(tod[t]), sign=int(np.sign(R[t])),
                       z=z[t], beta=beta)
            rows.append(rec)
    return pd.DataFrame(rows)


def table(df, label):
    if not len(df):
        return pd.DataFrame([dict(set=label, n=0)])
    out = []
    for h in HORIZONS:
        c, f, a = df[f"c{h}"].dropna(), df[f"f{h}"].dropna(), df[f"adv{h}"].dropna()
        out.append(dict(
            set=label, h=h, n=len(c),
            mean_bps=round(c.mean(), 2), med_bps=round(c.median(), 2),
            pct_closed=round(100 * f.mean(), 1),
            any_contract=round(100 * (c > 0).mean(), 1),
            c25=round(100 * (f >= .25).mean(), 1), c50=round(100 * (f >= .50).mean(), 1),
            c75=round(100 * (f >= .75).mean(), 1), c100=round(100 * (f >= 1.0).mean(), 1),
            expand=round(100 * (c < 0).mean(), 1),
            max_adv=round(a.mean(), 2),
        ))
    return pd.DataFrame(out)


def main() -> int:
    m, dropped = load()
    S = sessionise(m)
    days = sorted(S.keys())
    start = BETA_LOOKBACK
    months = len(pd.PeriodIndex(pd.DatetimeIndex(days[start:]), freq="M").unique())

    print(f"DISCOVERY {BLOCK[0]} .. {BLOCK[1]}  (2023 and 2024-25 NOT read)")
    print(f"sessions aligned {len(days)} | dropped <{NBARS_MIN} bars {dropped} | "
          f"beta warm-up {start} | usable {len(days)-start} | months {months}")

    EXT = collect(S, days, start)
    ORD = collect(S, days, start, lo=Z_ORD_LO, hi=Z_ORD_HI)

    print("\n=== 1. COUNTS FIRST ===")
    for lab, df in (("EXTREME |z|>=2.0", EXT), ("ORDINARY 0.5<=|z|<1.0", ORD)):
        pos, neg = int((df["sign"] > 0).sum()), int((df["sign"] < 0).sum())
        print(f"  {lab:24s} n={len(df):5d}  per month {len(df)/months:6.2f}  "
              f"pos {pos:5d} / neg {neg:5d}  mean |R| {df.absR.mean():5.2f} bps")
    print("\n  signals per horizon availability (EXTREME):")
    print("   " + "  ".join(f"h{h}: {int(EXT[f'c{h}'].notna().sum())}" for h in HORIZONS))
    print("\n  EXTREME by time-of-day bucket:")
    for lab, a, b in (("09:30-11:00", 570, 660), ("11:00-14:00", 660, 840),
                      ("14:00-16:00", 840, 960)):
        k = EXT[(EXT["tod"] >= a) & (EXT["tod"] < b)]
        print(f"    {lab}  n={len(k):5d}  {100*len(k)/max(len(EXT),1):5.1f}%")
    print("\n  EXTREME by year:")
    for y, g in EXT.groupby(pd.DatetimeIndex(EXT.date).year):
        print(f"    {y}  n={len(g):5d}  per month {len(g)/ (months/2):6.2f}")

    print("\n=== 2. CONTRACTION, EXTREME vs ORDINARY ===")
    print(pd.concat([table(EXT, "EXTREME"), table(ORD, "ORDINARY")]).to_string(index=False))

    print("\n=== 3. POSITIVE vs NEGATIVE RESIDUALS (EXTREME) ===")
    print(pd.concat([table(EXT[EXT.sign > 0], "EXT-POS"),
                     table(EXT[EXT.sign < 0], "EXT-NEG")]).to_string(index=False))

    print("\n=== 4. CONTROL: WRONG BETA ===")
    print(pd.concat([table(EXT, "beta x1.00"),
                     table(collect(S, days, start, mult=0.75), "beta x0.75"),
                     table(collect(S, days, start, mult=1.25), "beta x1.25")
                     ]).to_string(index=False))

    print("\n=== 5. CONTROL: DATE-SHUFFLED SPY PAIRING ===")
    rs = np.random.default_rng(SEED)
    rvs = {d: float(np.std(S[d]["rs"])) for d in days}
    donor = {}
    for d in days[start:]:
        yr = pd.Timestamp(d).year
        cand = [c for c in days if pd.Timestamp(c).year == yr and c != d
                and abs(rvs[c] - rvs[d]) <= 0.10 * rvs[d]]
        donor[d] = cand[rs.integers(len(cand))] if cand else d
    print(pd.concat([table(EXT, "true pairing"),
                     table(collect(S, days, start, donor=donor), "date-shuffled")
                     ]).to_string(index=False))

    print("\n=== 6. CONTROL: QQQ ALONE, HEDGE REMOVED ===")
    print(pd.concat([table(EXT, "hedged residual"),
                     table(collect(S, days, start, qqq_only=True), "QQQ only")
                     ]).to_string(index=False))

    print("\n=== 7. TIME-OF-DAY (EXTREME) ===")
    tod = []
    for lab, a, b in (("09:30-11:00", 570, 660), ("11:00-14:00", 660, 840),
                      ("14:00-16:00", 840, 960)):
        tod.append(table(EXT[(EXT["tod"] >= a) & (EXT["tod"] < b)], lab))
    print(pd.concat(tod).to_string(index=False))

    print("\n=== 8. BY YEAR (EXTREME) ===")
    yr = [table(g, str(y)) for y, g in EXT.groupby(pd.DatetimeIndex(EXT.date).year)]
    print(pd.concat(yr).to_string(index=False))

    print(f"\n  median time to first 50% contraction: "
          f"{EXT.t_half.median():.1f} min | resolved within 60 min on "
          f"{100*EXT.t_half.notna().mean():.1f}% of signals")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
