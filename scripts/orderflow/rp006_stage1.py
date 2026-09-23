#!/usr/bin/env python3
"""RP-006 Stage 1 — cross-sectional intraday momentum. DESCRIPTIVE ONLY.

No P&L, entries, stops, targets, profit factor or evaluation simulation.

Discovery 2021-2022 ONLY. 2023 is not read unless every discovery pass condition
is met. 2024-2025 is additionally gated behind the IJH 5-for-1 adjustment, which
this block does not need (the split is 2024-02-22).

Frozen: SPY is the market factor and is EXCLUDED from the ranked universe.
Ranked universe is QQQ, IWM, IJH -- three instruments, therefore only three
possible strongest-versus-weakest pairs, which is thin and is reported as such.
EFA excluded entirely (9.16% stale 10:00 prints). No-intercept beta from the
previous 20 completed sessions, current session excluded. Formation 09:30-10:00.
HIGH dispersion = top tercile of D against the prior 60 completed sessions.
Outcomes at 30/60/120 minutes after 10:00 and at the cash close, measured
strictly FORWARD -- the formation return never enters an outcome.
"""
from __future__ import annotations

import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
BLOCK = ("2021-01-04", "2022-12-31")
RANKED = ("QQQ", "IWM", "IJH")
FACTOR = "SPY"
NBARS_MIN = 380
BETA_LB = 20
DISP_LB = 60
SEED = 20260923
# 1 tick spread + $0.0035/share each way, round trip, per share
COST_PER_SHARE = 0.01 + 2 * 0.0035


def load():
    paths = {"QQQ": "data/intraday_long/QQQ_1m.parquet"}
    paths.update({s: f"data/related/{s}_1m.parquet" for s in ("SPY", "IWM", "IJH")})
    F = {}
    for k, p in paths.items():
        d = pd.read_parquet(ROOT / p, columns=["timestamp", "close"])
        d["ts"] = pd.to_datetime(d["timestamp"])
        d = d[(d["ts"] >= BLOCK[0]) & (d["ts"] <= BLOCK[1] + " 23:59")]
        F[k] = d.set_index("ts")["close"]
    M = pd.DataFrame(F).dropna()
    M["date"] = M.index.normalize()
    per = M.groupby("date").size()
    good = per[per >= NBARS_MIN].index
    return M[M["date"].isin(good)], int((per < NBARS_MIN).sum())


def main() -> int:
    M, dropped = load()
    days = sorted(M["date"].unique())
    cols = list(RANKED) + [FACTOR]

    # per-session arrays
    S = {}
    for d, g in M.groupby("date"):
        g = g.sort_index()
        t = g.index
        S[d] = dict(
            log={c: np.log(g[c].values) for c in cols},
            px={c: g[c].values for c in cols},
            mod=(t.hour * 60 + t.minute).values,
        )

    def idx(d, hhmm):
        w = np.where(S[d]["mod"] == hhmm)[0]
        return int(w[0]) if len(w) else None

    rows = []
    for i in range(BETA_LB, len(days)):
        d = days[i]
        i930, i1000 = idx(d, 570), idx(d, 600)
        if i930 is None or i1000 is None:
            continue
        # causal no-intercept beta from the 20 prior COMPLETED sessions
        beta = {}
        den = sum(float(np.dot(np.diff(S[days[j]]["log"][FACTOR]),
                               np.diff(S[days[j]]["log"][FACTOR])))
                  for j in range(i - BETA_LB, i))
        if den <= 0:
            continue
        for c in RANKED:
            num = sum(float(np.dot(np.diff(S[days[j]]["log"][c]),
                                   np.diff(S[days[j]]["log"][FACTOR])))
                      for j in range(i - BETA_LB, i))
            beta[c] = num / den

        L = S[d]["log"]
        mkt_form = L[FACTOR][i1000] - L[FACTOR][i930]
        a = {c: (L[c][i1000] - L[c][i930]) - beta[c] * mkt_form for c in RANKED}
        raw = {c: L[c][i1000] - L[c][i930] for c in RANKED}

        strong = max(a, key=a.get)
        weak = min(a, key=a.get)
        rstrong = max(raw, key=raw.get)
        rweak = min(raw, key=raw.get)

        # forward, beta-adjusted, from 10:00 only
        n = len(L[FACTOR])
        fwd = {c: (L[c][i1000:] - L[c][i1000])
                  - beta[c] * (L[FACTOR][i1000:] - L[FACTOR][i1000]) for c in RANKED}
        fwd_raw = {c: L[c][i1000:] - L[c][i1000] for c in RANKED}
        spath = (fwd[strong] - fwd[weak]) * 1e4
        rpath = (fwd_raw[rstrong] - fwd_raw[rweak]) * 1e4

        rec = dict(date=d, strong=strong, weak=weak, D=1e4 * (a[strong] - a[weak]),
                   pair=" / ".join(sorted([strong, weak])),
                   cost=1e4 * COST_PER_SHARE * (1 / S[d]["px"][strong][i1000]
                                                + 1 / S[d]["px"][weak][i1000]))
        for lab, off in (("30", 30), ("60", 60), ("120", 120), ("cl", None)):
            k = (len(spath) - 1) if off is None else off
            if k >= len(spath):
                rec[f"s{lab}"] = rec[f"lng{lab}"] = rec[f"sht{lab}"] = np.nan
                rec[f"mfe{lab}"] = rec[f"mae{lab}"] = rec[f"raw{lab}"] = np.nan
                continue
            rec[f"s{lab}"] = spath[k]
            rec[f"lng{lab}"] = 1e4 * fwd[strong][k]
            rec[f"sht{lab}"] = -1e4 * fwd[weak][k]
            rec[f"mfe{lab}"] = float(spath[: k + 1].max())
            rec[f"mae{lab}"] = float(spath[: k + 1].min())
            rec[f"raw{lab}"] = rpath[k] if k < len(rpath) else np.nan
        rows.append(rec)

    R = pd.DataFrame(rows)
    # HIGH dispersion: top tercile of D vs the prior 60 COMPLETED sessions
    q = np.full(len(R), np.nan)
    Dv = R["D"].values
    for k in range(DISP_LB, len(Dv)):
        q[k] = (Dv[k - DISP_LB:k] < Dv[k]).mean()
    R = R.assign(dq=q)
    R = R[R["dq"].notna()].copy()
    R["disp"] = np.where(R["dq"] >= 2 / 3, "HIGH", "ORDINARY")
    months = len(pd.PeriodIndex(pd.DatetimeIndex(R["date"]), freq="M").unique())

    print(f"RP-006 DISCOVERY {BLOCK[0]} .. {BLOCK[1]}   (2023 and 2024-25 NOT read)")
    print("*** THREE-INSTRUMENT RANKING: only 3 possible strongest-vs-weakest "
          "pairs. This cross-section is thin. ***")
    print("\n=== 1. COUNTS AND RANKING BALANCE ===")
    print(f"  sessions used {len(R)} | dropped for alignment {dropped} | "
          f"warm-up {BETA_LB}+{DISP_LB} | months {months} | "
          f"per month {len(R)/months:.2f}")
    print(f"  HIGH dispersion {int((R.disp=='HIGH').sum())} "
          f"({len(R[R.disp=='HIGH'])/months:.2f}/mo) | "
          f"ORDINARY {int((R.disp=='ORDINARY').sum())}")
    print("\n  rank occupancy:")
    flag = False
    for c in RANKED:
        s, w = (R.strong == c).mean(), (R.weak == c).mean()
        ext = ((R.strong == c) | (R.weak == c)).mean()
        mark = "  <== >60% MECHANICAL DOMINATION" if ext > 0.60 else ""
        flag |= ext > 0.60
        print(f"    {c}: strongest {100*s:5.1f}%  weakest {100*w:5.1f}%  "
              f"either extreme {100*ext:5.1f}%{mark}")
    if flag:
        print("  *** FLAG: mechanical rank domination present. ***")
    print("\n  directional pair occurrences (6 possible, 3 unordered):")
    for a_, b_ in combinations(RANKED, 2):
        for lo, hi in ((a_, b_), (b_, a_)):
            k = int(((R.strong == lo) & (R.weak == hi)).sum())
            print(f"    long {lo:4s} / short {hi:4s}  n={k:4d}  "
                  f"{100*k/len(R):5.1f}%")

    def blk(df, lab):
        out = []
        for h in ("30", "60", "120", "cl"):
            s = df[f"s{h}"].dropna()
            if not len(s):
                continue
            out.append(dict(
                set=lab, h=h, n=len(s),
                spread=round(s.mean(), 2), med=round(s.median(), 2),
                long_leg=round(df[f"lng{h}"].mean(), 2),
                short_leg=round(df[f"sht{h}"].mean(), 2),
                pos=round(100 * (s > 0).mean(), 1),
                reversal=round(100 * (s < 0).mean(), 1),
                MFE=round(df[f"mfe{h}"].mean(), 2), MAE=round(df[f"mae{h}"].mean(), 2),
            ))
        return pd.DataFrame(out)

    print("\n=== 2. GROSS CONTINUATION BY HORIZON (forward only) ===")
    print(blk(R, "ALL").to_string(index=False))

    print("\n=== 3. PAIR-SPECIFIC NET ECONOMIC HEADROOM ===")
    print(f"  mean realised pair round-trip cost {R.cost.mean():.3f} bps | "
          f"hurdle = 3x = {3*R.cost.mean():.3f} bps")
    for h in ("30", "60", "120", "cl"):
        s = R[f"s{h}"].dropna()
        hd = (R.loc[s.index, f"s{h}"] - 3 * R.loc[s.index, "cost"]).mean()
        print(f"    h{h:3s}: gross {s.mean():+6.2f} | mean hurdle "
              f"{3*R.loc[s.index,'cost'].mean():5.2f} | headroom {hd:+6.2f} bps")
    print("\n  by realised pair (each with its own hurdle):")
    for p, g in R.groupby("pair"):
        c = 3 * g.cost.mean()
        print(f"    {p:12s} n={len(g):4d} cost*3 {c:5.2f} | " +
              " ".join(f"h{h}:{g[f's{h}'].mean():+6.2f}" for h in ("30", "60", "120", "cl")))

    print("\n=== 4. HIGH vs ORDINARY DISPERSION ===")
    print(pd.concat([blk(R[R.disp == "HIGH"], "HIGH"),
                     blk(R[R.disp == "ORDINARY"], "ORDINARY")]).to_string(index=False))

    print("\n=== 5. LEG CONTRIBUTIONS, BY STRONGEST AND BY WEAKEST ===")
    for lab, col in (("strongest", "strong"), ("weakest", "weak")):
        print(f"  by {lab} instrument:")
        for c in RANKED:
            g = R[R[col] == c]
            if not len(g):
                continue
            print(f"    {c}: n={len(g):4d} " +
                  " ".join(f"h{h}:{g[f's{h}'].mean():+6.2f}" for h in ("30", "60", "120", "cl")))

    print("\n=== 6. CONTROLS ===")
    rng = np.random.default_rng(SEED)
    rev = R.copy()
    for h in ("30", "60", "120", "cl"):
        rev[f"s{h}"] = -R[f"s{h}"]
        rev[f"lng{h}"], rev[f"sht{h}"] = -R[f"sht{h}"], -R[f"lng{h}"]
        rev[f"mfe{h}"], rev[f"mae{h}"] = -R[f"mae{h}"], -R[f"mfe{h}"]
    sh = R.copy()
    perm = rng.permutation(len(R))
    for h in ("30", "60", "120", "cl"):
        sh[f"s{h}"] = R[f"s{h}"].values[perm]
        sh[f"lng{h}"] = R[f"lng{h}"].values[perm]
        sh[f"sht{h}"] = R[f"sht{h}"].values[perm]
        sh[f"mfe{h}"] = R[f"mfe{h}"].values[perm]
        sh[f"mae{h}"] = R[f"mae{h}"].values[perm]
    rawdf = R.copy()
    for h in ("30", "60", "120", "cl"):
        rawdf[f"s{h}"] = R[f"raw{h}"]
        rawdf[f"lng{h}"] = rawdf[f"sht{h}"] = np.nan
        rawdf[f"mfe{h}"] = rawdf[f"mae{h}"] = np.nan
    print(pd.concat([blk(R, "TRUE ranking"), blk(rev, "REVERSED"),
                     blk(sh, "SHUFFLED ranks"), blk(rawdf, "RAW, no beta adj")
                     ]).to_string(index=False))

    print("\n  RANDOM pair from the same three instruments, same dates:")
    out = []
    for h in ("30", "60", "120", "cl"):
        vals = []
        for _, r in R.iterrows():
            a_, b_ = rng.choice(RANKED, 2, replace=False)
            if r["strong"] == a_ and r["weak"] == b_:
                vals.append(r[f"s{h}"])
            elif r["strong"] == b_ and r["weak"] == a_:
                vals.append(-r[f"s{h}"])
            else:
                vals.append(np.nan)
        v = pd.Series(vals).dropna()
        out.append(dict(set="RANDOM pair", h=h, n=len(v),
                        spread=round(v.mean(), 2), pos=round(100 * (v > 0).mean(), 1)))
    print(pd.DataFrame(out).to_string(index=False))

    print("\n=== 7. BY YEAR ===")
    yy = pd.DatetimeIndex(R["date"]).year
    print(pd.concat([blk(R[yy == y], str(y)) for y in sorted(set(yy))]).to_string(index=False))

    print("\n=== APPENDIX: dispersion and t ===")
    for h in ("30", "60", "120", "cl"):
        s = R[f"s{h}"].dropna()
        se = s.std(ddof=1) / np.sqrt(len(s))
        print(f"  h{h:3s} n={len(s):4d} mean {s.mean():+6.2f} sd {s.std():6.2f} "
              f"SE {se:5.2f} t {s.mean()/se:+5.2f}")
    print(f"  mean formation dispersion D {R.D.mean():.2f} bps | "
          f"HIGH {R[R.disp=='HIGH'].D.mean():.2f} | ORDINARY {R[R.disp=='ORDINARY'].D.mean():.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
