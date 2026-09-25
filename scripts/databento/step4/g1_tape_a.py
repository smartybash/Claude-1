#!/usr/bin/env python3
"""Step 4, G1 -- T01 absorption, T02 tape sweep, T03 CVD-divergence audit.

PORT NOTE (committed before this file first ran)
------------------------------------------------
Data: 61 Databento discovery sessions via step4_adapters.load_tape_all(), patched
in for tape.load_all. Everything else is the frozen script: windows, quantiles,
the 5.0-point "no progress" band (set for the ATAS grid and kept frozen, not
re-tuned), holds, and the 2.0-point round-trip cost, which is stricter than the
NQ standard 0.725 and so applies (MNQ: max(2.0, 1.12) = 2.0 points).

Each frozen main() runs unchanged and its output is saved. The primary
statistics are then recomputed from the modules' own functions with session
labels kept, so they can be session-clustered (the frozen scripts pool
overlapping windows; the repository's audits established the per-session
statistic as the honest one).

T01 primary: the two absorption cells (buying absorbed -> short; selling
    absorbed -> long), 30 s windows, hold 4, heavy = top/bottom 20% of delta per
    session, flat = |move| <= 5.0. Holm across the two; study p = smaller.
T02 primary: every cost-bearing cell of H1 (8), H2 (8) and H3 (6) = 22 cells.
    Holm across 22; study p = smallest. H0 (no cost) reported only.
T03 primary: CVD divergence at 60-minute extremes, hold 5 min, no overlapping
    holds, net of cost. Pass also requires beating the frozen control (the same
    extremes without the CVD condition) in mean.
Pass bar (all three): net mean > 0 and study p <= 0.05, before the batch BH.
Old verdicts: T01 dead, T02 dead (except the H3 cell), T03 dead.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import step4_common as C                                           # noqa: E402
import step4_adapters as A                                         # noqa: E402
import tape                                                        # noqa: E402

tape.load_all = A.load_tape_all


def days():
    d = {k: tape.rth(v) for k, v in sorted(A.load_tape_all().items())}
    return {k: s for k, s in d.items() if len(s) > 5000}


def sess(k):
    return pd.Timestamp(f"{k[:4]}-{k[4:6]}-{k[6:]}")


def cell_eval(rows, frozen_rt, all_sessions):
    """rows: list of (session_key, gross_pts array)."""
    s = np.concatenate([[sess(k)] * len(v) for k, v in rows]) if rows else []
    g = np.concatenate([v for _, v in rows]) if rows else np.array([])
    ok = np.isfinite(g)
    return C.evaluate(pd.Index(s)[ok], g[ok], [sess(k) for k in all_sessions],
                      close_by_session=C.nq_close(), frozen_rt_pts=frozen_rt)


def t01(D):
    import absorption as M
    C.run_frozen("absorption", [], "T01_frozen_output.txt")
    rows = {"buy_absorbed_short": [], "sell_absorbed_long": []}
    for k, s in D.items():
        w = M.windows(s, 30)
        w["f"] = M.fwd(w, 4)
        hi, lo = w.delta.quantile(0.80), w.delta.quantile(0.20)
        flat = w["move"].abs() <= 5.0
        rows["buy_absorbed_short"].append((k, -w[(w.delta >= hi) & flat].f.values))
        rows["sell_absorbed_long"].append((k, w[(w.delta <= lo) & flat].f.values))
    return {c: cell_eval(v, M.COST_PTS, D) for c, v in rows.items()}


def t02(D):
    import sweep_tape as M
    C.run_frozen("sweep_tape", [], "T02_frozen_output.txt")
    cells = {}
    W = {(k, secs): M.windows(s, secs) for k, s in D.items() for secs in (30, 60)}
    for secs in (30, 60):
        for hold_s in (120, 300, 600, 1800):
            kk = max(1, hold_s // secs)
            rows = []
            for k in D:
                w = W[(k, secs)]
                f = w["last"].shift(-kk) - w["last"]
                sel = (w.delta >= w.delta.quantile(0.80)) & (w["move"].abs() <= 5)
                rows.append((k, (-f[sel]).values))
            cells[f"H1 {secs}s hold {hold_s//60}m"] = rows
    for q in (0.99, 0.999):
        for hold_s in (120, 600):
            kk = hold_s // 30
            go, fade = [], []
            for k, s in D.items():
                w = W[(k, 30)]
                bw, _ = M.block_windows(s, 30, q)
                w = w.join(bw).fillna({"bdelta": 0.0, "bvol": 0.0})
                f = w["last"].shift(-kk) - w["last"]
                hot = w.bdelta.abs() >= w.bdelta.abs().quantile(0.90)
                sgn = np.sign(w.bdelta)
                go.append((k, (sgn * f)[hot & (sgn != 0)].values))
                fade.append((k, (-sgn * f)[hot & (sgn != 0)].values))
            cells[f"H2 q{q} go hold {hold_s//60}m"] = go
            cells[f"H2 q{q} fade hold {hold_s//60}m"] = fade
    for look_m in (15, 30, 60):
        for hold_s in (300, 900):
            kk, L = hold_s // 30, look_m * 2
            rows = []
            for k in D:
                w = W[(k, 30)].copy()
                w["cvd"] = w.delta.cumsum()
                f = w["last"].shift(-kk) - w["last"]
                short = (w["last"] >= w["last"].rolling(L).max()) & (w["cvd"] < w["cvd"].rolling(L).max())
                long_ = (w["last"] <= w["last"].rolling(L).min()) & (w["cvd"] > w["cvd"].rolling(L).min())
                rows.append((k, np.concatenate([(-f[short]).values, f[long_].values])))
            cells[f"H3 look {look_m}m hold {hold_s//60}m"] = rows
    return {c: cell_eval(v, M.COST_PTS, D) for c, v in cells.items()}


def t03(D):
    import divergence_audit as M
    C.run_frozen("divergence_audit", [], "T03_frozen_output.txt")
    out = {}
    for use_cvd, lab in ((True, "divergence_dedup"), (False, "control_no_cvd")):
        rows = []
        for k, s in D.items():
            w = M.windows(s)
            tr, kk = M.trades(w, use_cvd, True)
            rows.append((k, M.pnl(w, tr, kk)))
        out[lab] = cell_eval(rows, M.COST_PTS, D)
    return out


def report(tid, name, res, primary, extra_ok=True, old="dead"):
    L = [f"=== {tid} {name} (61 Databento discovery sessions) ==="]
    keys = list(primary)
    ph = C.holm([res[k]["p_one"] if np.isfinite(res[k]["p_one"]) else 1.0 for k in keys])
    for k in res:
        L.append(f"  {k:<28} {C.fmt(res[k])}")
    raw = [res[k]["p_one"] if np.isfinite(res[k]["p_one"]) else 1.0 for k in keys]
    best = keys[min(range(len(keys)), key=lambda i: (ph[i], raw[i]))]
    pstudy = float(ph.min())
    ok = res[best]["net_pts_mean"] > 0 and pstudy <= 0.05 and extra_ok
    L.append(f"  PRIMARY: {len(keys)} cell(s), Holm on one-sided p; best = {best}, study p = {pstudy:.4f}")
    L.append(f"  pass bar (net > 0, p <= 0.05{', beats control' if tid == 'T03' else ''}): "
             f"{'MET' if ok else 'NOT MET'}  -> {'candidate for BH' if ok else 'stays closed'}")
    txt = "\n".join(L)
    (C.OUT / f"{tid}_output.txt").write_text(txt)
    print(txt, "\n")
    r = res[best]
    C.record(dict(id=tid, study=name, primary=best, n=r["n"], sessions=r["n_sessions"],
                  net_pts=r["net_pts_mean"], usd_trade=r["usd_per_trade"], sharpe=r["sharpe"],
                  cagr=r["cagr"], dd_nq=r["dd_NQ"], dd_mnq=r["dd_MNQ"], pf=r["pf"],
                  t=r["t"], p_raw=r["p"], p_one=r["p_one"], p_study=pstudy, pass_bar=ok,
                  old_verdict=old, new_verdict_pre_bh="pass bar met" if ok else "stays closed"))


def main():
    D = days()
    print(f"sessions: {len(D)}")
    r1 = t01(D)
    report("T01", "absorption 2x2", r1, ["buy_absorbed_short", "sell_absorbed_long"])
    r2 = t02(D)
    report("T02", "tape hypothesis sweep", r2, list(r2), old="dead except H3 cell")
    r3 = t03(D)
    beats = r3["divergence_dedup"]["net_pts_mean"] > r3["control_no_cvd"]["net_pts_mean"]
    report("T03", "CVD divergence audit", r3, ["divergence_dedup"], extra_ok=beats)


if __name__ == "__main__":
    main()
