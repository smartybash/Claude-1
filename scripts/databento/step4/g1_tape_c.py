#!/usr/bin/env python3
"""Step 4, G1 -- T06 weight rule + 1.5% CVD filter (oos.py), T07 CVD CHANGE gate
and T17 CVD LEVEL gates on the structure break (structure_cvd.py), T08 gap +
early CVD (gap_cvd.py).

PORT NOTE (committed before this file first ran)
------------------------------------------------
Data: 61 Databento discovery sessions (tape adapter); frozen constants unchanged;
cost 2.0 pt round trip (stricter than NQ/MNQ standard, applies). Every session is
out-of-sample for all four.

T06 primary: light levels AND cvd_against < 0.015 (oos.SKIP_SHARE), stop = target
    = 30, de-overlapped. Pass: net > 0, one-sided clustered p <= 0.05, and the
    kept trades beat the removed ones in mean.
T07 primary: structure_cvd "CHANGE: breaking bar 5%+ of its volume" (r1_with >=
    0.05), 3- and 5-minute bars, min_rr 0 as frozen. Two cells, Holm. Pass: gated
    trades net > 0 at one-sided p <= 0.05 AND the frozen paired comparison (gated
    minus refused, session bootstrap 8,000, seed 0) has a 95% interval above 0.
T17 primary: structure_cvd LEVEL gates (cvd_with >= 1,000; share_with >= 0.01),
    3 and 5 minutes. Four cells, Holm. Same pass bar as T07. (T07 and T17 were
    listed separately in the inventory and come from the same script; they are
    split by gate family, as the script's own tally splits them.)
T08 primary: the frozen permutation test of "early CVD agrees" minus "against"
    (group labels shuffled, 200,000 draws, seed 0), one-sided. FROZEN-DESIGN
    CAVEAT: the trade enters at the open while the filter uses the first 30
    minutes of flow, which is lookahead. The original result was recorded "as a
    direction, not a rule". A pass here answers the direction question only and
    CANNOT make T08 a trading candidate.
Old verdicts: T06 dead (OOS), T07 dead (does not reproduce), T17 dead, T08
direction only (p 0.028 on 6 sessions).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tape_lib as TL                                              # noqa: E402
C = TL.C


def pairs_of(D):
    k = sorted(D)
    return [(a, b) for a, b in zip(k, k[1:]) if len(pd.bdate_range(a, b)) == 2]


def t06(D):
    import oos as O
    import level_weight as LW
    import sweep2 as S2
    import tape
    C.run_frozen("oos", [], "T06_frozen_output.txt")
    T = LW.build(D, pairs_of(D)).reset_index(drop=True)
    T = T[T.light].reset_index(drop=True)
    share = []
    for _, r in T.iterrows():
        csig, cvol, _ = tape.prefix_sums(D[r.day])
        i = int(r.idx)
        share.append(np.nan if i < 200 else (csig[i] / cvol[i] if cvol[i] > 0 else np.nan))
    T["cvd_against"] = -np.array(share) * np.where(T.from_above, 1.0, -1.0)
    T = T.dropna(subset=["cvd_against"]).reset_index(drop=True)
    res = {}
    for lab, m in (("rule + CVD filter", T.cvd_against < O.SKIP_SHARE),
                   ("removed by filter", T.cvd_against >= O.SKIP_SHARE),
                   ("rule alone", T.cvd_against == T.cvd_against)):
        rows = [(d, S2.trade(D, T, LW.STOP, LW.TARGET, True, (m & (T.day == d)).values))
                for d in sorted(T.day.unique())]
        res[lab] = TL.cell_eval(rows, O.COST_PTS, D)
    return res


def boot_paired(rows, key, cut, n=8000, seed=0):
    df = pd.DataFrame(rows)
    df["hit"] = df[key] >= cut
    if df.hit.sum() < 8 or (~df.hit).sum() < 8:
        return np.nan, np.nan, np.nan
    d = df.R[df.hit].mean() - df.R[~df.hit].mean()
    by = {k: g for k, g in df.groupby("day")}
    sess = list(by)
    rng = np.random.default_rng(seed)
    boot = []
    for _ in range(n):
        g = pd.concat([by[x] for x in rng.choice(sess, size=len(sess), replace=True)])
        a, b = g.R[g.hit], g.R[~g.hit]
        if len(a) and len(b):
            boot.append(a.mean() - b.mean())
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return d, lo, hi


def t07_t17(D):
    import structure_cvd as SC
    C.run_frozen("structure_cvd", [], "T07_T17_frozen_output.txt")
    P = pairs_of(D)
    rows = {m: SC.collect(D, P, m, min_rr=0.0) for m in (3, 5)}
    gates = {"T07": [("r1_with", 0.05, "breaking bar 5%+ of volume")],
             "T17": [("cvd_with", 1000, "session delta >= +1,000"),
                     ("share_with", 0.01, "session delta >= 1% of volume")]}
    out = {}
    for tid, gl in gates.items():
        res, paired = {}, {}
        for m in (3, 5):
            for key, cut, lab in gl:
                on = [r for r in rows[m] if r[key] >= cut]
                per = {}
                for r in on:
                    per.setdefault(r["day"], []).append(r["pts"] + SC.COST_PTS)
                name = f"{m}-min {lab}"
                res[name] = TL.cell_eval(list(per.items()), SC.COST_PTS, D)
                paired[name] = boot_paired(rows[m], key, cut)
        out[tid] = (res, paired)
    return out


def t08(D):
    import gap_cvd as G
    import tape
    C.run_frozen("gap_cvd", [], "T08_frozen_output.txt")
    rows = []
    for d0, d1 in pairs_of(D):
        prev, s = D[d0], D[d1]
        pc, op = float(prev.price.iloc[-1]), float(s.price.iloc[0])
        gap = op - pc
        if abs(gap) < 10:
            continue
        up = gap < 0
        csig, cvol, _ = tape.prefix_sums(s)
        px, tm = s.price.to_numpy(), s.time.to_numpy()
        stop = op - G.STOP if up else op + G.STOP
        tgt = op + G.TARGET if up else op - G.TARGET
        out = None
        for i in range(1, len(px)):
            if (up and px[i] <= stop) or (not up and px[i] >= stop):
                out = -G.STOP
                break
            if (up and px[i] >= tgt) or (not up and px[i] <= tgt):
                out = G.TARGET
                break
        if out is None:
            out = (px[-1] - op) if up else (op - px[-1])
        cut = np.searchsorted(tm, np.datetime64(s.time.iloc[0] + pd.Timedelta(minutes=30)))
        cut = max(1, min(cut, len(px) - 1))
        early = csig[cut] / cvol[cut] if cvol[cut] > 0 else np.nan
        rows.append(dict(day=d1, gross=out, early_with=early * (1.0 if up else -1.0)))
    T = pd.DataFrame(rows)
    agree = (T.early_with > 0).to_numpy()
    net = T.gross.to_numpy() - G.COST_PTS
    obs = net[agree].mean() - net[~agree].mean()
    rng = np.random.default_rng(0)
    null = np.empty(200_000)
    for i in range(len(null)):
        lab = rng.permutation(agree)
        null[i] = net[lab].mean() - net[~lab].mean()
    p1 = float((1 + (null >= obs).sum()) / (len(null) + 1))
    res = {"gap trade, flow agrees": TL.cell_eval(
               [(r.day, [r.gross]) for r in T[agree].itertuples()], G.COST_PTS, D),
           "gap trade, flow against": TL.cell_eval(
               [(r.day, [r.gross]) for r in T[~agree].itertuples()], G.COST_PTS, D),
           "gap trade, no filter": TL.cell_eval(
               [(r.day, [r.gross]) for r in T.itertuples()], G.COST_PTS, D)}
    return res, obs, p1, len(T), int(agree.sum())


def main():
    D = TL.days()
    print(f"sessions: {len(D)}")
    r6 = t06(D)
    better = r6["rule + CVD filter"]["net_pts_mean"] > r6["removed by filter"]["net_pts_mean"]
    TL.report("T06", "weight rule + 1.5% CVD filter", r6, ["rule + CVD filter"],
              extra_ok=better, extra_lab=", kept beats removed", old="dead (OOS)")

    o = t07_t17(D)
    for tid, name, old in (("T07", "CVD CHANGE gate on structure break", "dead: does not reproduce"),
                           ("T17", "CVD LEVEL gates on structure break", "dead")):
        res, paired = o[tid]
        note = "; ".join(f"{k}: paired diff {d:+.3f}R [{lo:+.3f}, {hi:+.3f}]"
                         for k, (d, lo, hi) in paired.items())
        keys = list(res)
        raw = [res[k]["p_one"] if np.isfinite(res[k]["p_one"]) else 1.0 for k in keys]
        ph = C.holm(raw)
        best = keys[min(range(len(keys)), key=lambda i: (ph[i], raw[i]))]
        TL.report(tid, name, res, keys, extra_ok=bool(paired[best][1] > 0),
                  extra_lab=", paired interval above 0", old=old, note=note)

    r8, obs, p1, n, na = t08(D)
    L = [f"=== T08 gap + early CVD: {n} gap sessions, {na} with flow agreeing ===",
         f"  frozen permutation test, agree minus against: {obs:+.2f} pt, one-sided p = {p1:.4f}",
         "  CAVEAT: entry at the open, filter on the first 30 minutes (lookahead in the frozen design).",
         "  Direction question only; cannot be a trading candidate."]
    for k, r in r8.items():
        L.append(f"  {k:<28} {C.fmt(r)}")
    txt = "\n".join(L)
    print(txt)
    (C.OUT / "T08_output.txt").write_text(txt)
    r = r8["gap trade, flow agrees"]
    C.record(dict(id="T08", study="gap + early CVD (direction only)", primary="permutation agree-minus-against",
                  n=r["n"], sessions=r.get("n_sessions"), net_pts=r["net_pts_mean"],
                  usd_trade=r["usd_per_trade"], sharpe=r["sharpe"], cagr=r["cagr"], dd_nq=r["dd_NQ"],
                  dd_mnq=r["dd_MNQ"], pf=r["pf"], t=r["t"], p_raw=np.nan, p_one=p1, p_study=p1,
                  pass_bar=False, old_verdict="direction only (p 0.028, 6 sessions)",
                  new_verdict_pre_bh=f"direction p {p1:.4f}; not a candidate (lookahead)"))


if __name__ == "__main__":
    main()
