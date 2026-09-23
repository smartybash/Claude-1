#!/usr/bin/env python3
"""RP-006B Stage 1 — corrected cross-sectional intraday momentum. DESCRIPTIVE.

Pre-registered at commit d26c066 (reports/rp006b_preregistration.md), written
and committed before this script was executed.

Discovery = 2023 ONLY. 2024 and 2025 are NOT read. 2021-2022 is contaminated and
contributes NO observation and NO forward return.

WARM-UP DECLARATION: the 20-session beta window and the 60-session dispersion
tercile reference are drawn from late 2022. These are causal ESTIMATION INPUTS.
No 2022 session produces an observation and no outcome return is computed for
any 2022 date, so 2021-2022 enters no performance calculation. Without this the
first 80 sessions of 2023 would be lost.

Corrections applied to the defective RP-006 harness:
  * session eligibility is the six measurement timestamps + >=300 bars pairwise
    against SPY + a fresh 10:00 print -- NOT a 4-way 380-bar intersection
  * rank domination flagged at >80% / <53% against the 66.7% structural baseline
  * shuffled control permutes the (strong, weak) IDENTITY across dates
  * random-pair control evaluates the drawn pair on EVERY date
  * both randomised controls are repeated 200x and reported as distributions
"""
from __future__ import annotations

import sys
from itertools import combinations, permutations
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
LOAD_FROM, LOAD_TO = "2022-08-01", "2023-12-31"
OBS_FROM, OBS_TO = "2023-01-01", "2023-12-31"
RANKED = ("QQQ", "IWM", "IJH")
FACTOR = "SPY"
BETA_LB, DISP_LB = 20, 60
MIN_PAIR_BARS = 300
SEED, NREP = 20260923, 200
COST_PER_SHARE = 0.01 + 2 * 0.0035
HZ = (("30", 30), ("60", 60), ("120", 120), ("cl", None))


def load():
    paths = {"QQQ": "data/intraday_long/QQQ_1m.parquet"}
    paths.update({s: f"data/related/{s}_1m.parquet" for s in ("SPY", "IWM", "IJH")})
    F = {}
    for k, p in paths.items():
        d = pd.read_parquet(ROOT / p, columns=["timestamp", "close"])
        d["ts"] = pd.to_datetime(d["timestamp"])
        d = d[(d["ts"] >= LOAD_FROM) & (d["ts"] <= LOAD_TO + " 23:59")]
        F[k] = d.set_index("ts")["close"]
    return F


def build(F):
    """Per-session structures. Eligibility is checked against the SIX timestamps
    the design actually reads, not against a whole-session bar count."""
    allts = sorted(set().union(*[set(v.index) for v in F.values()]))
    days = sorted({t.normalize() for t in allts})
    byday = {k: {d: v[v.index.normalize() == d] for d in days} for k, v in F.items()}

    fails = dict(missing_ts=0, few_pair_bars=0, stale_1000=0, eligible=0)
    S = {}
    for d in days:
        g = {k: byday[k][d].sort_index() for k in F}
        if any(len(v) == 0 for v in g.values()):
            fails["missing_ts"] += 1
            continue
        mod = {k: (v.index.hour * 60 + v.index.minute).values for k, v in g.items()}

        def at(k, m):
            w = np.where(mod[k] == m)[0]
            return int(w[0]) if len(w) else None

        need = [570, 600, 630, 660, 720]
        pos = {k: {m: at(k, m) for m in need} for k in F}
        if any(pos[k][m] is None for k in F for m in need):
            fails["missing_ts"] += 1
            continue
        # fresh 10:00 print: not a repeat of 09:59 (09:30 is the session's first
        # bar, so staleness is undefined there and presence is the only test)
        stale = False
        for k in F:
            i = pos[k][600]
            if i > 0 and float(g[k].iloc[i]) == float(g[k].iloc[i - 1]):
                stale = True
        if stale:
            fails["stale_1000"] += 1
            continue
        S[d] = dict(g=g, mod=mod, pos=pos,
                    log={k: np.log(g[k].values) for k in F},
                    px={k: g[k].values for k in F})
        fails["eligible"] += 1
    return S, sorted(S.keys()), fails


def pairwise_bars(S, d, c):
    """Bars where the ranked instrument and SPY both print, same session."""
    a, b = S[d]["mod"][c], S[d]["mod"][FACTOR]
    return len(np.intersect1d(a, b))


def beta_from(S, days, i, c):
    """No-intercept OLS on the pairwise-aligned 1-min returns of the 20 PRIOR
    completed sessions. Current session excluded."""
    num = den = 0.0
    for j in range(i - BETA_LB, i):
        d = days[j]
        common = np.intersect1d(S[d]["mod"][c], S[d]["mod"][FACTOR])
        if len(common) < MIN_PAIR_BARS:
            continue
        ic = np.searchsorted(S[d]["mod"][c], common)
        isp = np.searchsorted(S[d]["mod"][FACTOR], common)
        rc = np.diff(S[d]["log"][c][ic])
        rs = np.diff(S[d]["log"][FACTOR][isp])
        num += float(np.dot(rc, rs)); den += float(np.dot(rs, rs))
    return num / den if den > 0 else np.nan


def main() -> int:
    F = load()
    S, days, fails = build(F)
    obs_days = [d for d in days if OBS_FROM <= str(d.date()) <= OBS_TO]
    start = days.index(obs_days[0])
    if start < BETA_LB + DISP_LB:
        print("insufficient warm-up"); return 1

    rows, few = [], 0
    for i in range(start, len(days)):
        d = days[i]
        if str(d.date()) > OBS_TO:
            break
        if any(pairwise_bars(S, d, c) < MIN_PAIR_BARS for c in RANKED):
            few += 1
            continue
        beta = {c: beta_from(S, days, i, c) for c in RANKED}
        if any(not np.isfinite(b) for b in beta.values()):
            continue
        L, P, pos = S[d]["log"], S[d]["px"], S[d]["pos"]
        mkt = L[FACTOR][pos[FACTOR][600]] - L[FACTOR][pos[FACTOR][570]]
        a = {c: (L[c][pos[c][600]] - L[c][pos[c][570]]) - beta[c] * mkt for c in RANKED}
        raw = {c: L[c][pos[c][600]] - L[c][pos[c][570]] for c in RANKED}

        rec = dict(date=d, strong=max(a, key=a.get), weak=min(a, key=a.get),
                   rstrong=max(raw, key=raw.get), rweak=min(raw, key=raw.get),
                   D=1e4 * (max(a.values()) - min(a.values())))
        for lab, off in HZ:
            for c in RANKED:
                k = pos[c][600] + off if off is not None else len(L[c]) - 1
                ks = pos[FACTOR][600] + off if off is not None else len(L[FACTOR]) - 1
                if k >= len(L[c]) or ks >= len(L[FACTOR]):
                    rec[f"f_{c}_{lab}"] = rec[f"r_{c}_{lab}"] = np.nan
                    continue
                rec[f"f_{c}_{lab}"] = 1e4 * ((L[c][k] - L[c][pos[c][600]])
                                             - beta[c] * (L[FACTOR][ks] - L[FACTOR][pos[FACTOR][600]]))
                rec[f"r_{c}_{lab}"] = 1e4 * (L[c][k] - L[c][pos[c][600]])
        for c in RANKED:
            rec[f"px_{c}"] = float(P[c][pos[c][600]])
        rows.append(rec)

    R = pd.DataFrame(rows)
    q = np.full(len(R), np.nan)
    Dv = R["D"].values
    # dispersion tercile needs 60 PRIOR D values; the first 60 come from the
    # warm-up sessions, computed the same way
    warm = []
    for i in range(start - DISP_LB, start):
        d = days[i]
        if any(pairwise_bars(S, d, c) < MIN_PAIR_BARS for c in RANKED):
            continue
        beta = {c: beta_from(S, days, i, c) for c in RANKED}
        if any(not np.isfinite(b) for b in beta.values()):
            continue
        L, pos = S[d]["log"], S[d]["pos"]
        mkt = L[FACTOR][pos[FACTOR][600]] - L[FACTOR][pos[FACTOR][570]]
        aa = {c: (L[c][pos[c][600]] - L[c][pos[c][570]]) - beta[c] * mkt for c in RANKED}
        warm.append(1e4 * (max(aa.values()) - min(aa.values())))
    hist = list(warm)
    for k in range(len(Dv)):
        if len(hist) >= DISP_LB:
            q[k] = (np.array(hist[-DISP_LB:]) < Dv[k]).mean()
        hist.append(Dv[k])
    R = R.assign(dq=q)
    R = R[R["dq"].notna()].copy()
    R["disp"] = np.where(R["dq"] >= 2 / 3, "HIGH", "ORDINARY")
    for lab, _ in HZ:
        R[f"s{lab}"] = [r[f"f_{r['strong']}_{lab}"] - r[f"f_{r['weak']}_{lab}"]
                        for _, r in R.iterrows()]
        R[f"lng{lab}"] = [r[f"f_{r['strong']}_{lab}"] for _, r in R.iterrows()]
        R[f"sht{lab}"] = [-r[f"f_{r['weak']}_{lab}"] for _, r in R.iterrows()]
        R[f"raw{lab}"] = [r[f"r_{r['rstrong']}_{lab}"] - r[f"r_{r['rweak']}_{lab}"]
                          for _, r in R.iterrows()]
    R["pair"] = [" / ".join(sorted([r["strong"], r["weak"]])) for _, r in R.iterrows()]
    R["cost"] = [1e4 * COST_PER_SHARE * (1 / r[f"px_{r['strong']}"]
                                         + 1 / r[f"px_{r['weak']}"]) for _, r in R.iterrows()]
    months = len(pd.PeriodIndex(pd.DatetimeIndex(R["date"]), freq="M").unique())

    print("RP-006B DISCOVERY 2023 ONLY.  2024 and 2025 NOT read.  "
          "2021-2022 contributes no observation.")
    print("*** Three-instrument ranking: only 3 unordered pairs. Thin. ***")
    print("\n=== 1. ELIGIBILITY FUNNEL ===")
    print(f"  sessions loaded (incl. warm-up window)  {len(days)}")
    print(f"  excluded: missing one of the six timestamps  {fails['missing_ts']}")
    print(f"  excluded: stale 10:00 print                  {fails['stale_1000']}")
    print(f"  excluded: <{MIN_PAIR_BARS} pairwise bars vs SPY   {few}")
    print(f"  ELIGIBLE 2023 observations {len(R)} | months {months} | "
          f"per month {len(R)/months:.2f}")
    print(f"  HIGH dispersion {int((R.disp=='HIGH').sum())} "
          f"({len(R[R.disp=='HIGH'])/months:.2f}/mo) | ORDINARY {int((R.disp=='ORDINARY').sum())}")

    print("\n=== 2. RANK BALANCE (neutral baseline 66.7%) ===")
    dom = {}
    for c in RANKED:
        s, w = (R.strong == c).mean(), (R.weak == c).mean()
        ext = ((R.strong == c) | (R.weak == c)).mean()
        dom[c] = ext
        tag = "  <== FLAG >80%" if ext > 0.80 else ("  <== FLAG <53%" if ext < 0.53 else "")
        print(f"  {c}: strongest {100*s:5.1f}%  weakest {100*w:5.1f}%  "
              f"either {100*ext:5.1f}%  deviation {100*(ext-2/3):+5.1f} pts{tag}")

    print("\n=== 3. PAIR COUNTS (6 directional) ===")
    for lo, hi in permutations(RANKED, 2):
        k = int(((R.strong == lo) & (R.weak == hi)).sum())
        print(f"  long {lo:4s} / short {hi:4s}  n={k:4d}  {100*k/len(R):5.1f}%")

    def blk(df, lab, col="s"):
        out = []
        for h, _ in HZ:
            s = df[f"{col}{h}"].dropna()
            if not len(s):
                continue
            r = dict(set=lab, h=h, n=len(s), spread=round(s.mean(), 2),
                     med=round(s.median(), 2), pos=round(100 * (s > 0).mean(), 1))
            if col == "s":
                r["long_leg"] = round(df[f"lng{h}"].mean(), 2)
                r["short_leg"] = round(df[f"sht{h}"].mean(), 2)
            out.append(r)
        return pd.DataFrame(out)

    print("\n=== 4. FUTURE SPREAD BY HORIZON (forward only) ===")
    print(blk(R, "ALL").to_string(index=False))

    print("\n=== 5. PAIR-SPECIFIC COST AND HEADROOM ===")
    for h, _ in HZ:
        s = R[f"s{h}"].dropna()
        hd = (R.loc[s.index, f"s{h}"] - 3 * R.loc[s.index, "cost"]).mean()
        print(f"  h{h:3s} gross {s.mean():+6.2f} | 3x cost "
              f"{3*R.loc[s.index,'cost'].mean():5.2f} | headroom {hd:+6.2f} bps")
    print("  by realised pair:")
    for p, g in R.groupby("pair"):
        print(f"    {p:12s} n={len(g):4d} 3xcost {3*g.cost.mean():5.2f} | " +
              " ".join(f"h{h}:{g[f's{h}'].mean():+6.2f}" for h, _ in HZ))

    print("\n=== 6. HIGH vs ORDINARY DISPERSION ===")
    print(pd.concat([blk(R[R.disp == "HIGH"], "HIGH"),
                     blk(R[R.disp == "ORDINARY"], "ORDINARY")]).to_string(index=False))

    print("\n=== 7. CONTROLS ===")
    rev = R.copy()
    for h, _ in HZ:
        rev[f"s{h}"] = -R[f"s{h}"]; rev[f"lng{h}"] = -R[f"sht{h}"]; rev[f"sht{h}"] = -R[f"lng{h}"]
    print(pd.concat([blk(R, "TRUE"), blk(rev, "REVERSED"),
                     blk(R, "RAW no beta", col="raw")]).to_string(index=False))

    rng = np.random.default_rng(SEED)
    print(f"\n  RANDOM-PAIR control, {NREP} repetitions, evaluated on EVERY date:")
    for h, _ in HZ:
        means = []
        for _ in range(NREP):
            v = []
            for _, r in R.iterrows():
                lo, hi = rng.choice(RANKED, 2, replace=False)
                v.append(r[f"f_{lo}_{h}"] - r[f"f_{hi}_{h}"])
            means.append(np.nanmean(v))
        m = np.array(means)
        print(f"    h{h:3s} mean {m.mean():+6.2f} sd {m.std():5.2f} "
              f"p5 {np.percentile(m,5):+6.2f} p95 {np.percentile(m,95):+6.2f} | "
              f"TRUE {R[f's{h}'].mean():+6.2f}")

    print(f"\n  SHUFFLED-RANKING control, {NREP} repetitions "
          f"(permutes the (strong, weak) identity across dates):")
    idpairs = list(zip(R["strong"].values, R["weak"].values))
    for h, _ in HZ:
        means = []
        for _ in range(NREP):
            perm = rng.permutation(len(R))
            v = [R.iloc[k][f"f_{idpairs[perm[k]][0]}_{h}"]
                 - R.iloc[k][f"f_{idpairs[perm[k]][1]}_{h}"] for k in range(len(R))]
            means.append(np.nanmean(v))
        m = np.array(means)
        print(f"    h{h:3s} mean {m.mean():+6.2f} sd {m.std():5.2f} "
              f"p5 {np.percentile(m,5):+6.2f} p95 {np.percentile(m,95):+6.2f} | "
              f"TRUE {R[f's{h}'].mean():+6.2f}")

    print("\n=== 8. PAIR CONCENTRATION (no pair may carry >60%) ===")
    for h, _ in HZ:
        tot = sum(abs(g[f"s{h}"].sum()) for _, g in R.groupby("pair"))
        parts = {p: abs(g[f"s{h}"].sum()) / tot for p, g in R.groupby("pair")} if tot > 0 else {}
        top = max(parts, key=parts.get) if parts else "-"
        print(f"  h{h:3s} " + "  ".join(f"{p}:{100*v:5.1f}%" for p, v in parts.items())
              + f"   max {top} {'<== >60%' if parts and parts[top] > .60 else ''}")

    print("\n=== APPENDIX ===")
    for h, _ in HZ:
        s = R[f"s{h}"].dropna()
        se = s.std(ddof=1) / np.sqrt(len(s))
        print(f"  h{h:3s} n={len(s):4d} mean {s.mean():+6.2f} sd {s.std():6.2f} "
              f"SE {se:5.2f} t {s.mean()/se:+5.2f}")
    print(f"  mean D {R.D.mean():.2f} | HIGH {R[R.disp=='HIGH'].D.mean():.2f} | "
          f"ORDINARY {R[R.disp=='ORDINARY'].D.mean():.2f}")
    if dom.get("QQQ", 0) > 0.80:
        nq = R[(R.strong != "QQQ") & (R.weak != "QQQ")]
        print(f"\n  QQQ >80% diagnostic: excluding all QQQ pairs leaves n={len(nq)}")
        if len(nq):
            print("   " + "  ".join(f"h{h}:{nq[f's{h}'].mean():+6.2f}" for h, _ in HZ))
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
