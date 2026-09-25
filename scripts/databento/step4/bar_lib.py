"""Shared helpers for step-4 BAR ports (G2-G4).

Prices in data/clean/step4/NQ_1m*.parquet are ratio back-adjusted. A trade's
points measured on those bars are converted to real NQ points by dividing by the
session's cumulative factor (NQ_factor.parquet); frozen costs expressed in
adjusted points are converted the same way. Dollars then follow from $20/pt
(NQ) and $2/pt (MNQ) inside step4_common.evaluate.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import step4_common as C                                           # noqa: E402

S4 = C.ROOT / "data/clean/step4"
NQ_FULL = S4 / "NQ_1m.parquet"
NQ_2021 = S4 / "NQ_1m_2021.parquet"
NQ_ETH_FULL = S4 / "NQ_1m_eth.parquet"
NQ_ETH_2021 = S4 / "NQ_1m_eth_2021.parquet"
WINDOWS = {"full": ("2010-06-07", "2026-09-24"), "2021": ("2021-01-04", "2026-08-31")}

_F = None


def factor():
    global _F
    if _F is None:
        f = pd.read_parquet(S4 / "NQ_factor.parquet")
        _F = pd.Series(f.factor.to_numpy(), index=pd.to_datetime(f.day))
    return _F


def sessions_in(window):
    a, b = WINDOWS[window]
    f = factor()
    return f.index[(f.index >= a) & (f.index <= b)]


def evaluate_adj(days, gross_adj_pts, window, frozen_rt_adj_pts=0.0):
    """Trades measured on adjusted bars -> step4_common.evaluate in real points."""
    d = pd.to_datetime(pd.Index(days))
    fac = factor().reindex(d).to_numpy()
    if np.isnan(fac).any():
        raise ValueError("trade on a session without a factor")
    g = np.asarray(gross_adj_pts, float) / fac
    fr = np.asarray(frozen_rt_adj_pts, float)
    fr = fr / fac if fr.ndim else fr          # scalar frozen costs are in real NQ points
    return C.evaluate(d, g, sessions_in(window), close_by_session=C.nq_close(),
                      frozen_rt_pts=fr)


def report_bar(tid, name, res, primary, pass_flags, old, note="", window_note=""):
    """res: {cell: {"full": metrics, "2021": metrics}}; pass_flags: {cell: bool}
    (frozen pass bar on the FULL sample, after NQ costs)."""
    L = [f"=== {tid} {name} (NQ 1-minute; primary = full 2010-06-07 -> 2026-09-24) ==="]
    if note:
        L.append(f"  note: {note}")
    keys = list(primary)
    raw = [res[k]["full"]["p_one"] if np.isfinite(res[k]["full"]["p_one"]) else 1.0 for k in keys]
    ph = C.holm(raw)
    for k in res:
        L.append(f"  {k:<26} FULL {C.fmt(res[k]['full'])}")
        if "2021" in res[k]:
            L.append(f"  {'':<26} 2021 {C.fmt(res[k]['2021'])}")
        L.append(f"  {'':<26} frozen pass bar (full, NQ costs): {'MET' if pass_flags.get(k) else 'not met'}")
    best = keys[min(range(len(keys)), key=lambda i: (ph[i], raw[i]))]
    pstudy = float(ph.min())
    r = res[best]["full"]
    ok = bool(pass_flags.get(best) and r["net_pts_mean"] > 0)
    L.append(f"  PRIMARY: {len(keys)} cell(s), Holm on one-sided p (full sample); best = {best}, "
             f"study p = {pstudy:.4f}")
    L.append(f"  frozen pass bar for best cell: {'MET' if ok else 'NOT MET'} -> "
             f"{'candidate for BH' if ok and pstudy <= 0.05 else 'stays closed' if not ok else 'bar met, p > 0.05: stays closed pending BH'}")
    txt = "\n".join(L)
    (C.OUT / f"{tid}_output.txt").write_text(txt)
    print(txt, "\n")
    r21 = res[best].get("2021", {})
    C.record(dict(id=tid, study=name, primary=best, n=r["n"], sessions=r.get("n_sessions"),
                  net_pts=r["net_pts_mean"], usd_trade=r["usd_per_trade"], sharpe=r["sharpe"],
                  cagr=r["cagr"], dd_nq=r["dd_NQ"], dd_mnq=r["dd_MNQ"], pf=r["pf"],
                  t=r["t"], p_raw=r["p"], p_one=r["p_one"], p_study=pstudy, pass_bar=ok,
                  sharpe_2021=r21.get("sharpe"), net_pts_2021=r21.get("net_pts_mean"),
                  old_verdict=old, new_verdict_pre_bh="pass bar met" if ok else "stays closed"))
    return ok
